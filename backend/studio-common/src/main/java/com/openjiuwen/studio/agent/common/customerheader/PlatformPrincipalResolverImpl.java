/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.SimpleConstants;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * 平台身份解析器实现 — 从 SimpleUserContextFilter.getUserByToken 抽取的 public bean
 *
 * <p>将原 Filter 的 private getUserByToken 逻辑提取为 Spring bean，
 * Filter 和 TaskRuntime 共注入，复用同一组类型异常。
 *
 * <p>异常映射（有意兼容变化）：
 * <ul>
 *   <li>HTTP 401 响应 → {@link InvalidPlatformTokenException}</li>
 *   <li>HTTP 5xx / 网络超时 → {@link PlatformAuthServiceUnavailableException}</li>
 *   <li>响应体解析失败 → {@link PlatformAuthProtocolException}</li>
 * </ul>
 */
@Component
public class PlatformPrincipalResolverImpl implements PlatformPrincipalResolver {

    private static final Logger log = LoggerFactory.getLogger(PlatformPrincipalResolverImpl.class);

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public PlatformPrincipal resolveOrThrow(String platformToken) {
        if (platformToken == null || platformToken.isEmpty()) {
            throw new InvalidPlatformTokenException("Platform token is empty");
        }

        try {
            OkHttpClientUtils okHttpClientUtils = SpringBeanUtils.getBean(OkHttpClientUtils.class);
            OkHttpClient httpClient = okHttpClientUtils.getHttpClient();
            String authEndpoint = SpringBeanUtils.getProperty("feign.client.config.userAuth.url", "");
            String contextPathValue = SpringBeanUtils.getProperty(SimpleConstants.SERVLET_CONTEXT_PATH, "");

            String url = authEndpoint + contextPathValue + SimpleConstants.AUTH_TOKEN_URI;
            Request httpRequest = new Request.Builder()
                .url(url)
                .addHeader("X-Subject-Token", platformToken)
                .get()
                .build();

            try (Response response = httpClient.newCall(httpRequest).execute()) {
                int code = response.code();
                if (code == 401 || code == 403) {
                    throw new InvalidPlatformTokenException("Platform token invalid or expired, HTTP " + code);
                }
                if (code >= 500) {
                    throw new PlatformAuthServiceUnavailableException(
                        "Platform auth service unavailable, HTTP " + code);
                }
                if (!response.isSuccessful() || response.body() == null) {
                    throw new InvalidPlatformTokenException("Platform auth failed, HTTP " + code);
                }

                SimpleUser simpleUser;
                try {
                    simpleUser = objectMapper.readValue(response.body().string(), SimpleUser.class);
                } catch (IOException e) {
                    throw new PlatformAuthProtocolException("Failed to parse auth response body", e);
                }

                if (simpleUser == null || simpleUser.getUserId() == null) {
                    throw new PlatformAuthProtocolException("Auth response missing userId");
                }

                return PlatformPrincipal.from(simpleUser);
            }
        } catch (PlatformAuthException e) {
            throw e;
        } catch (IOException e) {
            throw new PlatformAuthServiceUnavailableException("Platform auth service network error", e);
        } catch (Exception e) {
            log.error("[customer-header] Unexpected error during platform principal resolution", e);
            throw new PlatformAuthProtocolException("Unexpected auth error", e);
        }
    }
}
