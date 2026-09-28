/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.filter;

import org.apache.commons.lang3.StringUtils;

import java.util.List;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Origin 校验器（跨站 CSRF 兜底防护）
 *
 * <p>iframe SSO 场景下，前端会在跨站 https 拓扑写入 SameSite=None 的凭据
 * Cookie（Access-Token），该 Cookie 会随任意跨站请求自动携带；本工程后端
 * 安全链禁用了 CSRF（OAuth2SecurityConfig csrf.disable），此处按 Origin
 * 头做兜底校验：携带 Origin 头的请求须为同源（Origin 的 host:port 与
 * Host 头一致）或命中 auth.sso.allowed-origins 白名单（父平台完整 origin，
 * 含协议与端口），否则拒绝。该校验与前端部署确认开关
 * __SSO_CSRF_PROTECTION_CONFIRMED__ 配套，为其技术兜底。</p>
 *
 * <p>放行语义（不构成浏览器自动携带凭证的 CSRF 面）：</p>
 * <ul>
 *   <li>无 Origin 头：服务间调用、curl 等非浏览器客户端，或同源 GET 导航
 *       （浏览器对同源 GET 通常不发送 Origin）；</li>
 *   <li>OPTIONS 预检：CORS 预检不携带凭证，拦截只会连带业务请求失败，
 *       无安全收益。</li>
 * </ul>
 *
 * <p>已知边界：Origin 头可被非浏览器客户端伪造，本校验只针对浏览器
 * 场景（浏览器不允许页面脚本篡改 Origin）；非浏览器客户端本就不存在
 * "自动携带凭据 Cookie"的 CSRF 语义。</p>
 */
public final class OriginVerifier {

    private OriginVerifier() {
    }

    /**
     * 判断请求的 Origin 是否允许通过认证链
     *
     * @param request        当前请求
     * @param allowedOrigins 允许跨站携带认证凭证的父平台 origin 白名单（完整 origin 精确匹配）
     * @return true 表示放行（无 Origin / OPTIONS / 白名单命中 / 同源）
     */
    public static boolean isAllowed(HttpServletRequest request, List<String> allowedOrigins) {
        String origin = request.getHeader("Origin");
        if (StringUtils.isEmpty(origin)) {
            return true;
        }
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        if (allowedOrigins != null && allowedOrigins.contains(origin)) {
            return true;
        }
        String host = request.getHeader("Host");
        String originHost = extractHost(origin);
        return host != null && host.equals(originHost);
    }

    /**
     * 从 origin（scheme://host[:port]）中提取 host[:port]，格式非法返回 null
     */
    private static String extractHost(String origin) {
        int schemeEnd = origin.indexOf("://");
        if (schemeEnd < 0) {
            return null;
        }
        return origin.substring(schemeEnd + 3);
    }

}
