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
 * <p>按来源<strong>成组</strong>选值，避免 request/trace 来自不同来源而错配：
 * <ol>
 *   <li>入站 Header（Redis 缓存，本任务权威）：request 合法则采用；trace 仅取同组 Header，
 *       缺失/非法时回退为已选 request。</li>
 *   <li>仅当 request Header 不可用时，整体回退到 MDC（同样成组；trace 缺则回退 request）。</li>
 *   <li>再不行则生成新 UUID，trace 与 request 相同。</li>
 * </ol>
 * 不写入 MDC——由调用方用 {@link MdcScope} 安装。
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
        String headerRequest = header(headers, CorrelationContextFilter.REQUEST_ID_HEADER);
        if (CorrelationIdValidator.isValid(headerRequest)) {
            String headerTrace = header(headers, CorrelationContextFilter.TRACE_ID_HEADER);
            String traceId = CorrelationIdValidator.isValid(headerTrace) ? headerTrace : headerRequest;
            return new Pair(headerRequest, traceId);
        }

        String mdcRequest = MDC.get(MdcKeys.REQUEST_ID);
        if (CorrelationIdValidator.isValid(mdcRequest)) {
            String mdcTrace = MDC.get(MdcKeys.TRACE_ID);
            String traceId = CorrelationIdValidator.isValid(mdcTrace) ? mdcTrace : mdcRequest;
            return new Pair(mdcRequest, traceId);
        }

        String generated = UUID.randomUUID().toString();
        return new Pair(generated, generated);
    }

    private static String header(HttpHeaders headers, String name) {
        return headers == null ? null : headers.getFirst(name);
    }
}
