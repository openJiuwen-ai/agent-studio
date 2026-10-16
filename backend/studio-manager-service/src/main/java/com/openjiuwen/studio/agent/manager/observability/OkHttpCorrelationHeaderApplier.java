/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Set;

import okhttp3.OkHttpClient;
import okhttp3.Request;

/**
 * OkHttp/SSE 出站关联 Header 适配器（COM-04 §6.2）。
 *
 * <p>调用方必须显式给出策略与最终 URI；本适配器先做目标 origin 白名单校验
 * （scheme + host + effective port 归一化比较，配置为空/非法/不匹配即失败不发送），
 * 再把统一 Provider 的结果按覆盖算法写入 {@link Request.Builder}。
 * 业务 Header（鉴权、Content-Type 等）由原调用逻辑处理；调用方复制入站 Header 时
 * 应先用 {@link #isCorrelationHeader(String)} 排除三个关联 Header，最终权威值只来自这里。
 */
public final class OkHttpCorrelationHeaderApplier {

    private OkHttpCorrelationHeaderApplier() {
    }

    /**
     * Runtime 执行路径（Agent/Workflow/网页执行/节点）：origin 校验 + RUNTIME_EXECUTION 注入。
     *
     * @throws AgentStudioException CALL_RUNTIME_ERROR——目标 origin 不在白名单或 URL 非法
     */
    public static Request.Builder applyRuntimeExecution(String allowedOrigin, String targetUrl,
        Request.Builder builder) {
        return apply(OutboundCorrelationPolicy.RUNTIME_EXECUTION, allowedOrigin, targetUrl, builder);
    }

    /**
     * 目标感知的通用注入（§6.2）：origin 校验 + 按策略读取 MDC 权威值并先删后写。
     * Runtime 执行路径传 {@link OutboundCorrelationPolicy#RUNTIME_EXECUTION} + Runtime origin；
     * Builder 流式路径传 {@link OutboundCorrelationPolicy#BUILDER} + Builder origin——
     * 不得用固定 Runtime execution 策略同时服务 Builder。
     *
     * @throws AgentStudioException CALL_RUNTIME_ERROR——目标 origin 不在白名单或 URL 非法
     * @throws CorrelationHeaderProvider.MissingContextException MDC 缺少策略必需值
     */
    public static Request.Builder apply(OutboundCorrelationPolicy policy, String allowedOrigin, String targetUrl,
        Request.Builder builder) {
        requireSameOrigin(allowedOrigin, targetUrl);
        CorrelationHeaderProvider.apply(
            CorrelationHeaderProvider.provide(policy),
            new OkHttpSink(builder));
        return builder;
    }

    /** 归一化 origin 比较；任一地址为空/非法即失败，不降级为任意目标（§5.1）。 */
    static void requireSameOrigin(String allowedOrigin, String targetUrl) {
        CorrelationOriginValidator.requireSameOrigin(allowedOrigin, targetUrl);
    }

    /** 三个关联 Header 名的大小写不敏感判定——供调用方复制入站 Header 时排除。 */
    public static boolean isCorrelationHeader(String name) {
        return "X-Request-Id".equalsIgnoreCase(name) || "TraceID".equalsIgnoreCase(name)
            || "X-Execution-Id".equalsIgnoreCase(name);
    }

    /**
     * 禁用自动重定向的客户端变体（共享连接池）——防止关联 Header 被携带到新 origin
     * （§6.2 第 7 条；选择"禁用重定向"分支，重定向场景显式失败而非静默跟随）。
     */
    public static OkHttpClient withoutRedirects(OkHttpClient base) {
        return base.newBuilder().followRedirects(false).followSslRedirects(false).build();
    }

    /** Request.Builder Sink；{@link #headerNames()} 依赖 url 已设置（调用时序保证）。 */
    private static final class OkHttpSink implements CorrelationHeaderProvider.CorrelationHeaderSink {
        private final Request.Builder builder;

        OkHttpSink(Request.Builder builder) {
            this.builder = builder;
        }

        @Override
        public Set<String> headerNames() {
            return builder.build().headers().names();
        }

        @Override
        public void removeHeader(String name) {
            builder.removeHeader(name);
        }

        @Override
        public void setHeader(String name, String value) {
            builder.header(name, value);
        }
    }
}
