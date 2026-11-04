/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.auth;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.common.dto.auth.OauthInfo;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import lombok.extern.slf4j.Slf4j;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

import org.apache.commons.lang3.StringUtils;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;import org.apache.hc.core5.net.URIBuilder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class McpOauthAdapter {
    private static final String CONTENT_TYPE = "Content-Type";

    private static final String APPLICATION_JSON = "application/json";

    private static final String GRANT_TYPE = "client_credentials";

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    private final Cache<String, String> tokenCache = CacheBuilder.newBuilder()
            .maximumSize(50)
            .expireAfterWrite(1, TimeUnit.HOURS)
            .build();

    public Map<String, String> requestHeaderHandler(OauthInfo oauthInfo, Map<String, String> headers) {
        log.info("Start to execute oauth authentication!");
        String cacheKey = oauthInfo.getEndpointUrl() + "_" + oauthInfo.getClientId();
        String token;
        if (StringUtils.isEmpty(oauthInfo.getClientId())) {
            // 避免空指针
            token = queryOauthTokenFromOauth(oauthInfo);
        } else {
            try {
                token = tokenCache.get(cacheKey, () -> queryOauthTokenFromOauth(oauthInfo));
            } catch (Exception e) {
                log.warn("Fail query token from cache. {}", e.getMessage());
                token = queryOauthTokenFromOauth(oauthInfo);
            }
        }
        headers.put("Authorization", "Bearer " + token);

        return headers;
    }

    private String queryOauthTokenFromOauth(OauthInfo oauthInfo) {
        log.info("Start to query oauth token.");
        SpringBeanUtils.getBean(UrlCheckUtils.class).checkUrl(RequestContextUtils.getRequestProjectId(), oauthInfo.getEndpointUrl());
        URI uri = getRequestURI(oauthInfo);

        long start = System.currentTimeMillis();
        OkHttpClient httpClient = okHttpClientUtils.getHttpClient();

        Request.Builder builder = new Request.Builder();
        builder.addHeader(CONTENT_TYPE, APPLICATION_JSON);
        Request request = builder.url(uri.toString())
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            if (response.code() >= 300) {
                String responseStr = response.body() == null ? "" : response.body().string();
                log.error("Fail query oauth token. clientId:{} url:{}", oauthInfo.getClientId(), oauthInfo.getEndpointUrl());
                throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID);
            }

            ResponseBody body = response.body();
            if (Objects.isNull(body)) {
                log.info("Fail query oauth token. response is empty. clientId:{} url:{}", oauthInfo.getClientId(), oauthInfo.getEndpointUrl());
                throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID);
            }
            String rspStr = body.string();

            log.info("Success query oauth token. clientId:{} url:{}", oauthInfo.getClientId(), oauthInfo.getEndpointUrl());
            ObjectMapper objectMapper = new ObjectMapper();

            return (String) objectMapper.readValue(rspStr, new TypeReference<Map<String, Object>>() {}).get("access_token");
        } catch (IOException e) {
            log.error("Fail request {}, cost: {} ms", oauthInfo.getEndpointUrl(), System.currentTimeMillis() - start, e);
            throw new AgentStudioException(StudioError.MCP_AUTH_DATA_INVALID);
        }
    }


    /**
     * 拼接完成的uri，加入query参数
     * @param oauthInfo oauth鉴权信息
     * @return 拼接完成的uri
     */
    private URI getRequestURI(OauthInfo oauthInfo) {
        log.info("Start to get request uri.");
        try {
            String secret = encryptionAdapter.decrypt(oauthInfo.getClientSecret());

            URIBuilder uriBuilder = new URIBuilder(oauthInfo.getEndpointUrl());
            uriBuilder.addParameter("grant_type", GRANT_TYPE);
            uriBuilder.addParameter("client_id", oauthInfo.getClientId());
            uriBuilder.addParameter("client_secret", secret);
            uriBuilder.addParameter("scope", oauthInfo.getScope());

            return uriBuilder.build();
        } catch (URISyntaxException e) {
            log.error("Fail get request uri. clientId:{} url:{}",oauthInfo.getEndpointUrl(), oauthInfo.getClientId());
            throw new AgentStudioException(StudioError.PLUGIN_AUTH_DATA_INVALID);
        }
    }
}
