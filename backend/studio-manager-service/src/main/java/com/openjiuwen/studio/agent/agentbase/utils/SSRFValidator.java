/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.utils;

import com.openjiuwen.studio.agent.agentbase.config.SSRFStaticConfig;
import com.openjiuwen.studio.agent.common.utils.SensitiveLogContext;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.foundation.base.exception.AgentBaseException;
import com.openjiuwen.studio.agent.foundation.base.exception.ErrorCode;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.util.CollectionUtils;

import java.net.InetAddress;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

@Slf4j
public class SSRFValidator {

    /**
     * knowledge.ssrf.allowed-protocols 未注入或配置为空时的兜底协议白名单，与 application-manager.yml 的默认值一致。
     * 配置异常时不能静默 fail-closed 拒掉所有知识库连接，否则表现为「保存/测试连接全部失败」且难以定位。
     */
    private static final Set<String> DEFAULT_ALLOWED_PROTOCOLS = Set.of("http", "https");

    /** scheme 语法（RFC3986）：ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )。 */
    private static final Pattern SCHEME_PATTERN = Pattern.compile("^[A-Za-z][A-Za-z0-9+.\\-]*$");

    /** 白名单为空只在首次命中时告警一次，避免在校验热路径上刷日志。 */
    private static volatile boolean emptyProtocolsWarned;

    public static void checkSSRF(String url) {
        if (!isUrlSafe(url)) {
            log.error("url is unsafe, url is {}", maskUrl(url));
            throw new AgentBaseException(ErrorCode.ADDRESS_ILLEGAL);
        }
    }

    private static boolean isUrlSafe(String url) {

        if (StringUtils.isBlank(url)) {
            return true;
        }
        String trimmed = url.trim();

        // 协议白名单与 SSRF 总开关解耦：即便关闭内网地址校验，也不能放行 file://、ftp://、gopher:// 等协议。
        // 关闭开关只应放宽「内网地址/域名」判定，不应连带取消协议限制。
        // 这里只做宽松的 scheme 提取（第一个 ':' 之前 + RFC3986 scheme 语法），不要求整串通过 URI 严格解析：
        // 存量 endpoint 可能含空格、非 ASCII、未编码花括号，HTTP 客户端本身容忍这些字符，
        // 关闭 SSRF 校验不应反而新增语法拒绝；严格解析只在需要做 host/IP 判定时才要求。
        String scheme = extractScheme(trimmed);
        if (!isProtocolAllowed(scheme)) {
            log.error("protocol is not allowed, scheme is {}, url is {}", scheme, maskUrl(url));
            return false;
        }

        if (!SSRFStaticConfig.isSsrfValidationEnabled()) {
            return true;
        }

        URI uri;
        try {
            uri = new URI(trimmed);
        } catch (URISyntaxException e) {
            log.error("url is not a valid URI, url is {}, reason is {} at index {}", maskUrl(url), e.getReason(),
                e.getIndex());
            return false;
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
            log.error("url is invalid, url is {}, error is {}", maskUrl(url), e);
            return false;
        }
    }

    /**
     * 宽松提取 scheme：取第一个 ':' 之前的部分并校验 RFC3986 scheme 语法。
     *
     * @param url 已 trim 的原始 URL
     * @return 合法 scheme（保持原始大小写），无法提取时返回 null
     */
    private static String extractScheme(String url) {
        int colonIndex = url.indexOf(':');
        if (colonIndex <= 0) {
            return null;
        }
        String candidate = url.substring(0, colonIndex);
        return SCHEME_PATTERN.matcher(candidate).matches() ? candidate : null;
    }

    /**
     * 判断 scheme 是否命中 allowed-protocols 白名单，比较时忽略首尾空白与大小写（配置成 HTTPS,HTTP 也不会误判）。
     *
     * <p>白名单为空时回退到 {@link #DEFAULT_ALLOWED_PROTOCOLS} 并告警，避免配置异常导致全部连接被静默拒绝。
     */
    private static boolean isProtocolAllowed(String scheme) {
        if (StringUtils.isBlank(scheme)) {
            return false;
        }
        Set<String> allowedProtocols = SSRFStaticConfig.getAllowedProtocols();
        if (CollectionUtils.isEmpty(allowedProtocols)) {
            if (!emptyProtocolsWarned) {
                emptyProtocolsWarned = true;
                log.warn("knowledge.ssrf.allowed-protocols is empty, fallback to {}", DEFAULT_ALLOWED_PROTOCOLS);
            }
            allowedProtocols = DEFAULT_ALLOWED_PROTOCOLS;
        }
        String normalized = scheme.trim();
        for (String allowed : allowedProtocols) {
            if (allowed != null && allowed.trim().equalsIgnoreCase(normalized)) {
                return true;
            }
        }
        return false;
    }

    /** 日志脱敏：先去掉查询串（可能含 AK/Signature 等凭据），再遮蔽当前线程登记的敏感值。 */
    private static String maskUrl(String url) {
        return SensitiveLogContext.mask(UrlCheckUtils.redactUrlQuery(url));
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
