/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.servlet.DispatcherType;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

/**
 * #1654/#1723：性能 Filter 须放行链路、支持 ASYNC/ERROR 再派发，且不因探活崩溃。
 */
class PerformanceLoggingFilterTest {

    private final PerformanceLoggingFilter filter = new PerformanceLoggingFilter();

    @Test
    void loggerName_matchesLog4jConfig() {
        assertEquals("PERFORM_LOGGER", PerformanceLoggingFilter.LOGGER_NAME);
    }

    @Test
    void shouldNotFilterAsyncAndErrorDispatch_overriddenToFalse() throws Exception {
        java.lang.reflect.Method async =
            org.springframework.web.filter.OncePerRequestFilter.class.getDeclaredMethod("shouldNotFilterAsyncDispatch");
        async.setAccessible(true);
        java.lang.reflect.Method error =
            org.springframework.web.filter.OncePerRequestFilter.class.getDeclaredMethod("shouldNotFilterErrorDispatch");
        error.setAccessible(true);
        assertThat(async.invoke(filter)).isEqualTo(false);
        assertThat(error.invoke(filter)).isEqualTo(false);
    }

    @Test
    void businessRequest_invokesChain() throws Exception {
        HttpServletRequest request = mock(HttpServletRequest.class);
        HttpServletResponse response = mock(HttpServletResponse.class);
        FilterChain chain = mock(FilterChain.class);
        when(request.getRequestURI()).thenReturn("/v1/0/agent-manager/agents");
        // Sensitive query must not be required for logging; Filter omits query string.
        when(request.getQueryString()).thenReturn("token=secret&password=p");
        when(request.getMethod()).thenReturn("POST");
        when(request.getDispatcherType()).thenReturn(DispatcherType.REQUEST);
        when(request.isAsyncStarted()).thenReturn(false);
        when(response.getStatus()).thenReturn(400);

        assertDoesNotThrow(() -> filter.doFilter(request, response, chain));
        verify(chain).doFilter(request, response);
    }

    @Test
    void healthRequest_stillInvokesChain() throws Exception {
        HttpServletRequest request = mock(HttpServletRequest.class);
        HttpServletResponse response = mock(HttpServletResponse.class);
        FilterChain chain = mock(FilterChain.class);
        when(request.getRequestURI()).thenReturn("/health");
        when(request.getMethod()).thenReturn("GET");
        when(request.getDispatcherType()).thenReturn(DispatcherType.REQUEST);
        when(request.isAsyncStarted()).thenReturn(false);
        when(response.getStatus()).thenReturn(200);

        assertDoesNotThrow(() -> filter.doFilter(request, response, chain));
        verify(chain).doFilter(request, response);
    }

    @Test
    void asyncStart_defersLogging_untilAsyncDispatch() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, (req, res) -> {
            // Simulate Servlet async: REQUEST returns before completion.
            ((MockHttpServletRequest) req).setAsyncStarted(true);
            ((HttpServletResponse) res).setStatus(200);
        });

        assertThat(request.getAttribute(PerformanceLoggingFilter.START_NANOS_ATTRIBUTE)).isNotNull();
        assertThat(request.getAttribute(PerformanceLoggingFilter.LOGGED_ATTRIBUTE)).isNull();

        request.setAsyncStarted(false);
        request.setDispatcherType(DispatcherType.ASYNC);
        response.setStatus(201);
        filter.doFilter(request, response, (req, res) -> ((HttpServletResponse) res).setStatus(201));

        assertThat(request.getAttribute(PerformanceLoggingFilter.LOGGED_ATTRIBUTE)).isEqualTo(Boolean.TRUE);
    }

    @Test
    void uncaughtExceptionOnRequest_defersLogging_untilErrorDispatch() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        MockHttpServletResponse response = new MockHttpServletResponse();

        try {
            filter.doFilter(request, response, new FilterChain() {
                @Override
                public void doFilter(ServletRequest req, ServletResponse res) throws IOException, ServletException {
                    throw new ServletException("boom");
                }
            });
        } catch (ServletException expected) {
            assertThat(expected.getMessage()).isEqualTo("boom");
        }

        assertThat(request.getAttribute(PerformanceLoggingFilter.START_NANOS_ATTRIBUTE)).isNotNull();
        assertThat(request.getAttribute(PerformanceLoggingFilter.LOGGED_ATTRIBUTE)).isNull();

        request.setDispatcherType(DispatcherType.ERROR);
        response.setStatus(500);
        filter.doFilter(request, response, (req, res) -> {
        });

        assertThat(request.getAttribute(PerformanceLoggingFilter.LOGGED_ATTRIBUTE)).isEqualTo(Boolean.TRUE);
    }

    @Test
    void errorDispatch_doesNotDoubleLog_afterSuccessfulRequestLog() throws Exception {
        MockHttpServletRequest request = request(DispatcherType.REQUEST);
        MockHttpServletResponse response = new MockHttpServletResponse();
        response.setStatus(404);

        filter.doFilter(request, response, (req, res) -> ((HttpServletResponse) res).setStatus(404));
        assertThat(request.getAttribute(PerformanceLoggingFilter.LOGGED_ATTRIBUTE)).isEqualTo(Boolean.TRUE);

        Object start = request.getAttribute(PerformanceLoggingFilter.START_NANOS_ATTRIBUTE);
        request.setDispatcherType(DispatcherType.ERROR);
        filter.doFilter(request, response, (req, res) -> {
        });

        // Still logged exactly once; start nanos reused, attribute unchanged.
        assertThat(request.getAttribute(PerformanceLoggingFilter.LOGGED_ATTRIBUTE)).isEqualTo(Boolean.TRUE);
        assertThat(request.getAttribute(PerformanceLoggingFilter.START_NANOS_ATTRIBUTE)).isSameAs(start);
    }

    private static MockHttpServletRequest request(DispatcherType type) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/v1/0/agent-manager/agents");
        request.setDispatcherType(type);
        return request;
    }
}
