/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import jakarta.servlet.http.HttpServletRequest;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 客户 Header 捕获容器 — 从入站请求中按白名单捕获 cust-* header
 *
 * <p>不含 x-auth-token（属 AUTHENTICATED_PRINCIPAL，从 platformPrincipal 取）。
 * 不可变，保证请求生命周期内值不被篡改。
 */
public final class CapturedCustomerHeaders {

    private final Map<String, HeaderValue> captured;

    private CapturedCustomerHeaders(Map<String, HeaderValue> captured) {
        this.captured = Collections.unmodifiableMap(captured);
    }

    /**
     * 从 HTTP 请求中按白名单捕获客户 header
     *
     * @param allowList 捕获白名单（如 cust-userid、cust-token）
     * @param request   HTTP 请求
     * @return 不可变的 CapturedCustomerHeaders
     */
    public static CapturedCustomerHeaders capture(String[] allowList, HttpServletRequest request) {
        Map<String, HeaderValue> map = new LinkedHashMap<>();
        if (allowList == null || request == null) {
            return new CapturedCustomerHeaders(map);
        }
        for (String headerName : allowList) {
            String value = request.getHeader(headerName);
            if (value != null && !value.isEmpty()) {
                HeaderValue hv = HeaderValue.customerCaptured(headerName, value);
                map.put(hv.normalizedName(), hv);
            }
        }
        return new CapturedCustomerHeaders(map);
    }

    /**
     * 从已有 Map 构造（用于异步恢复从 Redis 快照重建）
     *
     * @param headers header 映射
     * @return 不可变的 CapturedCustomerHeaders
     */
    public static CapturedCustomerHeaders from(Map<String, HeaderValue> headers) {
        Map<String, HeaderValue> map = new LinkedHashMap<>();
        if (headers != null) {
            map.putAll(headers);
        }
        return new CapturedCustomerHeaders(map);
    }

    /**
     * 空捕获容器
     *
     * @return 空的 CapturedCustomerHeaders
     */
    public static CapturedCustomerHeaders empty() {
        return new CapturedCustomerHeaders(Collections.emptyMap());
    }

    /**
     * 获取捕获的 header 映射（不可变）
     *
     * @return 不可变 Map（key 为规范化小写名，value 为 HeaderValue）
     */
    public Map<String, HeaderValue> asMap() {
        return captured;
    }

    /**
     * 按名称获取 header 值（大小写不敏感）
     *
     * @param name header 名
     * @return header 值，不存在返回 null
     */
    public String get(String name) {
        if (name == null) {
            return null;
        }
        HeaderValue hv = captured.get(name.toLowerCase());
        return hv != null ? hv.value() : null;
    }

    /**
     * 是否包含指定 header
     *
     * @param name header 名
     * @return 是否包含
     */
    public boolean contains(String name) {
        return name != null && captured.containsKey(name.toLowerCase());
    }

    /**
     * 是否为空
     *
     * @return 是否无捕获 header
     */
    public boolean isEmpty() {
        return captured.isEmpty();
    }
}
