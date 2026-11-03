/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.error;

import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

/**
 * COM-03 §10.1: ErrorDescriptor 不变量测试。
 */
class ErrorDescriptorTest {

    private static final String CODE = "openjiuwen.02001129";
    private static final String MSG_KEY = "openjiuwen.02001129";
    private static final String REASON_KEY = "openjiuwen.02001129.reason";
    private static final String SUGGESTION_KEY = "openjiuwen.02001129.suggestion";
    private static final String REQ_ID = "req-abc-123";
    private static final Throwable CAUSE = new IllegalStateException("boom");
    private static final ErrorDetail VALID_DETAIL = new ErrorDetail()
        .setErrorCode("test-fake-detail-code").setErrorMsg("Invalid parameter: name");

    @Test
    void allRequiredFieldsPresent_constructsSuccessfully() {
        ErrorDescriptor d = base();
        assertEquals(CODE, d.getErrorCode());
        assertEquals(404, d.getHttpStatus());
        assertEquals(MSG_KEY, d.getMessageKey());
        assertEquals(REASON_KEY, d.getReasonKey());
        assertEquals(SUGGESTION_KEY, d.getSuggestionKey());
        assertEquals(REQ_ID, d.getRequestId());
    }

    @Test
    void blankErrorCode_rejected() {
        assertThrows(IllegalArgumentException.class, () ->
            new ErrorDescriptor("  ", 404, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
                REQ_ID, null, null, null, CAUSE));
    }

    @Test
    void httpStatusOutsideRange_rejected() {
        assertThrows(IllegalArgumentException.class, () -> base(200));
        assertThrows(IllegalArgumentException.class, () -> base(600));
    }

    @Test
    void blankRequestId_rejected() {
        assertThrows(IllegalArgumentException.class, () ->
            new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY, SUGGESTION_KEY, "",
                null, null, null, CAUSE));
    }

    @Test
    void downstreamServiceWithoutCode_accepted() {
        // 基础契约 §5：传输失败等无原码场景允许只记录 downstreamService。
        ErrorDescriptor d = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.RUNTIME, null, CAUSE);
        assertEquals(DownstreamService.RUNTIME, d.getDownstreamServiceInternal());
    }

    @Test
    void downstreamCodeWithoutService_rejected() {
        assertThrows(IllegalArgumentException.class, () ->
            new ErrorDescriptor(CODE, 500, MSG_KEY, REASON_KEY, SUGGESTION_KEY, REQ_ID,
                null, null, "test-fake-rt-code", CAUSE));
    }

    @Test
    void downstreamPaired_accepted() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.BUILDER,
            "test-fake-bld-code", CAUSE);
        assertEquals(DownstreamService.BUILDER, d.getDownstreamServiceInternal());
        assertEquals("test-fake-bld-code", d.getDownstreamErrorCodeInternal());
    }

    @Test
    void causeNotInToString() {
        ErrorDescriptor d = baseWithCause(CAUSE);
        String repr = d.toString();
        assertFalse(repr.contains("boom"), "toString must not contain cause message");
        assertFalse(repr.contains("IllegalStateException"),
            "toString must not contain cause type");
    }

    @Test
    void causeNotInEqualsOrHashCode() {
        ErrorDescriptor d1 = baseWithCause(CAUSE);
        ErrorDescriptor d2 = baseWithCause(new RuntimeException("different"));
        assertEquals(d1, d2, "descriptors with same safe fields but different cause must be equal");
        assertEquals(d1.hashCode(), d2.hashCode());
    }

    @Test
    void downstreamNotInEqualsOrToString() {
        ErrorDescriptor d1 = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.BUILDER,
            "test-fake-bld-code", null);
        ErrorDescriptor d2 = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.EXTERNAL,
            "test-fake-downstream-99999", null);
        assertEquals(d1, d2, "different downstream fields but same safe fields must be equal");
        assertFalse(d1.toString().contains("BUILDER"), "toString must not contain downstream");
        assertFalse(d1.toString().contains("downstream"), "toString must not contain downstream");
    }

    @Test
    void safeDetailsNull_omitted() {
        ErrorDescriptor d = base();
        assertNull(d.getSafeDetails());
    }

    @Test
    void safeDetailsEmpty_accepted() {
        ErrorDescriptor d = baseWithDetails(List.of());
        assertTrue(d.getSafeDetails().isEmpty());
    }

    @Test
    void safeDetailsValid_accepted() {
        ErrorDescriptor d = baseWithDetails(List.of(VALID_DETAIL));
        assertEquals(1, d.getSafeDetails().size());
        assertEquals("test-fake-detail-code", d.getSafeDetails().get(0).getErrorCode());
    }

    @Test
    void safeDetailsWithBlankErrorCode_rejected() {
        ErrorDetail bad = new ErrorDetail().setErrorCode("  ").setErrorMsg("msg");
        assertThrows(IllegalArgumentException.class, () -> baseWithDetails(List.of(bad)));
    }

    @Test
    void safeDetailsWithBlankErrorMsg_rejected() {
        ErrorDetail bad = new ErrorDetail().setErrorCode("test-fake-detail-code").setErrorMsg("");
        assertThrows(IllegalArgumentException.class, () -> baseWithDetails(List.of(bad)));
    }

    @Test
    void safeDetailsImmutable() {
        ErrorDescriptor d = baseWithDetails(List.of(VALID_DETAIL));
        assertThrows(UnsupportedOperationException.class,
            () -> d.getSafeDetails().add(VALID_DETAIL));
    }

    @Test
    void modifyingOriginalListDoesNotAffectDescriptor() {
        ErrorDetail original = new ErrorDetail().setErrorCode("orig-code").setErrorMsg("orig-msg");
        java.util.List<ErrorDetail> list = new java.util.ArrayList<>(List.of(original));
        ErrorDescriptor d = baseWithDetails(list);
        list.add(new ErrorDetail().setErrorCode("new").setErrorMsg("new"));
        assertEquals(1, d.getSafeDetails().size(), "original list modification must not affect descriptor");
    }

    @Test
    void modifyingOriginalErrorDetailDoesNotAffectDescriptor() {
        ErrorDetail original = new ErrorDetail().setErrorCode("orig-code").setErrorMsg("orig-msg");
        ErrorDescriptor d = baseWithDetails(List.of(original));
        original.setErrorCode("modified");
        assertEquals("orig-code", d.getSafeDetails().get(0).getErrorCode(),
            "original ErrorDetail modification must not affect descriptor");
    }

    @Test
    void modifyingGetterReturnedElementDoesNotAffectDescriptor() {
        ErrorDescriptor d = baseWithDetails(List.of(VALID_DETAIL));
        // getter returns defensive copy — modifying it should not affect descriptor
        ErrorDetail got = d.getSafeDetails().get(0);
        got.setErrorCode("hacked");
        // get a fresh copy and verify original value intact
        assertEquals("test-fake-detail-code", d.getSafeDetails().get(0).getErrorCode(),
            "modifying getter-returned element must not affect descriptor");
    }

    // ---- helpers ----

    private static ErrorDescriptor base() {
        return new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
            REQ_ID, null, null, null, null);
    }

    private static ErrorDescriptor baseWithCause(Throwable cause) {
        return new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
            REQ_ID, null, null, null, cause);
    }

    private static ErrorDescriptor baseWithDetails(List<ErrorDetail> details) {
        return new ErrorDescriptor(CODE, 404, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
            REQ_ID, details, null, null, null);
    }

    private static ErrorDescriptor base(int httpStatus) {
        return new ErrorDescriptor(CODE, httpStatus, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
            REQ_ID, null, null, null, CAUSE);
    }
}
