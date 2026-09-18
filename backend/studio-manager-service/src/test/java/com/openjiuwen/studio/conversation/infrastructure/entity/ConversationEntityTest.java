package com.openjiuwen.studio.conversation.infrastructure.entity;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ConversationEntityTest {

    @Test
    void testSerialization_UsesJsonPropertySnakeCase() throws JsonProcessingException {
        ConversationEntity e = new ConversationEntity();
        e.setConversationId("c1");
        e.setTitle("会话");
        e.setProjectId("p1");
        e.setWorkspaceId("w1");
        e.setDomainId("d1");
        e.setOwnerDomainId("od1");
        e.setOwnerUserId("ou1");
        e.setSource("console");
        e.setStatus("ACTIVE");
        e.setCreator("admin");
        e.setCreatorId("u1");
        e.setUpdater("admin");
        e.setUpdaterId("u1");
        e.setCreatedOn(new Date(0));
        e.setUpdatedOn(new Date(1));
        e.setDeleted(0);

        ObjectMapper mapper = new ObjectMapper();
        JsonNode tree = mapper.readTree(mapper.writeValueAsString(e));

        for (String key : List.of("conversation_id", "title", "project_id", "workspace_id",
                "domain_id", "owner_domain_id", "owner_user_id", "source", "status",
                "creator", "creator_id", "updater", "updater_id", "created_on", "updated_on", "deleted")) {
            assertTrue(tree.has(key), "missing JSON key: " + key);
        }
        assertFalse(tree.has("conversationId"));
        assertFalse(tree.has("ownerDomainId"));
        assertFalse(tree.has("createdOn"));
    }
}
