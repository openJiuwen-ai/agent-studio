/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.ConversationParams;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.manager.model.debugging.AgentCtrlTraceData;
import com.openjiuwen.studio.agent.manager.model.debugging.WorkflowInvokeData;
import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;
import com.openjiuwen.studio.agent.manager.service.JiuwenEventProcessor;
import com.openjiuwen.studio.agent.manager.service.debugging.ControllerDebuggingMgmtService;
import lombok.extern.slf4j.Slf4j;
import okhttp3.sse.EventSource;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

import java.util.Locale;
import java.util.Objects;

import static com.openjiuwen.studio.agent.manager.constant.Constant.TASK_ID;

/**
 * 多智能体（Controller）SSE事件监听器
 * 累积AgentCtrlTraceData，在onClosed时保存Controller调测数据
 */
@Slf4j
public class ControllerAgentListener extends BaseEventListener {
    private final AgentRuntimeService agentRuntimeService;

    private final ControllerDebuggingMgmtService controllerDebuggingMgmtService;

    private final AgentCtrlTraceData traceData = new AgentCtrlTraceData();

    private final AgentExecuteParams executeParams;

    public ControllerAgentListener(String requestId, AgentExecuteParams executeParams, HttpHeaders headers) {
        super(requestId, headers);
        agentRuntimeService = SpringBeanUtils.getBean(AgentRuntimeService.class);
        controllerDebuggingMgmtService = SpringBeanUtils.getBean(ControllerDebuggingMgmtService.class);
        this.executeParams = executeParams;
    }

    @Override
    public void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
        @NotNull String data) {
        JiuwenAgentEvent eventObj = parseJiuWenEventFromSseData(data, JiuwenAgentEvent.class);
        if (Objects.isNull(eventObj)) {
            passThrough(data);
            return;
        }
        try {
            String event = eventObj.getEvent();
            JiuwenEventType eventType;
            try {
                eventType = JiuwenEventType.valueOf(event.toUpperCase(Locale.ROOT));
            } catch (IllegalArgumentException exception) {
                log.warn("Event is not support: [{}]", event);
                passThrough(data);
                return;
            }
            if (executeParams.getExecuteType().equals(Constant.AppType.CONTROLLER)) {
                if (eventType != JiuwenEventType.TASK_END) {
                    traceData.setPreEventType(eventType);
                }
                processOnControllerEvent(data, eventType, eventObj);
            } else {
                passThrough(data);
            }
        } catch (Throwable e) {
            log.error("Fail handler controller event.", e);
        }
    }

    @Override
    public void onClosed(@NotNull EventSource eventSource) {
        log.info("ControllerAgentListener close.");
        try {
            saveInsightData(executeParams, traceData);

            ConversationParams conversationParams = new ConversationParams()
                .setConversationId(executeParams.getConversationId())
                .setId(executeParams.getAgentId())
                .setExecuteType(executeParams.getExecuteType())
                .setUserId(executeParams.getUserId())
                .setVersionId(executeParams.getVersionId());

            agentRuntimeService.updateConversation(conversationParams);
        } catch (Throwable e) {
            log.error("Agent close fail.", e);
        }
        sseEmitter.complete();
    }

    private void saveInsightData(AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        log.info("saveInsightData: isDebug={}, executionId={}, agentId={}, conversationId={}",
            executeParams.isDebug(), executeParams.getExecutionId(),
            executeParams.getAgentId(), executeParams.getConversationId());
        if (!executeParams.isDebug()) {
            log.info("Controller is not run with debug");
            return;
        }
        try {
            if (!traceData.isResume()) {
                traceData.setInputs(executeParams.getInputs());
            }
            traceData.setEndTime(System.currentTimeMillis());
            if (traceData.getStatus() == null) {
                traceData.setStatus("succeeded");
            }
            traceData.setAgentId(executeParams.getAgentId());
            controllerDebuggingMgmtService.saveControllerDebuggingInfo(executeParams, traceData);
        } catch (Exception e) {
            log.error("Fail save insight data.", e);
        }
    }

    void processOnControllerEvent(String sseData, JiuwenEventType eventType, JiuwenAgentEvent eventObj) {
        switch (eventType) {
            case AGENT_INTERRUPTED, WORKFLOW_BLOCKED -> blockHandler(sseData);
            case WORKFLOW_RESUME -> passResumeThrough(sseData);
            case WORKFLOW_NODE_MESSAGE -> processOnControllerWorkflowNodeMessage(sseData);
            case AGENT_NODE_MESSAGE -> processOnCtrlAgentNodeMessage(eventObj);
            default -> passThrough(sseData);
        }
    }

    private void blockHandler(String sseData) {
        passThrough(sseData);
        if (executeParams.isDebug() || executeParams.isUploadOpsSwitch()) {
            log.info("Agent task is block. receive task block message.");
        }
        traceData.setBlock(true);
        agentRuntimeService.saveTaskId(executeParams.getAgentId(), executeParams.getConversationId(),
            MDC.get(TASK_ID));
    }

    private void passResumeThrough(String sseData) {
        passThrough(sseData);
        traceData.setResume(true);
    }

    private void processOnControllerWorkflowNodeMessage(String sseData) {
        JiuwenEvent eventObj = com.alibaba.fastjson.JSON.parseObject(sseData, JiuwenEvent.class);
        if (eventObj == null) {
            log.error("Got null parsed jiuwen event. Do nothing with this workflow node message: {}.", sseData);
            return;
        }

        NodeRunInfo nodeRunInfo = JiuwenEventProcessor.convertNodeRunInfo(eventObj.getData());
        if (executeParams.isDebug()) {
            String workflowId = nodeRunInfo.getAgentId();
            WorkflowInvokeData invokeData = traceData.getWorkflows()
                .computeIfAbsent(workflowId, id -> new WorkflowInvokeData(workflowId));
            invokeData.updateProperties(nodeRunInfo, eventObj.getData());
        }
        eventObj.setExecutionId(executeParams.getExecutionId());
    }

    private void processOnCtrlAgentNodeMessage(JiuwenAgentEvent eventObj) {
        eventObj.setExecutionId(executeParams.getExecutionId());
        if (executeParams.isDebug()) {
            traceData.appendAgentNode(eventObj);
        }
    }
}
