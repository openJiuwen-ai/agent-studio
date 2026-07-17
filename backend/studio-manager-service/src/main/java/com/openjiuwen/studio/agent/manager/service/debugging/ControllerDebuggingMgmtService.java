/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.debugging;

import static com.openjiuwen.studio.agent.manager.constant.Constant.TASK_ID;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.TypeReference;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;
import com.openjiuwen.studio.agent.common.dto.run.ListControllerExecutionsQo;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.manager.model.debugging.AgentCtrlTraceData;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionBriefModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionDetailModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionInvokeModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionSummary;
import com.openjiuwen.studio.agent.manager.model.debugging.WorkflowInvokeData;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * ControllerDebuggingMgmtService
 *
 */
@Slf4j
@Component
@RequiredArgsConstructor(onConstructor_ = {@Autowired})
public class ControllerDebuggingMgmtService {
    private static final String LLM_EXEC_KEY_PREFIX = "agent.service.controller.execution.invocations.llm.";
    private static final String WORKFLOW_EXEC_KEY_PREFIX = "agent.service.controller.execution.invocations.workflow.";

    private final RedisClient redisClient;

    private final CtrlDebuggingModelProcessService ctrlDebuggingModelProcessService;

    @Value("${redis.expire_time}")
    private long expireTime;

    @Value("${agent.max-execution-size:20}")
    private Integer maxExecutionSize;

    private static final String INVOCATION_SUMMARY_KEY = "agent.service.controller.execution.invocations.summary.%s.%s";

    private static final String CONTROLLER_EXECUTION_INFO_RW_LOCK_KEY_FORMAT
        = "agent.service.controller.execution.invocations.%s.%s.lock";

    private static final String CONTROLLER_EXECUTIONS_KEY_FORMAT = "agent.service.controller.executions.%s.%s.%s";

    private static final String CONTROLLER_EXECUTIONS_RW_LOCK_KEY_FORMAT
        = "agent.service.controller.executions.%s.%s.%s.lock";

    /**
     * queryCtrlExecutionDetail
     *
     * @param agentId agentId
     * @param executionId executionId
     * @return ControllerExecutionDetailModel
     */
    public ControllerExecutionDetailModel queryCtrlExecutionDetail(String agentId, String executionId) {
        String execSummaryKey = obtainExecSummaryKey(agentId, executionId);
        String storedExecDetailStr = redisClient.get(execSummaryKey);

        if (StringUtils.isBlank(storedExecDetailStr)) {
            log.warn("Not found exec summary. key:{}", execSummaryKey);
            return new ControllerExecutionDetailModel();
        }

        ControllerExecutionSummary summary = com.openjiuwen.studio.agent.common.utils.JsonUtils.decode(
            storedExecDetailStr, ControllerExecutionSummary.class);
        if (summary == null) {
            log.warn("Exec summary is empty. {}", storedExecDetailStr);
            return new ControllerExecutionDetailModel();
        }

        ControllerExecutionDetailModel model = new ControllerExecutionDetailModel();
        model.setExecutionId(summary.getExecutionId());
        model.setQuery(summary.getQuery());
        model.setConversationId(summary.getConversationId());
        model.setStatus(summary.getStatus());

        List<ControllerExecutionInvokeModel> invocations = new ArrayList<>();
        long totalTime = 0;
        for (String nodeId : summary.getAgentNodeIds()) {
            String key = llmExecKey(agentId, executionId, nodeId);
            String storedExecDetail = redisClient.get(key);
            ControllerExecutionInvokeModel md = storedExecDetail == null
                ? null
                : com.openjiuwen.studio.agent.common.utils.JsonUtils.decode(storedExecDetail,
                    ControllerExecutionInvokeModel.class);
            if (md != null) {
                if (md.getEndTime() != null && md.getStartTime() != null) {
                    totalTime += md.getEndTime() - md.getStartTime();
                }
                invocations.add(md);
            } else {
                log.warn("Not found llm invoke content key:{}", key);
            }
        }

        boolean isWaiting = false;
        for (String nodeId : summary.getWorkflowIds()) {
            String key = workflowExecKey(agentId, executionId, nodeId);
            String storedExecDetail = redisClient.get(key);

            WorkflowInvokeData data = com.openjiuwen.studio.agent.common.utils.JsonUtils.decode(storedExecDetail,
                WorkflowInvokeData.class);

            if (data != null && !CollectionUtils.isEmpty(data.getEventList())) {
                invocations.addAll(data.getEventList());
                ControllerExecutionInvokeModel ft = data.getEventList().get(0);
                ControllerExecutionInvokeModel ed = data.getEventList().get(data.getEventList().size() - 1);
                if (ed.getEndTime() == null) {
                    isWaiting = true;
                    ed.setEndTime(ed.getStartTime());
                }
                totalTime += ed.getEndTime() - ft.getStartTime();
            } else {
                log.warn("Not found workflow invoke content key:{}", key);
            }
        }

        invocations.sort(Comparator.comparing(ControllerExecutionInvokeModel::getStartTime,
            Comparator.nullsLast(Comparator.naturalOrder())));

        invocations = ctrlDebuggingModelProcessService.filterUsefulNodes(invocations);
        invocations = ctrlDebuggingModelProcessService.normalizeCtrlExecNodes(invocations, model);

        invocations.sort(Comparator.comparing(ControllerExecutionInvokeModel::getStartTime,
            Comparator.nullsLast(Comparator.naturalOrder())));

        if (CollectionUtils.isNotEmpty(invocations)) {
            ControllerExecutionInvokeModel lastInvocation = invocations.get(invocations.size() - 1);
            if (lastInvocation.getStatus() != null && Strings.CS.equals("failed", lastInvocation.getStatus().getDesc())
                && !Strings.CS.equals("failed", model.getStatus())) {
                model.setError(lastInvocation.getErrorMsg());
                model.setStatus("failed");
            }
            model.setStartTime(invocations.get(0).getStartTime());
            model.setEndTime(invocations.get(0).getStartTime() + totalTime);
        }

        model.setInvocations(invocations);
        if (isWaiting) {
            model.setStatus("waiting");
        }
        return model;
    }

    /**
     * queryCtrlExecutions
     *
     * @param agentId agentId
     * @param conversationId conversationId
     * @param listControllerExecutionsQo listControllerExecutionsQo
     * @return List<ControllerExecutionBriefModel>
     */
    public List<ControllerExecutionBriefModel> queryCtrlExecutions(String agentId, String conversationId,
        ListControllerExecutionsQo listControllerExecutionsQo) {
        String userId = RequestContextUtils.getRequestUserId();
        String execsKey = obtainExecsKey(userId, agentId, conversationId);
        log.info("query conversation execution. {}", execsKey);

        String storedCtrlExecsStr = redisClient.get(execsKey);
        if (StringUtils.isBlank(storedCtrlExecsStr)) {
            return Collections.emptyList();
        }

        List<ControllerExecutionBriefModel> storedCtrlExecs = JSON.parseArray(storedCtrlExecsStr,
            ControllerExecutionBriefModel.class);

        return storedCtrlExecs == null ? Collections.emptyList() : storedCtrlExecs;
    }

    /**
     * saveControllerDebuggingInfo
     *
     * @param executeParams executeParams
     * @param traceData eventObj
     */
    public void saveControllerDebuggingInfo(AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        if (executeParams == null || !executeParams.isDebug() || traceData == null) {
            log.error("Execute param or event is null. Failed to save controller debugging info.");
            return;
        }

        String userId = executeParams.getUserId();
        String controllerId = executeParams.getAgentId();
        String conversationId = executeParams.getConversationId();
        String executionId = executeParams.getExecutionId() == null
            ? MDC.get(TASK_ID)
            : executeParams.getExecutionId();
        log.info("saveControllerDebuggingInfo: userId={}, controllerId={}, conversationId={}, executionId={}",
            userId, controllerId, conversationId, executionId);
        traceData.setConversationId(conversationId);

        if (traceData.isResume()) {
            String cacheId = redisClient.get(executionIdCacheKey(controllerId, conversationId));
            executionId = StringUtils.isBlank(cacheId) ? executionId : cacheId;
        }
        traceData.setExecutionId(executionId);

        RedisLock execOpLock = null;
        try {
            String execDetailOpLockKey = obtainExecDetailOpLockKey(controllerId, executionId);
            execOpLock = redisClient.getLock(execDetailOpLockKey);

            if (execOpLock.tryLock(Duration.ofSeconds(10))) {
                if (traceData.isBlock()) {
                    redisClient.set(executionIdCacheKey(controllerId, conversationId), executionId,
                        Duration.ofSeconds(expireTime));
                }

                String summaryKey = obtainExecSummaryKey(controllerId, executionId);
                String summaryKeyStr = redisClient.get(summaryKey);

                ControllerExecutionSummary summary = new ControllerExecutionSummary(traceData);
                summary.setQuery(executeParams.getQuery());
                summary.setMessages(executeParams.getMessages());
                if (StringUtils.isBlank(summaryKeyStr)) {
                    for (Map.Entry<String, WorkflowInvokeData> entry : traceData.getWorkflows().entrySet()) {
                        String key = workflowExecKey(controllerId, executionId, entry.getKey());
                        String ss = JSON.toJSONString(entry.getValue());
                        redisClient.set(key, ss, Duration.ofSeconds(expireTime));
                        log.debug("Success first save workflow to redis: {} {}", key, ss);
                    }

                    for (Map.Entry<String, ControllerExecutionInvokeModel> entry : traceData.getLlmInvokeDataMap()
                        .entrySet()) {
                        String key = llmExecKey(controllerId, executionId, entry.getKey());
                        String ss = JSON.toJSONString(entry.getValue());
                        redisClient.set(key, ss, Duration.ofSeconds(expireTime));
                        log.debug("Success first save llm to redis: {} {}", key, ss);
                    }

                    saveControllerExecution(userId, executeParams.getQuery(), traceData);
                } else {
                    ControllerExecutionSummary existSummary = JsonUtils.json2ObjQuietly(summaryKeyStr,
                        ControllerExecutionSummary.class);
                    if (existSummary != null) {
                        summary.setQuery(existSummary.getQuery());
                        summary.setInputs(existSummary.getInputs());
                        summary.getAgentNodeIds().addAll(existSummary.getAgentNodeIds());
                        summary.getWorkflowIds().addAll(existSummary.getWorkflowIds());
                        summary.setStartTime(existSummary.getStartTime());
                    }

                    for (Map.Entry<String, WorkflowInvokeData> entry : traceData.getWorkflows().entrySet()) {
                        String key = workflowExecKey(controllerId, executionId, entry.getKey());
                        String storedExecDetailStr = redisClient.get(key);
                        WorkflowInvokeData data = null;
                        if (!StringUtils.isBlank(storedExecDetailStr)) {
                            data = JSON.parseObject(storedExecDetailStr, WorkflowInvokeData.class);
                        }
                        if (data == null) {
                            data = entry.getValue();
                        } else {
                            data.getEventList().addAll(entry.getValue().getEventList());
                            if (entry.getValue().getOutputs() != null) {
                                data.setOutputs(entry.getValue().getOutputs());
                            }
                            if (entry.getValue().getEndTime() != null) {
                                data.setEndTime(entry.getValue().getEndTime());
                            }
                        }
                        String ss = JSON.toJSONString(data);
                        redisClient.set(key, ss, Duration.ofSeconds(expireTime));
                        log.debug("Success save workflow to redis:{} {}", key, ss);
                    }

                    for (Map.Entry<String, ControllerExecutionInvokeModel> entry : traceData.getLlmInvokeDataMap()
                        .entrySet()) {
                        String key = llmExecKey(controllerId, executionId, entry.getKey());
                        String ss = JSON.toJSONString(entry.getValue());

                        redisClient.set(key, ss, Duration.ofSeconds(expireTime));
                        log.debug("Success save llm to redis:{} {}", key, ss);
                    }
                }

                redisClient.set(summaryKey, JSON.toJSONString(summary), Duration.ofSeconds(expireTime));
            }
        } catch (Exception e) {
            log.error("Failed to save controller debugging info.", e);
        } finally {
            if (execOpLock != null) {
                execOpLock.unlock();
            }
        }
    }

    private void saveControllerExecution(String userId, String query, AgentCtrlTraceData ctrlExecDetailModel) {
        String agentId = ctrlExecDetailModel.getAgentId();
        String conversationId = ctrlExecDetailModel.getConversationId();
        log.info("saveControllerExecution: userId={}, agentId={}, conversationId={}, executionId={}",
            userId, agentId, conversationId, ctrlExecDetailModel.getExecutionId());

        RedisLock ctrlExecsOpLock = null;
        try {
            String ctrlExecsOpLockKey = obtainExecsOpLockKey(userId, agentId, conversationId);
            ctrlExecsOpLock = redisClient.getLock(ctrlExecsOpLockKey);

            if (ctrlExecsOpLock.tryLock(Duration.ofSeconds(10))) {
                String ctrlExecsKey = obtainExecsKey(userId, agentId, conversationId);

                String storedCtrlExecsStr = redisClient.get(ctrlExecsKey);

                List<ControllerExecutionBriefModel> existentExecutions;
                if (StringUtils.isBlank(storedCtrlExecsStr)) {
                    existentExecutions = new ArrayList<>();
                } else {
                    existentExecutions = JSON.parseObject(storedCtrlExecsStr, new TypeReference<>() {});
                }

                List<ControllerExecutionBriefModel> executions = new ArrayList<>();
                for (ControllerExecutionBriefModel existentExecution : existentExecutions) {
                    if (!Strings.CS.equals(existentExecution.getExecutionId(), ctrlExecDetailModel.getExecutionId())) {
                        executions.add(existentExecution);
                    }
                }

                ControllerExecutionBriefModel model = new ControllerExecutionBriefModel();
                model.setExecutionId(ctrlExecDetailModel.getExecutionId());
                model.setQuery(query);
                model.setStatus(ctrlExecDetailModel.getStatus());
                model.setStartTime(System.currentTimeMillis());
                executions.add(model);

                // 根据query size按时间戳倒序截断
                executions = executions.stream()
                    .sorted(Comparator.comparing(ControllerExecutionBriefModel::getStartTime).reversed())
                    .toList();

                if (executions.size() > maxExecutionSize) {
                    clearAgentExecutionRecordsAsync(agentId, executions.subList(maxExecutionSize, executions.size()));
                    executions = executions.subList(0, maxExecutionSize);
                }


                redisClient.set(ctrlExecsKey, JSON.toJSONString(executions), Duration.ofSeconds(expireTime));
                log.info("Save conversation execution:{} {}", ctrlExecsKey, JSON.toJSONString(executions));
            }
        } catch (Exception e) {
            log.error("Failed to save controller execution.", e);
        } finally {
            if (ctrlExecsOpLock != null) {
                ctrlExecsOpLock.unlock();
            }
        }
    }

    private String obtainExecSummaryKey(String agentId, String executionId) {
        return String.format(INVOCATION_SUMMARY_KEY, agentId, executionId);
    }

    private String executionIdCacheKey(String agentId, String conversationId) {
        return String.format("agent.service.controller.execution.invocations.id.%s.%s", agentId, conversationId);
    }

    private String workflowExecKey(String agentId, String executionId, String id) {
        return String.format(WORKFLOW_EXEC_KEY_PREFIX + "%s.%s.%s", agentId, executionId,
            id);
    }

    private String llmExecKey(String agentId, String executionId, String id) {
        return String.format(LLM_EXEC_KEY_PREFIX + "%s.%s.%s", agentId, executionId, id);
    }

    private String obtainExecDetailOpLockKey(String agentId, String executionId) {
        return String.format(CONTROLLER_EXECUTION_INFO_RW_LOCK_KEY_FORMAT, agentId, executionId);
    }

    public String obtainExecsKey(String userId, String agentId, String conversationId) {
        return String.format(CONTROLLER_EXECUTIONS_KEY_FORMAT, userId, agentId, conversationId);
    }

    public String obtainExecsOpLockKey(String userId, String agentId, String conversationId) {
        return String.format(CONTROLLER_EXECUTIONS_RW_LOCK_KEY_FORMAT, userId, agentId, conversationId);
    }

    public void clearAgentConversationRecords(String userId, String agentId,
        List<ConversationInfo> needDeleteConversations) {
        CompletableFuture.runAsync(() -> {
            log.info("start to clear controller agent conversation records. {}", agentId);
            for (ConversationInfo conversationInfo : needDeleteConversations) {
                try {
                    log.info("Start to clear controller agent record. agent:{} userId:{} conversation:{}", agentId,
                        userId, conversationInfo.getConversationId());

                    String execsKey = obtainExecsKey(userId, agentId, conversationInfo.getConversationId());
                    log.info("query controller conversation execution. {}", execsKey);

                    String storedCtrlExecsStr = redisClient.get(execsKey);
                    if (StringUtils.isBlank(storedCtrlExecsStr)) {
                        List<ControllerExecutionBriefModel> storedCtrlExecs = JSON.parseArray(storedCtrlExecsStr,
                            ControllerExecutionBriefModel.class);
                        clearAgentExecutionRecords(agentId, storedCtrlExecs);
                        redisClient.delete(execsKey);
                    }
                } catch (Exception e) {
                    log.warn("Start to clear controller agent record. agent:{} userId:{} conversation:{} {}", agentId,
                        userId, conversationInfo.getConversationId(), e.getMessage());
                }
            }
            log.info("success clear controller agent conversation records. {}", agentId);
        });
    }

    private void clearAgentExecutionRecords(String agentId, List<ControllerExecutionBriefModel> infos) {
        for (ControllerExecutionBriefModel info : infos) {
            try {
                redisClient.deleteByPrefix(LLM_EXEC_KEY_PREFIX + agentId + "." + info.getExecutionId() + ".");
                redisClient.deleteByPrefix(WORKFLOW_EXEC_KEY_PREFIX + agentId + "." + info.getExecutionId() + ".");
            } catch (Exception e) {
                log.error("Fail delete controller agent execution record. {} execution:{} {}", agentId,
                    info.getExecutionId(), e.getMessage());
            }
        }
    }

    CompletableFuture<Void> clearAgentExecutionRecordsAsync(String agentId, List<ControllerExecutionBriefModel> infos) {
        return CompletableFuture.runAsync(() -> clearAgentExecutionRecords(agentId, infos));
    }
}
