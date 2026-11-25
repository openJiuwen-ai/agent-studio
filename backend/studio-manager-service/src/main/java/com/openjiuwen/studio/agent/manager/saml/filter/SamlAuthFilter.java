/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.manager.saml.ConfigurationException;
import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.impl.SAMLRequestImpl;
import com.openjiuwen.studio.agent.manager.service.SessionService;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.codec.binary.Base64;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/**
 * SAML认证过滤器 - 专门处理SAML认证流程
 * 拦截未认证请求并重定向到SAML IDP进行认证
 */
@Component
@Slf4j
@RequiredArgsConstructor
@ConditionalOnProperty(name = "saml.enabled", havingValue = "true")
public class SamlAuthFilter extends OncePerRequestFilter {
    private static final String SESSION_COOKIE_NAME = "AUTH_SESSION";

    private static final String REDIS_REQUEST_PREFIX = "original_request:";
    private static final int REQUEST_TIMEOUT_MINUTES = 10;
    private final SessionService sessionService;

    @Value("${saml.idp-metadata-url:0}")
    private String idpUrl;
    private final RedisTemplate<String, Object> redisTemplate;



    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
        // 检查是否已认证
        String sessionId = extractSessionId(request);
        if (sessionId != null && sessionService.validateSession(sessionId)) {
            // 已认证，继续处理请求
            filterChain.doFilter(request, response);
            return;
        }

        String samlUserId = (String) request.getAttribute("SAML_USER_ID");
        if (samlUserId != null) {
            // 这是SAML认证后的请求，继续处理让SessionFilter设置x-auth-token头
            filterChain.doFilter(request, response);
            return;
        }

        // 未认证，重定向到SAML认证
        try {
            redirectToSamlLogin(request, response);
        } catch (SAMLException e) {
            throw new ConfigurationException("SAML认证重定向失败", e);
        }
    }

    /**
     * 重定向到SAML登录
     */
    private void redirectToSamlLogin(HttpServletRequest request, HttpServletResponse response)
        throws IOException, SAMLException {
        // 保存原始请求URL用于登录后跳转
        String originalUrl = request.getRequestURI();
        if (request.getQueryString() != null) {
            originalUrl += "?" + request.getQueryString();
        }
        // 生成唯一的请求token
        String traceId = UUID.randomUUID().toString();
        // 构建原始请求信息
        Map<String, Object> originalRequest = new HashMap<>();
        originalRequest.put("method", request.getMethod());
        originalRequest.put("url", originalUrl);
        if (request.getQueryString() != null) {
            originalUrl += "?" + request.getQueryString();
        }

        log.info("User not authenticated, redirecting to SAML login:originalUrl={}, redirectUrl={}", originalUrl);
        // 存储到Redis，设置10分钟过期时间REDIS_REQUEST_PREFIX
        String redisKey = REDIS_REQUEST_PREFIX + traceId;
        redisTemplate.opsForValue().set(redisKey, originalRequest, REQUEST_TIMEOUT_MINUTES, TimeUnit.MINUTES);
        byte[] samlRequest = new SAMLRequestImpl().generate().getBytes(StandardCharsets.UTF_8);
        samlRequest = new Base64().encode(samlRequest);
        String callbackUrl = idpUrl + "/sp?SAMLRequest="
            + URLEncoder.encode(new String(samlRequest, StandardCharsets.UTF_8),
                String.valueOf(StandardCharsets.UTF_8));
        // 重定向到SAML认证发起端点，传递traceId
        String redirectUrl = callbackUrl + "&RelayState="
            + URLEncoder.encode(traceId, String.valueOf(StandardCharsets.UTF_8));
        log.info(
            "User not authenticated, redirected to SAML login:method={}, originalUrl={}, traceId={}, redirectUrl={}",
            request.getMethod(),
            originalUrl, traceId, redirectUrl);
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");

        Map<String, String> responseData = new HashMap<>();
        responseData.put("code", "UNAUTHORIZED");
        responseData.put("message", "Authentication required");
        responseData.put("redirectUrl", redirectUrl);

        ObjectMapper mapper = new ObjectMapper();
        response.getWriter().write(mapper.writeValueAsString(responseData));

    }

    /**
     * 从请求中提取会话ID
     */
    private String extractSessionId(HttpServletRequest request) {
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

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return isAuthExcludedPath(path);
    }

    private boolean isAuthExcludedPath(String path) {
        return path.startsWith("/saml/") || path.startsWith("/api/auth/") || path.startsWith("/login")
            || path.startsWith("/css/") || path.startsWith("/js/") || path.startsWith("/images/")
            || path.startsWith("/api/public/") || path.equals("/") || path.equals("/favicon.ico")
            || path.equals("/v3/auth/tokens") || path.startsWith("/health");
    }
}
