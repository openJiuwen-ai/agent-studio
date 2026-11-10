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
 * <p>选值规则：合法入站 Header（任务创建时缓存于 Redis，为本任务权威来源）→ 合法 MDC（缺省回退）
 * → 新 UUID；{@code trace_id} 缺失时回退为已选定的 {@code request-id}。
 * 不写入 MDC——由调用方用 {@link MdcScope} 安装。
 *
 * <p>故意不把 MDC 放在 Header 之前：线程池 worker 可能残留与当前任务无关的合法 MDC，
 * 若优先 MDC 会覆盖 Redis Header，并可能让 request/trace 来自不同来源而错配。
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
            header(headers, CorrelationContextFilter.REQUEST_ID_HEADER),
            MDC.get(MdcKeys.REQUEST_ID));
        if (requestId == null) {
            requestId = UUID.randomUUID().toString();
        }
        String traceId = firstValid(
            header(headers, CorrelationContextFilter.TRACE_ID_HEADER),
            MDC.get(MdcKeys.TRACE_ID));
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
