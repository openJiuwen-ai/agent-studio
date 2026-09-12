package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class MessageVoTest {

    @Test
    void testSerialization_UsesJsonPropertySnakeCase() throws JsonProcessingException {
        MessageVo vo = MessageVo.builder()
                .role("tool")
                .content("{\"k\":\"v\"}")
                .toolId("tool-1")
                .toolArgs("{}")
                .fileIds("[\"f1\"]")
                .executionId("exec-1")
                .subExecutionId("sub-1")
                .agentId("agent-1")
                .event("run_done")
                .createdAt(new Date(0))
                .build();

        ObjectMapper mapper = new ObjectMapper();
        JsonNode tree = mapper.readTree(mapper.writeValueAsString(vo));

        for (String key : List.of("role", "content", "tool_id", "tool_args", "file_ids",
                "execution_id", "sub_execution_id", "agent_id", "event", "created_at")) {
            assertTrue(tree.has(key), "missing JSON key: " + key);
        }
        assertFalse(tree.has("toolId"));
        assertFalse(tree.has("subExecutionId"));
        assertFalse(tree.has("createdAt"));
    }

    @Test
    void testDeserialization_AcceptsSnakeCaseJson() throws JsonProcessingException {
        MessageVo vo = new ObjectMapper().readValue(
                "{\"role\":\"tool\",\"tool_id\":\"t1\",\"sub_execution_id\":\"s1\"}", MessageVo.class);

        assertEquals("tool", vo.getRole());
        assertEquals("t1", vo.getToolId());
        assertEquals("s1", vo.getSubExecutionId());
    }
}
