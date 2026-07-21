/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;

import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSourceListener;

import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;

@Slf4j
public class BaseEventListener extends EventSourceListener {
    static final String REQUEST_ID = "request-id";

    @Setter
    SseEmitter sseEmitter;

    final String requestId;

    boolean openConnect;

    @Getter
    ResponseEntity<Object> errorRsp;

    @Setter
    CountDownLatch latch;

    final HttpHeaders headers;

    public BaseEventListener(String requestId, HttpHeaders headers) {
        this.requestId = requestId;
        this.headers = headers;
    }

    @Override
    public void onClosed(@NotNull EventSource eventSource) {
        sseEmitter.complete();
        log.info("BaseEventListener close.");
    }

    @Override
    public void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
        @NotNull String data) {
        passThrough(data);
    }

    @Override
    public void onFailure(@NotNull EventSource eventSource, @Nullable Throwable t, @Nullable Response response) {
        try {
            MDC.put(REQUEST_ID, requestId);
            this.errorRsp = createErrorRsp(t, response);
            this.openConnect = true;
            log.error("Fail handler stream event. Throwable: {}, Response: {}", t, response);
            sseEmitter.complete();
        } catch (Throwable e) {
            log.warn("Fail handler exception. {}", e.getMessage());
        } finally {
            latch.countDown();
        }
    }

    protected void passThrough(String data) {
        try {
            sseEmitter.send(SseEmitter.event().data(data).build());
        } catch (Throwable e) {
            log.error("SSE send message fail.", e);
        }
    }

    ResponseEntity<Object> createErrorRsp(Throwable throwable, Response response) throws IOException {
        if (this.openConnect) {
            log.error("Fail handler request.", throwable);
            return null;
        }
        if (response != null) {
            String rsp = response.body() == null ? "{}" : new String(response.body().bytes(), StandardCharsets.UTF_8);
            log.error("Request fail. rsp:{}", rsp);
            try {
                return ResponseEntity.status(response.code()).body(JsonUtils.decode(rsp, Object.class));
            } catch (Exception e) {
                return ResponseEntity.status(response.code()).body(new ErrorRsp().setErrorMsg(rsp));
            }
        }
        log.error("Fail handler request.", throwable);
        return ResponseEntity.status(500).body(new ErrorRsp().setErrorMsg("Internal error."));
    }

    @Override
    public void onOpen(@NotNull EventSource eventSource, @NotNull Response response) {
        this.openConnect = true;
        MDC.put(REQUEST_ID, requestId);
        latch.countDown();
        log.info("Stream request open.");
    }

    <T> T parseJiuWenEventFromSseData(String sseData, Class<T> clazz) {
        try {
            return com.alibaba.fastjson.JSON.parseObject(sseData, clazz);
        } catch (Exception e) {
            log.error("Fail to parse sse data: [{}]", sseData);
            return null;
        }
    }
}
