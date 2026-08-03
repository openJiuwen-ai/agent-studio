/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.common.filter.simple;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.InvalidPlatformTokenException;
import com.openjiuwen.studio.agent.common.customerheader.PlatformAuthProtocolException;
import com.openjiuwen.studio.agent.common.customerheader.PlatformAuthServiceUnavailableException;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipal;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipalResolver;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.common.utils.simple.ServletUtils;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.io.PrintWriter;
import java.io.StringWriter;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
public class SimpleUserContextFilterTest {

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain filterChain;

    @Mock
    private PlatformPrincipalResolver platformPrincipalResolver;

    private MockedStatic<SpringBeanUtils> springBeanUtilsMock;
    private MockedStatic<ServletUtils> servletUtilsMock;

    private SimpleUserContextFilter filter;

    private static final PlatformPrincipal TEST_PRINCIPAL = new PlatformPrincipal(
        "user1", "test-token", "TestUser", "proj-1", "dom-1", "Domain1"
    );

    @BeforeEach
    void setUp() throws Exception {
        filter = new SimpleUserContextFilter(platformPrincipalResolver, new CustomerHeaderProfile());
        springBeanUtilsMock = mockStatic(SpringBeanUtils.class);
        servletUtilsMock = mockStatic(ServletUtils.class);
        springBeanUtilsMock.when(() -> SpringBeanUtils.getProperty(eq(SimpleConstants.SERVLET_CONTEXT_PATH), anyString()))
            .thenReturn("");
        lenient().when(response.getWriter()).thenReturn(new PrintWriter(new StringWriter()));
    }

    @AfterEach
    void tearDown() {
        springBeanUtilsMock.close();
        servletUtilsMock.close();
    }

    @Test
    void testDoFilter_PathNotMatching() throws Exception {
        when(request.getRequestURI()).thenReturn("/other/path");

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_HealthPath() throws Exception {
        when(request.getRequestURI()).thenReturn("/health");

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_AuthTokenUri() throws Exception {
        when(request.getRequestURI()).thenReturn(SimpleConstants.AUTH_TOKEN_URI);

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_V1Path_EmptySid() throws Exception {
        when(request.getRequestURI()).thenReturn("/v1/agents");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn(null);

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_V2Path_EmptySid() throws Exception {
        when(request.getRequestURI()).thenReturn("/v2/workflows");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("");

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_V3Path_WithSid_SuccessfulResponse() throws Exception {
        when(request.getRequestURI()).thenReturn("/v3/some-api");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("test-sid");
        when(platformPrincipalResolver.resolveOrThrow("test-sid")).thenReturn(TEST_PRINCIPAL);

        filter.doFilter(request, response, filterChain);

        verify(request).setAttribute(eq("CURRENT_USER"), any());
        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_V3Path_WithSid_InvalidToken() throws Exception {
        when(request.getRequestURI()).thenReturn("/v3/some-api");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("test-sid");
        when(platformPrincipalResolver.resolveOrThrow("test-sid"))
            .thenThrow(new InvalidPlatformTokenException("token expired"));

        filter.doFilter(request, response, filterChain);

        verify(response).setStatus(401);
        verify(request, never()).setAttribute(eq("CURRENT_USER"), any());
        verify(filterChain, never()).doFilter(request, response);
    }

    @Test
    void testDoFilter_V3Path_WithSid_AuthServiceUnavailable() throws Exception {
        when(request.getRequestURI()).thenReturn("/v3/some-api");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("test-sid");
        when(platformPrincipalResolver.resolveOrThrow("test-sid"))
            .thenThrow(new PlatformAuthServiceUnavailableException("auth down"));

        filter.doFilter(request, response, filterChain);

        verify(response).setStatus(503);
        verify(request, never()).setAttribute(eq("CURRENT_USER"), any());
        verify(filterChain, never()).doFilter(request, response);
    }

    @Test
    void testDoFilter_V3Path_WithSid_ProtocolError() throws Exception {
        when(request.getRequestURI()).thenReturn("/v3/some-api");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("test-sid");
        when(platformPrincipalResolver.resolveOrThrow("test-sid"))
            .thenThrow(new PlatformAuthProtocolException("bad response"));

        filter.doFilter(request, response, filterChain);

        verify(response).setStatus(500);
        verify(request, never()).setAttribute(eq("CURRENT_USER"), any());
        verify(filterChain, never()).doFilter(request, response);
    }

    @Test
    void testDoFilter_WithContextPath() throws Exception {
        springBeanUtilsMock.when(() -> SpringBeanUtils.getProperty(eq(SimpleConstants.SERVLET_CONTEXT_PATH), anyString()))
            .thenReturn("/api");
        when(request.getRequestURI()).thenReturn("/api/v1/agents");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn(null);

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_WithContextPath_AuthTokenUri() throws Exception {
        springBeanUtilsMock.when(() -> SpringBeanUtils.getProperty(eq(SimpleConstants.SERVLET_CONTEXT_PATH), anyString()))
            .thenReturn("/api");
        when(request.getRequestURI()).thenReturn("/api/v3/auth/tokens");

        filter.doFilter(request, response, filterChain);

        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDoFilter_V1Path_WithSid_SuccessfulResponse() throws Exception {
        when(request.getRequestURI()).thenReturn("/v1/agents");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("test-sid");
        when(platformPrincipalResolver.resolveOrThrow("test-sid")).thenReturn(TEST_PRINCIPAL);

        filter.doFilter(request, response, filterChain);

        verify(request).setAttribute(eq("CURRENT_USER"), any());
        verify(filterChain, times(1)).doFilter(request, response);
    }

    /**
     * M8：effective userId 查找的 header 名应由 profile.identity.user-id-header 驱动，
     * 而非硬编码常量 cust-userid（设计  L148 /  L72：新客户只加 profile 不改代码）。
     *
     * <p>用非默认名 cmb-userid 构造 profile，断言 Filter 按 cmb-userid 查找、
     * 且不再查询硬编码的 cust-userid。
     */
    @Test
    void testDoFilter_ProfileEnabled_EffectiveUserIdFromConfiguredHeader() throws Exception {
        CustomerHeaderProfile profile = mock(CustomerHeaderProfile.class);
        when(profile.isEnabledInSimpleMode()).thenReturn(true);
        when(profile.getUserIdHeader()).thenReturn("cmb-userid");
        // 空 capture 白名单，隔离 effective 查找的 getHeader 调用
        when(profile.getCaptureAllowList()).thenReturn(new String[0]);

        SimpleUserContextFilter profileFilter =
            new SimpleUserContextFilter(platformPrincipalResolver, profile);

        when(request.getRequestURI()).thenReturn("/v1/agents");
        servletUtilsMock.when(() -> ServletUtils.getAgentSid(request)).thenReturn("test-sid");
        when(platformPrincipalResolver.resolveOrThrow("test-sid")).thenReturn(TEST_PRINCIPAL);
        when(request.getHeader("cmb-userid")).thenReturn("customer-user-42");

        profileFilter.doFilter(request, response, filterChain);

        // effective 查找使用 profile 配置的 header 名
        verify(request, atLeastOnce()).getHeader("cmb-userid");
        // 硬编码常量 cust-userid 不再被使用
        verify(request, never()).getHeader("cust-userid");
        verify(request).setAttribute(eq("CURRENT_USER"), any());
        verify(filterChain, times(1)).doFilter(request, response);
    }

    @Test
    void testDestroy_NoException() {
        assertDoesNotThrow(() -> filter.destroy());
    }
}