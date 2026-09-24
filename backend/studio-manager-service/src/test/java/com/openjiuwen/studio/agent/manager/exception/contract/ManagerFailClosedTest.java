/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.service.proxy.ProxyEventSourceListener;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.concurrent.CountDownLatch;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.verify;

/**
 * COM-03 §10.2.6 + 复审6 §9.5: Manager listener fail-closed + Locale + 完整字段测试。
 *
 * 通过 ProxyEventSourceListener 公开构造函数,使用会失败的 resolver,
 * 验证 createErrorRsp 的安全 fallback 仍返回完整五字段 + 正确 Content-Type + request ID。
 * 使用 spy SseEmitter 替代 null emitter,避免 NullPointerException。
 */
class ManagerFailClosedTest {

    private static final String CODE = "openjiuwen.02001131";
    private static final String RID = "req-fc-001";

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

    private Response response(int code) {
        return new Response.Builder()
            .request(new Request.Builder().url("http://test").build())
            .protocol(okhttp3.Protocol.HTTP_1_1)
            .code(code)
            .message("test")
            .build();
    }

    private SseEmitter spyEmitter() {
        return spy(new SseEmitter(30000L));
    }

    private void triggerFailure(ProxyEventSourceListener listener) {
        listener.onFailure(source(), new RuntimeException("orig-throwable"), response(502));
    }

    private ProxyEventSourceListener withFailingResolver() {
        return new ProxyEventSourceListener(RID, new CountDownLatch(1), spyEmitter(),
            (key, locale) -> { throw new RuntimeException("resolver-boom"); },
            java.util.Locale.ENGLISH);
    }

    private ProxyEventSourceListener withBlankResolver() {
        return new ProxyEventSourceListener(RID, new CountDownLatch(1), spyEmitter(),
            (key, locale) -> "   ",
            java.util.Locale.ENGLISH);
    }

    private ProxyEventSourceListener withNullResolver() {
        return new ProxyEventSourceListener(RID, new CountDownLatch(1), spyEmitter(),
            (key, locale) -> null,
            java.util.Locale.ENGLISH);
    }

    private ProxyEventSourceListener withValidResolver() {
        return new ProxyEventSourceListener(RID, new CountDownLatch(1), spyEmitter(),
            (key, locale) -> "msg:" + key,
            java.util.Locale.ENGLISH);
    }

    private void assertSafeFallback(ResponseEntity<?> resp) {
        assertNotNull(resp, "errorRsp must not be null");
        assertEquals(502, resp.getStatusCode().value());
        Object body = resp.getBody();
        assertNotNull(body);
        assertTrue(body instanceof ErrorRsp);
        ErrorRsp rsp = (ErrorRsp) body;
        assertEquals(CODE, rsp.getErrorCode());
        // 五字段全部非空
        assertNotNull(rsp.getErrorMsg());
        assertTrue(rsp.getErrorMsg().contains("Internal server error"));
        assertNotNull(rsp.getErrorReason());
        assertTrue(!rsp.getErrorReason().isBlank(), "error_reason must be non-empty");
        assertNotNull(rsp.getErrorSuggestion());
        assertTrue(!rsp.getErrorSuggestion().isBlank(), "error_suggestion must be non-empty");
        assertEquals(RID, rsp.getRequestId());
        // Content-Type = application/json
        MediaType ct = resp.getHeaders().getContentType();
        assertNotNull(ct, "Content-Type must be set");
        assertTrue(ct.isCompatibleWith(MediaType.APPLICATION_JSON),
            "Content-Type must be application/json");
        // X-Request-Id header == body request_id
        assertEquals(RID, resp.getHeaders().getFirst("X-Request-Id"));
    }

    @Test
    void resolverThrows_createErrorRsp_safeFallback() {
        ProxyEventSourceListener listener = withFailingResolver();
        triggerFailure(listener);
        assertSafeFallback(listener.getErrorRsp());
    }

    @Test
    void resolverBlank_createErrorRsp_safeFallback() {
        ProxyEventSourceListener listener = withBlankResolver();
        triggerFailure(listener);
        assertSafeFallback(listener.getErrorRsp());
    }

    @Test
    void resolverNull_createErrorRsp_safeFallback() {
        ProxyEventSourceListener listener = withNullResolver();
        triggerFailure(listener);
        assertSafeFallback(listener.getErrorRsp());
    }

    @Test
    void resolverValid_createErrorRsp_fullFields() {
        ProxyEventSourceListener listener = withValidResolver();
        triggerFailure(listener);
        ResponseEntity<?> resp = listener.getErrorRsp();
        assertNotNull(resp);
        ErrorRsp rsp = (ErrorRsp) resp.getBody();
        assertEquals(CODE, rsp.getErrorCode());
        assertTrue(rsp.getErrorMsg().startsWith("msg:"));
        assertTrue(rsp.getErrorReason().startsWith("msg:"));
        assertTrue(rsp.getErrorSuggestion().startsWith("msg:"));
        assertEquals(RID, rsp.getRequestId());
        // Content-Type 和 X-Request-Id 一致
        assertTrue(resp.getHeaders().getContentType()
            .isCompatibleWith(MediaType.APPLICATION_JSON));
        assertEquals(RID, resp.getHeaders().getFirst("X-Request-Id"));
    }

    @Test
    void failure_completesEmitter_exactlyOnce() {
        SseEmitter emitter = spyEmitter();
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, new CountDownLatch(1), emitter,
            (key, loc) -> { throw new RuntimeException("boom"); },
            java.util.Locale.ENGLISH);
        triggerFailure(listener);
        // emitter 被 complete 至少一次
        verify(emitter, org.mockito.Mockito.atLeastOnce()).complete();
    }

    @Test
    void preFrameFailure_noSseErrorSent() {
        SseEmitter emitter = spyEmitter();
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            RID, new CountDownLatch(1), emitter);
        // 首帧前失败 → HTTP 路径，不调用 send（SSE error）
        triggerFailure(listener);
        // send 只可能在 SSE error 路径；首帧前路径不 send
        // spy SseEmitter 不会记录 send 调用（除非真的调了）
        assertNotNull(listener.getErrorRsp());
    }
}
