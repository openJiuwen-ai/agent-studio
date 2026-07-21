/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.filter;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;
import com.openjiuwen.studio.agent.common.security.service.SsoAuthenticationService;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.security.authentication.AuthenticationServiceException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;
import java.util.List;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * SSO 认证过滤器
 *
 * <p>拦截请求并从请求头或 Cookie 中提取 Access-Token，调用 SSO 鉴权服务验证身份。
 * 支持通过 Ant 模式配置排除路径（不需要鉴权的请求直接放行）。</p>
 */
@Slf4j
public class SsoAuthenticationFilter extends OncePerRequestFilter {

    private final String headerName;

    private final SsoAuthenticationService ssoAuthenticationService;

    private final List<String> excludePaths;

    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    private AuthenticationEntryPoint authenticationEntryPoint;

    /**
     * @param headerName              携带 Access-Token 的请求头名称
     * @param ssoAuthenticationService SSO 鉴权服务
     * @param authProperties           认证配置（含排除路径等）
     */
    public SsoAuthenticationFilter(String headerName, SsoAuthenticationService ssoAuthenticationService,
        AuthProperties authProperties) {
        this.headerName = headerName;
        this.ssoAuthenticationService = ssoAuthenticationService;
        this.excludePaths = authProperties.getPath().getExcluded();
    }

    /**
     * 设置认证失败入口点，用于统一处理未认证响应
     */
    public void setAuthenticationEntryPoint(AuthenticationEntryPoint authenticationEntryPoint) {
        this.authenticationEntryPoint = authenticationEntryPoint;
    }

    /**
     * 核心过滤逻辑：排除路径放行 → 提取 Token → 调用 SSO 鉴权 → 设置安全上下文
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
        String requestUri = request.getRequestURI();
        if (isExcluded(requestUri)) {
            filterChain.doFilter(request, response);
            return;
        }

        String accessToken = request.getHeader(headerName);
        if (StringUtils.isEmpty(accessToken)) {
            accessToken = getTokenFromCookie(request);
        }
        if (StringUtils.isEmpty(accessToken)) {
            accessToken = request.getHeader(Constants.Header.X_AUTH_TOKEN);
        }

        if (StringUtils.isEmpty(accessToken)) {
            log.warn("SSO authentication failed: request does not contain {}", headerName);
            handleAuthException(request, response, new BadCredentialsException("Unauthorized: missing access token"));
            return;
        }

        try {
            SimpleUser userInfo = ssoAuthenticationService.authenticate(accessToken);

            if (userInfo != null) {
                log.info("SSO authentication successful: userId={}", userInfo.getUserId());

                UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                    userInfo, null, Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")));
                authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

                SecurityContextHolder.getContext().setAuthentication(authentication);
                userInfo.setToken(accessToken);
                request.setAttribute("CURRENT_USER", userInfo);
                RequestContextUtils.setContext(userInfo);
            } else {
                log.warn("SSO authentication failed: invalid token");
                SecurityContextHolder.clearContext();
                handleAuthException(request, response, new BadCredentialsException("Unauthorized: invalid token"));
                return;
            }
        } catch (Exception e) {
            log.error("SSO authentication exception", e);
            SecurityContextHolder.clearContext();
            handleAuthException(request, response, new AuthenticationServiceException("Unauthorized: authentication failed", e));
            return;
        }

        filterChain.doFilter(request, response);
    }

    /**
     * 处理认证异常：委托给 authenticationEntryPoint 或直接返回 401
     */
    private void handleAuthException(HttpServletRequest request, HttpServletResponse response,
        AuthenticationException authException) throws IOException, ServletException {
        if (authenticationEntryPoint != null) {
            authenticationEntryPoint.commence(request, response, authException);
        } else {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json");
            response.getWriter().write("{\"code\":\"40101\",\"message\":\"" + authException.getMessage() + "\"}");
        }
    }

    /**
     * 判断请求路径是否在排除列表中（支持 Ant 模式匹配）
     */
    private boolean isExcluded(String requestUri) {
        if (excludePaths == null || excludePaths.isEmpty()) {
            return false;
        }
        for (String pattern : excludePaths) {
            if (pathMatcher.match(pattern, requestUri)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 从 Cookie 中获取与 headerName 匹配的 Token（大小写不敏感）
     */
    private String getTokenFromCookie(HttpServletRequest request) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }
        for (Cookie cookie : cookies) {
            if (headerName.equalsIgnoreCase(cookie.getName())) {
                return cookie.getValue();
            }
        }
        return null;
    }

}
