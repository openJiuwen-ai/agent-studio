/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.dto.ConversationParams;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;

import lombok.extern.slf4j.Slf4j;
import okhttp3.sse.EventSource;

import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.springframework.http.HttpHeaders;

import java.util.Locale;
import java.util.Objects;

/**
 * 单智能体（Agent）SSE事件监听器
 * 处理AGENT_NODE_MESSAGE事件并保存调测数据
 */
@Slf4j
public class LLMAgentListener extends BaseEventListener {
    private final AgentRuntimeService agentRuntimeService;

    private final AgentExecuteParams executeParams;

    public LLMAgentListener(String requestId, AgentExecuteParams executeParams, HttpHeaders headers) {
        super(requestId, headers);
        agentRuntimeService = SpringBeanUtils.getBean(AgentRuntimeService.class);
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
        String event = eventObj.getEvent();
        JiuwenEventType eventType;
        try {
            eventType = JiuwenEventType.valueOf(event.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException exception) {
            log.warn("Event is not support: [{}]", event);
            passThrough(data);
            return;
        }
        processOnAgentEvent(data, eventType, eventObj);
    }

    @Override
    public void onClosed(@NotNull EventSource eventSource) {
        ConversationParams conversationParams = new ConversationParams()
            .setConversationId(executeParams.getConversationId())
            .setId(executeParams.getAgentId())
            .setExecuteType(executeParams.getExecuteType())
            .setUserId(executeParams.getUserId())
            .setVersionId(executeParams.getVersionId());

        agentRuntimeService.updateConversation(conversationParams);

        sseEmitter.complete();
        log.info("LLMAgentListener close.");
    }

    private void processOnAgentEvent(String sseData, JiuwenEventType eventType, JiuwenAgentEvent eventObj) {
        if (eventType == JiuwenEventType.AGENT_NODE_MESSAGE) {
            processOnAgentNodeMessage(eventObj);
        } else {
            passThrough(sseData);
        }
    }

    private void processOnAgentNodeMessage(JiuwenAgentEvent eventObj) {
        eventObj.setExecutionId(executeParams.getExecutionId());
        if (eventObj.getConversationId() == null) {
            eventObj.setConversationId(executeParams.getConversationId());
        }
        agentRuntimeService.saveAgentExecutionInfo(eventObj, executeParams);
    }
}
