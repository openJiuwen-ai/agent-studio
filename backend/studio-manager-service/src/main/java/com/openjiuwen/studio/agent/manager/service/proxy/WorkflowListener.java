/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import static com.openjiuwen.studio.agent.manager.constant.Constant.REQUEST_ID;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;
import com.openjiuwen.studio.agent.manager.observability.CorrelationIdValidator;
import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;
import com.openjiuwen.studio.agent.manager.service.JiuwenEventProcessor;
import com.openjiuwen.studio.agent.manager.service.WorkflowInstanceService;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 工作流（Workflow）SSE事件监听器
 * 基于 OkHttp SSE（Server-Sent Events）机制，实时监听工作流执行过程中由九问（Jiuwen）引擎推送的各类事件流，
 * 完成事件解析、状态维护、前端透传和持久化存储等核心职责。
 *
 * <p>DEF-02：四个公开回调已由 {@link BaseEventListener} 声明为 {@code final} 并用快照 scope 包装，
 * 本类只覆盖 protected hook；中断保存、实例 ID 一律使用 {@code executeParams.executionId}
 * （Manager 选定权威值），不再从回调线程 MDC 或 {@code requestId} 兜底。
 */
@Slf4j
public class WorkflowListener extends BaseEventListener {
    private final WorkflowInstanceService instanceService;

    private final JiuwenEventProcessor eventProcessor;

    private final AgentRuntimeService agentRuntimeService;

    /**
     * 旁路线程池，用于 node_wait 的 saveTaskId 异步写 Redis，避免阻塞 SSE 事件透传。
     */
    private final Executor persistenceExecutor;

    /**
     * node_wait 透传节流窗口（毫秒）。循环节点密集 node_wait 逐个同步 sseEmitter.send 会阻塞
     * OkHttp SSE 回调线程导致事件积压（如 796a5338 runtime 退出后 manager 仍拖延 23s）。
     * 窗口内只 passThrough 一条 node_wait，其余仅 saveTaskId 异步落盘、跳过 send。
     */
    private static final long NODE_WAIT_PASSTHROUGH_THROTTLE_MS = 50L;

    private final ConcurrentHashMap<String, AtomicLong> nodeWaitLastPassThrough = new ConcurrentHashMap<>();

    private String lastSavedResumeExecutionId;

    protected final ExecuteParams executeParams;

    protected final WorkflowRunResult result;

    private static final String JIUWEN_EXCEPTION_NODE_ID = "jiuwen_exception_node_id";

    private static final List<JiuwenEventType> TO_RECORD_EVENTS = List.of(
        JiuwenEventType.START,
        JiuwenEventType.WORKFLOW_STARTED,
        JiuwenEventType.DONE,
        JiuwenEventType.WORKFLOW_FINISHED,
        JiuwenEventType.WORKFLOW_NODE_MESSAGE,
        JiuwenEventType.EXCEPTION);

    private int eventNum;

    public WorkflowListener(String requestId, ExecuteParams executeParams, WorkflowRunResult result,
        HttpHeaders headers) {
        super(requestId, headers);
        instanceService = SpringBeanUtils.getBean(WorkflowInstanceService.class);
        eventProcessor = SpringBeanUtils.getBean(JiuwenEventProcessor.class);
        agentRuntimeService = SpringBeanUtils.getBean(AgentRuntimeService.class);
        persistenceExecutor = SpringBeanUtils.getBean("insightPersistenceExecutor", Executor.class);
        this.executeParams = executeParams;
        this.result = result;
        eventNum = 0;
    }

    @Override
    protected void onEventBusinessHook(@Nullable String id, @Nullable String type, @NotNull String data) {
        ++eventNum;
        process(data);
    }

    @Override
    protected void onFailureInternal(@Nullable Throwable t, @Nullable Response response) {
        // DEF-02: 不再 MDC.put(REQUEST_ID)，快照 scope 已在 BaseEventListener.onFailure 安装并恢复
        try {
            // COM-04 响应 §5.4: handleTerminalFailure 返回赢家 descriptor（非赢家 null）
            // 完整栈只由赢家记录一次（handleTerminalFailure → logDownstreamFailureOnce）
            ErrorDescriptor descriptor = handleTerminalFailure(t, response);
            if (descriptor != null) {
                executeParams.setSuccess(-1);
                if (executeParams.isCanceled()) {
                    closed("canceled.");
                }
            }
        } catch (Exception e) {
            log.error("Fail handler response. {}", e.getMessage());
        } finally {
            latch.countDown();
            try {
                sseEmitter.complete();
            } catch (Throwable e) {
                log.warn("Fail close sse. {}", e.getMessage());
            }
        }
    }

    @Override
    protected void onClosedBusinessHook() {
        log.info("Workflow request is closed.");
        doClose("onClosed");
    }

    public JiuwenEventType process(@NotNull String eventStr) {
        WorkflowInstanceEntity instance = result.getInstance();
        if (instance == null) {
            instance = new WorkflowInstanceEntity();
            result.setInstance(instance);
        }

        // 先从原始JSON中提取event类型
        String event = extractEventFromJson(eventStr);
        JiuwenEventType eventType;
        try {
            eventType = JiuwenEventType.valueOf(event.toUpperCase(Locale.ROOT));
        } catch (Exception e) {
            // node_wait 事件不在 JiuwenEventType 枚举中，但需要保存 taskId 以支持中断恢复
            if ("node_wait".equalsIgnoreCase(event)) {
                saveResumeExecutionIdOnInterrupt();
                // Bug1①: resume 轮首个事件通常是 node_wait，走此 early-return 跳过了 processStart
                //（processStart 只在 eventNum==1 且非 early-return 时触发 getCache+copy 归并）。
                // 不归并的话，每轮 saveInsightMessage 用各自的空 instance 覆写共享 execution_id
                // 的 Redis 记录 → 只剩末轮事件 → "只显示最后一轮"。
                // 在此补一次归并：仅 eventNum==1（每流一次），getCache 命中（resume 有旧 instance）才 copy。
                // 新会话 getCache 返回 null → 不做，行为完全不变。
                if (eventNum == 1) {
                    // try/catch：getCache/copy/终态reset 若抛异常（Redis 故障等），不应阻断
                    // node_wait 的 passThrough（否则前端丢失 node_wait 事件）。log 后继续透传。
                    try {
                        // 对齐 processStart：优先从事件 JSON 取 executionId（子工作流场景事件
                        // 携带子工作流 executionId，executeParams 是顶层，直接用会取错 key），
                        // 空则回退 executeParams。
                        String eventExecId = null;
                        try {
                            JiuwenEvent eventObj = JSONObject.parseObject(eventStr, JiuwenEvent.class);
                            eventExecId = eventObj.getExecutionId();
                        } catch (Exception parseEx) {
                            // eventStr 非标准 JiuwenEvent JSON（node_wait 可能无 executionId 字段）
                        }
                        if (StringUtils.isEmpty(eventExecId)) {
                            eventExecId = executeParams.getExecutionId();
                        }
                        if (StringUtils.isEmpty(eventExecId)) {
                            // 第三层兜底（对齐 processStart）：MDC REQUEST_ID
                            eventExecId = MDC.get(REQUEST_ID);
                        }
                        WorkflowInstanceEntity cached = instanceService.getCache(
                            eventExecId, executeParams.getReleasedVersion(), executeParams.getUserId());
                        if (cached != null) {
                            instanceService.copy(cached, instance);
                            // 对齐 processStart：cached 若为终态（SUCCEEDED/FAILED/ABORTED）清 eventList
                            // + 重置 startTime，否则 resume 会继续累积在陈旧的已完成事件上、显示错乱；
                            // 最后打回 RUNNING（resume 在跑）。
                            String cachedStatus = cached.getStatus();
                            if (WorkflowRunStatus.SUCCEEDED.getStatus().getDesc().equalsIgnoreCase(cachedStatus)
                                || WorkflowRunStatus.FAILED.getStatus().getDesc().equalsIgnoreCase(cachedStatus)
                                || WorkflowRunStatus.ABORTED.getStatus().getDesc().equalsIgnoreCase(cachedStatus)) {
                                instance.setEventList(new ArrayList<>());
                                instance.setStartTime(System.currentTimeMillis());
                                // 清 endTime：copy 已把旧终态的 endTime 拷入，不清则
                                // 新 startTime + 旧 endTime → endTime 早于 startTime、
                                // 前端耗时/结束时间显示错误
                                instance.setEndTime(null);
                            }
                            instance.setStatus(WorkflowRunStatus.RUNNING.getStatus().getDesc());
                        }
                    } catch (Exception mergeEx) {
                        log.warn("Failed to merge cached instance on node_wait (continuing passThrough): {}",
                            mergeEx.getMessage());
                    }
                }
                // node_wait 节流透传：密集循环节点 node_wait 逐个同步 send 会阻塞 SSE 回调线程。
                // 前端 node_wait 仅用于 updateCallNode 状态更新，不触发交互（交互靠 node_started），
                // 窗口内跳过 send 不影响最终结果；saveResumeExecutionId 已同步落盘，调试历史不受影响。
                if (shouldThrottleNodeWaitPassThrough(executeParams.getExecutionId())) {
                    return JiuwenEventType.NOT_EXIST;
                }
            } else {
                log.warn("not support event:{}, passThrough anyway.", event);
            }
            passThrough(eventStr);
            return JiuwenEventType.NOT_EXIST;
        }

        // EXCEPTION事件直接透传，不需要完整解析
        if (eventType == JiuwenEventType.EXCEPTION) {
            // 处理exception原始事件，重构结构
            String processedStr = eventProcessor.processOriginEvent(eventStr);
            passThrough(processedStr);
            result.setTaskEnd(true);
            return eventType;
        }

        // 非EXCEPTION事件，正常解析
        JiuwenEvent eventObj = JSONObject.parseObject(eventStr, JiuwenEvent.class);
        // DEF-02 §4.4-6：Runtime 事件携带 execution ID 时先校验且与既定值一致；
        // 冲突或非法值不得覆盖权威值，只记录不含原值的安全告警并继续使用 Manager 既定值
        String eventExecId = eventObj.getExecutionId();
        if (StringUtils.isNotEmpty(eventExecId)
            && (!CorrelationIdValidator.isValid(eventExecId)
                || (StringUtils.isNotEmpty(executeParams.getExecutionId())
                    && !eventExecId.equals(executeParams.getExecutionId())))) {
            log.warn("Runtime event executionId conflicts or is invalid; keeping Manager-selected value");
        }
        // DEF-02 §4.4-7：instance ID 统一使用 Manager 选定的 executeParams.executionId，不再 requestId 兜底
        if (StringUtils.isNotEmpty(executeParams.getExecutionId())) {
            result.getInstance().setId(executeParams.getExecutionId());
        }

        eventProcessor.recordEvent(eventObj, eventType, result.getInstance());
        JiuwenEventData eventData = eventObj.getData();

        if (eventNum == 1) {
            log.info("This is first event. event: {}", event);
            processStart(eventObj);
        }

        switch (eventType) {
            case START -> {
                passThrough(eventStr);
            }
            case ERROR -> {
                // COM-04 响应 §5.4: 不透传原始 error 事件——基类已拦截并产出 Manager SSE error
                // guard TERMINATED 后 passThrough 被 allowMessage() 阻止
                result.setTaskEnd(true);
                processError(eventData);
            }
            case WORKFLOW_FINISHED -> {
                // Inject start_time and end_time into the event data for frontend display
                try {
                    com.alibaba.fastjson.JSONObject eventJson = com.alibaba.fastjson.JSONObject.parseObject(eventStr);
                    com.alibaba.fastjson.JSONObject dataJson = eventJson.getJSONObject("data");
                    if (dataJson != null) {
                        WorkflowInstanceEntity inst = result.getInstance();
                        if (inst.getStartTime() > 0) {
                            dataJson.putIfAbsent("start_time", inst.getStartTime());
                        }
                        dataJson.putIfAbsent("end_time", System.currentTimeMillis());
                        eventStr = eventJson.toJSONString();
                    }
                } catch (Exception e) {
                    log.warn("Failed to inject time into workflow_finished event: {}", e.getMessage());
                }
                passThrough(eventStr);
                result.setTaskEnd(true);
                result.setWorkflowEnd(true);
                WorkflowInstanceEntity instanceEntity = result.getInstance();
                if (StringUtils.isEmpty(instanceEntity.getStatus()) || !WorkflowRunStatus.FAILED.getStatus()
                    .getDesc().equalsIgnoreCase(instanceEntity.getStatus())) {
                    instanceEntity.setStatus(WorkflowRunStatus.SUCCEEDED.getStatus().getDesc());
                }
                instanceEntity.setEndTime(System.currentTimeMillis());
                // Delete resume executionId from Redis to prevent reuse by next execution in same conversation
                try {
                    agentRuntimeService.deleteResumeExecutionId(
                        executeParams.getWorkflowId(), executeParams.getConversationId());
                } catch (Exception e) {
                    log.warn("Failed to delete resume executionId on workflow finish: {}", e.getMessage());
                }
            }
            case WORKFLOW_NODE_MESSAGE -> {
                processWorkflowNodeMessage(eventData);
                // debug模式实时旁路存储insight事件：异步执行，避免 Redis 写入阻塞事件透传
                if (executeParams.isDebug()) {
                    instanceService.saveInsightMessageAsync(result.getInstance(), executeParams.getReleasedVersion(),
                        executeParams.getUserId(),
                        executeParams.getAsyncTaskParamHolder() != null
                            && executeParams.getAsyncTaskParamHolder().isAsync());
                }
            }
            case MESSAGE, SENSITIVE -> {
                passThrough(eventStr);
            }
            case DONE -> {
                passThrough(eventStr);
            }
            default -> passThrough(eventStr);
        }
        return eventType;
    }

    /**
     * 处理workflow node message事件
     */
    private void processWorkflowNodeMessage(JiuwenEventData eventData) {
        NodeRunInfo nodeRunInfo = JiuwenEventProcessor.convertNodeRunInfo(eventData);
        if (executeParams.isDebug()) {
            result.getNodeRunInfoList().add(nodeRunInfo);
        }
    }

    /**
     * 处理error事件
     */
    private void processError(JiuwenEventData eventData) {
        WorkflowInstanceEntity instance = result.getInstance();
        instance.setStatus(WorkflowRunStatus.FAILED.getStatus().getDesc());
        // COM-04 响应 §5.5.3: 实例诊断只用 Manager 稳定错误码，不保存下游 message
        if (lastErrorDescriptor != null) {
            instance.setErrorInfo(lastErrorDescriptor.getErrorCode());
        }
    }

    /**
     * 处理start事件
     */
    private void processStart(JiuwenEvent eventObj) {
        WorkflowInstanceEntity instance = result.getInstance();
        // DEF-02 §4.4-7：统一使用 Manager 选定的 executeParams.executionId，不再 requestId 兜底
        String eventExecId = executeParams.getExecutionId();
        if (StringUtils.isEmpty(eventExecId)) {
            log.warn("start event has no authoritative executionId; skip instance id assignment");
            return;
        }
        instance.setId(eventExecId);
        WorkflowInstanceEntity instanceEntity = instanceService.getCache(eventExecId, executeParams.getReleasedVersion(),
            executeParams.getUserId());
        log.info("Process start existInstance:{} nodeExecute:{}, instId:{}, version:{}",
            instanceEntity != null, executeParams.isNodeExecute(), eventExecId, executeParams.getReleasedVersion());
        if (instanceEntity == null && !executeParams.isNodeExecute()) {
            // 非单节点调测模式触发保存
            instanceService.save(instance, executeParams);
        } else if (instanceEntity != null) {
            instanceService.copy(instanceEntity, instance);
            // If cached instance is in terminal state, clear its event list and reset for new execution
            String cachedStatus = instanceEntity.getStatus();
            if (WorkflowRunStatus.SUCCEEDED.getStatus().getDesc().equalsIgnoreCase(cachedStatus)
                || WorkflowRunStatus.FAILED.getStatus().getDesc().equalsIgnoreCase(cachedStatus)
                || WorkflowRunStatus.ABORTED.getStatus().getDesc().equalsIgnoreCase(cachedStatus)) {
                instance.setEventList(new ArrayList<>());
                instance.setStartTime(System.currentTimeMillis());
                // 清 endTime：copy 已把旧终态的 endTime 拷入，不清则新 startTime + 旧 endTime
                // → endTime 早于 startTime、前端耗时/结束时间显示错误
                instance.setEndTime(null);
            }
            instance.setStatus(WorkflowRunStatus.RUNNING.getStatus().getDesc());
        }
        result.setInstance(instance);
    }

    /**
     * 中断时保存 resume executionId，确保恢复时 queryResumeExecutionId 能取到同一 execution_id。
     * DEF-02 §4.4-5：保存值直接取自 executeParams.executionId，不再从回调线程 MDC task-id 读取。
     */
    private void saveResumeExecutionIdOnInterrupt() {
        try {
            String executionId = executeParams.getExecutionId();
            if (StringUtils.isNotEmpty(executionId) && !executionId.equals(lastSavedResumeExecutionId)) {
                agentRuntimeService.saveResumeExecutionId(
                    executeParams.getWorkflowId(), executeParams.getConversationId(), executionId);
                lastSavedResumeExecutionId = executionId;
                log.info("Saved resume executionId on node_wait: workflowId={}, conversationId={}",
                    executeParams.getWorkflowId(), executeParams.getConversationId());
            }
        } catch (Exception e) {
            log.warn("Failed to save resume executionId on interrupt: {}", e.getMessage());
        }
    }

    /**
     * 判断 node_wait 是否应节流（跳过 passThrough）。
     * 按 executionId 维度，距上次透传不足 NODE_WAIT_PASSTHROUGH_THROTTLE_MS 则节流。
     * OkHttp SSE 回调单线程串行处理同 executionId 事件，无并发，AtomicLong 足够。
     */
    private boolean shouldThrottleNodeWaitPassThrough(String execId) {
        if (execId == null || execId.isEmpty()) {
            return false;
        }
        AtomicLong last = nodeWaitLastPassThrough.computeIfAbsent(execId, k -> new AtomicLong(0));
        long now = System.currentTimeMillis();
        long lastTime = last.get();
        if (now - lastTime < NODE_WAIT_PASSTHROUGH_THROTTLE_MS) {
            return true;
        }
        last.set(now);
        return false;
    }

    private void doClose(String eventType) {
        closed(eventType);
    }

    private void closed(String eventType) {
        try {
            log.info("closed. eventType:{}", eventType);
            saveInstance();
        } catch (Throwable e) {
            log.error("on closed failed.", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        } finally {
            // 清理 node_wait 节流状态，防内存泄漏
            String execId = executeParams.getExecutionId();
            if (execId != null) {
                nodeWaitLastPassThrough.remove(execId);
            }
            sseEmitter.complete();
        }
    }

    protected void saveInstance() {
        WorkflowInstanceEntity instance = result.getInstance();
        if (instance == null) {
            return;
        }
        // DEF-02 §4.4-7：不再用 MDC.get(REQUEST_ID) 兜底 instance ID；权威值缺失视为编程错误，不造假保存
        if (StringUtils.isEmpty(instance.getId()) && StringUtils.isNotEmpty(executeParams.getExecutionId())) {
            instance.setId(executeParams.getExecutionId());
        }
        if (result.isWorkflowEnd()) {
            if (StringUtils.isEmpty(instance.getStatus()) || WorkflowRunStatus.RUNNING.getStatus()
                .getDesc().equalsIgnoreCase(instance.getStatus())) {
                instance.setStatus(WorkflowRunStatus.SUCCEEDED.getStatus().getDesc());
            }
        }
        if (instance.getEndTime() == null) {
            instance.setEndTime(System.currentTimeMillis());
        }
        // 终态保存：分 key 模式下 saveTerminal 会先写 meta，再全量落盘 events List
        instanceService.saveTerminal(instance, executeParams);
    }

    /**
     * 从JSON字符串中提取event字段
     */
    private String extractEventFromJson(String jsonStr) {
        try {
            JSONObject jsonObject = JSONObject.parseObject(jsonStr);
            return jsonObject.getString("event");
        } catch (Exception e) {
            log.warn("Failed to extract event from json: {}", e.getMessage());
            return "unknown";
        }
    }
}
