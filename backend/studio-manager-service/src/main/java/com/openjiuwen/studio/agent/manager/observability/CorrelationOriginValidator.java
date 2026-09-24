/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import java.net.URI;

/**
 * 出站关联 Header 目标 origin 白名单校验（COM-04 §5.1）。
 *
 * <p>四类客户端适配器（Feign/OkHttp/WebClient/RestTemplate）共用同一套归一化比较：
 * {@code scheme + host + effective port}。拒绝 scheme 不同、端口不同、userinfo、欺骗性后缀主机
 * 和未登记重定向。目标地址配置为空或非法时明确失败，不降级为任意目标。
 *
 * <p>不使用字符串 {@code startsWith}、URL 路径关键字或主机名后缀匹配。
 * {@code http} 默认端口归一化为 80，{@code https} 为 443（与 OkHttp {@code HttpUrl.port()} 一致）。
 */
public final class CorrelationOriginValidator {

    private CorrelationOriginValidator() {
    }

    /**
     * 归一化 origin 比较；任一地址为空/非法或 origin 不匹配即抛 {@code CALL_RUNTIME_ERROR}。
     *
     * @param allowedOrigin 白名单允许的 origin（系统配置值，如 {@code agent_runtime_endpoint}）
     * @param targetUrl     实际出站请求的完整 URL
     */
    public static void requireSameOrigin(String allowedOrigin, String targetUrl) {
        URI allowed = parse(allowedOrigin);
        URI target = parse(targetUrl);
        if (allowed == null || target == null
            || !eq(allowed.getScheme(), target.getScheme())
            || !eq(allowed.getHost(), target.getHost())
            || effectivePort(allowed) != effectivePort(target)
            || hasUserInfo(allowed) || hasUserInfo(target)) {
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
    }

    private static URI parse(String url) {
        if (url == null || url.isEmpty()) {
            return null;
        }
        try {
            URI uri = new URI(url);
            // scheme/host 必须齐备，否则视为非法（不是相对 URL 场景）
            if (uri.getScheme() == null || uri.getHost() == null) {
                return null;
            }
            return uri;
        } catch (Exception e) {
            return null;
        }
    }

    private static int effectivePort(URI uri) {
        int port = uri.getPort();
        if (port != -1) {
            return port;
        }
        return "https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80;
    }

    private static boolean eq(String a, String b) {
        return a == null ? b == null : a.equalsIgnoreCase(b);
    }

    private static boolean hasUserInfo(URI uri) {
        return uri.getUserInfo() != null;
    }
}
