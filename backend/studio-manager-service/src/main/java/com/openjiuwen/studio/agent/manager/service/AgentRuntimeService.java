/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.alibaba.fastjson.TypeReference;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.AgentInvokeInfo;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.run.AgentExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.run.ExecutionQuery;
import com.openjiuwen.studio.agent.common.dto.run.GetAgentExecutionInfoQo;
import com.openjiuwen.studio.agent.common.dto.run.ListAgentConversationsQo;
import com.openjiuwen.studio.agent.common.dto.run.ListAgentExecutionQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListControllerExecutionsQo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.ConversationParams;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionBriefModel;
import com.openjiuwen.studio.agent.manager.service.debugging.ControllerDebuggingMgmtService;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

/**
 * Agent调测service
 */
@Slf4j
@Service
public class AgentRuntimeService {
    private static final String CHAIN_INVOKE_TYPE = "chain";

    private static final String LLM_INVOKE_TYPE = "llm";

    private static final String PLUGIN_INVOKE_TYPE = "plugin";

    private static final String KNOWLEDGE_INVOKE_TYPE = "knowledge";

    private static final String MCP_INVOKE_TYPE = "mcp";

    private static final String LOCK_STR = "_lock";

    @Value("${agent.insight-conv-rel:insight_conv_%s_%s}")
    private String agentInsightConvRel;

    @Value("${agent.insight-exec-rel:insight_exec_rel_%s_%s_%s}")
    private String agentInsightExecRel;

    @Value("${agent.insight-exec:insight_exec_%s_%s}")
    private String agentInsightExec;

    @Value("${redis.expire_time}")
    private long expireTime;

    @Value("${agent.max-conversation-size:20}")
    private Integer maxConversationSize;

    @Value("${agent.max-execution-size:20}")
    private Integer maxExecutionSize;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private ControllerDebuggingMgmtService controllerDebuggingMgmtService;

    // ============ 查询方法 ============

    /**
     * 查询Agent执行详情
     */
    public AgentExecutionInfo getAgentExecutionInfo(String projectId, String executionId, String agentId,
                                                    GetAgentExecutionInfoQo getAgentExecutionInfoQo) {
        AgentExecutionInfo executionInfo = new AgentExecutionInfo();
        try {
            String userId = RequestContextUtils.getRequestUserId();
            String insightExecKey = String.format(agentInsightExec, userId, executionId);
            if (redisClient.exists(insightExecKey)) {
                String text = redisClient.get(insightExecKey);
                if (StringUtils.isNotEmpty(text)) {
                    executionInfo = JSON.parseObject(text, AgentExecutionInfo.class);
                }
            } else {
                return executionInfo;
            }

            List<AgentInvokeInfo> invokeInfoList = executionInfo.getInvokeList();
            invokeInfoList.stream().sorted(Comparator.comparing(AgentInvokeInfo::getStartTime).reversed()).toList();
            return executionInfo;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    /**
     * 查询Agent会话下的执行列表
     */
    public AgentExecutionQueries listAgentExecutionQueries(String projectId, String agentId, String conversationId,
                                                           ListAgentExecutionQueriesQo listAgentExecutionQueriesQo) {
        try {
            String userId = RequestContextUtils.getRequestUserId();
            String executionQueryKey = String.format(agentInsightExecRel, userId, agentId, conversationId);
            List<ExecutionQuery> executionQueriyList = new ArrayList<>();
            if (redisClient.exists(executionQueryKey)) {
                String text = redisClient.get(executionQueryKey);
                if (StringUtils.isNotEmpty(text)) {
                    executionQueriyList = JSON.parseObject(text, new TypeReference<>() { });
                }
            }

            AgentExecutionQueries executionQueries = new AgentExecutionQueries();
            executionQueries.setCount(executionQueriyList.size());
            executionQueries.setExecutionQueries(executionQueriyList);
            return executionQueries;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    /**
     * 查询Agent会话列表
     */
    public ConversionQueries listAgentConversations(String projectId, String agentId,
                                                    ListAgentConversationsQo listAgentConversationsQo) {
        log.info("list agent conversations projectId is {}, agentId is {}, type is {}",
                projectId, agentId, listAgentConversationsQo.getType());
        try {
            String userId = RequestContextUtils.getRequestUserId();
            String executionQueryKey = String.format(agentInsightConvRel, agentId, userId);
            List<ConversationInfo> conversationInfoList = new ArrayList<>();
            String text = redisClient.get(executionQueryKey);
            if (StringUtils.isNotEmpty(text)) {
                conversationInfoList = JSON.parseObject(text, new TypeReference<>() { });
            }

            if (conversationInfoList.isEmpty()) {
                log.warn("Not found agent execution record. key:{}  value:{}", executionQueryKey, text);
            }

            ConversionQueries conversionQueries = new ConversionQueries();

            // 按照创建日期过滤conversation
            long filterStartTime = listAgentConversationsQo.getStartTime() != null
                    ? listAgentConversationsQo.getStartTime()
                    : Long.MIN_VALUE;
            long filterEndTime = listAgentConversationsQo.getEndTime() != null
                    ? listAgentConversationsQo.getEndTime()
                    : Long.MAX_VALUE;
            conversationInfoList = conversationInfoList.stream()
                    .filter(conversationInfo -> conversationInfo.getStartTime() >= filterStartTime
                            && conversationInfo.getStartTime() <= filterEndTime)
                    .toList();
            conversationInfoList = filterAndUpdateConversationStatus(projectId, agentId, conversationInfoList,
                    listAgentConversationsQo.getType());
            conversionQueries.setCount(conversationInfoList.size());
            conversionQueries.setConversationInfos(
                    CommonUtil.subList(listAgentConversationsQo.getOffset(), listAgentConversationsQo.getLimit(),
                            conversationInfoList));
            return conversionQueries;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    // ============ 保存方法 ============

    /**
     * 保存Agent execution info
     */
    public void saveAgentExecutionInfo(JiuwenAgentEvent eventObj, AgentExecuteParams executeParams) {
        log.info("start saveAgentExecutionInfo: {} invokeType:{}", eventObj.getConversationId(),
                eventObj.getData().getInvokeType());
        RedisLock lock = null;
        String userId = executeParams.getUserId();
        String executionId = eventObj.getExecutionId();
        executeParams.setExecutionId(executionId);
        String insightExecKey = String.format(agentInsightExec, userId, executionId);
        try {
            lock = redisClient.getLock(insightExecKey + "_lock");

            if (lock.tryLock(Duration.ofSeconds(3))) {
                AgentExecutionInfo executionInfo = new AgentExecutionInfo();
                if (redisClient.exists(insightExecKey)) {
                    String text = redisClient.get(insightExecKey);
                    if (StringUtils.isNotEmpty(text)) {
                        executionInfo = JSON.parseObject(text, AgentExecutionInfo.class);
                    }
                }
                convertAgentExecutionInfo(executionInfo, eventObj.getData(), executeParams);

                if (executionInfo.getEndTime() != null) {
                    saveAgentExecutionQueries(executionInfo, executeParams);
                }
                log.info("redisClient saveAgentExecutionInfo set.");
                redisClient.set(insightExecKey, JSON.toJSONString(executionInfo), Duration.ofSeconds(expireTime));
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * 从事件中提取Agent应用对话query记录并保存
     */
    public void saveAgentExecutionQueries(AgentExecutionInfo executionInfo, AgentExecuteParams executeParams) {
        RedisLock lock = null;

        String userId = executeParams.getUserId();
        String executionQueryKey = String.format(agentInsightExecRel, userId, executeParams.getAgentId(),
                executeParams.getConversationId());
        try {
            lock = redisClient.getLock(executionQueryKey + "_lock");

            if (lock.tryLock(Duration.ofSeconds(3))) {
                List<ExecutionQuery> executionQueries = new ArrayList<>();
                if (redisClient.exists(executionQueryKey)) {
                    String text = redisClient.get(executionQueryKey);
                    if (StringUtils.isNotEmpty(text)) {
                        executionQueries = JSON.parseObject(text, new TypeReference<List<ExecutionQuery>>() { });
                    }
                }

                List<String> queryIds = executionQueries.stream()
                        .map(ExecutionQuery::getExecutionId)
                        .distinct()
                        .toList();
                if (!queryIds.contains(executionInfo.getExecutionId())) {
                    ExecutionQuery executionQuery = new ExecutionQuery();
                    executionQuery.setExecutionId(executionInfo.getExecutionId());
                    executionQuery.setQuery(executeParams.getQuery());
                    executionQuery.setStatus(executionInfo.getStatus());
                    executionQuery.setErrorInfo(executionInfo.getErrorInfo());
                    executionQuery.setStartTime(executionInfo.getStartTime());
                    executionQueries.add(executionQuery);
                    log.info("update execution query: executionId={}, query={}, startTime={}",
                            executionQuery.getExecutionId(), executionQuery.getQuery(), executionQuery.getStartTime());
                }

                executionQueries = executionQueries.stream()
                        .sorted(Comparator.comparing(ExecutionQuery::getStartTime).reversed())
                        .toList();

                if (executionQueries.size() > maxExecutionSize) {
                    clearAgentExecutionRecordsAsync(userId,
                            executionQueries.subList(maxExecutionSize, executionQueries.size()));
                }

                executionQueries = CommonUtil.subList(0, maxExecutionSize, executionQueries);

                redisClient.set(executionQueryKey, JSON.toJSONString(executionQueries), Duration.ofSeconds(expireTime));
            } else {
                log.error("failed to get lock, other user is processing same agent query!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * 更新会话信息
     */
    public void updateConversation(ConversationParams conversationParams) {
        Long startTime = System.currentTimeMillis();
        try {
            if (Constant.AppType.AGENT.equals(conversationParams.getExecuteType())
                    || Constant.AppType.CONTROLLER.equals(conversationParams.getExecuteType())) {
                saveAgentConversations(conversationParams.getId(), conversationParams.getConversationId(),
                        conversationParams.getExecuteType(), conversationParams.getUserId());
            } else {
                log.info("AgentType={} not support.", conversationParams.getExecuteType());
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            Long endTime = System.currentTimeMillis();
            log.info("update conversation cost {}ms, conversation id: {}", endTime - startTime,
                    conversationParams.getConversationId());
        }
    }

    private void saveAgentConversations(String agentId, String conversationId, String agentType, String userId) {
        RedisLock lock = null;
        String conversationInfosKey = String.format(agentInsightConvRel, agentId, userId);
        try {
            lock = redisClient.getLock(conversationInfosKey + LOCK_STR);

            if (lock.tryLock(Duration.ofSeconds(3))) {
                List<ConversationInfo> conversationInfoList = new ArrayList<>();
                if (redisClient.exists(conversationInfosKey)) {
                    String text = redisClient.get(conversationInfosKey);
                    if (StringUtils.isNotEmpty(text)) {
                        conversationInfoList = JSON.parseObject(text, new TypeReference<>() { });
                    }
                }

                List<String> conversationIds = conversationInfoList.stream()
                        .map(ConversationInfo::getConversationId)
                        .distinct()
                        .toList();
                if (!conversationIds.contains(conversationId)) {
                    ConversationInfo conversationInfo = new ConversationInfo();
                    conversationInfo.setConversationId(conversationId);
                    conversationInfo.setStartTime(System.currentTimeMillis());
                    conversationInfoList.add(conversationInfo);
                    log.info("update conversation list: conversationId={}, startTime={}",
                            conversationInfo.getConversationId(), conversationInfo.getStartTime());
                }

                conversationInfoList = conversationInfoList.stream()
                        .sorted(Comparator.comparing(ConversationInfo::getStartTime).reversed())
                        .toList();

                if (conversationInfoList.size() > maxConversationSize) {
                    clearAgentConversationRecords(userId, agentId,
                            conversationInfoList.subList(maxConversationSize, conversationInfoList.size()), agentType);
                }

                conversationInfoList = CommonUtil.subList(0, maxConversationSize, conversationInfoList);

                redisClient.set(conversationInfosKey, JSON.toJSONString(conversationInfoList),
                        Duration.ofSeconds(expireTime));
            } else {
                log.error("failed to get lock, other user is processing same workflow!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * event转换为execution info
     */
    public AgentExecutionInfo convertAgentExecutionInfo(AgentExecutionInfo executionInfo,
                                                        JiuwenAgentEventData eventData, AgentExecuteParams executeParams) {
        executionInfo.setConversationId(executeParams.getConversationId());
        executionInfo.setExecutionId(executeParams.getExecutionId());
        executionInfo.setMetaData(eventData.getMetaData());
        executionInfo.setInputs(executeParams.getQuery());
        AgentInvokeInfo invokeInfo = convertAgentInvokeInfo(executionInfo, eventData, executeParams);
        if (executionInfo.getInvokeList() == null) {
            executionInfo.setInvokeList(new ArrayList<>());
        }
        if (invokeInfo != null) {
            executionInfo.getInvokeList().add(invokeInfo);
        }
        return executionInfo;
    }

    /**
     * event转换为invoke info
     */
    public AgentInvokeInfo convertAgentInvokeInfo(AgentExecutionInfo executionInfo, JiuwenAgentEventData eventData,
                                                  AgentExecuteParams executeParams) {
        if (StringUtils.isEmpty(eventData.getEndTime())) {
            return null;
        }
        AgentInvokeInfo agentInvokeInfo = new AgentInvokeInfo();

        long startTime = System.currentTimeMillis();
        if (StringUtils.isNotEmpty(eventData.getStartTime())) {
            LocalDateTime localDateTime = LocalDateTime.parse(eventData.getStartTime());
            startTime = localDateTime.atZone(ZoneOffset.systemDefault()).toInstant().toEpochMilli();
            agentInvokeInfo.setStartTime(startTime);
        }
        long endTime = System.currentTimeMillis();
        if (StringUtils.isNotEmpty(eventData.getEndTime())) {
            LocalDateTime localDateTime = LocalDateTime.parse(eventData.getEndTime());
            endTime = localDateTime.atZone(ZoneOffset.systemDefault()).toInstant().toEpochMilli();
            agentInvokeInfo.setEndTime(endTime);
        }

        String invokeType = eventData.getInvokeType();
        if (CHAIN_INVOKE_TYPE.equals(invokeType)) {
            if (eventData.getEndTime() != null) {
                executionInfo.setOutputs(Optional.ofNullable(eventData.getOutputs())
                        .map(Object::toString)
                        .map(str -> str.replaceAll("(?i)(九问|jiuwen)", "Runtime"))
                        .orElse(""));
                if (StringUtils.isNotBlank(eventData.getError())) {
                    executionInfo.setErrorInfo(eventData.getError().replaceAll("(?i)(九问|jiuwen)", "Runtime"));
                }
                executionInfo.setStatus(executionInfo.getStatus() == null ? "succeeded" : executionInfo.getStatus());
                executionInfo.setStartTime(startTime);
                executionInfo.setEndTime(endTime);
            }
            return null;
        }
        if (PLUGIN_INVOKE_TYPE.equals(invokeType)) {
            JSONObject instanceAttributes = JSON.parseObject(
                    eventData.getMetaData().get("instance_attributes").toString());
            String nodeName = instanceAttributes.getString("plugin_name");
            if (Objects.equals("retrieval", nodeName)) {
                invokeType = KNOWLEDGE_INVOKE_TYPE;
                nodeName = "知识库";
            } else if (Optional.ofNullable(instanceAttributes.getBoolean("is_mcp")).orElse(false)) {
                invokeType = MCP_INVOKE_TYPE;
                nodeName = instanceAttributes.getString("server_name");
            }
            agentInvokeInfo.setNodeName(nodeName);
        }

        if (LLM_INVOKE_TYPE.equals(invokeType)) {
            agentInvokeInfo.setModelDeploymentId(executeParams.getModelDeploymentId());
        }
        agentInvokeInfo.setNodeId(eventData.getInvokeId());
        agentInvokeInfo.setNodeType(invokeType);
        agentInvokeInfo.setInputs(eventData.getInputs());
        agentInvokeInfo.setOutputs(eventData.getOutputs());
        agentInvokeInfo.setMetaData(eventData.getMetaData());

        if (eventData.getError() != null) {
            agentInvokeInfo.setErrorMessage(eventData.getError());
            agentInvokeInfo.setNodeStatus("failed");
            executionInfo.setStatus("failed");
        } else {
            agentInvokeInfo.setNodeStatus("succeeded");
        }
        return agentInvokeInfo;
    }

    /**
     * 保存taskId
     */
    public void saveTaskId(String agentId, String conversationId, String taskId) {
        redisClient.set("task_id:" + agentId + ":" + conversationId, taskId, Duration.ofSeconds(expireTime));
    }

    /**
     * 查询taskId
     */
    public String queryTaskId(String agentId, String conversationId) {
        try {
            return redisClient.get("task_id:" + agentId + ":" + conversationId);
        } catch (Exception e) {
            return "";
        }
    }

    /**
     * Delete taskId from Redis after workflow completes, to prevent reuse by next execution.
     */
    public void deleteTaskId(String agentId, String conversationId) {
        try {
            redisClient.delete("task_id:" + agentId + ":" + conversationId);
        } catch (Exception e) {
            log.warn("Failed to delete taskId: {}", e.getMessage());
        }
    }

    /**
     * 清理Agent执行记录
     */
    public void clearAgentExecutionRecords(String userId, List<ExecutionQuery> needDeleteInfos) {
        if (needDeleteInfos == null || needDeleteInfos.isEmpty()) {
            return;
        }
        for (ExecutionQuery query : needDeleteInfos) {
            String insightExecKey = String.format(agentInsightExec, userId, query.getExecutionId());
            redisClient.delete(insightExecKey);
        }
    }

    private void clearAgentExecutionRecordsAsync(String userId, List<ExecutionQuery> needDeleteInfos) {
        CompletableFuture.runAsync(() -> clearAgentExecutionRecords(userId, needDeleteInfos));
    }

    /**
     * 清理Agent会话记录
     */
    public void clearAgentConversationRecords(String userId, String agentId,
                                               List<ConversationInfo> needDeleteConversations, String agentType) {
        if (Constant.AppType.CONTROLLER.equals(agentType)) {
            controllerDebuggingMgmtService.clearAgentConversationRecords(userId, agentId, needDeleteConversations);
            log.info("success clear agent conversation records. {}", agentId);
            return;
        }
        CompletableFuture.runAsync(() -> {
            log.info("start to clear agent conversation records. {}", agentId);
            for (ConversationInfo conversationInfo : needDeleteConversations) {
                try {
                    log.info("Start to clear agent record. agent:{} userId:{} conversation:{}", agentId, userId,
                            conversationInfo.getConversationId());
                    String executionQueryKey = String.format(agentInsightExecRel, userId, agentId,
                            conversationInfo.getConversationId());
                    String text = redisClient.get(executionQueryKey);
                    if (StringUtils.isNotEmpty(text)) {
                        List<ExecutionQuery> queries = JSON.parseObject(text, new TypeReference<List<ExecutionQuery>>() { });
                        clearAgentExecutionRecords(userId, queries);
                        redisClient.delete(executionQueryKey);
                    }
                } catch (Exception e) {
                    log.warn("To clear agent record. agent:{} userId:{} conversation:{} {}", agentId, userId,
                            conversationInfo.getConversationId(), e.getMessage());
                }
            }
            log.info("success clear agent conversation records. {}", agentId);
        });
    }

    // ============ 私有方法 ============

    private List<ConversationInfo> filterAndUpdateConversationStatus(String projectId, String agentId,
                                                                     List<ConversationInfo> conversationInfos,
                                                                     String type) {
        List<ConversationInfo> result = new ArrayList<>();
        for (ConversationInfo info : conversationInfos) {
            if (Constant.AppType.CONTROLLER.equals(type)) {
                log.info("now filter type is {}", type);
                List<ControllerExecutionBriefModel> ctrlExecBriefModels = controllerDebuggingMgmtService
                        .queryCtrlExecutions(agentId, info.getConversationId(), new ListControllerExecutionsQo());
                if (!ctrlExecBriefModels.isEmpty()) {
                    result.add(info);
                    info.setSuccessCount(0).setFailureCount(0);
                    for (ControllerExecutionBriefModel model : ctrlExecBriefModels) {
                        if (StringUtils.isEmpty(model.getStatus())
                                || Objects.equals(model.getStatus(),
                                WorkflowRunStatus.SUCCEEDED.getStatus().getDesc())) {
                            info.setSuccessCount(info.getSuccessCount() + 1);
                        } else {
                            info.setFailureCount(info.getFailureCount() + 1);
                        }
                    }
                }
            } else {
                AgentExecutionQueries queries = listAgentExecutionQueries(projectId, agentId,
                        info.getConversationId(), new ListAgentExecutionQueriesQo());
                if (queries.getCount() > 0) {
                    result.add(info);
                    info.setSuccessCount(0).setFailureCount(0);
                    for (ExecutionQuery query : queries.getExecutionQueries()) {
                        if (StringUtils.isEmpty(query.getStatus())
                                || Objects.equals(query.getStatus(),
                                WorkflowRunStatus.SUCCEEDED.getStatus().getDesc())) {
                            info.setSuccessCount(info.getSuccessCount() + 1);
                        } else {
                            info.setFailureCount(info.getFailureCount() + 1);
                        }
                    }
                }
            }
        }
        log.info("agent conversations with id: {}, total: {}, valid: {}", agentId, conversationInfos.size(),
                result.size());
        return result;
    }
}
