/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * COM-03 §10.2.6 + 复审6 §3: SseTerminalGuard 原子状态机测试。
 */
class SseTerminalGuardStateTest {

    @Test
    void cancelBeforeOpen_blocksBeginStreaming() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.cancel();
        assertFalse(g.beginStreaming(), "beginStreaming must fail after cancel");
        assertEquals(SseTerminalGuard.State.CANCELLED, g.getState());
    }

    @Test
    void normalLifecycle() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.beginStreaming());
        assertEquals(SseTerminalGuard.State.STREAMING, g.getState());
        assertTrue(g.allowMessage());
        assertTrue(g.trySendError());
        assertEquals(SseTerminalGuard.State.TERMINATED, g.getState());
        assertFalse(g.allowMessage());
        assertFalse(g.trySendError(), "second trySendError must fail");
    }

    @Test
    void cancelAfterErrorStaysTerminated() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        g.trySendError();
        g.cancel();
        assertEquals(SseTerminalGuard.State.TERMINATED, g.getState());
    }

    @Test
    void notStarted_trySendError_fails() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertFalse(g.trySendError());
    }

    @Test
    void cancelAfterOpen_preventsError() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        g.cancel();
        assertFalse(g.trySendError());
        assertEquals(SseTerminalGuard.State.CANCELLED, g.getState());
    }

    // --- 复审6 §3: 新增 HTTP_FAILED 路径测试 ---

    @Test
    void tryHttpFailure_fromNotStarted_succeeds() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.tryHttpFailure(), "first tryHttpFailure must win");
        assertEquals(SseTerminalGuard.State.HTTP_FAILED, g.getState());
        assertTrue(g.isTerminal());
        assertFalse(g.allowMessage(), "no messages after HTTP_FAILED");
    }

    @Test
    void tryHttpFailure_afterBeginStreaming_fails() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.beginStreaming());
        assertFalse(g.tryHttpFailure(), "tryHttpFailure must fail after STREAMING");
        assertEquals(SseTerminalGuard.State.STREAMING, g.getState());
    }

    @Test
    void tryHttpFailure_duplicate_fails() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.tryHttpFailure());
        assertFalse(g.tryHttpFailure(), "second tryHttpFailure must fail");
        assertFalse(g.trySendError(), "trySendError must also fail (not STREAMING)");
    }

    @Test
    void tryHttpFailure_thenBeginStreaming_fails() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertTrue(g.tryHttpFailure());
        assertFalse(g.beginStreaming(), "beginStreaming must fail after HTTP_FAILED");
    }

    @Test
    void cancel_doesNotOverrideHttpFailed() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.tryHttpFailure();
        g.cancel();
        assertEquals(SseTerminalGuard.State.HTTP_FAILED, g.getState());
    }

    @Test
    void cancel_doesNotOverrideTerminated() {
        SseTerminalGuard g = new SseTerminalGuard();
        g.beginStreaming();
        g.trySendError();
        g.cancel();
        assertEquals(SseTerminalGuard.State.TERMINATED, g.getState());
    }

    @Test
    void isTerminal_falseForNotStartedAndStreaming() {
        SseTerminalGuard g = new SseTerminalGuard();
        assertFalse(g.isTerminal());
        g.beginStreaming();
        assertFalse(g.isTerminal());
    }
}
