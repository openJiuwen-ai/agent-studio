/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.UUID;

import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

/**
 * 无 HTTP Filter 入口的后台路径（如异步工作流定时拉起）补齐 {@code request-id}/{@code trace_id}。
 *
 * <p>选值规则对齐 {@link CorrelationContextFilter}：合法 MDC → 合法入站 Header → 新 UUID；
 * {@code trace_id} 缺失时回退为 {@code request-id}。不写入 MDC——由调用方用 {@link MdcScope} 安装。
 */
public final class AsyncCorrelationIds {

    private AsyncCorrelationIds() {
    }

    /** 解析得到的关联 ID 对。 */
    public record Pair(String requestId, String traceId) {
    }

    /**
     * 解析异步出站所需的 request/trace。
     *
     * @param headers 任务创建时缓存的入站 Header（可为 null）
     */
    public static Pair resolve(HttpHeaders headers) {
        String requestId = firstValid(
            MDC.get(MdcKeys.REQUEST_ID),
            header(headers, CorrelationContextFilter.REQUEST_ID_HEADER));
        if (requestId == null) {
            requestId = UUID.randomUUID().toString();
        }
        String traceId = firstValid(
            MDC.get(MdcKeys.TRACE_ID),
            header(headers, CorrelationContextFilter.TRACE_ID_HEADER));
        if (traceId == null) {
            traceId = requestId;
        }
        return new Pair(requestId, traceId);
    }

    private static String firstValid(String primary, String secondary) {
        if (CorrelationIdValidator.isValid(primary)) {
            return primary;
        }
        if (CorrelationIdValidator.isValid(secondary)) {
            return secondary;
        }
        return null;
    }

    private static String header(HttpHeaders headers, String name) {
        return headers == null ? null : headers.getFirst(name);
    }
}
