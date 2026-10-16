/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.manager.observability.CorrelationHeaderProvider;
import com.openjiuwen.studio.agent.manager.observability.CorrelationHeaders;
import com.openjiuwen.studio.agent.manager.observability.CorrelationOriginValidator;
import com.openjiuwen.studio.agent.manager.observability.OutboundCorrelationPolicy;

import feign.RequestInterceptor;
import feign.RequestTemplate;
import feign.Target;

/**
 * Builder Feign 关联 Header 拦截器（COM-04 §6.1 / 复审 4.2）。
 *
 * <p>仅挂在 {@code agentBuilder} 客户端专用配置上；固定 BUILDER 策略
 * （request/trace，明确删除 execution），调用统一 Provider 与覆盖算法。
 * 发送前以注入的受信任 origin 对 {@code feignTarget().url()} 执行规范化 origin 校验。
 */
public class BuilderCorrelationFeignInterceptor implements RequestInterceptor {

    private final String allowedOrigin;

    public BuilderCorrelationFeignInterceptor(String allowedOrigin) {
        this.allowedOrigin = allowedOrigin;
    }

    @Override
    public void apply(RequestTemplate template) {
        Target<?> target = template.feignTarget();
        if (target == null) {
            throw new IllegalStateException("Feign target unavailable for correlation origin validation");
        }
        CorrelationOriginValidator.requireSameOrigin(allowedOrigin, target.url());
        CorrelationHeaders headers = CorrelationHeaderProvider.provide(OutboundCorrelationPolicy.BUILDER);
        CorrelationHeaderProvider.apply(headers, new FeignCorrelationHeaderSink(template));
    }
}
