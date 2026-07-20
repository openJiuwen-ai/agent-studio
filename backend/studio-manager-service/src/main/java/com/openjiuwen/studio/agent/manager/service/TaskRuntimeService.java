/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.fasterxml.jackson.core.type.TypeReference;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.run.TaskStatus;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.ConversationParams;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunReq;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunRsp;
import com.openjiuwen.studio.agent.manager.entity.TaskEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.enums.MessageRole;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.model.AsyncTaskParamHolder;
import com.openjiuwen.studio.agent.manager.model.Conversation;
import com.openjiuwen.studio.agent.manager.mapper.AsyncTaskMapper;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService;
import com.openjiuwen.studio.agent.manager.service.proxy.AsyncWorkflowListener;

import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * 任务运行时Service
 */
@Slf4j
@Service
public class TaskRuntimeService {
    /**
     * redis存header key
     */
    private static final String REDIS_HEADER_KEY = "agent:runtime:async:header:%s";

    /**
     * redis存header key
     */
    private static final String KEEP_ALIVE = "Keep-Alive";

    /**
     * redis存header key
     */
    private static final String TIMEOUT_VALUE = "timeout=%s";

    /**
     * 默认超时时间，单位毫秒
     */
    private static final int DEFAULT_TIMEOUT_MILLISECONDS = 3600000;

    /**
     * 分布式锁等待时间
     */
    private static final int LOCK_TIME = 10;

    /**
     * 最大错误描述长度
     */
    private static final int MAX_ERROR_MESSAGE_SIZE = 2048;

    /**
     * 任务id和线程池映射
     */
    private final ConcurrentMap<String, CompletableFuture<?>> taskFutures = new ConcurrentHashMap<>();

    /**
     * 任务id和okhttp连接映射
     */
    private final ConcurrentMap<String, AsyncTaskParamHolder> taskEventSource = new ConcurrentHashMap<>();

    @Value("${task.async.pool-size:100}")
    private int taskAsyncPoolSize;

    @Value("${task.async.execute-lock-key}")
    private String executeLock;

    @Value("${task.async.clear-lock-key}")
    private String clearLock;

    @Autowired
    private I18nUtil i18nUtil;

    @Value("${env.type}")
    private String envType;

    /**
     * 异步任务超期时间，建议调试记录超期时间保持一致
     */
    @Value("${task.async.expire-days:}")
    private int taskAsyncExpireDays;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private AsyncTaskMapper asyncTaskMapper;

    @Autowired
    private WorkflowRuntimeService workflowRuntimeService;

    @Autowired
    private ConversationHistoryService conversationHistoryService;

    @Autowired
    private AgentServiceProxyService agentServiceProxyService;

    @Value("${agent_runtime_endpoint:}")
    private String runtimeEndpoint;

    /**
     * 线程池
     */
    private ExecutorService executor;

    @PostConstruct
    private void init() {
        executor = Executors.newFixedThreadPool(taskAsyncPoolSize);
    }

    /**
     * 定期拉起初始状态的任务
     */
    @Scheduled(cron = "${task.async.execute-cron-expression:}")
    @Async
    public void doAsyncTask() {
        RedisLock lock = null;
        boolean isLocked = false;
        try {
            lock = redisClient.getLock(executeLock);

            // 获取redis分布式锁，如果锁不可用，则等待10秒，如果还是无法获取，则抛出异常
            isLocked = lock.tryLock(Duration.ofSeconds(LOCK_TIME));
            if (isLocked) {
                findAndAsyncExecuteWorkflow();
            } else {
                log.warn("failed to get execute lock");
            }
        } catch (Exception e) {
            log.error("async task execute failed!", e);
        } finally {
            if (lock != null && isLocked) {
                try {
                    lock.unlock();
                } catch (Exception e) {
                    log.warn("Failed to release lock", e);
                }
            }
        }
    }

    /**
     * 定期拉起清理超期的任务
     */
    @Scheduled(cron = "${task.async.clear-cron-expression:}")
    @Async
    public void clearExpiredMission() {
        RedisLock lock = null;
        boolean isLocked = false;
        try {
            lock = redisClient.getLock(clearLock);

            // 获取redis分布式锁，如果锁不可用，则等待10秒，如果还是无法获取，则抛出异常
            isLocked = lock.tryLock(Duration.ofSeconds(LOCK_TIME));
            if (isLocked) {
                long expireMillis = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(taskAsyncExpireDays);

                // 获取超期任务
                List<TaskEntity> expireTasks = asyncTaskMapper.getExpiredTaskEntity(new Date(expireMillis));
                List<String> expireIds = expireTasks.stream().map(TaskEntity::getId).toList();

                // 如当前任务仍在执行，需取消任务
                expireIds.forEach(this::cancelTask);
                asyncTaskMapper.deleteByIds(expireIds);
            } else {
                log.warn("failed to get clear lock");
            }
        } catch (Exception e) {
            log.error("async task clear failed!", e);
        } finally {
            if (lock != null && isLocked) {
                try {
                    lock.unlock();
                } catch (Exception e) {
                    log.warn("Failed to release lock", e);
                }
            }
        }
    }

    /**
     * 找到并异步执行工作流
     */
    public void findAndAsyncExecuteWorkflow() {
        // 获取当前空闲的线程池数
        int idlePoolNum = taskAsyncPoolSize - taskFutures.size();

        // 当前无空闲线程，拉起任务失败
        if (idlePoolNum == 0) {
            log.info("Current connection pool is full!");
            return;
        }
        // 按当前空闲线程个数拉起服务
        List<TaskEntity> taskEntities = asyncTaskMapper.getInitWorkflowTaskEntity(idlePoolNum);
        if (CollectionUtils.isEmpty(taskEntities)) {
            log.debug("Current async workflow task is empty!");
            return;
        }
        taskEntities.forEach(taskEntity -> {
            try {
                submitAsyncTask(taskEntity.getId(), () -> executeWorkflow(taskEntity));
            } catch (Exception e) {
                log.error("Run workflow failed.", e);
                throw new AgentStudioException(StudioError.WORKFLOW_ASYNC_EXECUTE_FAILED);
            }
            log.info("runWorkflowStream end.");
        });
    }

    private ExecuteParams buildExecuteParams(TaskEntity entity) {
        // 从redis读取用户header，并新增透传超时header
        String headerStr = redisClient.get(String.format(REDIS_HEADER_KEY, entity.getId()));
        HttpHeaders httpHeaders = new HttpHeaders();
        Integer timeout = entity.getTimeout() != null ? entity.getTimeout() : DEFAULT_TIMEOUT_MILLISECONDS;
        if (!StringUtils.isEmpty(headerStr)) {
            Map<String, String> headers = JsonUtils.json2Obj(headerStr, new TypeReference<>() { });
            if (headers != null) {
                headers.put(KEEP_ALIVE, String.format(TIMEOUT_VALUE, timeout));
                headers.forEach(httpHeaders::add);
            }
        } else {
            httpHeaders.add(KEEP_ALIVE, String.format(TIMEOUT_VALUE, timeout));
        }
        // 异步任务以debug模式运行，确保runtime发送WORKFLOW_NODE_MESSAGE事件（包含节点执行详情）
        httpHeaders.set("X-Invoke-Mode", "debug");
        // 根据是否发布决定appVersion是发布态或编辑态时间
        Long version = null;
        String releaseVersion = null;
        if (Boolean.TRUE.equals(entity.getIsPublished())) {
            releaseVersion = entity.getAppVersion();
        } else {
            version = StringUtils.isEmpty(entity.getAppVersion()) ? null : Long.valueOf(entity.getAppVersion());
        }
        return ExecuteParams.builder()
                .domainId(entity.getDomainId())
                .projectId(entity.getProjectId())
                .workspaceId(StringUtils.isNotEmpty(entity.getWorkspaceId()) ? entity.getWorkspaceId() : StringUtils.EMPTY)
                .workflowId(entity.getAppId())
                .debug(true)
                .traceMode(Constant.Agent.DEBUG)
                .trace(true)
                .isTreasure(false)
                .inputs(JsonUtils.json2Obj(entity.getInputs(), new TypeReference<>() { }))
                .stream(false)
                .isNodeExecute(false)
                .startTime(System.currentTimeMillis())
                .conversationId(entity.getConversationId())
                .version(version)
                .releasedVersion(releaseVersion)
                .userId(entity.getUserId())
                .inputsUserId(entity.getUserId())
                .httpHeaders(httpHeaders)
                .asyncTaskParamHolder(new AsyncTaskParamHolder(true, timeout))
                .build();
    }

    private TaskStatus convertWorkflowRunStatus(Status status) {
        // 九问事件转换成原始事件
        switch (status.getDesc()) {
            case "running" -> {
                return TaskStatus.RUNNING;
            }
            case "succeeded" -> {
                return TaskStatus.COMPLETED;
            }
            case "waiting" -> {
                return TaskStatus.PENDING;
            }
            default -> {
                return TaskStatus.FAILED;
            }
        }
    }

    private void executeWorkflow(TaskEntity taskEntity) {
        // 工作流开始运行
        ExecuteParams executeParams = buildExecuteParams(taskEntity);
        try {
            if ("simple".equals(envType)) {
                String authToken = taskEntity.getUserId() + "|" + taskEntity.getProjectId();
                RequestContextUtils.setRequestAuthTokenAndUserId(authToken, taskEntity.getProjectId(),
                        taskEntity.getUserId());
            } else {
                String authToken = "";
                RequestContextUtils.setRequestAuthTokenAndUserId(authToken, taskEntity.getProjectId(),
                        taskEntity.getUserId());
            }
        } catch (Exception e) {
            log.error("Call get-agency-token api exception.", e);
            taskEntity.setStartTime(new Date(System.currentTimeMillis()));
            taskEntity.setStatus(TaskStatus.FAILED.getValue());
            taskEntity.setMessage(i18nUtil.getMessage(StudioError.ASYNC_TASK_ACCOUNT_FAILED));
            asyncTaskMapper.updateByPrimaryKey(taskEntity);
            return;
        }

        // 更新状态为执行中
        Date startTime = new Date(System.currentTimeMillis());
        taskEntity.setStartTime(startTime);
        taskEntity.setUpdateTime(startTime);
        taskEntity.setStatus(TaskStatus.RUNNING.getValue());
        asyncTaskMapper.updateByPrimaryKey(taskEntity);

        // 透传参数绑定连接池，便于取消任务时手动释放连接池
        taskEventSource.put(taskEntity.getId(), executeParams.getAsyncTaskParamHolder());

        WorkflowRunResult result = null;
        AsyncWorkflowListener listener = null;
        try {
            // 通过流式通道调用runtime，AsyncWorkflowListener在manager侧保存调试记录并捕获消息内容
            listener = createAsyncListener(executeParams);
            result = callWorkflowViaStream(executeParams, listener);

            // 轮询等待工作流执行完成
            waitForWorkflowCompletion(result, executeParams);

            // 从流式结果构建WorkflowRunRsp
            WorkflowRunRsp workflowRunRsp = buildWorkflowRunRspFromResult(result, executeParams);

            // 工作流运行结束或失败更新状态
            Date finishTime = new Date(System.currentTimeMillis());
            taskEntity.setUpdateTime(finishTime);
            taskEntity.setFinishTime(finishTime);
            if (workflowRunRsp.getStatus() != null) {
                TaskStatus taskStatus = convertWorkflowRunStatus(workflowRunRsp.getStatus());
                taskEntity.setStatus(taskStatus.getValue());

                if (TaskStatus.FAILED.equals(taskStatus)) {
                    taskEntity.setMessage(workflowRunRsp.getErrorMessage());
                } else {
                    taskEntity.setOutputs(JsonUtils.toJson(workflowRunRsp));
                    taskEntity.setMessage(StringUtils.EMPTY);
                }
            } else {
                // 说明latch已超时，工作流未返回，直接返回超时信息
                taskEntity.setStatus(TaskStatus.FAILED.getValue());
                taskEntity.setMessage(i18nUtil.getMessage(StudioError.ASYNC_TASK_EXECUTE_TIMEOUT));
            }
        } catch (AgentStudioException e) {
            log.error("Execute workflow failed", e);
            taskEntity.setStatus(TaskStatus.FAILED.getValue());
            taskEntity.setMessage(StrUtils.truncateText(i18nUtil.getMessage(StudioError.ASYNC_TASK_EXECUTE_FAILED,
                    i18nUtil.getMessage(e.getErrorCode(), e.getArgs())), MAX_ERROR_MESSAGE_SIZE));
        } catch (Exception e) {
            log.error("Execute workflow failed", e);
            taskEntity.setStatus(TaskStatus.FAILED.getValue());
            taskEntity.setMessage(
                    StrUtils.truncateText(i18nUtil.getMessage(StudioError.ASYNC_TASK_EXECUTE_FAILED, e.getMessage()),
                            MAX_ERROR_MESSAGE_SIZE));
        }
        // 如不是用户取消导致的失败，刷新状态
        if (taskFutures.get(taskEntity.getId()) != null) {
            asyncTaskMapper.updateByPrimaryKey(taskEntity);
        }
        // 任务执行结果记录到会话历史
        saveConversationHistory(taskEntity, result, listener);
    }

    /**
     * 将工作流执行结果写入会话历史。
     * 成功时：优先从nodeRunInfoList中提取END节点输出，fallback到AsyncWorkflowListener捕获的message事件内容。
     * 失败时：将错误信息作为assistant消息。
     */
    private void saveConversationHistory(TaskEntity taskEntity, WorkflowRunResult result,
        AsyncWorkflowListener listener) {
        ConversationParams conversationParams = new ConversationParams()
                .setExecuteType(Constant.AppType.WORKFLOW)
                .setId(taskEntity.getAppId())
                .setConversationId(taskEntity.getConversationId());

        Message message = new Message();
        message.setRole(MessageRole.ASSISTANT.name().toLowerCase(Locale.ROOT));
        message.setCreateTime(taskEntity.getUpdateTime() != null ? taskEntity.getUpdateTime().getTime()
                : System.currentTimeMillis());

        if (TaskStatus.COMPLETED.getValue().equals(taskEntity.getStatus()) && result != null) {
            // 成功：优先从nodeRunInfoList提取，fallback到listener捕获的message事件内容
            String content = extractWorkflowOutput(result, listener);
            if (StringUtils.isNotEmpty(content)) {
                message.setContent(content);
                conversationHistoryService.updateConversation(conversationParams, List.of(message), true);
            }
        } else if (TaskStatus.FAILED.getValue().equals(taskEntity.getStatus())) {
            // 失败：记录错误信息
            if (StringUtils.isNotEmpty(taskEntity.getMessage())) {
                message.setContent(taskEntity.getMessage());
                conversationHistoryService.updateConversation(conversationParams, List.of(message), false);
            }
        }
    }

    /**
     * 提取工作流最终输出内容。
     * 优先从nodeRunInfoList中查找END节点的responseContent输出，
     * 若nodeRunInfoList为空（manager侧WorkflowListener不保证填充node info），
     * 则fallback到AsyncWorkflowListener从message事件中捕获的文本。
     */
    @SuppressWarnings("unchecked")
    private String extractWorkflowOutput(WorkflowRunResult result, AsyncWorkflowListener listener) {
        // 优先：从nodeRunInfoList中提取END节点输出
        if (result.getNodeRunInfoList() != null && !result.getNodeRunInfoList().isEmpty()) {
            for (int i = result.getNodeRunInfoList().size() - 1; i >= 0; i--) {
                com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo node = result.getNodeRunInfoList().get(i);
                if (node.getOutputs() != null && node.getOutputs() instanceof Map) {
                    Map<String, Object> outputs = (Map<String, Object>) node.getOutputs();
                    Object responseContent = outputs.get("responseContent");
                    if (responseContent != null) {
                        return responseContent.toString();
                    }
                }
            }
        }
        // fallback：从AsyncWorkflowListener捕获的message事件内容中获取
        if (listener != null && listener.getMessageContent().length() > 0) {
            return listener.getMessageContent().toString();
        }
        return null;
    }

    /**
     * 创建异步任务专用的WorkflowListener。
     * 在callWorkflowViaStream之前创建，以便后续saveConversationHistory时引用其捕获的消息内容。
     */
    private AsyncWorkflowListener createAsyncListener(ExecuteParams executeParams) {
        WorkflowRunResult result = initWorkflowRunResult(executeParams);
        // requestId在异步线程中可能为null，WorkflowListener.processStart()会fallback到executionId
        String requestId = org.slf4j.MDC.get("request-id");
        return new AsyncWorkflowListener(requestId, executeParams, result, executeParams.getHttpHeaders());
    }

    /**
     * 通过流式通道调用runtime工作流。
     * 复用AgentServiceProxyService的stream()方法 + AsyncWorkflowListener，
     * AsyncWorkflowListener负责解析SSE事件并保存调试记录（insight）到Redis。
     *
     * @param executeParams 执行参数
     * @param listener      异步任务监听器（已持有WorkflowRunResult）
     * @return WorkflowRunResult 流式执行结果
     */
    private WorkflowRunResult callWorkflowViaStream(ExecuteParams executeParams, AsyncWorkflowListener listener) {
        // 1. 构建runtime工作流URL
        String url = buildRuntimeWorkflowUrl(executeParams);

        // 2. 构建WorkflowRunReq请求体
        WorkflowRunReq reqBody = buildWorkflowRunReq(executeParams);

        // 3. 设置executionId
        String taskId = executeParams.getAsyncTaskParamHolder() != null
                ? java.util.UUID.randomUUID().toString() : null;
        if (taskId != null) {
            executeParams.setExecutionId(taskId);
        }
        org.slf4j.MDC.put(Constant.TASK_ID, executeParams.getExecutionId());
        executeParams.getHttpHeaders().set("X-Execution-Id", executeParams.getExecutionId());

        // 4. 调用stream()发起SSE请求，AsyncWorkflowListener自动处理事件并保存调试记录
        agentServiceProxyService.stream(url, executeParams.getHttpHeaders(),
                JsonUtils.toJson(reqBody), 900000L, listener);

        return listener.getResult();
    }

    /**
     * 构建runtime工作流URL
     */
    private String buildRuntimeWorkflowUrl(ExecuteParams executeParams) {
        String url = "%s/v1/%s/workflows/%s/conversations/%s?workspace_id=%s";
        url = String.format(Locale.ROOT, url, runtimeEndpoint,
                executeParams.getProjectId(), executeParams.getWorkflowId(),
                executeParams.getConversationId(), executeParams.getWorkspaceId());
        if (StringUtils.isNotEmpty(executeParams.getEnvironmentId())) {
            url += "&environment_id=" + executeParams.getEnvironmentId();
        }
        // 发布态传releaseVersion，编辑态不传version
        if (StringUtils.isNotEmpty(executeParams.getReleasedVersion())) {
            url += "&version=" + executeParams.getReleasedVersion();
        }
        return url;
    }

    /**
     * 构建WorkflowRunReq请求体
     */
    private WorkflowRunReq buildWorkflowRunReq(ExecuteParams executeParams) {
        WorkflowRunReq reqBody = new WorkflowRunReq();
        reqBody.setInputs(executeParams.getInputs());
        return reqBody;
    }

    /**
     * 初始化WorkflowRunResult和WorkflowInstanceEntity
     * 复用AgentServiceProxyController中的初始化模式
     */
    private WorkflowRunResult initWorkflowRunResult(ExecuteParams executeParams) {
        WorkflowRunResult result = new WorkflowRunResult();
        WorkflowInstanceEntity instance = new WorkflowInstanceEntity();
        instance.setConversationId(executeParams.getConversationId());
        instance.setWorkflowId(executeParams.getWorkflowId());
        instance.setInputs(executeParams.getInputs());
        instance.setStatus(WorkflowRunStatus.RUNNING.getStatus().getDesc());
        instance.setStartTime(executeParams.getStartTime());
        instance.setEventList(new ArrayList<>());
        instance.setUserId(executeParams.getUserId());
        instance.setProjectId(executeParams.getProjectId());
        result.setInstance(instance);
        return result;
    }

    /**
     * 轮询等待工作流执行完成。
     * WorkflowListener在处理WORKFLOW_FINISHED或ERROR事件时设置taskEnd=true。
     */
    private void waitForWorkflowCompletion(WorkflowRunResult result, ExecuteParams executeParams) {
        int timeout = (executeParams.getAsyncTaskParamHolder() != null)
                ? executeParams.getAsyncTaskParamHolder().getTimeout()
                : DEFAULT_TIMEOUT_MILLISECONDS;
        long deadline = System.currentTimeMillis() + timeout;

        while (!result.isTaskEnd()) {
            if (System.currentTimeMillis() > deadline) {
                log.warn("Async workflow polling timeout reached for conversationId: {}",
                        executeParams.getConversationId());
                return;
            }
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new AgentStudioException(StudioError.WORKFLOW_ASYNC_EXECUTE_FAILED);
            }
        }
    }

    /**
     * 从WorkflowRunResult构建WorkflowRunRsp。
     * 将流式执行结果转换为与原runWorkflow返回值一致的结构。
     */
    private WorkflowRunRsp buildWorkflowRunRspFromResult(WorkflowRunResult result, ExecuteParams executeParams) {
        WorkflowInstanceEntity instance = result.getInstance();

        // 从instance状态构建Status
        Status status = null;
        if (instance != null && StringUtils.isNotEmpty(instance.getStatus())) {
            status = WorkflowRunStatus.SUCCEEDED.getStatus().getDesc().equals(instance.getStatus())
                    ? WorkflowRunStatus.SUCCEEDED.getStatus()
                    : WorkflowRunStatus.FAILED.getStatus().getDesc().equals(instance.getStatus())
                    ? WorkflowRunStatus.FAILED.getStatus()
                    : WorkflowRunStatus.RUNNING.getStatus().getDesc().equals(instance.getStatus())
                    ? WorkflowRunStatus.RUNNING.getStatus()
                    : WorkflowRunStatus.FAILED.getStatus();
        }

        // 从WorkflowListener收集的结果构建WorkflowRunRsp
        WorkflowRunRsp rsp = new WorkflowRunRsp();
        rsp.setNodeInfo(result.getNodeRunInfoList() != null ? result.getNodeRunInfoList() : new ArrayList<>());
        rsp.setStartTime(executeParams.getStartTime());
        rsp.setEndTime(instance != null ? instance.getEndTime() : System.currentTimeMillis());
        rsp.setStatus(status);
        rsp.setErrorMessage(instance != null ? instance.getErrorInfo() : null);

        return rsp;
    }

    /**
     * 提交异步任务
     *
     * @param taskId 任务id
     * @param task 任务
     */
    public void submitAsyncTask(String taskId, Runnable task) {
        CompletableFuture<Void> future = CompletableFuture.runAsync(task, executor);
        taskFutures.put(taskId, future);

        // 任务结束释放
        future.whenComplete((result, exception) -> {
            if (taskFutures.get(taskId) != null) {
                taskFutures.remove(taskId);
            }
            if (taskEventSource.get(taskId) != null) {
                taskEventSource.remove(taskId);
            }
        });
    }

    /**
     * 取消任务
     *
     * @param taskId 任务id
     */
    public void cancelTask(String taskId) {
        AsyncTaskParamHolder asyncTaskParamHolder = taskEventSource.get(taskId);

        // 释放线程池
        if (asyncTaskParamHolder != null) {
            if (asyncTaskParamHolder.getEventSource() != null) {
                asyncTaskParamHolder.getEventSource().cancel();
            }
            taskEventSource.remove(taskId);
        }
        // 释放异步连接池
        CompletableFuture<?> future = taskFutures.get(taskId);
        if (future != null) {
            future.cancel(true);
            taskFutures.remove(taskId);
        }
    }

    /**
     * 释放资源
     */
    public void shutdown() {
        executor.shutdown();
    }
}
