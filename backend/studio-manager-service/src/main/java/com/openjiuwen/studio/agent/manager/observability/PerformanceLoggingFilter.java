/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * HTTP 请求性能日志：写入 log4j2 {@code PERFORM_LOGGER} → {@code perform.log}。
 *
 * <p>对齐 Python runtime {@code performance_logger} 的管道分隔埋点风格，记录
 * {@code http_request|METHOD|URI|status|durationMs}。须注册在
 * {@link CorrelationContextFilter} 内侧，以便带上 MDC 四 key。
 *
 * <p>#1654 / #1723：补齐死 appender 的业务写入侧。
 */
public class PerformanceLoggingFilter extends OncePerRequestFilter {

    /** 与 log4j2.xml {@code Logger name="PERFORM_LOGGER"} 对齐。 */
    public static final String LOGGER_NAME = "PERFORM_LOGGER";

    private static final Logger PERFORM_LOGGER = LogManager.getLogger(LOGGER_NAME);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
        long startNanos = System.nanoTime();
        try {
            filterChain.doFilter(request, response);
        } finally {
            if (shouldLog(request)) {
                long durationMs = (System.nanoTime() - startNanos) / 1_000_000L;
                String uri = request.getRequestURI();
                String query = request.getQueryString();
                String path = query == null || query.isEmpty() ? uri : uri + "?" + query;
                PERFORM_LOGGER.info("http_request|{}|{}|{}|{}",
                    request.getMethod(), path, response.getStatus(), durationMs);
            }
        }
    }

    private static boolean shouldLog(HttpServletRequest request) {
        String uri = request.getRequestURI();
        if (uri == null) {
            return false;
        }
        // 跳过探活，避免刷屏
        return !"/health".equals(uri) && !uri.startsWith("/actuator");
    }
}
