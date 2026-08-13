/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.utils;

import static org.apache.commons.configuration2.io.FileOptionsProvider.CURRENT_USER;

import com.openjiuwen.studio.agent.common.constant.Constants;
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

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * 功能描述 请求上下文工具类
 *
 */
@Slf4j
public class RequestContextUtils {
    private static final ThreadLocal<SimpleUser> THREAD_LOCAL_IAM_CTX = new ThreadLocal<>();

    private static final ThreadLocal<Map<String, String>> THREAD_LOCAL_HEADER = new ThreadLocal<>();

    /** 捕获的客户 header（白名单 cust-*） */
    private static final ThreadLocal<Map<String, String>> THREAD_LOCAL_CUSTOMER_HEADERS = new ThreadLocal<>();

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
        return getRequestIamCtx();
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
     * @return user id
     */
    public static String getRequestUserId() {
        return getRequestIamCtx().getUserId();
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

    public static void remove() {
        THREAD_LOCAL_IAM_CTX.remove();
        THREAD_LOCAL_HEADER.remove();
        THREAD_LOCAL_CUSTOMER_HEADERS.remove();
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

    public static HttpHeaders getHeader() {
        HttpHeaders headers = new HttpHeaders();
        headers.add(Constants.Header.X_LANGUAGE,
            Optional.ofNullable(LanguageUtils.getLanguage()).orElse(Constants.ZH_CN));
        headers.add(Constants.Header.X_AUTH_TOKEN,
            RequestContextUtils.getRequestAuthToken());
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = attrs.getRequest();
        AuthProperties authProperties = SpringBeanUtils.getBean(AuthProperties.class);
        if (authProperties != null && authProperties.getSso() != null
            && StringUtils.isNotEmpty(authProperties.getSso().getHeader())) {
            String ssoHeaderName = authProperties.getSso().getHeader();
            String ssoToken = request.getHeader(ssoHeaderName);
            if (StringUtils.isNotEmpty(ssoToken)) {
                headers.add(ssoHeaderName, ssoToken);
            }
        }
        String token = request.getHeader(Constants.CustomModel.CUSTOM_TOKEN);
        String userId = request.getHeader(Constants.CustomModel.CUSTOM_USER_ID);
        if (StringUtils.isNotEmpty(token)) {
            headers.add(Constants.CustomModel.CUSTOM_TOKEN, token);
        }
        if (StringUtils.isNotEmpty(userId)) {
            headers.add(Constants.CustomModel.CUSTOM_USER_ID, userId);
        }
        // 从 ThreadLocal 透传捕获的客户 header（配置启用时）
        Map<String, String> capturedHeaders = THREAD_LOCAL_CUSTOMER_HEADERS.get();
        if (capturedHeaders != null && !capturedHeaders.isEmpty()) {
            for (Map.Entry<String, String> entry : capturedHeaders.entrySet()) {
                headers.add(entry.getKey(), entry.getValue());
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

    public static String getRequestUserIdCompatibleCustom() {
        Map<String, String> headers = getHeaders();
        if (headers != null && headers.containsKey(Constants.CustomModel.CUSTOM_USER_ID)) {
            return headers.get(Constants.CustomModel.CUSTOM_USER_ID);
        }
        return getRequestUserId();

    }
    public static void setCustomerHeaders(Map<String, String> customerHeaders) {
        THREAD_LOCAL_CUSTOMER_HEADERS.set(customerHeaders);
    }

    public static Map<String, String> getCustomerHeaders() {
        Map<String, String> headers = THREAD_LOCAL_CUSTOMER_HEADERS.get();
        return headers != null ? headers : new HashMap<>();
    }
}
