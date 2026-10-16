/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import org.junit.jupiter.api.Test;

import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * COM-03 §10.3: Manager SSE builder + terminal guard 契约测试。
 */
class ManagerSseErrorEventBuilderTest {

    private static final String CODE = "openjiuwen.02001129";
    private static final String MSG_KEY = "openjiuwen.02001129";
    private static final String REASON_KEY = "openjiuwen.02001129.reason";
    private static final String SUGGESTION_KEY = "openjiuwen.02001129.suggestion";
    private static final String REQ_ID = "req-sse-001";

    private final ManagerHttpErrorResponseBuilder.I18nResolver resolver =
        (key, locale) -> key + "::resolved";

    private final ManagerSseErrorEventBuilder sseBuilder =
        new ManagerSseErrorEventBuilder(resolver);

    private ErrorDescriptor descriptor() {
        return new ErrorDescriptor(CODE, 500, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, null);
    }

    // ---- SSE envelope ----

    @Test
    void envelopeHasEventError() {
        Map<String, Object> env = sseBuilder.buildEnvelope(descriptor(), Locale.CHINA);
        assertEquals("error", env.get("event"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void envelopeDataHasFiveFields() {
        Map<String, Object> env = sseBuilder.buildEnvelope(descriptor(), Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals(CODE, data.get("error_code"));
        assertEquals(MSG_KEY + "::resolved", data.get("error_msg"));
        assertEquals(REASON_KEY + "::resolved", data.get("error_reason"));
        assertEquals(SUGGESTION_KEY + "::resolved", data.get("error_suggestion"));
        assertEquals(REQ_ID, data.get("request_id"));
    }

    @Test
    void envelopeExcludesCauseAndDownstream() {
        ErrorDescriptor d = new ErrorDescriptor(CODE, 502, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, DownstreamService.BUILDER,
            "test-fake-code", new IllegalStateException("secret"));
        Map<String, Object> env = sseBuilder.buildEnvelope(d, Locale.CHINA);
        String envStr = env.toString();
        assertFalse(envStr.contains("secret"), "cause must not appear in envelope");
        assertFalse(envStr.contains("downstream"), "downstream must not appear in envelope");
    }

    @Test
    void formatSseEventHasDataPrefix() {
        String wire = sseBuilder.formatSseEvent(descriptor(), Locale.CHINA);
        assertTrue(wire.startsWith("data: "), "SSE event must start with 'data: '");
        assertTrue(wire.endsWith("\n\n"), "SSE event must end with \\n\\n");
        assertTrue(wire.contains("\"event\":\"error\""));
    }

    // ---- Terminal guard ----

    @Test
    void guardInitialNotStarted() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertEquals(SseTerminalGuard.State.NOT_STARTED, g.getState());
    }

    @Test
    void guardNotStartedShouldNotSendError() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertFalse(g.trySendError());
    }

    @Test
    void guardBeginStreaming() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.beginStreaming());
        assertEquals(SseTerminalGuard.State.STREAMING, g.getState());
    }

    @Test
    void guardBeginStreamingOnlyOnce() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.beginStreaming());
        assertFalse(g.beginStreaming());
    }

    @Test
    void guardTrySendErrorTerminates() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        assertTrue(g.allowMessage());
        assertTrue(g.trySendError());
        assertEquals(SseTerminalGuard.State.TERMINATED, g.getState());
        assertFalse(g.trySendError());
        assertFalse(g.allowMessage());
    }

    @Test
    void guardCancelPreventsError() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        g.cancel();
        assertEquals(SseTerminalGuard.State.CANCELLED, g.getState());
        assertFalse(g.trySendError());
    }

    @Test
    void guardCancelAfterErrorStaysTerminated() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        g.trySendError();
        g.cancel();
        assertEquals(SseTerminalGuard.State.TERMINATED, g.getState());
    }

    @Test
    void guardOnlyOneError() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        assertTrue(g.trySendError());
        assertFalse(g.trySendError());
    }
}
