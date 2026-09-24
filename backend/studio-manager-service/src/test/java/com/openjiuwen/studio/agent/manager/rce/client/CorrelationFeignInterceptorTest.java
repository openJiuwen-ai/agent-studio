/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.manager.observability.CorrelationHeaderProvider;
import com.openjiuwen.studio.agent.manager.observability.MdcKeys;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

import feign.RequestTemplate;
import feign.Target;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-04 §10.3（Feign 行）/ 复审 4.2：拦截器在 RequestTemplate 级的行为——执行方法三 Header、
 * 非执行/Builder 两 Header 且删除伪造 execution、伪造变体被先删后写、
 * 规范化 origin 校验、缺失上下文与未登记路由明确失败。
 */
class CorrelationFeignInterceptorTest {

    private static final String RUNTIME_ORIGIN = "http://runtime:8080";
    private static final String BUILDER_ORIGIN = "http://builder:8080";

    private final RuntimeCorrelationFeignInterceptor runtimeInterceptor =
        new RuntimeCorrelationFeignInterceptor(RUNTIME_ORIGIN);
    private final BuilderCorrelationFeignInterceptor builderInterceptor =
        new BuilderCorrelationFeignInterceptor(BUILDER_ORIGIN);

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    private void fullMdc() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
    }

    private static RequestTemplate runtimePost(String uri) {
        return targeted(AgentRuntimeClient.class, "agentRuntime", RUNTIME_ORIGIN, "POST", uri);
    }

    private static RequestTemplate builderPost(String uri) {
        return targeted(AgentBuilderClient.class, "agentBuilder", BUILDER_ORIGIN, "POST", uri);
    }

    private static RequestTemplate targeted(Class<?> type, String name, String origin, String method, String uri) {
        RequestTemplate template = new RequestTemplate().method(method).uri(uri);
        template.feignTarget(new Target.HardCodedTarget<>(type, name, origin));
        return template;
    }

    private static String first(RequestTemplate template, String name) {
        return template.headers().entrySet().stream()
            .filter(e -> e.getKey().equalsIgnoreCase(name))
            .findFirst().map(e -> e.getValue().iterator().next()).orElse(null);
    }

    private static int count(RequestTemplate template, String name) {
        return template.headers().entrySet().stream()
            .filter(e -> e.getKey().equalsIgnoreCase(name))
            .mapToInt(e -> e.getValue().size()).sum();
    }

    /** 执行方法：三 Header 同 MDC 权威值；伪造大小写变体被删除替换。 */
    @Test
    void runtimeInterceptor_executionPath_threeAuthoritativeHeaders_forgedReplaced() {
        fullMdc();
        RequestTemplate template = runtimePost("/v1/p1/agents/a1/conversations/c1")
            .header("x-request-id", "forged-1")
            .header("X-REQUEST-ID", "forged-2")
            .header("X-Execution-Id", "forged-exec");

        runtimeInterceptor.apply(template);

        assertThat(count(template, "X-Request-Id")).isEqualTo(1);
        assertThat(first(template, "X-Request-Id")).isEqualTo("req-1");
        assertThat(first(template, "TraceID")).isEqualTo("trace-1");
        assertThat(first(template, "X-Execution-Id")).isEqualTo("exec-1");
    }

    /** 非执行方法（listIndustry 反向路径）：request/trace 注入，伪造 execution 被删除。 */
    @Test
    void runtimeInterceptor_nonExecutionPath_executionStripped() {
        fullMdc();
        RequestTemplate template = targeted(AgentRuntimeClient.class, "agentRuntime", RUNTIME_ORIGIN, "GET",
            "/v1/p1/agent-builder/prompt/industry/list")
            .header("X-Execution-Id", "forged-exec");

        runtimeInterceptor.apply(template);

        assertThat(first(template, "X-Request-Id")).isEqualTo("req-1");
        assertThat(first(template, "TraceID")).isEqualTo("trace-1");
        assertThat(count(template, "X-Execution-Id")).isZero();
    }

    /** 执行方法缺 execution MDC → MissingContextException 传播（Feign 调用失败，不静默）。 */
    @Test
    void runtimeInterceptor_executionPathMissingExecution_fails() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        RequestTemplate template = runtimePost("/v1/p1/agents/a1/conversations/c1");

        assertThatThrownBy(() -> runtimeInterceptor.apply(template))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class);
    }

    /** 未登记路由 → 治理错误，调用失败。 */
    @Test
    void runtimeInterceptor_unclassifiedPath_fails() {
        fullMdc();
        assertThatThrownBy(() -> runtimeInterceptor.apply(runtimePost("/v1/unknown/path")))
            .isInstanceOf(IllegalStateException.class);
    }

    /** 复审 4.2：feignTarget origin 与允许 origin 不一致 → 失败，不发送。 */
    @Test
    void runtimeInterceptor_targetOriginMismatch_fails() {
        fullMdc();
        RequestTemplate template = targeted(AgentRuntimeClient.class, "agentRuntime",
            "http://evil:8080", "POST", "/v1/p1/agents/a1/conversations/c1");

        assertThatThrownBy(() -> runtimeInterceptor.apply(template))
            .isInstanceOf(com.openjiuwen.studio.agent.common.exception.AgentStudioException.class);
    }

    /** 复审 4.2：feignTarget 缺失 → 明确失败（不静默发送）。 */
    @Test
    void runtimeInterceptor_missingFeignTarget_fails() {
        fullMdc();
        RequestTemplate template = new RequestTemplate().method("POST")
            .uri("/v1/p1/agents/a1/conversations/c1");

        assertThatThrownBy(() -> runtimeInterceptor.apply(template))
            .isInstanceOf(IllegalStateException.class);
    }

    /** Builder：固定两 Header；伪造 execution（含大小写变体）全部删除。 */
    @Test
    void builderInterceptor_twoHeaders_executionNeverPresent() {
        fullMdc();
        RequestTemplate template = builderPost("/v1/builder/anything")
            .header("x-execution-id", "forged")
            .header("X-Execution-Id", "forged-2");

        builderInterceptor.apply(template);

        assertThat(first(template, "X-Request-Id")).isEqualTo("req-1");
        assertThat(first(template, "TraceID")).isEqualTo("trace-1");
        assertThat(count(template, "X-Execution-Id")).isZero();
    }

    /** Builder 缺 request MDC → 失败（不回退生成）。 */
    @Test
    void builderInterceptor_missingRequest_fails() {
        assertThatThrownBy(() -> builderInterceptor.apply(builderPost("/v1/builder/anything")))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class);
    }

    /** 复审 4.2：Builder feignTarget origin 与允许 origin 不一致 → 失败。 */
    @Test
    void builderInterceptor_targetOriginMismatch_fails() {
        fullMdc();
        RequestTemplate template = targeted(AgentBuilderClient.class, "agentBuilder",
            "http://evil:8080", "POST", "/v1/builder/anything");

        assertThatThrownBy(() -> builderInterceptor.apply(template))
            .isInstanceOf(com.openjiuwen.studio.agent.common.exception.AgentStudioException.class);
    }

    /** CustomerHeader 透传排除：三个关联 Header（含大小写变体）不参与客户透传。 */
    @Test
    void customerHeaderExclusion_caseInsensitive() {
        assertThat(CustomerHeaderFeignInterceptor.isCorrelationHeader("X-Request-Id")).isTrue();
        assertThat(CustomerHeaderFeignInterceptor.isCorrelationHeader("x-request-id")).isTrue();
        assertThat(CustomerHeaderFeignInterceptor.isCorrelationHeader("TRACEID")).isTrue();
        assertThat(CustomerHeaderFeignInterceptor.isCorrelationHeader("X-EXECUTION-ID")).isTrue();
        assertThat(CustomerHeaderFeignInterceptor.isCorrelationHeader("x-customer-custom")).isFalse();
    }
}
