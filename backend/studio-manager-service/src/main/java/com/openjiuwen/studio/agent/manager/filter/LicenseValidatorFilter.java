/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.filter;

import com.openjiuwen.studio.agent.common.utils.I18nUtil;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 功能描述
 *
 */
@Component
@Order(0)
@ConditionalOnProperty(name = "env_type", havingValue = "lite")
public class LicenseValidatorFilter extends OncePerRequestFilter {
    private static final Set<String> WHITE_LIST =
        new HashSet<>(List.of("/v1/*/agent-manager/license/upload-file", "/v1/*/agent-manager/license", "/v3/**",
            "/saml/**", "/v1/health", "/health", "/login", "/api/public/**", "/v1/*/agent-manager/workspace/init"));

    @Autowired
    private I18nUtil i18nUtil;

    private final AntPathMatcher antPathMatcher = new AntPathMatcher();

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
        throws ServletException, IOException {
        String uri = request.getRequestURI();
        // 静态资源放行
        if (uri.startsWith("/static/") || uri.startsWith("/public/")
            || uri.matches(".*\\.(css|js|png|jpg|jpeg|gif|ico|woff|woff2)$")) {
            chain.doFilter(request, response);
            return;
        }
        // 白名单放行
        if (isInWhiteList(uri)) {
            chain.doFilter(request, response);
            return;
        }
        chain.doFilter(request, response);
    }

    private boolean isInWhiteList(String requestUri) {
        for (String pattern : WHITE_LIST) {
            if (antPathMatcher.match(pattern, requestUri)) {
                return true;
            }
        }
        return false;
    }
}
