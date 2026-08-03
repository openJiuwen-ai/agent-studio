/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.filter.simple;

import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.customerheader.CapturedCustomerHeaders;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.ExecutionIdentityContext;
import com.openjiuwen.studio.agent.common.customerheader.InvalidPlatformTokenException;
import com.openjiuwen.studio.agent.common.customerheader.PlatformAuthProtocolException;
import com.openjiuwen.studio.agent.common.customerheader.PlatformAuthServiceUnavailableException;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipal;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipalResolver;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.common.utils.simple.ServletUtils;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.regex.Pattern;

/**
 * 将token对应的用户信息设置到请求上下文中
 *
 * <p>改造：
 * <ul>
 *   <li>capture cust-* header（白名单，不含 x-auth-token）</li>
 *   <li>cust-userid 作 effectiveUserId（simple 模式门控）</li>
 *   <li>平台 token/agentSid 认证不绕过：使用 PlatformPrincipalResolver bean</li>
 *   <li>Resolver 异常映射：Token 无效→401、认证服务超时→503、协议错→500</li>
 *   <li>finally remove 清理 ThreadLocal</li>
 *   <li>CURRENT_USER 存平台 principal（非 effective 视图，防非执行模块漂移）</li>
 * </ul>
 */
public class SimpleUserContextFilter implements Filter {
    private static final Logger log = LoggerFactory.getLogger(SimpleUserContextFilter.class);

    private static final String CURRENT_USER = "CURRENT_USER";

    private String contextPath;

    private final PlatformPrincipalResolver platformPrincipalResolver;

    private final CustomerHeaderProfile customerHeaderProfile;

    /**
     * 构造函数 — 由 FilterConfig 注入 resolver 和 profile bean
     *
     * @param platformPrincipalResolver 平台身份解析器 bean
     * @param customerHeaderProfile     客户 Header Profile 配置 bean
     */
    public SimpleUserContextFilter(PlatformPrincipalResolver platformPrincipalResolver,
                                   CustomerHeaderProfile customerHeaderProfile) {
        this.platformPrincipalResolver = platformPrincipalResolver;
        this.customerHeaderProfile = customerHeaderProfile;
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
        throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;
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
            // agentSid 缺失 → 按现有入口契约续链（不设用户上下文）
            chain.doFilter(request, response);
            return;
        }

        // 平台身份解析 — 使用 PlatformPrincipalResolver bean（原 private getUserByToken 逻辑）
        final PlatformPrincipal principal;
        try {
            principal = platformPrincipalResolver.resolveOrThrow(agentSid);
        } catch (InvalidPlatformTokenException e) {
            // Token 无效/过期/撤权 → 401
            log.warn("[customer-header] Platform token invalid: {}", e.getMessage());
            writeError(httpResponse, 401, "Unauthorized");
            return;
        } catch (PlatformAuthServiceUnavailableException e) {
            // 认证服务超时/5xx → 503（不退化为仅凭 cust-userid 继续）
            log.error("[customer-header] Platform auth service unavailable: {}", e.getMessage());
            writeError(httpResponse, 503, "Service Unavailable");
            return;
        } catch (PlatformAuthProtocolException e) {
            // 响应格式错 → 500（不设 effective）
            log.error("[customer-header] Platform auth protocol error", e);
            writeError(httpResponse, 500, "Internal Server Error");
            return;
        }

        // 计算 effective userId（simple 模式 + Profile 启用 + identity.user-id-header 非空时替代）
        // M8：header 名由 profile.identity.user-id-header 驱动，非硬编码常量（新客户只加 profile 不改代码）
        String effectiveUserId = principal.userId();
        boolean profileEnabled = customerHeaderProfile != null && customerHeaderProfile.isEnabledInSimpleMode();
        if (profileEnabled) {
            String userIdHeader = customerHeaderProfile.getUserIdHeader();
            if (StringUtils.isNotEmpty(userIdHeader)) {
                String custUserId = httpRequest.getHeader(userIdHeader);
                if (StringUtils.isNotEmpty(custUserId)) {
                    effectiveUserId = custUserId;
                }
            }
        }

        // 捕获客户 header（白名单 cust-*，不含 x-auth-token）
        String[] allowList = customerHeaderProfile != null ? customerHeaderProfile.getCaptureAllowList() : new String[0];
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.capture(allowList, httpRequest);

        try {
            // CURRENT_USER 存平台 principal 的 SimpleUser 副本（非 effective 视图，防非执行模块漂移）
            httpRequest.setAttribute(CURRENT_USER, principal.toSimpleUserCopy());
            RequestContextUtils.setContext(principal.toSimpleUserCopy());
            // 设置执行身份上下文（平台 principal + effective userId）
            RequestContextUtils.setIdentityContext(new ExecutionIdentityContext(principal, effectiveUserId));
            // 设置捕获的客户 header
            RequestContextUtils.setCustomerHeaders(captured);
            chain.doFilter(request, response);
        } finally {
            // 请求结束/异常/线程复用后清理上下文
            RequestContextUtils.remove();
        }
    }

    /**
     * 写错误响应
     *
     * @param response HTTP 响应
     * @param status   HTTP 状态码
     * @param message  错误消息
     */
    private void writeError(HttpServletResponse response, int status, String message) {
        try {
            response.setStatus(status);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"error\":\"" + message + "\"}");
            response.getWriter().flush();
        } catch (IOException e) {
            log.error("[customer-header] Failed to write error response", e);
        }
    }

    @Override
    public void destroy() {
    }
}
