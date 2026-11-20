/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.DispatcherType;
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
 * <p>只记 {@link HttpServletRequest#getRequestURI()}，不拼接 query string：
 * nginx access log 已对 password/token/key 等查询参数打码，原样写入会让敏感值在
 * manager 本地 {@code perform.log} 明文落盘（Vector redact 只保护转发链路）。
 *
 * <p>ASYNC/ERROR：须覆写 {@link #shouldNotFilterAsyncDispatch()} /
 * {@link #shouldNotFilterErrorDispatch()}（OncePerRequestFilter 默认均为 true）。
 * 首次 REQUEST 若 {@code startAsync}，此时 status/耗时尚未最终化，推迟到 ASYNC
 * 派发结束再记；起始时间保存在 request attribute。未处理异常从 REQUEST 抛出时
 * 推迟到 ERROR 派发，避免默认 200 提前落盘。同一请求只记一条（{@code LOGGED} attribute）。
 *
 * <p>#1654 / #1723：补齐死 appender 的业务写入侧。
 */
public class PerformanceLoggingFilter extends OncePerRequestFilter {

    /** 与 log4j2.xml {@code Logger name="PERFORM_LOGGER"} 对齐。 */
    public static final String LOGGER_NAME = "PERFORM_LOGGER";

    /** 首次进入本 Filter 时记录的 {@link System#nanoTime()}。 */
    static final String START_NANOS_ATTRIBUTE = PerformanceLoggingFilter.class.getName() + ".START_NANOS";

    /** 已写入 perform.log，防止 REQUEST+ERROR 双记。 */
    static final String LOGGED_ATTRIBUTE = PerformanceLoggingFilter.class.getName() + ".LOGGED";

    private static final Logger PERFORM_LOGGER = LogManager.getLogger(LOGGER_NAME);

    @Override
    protected boolean shouldNotFilterAsyncDispatch() {
        // 与 CorrelationContextFilter / CorrelationFilterConfig 的 ASYNC 注册对齐
        return false;
    }

    @Override
    protected boolean shouldNotFilterErrorDispatch() {
        // 与 CorrelationContextFilter / CorrelationFilterConfig 的 ERROR 注册对齐
        return false;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
        Long startNanos = (Long) request.getAttribute(START_NANOS_ATTRIBUTE);
        if (startNanos == null) {
            startNanos = System.nanoTime();
            request.setAttribute(START_NANOS_ATTRIBUTE, startNanos);
        }

        boolean failed = false;
        try {
            filterChain.doFilter(request, response);
        } catch (IOException | ServletException | RuntimeException ex) {
            failed = true;
            throw ex;
        } finally {
            logIfComplete(request, response, startNanos, failed);
        }
    }

    private static void logIfComplete(HttpServletRequest request, HttpServletResponse response, long startNanos,
        boolean failed) {
        if (!shouldLog(request)) {
            return;
        }
        // ASYNC 刚 start：REQUEST 派发会提前返回，等 ASYNC 派发结束再记。
        if (request.isAsyncStarted()) {
            return;
        }
        // 未处理异常仍在 REQUEST：容器通常会再走 ERROR 派发，避免此时默认 200 落盘。
        if (failed && request.getDispatcherType() == DispatcherType.REQUEST) {
            return;
        }
        if (Boolean.TRUE.equals(request.getAttribute(LOGGED_ATTRIBUTE))) {
            return;
        }
        request.setAttribute(LOGGED_ATTRIBUTE, Boolean.TRUE);
        long durationMs = (System.nanoTime() - startNanos) / 1_000_000L;
        PERFORM_LOGGER.info("http_request|{}|{}|{}|{}",
            request.getMethod(), request.getRequestURI(), response.getStatus(), durationMs);
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
