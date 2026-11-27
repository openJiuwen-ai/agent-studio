/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.error.DownstreamService;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.PassthroughText;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import org.junit.jupiter.api.Test;

import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
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

    // Resolver: args 非 null 时把 args[0] 拼进返回值（验证 args 透传），否则只返回 key。
    private final ManagerHttpErrorResponseBuilder.I18nResolver resolver =
        (key, args, locale) -> args != null && args.length > 0 ? key + "::" + args[0] : key + "::resolved";

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

    // ---- 受管三段文案回退（COM-04 §5.2 修订，2026-11-02）----

    private static final String ENGINE_CODE = "openjiuwen.101003";

    private ErrorDescriptor engineDescriptor(PassthroughText passthrough) {
        return new ErrorDescriptor(ENGINE_CODE, 500, ENGINE_CODE,
            ENGINE_CODE + ".reason", ENGINE_CODE + ".suggestion", REQ_ID, null, null, null,
            null, passthrough);
    }

    @Test
    @SuppressWarnings("unchecked")
    void envelope_uses_passthrough_text_when_i18n_misses() {
        // I18nUtil 语义：key 缺失时回显 key 本身（视为未命中）
        ManagerSseErrorEventBuilder b =
            new ManagerSseErrorEventBuilder((key, args, locale) -> key);
        ErrorDescriptor d = engineDescriptor(new PassthroughText(
            "LLM调用失败：LLM stream failed: Connection error.",
            "LLM组件调用模型服务失败", "请检查模型服务状态"));
        Map<String, Object> env = b.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals(ENGINE_CODE, data.get("error_code"));
        assertEquals("LLM调用失败：LLM stream failed: Connection error.", data.get("error_msg"));
        assertEquals("LLM组件调用模型服务失败", data.get("error_reason"));
        assertEquals("请检查模型服务状态", data.get("error_suggestion"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void envelope_i18n_hit_wins_over_passthrough() {
        // Manager i18n 已覆盖的码（8 位族）不受回退影响——行为保持
        ManagerSseErrorEventBuilder b =
            new ManagerSseErrorEventBuilder((key, args, locale) -> key + "::resolved");
        ErrorDescriptor d = new ErrorDescriptor(CODE, 500, MSG_KEY, REASON_KEY, SUGGESTION_KEY,
            REQ_ID, null, null, null, null, new PassthroughText("passthrough-msg", null, null));
        Map<String, Object> env = b.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals(MSG_KEY + "::resolved", data.get("error_msg"));
        assertEquals(REASON_KEY + "::resolved", data.get("error_reason"));
        assertEquals(SUGGESTION_KEY + "::resolved", data.get("error_suggestion"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void envelope_resolver_throw_with_passthrough_uses_fallback() {
        ManagerSseErrorEventBuilder b = new ManagerSseErrorEventBuilder((key, args, locale) -> {
            throw new IllegalStateException("resolver boom");
        });
        // mapper 已做完整性兜底：reason/suggestion 缺失由 message 填充
        ErrorDescriptor d = engineDescriptor(new PassthroughText("回退文案", null, null));
        Map<String, Object> env = b.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals("回退文案", data.get("error_msg"));
        assertEquals("回退文案", data.get("error_reason"));
        assertEquals("回退文案", data.get("error_suggestion"));
    }

    @Test
    void envelope_resolver_throw_without_passthrough_fails_closed() {
        ManagerSseErrorEventBuilder b = new ManagerSseErrorEventBuilder((key, args, locale) -> {
            throw new IllegalStateException("resolver boom");
        });
        assertThrows(IllegalStateException.class,
            () -> b.buildEnvelope(descriptor(), Locale.CHINA));
    }

    @Test
    void envelope_blank_resolve_without_passthrough_fails_closed() {
        ManagerSseErrorEventBuilder b =
            new ManagerSseErrorEventBuilder((key, args, locale) -> "");
        assertThrows(IllegalStateException.class,
            () -> b.buildEnvelope(descriptor(), Locale.CHINA));
    }

    // ---- 统一族格式（COM-04 §5.2 修订二期，2026-11-02 用户裁定）----

    @Test
    @SuppressWarnings("unchecked")
    void envelope_unified_family_format_label_with_passthrough() {
        // i18n miss（key 回显）→ error_msg=族前缀，error_reason="组件runtime：{受管文案}"
        ManagerSseErrorEventBuilder b =
            new ManagerSseErrorEventBuilder((key, args, locale) -> key);
        ErrorDescriptor d = new ErrorDescriptor(ENGINE_CODE, 500, ENGINE_CODE,
            ENGINE_CODE + ".reason", ENGINE_CODE + ".suggestion", REQ_ID, null, null, null,
            null, new PassthroughText("LLM调用失败：Connection error", null, "请检查模型服务"),
            "runtime");
        Map<String, Object> env = b.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals(ENGINE_CODE, data.get("error_code"));
        assertEquals("下游依赖访问失败。", data.get("error_msg"));
        assertEquals("组件runtime：LLM调用失败：Connection error", data.get("error_reason"));
        assertEquals("请检查模型服务", data.get("error_suggestion"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void envelope_unified_family_format_default_bucket_detail() {
        // 兜底码（messageKey=族 key）+ i18n miss → detail 落到字面量
        ManagerSseErrorEventBuilder b =
            new ManagerSseErrorEventBuilder((key, args, locale) -> key);
        ErrorDescriptor d = new ErrorDescriptor("openjiuwen.02001131", 502,
            "openjiuwen.02001131", "openjiuwen.02001131.reason",
            "openjiuwen.02001131.suggestion", REQ_ID, null, null, null, null, null,
            "runtime");
        Map<String, Object> env = b.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals("下游依赖访问失败。", data.get("error_msg"));
        assertEquals("组件runtime：下游服务调用返回错误或网络不可达", data.get("error_reason"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void envelope_unified_family_format_obs_label() {
        // manager 自有 OBS 码（factory 打 obs 标签），原码 message 作为错误信息
        ManagerSseErrorEventBuilder b = new ManagerSseErrorEventBuilder((key, args, locale) -> {
            if ("openjiuwen.02001004".equals(key)) {
                return "OBS服务出错。";
            }
            if ("openjiuwen.02001004.suggestion".equals(key)) {
                return "请检查对象存储配置。";
            }
            return key; // 其余视为未命中
        });
        ErrorDescriptor d = new ErrorDescriptor("openjiuwen.02001004", 500,
            "openjiuwen.02001004", "openjiuwen.02001004.reason",
            "openjiuwen.02001004.suggestion", REQ_ID, null, null, null, null, null,
            "obs");
        Map<String, Object> env = b.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals("下游依赖访问失败。", data.get("error_msg"));
        assertEquals("组件obs：OBS服务出错。", data.get("error_reason"));
        assertEquals("请检查对象存储配置。", data.get("error_suggestion"));
    }

    /** bug009 根因2: cause 为 ASE 时, args 透传给 resolver 填占位符。 */
    @Test
    @SuppressWarnings("unchecked")
    void causeAgentStudioException_argsPassedToResolver() {
        AgentStudioException cause = new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS,
            "agent");
        ErrorDescriptor d = new ErrorDescriptor(CODE, 400, MSG_KEY, REASON_KEY,
            SUGGESTION_KEY, REQ_ID, null, null, null, cause);
        Map<String, Object> env = sseBuilder.buildEnvelope(d, Locale.CHINA);
        Map<String, Object> data = (Map<String, Object>) env.get("data");
        assertEquals(MSG_KEY + "::agent", data.get("error_msg"));
        assertEquals(REASON_KEY + "::agent", data.get("error_reason"));
        assertEquals(SUGGESTION_KEY + "::agent", data.get("error_suggestion"));
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
