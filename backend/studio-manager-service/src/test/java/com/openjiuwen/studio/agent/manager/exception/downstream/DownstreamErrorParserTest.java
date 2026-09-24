/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * COM-04 §9.1: Parser 参数化测试。
 */
class DownstreamErrorParserTest {

    private DownstreamErrorParser parser;

    @BeforeEach
    void setUp() {
        parser = new DownstreamErrorParser(new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
    }

    private static byte[] body(String json) {
        return json.getBytes(StandardCharsets.UTF_8);
    }

    // ---- 标准五字段 + 八码 ----

    @ParameterizedTest
    @ValueSource(strings = {
        "openjiuwen.13100006", "openjiuwen.13100007", "openjiuwen.13100008",
        "openjiuwen.13100009", "openjiuwen.13100010", "openjiuwen.13100011",
        "openjiuwen.13100012", "openjiuwen.13100013"
    })
    void parseHttp_extracts_trusted_canonical_code(String code) {
        byte[] body = body("{\"error_code\":\"" + code + "\",\"error_msg\":\"x\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, "application/json", body, new RuntimeException("cause"));
        assertEquals(code, f.getDownstreamErrorCode());
        assertEquals(DownstreamService.BUILDER, f.getService());
        assertEquals(Transport.CLIENT_TEMPLATE, f.getTransport());
        assertEquals(400, f.getDownstreamHttpStatus());
        assertEquals(FailurePhase.HTTP_RESPONSE, f.getPhase());
        assertTrue(f.hasTrustedErrorCode());
    }

    @Test
    void parseHttp_extra_unknown_fields_and_field_order_tolerated() {
        byte[] body = body("{\"error_msg\":\"x\",\"error_code\":\"openjiuwen.13100007\",\"extra\":42}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.WEBCLIENT,
            404, null, body, null);
        assertEquals("openjiuwen.13100007", f.getDownstreamErrorCode());
    }

    // ---- 无可信原码的各类情况 ----

    @ParameterizedTest
    @ValueSource(strings = {
        "", "   ", "<html>not json</html>", "[]", "[1,2]", "42", "true", "null",
        "{\"error_msg\":\"no code\"}", "{\"error_code\":123}",
        "{\"error_code\":true}", "{\"error_code\":{\"x\":1}}", "{\"error_code\":[\"x\"]}",
        "{\"error_code\":\"\"}", "{\"error_code\":\"   \"}",
        "not json at all", "{broken"
    })
    void parseHttp_unparseable_yields_no_trusted_code(String badBody) {
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.FEIGN,
            500, "text/html", body(badBody), null);
        assertNull(f.getDownstreamErrorCode());
        assertTrue(!f.hasTrustedErrorCode());
    }

    @Test
    void parseHttp_null_body_no_code() {
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.OKHTTP_SSE,
            502, null, null, null);
        assertNull(f.getDownstreamErrorCode());
    }

    @Test
    void parseHttp_unknown_canonical_not_trusted() {
        // valid canonical8 format but not a registered Builder code
        byte[] body = body("{\"error_code\":\"openjiuwen.13100099\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            500, null, body, null);
        assertNull(f.getDownstreamErrorCode());
    }

    @Test
    void parseHttp_legacy_integer_not_trusted() {
        // DEF-06 legacy input 102154 is NOT a canonical code Manager trusts
        byte[] body = body("{\"error_code\":\"102154\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, null, body, null);
        assertNull(f.getDownstreamErrorCode());
    }

    @Test
    void parseHttp_no_prefix_fuzzy_match() {
        // must NOT add openjiuwen. prefix or normalize
        byte[] body = body("{\"error_code\":\"13100006\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, null, body, null);
        assertNull(f.getDownstreamErrorCode());
    }

    @Test
    void parseHttp_case_change_not_trusted() {
        byte[] body = body("{\"error_code\":\"OPENJIUWEN.13100006\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, null, body, null);
        assertNull(f.getDownstreamErrorCode());
    }

    // ---- body 上限 ----

    @Test
    void parseHttp_body_at_limit_parsed() {
        StringBuilder sb = new StringBuilder("{\"error_code\":\"openjiuwen.13100006\",\"x\":\"");
        int pad = DownstreamErrorParser.MAX_BODY_BYTES - sb.length() - 2;
        sb.append("a".repeat(Math.max(0, pad))).append("\"}");
        byte[] body = sb.toString().getBytes(StandardCharsets.UTF_8);
        // body length may slightly exceed due to exact; truncate to exact limit
        byte[] bounded = new byte[DownstreamErrorParser.MAX_BODY_BYTES];
        System.arraycopy(body, 0, bounded, 0, Math.min(body.length, bounded.length));
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, null, bounded, null);
        // at-or-under limit → parse attempted; code present if body valid
        // (we only assert no crash + phase)
        assertEquals(FailurePhase.HTTP_RESPONSE, f.getPhase());
    }

    @Test
    void parseHttp_body_over_limit_no_code() {
        byte[] body = new byte[DownstreamErrorParser.MAX_BODY_BYTES + 1];
        // fill with valid-json-looking bytes (won't matter; over-limit short-circuits)
        java.util.Arrays.fill(body, (byte) ' ');
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            500, null, body, null);
        assertNull(f.getDownstreamErrorCode());
    }

    // ---- Runtime 不识别（初始）----

    @Test
    void parseHttp_runtime_code_not_trusted_initially() {
        byte[] body = body("{\"error_code\":\"openjiuwen.121007\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.RUNTIME, Transport.OKHTTP_SSE,
            500, null, body, null);
        assertNull(f.getDownstreamErrorCode());
        assertEquals(DownstreamService.RUNTIME, f.getService());
    }

    // ---- SSE ----

    @Test
    void parseSseError_error_event_extracts_code() {
        byte[] data = body("{\"error_code\":\"openjiuwen.13100009\"}");
        var opt = parser.parseSseError(DownstreamService.BUILDER, Transport.WEBCLIENT,
            "error", data, null);
        assertTrue(opt.isPresent());
        DownstreamFailure f = opt.get();
        assertEquals("openjiuwen.13100009", f.getDownstreamErrorCode());
        assertEquals(FailurePhase.SSE_EVENT, f.getPhase());
    }

    @ParameterizedTest
    @ValueSource(strings = {"message", "done", "data", ""})
    void parseSseError_non_error_event_empty_not_failure(String eventName) {
        // 非 error event 不构成失败事实——返回 empty，调用方不得交给 mapper
        byte[] data = body("{\"error_code\":\"openjiuwen.13100009\"}");
        var opt = parser.parseSseError(DownstreamService.BUILDER, Transport.WEBCLIENT,
            eventName, data, null);
        assertTrue(opt.isEmpty(), "non-error event must not produce a DownstreamFailure");
    }

    @Test
    void parseSseError_plain_message_with_error_code_not_misjudged() {
        // a "message" event whose data happens to contain error_code must NOT be treated as error
        byte[] data = body("{\"error_code\":\"openjiuwen.13100009\"}");
        var opt = parser.parseSseError(DownstreamService.BUILDER, Transport.WEBCLIENT,
            "message", data, null);
        assertTrue(opt.isEmpty());
    }

    // ---- 损坏 UTF-8 严格拒绝 ----

    @Test
    void parseHttp_invalid_utf8_in_other_field_no_trusted_code() {
        // 顶层 canonical 码合法，但另一字符串字段含非法 UTF-8 字节 → 一律无可信原码
        byte[] validPart = "{\"error_code\":\"openjiuwen.13100006\",\"other\":\"".getBytes(StandardCharsets.UTF_8);
        byte[] invalidByte = {(byte) 0xFF, (byte) 0xFE, (byte) 0xC0};
        byte[] tail = "\"}".getBytes(StandardCharsets.UTF_8);
        byte[] badBody = new byte[validPart.length + invalidByte.length + tail.length];
        System.arraycopy(validPart, 0, badBody, 0, validPart.length);
        System.arraycopy(invalidByte, 0, badBody, validPart.length, invalidByte.length);
        System.arraycopy(tail, 0, badBody, validPart.length + invalidByte.length, tail.length);
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, null, badBody, null);
        assertNull(f.getDownstreamErrorCode(), "corrupt UTF-8 anywhere must yield no trusted code");
    }

    // ---- DownstreamFailureException 空值检查 ----

    @Test
    void failureException_null_fails_with_illegal_argument() {
        org.junit.jupiter.api.Assertions.assertThrows(IllegalArgumentException.class,
            () -> new DownstreamFailureException(null));
    }

    // ---- transport failure ----

    @Test
    void fromTransportFailure_no_code() {
        DownstreamFailure f = parser.fromTransportFailure(DownstreamService.RUNTIME,
            Transport.OKHTTP_SSE, new RuntimeException("connect refused"));
        assertNull(f.getDownstreamErrorCode());
        assertEquals(FailurePhase.TRANSPORT, f.getPhase());
        assertEquals(DownstreamService.RUNTIME, f.getService());
    }

    // ---- parser 不泄漏 body ----

    @Test
    void parseHttp_failure_repr_excludes_body() {
        byte[] body = body("{\"error_code\":\"openjiuwen.13100006\",\"secret\":\"leak-me\"}");
        DownstreamFailure f = parser.parseHttp(DownstreamService.BUILDER, Transport.CLIENT_TEMPLATE,
            400, null, body, null);
        assertTrue(!f.toString().contains("leak-me"));
        assertTrue(!f.toString().contains("secret"));
    }
}
