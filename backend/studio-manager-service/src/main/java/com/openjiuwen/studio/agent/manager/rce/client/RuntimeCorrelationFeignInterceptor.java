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
 * Runtime Feign 关联 Header 拦截器（COM-04 §6.1 / 复审 4.2）。
 *
 * <p>仅挂在 {@code agentRuntime} 客户端专用配置上；按方法级清单解析策略后
 * 调用统一 Provider 与覆盖算法（大小写不敏感先删后写）。发送前以注入的受信任 origin
 * 对 {@code feignTarget().url()} 执行规范化 origin 校验（scheme+host+effective port），
 * 配置为空/非法/与允许 origin 不一致即失败，不静默发送。缺失必需 MDC 时
 * {@link CorrelationHeaderProvider.MissingContextException} 直接传播——Feign 调用按错误失败，不补造。
 */
public class RuntimeCorrelationFeignInterceptor implements RequestInterceptor {

    private final String allowedOrigin;

    public RuntimeCorrelationFeignInterceptor(String allowedOrigin) {
        this.allowedOrigin = allowedOrigin;
    }

    @Override
    public void apply(RequestTemplate template) {
        Target<?> target = template.feignTarget();
        if (target == null) {
            throw new IllegalStateException("Feign target unavailable for correlation origin validation");
        }
        CorrelationOriginValidator.requireSameOrigin(allowedOrigin, target.url());
        OutboundCorrelationPolicy policy =
            AgentRuntimeFeignMethodCatalog.resolve(template.method(), template.path());
        CorrelationHeaders headers = CorrelationHeaderProvider.provide(policy);
        CorrelationHeaderProvider.apply(headers, new FeignCorrelationHeaderSink(template));
    }
}
