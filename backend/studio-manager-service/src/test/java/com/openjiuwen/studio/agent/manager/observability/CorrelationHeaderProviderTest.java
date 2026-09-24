/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-04 §10.1：Provider 单元测试——三种策略输出、必需值缺失明确失败、
 * 非执行/Builder 不输出 execution、不修改 MDC、覆盖算法（大小写不敏感先删后写）。
 */
class CorrelationHeaderProviderTest {

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    private void fullMdc() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
    }

    // ---- provide：三策略输出 ----

    @Test
    void runtimeExecution_completeMdc_outputsThreeHeaders() {
        fullMdc();
        CorrelationHeaders headers = CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        assertThat(headers.asMap()).isEqualTo(Map.of(
            "X-Request-Id", "req-1",
            "TraceID", "trace-1",
            "X-Execution-Id", "exec-1"));
    }

    @Test
    void runtimeNonExecution_outputsRequestTraceOnly() {
        fullMdc();
        CorrelationHeaders headers =
            CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION);
        assertThat(headers.asMap()).isEqualTo(Map.of(
            "X-Request-Id", "req-1",
            "TraceID", "trace-1"));
    }

    @Test
    void builder_outputsRequestTraceOnly_evenWithExecutionInMdc() {
        fullMdc();
        CorrelationHeaders headers = CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.BUILDER);
        assertThat(headers.asMap()).isEqualTo(Map.of(
            "X-Request-Id", "req-1",
            "TraceID", "trace-1"));
    }

    // ---- provide：必需值缺失明确失败 ----

    @Test
    void runtimeExecution_missingRequest_failsWithFieldNameOnly() {
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        assertThatThrownBy(() -> CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class)
            .hasMessageContaining("request-id")
            .hasMessageNotContaining("exec-1");
    }

    @Test
    void runtimeExecution_missingTrace_fails() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        assertThatThrownBy(() -> CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class)
            .hasMessageContaining("trace_id");
    }

    @Test
    void runtimeExecution_missingExecution_fails() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        assertThatThrownBy(() -> CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class)
            .hasMessageContaining("execution-id");
    }

    @Test
    void runtimeExecution_emptyExecution_treatedAsMissing() {
        // COM-05 入口 Filter 外层 scope 将 execution-id 显式置空——空串即缺失
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MDC.put(MdcKeys.EXECUTION_ID, "");
        assertThatThrownBy(() -> CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class);
    }

    @Test
    void runtimeNonExecution_missingRequest_fails() {
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        assertThatThrownBy(() ->
                CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class)
            .hasMessageContaining("request-id");
    }

    // ---- provide：不修改 MDC、不生成值 ----

    @Test
    void provide_doesNotModifyMdc() {
        fullMdc();
        CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION);
        CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.BUILDER);
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("req-1");
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("trace-1");
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("exec-1");
    }

    @Test
    void runtimeNonExecution_missingTrace_fails_noRequestFallback() {
        // Provider 只读 MDC：trace 缺失时不得用 request 回退（回退属 COM-05 入口选值规则）
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        assertThatThrownBy(() ->
                CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class)
            .hasMessageContaining("trace_id")
            .hasMessageNotContaining("req-1");
    }

    // ---- 覆盖算法：大小写不敏感先删后写 ----

    @Test
    void apply_removesCaseVariantsAndDuplicates_writesSingleAuthoritativeValue() {
        fullMdc();
        MapSink sink = new MapSink();
        sink.seed("x-request-id", "forged-1");
        sink.seed("X-REQUEST-ID", "forged-2");
        sink.seed("traceid", "forged-trace");
        sink.seed("X-Execution-Id", "forged-exec");
        sink.seed("Content-Type", "application/json");

        CorrelationHeaderProvider.apply(
            CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_EXECUTION), sink);

        assertThat(sink.countValues("X-Request-Id")).isEqualTo(1);
        assertThat(sink.getFirst("X-Request-Id")).isEqualTo("req-1");
        assertThat(sink.countValues("TraceID")).isEqualTo(1);
        assertThat(sink.getFirst("TraceID")).isEqualTo("trace-1");
        assertThat(sink.countValues("X-Execution-Id")).isEqualTo(1);
        assertThat(sink.getFirst("X-Execution-Id")).isEqualTo("exec-1");
        // 非关联 Header 不受影响
        assertThat(sink.getFirst("Content-Type")).isEqualTo("application/json");
    }

    @Test
    void apply_nonExecution_leavesExecutionAbsent_evenIfSinkHadIt() {
        fullMdc();
        MapSink sink = new MapSink();
        sink.seed("X-Execution-Id", "residue-exec");

        CorrelationHeaderProvider.apply(
            CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.RUNTIME_NON_EXECUTION), sink);

        assertThat(sink.countValues("X-Execution-Id")).isZero();
        assertThat(sink.getFirst("X-Request-Id")).isEqualTo("req-1");
    }

    @Test
    void apply_builder_neverWritesExecution() {
        fullMdc();
        MapSink sink = new MapSink();

        CorrelationHeaderProvider.apply(CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.BUILDER), sink);

        assertThat(sink.countValues("X-Execution-Id")).isZero();
        assertThat(sink.getFirst("TraceID")).isEqualTo("trace-1");
    }

    // ---- 不可变返回 ----

    @Test
    void correlationHeaders_immutable_sourceMutationDoesNotLeak() {
        Map<String, String> source = new LinkedHashMap<>();
        source.put("X-Request-Id", "req-1");
        CorrelationHeaders headers = CorrelationHeaders.of(source);
        source.put("TraceID", "mutated");
        assertThat(headers.asMap()).doesNotContainKey("TraceID");
        assertThatThrownBy(() -> headers.asMap().put("TraceID", "x"))
            .isInstanceOf(UnsupportedOperationException.class);
    }

    // ---- 测试用 Sink ----

    /** 多值 Map Sink：支持大小写变体播种与大小写不敏感计数。 */
    static final class MapSink implements CorrelationHeaderProvider.CorrelationHeaderSink {
        private final LinkedHashMap<String, List<String>> headers = new LinkedHashMap<>();

        void seed(String name, String value) {
            headers.computeIfAbsent(name, k -> new ArrayList<>()).add(value);
        }

        @Override
        public Set<String> headerNames() {
            return headers.keySet();
        }

        @Override
        public void removeHeader(String name) {
            headers.remove(name);
        }

        @Override
        public void setHeader(String name, String value) {
            headers.put(name, new ArrayList<>(List.of(value)));
        }

        int countValues(String name) {
            return headers.entrySet().stream()
                .filter(e -> e.getKey().equalsIgnoreCase(name))
                .mapToInt(e -> e.getValue().size()).sum();
        }

        String getFirst(String name) {
            return headers.entrySet().stream()
                .filter(e -> e.getKey().equalsIgnoreCase(name))
                .findFirst().map(e -> e.getValue().get(0)).orElse(null);
        }
    }
}
