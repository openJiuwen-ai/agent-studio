package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ConversationVoTest {

    @Test
    void testSerialization_UsesJsonPropertySnakeCase() throws JsonProcessingException {
        ConversationVo vo = ConversationVo.builder()
                .conversationId("c1")
                .title("会话")
                .status("ACTIVE")
                .source("console")
                .createdAt(new Date(0))
                .updatedAt(new Date(1))
                .build();

        ObjectMapper mapper = new ObjectMapper();
        JsonNode tree = mapper.readTree(mapper.writeValueAsString(vo));

        for (String key : List.of("conversation_id", "title", "status", "source", "created_at", "updated_at")) {
            assertTrue(tree.has(key), "missing JSON key: " + key);
        }
        assertFalse(tree.has("conversationId"));
        assertFalse(tree.has("createdAt"));
    }

    @Test
    void testDeserialization_AcceptsSnakeCaseJson() throws JsonProcessingException {
        ConversationVo vo = new ObjectMapper().readValue(
                "{\"conversation_id\":\"c1\",\"status\":\"ACTIVE\"}", ConversationVo.class);

        assertEquals("c1", vo.getConversationId());
        assertEquals("ACTIVE", vo.getStatus());
    }
}
