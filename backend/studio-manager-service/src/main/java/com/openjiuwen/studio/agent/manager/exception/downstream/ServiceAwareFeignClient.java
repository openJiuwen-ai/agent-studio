/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.exception.downstream;

import com.openjiuwen.studio.agent.common.error.DownstreamService;

import feign.Client;
import feign.Request;
import feign.Response;

import java.io.IOException;

/**
 * COM-04 响应 §5.1/P1-2: Feign {@link Client} 装饰器——保留 Runtime/Builder 身份。
 * <p>
 * Feign 无 HTTP 响应的 transport failure（DNS/connect/TLS/read timeout）不经
 * {@code ErrorDecoder}，直接抛 {@code IOException} 被 Feign 包为
 * {@code FeignException}，全局 Advice 无法判定来源，统一标为 {@code EXTERNAL}。
 * <p>
 * 本装饰器在 {@code Client.execute} 层捕获 {@code IOException}，转为携带
 * 显式 service 身份的 {@link DownstreamFailureException}（RuntimeException），
 * 直接传播至 {@code handleDownstreamFailure} 一次映射，不经过
 * {@code handleFeignException} 的 {@code EXTERNAL} 兜底。
 *
 * <p>不增加重试：{@code DownstreamFailureException} 不是 {@code RetryableException}，
 * Feign 不会重试。
 */
public final class ServiceAwareFeignClient implements Client {

    private final DownstreamService service;
    private final Client delegate;
    private final DownstreamErrorParser parser;

    public ServiceAwareFeignClient(DownstreamService service, Client delegate,
                                   DownstreamErrorParser parser) {
        if (service == null) {
            throw new IllegalArgumentException("DownstreamService must not be null");
        }
        if (delegate == null) {
            throw new IllegalArgumentException("Delegate Client must not be null");
        }
        this.service = service;
        this.delegate = delegate;
        this.parser = parser;
    }

    @Override
    public Response execute(Request request, Request.Options options) throws IOException {
        try {
            return delegate.execute(request, options);
        } catch (IOException e) {
            // transport failure（无 HTTP 响应）→ 携带 service 身份的 DownstreamFailureException
            DownstreamFailure failure = parser.fromTransportFailure(service, Transport.FEIGN, e);
            throw new DownstreamFailureException(failure);
        }
    }
}
