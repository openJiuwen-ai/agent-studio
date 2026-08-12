/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.filter.simple;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.common.utils.simple.ServletUtils;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 将token对应的用户信息设置到请求上下文中
 *
 */
public class SimpleUserContextFilter implements Filter {
    private static final Logger log = LoggerFactory.getLogger(SimpleUserContextFilter.class);

    private static final String CURRENT_USER = "CURRENT_USER";

    private String contextPath;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        if (contextPath == null) {
            contextPath = SpringBeanUtils.getProperty(SimpleConstants.SERVLET_CONTEXT_PATH, "");
        }
        String path = httpRequest.getRequestURI();
        String quoteContextPath = Pattern.quote(contextPath);
        if (!path.matches(quoteContextPath + "/health|" + quoteContextPath + "/v1/.*|" + quoteContextPath + "/v2/.*|"
            + quoteContextPath + "/v3/.*")) {
            chain.doFilter(request, response);
            return;
        }

        // 调用/v3/auth/tokens接口本身不需要设置用户信息，避免循环调用
        if (path.equals(contextPath + SimpleConstants.AUTH_TOKEN_URI)) {
            chain.doFilter(request, response);
            return;
        }

        String agentSid = ServletUtils.getAgentSid(httpRequest);
        if (StringUtils.isEmpty(agentSid)) {
            chain.doFilter(request, response);
            return;
        }

        SimpleUser simpleUser = getUserByToken(agentSid);
        if (simpleUser != null) {
            httpRequest.setAttribute(CURRENT_USER, simpleUser);
            RequestContextUtils.setContext(simpleUser);
        }

        // 捕获客户 header（cust-*）到 ThreadLocal，供下游 rename 使用
        captureCustomerHeaders(httpRequest);

        chain.doFilter(request, response);
    }

    private SimpleUser getUserByToken(String token) {
        try {
            OkHttpClientUtils okHttpClientUtils = SpringBeanUtils.getBean(OkHttpClientUtils.class);
            OkHttpClient httpClient = okHttpClientUtils.getHttpClient();
            String authEndpoint = SpringBeanUtils.getProperty("feign.client.config.userAuth.url", "");
            String contextPathValue = SpringBeanUtils.getProperty(SimpleConstants.SERVLET_CONTEXT_PATH, "");

            String url = authEndpoint + contextPathValue + SimpleConstants.AUTH_TOKEN_URI;
            Request httpRequest = new Request.Builder()
                .url(url)
                .addHeader("X-Subject-Token", token)
                .get()
                .build();

            try (Response response = httpClient.newCall(httpRequest).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    return objectMapper.readValue(response.body().string(), SimpleUser.class);
                }
            }
        } catch (Exception e) {
            log.warn("Failed to get user by token.", e);
        }
        return null;
    }

    @Override
    public void destroy() {
    }

    private void captureCustomerHeaders(HttpServletRequest request) {
        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        if (profile == null || !profile.isEnabled()) return;
        String[] allowList = profile.getCaptureAllowList();
        Map<String, String> captured = new HashMap<>();
        for (String name : allowList) {
            String value = request.getHeader(name);
            if (StringUtils.isNotEmpty(value)) {
                captured.put(name.toLowerCase(), value);
            }
        }
        RequestContextUtils.setCustomerHeaders(captured);
    }
}
