/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.filter;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.User;
import com.openjiuwen.studio.agent.manager.service.SessionService;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
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

    /** 与 RequestContextUtils 读取的 request attribute 名一致（FileOptionsProvider.CURRENT_USER） */
    private static final String CURRENT_USER_ATTR = "currentUser";

    private final SessionService sessionService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {

        String sessionId = extractSessionId(request);
        boolean contextSet = false;

        try {
            if (sessionId != null) {
                // 会话校验
                if (sessionService.validateSession(sessionId)) {
                    // 会话刷新
                    sessionService.refreshSession(sessionId);

                    // 设置用户上下文（必须是 SimpleUser，供 RequestContextUtils 使用）
                    Optional<User> userOpt = sessionService.getUserBySession(sessionId);
                    if (userOpt.isPresent()) {
                        setUserContext(request, userOpt.get(), sessionId);
                        contextSet = true;
                    }

                } else {
                    // 会话无效，清除cookie
                    clearSessionCookie(request, response);
                }
            }

            filterChain.doFilter(request, response);
        } finally {
            if (contextSet) {
                RequestContextUtils.remove();
            }
        }
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
     * 设置用户上下文：写入 SimpleUser，避免 ClassCastException → openjiuwen.03000000
     */
    private void setUserContext(HttpServletRequest request, User user, String sessionId) {
        String userId = StringUtils.isNotBlank(user.getExternalId()) ? user.getExternalId() : user.getUsername();
        String projectId = StringUtils.defaultIfBlank(user.getProjectId(), "0");
        String domainId = StringUtils.defaultIfBlank(user.getDomainId(), "0");
        String token = userId + "|" + projectId;

        SimpleUser simpleUser = SimpleUser.builder()
            .userId(userId)
            .userName(user.getUsername())
            .projectId(projectId)
            .domainId(domainId)
            .token(token)
            .build();

        request.setAttribute(CURRENT_USER_ATTR, simpleUser);
        request.setAttribute("CURRENT_USER", simpleUser);
        request.setAttribute("userId", userId);
        request.setAttribute("username", user.getUsername());
        request.setAttribute("domainId", domainId);
        request.setAttribute("projectId", projectId);
        request.setAttribute("sessionId", sessionId);
        RequestContextUtils.setContext(simpleUser);
    }

    /**
     * 清除会话cookie
     */
    private void clearSessionCookie(HttpServletRequest request, HttpServletResponse response) {
        Cookie cookie = new Cookie(SESSION_COOKIE_NAME, null);
        cookie.setPath("/");
        cookie.setHttpOnly(true);
        cookie.setMaxAge(0); // 立即过期
        cookie.setSecure(request.isSecure());
        response.addCookie(cookie);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return path.startsWith("/saml/") || path.startsWith("/login") || path.startsWith("/health")
            || path.equals("/v3/auth/tokens");
    }
}
