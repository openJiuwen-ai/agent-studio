/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import static org.apache.commons.configuration2.io.FileOptionsProvider.CURRENT_USER;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.customerheader.CapturedCustomerHeaders;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.ExecutionIdentityContext;
import com.openjiuwen.studio.agent.common.customerheader.HeaderProjectionEngine;
import com.openjiuwen.studio.agent.common.customerheader.HeaderValue;
import com.openjiuwen.studio.agent.common.customerheader.InternalTarget;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipal;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;

import jakarta.annotation.Nullable;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Map;
import java.util.Optional;

/**
 * 功能描述 请求上下文工具类
 *
 * <p>改造：
 * <ul>
 *   <li>新增执行专用 getter：{@link #getEffectiveExecutionUserId}、{@link #getExecutionIdentityContext}</li>
 *   <li>新增 {@link #setIdentityContext(ExecutionIdentityContext)} 设置执行身份上下文</li>
 *   <li>新增 {@link #setCustomerHeaders(CapturedCustomerHeaders)} 设置捕获的客户 header</li>
 *   <li>{@link #getHeader} 硬编码透传改经 factory（Profile 启用时）</li>
 *   <li>删 {@code getRequestUserIdCompatibleCustom}（dormant）</li>
 *   <li>{@link #remove} 清理身份上下文 + 客户 header</li>
 * </ul>
 */
@Slf4j
public class RequestContextUtils {
    private static final ThreadLocal<SimpleUser> THREAD_LOCAL_IAM_CTX = new ThreadLocal<>();

    private static final ThreadLocal<Map<String, String>> THREAD_LOCAL_HEADER = new ThreadLocal<>();

    /** 执行身份上下文（平台 principal + effective userId） */
    private static final ThreadLocal<ExecutionIdentityContext> THREAD_LOCAL_IDENTITY_CTX = new ThreadLocal<>();

    /** 捕获的客户 header（白名单 cust-*，不含 x-auth-token） */
    private static final ThreadLocal<CapturedCustomerHeaders> THREAD_LOCAL_CUSTOMER_HEADERS = new ThreadLocal<>();

    /**
     * 获取当前请求的token
     *
     * @return 当前请求的token
     */
    public static String getRequestAuthToken() {
        return getRequestIamCtx().getToken();
    }

    /**
     * 获取当前请求用户
     *
     * @return userName
     */
    public static SimpleUser getRequestUser() {
        // 返回防御性副本，防止调用方修改 SimpleUser 影响其他调用方（线程安全）
        return PlatformPrincipal.from(getRequestIamCtx()).toSimpleUserCopy();
    }

    public static void setRequestAuthTokenAndProjectId(String token, String projectId) {
        final SimpleUser simpleUser = new SimpleUser();
        simpleUser.setToken(token);
        simpleUser.setProjectId(projectId);
        THREAD_LOCAL_IAM_CTX.set(simpleUser);
    }

    /**
     * 获取当前请求的project id
     *
     * @return project id
     */
    public static String getRequestProjectId() {
        return getRequestIamCtx().getProjectId();
    }

    /**
     * 获取当前请求的user id
     *
     * <p>平台语义（非执行模块用此 getter）— 返回平台 principal 的 userId，不受 cust-userid 影响。
     * 执行入口应使用 {@link #getEffectiveExecutionUserId}。
     *
     * @return user id
     */
    public static String getRequestUserId() {
        return getRequestIamCtx().getUserId();
    }

    /**
     * 获取执行用 effective userId
     *
     * <p>返回 cust-userid（simple 模式 + Profile 启用 + cust-userid 非空时），
     * 缺失回退平台 userId。仅在执行入口（Agent/Workflow/Controller 执行）使用。
     *
     * @return effective userId
     */
    public static String getEffectiveExecutionUserId() {
        ExecutionIdentityContext ctx = THREAD_LOCAL_IDENTITY_CTX.get();
        if (ctx != null) {
            return ctx.effectiveUserId();
        }
        // 回退：未设置执行身份上下文（如异步任务未走 Filter），使用平台 userId
        return getRequestUserId();
    }

    /**
     * 获取执行身份上下文
     *
     * @return ExecutionIdentityContext，未设置返回 null
     */
    public static ExecutionIdentityContext getExecutionIdentityContext() {
        return THREAD_LOCAL_IDENTITY_CTX.get();
    }

    /**
     * 获取平台身份 principal— 平台认证后的不可变身份，不受 cust-userid 影响
     *
     * <p>优先从执行身份上下文取；未设置（如异步任务未走 Filter）时从 IAM 上下文构造。
     *
     * @return PlatformPrincipal，无平台身份时返回 null
     */
    public static PlatformPrincipal getPlatformPrincipal() {
        ExecutionIdentityContext ctx = THREAD_LOCAL_IDENTITY_CTX.get();
        if (ctx != null) {
            return ctx.platformPrincipal();
        }
        // 回退：未设置执行身份上下文，从 IAM 上下文（平台 SimpleUser）构造
        return getRequestIamCtxOptional()
            .map(PlatformPrincipal::from)
            .orElse(null);
    }

    /**
     * 获取平台认证 Token— 平台 Token，非客户 cust-token
     *
     * @return 平台 Token，无身份时返回 null
     */
    public static String getPlatformAuthToken() {
        PlatformPrincipal principal = getPlatformPrincipal();
        return principal != null ? principal.token() : null;
    }

    /**
     * 设置执行身份上下文（由 SimpleUserContextFilter 调用）
     *
     * @param context 执行身份上下文
     */
    public static void setIdentityContext(ExecutionIdentityContext context) {
        THREAD_LOCAL_IDENTITY_CTX.set(context);
    }

    /**
     * 获取捕获的客户 header
     *
     * @return CapturedCustomerHeaders，未设置返回 null
     */
    public static CapturedCustomerHeaders getCustomerHeaders() {
        return THREAD_LOCAL_CUSTOMER_HEADERS.get();
    }

    /**
     * 设置捕获的客户 header（由 SimpleUserContextFilter 调用）
     *
     * @param headers 捕获的客户 header
     */
    public static void setCustomerHeaders(CapturedCustomerHeaders headers) {
        THREAD_LOCAL_CUSTOMER_HEADERS.set(headers);
    }

    /**
     * 获取当前请求用户的domain id
     *
     * @return domain id
     */
    public static String getRequestUserDomainId() {
        return getRequestIamCtx().getDomainId();
    }

    /**
     * 获取当前请求用户的domain id
     *
     * @return domain id
     */
    public static Optional<String> getRequestUserDomainIdOptional() {
        return getRequestIamCtxOptional().map(SimpleUser::getDomainId);
    }

    public static String getRequestWorkspaceName() {
        return ThreadLocalUtils.getWorkspaceName();
    }

    /**
     * 清理所有 ThreadLocal
     *
     * <p>清理：IAM 上下文、header、执行身份上下文、客户 header
     */
    public static void remove() {
        THREAD_LOCAL_IAM_CTX.remove();
        THREAD_LOCAL_HEADER.remove();
        THREAD_LOCAL_IDENTITY_CTX.remove();
        THREAD_LOCAL_CUSTOMER_HEADERS.remove();
        // 清理投影追踪状态（请求结束/异常/线程复用后）
        HeaderProjectionEngine.clearProjectionTracking();
    }

    /**
     * 获取当前请求用户的domain name
     *
     * @return domain name
     */
    public static String getRequestUserDomainName() {
        return getRequestIamCtx().getDomainName();
    }

    /**
     * 获取当前请求用户名
     *
     * @return userName
     */
    public static String getRequestUserName() {
        return getRequestIamCtx().getUserName();
    }

    /**
     * 获取当前请求用户的headers
     *
     * @return headers
     */
    public static Map<String, String> getHeaders() {
        return THREAD_LOCAL_HEADER.get();
    }

    /**
     * 获取当前请求的IAM上下文
     *
     */
    public static SimpleUser getRequestIamCtx() {
        SimpleUser simpleUser = getIamCtxFromReqAttr();
        if (simpleUser != null) {
            return simpleUser;
        }

        simpleUser = THREAD_LOCAL_IAM_CTX.get();
        if (simpleUser != null) {
            return simpleUser;
        }
        log.error("getRequestIamCtx failed, can't get Context from ThreadLocal");
        throw new RuntimeException("Get request iam context failed");
    }

    /**
     * 获取当前请求的IAM上下文
     *
     * @return Context信息
     */
    public static Optional<SimpleUser> getRequestIamCtxOptional() {
        SimpleUser simpleUser = getIamCtxFromReqAttr();
        if (simpleUser != null) {
            return Optional.of(simpleUser);
        }

        simpleUser = THREAD_LOCAL_IAM_CTX.get();
        if (simpleUser != null) {
            return Optional.of(simpleUser);
        }
        log.debug("getRequestIamCtx failed, can't get Context from ThreadLocal");
        return Optional.empty();
    }

    /**
     * 从请求获取Context信息
     *
     * @return Context信息
     */
    @Nullable
    private static SimpleUser getIamCtxFromReqAttr() {
        if (RequestContextHolder.getRequestAttributes() == null || RequestContextHolder.getRequestAttributes()
            .getAttribute(CURRENT_USER, RequestAttributes.SCOPE_REQUEST) == null) {
            return null;
        }

        return (SimpleUser) RequestContextHolder.getRequestAttributes()
            .getAttribute(CURRENT_USER, RequestAttributes.SCOPE_REQUEST);
    }

    /**
     * @return java.lang.String
     * @implNote 未实现，临时返回default
     * @description 获取当前请求的工作空间id
     * @date 15:20 2025/8/8
     **/
    public static String getRequestWorkspaceId() {
        return ThreadLocalUtils.getWorkspaceId();
    }

    /**
     * 构建出站 HttpHeaders — 改造：cust-* 透传改经 factory
     *
     * <p>Profile 启用时：使用 InternalRequestHeaderFactory 的 passthrough 逻辑（配置驱动）。
     * Profile 未启用时：保持现有行为（从入站请求直接读 cust-*），向后兼容。
     *
     * @return HttpHeaders 包含平台协议 header + 客户 header
     */
    public static HttpHeaders getHeader() {
        HttpHeaders headers = new HttpHeaders();
        // 平台协议 header（manager 可信生成）
        headers.add(Constants.Header.X_LANGUAGE,
            Optional.ofNullable(LanguageUtils.getLanguage()).orElse(Constants.ZH_CN));
        headers.add(Constants.Header.X_AUTH_TOKEN,
            RequestContextUtils.getRequestAuthToken());

        // SSO header（如果配置了）
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = attrs != null ? attrs.getRequest() : null;
        AuthProperties authProperties = SpringBeanUtils.getBean(AuthProperties.class);
        if (authProperties != null && authProperties.getSso() != null
            && StringUtils.isNotEmpty(authProperties.getSso().getHeader())) {
            String ssoHeaderName = authProperties.getSso().getHeader();
            if (request != null) {
                String ssoToken = request.getHeader(ssoHeaderName);
                if (StringUtils.isNotEmpty(ssoToken)) {
                    headers.add(ssoHeaderName, ssoToken);
                }
            }
        }

        // 客户 header 透传 — Profile 启用时使用 factory（配置驱动）
        CapturedCustomerHeaders captured = THREAD_LOCAL_CUSTOMER_HEADERS.get();
        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        if (profile != null && profile.isEnabledInSimpleMode() && captured != null && !captured.isEmpty()) {
            // 使用 HeaderProjectionEngine 的 passthrough 逻辑
            HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
            Map<String, HeaderValue> passthrough =
                engine.passthrough(InternalTarget.AGENT_RUNTIME_INBOUND, captured);
            for (Map.Entry<String, HeaderValue> entry : passthrough.entrySet()) {
                headers.add(entry.getKey(), entry.getValue().value());
            }
            log.info("[customer-header] Customer header passthrough applied: target=AGENT_RUNTIME_INBOUND, keys={}", passthrough.keySet());
        } else if (request != null) {
            // 向后兼容：Profile 未启用时，从入站请求直接读 cust-*（业务语义不变）
            String token = request.getHeader(Constants.CustomModel.CUSTOM_TOKEN);
            String userId = request.getHeader(Constants.CustomModel.CUSTOM_USER_ID);
            if (StringUtils.isNotEmpty(token)) {
                headers.add(Constants.CustomModel.CUSTOM_TOKEN, token);
            }
            if (StringUtils.isNotEmpty(userId)) {
                headers.add(Constants.CustomModel.CUSTOM_USER_ID, userId);
            }
        }
        return headers;
    }

    /**
     * 置请求上下文
     * 同时支持 Token, ProjectId, DomainId。
     * 兼容性说明：如果不需要某个参数（比如旧代码不需要 domainId），传 null 即可。
     */
    public static void setContext(String token, String projectId, String domainId) {
        final SimpleUser simpleUser = new SimpleUser();
        simpleUser.setToken(token);
        simpleUser.setProjectId(projectId);
        simpleUser.setDomainId(domainId);
        THREAD_LOCAL_IAM_CTX.set(simpleUser);
    }

    /**
     * 设置用户上下文
     * @param simpleUser 用户上下文
     */
    public static void setContext(SimpleUser simpleUser) {
        THREAD_LOCAL_IAM_CTX.set(simpleUser);
    }

    public static void setRequestAuthTokenAndUserId(String token, String projectId, String userId) {
        final SimpleUser simpleUser = new SimpleUser();
        simpleUser.setToken(token);
        simpleUser.setProjectId(projectId);
        simpleUser.setUserId(userId);
        THREAD_LOCAL_IAM_CTX.set(simpleUser);
    }

    /**
     * 获取当前请求用户的headers
     */
    public static void setHeaders(Map<String, String> headers) {
        THREAD_LOCAL_HEADER.set(headers);
    }
}
