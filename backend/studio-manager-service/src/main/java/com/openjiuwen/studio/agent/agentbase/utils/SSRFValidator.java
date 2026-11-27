/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.utils;

import com.openjiuwen.studio.agent.agentbase.config.SSRFStaticConfig;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.util.CollectionUtils;

import java.net.InetAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

@Slf4j
public class SSRFValidator {

    public static void checkSSRF(String url) {
        if (!isUrlSafe(url)) {
            log.error("url is unsafe ,url is {}", url);
            throw new AgentBaseException(ErrorCode.ADDRESS_ILLEGAL);
        }
    }

    private static boolean isUrlSafe(String url) {

        if (url == null || url.trim().isEmpty()) {
            return true;
        }

        URI uri;
        try {
            uri = new URI(url.trim());
        } catch (URISyntaxException e) {
            log.error("url is not a valid URI, url is {}", url);
            return false;
        }

        // 协议白名单与 SSRF 总开关解耦：即便关闭内网地址校验，也不能放行 file://、ftp://、gopher:// 等协议。
        // 关闭开关只应放宽「内网地址/域名」判定，不应连带取消协议限制。
        String scheme = uri.getScheme();
        if (StringUtils.isEmpty(scheme) || !isProtocolAllowed(scheme)) {
            log.error("protocol is not allowed, url is {}", url);
            return false;
        }

        if (!SSRFStaticConfig.isSsrfValidationEnabled()) {
            return true;
        }

        try {
            String host = uri.getHost();
            if (host == null || host.isEmpty()) {
                return false;
            }
            // 解析主机名为 IP 地址 <防止 DNS 重绑定攻击>
            InetAddress address = InetAddress.getByName(host);

            // 域名白名单检查
            if (SSRFStaticConfig.getAllowedInternalDomains().contains(host)) {
                log.error("host is not allowed, host is {}", host);
                return true;
            }
            // 域名黑名单检查
            if (isBlockedInternalDomain(host)) {
                log.error("host is blocked, host is {}", host);
                return false;
            }
            // 检查是否为私有地址、回环地址、本地地址等
            // 1. 阻止回环地址 (Loopback Address: 127.0.0.1/8, ::1/128)
            // 攻击者访问服务器本机服务
            if (address.isLoopbackAddress()) {
                log.error("host is loopback address, host is {}", host);
                return false;
            }

            // 2. 阻止站点本地地址 (Site Local Address: 私有网络 IP)
            // IPv4: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
            // IPv6: fc00::/7 (Unique Local Address, ULA)
            // 攻击者访问内部局域网中的其他服务器
            if (address.isSiteLocalAddress()) {
                log.error("host is site local address, host is {}", host);
                return false;
            }

            // 3. 阻止链路本地地址 (Link Local Address: 169.254.0.0/16, fe80::/10)
            // 攻击者获取云服务（如 AWS, GCP, Azure）的元数据，这是 SSRF 最常见的利用方式
            if (address.isLinkLocalAddress()) {
                log.error("host is link local address, host is {}", host);
                return false;
            }

            // 4. 阻止任意本地地址 (Any Local Address: 0.0.0.0 或 ::)
            // 虽然通常不直接用于攻击，但出于严格安全考虑，应阻止
            if (address.isAnyLocalAddress()) {
                log.error("host is any local address, host is {}", host);
                return false;
            }

            // 5. 阻止多播地址 (Multicast Address: 224.0.0.0/4, ff00::/8)
            // 通常用于网络发现，也应阻止
            if (address.isMulticastAddress()) {
                log.error("host is multicast address, host is {}", host);
                return false;
            }
            // 可选：检查端口 <防止访问非标准端口>
            int port = uri.getPort();
            if (port != -1 && (port < 1 || port > 65535)) {
                log.error("port is invalid, port is {}", port);
                return false;
            }
            return true;
        } catch (Exception e) {
            log.error("url is invalid, url is {}, error is {}", url, e);
            return false;
        }
    }

    private static boolean isProtocolAllowed(String scheme) {
        return SSRFStaticConfig.getAllowedProtocols().stream()
            .anyMatch(allowed -> allowed != null && allowed.trim().equalsIgnoreCase(scheme));
    }

    private static boolean isBlockedInternalDomain(String host) {
        String lowerHost = host.toLowerCase(Locale.ROOT);
        if (CollectionUtils.isEmpty(SSRFStaticConfig.getBlockedInternalDomains())) {
            return false;
        }

        for (String blockedDomain : SSRFStaticConfig.getBlockedInternalDomains()) {
            if (blockedDomain.startsWith("*.")) {
                String suffix = blockedDomain.substring(2);
                if (lowerHost.endsWith("." + suffix) || lowerHost.equals(suffix)) {
                    return true;
                }
            } else if (lowerHost.equals(blockedDomain)) {
                return true;
            }
        }
        return false;
    }

}
