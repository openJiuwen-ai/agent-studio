/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.saml.controller;

import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.utils.simple.ServletUtils;
import com.openjiuwen.studio.agent.manager.entity.User;
import com.openjiuwen.studio.agent.manager.saml.SAMLException;
import com.openjiuwen.studio.agent.manager.saml.SAMLResponseValidator;
import com.openjiuwen.studio.agent.manager.saml.impl.SAMLResponseValidatorImpl;
import com.openjiuwen.studio.agent.manager.service.SessionService;
import com.openjiuwen.studio.agent.manager.service.UserService;

import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.codec.binary.Base64;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * SAML 2.0 认证控制器 - 处理SAML认证流程
 */
@Controller
@RequestMapping("/saml")
@Slf4j
@RequiredArgsConstructor
@SuppressWarnings("unchecked")
public class SamlController {

    private static final String REDIS_REQUEST_PREFIX = "original_request:";
    private final UserService userService;
    private final SessionService sessionService;
    private final RedisTemplate<String, Object> redisTemplate;
    @Value("${saml.domainId:0}")
    private String domainId;
    @Value("${saml.projectId:0}")
    private String projectId;

    @Value("${saml.redirectUrl:0}")
    private String redirectUrl;

    /**
     * SAML响应处理端点 - 接收SAML身份提供商的响应
     * 为了满足IDP要求
     */
    @PostMapping("/login")
    public void handleSamlResponse(HttpServletRequest request, HttpServletResponse response)
        throws IOException, SAMLException {
        String samlResp = request.getParameter("SAMLResponse");
        SAMLResponseValidator vld = null;
        if (samlResp == null || samlResp.trim().isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.getWriter().write("SAMLResponse参数不能为空");
            return;
        }
        try {
            vld = new SAMLResponseValidatorImpl(
                new String(new Base64().decode(samlResp.getBytes(StandardCharsets.UTF_8)), StandardCharsets.UTF_8));
            vld.validate();

            // 验证成功，返回用户信息
            response.setContentType("application/json;charset=UTF-8");
            response.setStatus(HttpServletResponse.SC_OK);

            // 验证UIBean不为null
            if (vld.getUIBean() == null) {
                throw new SAMLException("UIBean is null, authentication failed");
            }

            String uid = vld.getUIBean().getUid();
            if (uid == null || uid.trim().isEmpty()) {
                throw new SAMLException("User ID is empty, authentication failed");
            }

            // 首次登录自动创建用户或更新用户信息
            User user = userService.createUserOnFirstLogin(uid, uid, uid, domainId, projectId);

            // 创建会话
            var session = sessionService.createSession(user, null);
            if (session == null || session.getSessionId() == null) {
                throw new SAMLException("Session creation failed");
            }

            // 设置会话cookie
            setSessionCookie(response, SimpleConstants.AGENT_SID, uid + "|" + projectId);
            setSessionCookie(response, "AUTH_SESSION", session.getSessionId());
            ServletUtils.setSidToCookie(response, uid + "|" + projectId);

            // 验证重定向URL
            String finalRedirectUrl = (redirectUrl != null && !redirectUrl.trim().isEmpty()) ? redirectUrl : "/";
            response.sendRedirect(finalRedirectUrl);

        } catch (SAMLException e) {
            // SAML验证失败
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"error\": \"SAMLResponse验证失败\", \"message\": \"" + e.getMessage() + "\"}");

        } catch (IllegalArgumentException e) {
            // Base64解码失败
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"error\": \"SAMLResponse格式错误\", \"message\": \"Base64解码失败\"}");
        } catch (Exception e) {
            // 其他异常
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"error\": \"服务器内部错误\"}");
        }
    }

    /**
     * 确定重定向URL
     */
    private String determineRedirectUrl(HttpServletRequest request, Map<String, Object> originalRequest) {
        if (request == null) {
            return "/";
        }

        // 优先使用原始请求的URL
        if (originalRequest != null) {
            Object urlObj = originalRequest.get("url");
            if (urlObj instanceof String) {
                String originalUrl = (String) urlObj;
                if (originalUrl != null && !originalUrl.trim().isEmpty()) {
                    return originalUrl;
                }
            }
        }

        // 其次使用session中的relayState
        try {
            String sessionRelayState = (String) request.getSession().getAttribute("SAML_RELAY_STATE");
            if (sessionRelayState != null && !sessionRelayState.trim().isEmpty()) {
                try {
                    String decodedUrl = URLDecoder.decode(sessionRelayState, StandardCharsets.UTF_8.name());
                    // 清除session中的relayState
                    request.getSession().removeAttribute("SAML_RELAY_STATE");
                    return decodedUrl;
                } catch (Exception e) {
                    log.warn("Decoding relayState failed");
                }
            }
        } catch (IllegalStateException e) {
            log.warn("Session is invalid, using default redirect URL", e);
        }

        // 默认重定向到首页
        return "/";
    }

    /**
     * 设置会话cookie
     */
    private void setSessionCookie(HttpServletResponse response, String cookieKey, String cookieValue) {
        Cookie cookie = new Cookie(cookieKey, cookieValue);
        cookie.setPath("/");
        cookie.setHttpOnly(true);
        cookie.setMaxAge(30 * 60); // 30分钟
        cookie.setSecure(true);
        response.addCookie(cookie);
    }

}
