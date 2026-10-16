/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptorDiagnostics;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerErrorCatalog;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerHttpErrorResponseBuilder;
import com.openjiuwen.studio.agent.manager.exception.contract.ManagerSseErrorEventBuilder;
import com.openjiuwen.studio.agent.manager.exception.contract.SseTerminalGuard;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMapper;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorMappingCatalog;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamErrorParser;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFailure;
import com.openjiuwen.studio.agent.manager.exception.downstream.Transport;
import com.openjiuwen.studio.agent.manager.observability.MdcKeys;
import com.openjiuwen.studio.agent.manager.observability.MdcScope;
import com.openjiuwen.studio.agent.manager.observability.MdcSnapshot;

import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSourceListener;

import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;

/**
 * SSE 事件监听器基类（DEF-02 §4.4 / COM-04 响应 §5.4）。
 *
 * <p>构造时捕获 COM-02 {@link MdcSnapshot}（含 request-id/execution-id 等白名单键），
 * 不只保存 {@code requestId} 字符串。四个公开回调 {@link #onOpen}/{@link #onEvent}/
 * {@link #onFailure}/{@link #onClosed} 声明为 {@code final}，各自用
 * {@code snapshot.openScope()}（whitelist full-replace）包住对应 protected hook，
 * 保证 OkHttp 回调线程在回调期间持有构造时上下文、回调结束（含异常路径）恢复原值。
 *
 * <p>派生类只覆盖 {@link #onOpenInternal}/{@link #onEventBusinessHook}/
 * {@link #onFailureInternal}/{@link #onClosedBusinessHook}，不得直接覆盖四个公开回调或
 * {@link #onEventInternal}/{@link #onClosedInternal}（已声明 final，基类统一拥有状态迁移）；
 * 派生类追加的逻辑也必须位于 hook 内，从而处于同一 scope。
 *
 * <p>COM-04 响应 §5.4：{@code openConnect} 普通布尔已迁移到
 * {@link SseTerminalGuard} 单一原子终态（HTTP 失败/SSE error/完成/取消唯一赢家）；
 * 下游失败经统一 parser/mapper（{@code DownstreamFailure} → 一次映射）产出 Manager
 * 标准 {@link ErrorDescriptor}，不再按下游状态透传任意 JSON、不回显原始正文、
 * 不在日志输出完整 {@code rsp}/{@code Response}。
 */
@Slf4j
public class BaseEventListener extends EventSourceListener {

    @Setter
    SseEmitter sseEmitter;

    final String requestId;

    /** COM-04 响应 §5.4: 单一原子终态守卫（替代 openConnect 普通布尔）。 */
    final SseTerminalGuard terminalGuard = new SseTerminalGuard();

    /** COM-04 响应 §5.4: 唯一 pre-frame HTTP 失败响应（标准五字段）。 */
    @Getter
    ResponseEntity<?> errorRsp;

    /** COM-04 响应: SSE error event 检测到的最近 descriptor（供子类业务处理使用稳定码）。 */
    @Getter
    ErrorDescriptor lastErrorDescriptor;

    @Setter
    CountDownLatch latch;

    final HttpHeaders headers;

    private final MdcSnapshot snapshot;

    // COM-04 响应 §5.4: 统一 parser/mapper/builder——四个 listener 共享（RUNTIME 身份）
    private final DownstreamErrorParser downstreamParser = new DownstreamErrorParser(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
    private final DownstreamErrorMapper downstreamMapper = new DownstreamErrorMapper(
        new DownstreamErrorMappingCatalog(new ManagerErrorCatalog()));
    private final ManagerHttpErrorResponseBuilder httpBuilder;
    private final ManagerSseErrorEventBuilder sseBuilder;
    private final Locale localeSnapshot;

    public BaseEventListener(String requestId, HttpHeaders headers) {
        this.requestId = requestId;
        this.headers = headers;
        // DEF-02: 捕获构造线程（请求线程，已建立 execution-id scope）的完整白名单快照
        this.snapshot = MdcSnapshot.capture();
        // COM-04 响应 §5.4: 入口 locale 快照——回调线程不读取线程默认 locale
        this.localeSnapshot = resolveLocale();
        ManagerHttpErrorResponseBuilder.I18nResolver resolver = resolveResolver();
        this.httpBuilder = new ManagerHttpErrorResponseBuilder(resolver);
        this.sseBuilder = new ManagerSseErrorEventBuilder(resolver);
    }

    private static Locale resolveLocale() {
        try {
            return Locale.getDefault();
        } catch (RuntimeException e) {
            return Locale.ENGLISH;
        }
    }

    /** 正式 i18n resolver（Spring 可用且 bean 非空时），否则安全 fallback。 */
    private static ManagerHttpErrorResponseBuilder.I18nResolver resolveResolver() {
        I18nUtil i18n = lookupI18n();
        if (i18n != null) {
            return (key, locale) -> i18n.getMessage(key, locale);
        }
        return fallbackResolver();
    }

    private static I18nUtil lookupI18n() {
        try {
            return SpringBeanUtils.getBean(I18nUtil.class);
        } catch (Exception e) {
            // 无 Spring 上下文（单测）→ fallback
            return null;
        }
    }

    private static ManagerHttpErrorResponseBuilder.I18nResolver fallbackResolver() {
        return (key, locale) -> {
            if (key.endsWith(".reason")) {
                return "A downstream service returned an error or was unreachable.";
            }
            if (key.endsWith(".suggestion")) {
                return "Please retry later; contact support if the issue persists.";
            }
            return "Downstream service call failed.";
        };
    }

    // ============ final 公开回调：scope 包装 + 委派 hook ============

    @Override
    public final void onOpen(@NotNull EventSource eventSource, @NotNull Response response) {
        try (MdcScope scope = snapshot.openScope()) {
            onOpenInternal(response);
        }
    }

    @Override
    public final void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
        @NotNull String data) {
        try (MdcScope scope = snapshot.openScope()) {
            onEventInternal(id, type, data);
        }
    }

    @Override
    public final void onFailure(@NotNull EventSource eventSource, @Nullable Throwable t, @Nullable Response response) {
        try (MdcScope scope = snapshot.openScope()) {
            onFailureInternal(t, response);
        }
    }

    @Override
    public final void onClosed(@NotNull EventSource eventSource) {
        try (MdcScope scope = snapshot.openScope()) {
            onClosedInternal();
        }
    }

    // ============ protected hooks（派生类覆盖） ============

    protected void onOpenInternal(@NotNull Response response) {
        // COM-04 响应 §5.4: 只有 beginStreaming 成功时释放 latch（同 COM-03 协议）
        if (terminalGuard.beginStreaming()) {
            latch.countDown();
            log.info("Stream request open.");
        } else {
            log.info("Stream open after terminal state; latch not released by onOpen.");
        }
    }

    /**
     * COM-04 响应 §5.4: final 事件 hook——基类统一拥有状态迁移和 error 拦截。
     * <p>
     * 在子类业务分派和 passThrough 之前检测 SSE error event（Runtime 把
     * {@code event:error} 嵌入 JSON data）。检测到时走 guard 原子终态 +
     * parser/mapper 一次 + Manager SSE error。非 error event 委派子类
     * {@link #onEventBusinessHook} 处理业务逻辑。
     * <p>派生类不得覆盖此方法；覆盖 {@link #onEventBusinessHook}。
     */
    protected final void onEventInternal(@Nullable String id, @Nullable String type, @NotNull String data) {
        if (isDownstreamErrorEvent(data)) {
            handleSseErrorEvent(data);
        }
        onEventBusinessHook(id, type, data);
    }

    /**
     * 事件业务处理 hook（派生类覆盖）。
     * 默认实现仅 passThrough；派生类按事件类型分派业务逻辑。
     * error event 已由基类拦截并产出 Manager SSE error，此处不得重复透传原始 error 事件。
     */
    protected void onEventBusinessHook(@Nullable String id, @Nullable String type, @NotNull String data) {
        passThrough(data);
    }

    /**
     * COM-04 响应 §5.4: 统一失败终态。派生类覆盖时应调用 {@link #handleTerminalFailure}
     * （或完整复刻其原子协议），不得再调用已删除的旧 {@code createErrorRsp} 透传路径。
     */
    protected void onFailureInternal(@Nullable Throwable t, @Nullable Response response) {
        try {
            handleTerminalFailure(t, response);
        } catch (Throwable e) {
            log.warn("Fail handler exception. {}", e.getMessage());
        } finally {
            latch.countDown();
        }
    }

    /**
     * COM-04 响应 §5.4: final 关闭 hook——基类统一拥有 guard.cancel() + emitter 关闭。
     * 派生类不得覆盖此方法；覆盖 {@link #onClosedBusinessHook}。
     */
    protected final void onClosedInternal() {
        terminalGuard.cancel();
        onClosedBusinessHook();
        completeEmitterQuietly();
    }

    /** 关闭业务处理 hook（派生类覆盖）。默认仅记日志。 */
    protected void onClosedBusinessHook() {
        log.info("BaseEventListener close.");
    }

    // ============ COM-04 响应 §5.4/§5.5: 统一下游失败处理 ============

    /**
     * 原子失败终态（guard 唯一赢家）：
     * <ul>
     *   <li>pre-frame（tryHttpFailure 赢家）：受限读 body → parser → mapper 一次 →
     *       HTTP builder 标准五字段 {@code errorRsp}（供 stream() 调用方返回）；</li>
     *   <li>post-frame（trySendError 赢家）：transport failure → mapper 一次 →
     *       SSE error event（Manager envelope）；</li>
     *   <li>已终态：只做幂等清理，不输出、不记第二份栈。</li>
     * </ul>
     * 完整原始栈只由赢家记录一次（含安全结构化诊断，不含原始 body/Response 对象）。
     *
     * @return 赢家的 descriptor（供子类执行 winner-only 业务副作用）；非赢家返回 null
     */
    protected final ErrorDescriptor handleTerminalFailure(@Nullable Throwable t, @Nullable Response response) {
        ErrorDescriptor descriptor = null;
        if (terminalGuard.tryHttpFailure()) {
            descriptor = buildDownstreamDescriptor(t, response);
            this.lastErrorDescriptor = descriptor;
            logDownstreamFailureOnce(descriptor, t, "pre-frame HTTP");
            setErrorResponse(descriptor);
        } else if (terminalGuard.trySendError()) {
            descriptor = buildDownstreamDescriptor(t, response);
            this.lastErrorDescriptor = descriptor;
            logDownstreamFailureOnce(descriptor, t, "post-frame transport");
            sendErrorToConsumer(descriptor);
        }
        // 两个都败（已终态）→ 幂等清理
        completeEmitterQuietly();
        return descriptor;
    }

    /**
     * pre-frame HTTP errorRsp 输出。同步 listener 构造标准五字段 ResponseEntity；
     * 异步 listener（无前端消费者）覆写为 no-op。
     */
    protected void setErrorResponse(ErrorDescriptor descriptor) {
        this.errorRsp = buildHttpErrorResponse(descriptor);
    }

    /**
     * COM-04 响应 §5.4/§5.5: 共享 adapter——下游事实一次解析、一次映射。
     * pre-frame（有 HTTP 响应）受限读 body 解析；无响应按 transport failure。
     * 派生类（如 AsyncWorkflowListener）可直接取 descriptor 做安全任务终态，
     * 不构造 HTTP/SSE 输出。
     */
    protected final ErrorDescriptor buildDownstreamDescriptor(@Nullable Throwable t,
                                                              @Nullable Response response) {
        String rid = (requestId != null && !requestId.isBlank()) ? requestId : "unknown";
        if (response != null) {
            byte[] boundedBody = readBounded(response);
            String contentType = null;
            try {
                contentType = response.header("Content-Type");
            } catch (RuntimeException ignored) {
                // Content-Type 仅诊断
            }
            var failure = downstreamParser.parseHttp(DownstreamService.RUNTIME, Transport.OKHTTP_SSE,
                response.code(), contentType, boundedBody, t);
            return downstreamMapper.map(failure, rid);
        }
        var failure = downstreamParser.fromTransportFailure(DownstreamService.RUNTIME,
            Transport.OKHTTP_SSE, t);
        return downstreamMapper.map(failure, rid);
    }

    /** 受限读取 response body（≤ MAX+1 字节，超限 parser 安全降级）。 */
    private static byte[] readBounded(Response response) {
        if (response.body() == null) {
            return null;
        }
        int limit = DownstreamErrorParser.MAX_BODY_BYTES + 1;
        try (InputStream is = response.body().byteStream()) {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
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
        } catch (IOException e) {
            return null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    /** 最终责任边界一次完整栈 + 安全结构化诊断（不含 body/Response/cause message 外泄）。 */
    private void logDownstreamFailureOnce(ErrorDescriptor descriptor, @Nullable Throwable t, String phase) {
        Map<String, Object> diag = ErrorDescriptorDiagnostics.toSafeLogFields(descriptor);
        if (t != null) {
            log.error("Downstream stream failure ({}): managerCode={}, diag={}", phase,
                descriptor.getErrorCode(), diag, t);
        } else {
            log.error("Downstream stream failure ({}): managerCode={}, diag={}", phase,
                descriptor.getErrorCode(), diag);
        }
    }

    /** pre-frame HTTP builder（标准五字段）+ fail-closed 安全 fallback。 */
    private ResponseEntity<?> buildHttpErrorResponse(ErrorDescriptor descriptor) {
        try {
            return httpBuilder.build(descriptor, localeSnapshot);
        } catch (Exception e) {
            log.error("HTTP builder failed, using safe fallback: {}", e.getMessage());
            ErrorRsp rsp = new ErrorRsp()
                .setErrorCode(descriptor.getErrorCode())
                .setErrorMsg("Internal server error.")
                .setErrorReason("An internal error occurred while processing the request.")
                .setErrorSuggestion("Please retry later; contact support if the issue persists.")
                .setRequestId(descriptor.getRequestId());
            HttpHeaders hdrs = new HttpHeaders();
            hdrs.setContentType(MediaType.APPLICATION_JSON);
            hdrs.set("X-Request-Id", descriptor.getRequestId());
            return new ResponseEntity<>(rsp, hdrs,
                org.springframework.http.HttpStatus.valueOf(descriptor.getHttpStatus()));
        }
    }

    /** post-frame 唯一 Manager SSE error（标准 envelope；写失败只记一次安全日志）。 */
    private void sendManagerSseError(ErrorDescriptor descriptor) {
        try {
            Map<String, Object> envelope = sseBuilder.buildEnvelope(descriptor, localeSnapshot);
            sseEmitter.send(SseEmitter.event().name("error").data(envelope).build());
        } catch (Throwable e) {
            log.warn("Failed to send Manager error event: {}", e.getMessage());
        }
    }

    // ---- COM-04 响应 §5.4: SSE 流内 error event 拦截（JSON 内嵌 event=error）----

    /**
     * SSE error event 原子终态（guard trySendError 唯一赢家）：
     * 解析 JSON data 子对象 → parser → mapper 一次 → 写 {@link #lastErrorDescriptor}
     * → 输出到消费者（同步走 Manager SSE error；异步子类覆写为 no-op）。
     * 已终态时返回 null（非赢家，只做幂等清理）。
     */
    protected final ErrorDescriptor handleSseErrorEvent(String data) {
        if (!terminalGuard.trySendError()) {
            return null; // 已终态——非赢家
        }
        ErrorDescriptor descriptor = buildSseErrorDescriptor(data);
        this.lastErrorDescriptor = descriptor;
        logDownstreamFailureOnce(descriptor, null, "SSE error event");
        sendErrorToConsumer(descriptor);
        return descriptor;
    }

    /**
     * 错误终态输出到消费者。同步 listener 走 Manager SSE error；
     * 异步 listener（无前端消费者）覆写为 no-op。
     */
    protected void sendErrorToConsumer(ErrorDescriptor descriptor) {
        sendManagerSseError(descriptor);
    }

    /** 从 SSE error event JSON 解析下游事实并一次映射为 descriptor。 */
    private ErrorDescriptor buildSseErrorDescriptor(String data) {
        String rid = (requestId != null && !requestId.isBlank()) ? requestId : "unknown";
        byte[] dataBytes = extractErrorDataBytes(data);
        Optional<DownstreamFailure> failure = downstreamParser.parseSseError(
            DownstreamService.RUNTIME, Transport.OKHTTP_SSE, "error", dataBytes, null);
        DownstreamFailure f = failure.orElseGet(() ->
            downstreamParser.fromTransportFailure(DownstreamService.RUNTIME, Transport.OKHTTP_SSE, null));
        return downstreamMapper.map(f, rid);
    }

    /**
     * 检测 SSE data 是否为 error event。Runtime/Builder 把 event 类型嵌入
     * JSON data（{@code {"event":"error",...}}），非 SSE {@code event:} 字段。
     */
    private static boolean isDownstreamErrorEvent(String data) {
        if (data == null || data.isBlank()) {
            return false;
        }
        try {
            com.alibaba.fastjson.JSONObject json = com.alibaba.fastjson.JSON.parseObject(data);
            return json != null && "error".equals(json.getString("event"));
        } catch (Exception e) {
            return false;
        }
    }

    /** 提取 SSE error event JSON 中 {@code data} 子对象字节（error_code 在 data 内层）。 */
    private static byte[] extractErrorDataBytes(String data) {
        try {
            com.alibaba.fastjson.JSONObject json = com.alibaba.fastjson.JSON.parseObject(data);
            com.alibaba.fastjson.JSONObject dataObj = json.getJSONObject("data");
            if (dataObj != null) {
                return dataObj.toJSONString().getBytes(StandardCharsets.UTF_8);
            }
        } catch (Exception e) {
            // ignore — parser 安全降级
        }
        return null;
    }

    /** 幂等安全关闭 emitter（complete 异常不传播）。 */
    protected final void completeEmitterQuietly() {
        try {
            sseEmitter.complete();
        } catch (Throwable ignored) {
            // already closing
        }
    }

    // ============ 共享工具 ============

    protected void passThrough(String data) {
        // COM-04 响应 §5.4/P1-1: 终态后不发送（guard 原子保证唯一输出）
        if (!terminalGuard.allowMessage()) {
            return;
        }
        try {
            sseEmitter.send(SseEmitter.event().data(data).build());
        } catch (Throwable e) {
            log.error("SSE send message fail.", e);
        }
    }

    <T> T parseJiuWenEventFromSseData(String sseData, Class<T> clazz) {
        try {
            return com.alibaba.fastjson.JSON.parseObject(sseData, clazz);
        } catch (Exception e) {
            // COM-04 响应 §5.3: chunk 解析失败不记录完整 chunk，只记录长度与安全原因
            log.warn("Failed to parse sse data (length={})", sseData != null ? sseData.length() : 0);
            return null;
        }
    }
}
