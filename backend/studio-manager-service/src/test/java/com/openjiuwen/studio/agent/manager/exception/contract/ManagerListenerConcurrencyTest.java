/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.manager.exception.contract.ManagerHttpErrorResponseBuilder.I18nResolver;
import com.openjiuwen.studio.agent.manager.service.proxy.ProxyEventSourceListener;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.Test;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.LogRecord;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.*;

/**
 * COM-03 复审7 §3/§4 + 复审8 §4/§8: ProxyEventSourceListener 原子状态机、
 * latch 释放竞态、上游 EventSource 取消与唯一输出测试。
 */
class ManagerListenerConcurrencyTest {

    private static final String RID = "req-conc-001";

    private EventSource source() {
        return new EventSource() {
            @Override
            public @NotNull Request request() {
                return new Request.Builder().url("http://test").build();
            }

            @Override
            public void cancel() {
            }
        };
    }

    /** mock EventSource——统计 cancel() 次数。 */
    private EventSource mockSource() {
        return mock(EventSource.class);
    }

    private Response response(int code) {
        return new Response.Builder()
            .request(new Request.Builder().url("http://test").build())
            .protocol(okhttp3.Protocol.HTTP_1_1)
            .code(code)
            .message("test")
            .build();
    }

    /** mock SseEmitter——精确统计 send/complete 次数。 */
    private SseEmitter mockEmitter() {
        return mock(SseEmitter.class);
    }

    private I18nResolver validResolver() {
        return (key, loc) -> "msg:" + key;
    }

    // === P0(复审7 §3): HTTP_FAILED 后 onOpen 不得提前释放 latch ===
    // 复审8 §3.3: 用 enteredResolver 屏障替换 Thread.sleep——严格可重复。

    @Test
    void httpFailed_onOpen_doesNotReleaseLatch_beforeErrorRspComplete() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);

        // 屏障 1: resolver 已进入（替换 Thread.sleep 猜测）
        CountDownLatch enteredResolver = new CountDownLatch(1);
        // 屏障 2: 主线程放行 resolver（errorRsp 构建完成后释放 latch）
        CountDownLatch releaseResolver = new CountDownLatch(1);
        I18nResolver blockingResolver = (key, loc) -> {
            enteredResolver.countDown();
            try {
                releaseResolver.await();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            return "msg:" + key;
        };

        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, blockingResolver, java.util.Locale.ENGLISH);

        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            // Thread 1: onFailure → tryHttpFailure wins → createErrorRsp → resolver 进入并阻塞
            pool.submit(() -> listener.onFailure(source(),
                new RuntimeException("pre-frame"), response(502)));

            // 严格等待 onFailure 已进入 resolver（不再依赖时间猜测）
            assertTrue(enteredResolver.await(5, TimeUnit.SECONDS),
                "onFailure must have entered resolver");

            // Thread 2: onOpen → beginStreaming fails → 不 countDown
            pool.submit(() -> listener.onOpen(source(), response(200)));

            // 关键断言：latch 未释放——onOpen 没有提前 countDown
            assertFalse(latch.await(200, TimeUnit.MILLISECONDS),
                "latch must NOT be released while errorRsp is incomplete");

            // 释放 resolver → onFailure 继续 → errorRsp 赋值 → finally countDown
            releaseResolver.countDown();
            assertTrue(latch.await(5, TimeUnit.SECONDS),
                "latch must be released after errorRsp is complete");

            // errorRsp 已可见且非空
            assertNotNull(listener.getErrorRsp(),
                "errorRsp must be visible after latch release");
            assertEquals(502, listener.getErrorRsp().getStatusCode().value());

            pool.shutdown();
            assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS));
        } finally {
            if (!pool.isTerminated()) pool.shutdownNow();
        }
    }

    // === P1(复审7 §4): failure-before-open then onOpen ===

    @Test
    void failureBeforeOpen_thenOnOpen_errorRspUnique_noSseError() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        listener.onFailure(source(), new RuntimeException("pre-frame"), response(502));
        listener.onOpen(source(), response(200));

        assertNotNull(listener.getErrorRsp());
        assertEquals(502, listener.getErrorRsp().getStatusCode().value());
        // 首帧前路径不发送 SSE error
        verify(emitter, never()).send(anySet());
        // onFailure 主路径 complete 恰好一次
        verify(emitter, times(1)).complete();
    }

    // === P1(复审7 §4 + 复审8 §6): 并发 pre-frame failure →
    //     errorRsp 恰好一个 + 完整栈日志恰好一次 ===

    @Test
    void twoConcurrentPreFrameFailures_errorRspOne_fullStackLogOnce() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        // 捕获 listener 的 ERROR 级日志（完整原始栈恰好一次）
        // 项目日志框架为 log4j2——直接给 log4j2 logger config 加 appender
        // （不走 logback 强转，避免 SLF4J 双 provider 下 ClassCastException，检视意见2）
        List<LogRecord> errorRecords = new CopyOnWriteArrayList<>();
        org.apache.logging.log4j.core.LoggerContext log4j2Ctx =
            (org.apache.logging.log4j.core.LoggerContext) org.apache.logging.log4j.LogManager.getContext(false);
        org.apache.logging.log4j.core.config.LoggerConfig log4j2Cfg =
            log4j2Ctx.getConfiguration().getLoggerConfig(ProxyEventSourceListener.class.getName());
        org.apache.logging.log4j.core.appender.AbstractAppender appender =
            new org.apache.logging.log4j.core.appender.AbstractAppender(
                "test-pre-frame-capture", null, null, true,
                org.apache.logging.log4j.core.config.Property.EMPTY_ARRAY) {
                @Override
                public void append(org.apache.logging.log4j.core.LogEvent event) {
                    if (event.getLevel() == org.apache.logging.log4j.Level.ERROR
                        && event.getMessage() != null
                        && event.getMessage().getFormattedMessage().contains("Pre-frame HTTP failure")) {
                        LogRecord rec = new LogRecord(Level.SEVERE,
                            event.getMessage().getFormattedMessage());
                        if (event.getThrown() != null || event.getThrownProxy() != null) {
                            rec.setThrown(new RuntimeException("proxy-present"));
                        }
                        errorRecords.add(rec);
                    }
                }
            };
        appender.start();
        log4j2Cfg.addAppender(appender, null, null);
        log4j2Ctx.updateLoggers();

        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            pool.submit(() -> listener.onFailure(source(),
                new RuntimeException("fail-a"), response(502)));
            pool.submit(() -> listener.onFailure(source(),
                new RuntimeException("fail-b"), response(503)));
            pool.shutdown();
            assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS));
        } finally {
            log4j2Cfg.removeAppender("test-pre-frame-capture");
            log4j2Ctx.updateLoggers();
            if (!pool.isTerminated()) pool.shutdownNow();
        }

        assertNotNull(listener.getErrorRsp(), "exactly one winner must build errorRsp");
        verify(emitter, never()).send(anySet());
        // 完整原始栈日志恰好一次（tryHttpFailure 唯一赢家记录）
        assertEquals(1, errorRecords.size(), (
            "pre-frame full stack log must be recorded exactly once, "
            + "got " + errorRecords.size()));
    }

    // === P1(复审7 §4): 并发 post-frame failure → SSE error 恰好一次 ===

    @Test
    void twoConcurrentPostFrameFailures_sseErrorExactlyOne() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        listener.onOpen(source(), response(200));

        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            pool.submit(() -> listener.onFailure(source(),
                new RuntimeException("post-a"), response(500)));
            pool.submit(() -> listener.onFailure(source(),
                new RuntimeException("post-b"), response(500)));
            pool.shutdown();
            assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS));
        } finally {
            if (!pool.isTerminated()) pool.shutdownNow();
        }

        assertNull(listener.getErrorRsp(), "post-frame path must not set errorRsp");
        verify(emitter, times(1)).send(anySet());
    }

    // === P1(复审7 §4): 终态后 onEvent 不发送 ===

    @Test
    void afterTerminalState_onEvent_doesNotSend() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        listener.onFailure(source(), new RuntimeException("pre"), response(502));
        listener.onEvent(source(), "1", "message", "hello");

        verify(emitter, never()).send(anySet());
    }

    // === 复审8 §4.1: send 失败 → eventSource.cancel 恰好一次 + 无递归 ===

    @Test
    void sendFailure_cancelsUpstream_once_noRecursion() throws Exception {
        SseEmitter emitter = mockEmitter();
        doThrow(new IOException("send failed")).when(emitter).send(anySet());

        EventSource source = mockSource();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        listener.onOpen(source, response(200));
        listener.onEvent(source, "1", "message", "hello");

        // send 恰好一次（失败的 message），无递归 error send
        verify(emitter, times(1)).send(anySet());
        // 上游 EventSource 取消恰好一次
        verify(source, times(1)).cancel();
        // emitter 被关闭
        verify(emitter, times(1)).complete();
    }

    // === 复审8 §4.2: emitter completion/timeout/error → 幂等取消上游 ===

    @Test
    void emitterLifecycleCallbacks_cancelUpstream_idempotent() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        EventSource source = mockSource();

        // completion
        listener.onEmitterCompletion(source);
        verify(source, times(1)).cancel();
        // timeout（complete 也会被调用）
        listener.onEmitterTimeout(source);
        verify(source, times(1)).cancel();  // 幂等——仍一次
        verify(emitter, times(1)).complete();
        // error
        listener.onEmitterError(source);
        verify(source, times(1)).cancel();  // 幂等——仍一次
        // 重复 completion
        listener.onEmitterCompletion(source);
        verify(source, times(1)).cancel();  // 幂等——仍一次
    }

    // === 复审8 §4.2: 重复 completion + onClosed 不重复输出 ===

    @Test
    void duplicateCompletionAndOnClosed_noDuplicateOutput() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        EventSource source = mockSource();

        // 正常流: open → completion(emitter 回调) → onClosed(下游正常关闭)
        listener.onOpen(source, response(200));
        listener.onEmitterCompletion(source);
        listener.onClosed(source);

        // 取消只发生一次,无任何 send
        verify(source, times(1)).cancel();
        verify(emitter, never()).send(anySet());
    }

    // === 复审8 §4.2: 取消后 onEvent 不 send,onFailure 不产生 error ===

    @Test
    void afterCancelUpstream_noFurtherOutput() throws Exception {
        SseEmitter emitter = mockEmitter();
        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, latch, emitter, validResolver(), java.util.Locale.ENGLISH);

        EventSource source = mockSource();
        listener.onOpen(source, response(200));

        // 客户端断开 → completion 取消上游
        listener.onEmitterCompletion(source);

        // 之后 onEvent 不 send
        listener.onEvent(source, "1", "message", "hello");
        verify(emitter, never()).send(anySet());

        // 之后 onFailure 也不产生 SSE error(guard 已 CANCELLED,
        // tryHttpFailure/trySendError 都失败 → 只清理)
        listener.onFailure(source, new RuntimeException("late-fail"), response(500));
        verify(emitter, never()).send(anySet());
        assertNull(listener.getErrorRsp());
    }
}
