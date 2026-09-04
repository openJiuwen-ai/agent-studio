/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.service;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.model.ConversationMessage;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 会话历史组装服务：按 created_on 序将聚合内全部消息转换为平台 Message 列表（全量注入，不做上下文裁剪）。
 *
 * <p>工具消息合成规则：每个 role=tool 行自含请求与结果，引擎/模型 API 要求 tool 消息前必须有对应的
 * assistant(tool_calls) 消息，故注入时每个 tool 行合成一对 Message（assistant 带 tool_calls + tool 结果带
 * tool_call_id 关联），不做 role/content 直映。</p>
 */
@Service
public class ConversationHistoryAssembler {

    /**
     * 组装全量历史
     *
     * @param conversation 会话聚合（含全部消息，created_on 序）
     * @return 平台 Message 列表
     */
    public List<Message> assemble(Conversation conversation) {
        List<Message> messages = new ArrayList<>();
        for (ConversationMessage message : conversation.getMessages()) {
            // TODO 不要直接用字符串，用枚举类
            if ("tool".equals(message.getRole()) && message.getToolRef() != null) {
                appendSynthesizedToolPair(messages, message);
            } else if ("user".equals(message.getRole()) || "assistant".equals(message.getRole())) {
                messages.add(new Message().setRole(message.getRole()).setContent(message.getContent()));
            }
        }
        return messages;
    }

    /**
     * 合成 assistant(tool_calls) + tool 结果一对 Message
     */
    private void appendSynthesizedToolPair(List<Message> messages, ConversationMessage message) {
        String callId = "call_" + UUID.randomUUID();

        Map<String, Object> function = new LinkedHashMap<>();
        function.put("name", message.getToolRef().getToolId());
        function.put("arguments", message.getToolRef().getArgs());
        Map<String, Object> toolCall = new LinkedHashMap<>();
        toolCall.put("id", callId);
        toolCall.put("type", "function");
        toolCall.put("function", function);

        Message callMessage = new Message().setRole("assistant")
            .setToolCalls(Collections.singletonList(toolCall));
        messages.add(callMessage);

        Message toolMessage = new Message().setRole("tool")
            .setToolCallId(callId)
            .setContent(message.getContent());
        messages.add(toolMessage);
    }
}
