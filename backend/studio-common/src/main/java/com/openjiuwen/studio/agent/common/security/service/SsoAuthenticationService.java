/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.security.service;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.security.properties.AuthProperties;

import javax.net.ssl.SSLContext;
import lombok.extern.slf4j.Slf4j;

import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.client5.http.io.HttpClientConnectionManager;
import org.apache.hc.client5.http.ssl.DefaultClientTlsStrategy;
import org.apache.hc.client5.http.ssl.NoopHostnameVerifier;
import org.apache.hc.core5.reactor.ssl.SSLBufferMode;
import org.apache.hc.core5.ssl.SSLContextBuilder;
import org.apache.hc.core5.util.Timeout;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.HttpComponentsClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.security.SecureRandom;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * SSO 远程鉴权服务
 *
 * <p>当 auth.sso.validate-url 配置后启用。通过调用客户 SSO 鉴权接口验证 Access-Token，
 * 并获取用户信息。内置 Token 缓存机制，在 SSO 服务不可用时降级使用缓存结果。</p>
 */
@Slf4j
@Service
public class SsoAuthenticationService {

    /** SSO 连接超时时间（秒） */
    private static final int CONNECT_TIMEOUT_SECONDS = 3;

    /** SSO 读取超时时间（秒） */
    private static final int READ_TIMEOUT_SECONDS = 5;

    /** Token 缓存有效期（秒） */
    private static final long TOKEN_CACHE_TTL_SECONDS = 300;

    private final RestTemplate restTemplate;

    private final AuthProperties authProperties;

    private final ConcurrentHashMap<String, CachedUserInfo> tokenCache = new ConcurrentHashMap<>();

    /**
     * 构造 SSO 鉴权服务，初始化支持跳过 SSL 校验的 RestTemplate
     */
    public SsoAuthenticationService(AuthProperties authProperties) {
        this.authProperties = authProperties;
        this.restTemplate = new RestTemplate(createHttpRequestFactory());
    }

    /**
     * Token 缓存条目，记录用户信息和缓存时间
     */
    private static class CachedUserInfo {
        final SimpleUser userInfo;
        final long cachedAt;

        CachedUserInfo(SimpleUser userInfo) {
            this.userInfo = userInfo;
            this.cachedAt = System.currentTimeMillis();
        }

        boolean isExpired() {
            return System.currentTimeMillis() - cachedAt > TimeUnit.SECONDS.toMillis(TOKEN_CACHE_TTL_SECONDS);
        }
    }

    /**
     * 创建跳过 SSL 证书校验的 HTTP 请求工厂，用于对接自签名证书的 SSO 服务
     */
    private ClientHttpRequestFactory createHttpRequestFactory() {
        try {
            SSLContext sslContext = SSLContextBuilder.create()
                .setSecureRandom(SecureRandom.getInstanceStrong())
                .loadTrustMaterial(null, (x509Certificates, s) -> true)
                .build();

            HttpClientConnectionManager connectionManager = PoolingHttpClientConnectionManagerBuilder.create()
                .setTlsSocketStrategy(
                    new DefaultClientTlsStrategy(sslContext, new String[] {"TLSv1.2", "TLSv1.3"}, null,
                        SSLBufferMode.STATIC, NoopHostnameVerifier.INSTANCE))
                .setDefaultConnectionConfig(ConnectionConfig.custom()
                    .setConnectTimeout(Timeout.ofSeconds(CONNECT_TIMEOUT_SECONDS))
                    .setSocketTimeout(Timeout.ofSeconds(READ_TIMEOUT_SECONDS))
                    .build())
                .build();

            HttpComponentsClientHttpRequestFactory factory = new HttpComponentsClientHttpRequestFactory(
                HttpClients.custom().setConnectionManager(connectionManager).build());
            return factory;
        } catch (Exception e) {
            log.error("Failed to create SSL trusted RestTemplate, fallback to default", e);
            return new HttpComponentsClientHttpRequestFactory();
        }
    }

    /**
     * 调用 SSO 鉴权接口验证 Token 并获取用户信息
     *
     * @param accessToken 访问令牌
     * @return 用户信息，验证失败返回 null
     */
    public SimpleUser authenticate(String accessToken) {
        try {
            String ssoValidateUrl = authProperties.getSso().getValidateUrl();
            String ssoHeaderName = authProperties.getSso().getHeader();

            log.info("Start SSO authentication request: {}", ssoValidateUrl);

            HttpHeaders headers = new HttpHeaders();
            headers.set("Content-Type", "application/json");
            headers.set(ssoHeaderName, accessToken);

            HttpEntity<String> entity = new HttpEntity<>(headers);

            Map<String, Object> responseBody = restTemplate.exchange(ssoValidateUrl, HttpMethod.POST, entity,
                new ParameterizedTypeReference<Map<String, Object>>() {}).getBody();
            if (responseBody != null) {
                log.info("SSO authentication successful");
                SimpleUser userInfo = convertToUserInfo(responseBody);
                tokenCache.put(accessToken, new CachedUserInfo(userInfo));
                return userInfo;
            }

            log.error("SSO authentication failed: response body is null, SSO service may be malfunctioning");
            return null;

        } catch (HttpClientErrorException e) {
            if (e.getStatusCode() == HttpStatusCode.valueOf(401)) {
                log.warn("SSO authentication failed: invalid or expired token");
                tokenCache.remove(accessToken);
            } else {
                log.error("SSO authentication failed: SSO service returned HTTP {}", e.getStatusCode());
            }
            return null;
        } catch (ResourceAccessException e) {
            log.error("SSO service unavailable: {}", e.getMessage());
            return getFromCache(accessToken);
        } catch (Exception e) {
            log.error("SSO service unavailable: unexpected error - {}", e.getMessage());
            return getFromCache(accessToken);
        }
    }

    /**
     * SSO 服务不可用时尝试从缓存获取用户信息
     */
    private SimpleUser getFromCache(String accessToken) {
        CachedUserInfo cached = tokenCache.get(accessToken);
        if (cached != null && !cached.isExpired()) {
            log.warn("SSO service unavailable, using cached authentication result for token");
            return cached.userInfo;
        }
        log.error("SSO service unavailable and no valid cache found, request will be rejected");
        return null;
    }

    /**
     * 将 SSO 响应体按配置的 Claims 映射转换为 SimpleUser
     */
    private SimpleUser convertToUserInfo(Map<String, Object> ssoUserInfo) {
        AuthProperties.UserInfoConfig userInfoConfig = authProperties.getUserInfo();
        AuthProperties.UserInfoConfig.ClaimsConfig claims = userInfoConfig.getClaims();
        AuthProperties.UserInfoConfig.DefaultsConfig defaults = userInfoConfig.getDefaults();

        return SimpleUser.builder()
            .userId(getValueOrDefault(extractClaim(ssoUserInfo, claims.getUserId()), "unknown"))
            .userName(getValueOrDefault(extractClaim(ssoUserInfo, claims.getUserName()), "unknown"))
            .domainId(getValueOrDefault(extractClaim(ssoUserInfo, claims.getDomainId()), defaults.getDomainId()))
            .projectId(getValueOrDefault(extractClaim(ssoUserInfo, claims.getProjectId()), defaults.getProjectId()))
            .build();
    }

    /**
     * 从 SSO 响应中按 Claim 名称提取字段值
     */
    private String extractClaim(Map<String, Object> ssoUserInfo, String claimName) {
        if (claimName == null || claimName.isBlank()) {
            return null;
        }
        Object value = ssoUserInfo.get(claimName);
        return value != null ? value.toString() : null;
    }

    /**
     * 获取值，如果为空则返回默认值
     */
    private String getValueOrDefault(String value, String defaultValue) {
        return (value != null && !value.isBlank()) ? value : defaultValue;
    }
}
