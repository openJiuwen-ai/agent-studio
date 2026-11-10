/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * 异步工作流出站 RUNTIME_EXECUTION 前补齐 request-id/trace_id 的回归：
 * 无 HTTP Filter MDC 时不得再抛 missing correlation context。
 */
class AsyncCorrelationIdsTest {

    @BeforeEach
    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    @Test
    void resolve_emptyMdcAndHeaders_generatesValidPair() {
        AsyncCorrelationIds.Pair pair = AsyncCorrelationIds.resolve(null);
        assertThat(CorrelationIdValidator.isValid(pair.requestId())).isTrue();
        assertThat(CorrelationIdValidator.isValid(pair.traceId())).isTrue();
        assertThat(pair.traceId()).isEqualTo(pair.requestId());
    }

    @Test
    void resolve_prefersValidHeaders_whenMdcAbsent() {
        HttpHeaders headers = new HttpHeaders();
        headers.add(CorrelationContextFilter.REQUEST_ID_HEADER, "hdr-req-1");
        headers.add(CorrelationContextFilter.TRACE_ID_HEADER, "hdr-trace-1");
        AsyncCorrelationIds.Pair pair = AsyncCorrelationIds.resolve(headers);
        assertThat(pair.requestId()).isEqualTo("hdr-req-1");
        assertThat(pair.traceId()).isEqualTo("hdr-trace-1");
    }

    @Test
    void resolve_prefersHeaders_overStaleMdc() {
        // 线程池残留 MDC 不得盖住 Redis 缓存的本任务 Header
        MDC.put(MdcKeys.REQUEST_ID, "mdc-req");
        MDC.put(MdcKeys.TRACE_ID, "mdc-trace");
        HttpHeaders headers = new HttpHeaders();
        headers.add(CorrelationContextFilter.REQUEST_ID_HEADER, "hdr-req");
        headers.add(CorrelationContextFilter.TRACE_ID_HEADER, "hdr-trace");
        AsyncCorrelationIds.Pair pair = AsyncCorrelationIds.resolve(headers);
        assertThat(pair.requestId()).isEqualTo("hdr-req");
        assertThat(pair.traceId()).isEqualTo("hdr-trace");
    }

    @Test
    void resolve_fallsBackToMdc_whenHeadersAbsent() {
        MDC.put(MdcKeys.REQUEST_ID, "mdc-req");
        MDC.put(MdcKeys.TRACE_ID, "mdc-trace");
        AsyncCorrelationIds.Pair pair = AsyncCorrelationIds.resolve(null);
        assertThat(pair.requestId()).isEqualTo("mdc-req");
        assertThat(pair.traceId()).isEqualTo("mdc-trace");
    }

    @Test
    void runtimeExecution_afterAsyncBootstrap_doesNotThrowMissingContext() {
        // 异步线程仅有 execution-id 时 provide 会缺 request-id,trace_id
        MDC.clear();
        AsyncCorrelationIds.Pair pair = AsyncCorrelationIds.resolve(null);
        String executionId = "async-exec-1";
        try (MdcScope correlation = MdcScope.open(Map.of(
                MdcKeys.REQUEST_ID, pair.requestId(),
                MdcKeys.TRACE_ID, pair.traceId()));
             MdcScope execution = MdcScope.open(Map.of(MdcKeys.EXECUTION_ID, executionId))) {
            assertThatCode(() ->
                CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION))
                .doesNotThrowAnyException();
            CorrelationHeaders headers =
                CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION);
            assertThat(headers.asMap()).containsEntry("X-Request-Id", pair.requestId())
                .containsEntry("TraceID", pair.traceId())
                .containsEntry("X-Execution-Id", executionId);
        }
    }

    @Test
    void runtimeExecution_onlyExecutionId_stillFailsWithoutBootstrap() {
        // 对照：仅补 execution-id（修复前 callWorkflowViaStream 行为）仍失败
        MDC.clear();
        try (MdcScope execution = MdcScope.open(Map.of(MdcKeys.EXECUTION_ID, "async-exec-1"))) {
            org.assertj.core.api.Assertions.assertThatThrownBy(() ->
                    CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION))
                .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class)
                .hasMessageContaining("request-id")
                .hasMessageContaining("trace_id");
        }
    }
}
