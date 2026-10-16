/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.prompt.engineering.remote.ClientTemplate;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.DefaultResponseErrorHandler;

import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.http.HttpMethod.POST;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * COM-04 §6.4/§10.3（RestTemplate 行）：builderClientTemplate 通过 {@link BuilderCorrelationInterceptor}
 * 在调用线程 MDC 内注入 BUILDER 两 Header、删除 execution、校验 origin。用 MockRestServiceServer
 * 捕获实际出站请求。
 */
class BuilderCorrelationInterceptorTest {

    private ClientTemplate builderClientTemplate;
    private ClientTemplate mismatchedClientTemplate;
    private MockRestServiceServer server;
    private MockRestServiceServer mismatchServer;

    private static final String BUILDER_ORIGIN = "http://builder";

    @BeforeEach
    void setUp() {
        ClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        DefaultResponseErrorHandler handler = new DefaultResponseErrorHandler();
        builderClientTemplate = new ClientTemplate(factory, handler,
            new BuilderCorrelationInterceptor(BUILDER_ORIGIN));
        server = MockRestServiceServer.bindTo(restTemplateOf(builderClientTemplate)).build();

        // origin 配置为别的 host，用于校验不匹配失败
        mismatchedClientTemplate = new ClientTemplate(factory, handler,
            new BuilderCorrelationInterceptor("http://allowed-only"));
        mismatchServer = MockRestServiceServer.bindTo(restTemplateOf(mismatchedClientTemplate)).build();
    }

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    private void fullMdc() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
    }

    /** ClientTemplate 内的 RestTemplate 不可直接取——通过反射获取以绑定 MockRestServiceServer。 */
    private static org.springframework.web.client.RestTemplate restTemplateOf(ClientTemplate ct) {
        try {
            java.lang.reflect.Field f = ClientTemplate.class.getDeclaredField("restTemplate");
            f.setAccessible(true);
            return (org.springframework.web.client.RestTemplate) f.get(ct);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    void builderCall_injectsTwoHeaders_executionAbsent_forgedReplaced() {
        fullMdc();
        server.expect(requestTo(BUILDER_ORIGIN + "/v1/prompt/build"))
            .andExpect(method(POST))
            .andExpect(header("X-Request-Id", "req-1"))
            .andExpect(header("TraceID", "trace-1"))
            .andRespond(withStatus(HttpStatus.OK).body("{}"));

        // 调用方伪造 execution（postForEntity 内部 token 重置 headers，故只验证注入值）
        builderClientTemplate.postForEntity(BUILDER_ORIGIN + "/v1/prompt/build",
            "token", "{}", String.class);

        server.verify();
    }

    /** 调用方传入伪造 X-Request-Id 变体 → 被先删后写为权威值。 */
    @Test
    void builderCall_forgedHeaderReplaced() {
        fullMdc();
        server.expect(requestTo(BUILDER_ORIGIN + "/v1/prompt/build"))
            .andExpect(method(POST))
            .andExpect(header("X-Request-Id", "req-1"))
            .andExpect(header("TraceID", "trace-1"))
            .andRespond(withStatus(HttpStatus.OK).body("{}"));

        org.springframework.http.HttpHeaders h = new org.springframework.http.HttpHeaders();
        h.add("x-request-id", "forged-1");
        h.add("X-REQUEST-ID", "forged-2");
        h.add("X-Execution-Id", "forged-exec");
        builderClientTemplate.postForEntity(BUILDER_ORIGIN + "/v1/prompt/build",
            h, "{}", String.class);

        server.verify();
    }

    @Test
    void originMismatch_failsWithoutRequest() {
        fullMdc();
        // mismatchServer 不期望任何请求；origin 不匹配时拦截器先于请求抛出
        assertThatThrownBy(() -> mismatchedClientTemplate.postForEntity(
            BUILDER_ORIGIN + "/v1/prompt/build", "token", "{}", String.class))
            .isInstanceOf(AgentStudioException.class);
        mismatchServer.verify();
    }

    @Test
    void missingContext_fails() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        // 无 trace
        assertThatThrownBy(() -> builderClientTemplate.postForEntity(
            BUILDER_ORIGIN + "/v1/prompt/build", "token", "{}", String.class))
            .isInstanceOf(CorrelationHeaderProvider.MissingContextException.class);
    }
}
