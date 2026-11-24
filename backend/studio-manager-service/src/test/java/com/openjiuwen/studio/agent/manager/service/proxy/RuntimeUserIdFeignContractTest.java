/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ServiceWorkflowRunReq;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.client.CustomerHeaderFeignInterceptor;

import feign.RequestTemplate;
import feign.Target;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;

import java.util.Collection;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 契约：非流式 Feign 必须显式携带 cust-userid；CustomerHeader 拦截器在
 * profile 默认关闭时不会透传 ThreadLocal。
 */
@ExtendWith(MockitoExtension.class)
class RuntimeUserIdFeignContractTest {

    @Mock
    private AgentRuntimeClient runtimeClient;

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    @Test
    void nonStreamWorkflowFeign_receivesExplicitCustUserId() {
        when(runtimeClient.runWorkflowWithConversation(any(), any(), any(), any(), any(), any(), any(), any(), any(),
            any(), any())).thenReturn(ResponseEntity.ok().build());

        try (MockedStatic<RequestContextUtils> mocked = org.mockito.Mockito.mockStatic(RequestContextUtils.class)) {
            SimpleUser user = new SimpleUser();
            user.setUserId("login-feign-uid");
            mocked.when(RequestContextUtils::getRequestIamCtxOptional).thenReturn(Optional.of(user));
            mocked.when(RequestContextUtils::getRequestAuthToken).thenReturn("login-feign-uid|0");

            HttpHeaders headers = new HttpHeaders();
            ServiceWorkflowRunReq body = new ServiceWorkflowRunReq();
            RuntimeUserIdPropagator.applyLoginUser(headers, body::setUserId);

            runtimeClient.runWorkflowWithConversation(
                RequestContextUtils.getRequestAuthToken(),
                RuntimeUserIdPropagator.custUserIdHeaderValue(),
                "p0", "wf0", "c0", "ws0", "env0", null, body, null, null);

            ArgumentCaptor<String> custCaptor = ArgumentCaptor.forClass(String.class);
            verify(runtimeClient).runWorkflowWithConversation(
                eq("login-feign-uid|0"), custCaptor.capture(),
                eq("p0"), eq("wf0"), eq("c0"), eq("ws0"), eq("env0"), isNull(), eq(body),
                isNull(), isNull());
            assertThat(custCaptor.getValue()).isEqualTo("login-feign-uid");
            assertThat(body.getUserId()).isEqualTo("login-feign-uid");
            assertThat(headers.getFirst(CommonConstant.CustomModel.CUSTOM_USER_ID)).isEqualTo("login-feign-uid");
        }
    }

    @Test
    void nonStreamAgentFeign_receivesExplicitCustUserId() {
        when(runtimeClient.runAgentWithConversation(any(), any(), any(), any(), any(), any(), any(), any(), any(),
            any(), any(), any(), any(), any())).thenReturn(ResponseEntity.ok().build());

        try (MockedStatic<RequestContextUtils> mocked = org.mockito.Mockito.mockStatic(RequestContextUtils.class)) {
            SimpleUser user = new SimpleUser();
            user.setUserId("agent-uid");
            mocked.when(RequestContextUtils::getRequestIamCtxOptional).thenReturn(Optional.of(user));
            mocked.when(RequestContextUtils::getRequestAuthToken).thenReturn("agent-uid|0");

            runtimeClient.runAgentWithConversation(
                RequestContextUtils.getRequestAuthToken(), null,
                RuntimeUserIdPropagator.custUserIdHeaderValue(),
                "p0", "a0", "c0", "ws0", "agent", null, null, null, Map.of(), null, null);

            ArgumentCaptor<String> custCaptor = ArgumentCaptor.forClass(String.class);
            verify(runtimeClient).runAgentWithConversation(
                eq("agent-uid|0"), isNull(), custCaptor.capture(),
                eq("p0"), eq("a0"), eq("c0"), eq("ws0"), eq("agent"), isNull(), isNull(), isNull(), any(),
                isNull(), isNull());
            assertThat(custCaptor.getValue()).isEqualTo("agent-uid");
        }
    }

    @Test
    void customerHeaderInterceptor_skipsWhenProfileDisabled_evenIfThreadLocalHasCustUserid() {
        // 模拟评审指出的默认配置：ThreadLocal 有值但 profile=false → 拦截器不写 header
        RequestTemplate template = new RequestTemplate();
        Target<?> target = mock(Target.class);
        when(target.name()).thenReturn("agentRuntime");
        template.feignTarget(target);

        try (MockedStatic<RequestContextUtils> mocked = org.mockito.Mockito.mockStatic(RequestContextUtils.class);
             MockedStatic<com.openjiuwen.studio.agent.common.utils.SpringBeanUtils> spring =
                 org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.SpringBeanUtils.class)) {
            mocked.when(RequestContextUtils::getCustomerHeaders)
                .thenReturn(Map.of("cust-userid", "stale-from-threadlocal"));
            com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile profile =
                mock(com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile.class);
            when(profile.isEnabled()).thenReturn(false);
            spring.when(() -> com.openjiuwen.studio.agent.common.utils.SpringBeanUtils.getBean(
                    com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile.class))
                .thenReturn(profile);

            new CustomerHeaderFeignInterceptor().apply(template);

            Map<String, Collection<String>> headers = template.headers();
            assertThat(headers == null || !headers.containsKey("cust-userid")
                && !headers.containsKey("CUST-USERID")).isTrue();
        }
    }
}
