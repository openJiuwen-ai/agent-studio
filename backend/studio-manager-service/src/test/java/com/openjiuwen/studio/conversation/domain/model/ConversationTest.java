package com.openjiuwen.studio.conversation.domain.model;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ConversationTest {

    @Test
    void testBuilder_DefaultMessages_IsEmptyList() {
        Conversation c = Conversation.builder().conversationId("c1").title("会话").build();

        assertNotNull(c.getMessages());
        assertTrue(c.getMessages().isEmpty());
    }

    @Test
    void testBuilder_WithMessages_ReturnsProvided() {
        ConversationMessage m = ConversationMessage.builder().role("assistant").content("hi").build();

        Conversation c = Conversation.builder()
                .conversationId("c1")
                .messages(List.of(m))
                .build();

        assertEquals(List.of(m), c.getMessages());
    }

    @Test
    void testBuilder_SetsFields() {
        Conversation c = Conversation.builder()
                .conversationId("c1").title("t").source("console").status("ACTIVE").build();

        assertEquals("c1", c.getConversationId());
        assertEquals("t", c.getTitle());
        assertEquals("console", c.getSource());
        assertEquals("ACTIVE", c.getStatus());
    }

    @Test
    void testNoArgsConstructor_Messages_IsEmptyList() {
        Conversation c = new Conversation();

        assertNotNull(c.getMessages());
        assertTrue(c.getMessages().isEmpty());
    }
}
