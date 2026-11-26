/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.ServiceWorkflowRunReq;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.observability.MdcScope;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.client.CustomerHeaderFeignInterceptor;
import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;
import com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService;
import com.openjiuwen.studio.agent.manager.service.WorkflowRuntimeService;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.controller.AgentServiceProxyController;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;

import feign.RequestTemplate;
import feign.Target;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collection;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 评审要求：stream=true/false × CUSTOMER_HEADER profile 开/关，共四组合。
 *
 * <p>断言：无论 profile 是否开启，试运行出站都必须带上登录用户 {@code cust-userid}
 * （流式靠 OkHttp headers，非流式靠 Feign 显式 {@code @RequestHeader}）；
 * profile 仅影响旧 ThreadLocal 拦截器，不再作为本修复的依赖。
 */
@ExtendWith(MockitoExtension.class)
class RuntimeUserIdStreamProfileMatrixTest {

    private static final String LOGIN_UID = "matrix-login-uid";

    @Mock
    private AgentRuntimeClient runtimeClient;
    @Mock
    private RedisClient redisClient;
    @Mock
    private AgentMapper agentMapper;
    @Mock
    private WorkflowMapper workflowMapper;
    @Mock
    private AgentServiceProxyService agentServiceProxyService;
    @Mock
    private ShareResourceManagerService shareResourceManagerService;
    @Mock
    private AppMapper appMapper;
    @Mock
    private AssetFreeTrialMgmtService assetFreeTrialMgmtService;
    @Mock
    private ReleaseVersionMapper releaseVersionMapper;
    @Mock
    private WorkflowRuntimeService workflowRuntimeService;
    @Mock
    private AgentRuntimeService agentRuntimeService;

    private AgentServiceProxyController controller;

    @BeforeEach
    void setUp() {
        controller = new AgentServiceProxyController(runtimeClient, redisClient, agentMapper, workflowMapper,
            agentServiceProxyService, shareResourceManagerService, appMapper, assetFreeTrialMgmtService,
            releaseVersionMapper, workflowRuntimeService, agentRuntimeService);
        ReflectionTestUtils.setField(controller, "runtimeEndpoint", "http://runtime:8080");

        WorkflowEntity wf = new WorkflowEntity();
        wf.setProjectId("p0");
        wf.setWorkspaceId("ws0");
        lenient().when(workflowMapper.getWorkflowById("wf0")).thenReturn(wf);
        lenient().when(shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(anyString(), anyString()))
            .thenReturn(false);
        lenient().when(agentServiceProxyService.resolveEnvironmentId(eq("p0"), any())).thenAnswer(inv -> inv.getArgument(1));
    }

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    @ParameterizedTest(name = "stream={0}, customerHeaderEnabled={1}")
    @CsvSource({
        "true, false",
        "true, true",
        "false, false",
        "false, true"
    })
    void workflowTrialRun_propagatesLoginCustUserid_forAllStreamAndProfileCombos(boolean stream,
        boolean customerHeaderEnabled) {
        try (MockedStatic<RequestContextUtils> mocked = org.mockito.Mockito.mockStatic(RequestContextUtils.class);
             MockedStatic<SpringBeanUtils> spring = org.mockito.Mockito.mockStatic(SpringBeanUtils.class)) {
            SimpleUser loginUser = new SimpleUser();
            loginUser.setUserId(LOGIN_UID);
            mocked.when(RequestContextUtils::getRequestIamCtxOptional).thenReturn(Optional.of(loginUser));
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn(LOGIN_UID);
            mocked.when(RequestContextUtils::getRequestAuthToken).thenReturn(LOGIN_UID + "|0");
            // propagator 不再读写 ThreadLocal；即使 profile 开着也不依赖
            mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(Map.of());

            // profile 开/关下拦截器行为：本修复不依赖它，但四组合仍要可观测
            assertInterceptorRespectsProfile(customerHeaderEnabled, spring, mocked);

            HttpHeaders inbound = new HttpHeaders();
            // 画布试运行：仅 debug 才注入登录 cust-userid
            inbound.set(Constant.Agent.INVOKE_HEADER_KEY, Constant.Common.INVOKE_MOD_DEBUG);
            ServiceWorkflowRunReq body = new ServiceWorkflowRunReq();

            if (stream) {
                when(agentServiceProxyService.workflowStream(anyString(), any(HttpHeaders.class), anyString(),
                    any(WorkflowRunResult.class), any(ExecuteParams.class))).thenReturn("stream-ok");

                Object result = controller.runWorkflowWithConversation("p0", "ws0", null, "wf0", "c0", null, true,
                    body, inbound);

                assertThat(result).isEqualTo("stream-ok");
                ArgumentCaptor<HttpHeaders> headersCaptor = ArgumentCaptor.forClass(HttpHeaders.class);
                verify(agentServiceProxyService).workflowStream(anyString(), headersCaptor.capture(), anyString(),
                    any(WorkflowRunResult.class), any(ExecuteParams.class));
                assertThat(headersCaptor.getValue().getFirst(CommonConstant.CustomModel.CUSTOM_USER_ID))
                    .isEqualTo(LOGIN_UID);
                assertThat(body.getUserId()).isEqualTo(LOGIN_UID);
            } else {
                MdcScope scope = mock(MdcScope.class);
                when(agentServiceProxyService.establishExecutionScope(any(HttpHeaders.class))).thenReturn(scope);
                when(runtimeClient.runWorkflowWithConversation(any(), any(), any(), any(), any(), any(), any(), any(),
                    any(), any(), any())).thenReturn(ResponseEntity.ok("feign-ok"));

                Object result = controller.runWorkflowWithConversation("p0", "ws0", "env0", "wf0", "c0", null, false,
                    body, inbound);

                // 非流式经 relayUpstreamOtelHeaders 透传上游状态码/OTel 头，返回 ResponseEntity
                assertThat(result).isInstanceOf(ResponseEntity.class);
                assertThat(((ResponseEntity<?>) result).getBody()).isEqualTo("feign-ok");
                ArgumentCaptor<String> custCaptor = ArgumentCaptor.forClass(String.class);
                verify(runtimeClient).runWorkflowWithConversation(
                    eq(LOGIN_UID + "|0"), custCaptor.capture(),
                    eq("p0"), eq("wf0"), eq("c0"), eq("ws0"), eq("env0"), isNull(), eq(body),
                    eq(Boolean.FALSE), eq(Constant.Common.INVOKE_MOD_DEBUG));
                assertThat(custCaptor.getValue()).isEqualTo(LOGIN_UID);
                assertThat(body.getUserId()).isEqualTo(LOGIN_UID);
                // 入站 headers 同样被写入（与流式一致），供可观测/后续扩展
                assertThat(inbound.getFirst(CommonConstant.CustomModel.CUSTOM_USER_ID)).isEqualTo(LOGIN_UID);
            }
        }
    }

    @org.junit.jupiter.api.Test
    void publishedInvoke_doesNotOverrideCustUseridEvenWithLoginContext() {
        try (MockedStatic<RequestContextUtils> mocked = org.mockito.Mockito.mockStatic(RequestContextUtils.class)) {
            SimpleUser loginUser = new SimpleUser();
            loginUser.setUserId(LOGIN_UID);
            mocked.when(RequestContextUtils::getRequestIamCtxOptional).thenReturn(Optional.of(loginUser));
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn(LOGIN_UID);
            mocked.when(RequestContextUtils::getRequestAuthToken).thenReturn(LOGIN_UID + "|0");

            HttpHeaders inbound = new HttpHeaders();
            inbound.set(Constant.Agent.INVOKE_HEADER_KEY, "PUBLISHED");
            inbound.set(CommonConstant.CustomModel.CUSTOM_USER_ID, "client-forged");
            ServiceWorkflowRunReq body = new ServiceWorkflowRunReq();

            MdcScope scope = mock(MdcScope.class);
            when(agentServiceProxyService.establishExecutionScope(any(HttpHeaders.class))).thenReturn(scope);
            when(runtimeClient.runWorkflowWithConversation(any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any())).thenReturn(ResponseEntity.ok("feign-ok"));

            controller.runWorkflowWithConversation("p0", "ws0", "env0", "wf0", "c0", null, false, body, inbound);

            ArgumentCaptor<String> custCaptor = ArgumentCaptor.forClass(String.class);
            verify(runtimeClient).runWorkflowWithConversation(
                eq(LOGIN_UID + "|0"), custCaptor.capture(),
                eq("p0"), eq("wf0"), eq("c0"), eq("ws0"), eq("env0"), isNull(), eq(body),
                eq(Boolean.FALSE), eq("PUBLISHED"));
            assertThat(custCaptor.getValue()).isNull();
            assertThat(body.getUserId()).isNull();
            // 不得用登录用户覆盖客户端伪造/静态值
            assertThat(inbound.getFirst(CommonConstant.CustomModel.CUSTOM_USER_ID)).isEqualTo("client-forged");
        }
    }

    /**
     * profile=false：ThreadLocal 有值也不透传；profile=true：会透传（旧路径能力仍在，
     * 但本修复的试运行出站不依赖这条路径）。
     */
    private void assertInterceptorRespectsProfile(boolean enabled, MockedStatic<SpringBeanUtils> spring,
        MockedStatic<RequestContextUtils> mocked) {
        RequestTemplate template = new RequestTemplate();
        Target<?> target = mock(Target.class);
        when(target.name()).thenReturn("agentRuntime");
        template.feignTarget(target);

        mocked.when(RequestContextUtils::getCustomerHeaders)
            .thenReturn(Map.of("cust-userid", "from-threadlocal-only"));

        CustomerHeaderProfile profile = mock(CustomerHeaderProfile.class);
        when(profile.isEnabled()).thenReturn(enabled);
        spring.when(() -> SpringBeanUtils.getBean(CustomerHeaderProfile.class)).thenReturn(profile);

        new CustomerHeaderFeignInterceptor().apply(template);

        Map<String, Collection<String>> headers = template.headers();
        boolean hasCust = headers != null && (headers.containsKey("cust-userid") || headers.containsKey("CUST-USERID")
            || headers.keySet().stream().anyMatch(k -> k != null && k.equalsIgnoreCase("cust-userid")));
        if (enabled) {
            assertThat(hasCust).as("profile=true 时拦截器应透传 ThreadLocal cust-userid").isTrue();
        } else {
            assertThat(hasCust).as("profile=false 时拦截器不得透传 ThreadLocal").isFalse();
        }

        // 恢复矩阵主路径用的空 ThreadLocal 语义
        mocked.when(RequestContextUtils::getCustomerHeaders).thenReturn(Map.of());
    }
}
