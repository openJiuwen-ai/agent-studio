/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.contract;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.error.ErrorDescriptor;

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
     *
     * @return Map 形式的 {@code {event:"error", data:{...}}}
     */
    public Map<String, Object> buildEnvelope(ErrorDescriptor descriptor, Locale locale) {
        String errorMsg = safeResolve(descriptor.getMessageKey(), locale);
        String errorReason = safeResolve(descriptor.getReasonKey(), locale);
        String errorSuggestion = safeResolve(descriptor.getSuggestionKey(), locale);

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

    /** COM-03 §4: fail-closed——resolver 异常或空值时抛出,不返回空串。 */
    private String safeResolve(String key, Locale locale) {
        String result = resolver.resolve(key, locale);
        if (result == null || result.isBlank()) {
            throw new IllegalStateException(
                "i18n resolution returned blank for key=" + key + " locale=" + locale);
        }
        return result;
    }
}
