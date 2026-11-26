/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * issue 1754：上游 OTel 头抓取与 SSE 帧补齐。
 */
class UpstreamOtelHeadersTest {

    private static final String TID = "a".repeat(32);

    private static Map<String, String> headers(String traceId, String traceResponse) {
        Map<String, String> map = new LinkedHashMap<>();
        if (traceId != null) {
            map.put(UpstreamOtelHeaders.X_OTEL_TRACE_ID, traceId);
        }
        if (traceResponse != null) {
            map.put(UpstreamOtelHeaders.TRACERESPONSE, traceResponse);
        }
        return map;
    }

    @Test
    void decorateFrame_appendsFieldsKeepingOriginalContent() {
        String data = "{\"event\":\"done\",\"data\":{\"text\":\"x\"}}";
        String out = UpstreamOtelHeaders.decorateFrame(data,
            headers(TID, "00-" + TID + "-" + "b".repeat(16) + "-01"));

        assertThat(out).startsWith("{\"event\":\"done\",\"data\":{\"text\":\"x\"}");
        assertThat(out).contains("\"otel_trace_id\":\"" + TID + "\"");
        assertThat(out).contains("\"otel_span_id\":\"" + "b".repeat(16) + "\"");
        assertThat(out.endsWith("}")).isTrue();
    }

    @Test
    void decorateFrame_keepsExistingOtelFields() {
        String data = "{\"event\":\"done\",\"otel_trace_id\":\"keep\"}";
        assertThat(UpstreamOtelHeaders.decorateFrame(data, headers(TID, null))).isEqualTo(data);
    }

    @Test
    void decorateFrame_emptyObjectStaysJsonValid() {
        String out = UpstreamOtelHeaders.decorateFrame("{}", headers(TID, null));
        assertThat(out).isEqualTo("{\"otel_trace_id\":\"" + TID + "\"}");
    }

    @Test
    void decorateFrame_nonJsonPassThrough() {
        assertThat(UpstreamOtelHeaders.decorateFrame("plain text", headers(TID, null))).isEqualTo("plain text");
        assertThat(UpstreamOtelHeaders.decorateFrame("[1,2]", headers(TID, null))).isEqualTo("[1,2]");
        assertThat(UpstreamOtelHeaders.decorateFrame(null, headers(TID, null))).isNull();
    }

    @Test
    void decorateFrame_withoutUpstreamTraceIsNoOp() {
        String data = "{\"event\":\"done\"}";
        assertThat(UpstreamOtelHeaders.decorateFrame(data, Map.of())).isEqualTo(data);
    }

    @Test
    void spanIdOf_parsesW3cFormat() {
        String span = "0123456789abcdef";
        assertThat(UpstreamOtelHeaders.spanIdOf("00-" + TID + "-" + span + "-01")).isEqualTo(span);
        assertThat(UpstreamOtelHeaders.spanIdOf("bad")).isEmpty();
        assertThat(UpstreamOtelHeaders.spanIdOf("00-" + TID + "-c0ffee-01")).isEmpty();
        assertThat(UpstreamOtelHeaders.spanIdOf(null)).isEmpty();
    }

    @Test
    void capture_rejectsMalformedTraceId() {
        // 检视意见：伪造/注入头必须丢弃（不进入响应头与帧）
        Map<String, String> captured = UpstreamOtelHeaders.capture(
            stubResponse("x\",\"injected\":\"y", null));
        assertThat(captured).isEmpty();
    }

    @Test
    void capture_rejectsMismatchedTraceResponse() {
        Map<String, String> captured = UpstreamOtelHeaders.capture(
            stubResponse(TID, "00-" + "c".repeat(32) + "-" + "b".repeat(16) + "-01"));
        assertThat(captured).containsOnlyKeys(UpstreamOtelHeaders.X_OTEL_TRACE_ID);
    }

    @Test
    void decorateFrame_ignoresIllegalTraceId() {
        String data = "{\"event\":\"done\"}";
        assertThat(UpstreamOtelHeaders.decorateFrame(data, headers("bad-trace", null)))
            .isEqualTo(data);
    }

    @Test
    void sanitize_keepsConsistentPair() {
        String traceResponse = "00-" + TID + "-" + "b".repeat(16) + "-01";
        assertThat(UpstreamOtelHeaders.sanitize(headers(TID, traceResponse)))
            .containsOnlyKeys(UpstreamOtelHeaders.X_OTEL_TRACE_ID, UpstreamOtelHeaders.TRACERESPONSE);
    }

    @Test
    void sanitize_dropsIllegalTraceIdButKeepsValidTraceResponse() {
        String traceResponse = "00-" + "c".repeat(32) + "-" + "b".repeat(16) + "-01";
        assertThat(UpstreamOtelHeaders.sanitize(headers("x\",\"injected\":\"y", traceResponse)))
            .containsOnlyKeys(UpstreamOtelHeaders.TRACERESPONSE);
    }

    @Test
    void sanitize_dropsMismatchedTraceResponse() {
        String mismatched = "00-" + "c".repeat(32) + "-" + "b".repeat(16) + "-01";
        assertThat(UpstreamOtelHeaders.sanitize(headers(TID, mismatched)))
            .containsOnlyKeys(UpstreamOtelHeaders.X_OTEL_TRACE_ID);
    }

    @Test
    void sanitize_handlesHalfPairAndEmptyInput() {
        String traceResponse = "00-" + TID + "-" + "b".repeat(16) + "-01";
        assertThat(UpstreamOtelHeaders.sanitize(headers(null, traceResponse)))
            .containsOnlyKeys(UpstreamOtelHeaders.TRACERESPONSE);
        assertThat(UpstreamOtelHeaders.sanitize(null)).isEmpty();
        assertThat(UpstreamOtelHeaders.sanitize(Map.of())).isEmpty();
    }

    @Test
    void sanitize_dropsMalformedTraceResponse() {
        String shortTraceId = "00-" + "c".repeat(16) + "-" + "b".repeat(16) + "-01";
        assertThat(UpstreamOtelHeaders.sanitize(headers(TID, shortTraceId)))
            .containsOnlyKeys(UpstreamOtelHeaders.X_OTEL_TRACE_ID);
        String upperCase = "00-" + TID.toUpperCase() + "-" + "b".repeat(16) + "-01";
        assertThat(UpstreamOtelHeaders.sanitize(headers(null, upperCase))).isEmpty();
    }

    @Test
    void sanitize_blankValuesYieldEmpty() {
        assertThat(UpstreamOtelHeaders.sanitize(headers("  ", "  "))).isEmpty();
    }

    private static okhttp3.Response stubResponse(String traceId, String traceResponse) {
        okhttp3.Response.Builder builder = new okhttp3.Response.Builder()
            .request(new okhttp3.Request.Builder().url("http://127.0.0.1/").build())
            .protocol(okhttp3.Protocol.HTTP_1_1)
            .code(200)
            .message("OK");
        if (traceId != null) {
            builder.header(UpstreamOtelHeaders.X_OTEL_TRACE_ID, traceId);
        }
        if (traceResponse != null) {
            builder.header(UpstreamOtelHeaders.TRACERESPONSE, traceResponse);
        }
        return builder.build();
    }
}
