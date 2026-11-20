/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.filter;

import com.openjiuwen.studio.agent.manager.entity.User;
import com.openjiuwen.studio.agent.manager.service.SessionService;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Optional;

/**
 * 会话过滤器 - 用于会话校验、刷新和上下文设置
 */
@Component
@Slf4j
@RequiredArgsConstructor
@ConditionalOnProperty(name = "saml.enabled", havingValue = "true")
public class SessionFilter extends OncePerRequestFilter {

    static final String SESSION_COOKIE_NAME = "AUTH_SESSION";

    private final SessionService sessionService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {

        String sessionId = extractSessionId(request);

        if (sessionId != null) {
            // 会话校验
            if (sessionService.validateSession(sessionId)) {
                // 会话刷新
                sessionService.refreshSession(sessionId);

                // 设置用户上下文
                Optional<User> userOpt = sessionService.getUserBySession(sessionId);
                userOpt.ifPresent(user -> setUserContext(request, user));

            } else {
                // 会话无效，清除cookie
                clearSessionCookie(response);
            }
        }

        filterChain.doFilter(request, response);
    }

    /**
     * 从请求中提取会话ID
     */
    String extractSessionId(HttpServletRequest request) {
        // 首先检查cookie
        Cookie[] cookies = request.getCookies();
        if (cookies != null) {
            for (Cookie cookie : cookies) {
                if (SESSION_COOKIE_NAME.equals(cookie.getName())) {
                    return cookie.getValue();
                }
            }
        }

        // 然后检查header
        String headerSession = request.getHeader("X-Session-Id");
        if (headerSession != null && !headerSession.trim().isEmpty()) {
            return headerSession.trim();
        }

        return null;
    }

    /**
     * 设置用户上下文
     */
    private void setUserContext(HttpServletRequest request, User user) {
        request.setAttribute("currentUser", user);
        request.setAttribute("userId", user.getId());
        request.setAttribute("username", user.getUsername());
        request.setAttribute("domainId", user.getDomainId());
        request.setAttribute("projectId", user.getProjectId());
    }

    /**
     * 清除会话cookie
     */
    private void clearSessionCookie(HttpServletResponse response) {
        Cookie cookie = new Cookie(SESSION_COOKIE_NAME, null);
        cookie.setPath("/");
        cookie.setHttpOnly(true);
        cookie.setMaxAge(0); // 立即过期
        cookie.setSecure(true);
        response.addCookie(cookie);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return isPublicPath(path);
    }

    private boolean isPublicPath(String path) {
        return path.startsWith("/login") || path.startsWith("/saml/") || path.startsWith("/api/public/")
            || path.startsWith("/css/") || path.startsWith("/js/") || path.startsWith("/images/")
            || path.equals("/v3/auth/tokens") || path.startsWith("/health");
    }
}
