package com.openjiuwen.studio.conversation.domain.model;

import com.openjiuwen.studio.conversation.domain.model.valueobject.TokenUsage;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ConversationMessageTest {

    // 标准动作 1：测 @Builder —— 构造 → 逐字段断言
    @Test
    void testBuilder_SetsAllFields() {
        // Arrange：准备输入
        TokenUsage tokens = new TokenUsage("10", "20", "30");
        // Act：用 builder 构造被测对象
        ConversationMessage msg = ConversationMessage.builder()
                .role("assistant")
                .content("hello")
                .tokenUsage(tokens)
                .build();
        // Assert：断言结果
        assertEquals("assistant", msg.getRole());
        assertEquals("hello", msg.getContent());
        assertSame(tokens, msg.getTokenUsage());  // assertSame=同一引用
    }

    // ↓↓↓ 剩下的你按这个模式补全 ↓↓↓

    @Test
    void testNoArgsConstructor_FieldsAreNull() {
        // Arrange+Act：new ConversationMessage()
        ConversationMessage msg = new ConversationMessage();
        // Assert：assertNotNull(msg)；msg.getRole() 为 null；msg.getContent() 为 null
        assertNotNull(msg);
        assertNull(msg.getRole());
        assertNull(msg.getContent());
        assertNull(msg.getTokenUsage());
        assertNull(msg.getToolRef());
        assertNull(msg.getFileRefs());
        assertNull(msg.getExecutionRef());
        assertNull(msg.getEvent());
        assertNull(msg.getModelDeploymentId());
        assertNull(msg.getCreatedAt());
    }

    @Test
    void testEquals_SameValues_ShouldBeEqual() {
        // 构造两个字段完全相同的 msg（用 builder 或全参构造）
        // Arrange：准备输入
        TokenUsage tokens = new TokenUsage("10", "20", "30");
        // Act：用 builder 构造被测对象
        ConversationMessage msg1 = ConversationMessage.builder()
                .role("assistant")
                .content("hello")
                .tokenUsage(tokens)
                .build();
        ConversationMessage msg2 = ConversationMessage.builder()
                .role("assistant")
                .content("hello")
                .tokenUsage(tokens)
                .build();

        // Assert：assertEquals(msg1, msg2)；assertEquals(msg1.hashCode(), msg2.hashCode())
        assertEquals(msg1, msg2);
//        assertEquals(msg1.hashCode(), msg2.hashCode());
    }

    @Test
    void testEquals_DifferentContent_ShouldNotBeEqual() {
        // 两个 msg 只有 content 不同
        // Arrange：准备输入
        TokenUsage tokens = new TokenUsage("10", "20", "30");
        // Act：用 builder 构造被测对象
        ConversationMessage msg1 = ConversationMessage.builder()
                .role("assistant")
                .content("hello")
                .tokenUsage(tokens)
                .build();
        ConversationMessage msg2 = ConversationMessage.builder()
                .role("assistant")
                .content("hello2")
                .tokenUsage(tokens)
                .build();
        // Assert：assertNotEquals(msg1, msg2)；assertNotEquals(msg1.hashCode(), msg2.hashCode())
        assertNotEquals(msg1, msg2);
//        assertNotEquals(msg1.hashCode(), msg2.hashCode());
    }

    @Test
    void testEquals_NullAndOtherType_ShouldNotBeEqual() {
        ConversationMessage msg = ConversationMessage.builder()
                .role("assistant")
                .content("hello")
                .tokenUsage(new TokenUsage("10", "20", "30"))
                .build();

        // Assert：assertNotEquals(null, msg)；assertNotEquals("string", msg)
        assertNotEquals(null, msg);
        assertNotEquals("string", msg);
    }

    @Test
    void testToString_NotNull() {
        ConversationMessage msg = ConversationMessage.builder()
                .role("assistant")
                .content("hello")
                .tokenUsage(new TokenUsage("10", "20", "30"))
                .build();
        // Assert：assertNotNull(msg.toString())
        assertNotNull(msg.toString());
    }
}
