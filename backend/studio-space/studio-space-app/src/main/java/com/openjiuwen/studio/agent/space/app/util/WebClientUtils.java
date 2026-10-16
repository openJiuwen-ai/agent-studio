/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2022. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.app.util;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.space.common.constant.HeaderConstant;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceErrorCodes;
import com.openjiuwen.studio.agent.space.common.exception.AgentSpaceException;
import com.openjiuwen.studio.agent.space.common.utils.CollectionUtil;

import io.netty.handler.ssl.SslContext;
import io.netty.handler.ssl.SslContextBuilder;
import io.netty.handler.ssl.util.InsecureTrustManagerFactory;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.netty.http.client.HttpClient;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

import javax.net.ssl.SSLException;

/**
 * 调用第三方SSE类型接口工具类
 */
@Slf4j
public class WebClientUtils {
    private static final WebClient WEB_CLIENT;

    static {
        SslContext sslContext = createSSLContext();
        HttpClient httpClient = HttpClient.create().secure(t -> t.sslContext(sslContext));
        WEB_CLIENT = WebClient.builder().clientConnector(new ReactorClientHttpConnector(httpClient)).build();
    }

    private static SslContext createSSLContext() {
        try {
            return SslContextBuilder.forClient().trustManager(InsecureTrustManagerFactory.INSTANCE).build();
        } catch (SSLException e) {
            log.error("create Client is error,error message is : {}", e.getMessage());
            throw new AgentSpaceException("system error.");
        }
    }

    /**
     * 获取sse返回的chunk
     */
    public static Flux<String> getSseResponseChunk(String url, JSONObject request, Map<String, String> headers) {
        return WEB_CLIENT.post()
            .uri(url)
            .headers(h -> h.addAll(getHeader(headers)))
            .body(BodyInserters.fromValue(request))
            .retrieve()
            .onStatus(HttpStatusCode::is5xxServerError,
                // 捕获所有5xx错误
                response -> {
                    // 1. 可以记录详细的错误日志
                    // 2. 可以解析response body，获取更多错误信息
                    return response.bodyToMono(String.class).flatMap(errorBody -> {
                        log.error("post sse error");
                        return Mono.error(new AgentSpaceException(AgentSpaceErrorCodes.POST_SSE_EXCEPTION,
                            "server responded with " + response.statusCode()));
                    });
                })
            .onStatus(HttpStatusCode::is4xxClientError,
                // 4xx错误
                response -> response.bodyToMono(String.class).flatMap(errorBody -> {
                    log.error("post error");
                    return Mono.error(new AgentSpaceException(AgentSpaceErrorCodes.POST_SSE_EXCEPTION,
                        "client responded with " + response.statusCode()));
                }))
            .bodyToFlux(String.class);
    }

    private static HttpHeaders getHeader(Map<String, String> headers) {
        // 设置请求头
        HttpHeaders forwardHeaders = new HttpHeaders();
        if (CollectionUtil.isNotEmpty(headers)) {
            headers.forEach(forwardHeaders::add);
        }
        forwardHeaders.add(HeaderConstant.HEADER_CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE);
        return forwardHeaders;
    }
}
