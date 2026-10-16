/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorDescriptorFactory;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerHttpErrorResponseBuilder;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerSseErrorEventBuilder;
import com.openjiuwen.studio.agent.manager.exception.contract.SseTerminalGuard;
import com.openjiuwen.studio.agent.manager.observability.MdcScope;
import com.openjiuwen.studio.agent.manager.observability.MdcSnapshot;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSourceListener;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.CountDownLatch;

/**
 * 通用 SSE 代理监听器（不继承 {@link BaseEventListener}）。
 *
 * <p>DEF-02 §4.4：不强行改变继承关系，但在自身四个公开回调中采用同一快照包装原则——
 * 构造时捕获 {@link MdcSnapshot}，每个回调用 {@code snapshot.openScope()} 包住完整逻辑，
 * 回调结束（含异常路径）恢复 OkHttp 工作线程原值。不再手动 {@code MDC.put(REQUEST_ID)}。
 *
 * <p>COM-03 复审6 §3：openConnect 普通 boolean 已移除，"是否已打开"与"谁获得终态"
 * 统一收敛到 {@link SseTerminalGuard} 的原子 CAS 状态机。onFailure 通过
 * tryHttpFailure() / trySendError() 原子二选一，保证最多一个赢家构建 HTTP error
 * 或发送 SSE error，完整原始栈恰好记录一次。
 */
@Slf4j
public class ProxyEventSourceListener extends EventSourceListener {

    private final SseEmitter sseEmitter;

    private final String requestId;

    @Getter
    private ResponseEntity<?> errorRsp;

    private final CountDownLatch latch;

    private final MdcSnapshot snapshot;

    /** COM-03 §6.2 + 复审6 §3: 唯一原子终态守卫 */
    private final SseTerminalGuard terminalGuard = new SseTerminalGuard();

    /** COM-03 复审8 §4: 上游 EventSource 幂等取消标记——重复回调只清理一次 */
    private final java.util.concurrent.atomic.AtomicBoolean upstreamCancelDone =
        new java.util.concurrent.atomic.AtomicBoolean(false);

    // COM-03 §5.1/§5.2: 实例字段,使用调用方注入的正式 i18n resolver
    private final ManagerErrorDescriptorFactory factory;
    private final ManagerHttpErrorResponseBuilder httpBuilder;
    private final ManagerSseErrorEventBuilder sseBuilder;
    // COM-03 §5.1: 入口 locale 快照——callback 线程不读取线程默认 locale
    private final java.util.Locale localeSnapshot;

    // COM-04 响应 §5.4: 统一下游 parser/mapper（RUNTIME 身份）——替代
    // fromDownstreamDependencyWithRequestId 的通用 502 兜底；body 严格解析一次
    private final com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser
        downstreamParser = new com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser(
            new com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMappingCatalog(
                new ManagerErrorCatalog()));
    private final com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMapper
        downstreamMapper = new com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMapper(
            new com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMappingCatalog(
                new ManagerErrorCatalog()));

    /**
     * COM-03 §5.1: 主构造函数——接受正式 i18n resolver 和入口 locale 快照,
     * 与 MgGlobalExceptionHandler 同源。callback 线程使用快照,不读取线程默认 locale。
     */
    public ProxyEventSourceListener(String requestId, CountDownLatch latch, SseEmitter sseEmitter,
            ManagerHttpErrorResponseBuilder.I18nResolver resolver, java.util.Locale locale) {
        this.requestId = requestId;
        this.latch = latch;
        this.sseEmitter = sseEmitter;
        this.snapshot = MdcSnapshot.capture();
        this.factory = new ManagerErrorDescriptorFactory(new ManagerErrorCatalog());
        this.httpBuilder = new ManagerHttpErrorResponseBuilder(resolver);
        this.sseBuilder = new ManagerSseErrorEventBuilder(resolver);
        this.localeSnapshot = locale;
    }

    /** 向后兼容构造函数（测试用）——使用安全 fallback resolver 和默认 locale。 */
    public ProxyEventSourceListener(String requestId, CountDownLatch latch, SseEmitter sseEmitter) {
        this(requestId, latch, sseEmitter, (key, loc) -> {
            if (key.endsWith(".reason")) return "A downstream service returned an error or was unreachable.";
            if (key.endsWith(".suggestion")) return "Please retry later; contact support if the issue persists.";
            return "Downstream service call failed.";
        }, java.util.Locale.ENGLISH);
    }

    @Override
    public void onClosed(@NotNull EventSource eventSource) {
        try (MdcScope scope = snapshot.openScope()) {
            terminalGuard.cancel();
            sseEmitter.complete();
            log.info("ProxyEventSourceListener close.");
        }
    }

    @Override
    public void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
        @NotNull String data) {
        try (MdcScope scope = snapshot.openScope()) {
            if (!terminalGuard.allowMessage()) {
                return;
            }
            // COM-04 响应 §5.4: 明确 SSE error event → parser → mapper → 唯一 Manager
            // error 终态；不透传下游原 event（不同时发下游原 event 和 Manager error）
            if ("error".equals(type)) {
                if (terminalGuard.trySendError()) {
                    handleDownstreamSseErrorEvent(eventSource, data);
                }
                return;
            }
            try {
                sseEmitter.send(SseEmitter.event().data(data).build());
            } catch (Throwable e) {
                log.error("SSE send message fail.", e);
                // COM-03 复审8 §4.1: 本地无法向前端发送 → 原子取消 guard +
                // 取消上游 EventSource + 关闭 emitter，不递归 error
                terminalGuard.cancel();
                cancelUpstream(eventSource);
                try { sseEmitter.complete(); } catch (Throwable ignored) { /* already closing */ }
            }
        }
    }

    /**
     * COM-04 响应 §5.4: 下游 SSE error event 统一处理——trySendError 赢家专属。
     * parseSseError（非 error event 已在外层过滤；普通 data 不进入）→ mapper 一次 →
     * Manager 标准 envelope 唯一 SSE error；随后取消上游并关闭 emitter。
     */
    private void handleDownstreamSseErrorEvent(EventSource eventSource, String data) {
        ErrorDescriptor descriptor;
        try {
            byte[] bounded = (data != null)
                ? java.util.Arrays.copyOf(data.getBytes(java.nio.charset.StandardCharsets.UTF_8),
                    Math.min(data.getBytes(java.nio.charset.StandardCharsets.UTF_8).length,
                        com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser.MAX_BODY_BYTES + 1))
                : null;
            var failureOpt = downstreamParser.parseSseError(
                com.openjiuwen.studio.agent.common.error.DownstreamService.RUNTIME,
                com.openjiuwen.studio.agent.manager.exception.downstream.Transport.OKHTTP_SSE,
                "error", bounded, null);
            var failure = failureOpt.orElseGet(() ->
                com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFailure.sseEvent(
                    com.openjiuwen.studio.agent.common.error.DownstreamService.RUNTIME,
                    com.openjiuwen.studio.agent.manager.exception.downstream.Transport.OKHTTP_SSE,
                    null, null));
            descriptor = downstreamMapper.map(failure, requestId != null ? requestId : "unknown");
        } catch (RuntimeException e) {
            descriptor = factory.fromDownstreamDependencyWithRequestId(requestId, null);
        }
        log.error("Downstream SSE error event received; managerCode={}, diag={}",
            descriptor.getErrorCode(),
            com.openjiuwen.studio.agent.common.error.ErrorDescriptorDiagnostics.toSafeLogFields(descriptor));
        try {
            java.util.Map<String, Object> envelope = sseBuilder.buildEnvelope(descriptor, localeSnapshot);
            sseEmitter.send(SseEmitter.event().name("error").data(envelope).build());
        } catch (Throwable e) {
            log.warn("Failed to send Manager error event: {}", e.getMessage());
        }
        cancelUpstream(eventSource);
        try { sseEmitter.complete(); } catch (Throwable ignored) { /* already closing */ }
    }

    /**
     * COM-03 复审8 §4.3: 幂等取消上游 EventSource——重复回调只清理一次。
     * onEvent send 失败与 emitter 生命周期回调（completion/timeout/error）共用。
     */
    public void cancelUpstream(EventSource eventSource) {
        if (eventSource == null) {
            return;
        }
        if (upstreamCancelDone.compareAndSet(false, true)) {
            try {
                eventSource.cancel();
            } catch (Throwable e) {
                log.warn("Cancel upstream EventSource failed: {}", e.getMessage());
            }
        }
    }

    /**
     * COM-03 复审10 §3.2.4: 原子终态取消——NOT_STARTED 或 STREAMING 首次进入
     * CANCELLED 的赢家释放等待线程。中断路径使用；保证此后 guard 不可再进入
     * STREAMING，迟到 onOpen/onEvent 均被拒绝。
     */
    public boolean tryCancelTerminal() {
        if (terminalGuard.tryCancel()) {
            latch.countDown();
            return true;
        }
        return false;
    }

    /**
     * COM-03 复审10 §3.2.2: 等待超时抢占——仅 NOT_STARTED → CANCELLED。
     * 赢家是唯一超时责任者（返回超时错误）；CAS 失败表示已有赢家：
     * STREAMING 由 onOpen 继续持有流，HTTP_FAILED 由失败赢家继续发布 errorRsp。
     */
    public boolean tryAbortBeforeOpen() {
        if (terminalGuard.tryAbortBeforeOpen()) {
            latch.countDown();
            return true;
        }
        return false;
    }

    /**
     * COM-03 复审8 §4.2 + 复审9 §4.2: emitter 完成（客户端断开/正常完成）→
     * guard 原子进入 CANCELLED + 取消上游。tryCancel 赢家释放等待线程——
     * 建连前（NOT_STARTED）取消时无其他 latch 释放者，必须由取消赢家释放，
     * 避免请求线程滞留至 30 秒上限。
     */
    public void onEmitterCompletion(EventSource eventSource) {
        tryCancelTerminal();
        cancelUpstream(eventSource);
    }

    /** COM-03 复审9 §4.2: emitter 超时 → guard CANCELLED + 释放等待者 + 幂等取消上游 + 安全收尾。 */
    public void onEmitterTimeout(EventSource eventSource) {
        tryCancelTerminal();
        cancelUpstream(eventSource);
        try { sseEmitter.complete(); } catch (Throwable ignored) { /* already closing */ }
    }

    /** COM-03 复审9 §4.2: emitter 出错 → guard CANCELLED + 释放等待者 + 幂等取消上游。 */
    public void onEmitterError(EventSource eventSource) {
        tryCancelTerminal();
        cancelUpstream(eventSource);
    }

    /**
     * COM-03 复审9 §4: 等待线程判定——guard 是否已进入 CANCELLED
     * （建连前客户端断开/超时/出错）。用于 await 后区分 OPENED 与 CANCELLED。
     */
    public boolean isCancelled() {
        return terminalGuard.getState() == SseTerminalGuard.State.CANCELLED;
    }

    /**
     * COM-03 复审10 §4: 等待线程判定——失败赢家是否已抢占 HTTP_FAILED。
     * 用于超时与 errorRsp 发布竞态时选择"等待发布"而非返回通用错误。
     */
    public boolean isHttpFailed() {
        return terminalGuard.getState() == SseTerminalGuard.State.HTTP_FAILED;
    }

    /**
     * COM-03 复审8 §4.2: 注册 SseEmitter 生命周期回调——客户端断开/超时/完成时
     * 幂等取消上游 EventSource，防止下游继续占用连接与生成资源。
     */
    public void bindEmitterLifecycle(SseEmitter emitter, EventSource eventSource) {
        emitter.onCompletion(() -> onEmitterCompletion(eventSource));
        emitter.onTimeout(() -> onEmitterTimeout(eventSource));
        emitter.onError(t -> onEmitterError(eventSource));
    }

    @Override
    public void onFailure(@NotNull EventSource eventSource, @Nullable Throwable t, @Nullable Response response) {
        try (MdcScope scope = snapshot.openScope()) {
            try {
                // COM-03 复审6 §3: 原子二选一——tryHttpFailure 或 trySendError 恰好一个赢家
                if (terminalGuard.tryHttpFailure()) {
                    // 首帧前 HTTP 失败：记一次完整原始栈 + 构建唯一 errorRsp
                    log.error("Pre-frame HTTP failure, downstream throwable:", t);
                    this.errorRsp = createErrorRsp(t, response);
                } else if (terminalGuard.trySendError()) {
                    // 首帧后 SSE 失败：记一次完整原始栈 + 发唯一 SSE error
                    log.error("Fail handler stream event.", t);
                    sendErrorEvent(t);
                }
                // 两个都败（已终态）→ 只清理，不输出、不记第二份栈
                sseEmitter.complete();
            } catch (Throwable e) {
                log.warn("Fail handler exception. {}", e.getMessage());
            } finally {
                latch.countDown();
            }
        }
    }

    /**
     * COM-03 §5.2 / COM-04 响应 §5.4: 接受原始 throwable,不用 new RuntimeException 替换根因。
     * descriptor 来源已替换为统一 adapter——transport failure → parser → mapper 一次。
     */
    private void sendErrorEvent(Throwable originalCause) {
        try {
            Throwable cause = (originalCause != null) ? originalCause
                : new RuntimeException("downstream stream failure (no throwable)");
            var failure = downstreamParser.fromTransportFailure(
                com.openjiuwen.studio.agent.common.error.DownstreamService.RUNTIME,
                com.openjiuwen.studio.agent.manager.exception.downstream.Transport.OKHTTP_SSE, cause);
            ErrorDescriptor descriptor = downstreamMapper.map(failure,
                requestId != null ? requestId : "unknown");
            java.util.Map<String, Object> envelope = sseBuilder.buildEnvelope(
                descriptor, localeSnapshot);
            sseEmitter.send(SseEmitter.event().name("error").data(envelope).build());
        } catch (Throwable e) {
            // COM-03 §6.2/§5.5: 写 error 自身失败只记录一次安全日志并关闭,
            // 不递归创建第二个 error,不发残缺帧
            log.warn("Failed to send error event to frontend: {}", e.getMessage());
        }
    }

    private ResponseEntity<?> createErrorRsp(Throwable throwable, Response response) throws IOException {
        // COM-04 响应 §5.4: 统一 adapter——受限读 body → parser（RUNTIME 身份）→ mapper 一次
        // （不再用通用 02001131 兜底替代解析；guard 的 tryHttpFailure 已保证唯一调用）
        int downstreamStatus = (response != null) ? response.code() : 500;
        log.debug("Request fail. downstream_status={}", downstreamStatus);
        ErrorDescriptor descriptor;
        if (response != null) {
            byte[] boundedBody = readBounded(response);
            String contentType = null;
            try {
                contentType = response.header("Content-Type");
            } catch (RuntimeException ignored) {
                // Content-Type 仅诊断
            }
            var failure = downstreamParser.parseHttp(
                com.openjiuwen.studio.agent.common.error.DownstreamService.RUNTIME,
                com.openjiuwen.studio.agent.manager.exception.downstream.Transport.OKHTTP_SSE,
                response.code(), contentType, boundedBody, throwable);
            descriptor = downstreamMapper.map(failure, requestId != null ? requestId : "unknown");
        } else {
            var failure = downstreamParser.fromTransportFailure(
                com.openjiuwen.studio.agent.common.error.DownstreamService.RUNTIME,
                com.openjiuwen.studio.agent.manager.exception.downstream.Transport.OKHTTP_SSE, throwable);
            descriptor = downstreamMapper.map(failure, requestId != null ? requestId : "unknown");
        }
        try {
            return httpBuilder.build(descriptor, localeSnapshot);
        } catch (Exception e) {
            log.error("HTTP builder failed in createErrorRsp, using safe fallback: {}", e.getMessage());
            ErrorRsp rsp = new ErrorRsp()
                .setErrorCode(descriptor.getErrorCode())
                .setErrorMsg("Internal server error.")
                .setErrorReason("An internal error occurred while processing the request.")
                .setErrorSuggestion("Please retry later; contact support if the issue persists.")
                .setRequestId(requestId);
            org.springframework.http.HttpHeaders hdrs = new org.springframework.http.HttpHeaders();
            hdrs.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
            hdrs.set("X-Request-Id", requestId);
            return new org.springframework.http.ResponseEntity<>(rsp, hdrs,
                org.springframework.http.HttpStatus.valueOf(descriptor.getHttpStatus()));
        }
    }

    /** COM-04 响应 §5.4: 受限读取 response body（≤ MAX+1 字节，超限 parser 安全降级）。 */
    private static byte[] readBounded(Response response) {
        if (response.body() == null) {
            return null;
        }
        int limit =
            com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser.MAX_BODY_BYTES + 1;
        try (java.io.InputStream is = response.body().byteStream()) {
            java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) != -1) {
                int remaining = limit - baos.size();
                if (remaining <= 0) {
                    break;
                }
                baos.write(buf, 0, Math.min(n, remaining));
                if (baos.size() >= limit) {
                    break;
                }
            }
            return baos.toByteArray();
        } catch (java.io.IOException e) {
            return null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    @Override
    public void onOpen(@NotNull EventSource eventSource, @NotNull Response response) {
        try (MdcScope scope = snapshot.openScope()) {
            // COM-03 复审7 §3: 只有 beginStreaming 成功时才释放 latch。
            // 若 HTTP_FAILED 已由 onFailure 抢占，onOpen 不得提前 countDown——
            // 首帧前 failure 赢家在 errorRsp 完整写入后才在 finally 释放 latch，
            // 保证调用方 await 返回时 errorRsp 已可见。
            if (terminalGuard.beginStreaming()) {
                log.info("Stream request open.");
                latch.countDown();
            } else {
                log.info("Stream open after terminal state; latch not released by onOpen.");
            }
        }
    }
}
