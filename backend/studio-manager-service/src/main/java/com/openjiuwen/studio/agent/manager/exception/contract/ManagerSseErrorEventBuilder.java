/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;
import com.openjiuwen.studio.agent.common.error.PassthroughText;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * COM-03 §6.1: Manager SSE 错误事件构建器。
 * <p>
 * 输入 ErrorDescriptor + Locale，输出统一 {@code event="error"} envelope。
 * 只负责序列化，不选码、不读原始异常、不递归创建第二个 error。
 */
public class ManagerSseErrorEventBuilder {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final ManagerHttpErrorResponseBuilder.I18nResolver resolver;

    public ManagerSseErrorEventBuilder(ManagerHttpErrorResponseBuilder.I18nResolver resolver) {
        this.resolver = resolver;
    }

    /**
     * 构建 SSE error 事件的业务 JSON envelope。
     * <p>
     * 统一族格式（COM-04 §5.2 修订二期，2026-11-02 用户裁定）：下游失败
     * （descriptor 携带组件标签）时 {@code error_msg=族前缀}、
     * {@code error_reason="组件{label}：{错误信息}"}；非下游错误保持
     * i18n 三键 + fail-closed 原行为。
     *
     * @return Map 形式的 {@code {event:"error", data:{...}}}
     */
    public Map<String, Object> buildEnvelope(ErrorDescriptor descriptor, Locale locale) {
        // 从异常 cause 提取 args 填 i18n 占位符（origin 10f62b9cd 特性）；族格式
        // 文案无占位符, 多传 args 被忽略, 与统一族格式兼容。
        Object[] args = extractArgs(descriptor);
        String label = descriptor.getDownstreamComponentLabel();
        String errorMsg;
        String errorReason;
        String errorSuggestion;
        if (label != null) {
            errorMsg = DownstreamFamilyFormat.message(resolver, args, locale);
            errorReason = DownstreamFamilyFormat.reason(resolver, descriptor, label, args, locale);
            errorSuggestion = DownstreamFamilyFormat.suggestion(resolver, descriptor, args, locale);
        } else {
            PassthroughText passthrough = descriptor.getPassthroughText();
            String messageFallback = passthrough != null ? passthrough.getMessage() : null;
            errorMsg = safeResolve(descriptor.getMessageKey(), args, locale, messageFallback);
            errorReason = safeResolve(descriptor.getReasonKey(), args, locale,
                passthrough != null ? firstNonBlank(passthrough.getReason(), messageFallback) : null);
            errorSuggestion = safeResolve(descriptor.getSuggestionKey(), args, locale,
                passthrough != null ? firstNonBlank(passthrough.getSuggestion(), messageFallback) : null);
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("error_code", descriptor.getErrorCode());
        data.put("error_msg", errorMsg);
        data.put("error_reason", errorReason);
        data.put("error_suggestion", errorSuggestion);
        data.put("request_id", descriptor.getRequestId());

        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("event", "error");
        envelope.put("data", data);
        return envelope;
    }

    /**
     * 将 envelope 编码为 SSE wire 格式字符串（{@code data: {...}\n\n}）。
     */
    public String formatSseEvent(ErrorDescriptor descriptor, Locale locale) {
        Map<String, Object> envelope = buildEnvelope(descriptor, locale);
        try {
            return "data: " + MAPPER.writeValueAsString(envelope) + "\n\n";
        } catch (JsonProcessingException e) {
            // COM-03 §5.5: 序列化失败不返回残缺帧——向调用边界报告失败,
            // 由 listener 记录一次安全日志并关闭,不递归发送 error。
            throw new RuntimeException("SSE JSON serialization failed", e);
        }
    }

    /**
     * COM-03 §4 fail-closed + COM-04 §5.2 修订（2026-11-02）回退：
     * 优先 i18n 解析（含"回显 key"视为未命中——I18nUtil 以 key 作默认值返回）；
     * 未命中且有受管三段文案回退值时使用回退值；否则按原 fail-closed 语义
     * 抛出（resolver 异常原样重抛，空值抛 IllegalStateException），不返回空串。
     */
    private String safeResolve(String key, Object[] args, Locale locale, String passthroughFallback) {
        String result = null;
        RuntimeException resolveError = null;
        try {
            result = resolver.resolve(key, args, locale);
        } catch (RuntimeException e) {
            resolveError = e;
        }
        boolean miss = result == null || result.isBlank() || key.equals(result);
        if (miss && passthroughFallback != null && !passthroughFallback.isBlank()) {
            return passthroughFallback;
        }
        if (resolveError != null) {
            throw resolveError;
        }
        if (result == null || result.isBlank()) {
            throw new IllegalStateException(
                "i18n resolution returned blank for key=" + key + " locale=" + locale);
        }
        return result;
    }

    /** 字段级回退链的第二跳：字段文案缺失时回退到 message（mapper 兜底之外的双保险）。 */
    private static String firstNonBlank(String primary, String secondary) {
        if (primary != null && !primary.isBlank()) {
            return primary;
        }
        if (secondary != null && !secondary.isBlank()) {
            return secondary;
        }
        return null;
    }

    /** 从 descriptor.cause 提取 i18n 占位符 args（同 ManagerHttpErrorResponseBuilder）。 */
    private Object[] extractArgs(ErrorDescriptor descriptor) {
        Throwable cause = descriptor.getCause();
        if (cause instanceof com.openjiuwen.studio.agent.common.exception.AgentStudioException ase) {
            return ase.getArgs();
        }
        return null;
    }
}
