/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;

import org.apache.commons.lang3.StringUtils;

import jakarta.servlet.http.HttpServletResponse;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 上游（Runtime）真实 OTel 标识透传常量与工具（issue 1754）。
 *
 * <p>Runtime 在根 Span 建立后输出 {@code X-OTel-Trace-Id}（32 位 hex）与 W3C
 * {@code traceresponse}；Manager 只做透传，不生成、不改写、不推断。
 *
 * <p>安全约束（检视意见）：上游头可能被异常/恶意 Runtime 伪造，必须严格校验格式；
 * 帧字段注入必须走 JSON 反序列化，禁止字符串拼接（否则可注入额外 JSON 字段）。
 */
public final class UpstreamOtelHeaders {

    /** 便于一键查询的 trace id 头（非 W3C 标准，Runtime/Manager 约定）。 */
    public static final String X_OTEL_TRACE_ID = "X-OTel-Trace-Id";

    /** W3C Trace Context 响应头：{@code 00-<trace-id>-<parent-id>-<flags>}。 */
    public static final String TRACERESPONSE = "traceresponse";

    /** trace id：32 位小写 hex（W3C 规定非全零；此处只做格式校验，避免过度拒绝）。 */
    private static final Pattern TRACE_ID_PATTERN = Pattern.compile("^[0-9a-f]{32}$");

    /** traceresponse：{@code 00-<32hex>-<16hex>-<2hex>}。 */
    private static final Pattern TRACE_RESPONSE_PATTERN =
        Pattern.compile("^00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}$");

    private UpstreamOtelHeaders() {
    }

    /**
     * 只抓取两个 OTel 响应头并校验格式；非法/空值丢弃（不臆造、不注入）。
     */
    public static Map<String, String> capture(okhttp3.Response response) {
        if (response == null) {
            return Collections.emptyMap();
        }
        Map<String, String> captured = new LinkedHashMap<>(2);
        String traceId = response.header(X_OTEL_TRACE_ID);
        boolean validTraceId = StringUtils.isNotBlank(traceId)
            && TRACE_ID_PATTERN.matcher(traceId).matches();
        if (validTraceId) {
            captured.put(X_OTEL_TRACE_ID, traceId);
        }
        String traceResponse = response.header(TRACERESPONSE);
        Matcher matcher = traceResponse == null ? null : TRACE_RESPONSE_PATTERN.matcher(traceResponse);
        // traceresponse 的 trace-id 必须与 X-OTel-Trace-Id 一致（防拼接头）
        if (matcher != null && matcher.matches()
            && (!validTraceId || matcher.group(1).equals(traceId))) {
            captured.put(TRACERESPONSE, traceResponse);
        }
        return captured.isEmpty() ? Collections.emptyMap() : captured;
    }

    /**
     * 给上游 SSE 帧补齐 {@code otel_trace_id/otel_span_id}（issue 1754）。
     *
     * <p>Manager 派生的 listener 会重组部分帧从而丢掉这两个字段；此处用 JSON
     * 反序列化 + 回写对象（不经字符串拼接，避免 JSON 注入），已含该字段时原样返回。
     */
    public static String decorateFrame(String data, Map<String, String> headers) {
        if (data == null || headers == null || headers.isEmpty()) {
            return data;
        }
        String traceId = headers.get(X_OTEL_TRACE_ID);
        if (traceId == null || !TRACE_ID_PATTERN.matcher(traceId).matches()) {
            return data;
        }
        String trimmed = data.strip();
        if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) {
            return data;
        }
        try {
            JSONObject frame = JSON.parseObject(trimmed);
            if (frame == null || frame.containsKey("otel_trace_id")) {
                return data;
            }
            frame.put("otel_trace_id", traceId);
            String spanId = spanIdOf(headers.get(TRACERESPONSE));
            if (StringUtils.isNotEmpty(spanId)) {
                frame.put("otel_span_id", spanId);
            }
            return frame.toJSONString();
        } catch (Exception ignored) {
            // 非 JSON 对象或无合法结构：原样透传（不臆造）
            return data;
        }
    }

    /**
     * 从 W3C traceresponse（{@code 00-<trace>-<span>-<flags>}）取 span id；
     * 非合法格式返回空串（不解析、不外发）。
     */
    public static String spanIdOf(String traceResponse) {
        if (traceResponse == null) {
            return "";
        }
        Matcher matcher = TRACE_RESPONSE_PATTERN.matcher(traceResponse);
        return matcher.matches() ? matcher.group(2) : "";
    }

    /**
     * 写回下游响应头；必须在响应提交（首个 SSE 帧写出）前调用。
     */
    public static void apply(HttpServletResponse response, Map<String, String> headers) {
        if (response == null || headers == null || headers.isEmpty()) {
            return;
        }
        headers.forEach(response::setHeader);
    }
}