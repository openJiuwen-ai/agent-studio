package com.openjiuwen.studio.conversation.application.dto;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ConversationListQueryTest {

    @Test
    void testDefaults_Page0Size20() {
        ConversationListQuery q = new ConversationListQuery();

        assertEquals(0, q.getPage());
        assertEquals(20, q.getSize());
    }

    @Test
    void testSetters_OverrideDefaults() {
        ConversationListQuery q = new ConversationListQuery();
        q.setPage(2);
        q.setSize(50);

        assertEquals(2, q.getPage());
        assertEquals(50, q.getSize());
    }
}
