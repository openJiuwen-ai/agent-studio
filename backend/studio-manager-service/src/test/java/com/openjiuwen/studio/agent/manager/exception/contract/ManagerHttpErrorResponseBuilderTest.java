/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Locale;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * COM-03 §10.2: Manager HTTP builder 契约测试。
 */
class ManagerHttpErrorResponseBuilderTest {

    private static final String CODE = "openjiuwen.02001129";
    private static final String MSG_KEY = "openjiuwen.02001129";
    private static final String REASON_KEY = "openjiuwen.02001129.reason";
    private static final String SUGGESTION_KEY = "openjiuwen.02001129.suggestion";
    private static final String REQ_ID = "req-test-001";

    // Simple resolver: returns key + "::resolved" for any key
    private final ManagerHttpErrorResponseBuilder.I18nResolver resolver =
        (key, locale) -> key + "::resolved";

    private final ManagerHttpErrorResponseBuilder builder =
        new ManagerHttpErrorResponseBuilder(resolver);

    private ErrorDescriptor descriptor() {
        return new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, null);
    }

    @Test
    void fiveFieldsNonEmptyStrings() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        ErrorRsp body = resp.getBody();
        assertNotNull(body);
        assertEquals(CODE, body.getErrorCode());
        assertEquals(MSG_KEY + "::resolved", body.getErrorMsg());
        assertEquals(REASON_KEY + "::resolved", body.getErrorReason());
        assertEquals(SUGGESTION_KEY + "::resolved", body.getErrorSuggestion());
        assertEquals(REQ_ID, body.getRequestId());
    }

    @Test
    void bodyRequestIdEqualsHeader() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        ErrorRsp body = resp.getBody();
        assertNotNull(body);
        assertEquals(REQ_ID, body.getRequestId());
        assertEquals(REQ_ID, resp.getHeaders().getFirst("X-Request-Id"));
    }

    @Test
    void httpStatusFromDescriptor() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        assertEquals(404, resp.getStatusCode().value());
    }

    @Test
    void contentTypeJson() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        assertEquals("application/json", resp.getHeaders().getFirst("Content-Type"));
    }

    @Test
    void detailsOmittedWhenNull() {
        ResponseEntity<ErrorRsp> resp = builder.build(descriptor(), Locale.CHINA);
        assertNull(resp.getBody().getDetails());
    }

    @Test
    void detailsPresentWhenNonEmpty() {
        ErrorDetail detail = new ErrorDetail()
            .setErrorCode("test-fake-detail-code").setErrorMsg("Invalid field");
        ErrorDescriptor d = new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, List.of(detail), null, null, null);
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        assertNotNull(resp.getBody().getDetails());
        assertEquals(1, resp.getBody().getDetails().size());
        assertEquals("test-fake-detail-code", resp.getBody().getDetails().get(0).getErrorCode());
    }

    @Test
    void causeNotInBody() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, new IllegalStateException("secret"));
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        String bodyStr = resp.getBody().toString();
        assertFalse(bodyStr.contains("secret"), "cause message must not appear in body");
    }

    @Test
    void downstreamNotInBody() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.BUILDER,
            "test-fake-code", null);
        ResponseEntity<ErrorRsp> resp = builder.build(d, Locale.CHINA);
        String bodyStr = resp.getBody().toString();
        assertFalse(bodyStr.contains("BUILDER"), "downstream must not appear in body");
        assertFalse(bodyStr.contains("downstream"), "downstream must not appear in body");
    }

    @Test
    void differentStatusProducesCorrectHttpStatus() {
        ErrorDescriptor d500 = new ErrorDescriptor(CODE, 500, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, null);
        ResponseEntity<ErrorRsp> resp = builder.build(d500, Locale.CHINA);
        assertEquals(500, resp.getStatusCode().value());
    }
}
