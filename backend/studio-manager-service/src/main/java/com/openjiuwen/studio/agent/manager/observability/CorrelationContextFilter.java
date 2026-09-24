/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.util.Map;
import java.util.UUID;

import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Manager 唯一 HTTP request/trace 选值与四 key 外层 MDC scope（COM-05 §11）。
 *
 * <p>首次 REQUEST 派发按 {@code valid(X-Request-Id) ? 原值 : UUID}、
 * {@code valid(TraceID) ? 原值 : request_id} 选值一次，保存到 request attribute；
 * 独立 ASYNC/ERROR 再派发只复用同值，不生成第二组 ID（§11.3）。
 * 非法 Header 原值被忽略替换，不进 MDC 也不回显（§11.1）。
 *
 * <p>每次实际进入本 Filter 的派发先写响应 Header（保证认证短路、404、
 * 参数校验失败、ControllerAdvice 异常路径也携带同值，§11.4），再用
 * {@link MdcScope#open(Map)} 一次性覆盖四个白名单 key：本请求 request/trace +
 * 显式空 execution/conversation——清除容器工作线程历史残留；close 恢复入站前状态。
 * DEF-02 的 execution scope 与会话拦截器的 conversation scope 是内层部分覆盖，
 * 关闭后回到外层空值。本 Filter 不选择 execution_id，也不从任何 Header/body 推断
 * conversation_id（§11.2）。
 *
 * <p>注册约束（§11.3）：由 {@link CorrelationFilterConfig} 显式注册为 Manager
 * 可控应用 Filter 的最外层（{@code HIGHEST_PRECEDENCE}），dispatcher types 显式为
 * REQUEST/ASYNC/ERROR；本类不得加 {@code @Component}，避免 Boot 自动注册第二份。
 */
public class CorrelationContextFilter extends OncePerRequestFilter {

    /** 入站/回写 Header 名：X-Request-Id。 */
    public static final String REQUEST_ID_HEADER = "X-Request-Id";

    /** 入站/回写 Header 名：TraceID。 */
    public static final String TRACE_ID_HEADER = "TraceID";

    /** 首次 REQUEST 派发选值后保存的 request attribute：request_id。 */
    public static final String REQUEST_ID_ATTRIBUTE = CorrelationContextFilter.class.getName() + ".REQUEST_ID";

    /** 首次 REQUEST 派发选值后保存的 request attribute：trace_id。 */
    public static final String TRACE_ID_ATTRIBUTE = CorrelationContextFilter.class.getName() + ".TRACE_ID";

    @Override
    protected boolean shouldNotFilterAsyncDispatch() {
        // §11.3：OncePerRequestFilter 默认跳过 ASYNC 派发，必须显式覆盖
        return false;
    }

    @Override
    protected boolean shouldNotFilterErrorDispatch() {
        // §11.3：独立 ERROR 再派发需重建同值 scope
        return false;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
        String requestId = (String) request.getAttribute(REQUEST_ID_ATTRIBUTE);
        String traceId = (String) request.getAttribute(TRACE_ID_ATTRIBUTE);
        if (requestId == null) {
            String headerRequestId = request.getHeader(REQUEST_ID_HEADER);
            requestId = CorrelationIdValidator.isValid(headerRequestId) ? headerRequestId
                : UUID.randomUUID().toString();
            String headerTraceId = request.getHeader(TRACE_ID_HEADER);
            traceId = CorrelationIdValidator.isValid(headerTraceId) ? headerTraceId : requestId;
            request.setAttribute(REQUEST_ID_ATTRIBUTE, requestId);
            request.setAttribute(TRACE_ID_ATTRIBUTE, traceId);
        }
        if (traceId == null) {
            traceId = requestId;
            request.setAttribute(TRACE_ID_ATTRIBUTE, traceId);
        }
        // 先写响应 Header 再进链：内层任意短路/异常出口都携带同值
        response.setHeader(REQUEST_ID_HEADER, requestId);
        response.setHeader(TRACE_ID_HEADER, traceId);
        try (MdcScope scope = MdcScope.open(Map.of(
            MdcKeys.REQUEST_ID, requestId,
            MdcKeys.TRACE_ID, traceId,
            MdcKeys.EXECUTION_ID, "",
            MdcKeys.CONVERSATION_ID, ""))) {
            filterChain.doFilter(request, response);
        }
    }
}
