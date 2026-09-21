package com.openjiuwen.studio.conversation.infrastructure.entity;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ConversationSubRunEntityTest {

    @Test
    void testSerialization_UsesJsonPropertySnakeCase() throws JsonProcessingException {
        ConversationSubRunEntity e = new ConversationSubRunEntity();
        e.setId(1L);
        e.setSubExecutionId("sub-1");
        e.setExecutionId("exec-1");
        e.setConversationId("c1");
        e.setAgentId("agent-1");
        e.setRole("tool");
        e.setContent("结果");
        e.setToolId("tool-1");
        e.setToolArgs("{}");
        e.setFileIds("[]");
        e.setEvent("sub_done");
        e.setTotalTokens("10");
        e.setPromptTokens("5");
        e.setCompletionTokens("5");
        e.setProjectId("p1");
        e.setWorkspaceId("w1");
        e.setDomainId("d1");
        e.setCreator("admin");
        e.setCreatorId("u1");
        e.setUpdater("admin");
        e.setUpdaterId("u1");
        e.setCreatedOn(new Date(0));
        e.setUpdatedOn(new Date(1));
        e.setDeleted(0);

        ObjectMapper mapper = new ObjectMapper();
        JsonNode tree = mapper.readTree(mapper.writeValueAsString(e));

        for (String key : List.of("id", "sub_execution_id", "execution_id", "conversation_id",
                "agent_id", "role", "content", "tool_id", "tool_args", "file_ids", "event",
                "total_tokens", "prompt_tokens", "completion_tokens", "project_id", "workspace_id",
                "domain_id", "creator", "creator_id", "updater", "updater_id", "created_on",
                "updated_on", "deleted")) {
            assertTrue(tree.has(key), "missing JSON key: " + key);
        }
        assertFalse(tree.has("subExecutionId"));
        assertFalse(tree.has("executionId"));
        assertFalse(tree.has("createdOn"));
    }
}
