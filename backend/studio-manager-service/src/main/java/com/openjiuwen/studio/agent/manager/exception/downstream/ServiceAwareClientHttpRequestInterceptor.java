/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpRequestExecution;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.ClientHttpResponse;

import java.io.IOException;

/**
 * COM-04 响应 P1（审视意见 §3.1）: ClientTemplate transport failure 统一适配。
 * <p>
 * RestTemplate 的 {@link DefaultResponseErrorHandler}（含
 * {@link DownstreamClientTemplateErrorHandler}）只在已获得
 * {@code ClientHttpResponse} 且状态为非 2xx 时工作。连接拒绝、DNS、建连超时、
 * 读取前断开等无 HTTP response 的 {@link IOException} 由 RestTemplate 包装为
 * {@code ResourceAccessException}，被业务层 catch 后改码为 {@code 02701115}，
 * 未进入统一 {@code DownstreamFailure → mapper → 02001131/502} 内核。
 *
 * <p>本 interceptor 在最靠近 transport 的统一边界捕获 {@link IOException}，转为
 * 携带显式 service 身份的 {@link DownstreamFailureException}（RuntimeException），
 * 直接传播至 {@code handleDownstreamFailure} 一次映射。
 *
 * <p><b>注意（adversarial ADV-03 订正）</b>：{@code ClientTemplate} 的 {@code @Retryable}
 * 方法<b>未声明</b> {@code exclude = DownstreamFailureException.class}。当前未检出
 * {@code @EnableRetry}，{@code @Retryable} 不生效——生产行为为单次请求。但若未来启用
 * {@code @EnableRetry}，已分类下游失败（确定性 4xx + transport failure）会被重试
 *（maxAttempts=2），违反 COM-04 §5.2"已分类下游失败不被重试"。启用前须给
 * {@code @Retryable} 加 {@code exclude = DownstreamFailureException.class}。
 */
public final class ServiceAwareClientHttpRequestInterceptor implements ClientHttpRequestInterceptor {

    private final DownstreamService service;
    private final DownstreamErrorParser parser;

    public ServiceAwareClientHttpRequestInterceptor(DownstreamService service,
                                                     DownstreamErrorParser parser) {
        if (service == null) {
            throw new IllegalArgumentException("DownstreamService must not be null");
        }
        if (parser == null) {
            throw new IllegalArgumentException("DownstreamErrorParser must not be null");
        }
        this.service = service;
        this.parser = parser;
    }

    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body,
                                        ClientHttpRequestExecution execution) throws IOException {
        try {
            return execution.execute(request, body);
        } catch (IOException e) {
            // transport failure（无 HTTP 响应）→ 携带 service 身份的 DownstreamFailureException
            DownstreamFailure failure = parser.fromTransportFailure(
                service, Transport.CLIENT_TEMPLATE, e);
            throw new DownstreamFailureException(failure);
        }
    }
}
