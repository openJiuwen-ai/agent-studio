/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.junit.jupiter.api.Test;

/**
 * #1654/#1723：性能 Filter 须放行链路且不因探活崩溃；写入侧由 E2E/配置契约覆盖。
 */
class PerformanceLoggingFilterTest {

    @Test
    void loggerName_matchesLog4jConfig() {
        assertEquals("PERFORM_LOGGER", PerformanceLoggingFilter.LOGGER_NAME);
    }

    @Test
    void businessRequest_invokesChain() throws Exception {
        HttpServletRequest request = mock(HttpServletRequest.class);
        HttpServletResponse response = mock(HttpServletResponse.class);
        FilterChain chain = mock(FilterChain.class);
        when(request.getRequestURI()).thenReturn("/v1/0/agent-manager/agents");
        when(request.getQueryString()).thenReturn("workspace_id=ws1");
        when(request.getMethod()).thenReturn("POST");
        when(response.getStatus()).thenReturn(400);

        assertDoesNotThrow(() -> new PerformanceLoggingFilter().doFilter(request, response, chain));
        verify(chain).doFilter(request, response);
    }

    @Test
    void healthRequest_stillInvokesChain() throws Exception {
        HttpServletRequest request = mock(HttpServletRequest.class);
        HttpServletResponse response = mock(HttpServletResponse.class);
        FilterChain chain = mock(FilterChain.class);
        when(request.getRequestURI()).thenReturn("/health");
        when(request.getMethod()).thenReturn("GET");
        when(response.getStatus()).thenReturn(200);

        assertDoesNotThrow(() -> new PerformanceLoggingFilter().doFilter(request, response, chain));
        verify(chain).doFilter(request, response);
    }
}
