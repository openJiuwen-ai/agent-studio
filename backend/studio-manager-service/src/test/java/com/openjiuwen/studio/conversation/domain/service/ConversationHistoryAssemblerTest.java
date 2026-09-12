package com.openjiuwen.studio.conversation.domain.service;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.model.ConversationMessage;
import com.openjiuwen.studio.conversation.domain.model.valueobject.ToolRef;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ConversationHistoryAssemblerTest {

    private final ConversationHistoryAssembler service = new ConversationHistoryAssembler();

    private Conversation conversationOf(ConversationMessage... messages) {
        return Conversation.builder().messages(List.of(messages)).build();
    }

    @Test
    void testAssemble_ToolMessage_SynthesizesPair() {
        ConversationMessage toolMsg = ConversationMessage.builder()
                .role("tool")
                .content("查询结果")
                .toolRef(new ToolRef("search_tool", "{\"q\":\"test\"}"))
                .build();

        List<Message> msgs = service.assemble(conversationOf(toolMsg));

        assertEquals(2, msgs.size(), "一条 tool 消息应合成一对");
        Message call = msgs.get(0);
        assertEquals("assistant", call.getRole());
        List<Map<String, Object>> toolCalls = (List<Map<String, Object>>) call.getToolCalls();
        Map<String, Object> function = (Map<String, Object>) toolCalls.get(0).get("function");
        assertEquals("search_tool", function.get("name"));
        assertEquals("{\"q\":\"test\"}", function.get("arguments"));

        Message result = msgs.get(1);
        assertEquals("tool", result.getRole());
        assertEquals("查询结果", result.getContent());
        assertEquals(toolCalls.get(0).get("id"), result.getToolCallId(), "共享 call_id");
    }

    @Test
    void testAssemble_UserMessage_Transmits() {
        ConversationMessage userMsg = ConversationMessage.builder()
                .role("user")
                .content("查询结果")
                .build();

        List<Message> msgs = service.assemble(conversationOf(userMsg));
        assertEquals(1, msgs.size(), "一条 user 消息应透传");
        assertEquals("user", msgs.get(0).getRole());
        assertEquals("查询结果", msgs.get(0).getContent());
    }

    @Test
    void testAssemble_AssistantMessage_Transmits() {
        ConversationMessage assistantMsg = ConversationMessage.builder()
                .role("assistant")
                .content("查询结果")
                .build();

        List<Message> msgs = service.assemble(conversationOf(assistantMsg));
        assertEquals(1, msgs.size(), "一条 assistant 消息应透传");
        assertEquals("assistant", msgs.get(0).getRole());
        assertEquals("查询结果", msgs.get(0).getContent());
    }

    @Test
    void testAssemble_ToolMessage_WithoutToolRef_Discards() {
        ConversationMessage toolMsg = ConversationMessage.builder()
                .role("tool")
                .content("查询结果")
                .build();

        List<Message> msgs = service.assemble(conversationOf(toolMsg));
        assertEquals(0, msgs.size(), "无 toolRef 消息应丢弃");
    }

    @Test
    void testAssemble_UnknownRole_Discards() {
        ConversationMessage unknownMsg = ConversationMessage.builder()
                .role("unknown")
                .content("查询结果")
                .build();

        List<Message> msgs = service.assemble(conversationOf(unknownMsg));
        assertEquals(0, msgs.size(), "未知 role 消息应丢弃");
    }

    @Test
    void testAssemble_EmptyList_ReturnsEmptyList() {
        List<Message> msgs = service.assemble(conversationOf());
        assertEquals(0, msgs.size(), "空列表应返回空列表");
    }
}