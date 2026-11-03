/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.io.IOException;

import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpRequestExecution;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.http.client.ClientHttpResponse;

/**
 * Builder 目标 RestTemplate/ClientTemplate 关联 Header 拦截器（COM-04 §6.4）。
 *
 * <p>仅挂载在 {@code builderClientTemplate}（Builder 专用实例）上，固定使用 {@link OutboundCorrelationPolicy#BUILDER}：
 * 注入 {@code X-Request-Id}/{@code TraceID}，明确删除任何 {@code X-Execution-Id}。
 * 在调用线程（HTTP 入站 scope 或后台入口 scope）的有效 MDC 上下文内同步读取权威值；
 * 拦截器执行时校验最终请求 URI origin 与配置的 Builder origin 一致，不匹配即失败不发送。
 *
 * <p>通用 {@code remoteClientTemplate}（Manager 自调用等）不挂载本拦截器——未登记目标收不到三个平台关联 Header。
 */
public class BuilderCorrelationInterceptor implements ClientHttpRequestInterceptor {

    private final String allowedOrigin;

    public BuilderCorrelationInterceptor(String allowedOrigin) {
        this.allowedOrigin = allowedOrigin;
    }

    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body, ClientHttpRequestExecution execution)
        throws IOException {
        CorrelationOriginValidator.requireSameOrigin(allowedOrigin, request.getURI().toString());
        CorrelationHeaderProvider.apply(
            CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.BUILDER),
            new HttpHeadersCorrelationSink(request.getHeaders()));
        return execution.execute(request, body);
    }
}
