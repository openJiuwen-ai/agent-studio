/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.HandlerMapping;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * COM-05 §12：会话拦截器生命周期——preHandle 部分覆盖 scope、非法值不写 MDC、
 * 同步 afterCompletion 与异步 afterConcurrentHandlingStarted 关闭、幂等、ERROR/ASYNC 再派发新建。
 */
class ConversationContextInterceptorTest {

    private final ConversationContextInterceptor interceptor = new ConversationContextInterceptor();
    private final MockHttpServletResponse response = new MockHttpServletResponse();
    private final Object handler = new Object();

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    private MockHttpServletRequest conversationRequest(String pattern, Map<String, String> vars) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE, pattern);
        request.setAttribute(HandlerMapping.URI_TEMPLATE_VARIABLES_ATTRIBUTE, vars);
        return request;
    }

    @Test
    void preHandle_installsConversationScope_afterCompletionRestores() throws Exception {
        // 外层 Filter 已置空 conversation-id（模拟）
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Map.of("conversation_id", "conv-1"));

        assertThat(interceptor.preHandle(request, response, handler)).isTrue();
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("conv-1");

        interceptor.afterCompletion(request, response, handler, null);
        // 关闭后回到外层空值
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void preHandle_n2lRoute_readsCidVariable() throws Exception {
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat",
            Map.of("cid", "n2l-conv-1"));

        interceptor.preHandle(request, response, handler);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("n2l-conv-1");
        interceptor.afterCompletion(request, response, handler, null);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void preHandle_illegalValue_skipsMdcAndProceeds() throws Exception {
        // 外层空值；非法路径值不写 MDC，交由 Controller 既有参数校验拒绝
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Map.of("conversation_id", "bad value"));

        assertThat(interceptor.preHandle(request, response, handler)).isTrue();
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
        // 未建 scope 的请求 afterCompletion 不得影响 MDC
        interceptor.afterCompletion(request, response, handler, null);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void preHandle_nonConversationRoute_leavesMdcUntouched() throws Exception {
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        // 已匹配但未登记会话来源的路由：不猜 URL、不写 MDC
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/apps", Map.of("project_id", "p1"));

        assertThat(interceptor.preHandle(request, response, handler)).isTrue();
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void asyncStart_closesScopeOnServletThread_noCrossThreadClose() throws Exception {
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Map.of("conversation_id", "conv-1"));
        interceptor.preHandle(request, response, handler);

        // SseEmitter 进入异步：当前 Servlet 线程关闭 scope
        interceptor.afterConcurrentHandlingStarted(request, response, handler);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();

        // 异步结束后 afterCompletion 到达：已消费的 scope 幂等关闭，不双重恢复
        interceptor.afterCompletion(request, response, handler, null);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void doubleAfterCompletion_idempotent() throws Exception {
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Map.of("conversation_id", "conv-1"));
        interceptor.preHandle(request, response, handler);
        interceptor.afterCompletion(request, response, handler, null);
        interceptor.afterCompletion(request, response, handler, null);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void errorRedispatch_reentersMvcAndOpensFreshScope() throws Exception {
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Map.of("conversation_id", "conv-1"));

        // 第一轮派发完成
        interceptor.preHandle(request, response, handler);
        interceptor.afterCompletion(request, response, handler, null);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();

        // ERROR/ASYNC 再派发重新进入 MVC：新建并关闭自己的 scope
        interceptor.preHandle(request, response, handler);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("conv-1");
        interceptor.afterCompletion(request, response, handler, null);
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }

    @Test
    void viewThrowsScopeStillClosed_viaAfterCompletion() throws Exception {
        // ControllerAdvice 异常路径：afterCompletion 收到异常对象也关闭 scope
        MDC.put(MdcKeys.CONVERSATION_ID, "");
        MockHttpServletRequest request = conversationRequest(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Map.of("conversation_id", "conv-1"));
        interceptor.preHandle(request, response, handler);
        interceptor.afterCompletion(request, response, handler, new IllegalStateException("boom"));
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEmpty();
    }
}
