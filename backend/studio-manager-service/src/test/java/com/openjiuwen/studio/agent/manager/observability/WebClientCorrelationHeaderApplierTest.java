/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-04 §6.3/§10.3（WebClient 行）：调用点显式策略 + origin 校验 + MDC 读取，
 * 返回的 Consumer 在请求构建时按覆盖算法写入——Builder 两 Header、伪造变体先删后写、
 * execution 不存在、origin 不匹配与缺上下文明确失败。
 */
class WebClientCorrelationHeaderApplierTest {

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    private void fullMdc() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
    }

    @Test
    void builder_twoHeaders_executionAbsent_forgedReplaced() {
        fullMdc();
        HttpHeaders headers = new HttpHeaders();
        headers.add("x-request-id", "forged");
        headers.add("X-EXECUTION-ID", "forged-exec");

        WebClientCorrelationHeaderApplier.apply(OutboundCorrelationPolicy.BUILDER,
            "http://builder", "http://builder/v1/prompt/build").accept(headers);

        assertThat(headers.getFirst("X-Request-Id")).isEqualTo("req-1");
        assertThat(headers.getFirst("TraceID")).isEqualTo("trace-1");
        assertThat(headers.getFirst("X-Execution-Id")).isNull();
    }

    /** Runtime 非执行：路径含 agent-builder（反向陷阱），origin 为 Runtime → 仍两 Header、无 execution。 */
    @Test
    void runtimeNonExecution_agentBuilderPath_twoHeadersNoExecution() {
        fullMdc();
        HttpHeaders headers = new HttpHeaders();

        WebClientCorrelationHeaderApplier.apply(OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION,
            "http://runtime", "http://runtime/v1/agent-builder/chat/completions").accept(headers);

        assertThat(headers.getFirst("X-Request-Id")).isEqualTo("req-1");
        assertThat(headers.getFirst("TraceID")).isEqualTo("trace-1");
        assertThat(headers.getFirst("X-Execution-Id")).isNull();
    }

    @Test
    void runtimeExecution_threeHeaders() {
        fullMdc();
        HttpHeaders headers = new HttpHeaders();

        WebClientCorrelationHeaderApplier.apply(OutboundCorrelationPolicy.RUNTIME_EXECUTION,
            "http://runtime", "http://runtime/v1/agents/a/conversations/c").accept(headers);

        assertThat(headers.getFirst("X-Request-Id")).isEqualTo("req-1");
        assertThat(headers.getFirst("TraceID")).isEqualTo("trace-1");
        assertThat(headers.getFirst("X-Execution-Id")).isEqualTo("exec-1");
    }

    @Test
    void originMismatch_fails() {
        fullMdc();
        assertThatThrownBy(() -> WebClientCorrelationHeaderApplier.apply(OutboundCorrelationPolicy.BUILDER,
            "http://allowed", "http://evil/v1/x")).isInstanceOf(AgentStudioException.class);
    }

    @Test
    void missingContext_fails() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        // 无 trace
        assertThatThrownBy(() -> WebClientCorrelationHeaderApplier.apply(OutboundCorrelationPolicy.BUILDER,
            "http://builder", "http://builder/v1/x"))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class);
    }

    /** 值在 apply() 调用时从 MDC 读取并固化；之后改 MDC 不影响已返回的 Consumer。 */
    @Test
    void valuesCapturedAtApplyTime_immutableToLaterMdcChange() {
        fullMdc();
        HttpHeaders headers = new HttpHeaders();
        java.util.function.Consumer<HttpHeaders> consumer = WebClientCorrelationHeaderApplier.apply(
            OutboundCorrelationPolicy.BUILDER, "http://builder", "http://builder/v1/x");
        MDC.put(MdcKeys.REQUEST_ID, "changed");
        consumer.accept(headers);
        assertThat(headers.getFirst("X-Request-Id")).isEqualTo("req-1");
    }
}
