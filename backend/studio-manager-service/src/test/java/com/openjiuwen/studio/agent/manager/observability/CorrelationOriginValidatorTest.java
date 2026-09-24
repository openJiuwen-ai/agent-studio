/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-04 §5.1/§10.2：目标 origin 白名单归一化与安全测试——
 * 精确 scheme/host/effective port 匹配；scheme/端口不同、欺骗性后缀主机、userinfo、
 * 空值/非法 URL 均拒绝；不使用字符串 startsWith 或路径关键字。
 */
class CorrelationOriginValidatorTest {

    @Test
    void sameOrigin_httpDefaultPort_matches() {
        assertThatCode(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime", "http://runtime/v1/agents?x=1")).doesNotThrowAnyException();
    }

    @Test
    void sameOrigin_httpsDefaultPort_matches() {
        assertThatCode(() -> CorrelationOriginValidator.requireSameOrigin(
            "https://runtime", "https://runtime/v1/build")).doesNotThrowAnyException();
    }

    @Test
    void sameOrigin_explicitPort_matches() {
        assertThatCode(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime:8000", "http://runtime:8000/v1/x")).doesNotThrowAnyException();
    }

    /** 默认端口与显式 80 等价（http），不误判。 */
    @Test
    void defaultPort_equalsExplicit80() {
        assertThatCode(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime", "http://runtime:80/v1/x")).doesNotThrowAnyException();
    }

    @Test
    void schemeMismatch_rejected() {
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime", "https://runtime/v1/x"))
            .isInstanceOf(AgentStudioException.class);
    }

    @Test
    void portMismatch_rejected() {
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime:8000", "http://runtime:9000/v1/x"))
            .isInstanceOf(AgentStudioException.class);
    }

    /** 欺骗性后缀主机：allowed.example.evil 不等于 allowed.example。 */
    @Test
    void deceptiveSuffixHost_rejected() {
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://allowed.example", "http://allowed.example.evil/v1/x"))
            .isInstanceOf(AgentStudioException.class);
    }

    @Test
    void hostMismatch_rejected() {
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime", "http://evil/v1/x"))
            .isInstanceOf(AgentStudioException.class);
    }

    /** 目标带 userinfo → 拒绝（凭据不得出现在关联目标 URL）。 */
    @Test
    void targetUserInfo_rejected() {
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime", "http://user:pass@runtime/v1/x"))
            .isInstanceOf(AgentStudioException.class);
    }

    @Test
    void emptyOrInvalid_rejected() {
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin("", "http://runtime/v1"))
            .isInstanceOf(AgentStudioException.class);
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin("http://runtime", null))
            .isInstanceOf(AgentStudioException.class);
        assertThatThrownBy(() -> CorrelationOriginValidator.requireSameOrigin("http://runtime", "not-a-url"))
            .isInstanceOf(AgentStudioException.class);
    }

    /** 路径含 agent-builder 但 origin 同 Runtime → 不按路径关键字拒绝（§10.4 反向陷阱）。 */
    @Test
    void agentBuilderPath_onRuntimeOrigin_matches() {
        assertThatCode(() -> CorrelationOriginValidator.requireSameOrigin(
            "http://runtime", "http://runtime/v1/agent-builder/chat/completions"))
            .doesNotThrowAnyException();
    }
}
