/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.function.Consumer;

import org.springframework.http.HttpHeaders;

/**
 * WebClient 出站关联 Header 适配器（COM-04 §6.3）。
 *
 * <p>共享 {@code WebClient} Bean 同时访问 Runtime 与 Builder，禁止在其上安装无条件全局 Filter。
 * 本适配器由每个调用点显式选择策略并传入目标 origin + 最终 URL：先做白名单 origin 校验，
 * 再在调用线程的有效 MDC 上下文内读取权威值（{@link CorrelationHeaderProvider#provide}），
 * 返回的 {@link Consumer} 在请求构建时按覆盖算法写入。
 *
 * <p>不在单例 Filter 创建时捕获 MDC；MDC 在调用线程（HTTP 入站 scope 或后台入口 scope）已建立。
 * 返回的 Header 值是不可变字符串，跨 Reactor 边界稳定。
 */
public final class WebClientCorrelationHeaderApplier {

    private WebClientCorrelationHeaderApplier() {
    }

    /**
     * 校验目标 origin 并读取当前 MDC，返回可链式接入 {@code .headers(...)} 的 Header 写入器。
     *
     * @param policy        出站策略（Runtime 执行/非执行、Builder）
     * @param allowedOrigin 白名单允许 origin（系统配置值，如 {@code agent_runtime_endpoint}）
     * @param targetUrl     实际出站请求的完整 URL
     * @return 写入 {@link HttpHeaders} 的 Consumer
     * @throws com.openjiuwen.studio.agent.common.exception.AgentStudioException 目标 origin 不在白名单
     * @throws CorrelationHeaderProvider.MissingContextException MDC 缺少策略必需值
     */
    public static Consumer<HttpHeaders> apply(OutboundCorrelationPolicy policy, String allowedOrigin,
        String targetUrl) {
        CorrelationOriginValidator.requireSameOrigin(allowedOrigin, targetUrl);
        CorrelationHeaders headers = CorrelationHeaderProvider.provide(policy);
        return httpHeaders -> CorrelationHeaderProvider.apply(headers, new HttpHeadersCorrelationSink(httpHeaders));
    }
}
