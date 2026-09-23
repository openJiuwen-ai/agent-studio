/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.validation.ConstraintViolationException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.validation.beanvalidation.MethodValidationPostProcessor;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

import com.openjiuwen.studio.agent.manager.controller.AgentServiceProxyController;
import com.openjiuwen.studio.agent.manager.controller.JiuwenServiceProxyController;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * COM-05 收口复审 3 §3：三个新增拒绝入口（additional-questions ×2、N2L {cid}）的完整 profile 矩阵。
 * 用 MethodValidationPostProcessor AOP 代理启用 @Validated + @Pattern，覆盖三类 profile 的
 * 合法边界、合法特殊字符、非法字符、超长值；非法用例断言 resolved exception 为
 * ConstraintViolationException、业务服务零调用、MDC 不含非法原值、响应不回显非法值。
 */
class ConversationRejectionMvcTest {

    private MockMvc agentMvc;
    private MockMvc n2lMvc;

    /** AOP 代理的 N2L Controller——供个别用例以自定义拦截器重建 MockMvc（如强制异步生命周期验证）。 */
    private JiuwenServiceProxyController n2lController;

    private com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService agentProxyService;
    private com.openjiuwen.studio.agent.manager.rce.service.JiuWenService jiuWenService;

    /** ControllerAdvice 捕获 ConstraintViolationException 时的 MDC conversation-id（验证非法值不泄漏）。 */
    private static String capturedConversationMdc;

    private static final String AQ_BODY = "{\"name\":\"test\",\"enable\":true}";
    private static final String N2L_BODY = "{\"query\":\"hello\"}";

    @BeforeEach
    void setUp() {
        LocalValidatorFactoryBean validator = new LocalValidatorFactoryBean();
        validator.afterPropertiesSet();
        MethodValidationPostProcessor processor = new MethodValidationPostProcessor();
        processor.setValidator(validator);
        processor.afterPropertiesSet();

        agentProxyService = mock(com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService.class);
        AgentServiceProxyController agentController = (AgentServiceProxyController) processor
            .postProcessAfterInitialization(
                new AgentServiceProxyController(
                    mock(com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient.class),
                    mock(com.openjiuwen.studio.agent.common.redis.RedisClient.class),
                    mock(com.openjiuwen.studio.agent.manager.mapper.AgentMapper.class),
                    mock(com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper.class),
                    agentProxyService,
                    mock(com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService.class),
                    mock(com.openjiuwen.studio.agent.manager.mapper.AppMapper.class),
                    mock(com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService.class),
                    mock(com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper.class),
                    mock(com.openjiuwen.studio.agent.manager.service.WorkflowRuntimeService.class),
                    mock(com.openjiuwen.studio.agent.manager.service.AgentRuntimeService.class)),
                "agentController");
        org.springframework.test.util.ReflectionTestUtils.setField(agentController, "runtimeEndpoint", "http://rt");
        agentMvc = MockMvcBuilders.standaloneSetup(agentController)
            .addFilters(new CorrelationContextFilter())
            .addInterceptors(new ConversationContextInterceptor())
            .setControllerAdvice(new ConstraintViolationAdvice())
            .build();

        jiuWenService = mock(com.openjiuwen.studio.agent.manager.rce.service.JiuWenService.class);
        n2lController = (JiuwenServiceProxyController) processor
            .postProcessAfterInitialization(new JiuwenServiceProxyController(
                jiuWenService,
                mock(com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager.class),
                mock(com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper.class),
                mock(com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl.class),
                mock(com.openjiuwen.studio.agent.manager.service.plugin.PluginService.class),
                mock(com.openjiuwen.studio.agent.manager.service.WorkflowManagementService.class),
                mock(com.openjiuwen.studio.agent.manager.service.JiuwenRuntimeI18nService.class)),
                "n2lController");
        n2lMvc = MockMvcBuilders.standaloneSetup(n2lController)
            .addFilters(new CorrelationContextFilter())
            .addInterceptors(new ConversationContextInterceptor())
            .setControllerAdvice(new ConstraintViolationAdvice())
            .build();
    }

    @AfterEach
    void clearMdc() {
        org.slf4j.MDC.clear();
        capturedConversationMdc = null;
    }

    // ---- Agent additional-questions（STANDARD profile: [A-Za-z0-9_-] 1~64）----

    /** 合法值进入业务方法，业务服务收到路径原值，组合链中 conversation MDC = 路径值（§4.2.4）。 */
    @Test
    void agent_legal_entersBusinessAndReceivesPathValue() throws Exception {
        final String[] capturedConversationMdc = {null};
        doAnswer(inv -> {
            capturedConversationMdc[0] = org.slf4j.MDC.get(MdcKeys.CONVERSATION_ID);
            return ResponseEntity.ok(new AutoAddResultJsonObject());
        }).when(agentProxyService).additionalQuestions(anyString(), anyString(), anyString(), anyString(), any());

        agentMvc.perform(post("/v1/p1/agent-manager/agents/a1/conversations/conv-1/additional-questions")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isOk());

        verify(agentProxyService).additionalQuestions(eq("p1"), eq("a1"), eq("conv-1"), eq("ws1"), any());
        // §4.2.4 有效会话作用域：Interceptor 在组合链中安装了 conversation scope，Controller 内 MDC = 路径值
        assertThat(capturedConversationMdc[0]).isEqualTo("conv-1");
    }

    /** 64 字符最大长度合法边界。 */
    @Test
    void agent_maxLength64_passes() throws Exception {
        String conv = "a".repeat(64);
        when(agentProxyService.additionalQuestions(anyString(), anyString(), anyString(), anyString(), any()))
            .thenReturn(ResponseEntity.ok(new AutoAddResultJsonObject()));

        agentMvc.perform(post("/v1/p1/agent-manager/agents/a1/conversations/" + conv + "/additional-questions")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isOk());
        verify(agentProxyService).additionalQuestions(eq("p1"), eq("a1"), eq(conv), eq("ws1"), any());
    }

    /** 点号被 @Pattern 拒绝——resolved exception 为 ConstraintViolationException，业务零调用，MDC 不含非法值。 */
    @Test
    void agent_dot_rejectedWithConstraintViolation() throws Exception {
        agentMvc.perform(post("/v1/p1/agent-manager/agents/a1/conversations/bad.value/additional-questions")
                .queryParam("workspace_id", "ws1")
                .header("X-Request-Id", "req-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isBadRequest())
            .andExpect(result -> assertThat(result.getResolvedException())
                .isInstanceOf(ConstraintViolationException.class))
            .andExpect(header().string("X-Request-Id", "req-1"));
        verifyNoInteractions(agentProxyService);
        assertThat(capturedConversationMdc).isEmpty();
    }

    /** 65 字符超长被 @Size 拒绝。 */
    @Test
    void agent_overLength65_rejectedWithConstraintViolation() throws Exception {
        agentMvc.perform(post("/v1/p1/agent-manager/agents/a1/conversations/" + "a".repeat(65) + "/additional-questions")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isBadRequest())
            .andExpect(result -> assertThat(result.getResolvedException())
                .isInstanceOf(ConstraintViolationException.class));
        verifyNoInteractions(agentProxyService);
    }

    // ---- Workflow additional-questions（WORKFLOW profile: [A-Za-z0-9_()-] 1~64）----

    /** 括号合法——WORKFLOW profile 允许括号，业务内 MDC conversation = 路径值 + 业务服务收到原始 ID。 */
    @Test
    void workflow_parens_legalEntersBusiness() throws Exception {
        final String[] capturedConversationMdc = {null};
        doAnswer(inv -> {
            capturedConversationMdc[0] = org.slf4j.MDC.get(MdcKeys.CONVERSATION_ID);
            return ResponseEntity.ok(new AutoAddResultJsonObject());
        }).when(agentProxyService).additionalQuestionsWorkflow(anyString(), anyString(), anyString(), anyString(), any());

        agentMvc.perform(post("/v1/p1/agent-manager/workflows/wf1/conversations/a(b)c/additional-questions")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isOk());
        verify(agentProxyService).additionalQuestionsWorkflow(eq("p1"), eq("wf1"), eq("a(b)c"), eq("ws1"), any());
        assertThat(capturedConversationMdc[0]).isEqualTo("a(b)c");
    }

    /** 64 字符最大长度合法边界。 */
    @Test
    void workflow_maxLength64_passes() throws Exception {
        String conv = "a".repeat(64);
        when(agentProxyService.additionalQuestionsWorkflow(anyString(), anyString(), anyString(), anyString(), any()))
            .thenReturn(ResponseEntity.ok(new AutoAddResultJsonObject()));

        agentMvc.perform(post("/v1/p1/agent-manager/workflows/wf1/conversations/" + conv + "/additional-questions")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isOk());
        verify(agentProxyService).additionalQuestionsWorkflow(eq("p1"), eq("wf1"), eq(conv), eq("ws1"), any());
    }

    /** 点号被拒绝（WORKFLOW 允许括号但不允许点号）。 */
    @Test
    void workflow_dot_rejectedWithConstraintViolation() throws Exception {
        agentMvc.perform(post("/v1/p1/agent-manager/workflows/wf1/conversations/bad.value/additional-questions")
                .queryParam("workspace_id", "ws1")
                .header("X-Request-Id", "req-wf")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isBadRequest())
            .andExpect(result -> assertThat(result.getResolvedException())
                .isInstanceOf(ConstraintViolationException.class))
            .andExpect(header().string("X-Request-Id", "req-wf"));
        verifyNoInteractions(agentProxyService);
        assertThat(capturedConversationMdc).isEmpty();
    }

    /** 65 字符超长被拒绝。 */
    @Test
    void workflow_overLength65_rejected() throws Exception {
        agentMvc.perform(post("/v1/p1/agent-manager/workflows/wf1/conversations/" + "a".repeat(65)
                + "/additional-questions")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(AQ_BODY))
            .andExpect(status().isBadRequest())
            .andExpect(result -> assertThat(result.getResolvedException())
                .isInstanceOf(ConstraintViolationException.class));
        verifyNoInteractions(agentProxyService);
    }

    // ---- N2L {cid}（N2L profile: [A-Za-z0-9._:-] 1~128）----

    /** 点号、冒号合法——N2L profile 允许，完整异步链 + conversation MDC = cid + 双 Header 复用。 */
    @Test
    void n2l_dotColon_legalAsyncChainWithConversationMdc() throws Exception {
        final String[] capturedConversationMdc = {null};
        try (var mr = org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.RequestContextUtils.class);
             var mrh = org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils.class)) {
            mr.when(com.openjiuwen.studio.agent.common.utils.RequestContextUtils::getRequestAuthToken)
                .thenReturn("token");
            mrh.when(com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils::getRequestLanguage)
                .thenReturn("en");
            doAnswer(inv -> {
                capturedConversationMdc[0] = org.slf4j.MDC.get(MdcKeys.CONVERSATION_ID);
                return reactor.core.publisher.Flux.empty();
            }).when(jiuWenService).generatorAgentOrWorkflow(anyString(), anyString(), anyString(), anyString(),
                anyString(), any());

            org.springframework.test.web.servlet.MvcResult result = n2lMvc.perform(
                    post("/v1/p1/agent/generator/conversations/a.b:c-d/chat")
                        .queryParam("workspace_id", "ws1")
                        .header("X-Request-Id", "req-n2l")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(N2L_BODY))
                .andExpect(header().string("X-Request-Id", "req-n2l"))
                .andReturn();

            // 如果进入异步，完成 ASYNC 派发；如果已同步完成，直接验证最终响应
            if (result.getRequest().isAsyncStarted()) {
                n2lMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                        .asyncDispatch(result))
                    .andExpect(header().string("X-Request-Id", "req-n2l"))
                    .andExpect(header().string("TraceID", "req-n2l"));
            }

            org.mockito.ArgumentCaptor<String> cidCaptor = org.mockito.ArgumentCaptor.forClass(String.class);
            verify(jiuWenService).generatorAgentOrWorkflow(eq("token"), eq("p1"), eq("agent"), cidCaptor.capture(),
                eq("ws1"), any());
            assertThat(cidCaptor.getValue()).isEqualTo("a.b:c-d");
            // 业务执行期间 conversation MDC = 路径值（组合链中有效会话 scope）
            assertThat(capturedConversationMdc[0]).isEqualTo("a.b:c-d");
            // 异步/同步完成后调用线程 MDC 恢复
            assertThat(org.slf4j.MDC.get(MdcKeys.REQUEST_ID)).isNull();
        }
    }

    /** 128 字符最大长度合法边界——业务服务收到路径原值。 */
    @Test
    void n2l_maxLength128_legalEntersBusiness() throws Exception {
        String cid = "a".repeat(128);
        try (var mr = org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.RequestContextUtils.class);
             var mrh = org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils.class)) {
            mr.when(com.openjiuwen.studio.agent.common.utils.RequestContextUtils::getRequestAuthToken)
                .thenReturn("token");
            mrh.when(com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils::getRequestLanguage)
                .thenReturn("en");
            when(jiuWenService.generatorAgentOrWorkflow(anyString(), anyString(), anyString(), anyString(),
                anyString(), any())).thenReturn(reactor.core.publisher.Flux.empty());

            n2lMvc.perform(post("/v1/p1/agent/generator/conversations/" + cid + "/chat")
                    .queryParam("workspace_id", "ws1")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(N2L_BODY));

            org.mockito.ArgumentCaptor<String> cidCaptor = org.mockito.ArgumentCaptor.forClass(String.class);
            verify(jiuWenService).generatorAgentOrWorkflow(eq("token"), eq("p1"), eq("agent"), cidCaptor.capture(),
                eq("ws1"), any());
            assertThat(cidCaptor.getValue()).isEqualTo(cid);
        }
    }

    /**
     * 验收缺口补齐（§15.3.4/§15.5）：SseEmitter 真实链生命周期——强制进入异步 + 断言
     * afterConcurrentHandlingStarted 在原 Servlet 线程关闭 conversation scope。
     *
     * <p>用 delaySubscription 延迟 Flux 保证 SseEmitter 在 Controller 返回时尚未完成
     * → MockMvc 必然检测 asyncStarted；spy 拦截器在 afterConcurrentHandlingStarted 内
     * （super 调用后）捕获 MDC——此刻内层 conversation scope 已关闭（回到外层空值），
     * 而外层 Filter 的 request scope 仍未退出（request-id 仍可见），证明按所有权分层恢复。
     */
    @Test
    void n2l_sseEmitter_forcedAsyncStarted_conversationScopeClosedOnServletThread() throws Exception {
        final String[] conversationAfterAsyncStart = {null};
        final String[] requestAfterAsyncStart = {null};
        ConversationContextInterceptor spyInterceptor = new ConversationContextInterceptor() {
            @Override
            public void afterConcurrentHandlingStarted(jakarta.servlet.http.HttpServletRequest req,
                jakarta.servlet.http.HttpServletResponse res, Object handler) {
                super.afterConcurrentHandlingStarted(req, res, handler);
                conversationAfterAsyncStart[0] = org.slf4j.MDC.get(MdcKeys.CONVERSATION_ID);
                requestAfterAsyncStart[0] = org.slf4j.MDC.get(MdcKeys.REQUEST_ID);
            }
        };
        MockMvc sseMvc = MockMvcBuilders.standaloneSetup(n2lController)
            .addFilters(new CorrelationContextFilter())
            .addInterceptors(spyInterceptor)
            .setControllerAdvice(new ConstraintViolationAdvice())
            .build();

        try (var mr = org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.RequestContextUtils.class);
             var mrh = org.mockito.Mockito.mockStatic(com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils.class)) {
            mr.when(com.openjiuwen.studio.agent.common.utils.RequestContextUtils::getRequestAuthToken)
                .thenReturn("token");
            mrh.when(com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils::getRequestLanguage)
                .thenReturn("en");
            // 延迟订阅 + 空流：SseEmitter 在 Controller 返回时未完成 → 必然进入异步；
            // ~100ms 后异步完成（无 data 事件，避免跨线程 send）
            when(jiuWenService.generatorAgentOrWorkflow(anyString(), anyString(), anyString(), anyString(),
                anyString(), any()))
                    .thenReturn(reactor.core.publisher.Flux.<java.util.Map<String, Object>>empty()
                        .delaySubscription(java.time.Duration.ofMillis(100)));

            org.springframework.test.web.servlet.MvcResult result = sseMvc.perform(
                    post("/v1/p1/agent/generator/conversations/conv-sse-1/chat")
                        .queryParam("workspace_id", "ws1")
                        .header("X-Request-Id", "req-sse")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(N2L_BODY))
                .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.request()
                    .asyncStarted())
                .andExpect(header().string("X-Request-Id", "req-sse"))
                .andReturn();

            // 第一次派发返回（异步已启动）：afterConcurrentHandlingStarted 已在原 Servlet 线程
            // 关闭 conversation scope（回到外层空值），而外层 Filter request scope 此刻仍未退出
            assertThat(conversationAfterAsyncStart[0]).isEmpty();
            assertThat(requestAfterAsyncStart[0]).isEqualTo("req-sse");

            // 完成 ASYNC 派发：最终响应复用首次选定的关联值，不生成第二组 ID
            sseMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
                    .asyncDispatch(result))
                .andExpect(header().string("X-Request-Id", "req-sse"))
                .andExpect(header().string("TraceID", "req-sse"));

            // 异步完成后调用线程 MDC 完整恢复（外层 Filter scope 已关闭）
            assertThat(org.slf4j.MDC.get(MdcKeys.REQUEST_ID)).isNull();
            assertThat(org.slf4j.MDC.get(MdcKeys.CONVERSATION_ID)).isNull();
        }
    }

    /** 括号被拒绝——N2L profile 不允许括号。 */
    @Test
    void n2l_parens_rejectedWithConstraintViolation() throws Exception {
        n2lMvc.perform(post("/v1/p1/agent/generator/conversations/a(b)c/chat")
                .queryParam("workspace_id", "ws1")
                .header("X-Request-Id", "req-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(N2L_BODY))
            .andExpect(status().isBadRequest())
            .andExpect(result -> assertThat(result.getResolvedException())
                .isInstanceOf(ConstraintViolationException.class))
            .andExpect(header().string("X-Request-Id", "req-1"));
        verifyNoInteractions(jiuWenService);
        assertThat(capturedConversationMdc).isEmpty();
    }

    /** 129 字符超长被拒绝。 */
    @Test
    void n2l_overLength129_rejectedWithConstraintViolation() throws Exception {
        n2lMvc.perform(post("/v1/p1/agent/generator/conversations/" + "a".repeat(129) + "/chat")
                .queryParam("workspace_id", "ws1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(N2L_BODY))
            .andExpect(status().isBadRequest())
            .andExpect(result -> assertThat(result.getResolvedException())
                .isInstanceOf(ConstraintViolationException.class));
        verifyNoInteractions(jiuWenService);
    }

    @ControllerAdvice
    static class ConstraintViolationAdvice {
        @ExceptionHandler(ConstraintViolationException.class)
        public ResponseEntity<String> handle(ConstraintViolationException e) {
            capturedConversationMdc = org.slf4j.MDC.get(MdcKeys.CONVERSATION_ID);
            return ResponseEntity.badRequest().body("validation error");
        }
    }
}
