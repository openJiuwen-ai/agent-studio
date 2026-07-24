/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.filter;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;
import com.openjiuwen.studio.agent.common.security.service.SsoAuthenticationService;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.PrintWriter;
import java.util.Collections;
import java.util.List;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * SsoAuthenticationFilter 单元测试
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
public class SsoAuthenticationFilterTest {

    @Mock
    private SsoAuthenticationService ssoAuthenticationService;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain filterChain;

    @Mock
    private PrintWriter writer;

    private static final String HEADER_NAME = "X-Auth-Token";

    private SsoAuthenticationFilter filter;

    private AuthProperties authProperties;

    @BeforeEach
    void setUp() {
        SecurityContextHolder.clearContext();
        authProperties = new AuthProperties();
        filter = new SsoAuthenticationFilter(HEADER_NAME, ssoAuthenticationService, authProperties);
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private void setExcludedPaths(List<String> paths) {
        ReflectionTestUtils.setField(filter, "excludePaths", paths);
    }

    // 场景：请求路径在排除列表中时，直接通过过滤器链
    @Test
    void doFilter_excludedPath_shouldPassThrough() throws Exception {
        setExcludedPaths(List.of("/v1/**"));

        when(request.getRequestURI()).thenReturn("/v1/health");
        when(response.getWriter()).thenReturn(writer);

        filter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        verify(ssoAuthenticationService, never()).authenticate(anyString());
    }

    // 场景：排除列表为空时，不排除任何路径
    @Test
    void doFilter_emptyExcludePaths_shouldNotExclude() throws Exception {
        setExcludedPaths(Collections.emptyList());

        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("valid-token");
        when(response.getWriter()).thenReturn(writer);
        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("valid-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("valid-token");
        verify(filterChain).doFilter(request, response);
    }

    // 场景：请求头中没有token，Cookie中也没有token，返回401
    @Test
    void doFilter_noTokenInHeaderAndCookie_shouldReturn401() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn(null);
        when(request.getCookies()).thenReturn(null);
        when(response.getWriter()).thenReturn(writer);

        filter.doFilterInternal(request, response, filterChain);

        verify(response).setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        verify(response).setContentType("application/json");
        verify(writer).write("{\"code\":\"40101\",\"message\":\"Unauthorized: missing access token\"}");
        verify(filterChain, never()).doFilter(any(), any());
    }

    // 场景：请求头中有空字符串token，Cookie中也无token，返回401
    @Test
    void doFilter_emptyTokenInHeader_shouldReturn401() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("");
        when(request.getCookies()).thenReturn(null);
        when(response.getWriter()).thenReturn(writer);

        filter.doFilterInternal(request, response, filterChain);

        verify(response).setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        verify(filterChain, never()).doFilter(any(), any());
    }

    // 场景：请求头中没有token，但Cookie中有token，鉴权成功
    @Test
    void doFilter_tokenFromCookie_shouldAuthenticate() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn(null);

        Cookie authCookie = new Cookie(HEADER_NAME, "cookie-token");
        Cookie otherCookie = new Cookie("other", "value");
        when(request.getCookies()).thenReturn(new Cookie[]{otherCookie, authCookie});

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("cookie-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("cookie-token");
        verify(filterChain).doFilter(request, response);

        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        assert authentication != null;
        assert authentication.getPrincipal() instanceof SimpleUser;
        assert ((SimpleUser) authentication.getPrincipal()).getUserId().equals("user1");
    }

    // 场景：Cookie为空数组时，应从header中获取token
    @Test
    void doFilter_emptyCookieArray_shouldFallbackToHeader() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("header-token");
        when(request.getCookies()).thenReturn(new Cookie[0]);

        SimpleUser userInfo = SimpleUser.builder().userId("user2").userName("testUser2").domainId("domain2").projectId("proj2").build();
        when(ssoAuthenticationService.authenticate("header-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("header-token");
        verify(filterChain).doFilter(request, response);
    }

    // 场景：鉴权成功，设置SecurityContext和request属性
    @Test
    void doFilter_authenticationSuccess_shouldSetContextAndProceed() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("valid-token");

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("valid-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);

        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        assert authentication != null;
        assert authentication.getPrincipal().equals(userInfo);
        assert authentication.getAuthorities().stream()
            .anyMatch(a -> a.getAuthority().equals("ROLE_USER"));

        verify(request).setAttribute("CURRENT_USER", userInfo);
        assert "valid-token".equals(userInfo.getToken());
    }

    // 场景：鉴权返回null用户信息，返回401
    @Test
    void doFilter_authenticationReturnsNull_shouldReturn401() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("invalid-token");
        when(response.getWriter()).thenReturn(writer);
        when(ssoAuthenticationService.authenticate("invalid-token")).thenReturn(null);

        filter.doFilterInternal(request, response, filterChain);

        verify(response).setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        verify(response).setContentType("application/json");
        verify(writer).write("{\"code\":\"40101\",\"message\":\"Unauthorized: invalid token\"}");
        verify(filterChain, never()).doFilter(any(), any());
        assert SecurityContextHolder.getContext().getAuthentication() == null;
    }

    // 场景：鉴权抛出异常，返回401
    @Test
    void doFilter_authenticationThrowsException_shouldReturn401() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("error-token");
        when(response.getWriter()).thenReturn(writer);
        when(ssoAuthenticationService.authenticate("error-token")).thenThrow(new RuntimeException("Connection refused"));

        filter.doFilterInternal(request, response, filterChain);

        verify(response).setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        verify(response).setContentType("application/json");
        verify(writer).write("{\"code\":\"40101\",\"message\":\"Unauthorized: authentication failed\"}");
        verify(filterChain, never()).doFilter(any(), any());
        assert SecurityContextHolder.getContext().getAuthentication() == null;
    }

    // 场景：排除路径使用Ant模式匹配
    @Test
    void doFilter_antPatternExcludedPath_shouldPassThrough() throws Exception {
        setExcludedPaths(List.of("/public/**", "/health"));

        when(request.getRequestURI()).thenReturn("/public/resource/sub");
        when(response.getWriter()).thenReturn(writer);

        filter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        verify(ssoAuthenticationService, never()).authenticate(anyString());
    }

    // 场景：排除路径不匹配时，继续鉴权流程
    @Test
    void doFilter_antPatternNotMatched_shouldContinueAuth() throws Exception {
        setExcludedPaths(List.of("/public/**"));

        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("valid-token");

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("valid-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("valid-token");
        verify(filterChain).doFilter(request, response);
    }

    // 场景：鉴权成功时，IamContext被正确设置到request属性中
    @Test
    void doFilter_authenticationSuccess_shouldSetIamContext() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("valid-token");

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("valid-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);
    }

    // 场景：Cookie中有token但名称不匹配（大小写不敏感），仍可获取
    @Test
    void doFilter_cookieNameCaseInsensitive_shouldGetToken() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn(null);

        Cookie authCookie = new Cookie("x-auth-token", "cookie-token");
        when(request.getCookies()).thenReturn(new Cookie[]{authCookie});

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("cookie-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("cookie-token");
    }

    // 场景：请求头有token优先使用请求头的token，不检查Cookie
    @Test
    void doFilter_tokenInHeader_shouldNotCheckCookie() throws Exception {
        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("header-token");

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("header-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("header-token");
        verify(request, never()).getCookies();
    }

    // 场景：排除列表为null时，不排除任何路径
    @Test
    void doFilter_nullExcludePaths_shouldNotExclude() throws Exception {
        setExcludedPaths(null);

        when(request.getRequestURI()).thenReturn("/api/data");
        when(request.getHeader(HEADER_NAME)).thenReturn("valid-token");

        SimpleUser userInfo = SimpleUser.builder().userId("user1").userName("testUser").domainId("domain1").projectId("proj1").build();
        when(ssoAuthenticationService.authenticate("valid-token")).thenReturn(userInfo);

        filter.doFilterInternal(request, response, filterChain);

        verify(ssoAuthenticationService).authenticate("valid-token");
        verify(filterChain).doFilter(request, response);
    }
}
