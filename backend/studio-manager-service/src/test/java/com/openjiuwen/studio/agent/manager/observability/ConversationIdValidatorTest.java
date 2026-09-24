/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * COM-05 §12.2：三类会话校验 profile 的字符集/长度边界，及路由 pattern 到 profile 的显式映射。
 * profile 接受范围不得宽于对应 Controller 注解（STANDARD/WORKFLOW 均不含点号冒号，N2L 仅 1~128）。
 */
class ConversationIdValidatorTest {

    // ---- STANDARD_CONVERSATION：[A-Za-z0-9_-]，1～64 ----

    @Test
    void standardProfile_boundaries() {
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a")).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a".repeat(64))).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a".repeat(65))).isFalse();
    }

    @Test
    void standardProfile_rejectsDotColonAndWhitespace() {
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a.b")).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a:b")).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a b")).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "a-b_c9")).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, "")).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.STANDARD_CONVERSATION, null)).isFalse();
    }

    // ---- WORKFLOW_CONVERSATION：[A-Za-z0-9_()-]，1～64 ----

    @Test
    void workflowProfile_allowsParenthesesOnly() {
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.WORKFLOW_CONVERSATION, "a(b)c")).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.WORKFLOW_CONVERSATION, "a-b_c()9")).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.WORKFLOW_CONVERSATION, "a.b")).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.WORKFLOW_CONVERSATION, "a".repeat(65))).isFalse();
    }

    // ---- N2L_CONVERSATION：[A-Za-z0-9._:-]，1～128 ----

    @Test
    void n2lProfile_boundariesAndCharset() {
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.N2L_CONVERSATION, "a")).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.N2L_CONVERSATION, "a.b:c-d_e".repeat(13))).isTrue();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.N2L_CONVERSATION, "a".repeat(129))).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.N2L_CONVERSATION, "a b")).isFalse();
        assertThat(ConversationIdValidator.isValid(
            ConversationIdValidator.Profile.N2L_CONVERSATION, "a(b)")).isFalse();
    }

    // ---- 路由 pattern → profile 显式映射 ----

    @Test
    void profileFor_registeredRoutes() {
        assertThat(ConversationIdValidator.profileFor(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}"))
            .isEqualTo(ConversationIdValidator.Profile.STANDARD_CONVERSATION);
        assertThat(ConversationIdValidator.profileFor(
            "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}"))
            .isEqualTo(ConversationIdValidator.Profile.WORKFLOW_CONVERSATION);
        assertThat(ConversationIdValidator.profileFor(
            "/v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}"))
            .isEqualTo(ConversationIdValidator.Profile.WORKFLOW_CONVERSATION);
        assertThat(ConversationIdValidator.profileFor(
            "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat"))
            .isEqualTo(ConversationIdValidator.Profile.N2L_CONVERSATION);
    }

    @Test
    void profileFor_unregisteredRoute_returnsNull() {
        assertThat(ConversationIdValidator.profileFor("/v1/unknown/route")).isNull();
        assertThat(ConversationIdValidator.profileFor(null)).isNull();
    }
}
