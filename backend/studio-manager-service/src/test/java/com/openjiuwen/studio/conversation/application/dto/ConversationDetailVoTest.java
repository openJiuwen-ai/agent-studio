package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ConversationDetailVoTest {

    @Test
    void testSerialization_UsesJsonPropertySnakeCase() throws JsonProcessingException {
        MessageVo message = MessageVo.builder().role("assistant").content("hi").build();
        ConversationDetailVo vo = ConversationDetailVo.builder()
                .conversationId("c1")
                .title("会话")
                .status("ACTIVE")
                .messages(List.of(message))
                .build();

        ObjectMapper mapper = new ObjectMapper();
        JsonNode tree = mapper.readTree(mapper.writeValueAsString(vo));

        for (String key : List.of("conversation_id", "title", "status", "messages")) {
            assertTrue(tree.has(key), "missing JSON key: " + key);
        }
        assertTrue(tree.get("messages").isArray());
        assertEquals(1, tree.get("messages").size());
        assertFalse(tree.has("conversationId"));
    }

    @Test
    void testDeserialization_AcceptsSnakeCaseJson() throws JsonProcessingException {
        ConversationDetailVo vo = new ObjectMapper().readValue(
                "{\"conversation_id\":\"c1\",\"messages\":[{\"role\":\"user\"}]}",
                ConversationDetailVo.class);

        assertEquals("c1", vo.getConversationId());
        assertEquals(1, vo.getMessages().size());
        assertEquals("user", vo.getMessages().get(0).getRole());
    }
}
