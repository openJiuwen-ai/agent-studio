/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;
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

/**
 * 工作流（Workflow）SSE事件监听器
 * 基于 OkHttp SSE（Server-Sent Events）机制，实时监听工作流执行过程中由九问（Jiuwen）引擎推送的各类事件流，
 * 完成事件解析、状态维护、前端透传和持久化存储等核心职责。
 *
 */
@Slf4j
public class WorkflowListener extends BaseEventListener {
    private final WorkflowInstanceService instanceService;

    private final JiuwenEventProcessor eventProcessor;

    private final AgentRuntimeService agentRuntimeService;

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
        this.executeParams = executeParams;
        this.result = result;
        eventNum = 0;
    }

    @Override
    public void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
        @NotNull String data) {
        ++eventNum;
        process(data);
    }

    @Override
    public void onFailure(@NotNull EventSource eventSource, @Nullable Throwable t, @Nullable Response response) {
        MDC.put(REQUEST_ID, requestId);
        try {
            executeParams.setSuccess(-1);
            log.error("Workflow process failed. Throwable: {}, Response: {}", t, response);
            if (executeParams.isCanceled()) {
                closed("canceled.");
            } else {
                log.error("Workflow process failed.");
            }
            this.errorRsp = createErrorRsp(t, response);
            this.openConnect = true;
        } catch (Exception e) {
            log.error("Fail handler response. {}", e.getMessage());
            this.openConnect = true;
        } finally {
            try {
                sseEmitter.complete();
            } catch (Throwable e) {
                log.warn("Fail close sse. {}", e.getMessage());
            }
        }
    }

    @Override
    public void onClosed(@NotNull EventSource eventSource) {
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
                saveTaskIdOnInterrupt();
            }
            log.warn("not support event:{}, passThrough anyway.", event);
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
        String eventExecId = eventObj.getExecutionId();
        if (StringUtils.isEmpty(eventExecId)) {
            eventExecId = executeParams.getExecutionId();
        }
        executeParams.setExecutionId(eventExecId);
        String instId = StringUtils.isEmpty(eventExecId) ? requestId : eventExecId;
        result.getInstance().setId(instId);

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
                passThrough(eventStr);
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
                // Delete taskId from Redis to prevent reuse by next execution in same conversation
                try {
                    agentRuntimeService.deleteTaskId(
                        executeParams.getWorkflowId(), executeParams.getConversationId());
                } catch (Exception e) {
                    log.warn("Failed to delete taskId on workflow finish: {}", e.getMessage());
                }
            }
            case WORKFLOW_NODE_MESSAGE -> {
                processWorkflowNodeMessage(eventData);
                // debug模式异步实时存储insight事件
                if (executeParams.isDebug()) {
                    instanceService.saveInsightMessage(result.getInstance(), executeParams.getReleasedVersion(),
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
        if (eventData != null && eventData.getMessage() != null) {
            instance.setErrorInfo(eventData.getMessage());
        }
    }

    /**
     * 处理start事件
     */
    private void processStart(JiuwenEvent eventObj) {
        WorkflowInstanceEntity instance = result.getInstance();
        String eventExecId = eventObj.getExecutionId();
        if (StringUtils.isEmpty(eventExecId)) {
            eventExecId = executeParams.getExecutionId();
        }
        if (StringUtils.isEmpty(eventExecId)) {
            log.warn("start event executionId is null, fallback to requestId!");
            eventExecId = MDC.get(REQUEST_ID);
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
            }
            instance.setStatus(WorkflowRunStatus.RUNNING.getStatus().getDesc());
        }
        result.setInstance(instance);
    }

    /**
     * 中断时保存 taskId，确保恢复时 queryTaskId 能取到同一 execution_id
     */
    private void saveTaskIdOnInterrupt() {
        try {
            String taskId = MDC.get(Constant.TASK_ID);
            if (StringUtils.isEmpty(taskId)) {
                taskId = executeParams.getExecutionId();
            }
            if (!StringUtils.isEmpty(taskId)) {
                agentRuntimeService.saveTaskId(executeParams.getWorkflowId(), executeParams.getConversationId(), taskId);
                log.info("Saved taskId on node_wait: workflowId={}, conversationId={}, taskId={}",
                    executeParams.getWorkflowId(), executeParams.getConversationId(), taskId);
            }
        } catch (Exception e) {
            log.warn("Failed to save taskId on interrupt: {}", e.getMessage());
        }
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
            sseEmitter.complete();
        }
    }

    protected void saveInstance() {
        WorkflowInstanceEntity instance = result.getInstance();
        if (instance == null) {
            return;
        }
        if (StringUtils.isEmpty(instance.getId())) {
            instance.setId(MDC.get(REQUEST_ID));
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
        instanceService.save(instance, executeParams);
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
