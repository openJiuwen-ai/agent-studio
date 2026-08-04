/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.filter.simple;

import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.common.utils.simple.ServletUtils;
import com.openjiuwen.studio.agent.common.utils.simple.SimpleAuthUtils;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.apache.commons.lang3.StringUtils;

import java.io.IOException;

/**
 * url里面的用户信息设置到agent_sid的cookie里面
 *
 */
public class SimpleAuthFilter implements Filter {

    private String contextPath;

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException {
        HttpServletRequest httpRequest = ((HttpServletRequest) request);
        String uri = ((HttpServletRequest) request).getRequestURI();
        if (contextPath == null) {
            contextPath = SpringBeanUtils.getProperty(SimpleConstants.SERVLET_CONTEXT_PATH, "");
        }
        if (uri.equals(contextPath + SimpleConstants.AUTH_TOKEN_URI)) {
            chain.doFilter(request, response);
            return;
        }

        String existToken = ServletUtils.getAgentSid(httpRequest);
        // 外部调用无cookie时，回退到X-Auth-Token header
        if (StringUtils.isEmpty(existToken)) {
            existToken = httpRequest.getHeader(SimpleConstants.X_AUTH_TOKEN);
        }
        // 如果从url参数或者header参数取到用户信息，则设置到cookie
        String token = SimpleAuthUtils.paramToToken(httpRequest, existToken);
        // paramToToken在existToken非空且无X-USER-ID时返回空，需用existToken兜底
        if (StringUtils.isEmpty(token) && !StringUtils.isEmpty(existToken)) {
            token = existToken;
        }

        // 如果不为空则设置到attribute和cookie；否则不设置
        if (!StringUtils.isEmpty(token)) {
            // 首次设置到attribute，后续流程从attribute取
            httpRequest.setAttribute(SimpleConstants.AGENT_SID, token);

            // 如果token构建成功设置到cookie，前端调用时带入
            ServletUtils.setSidToCookie((HttpServletResponse) response, token);
        }

        chain.doFilter(request, response);
    }

    @Override
    public void destroy() {
    }
}
