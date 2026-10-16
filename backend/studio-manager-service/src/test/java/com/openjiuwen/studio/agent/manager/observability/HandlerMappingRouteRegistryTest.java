/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockServletContext;
import org.springframework.web.context.support.GenericWebApplicationContext;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.mvc.method.RequestMappingInfo;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

import com.openjiuwen.studio.agent.manager.controller.AgentServiceProxyController;
import com.openjiuwen.studio.agent.manager.controller.ConversationHistoryApiController;
import com.openjiuwen.studio.agent.manager.controller.JiuwenServiceProxyController;
import com.openjiuwen.studio.agent.manager.controller.WorkflowRuntimeApiController;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * COM-05 审视 T2：使用实际 {@link RequestMappingHandlerMapping} 对账会话路由。
 * 用 GenericWebApplicationContext 注册 4 个有会话路由的业务 Controller + 真实
 * RequestMappingHandlerMapping，从 {@code getHandlerMethods()} 读取 Spring 实际注册
 * 的路由，验证所有含 {@code {conversation_id}} 或 {@code {cid}} 的路由均绑定 profile。
 * 与 {@link ConversationRouteRegistryTest}（classpath 扫描）互补。
 */
class HandlerMappingRouteRegistryTest {

    /** 从真实 RequestMappingHandlerMapping 读路由，与 ConversationIdValidator 注册表双向对账。 */
    @Test
    void allConversationRoutesInHandlerMappingHaveProfile() throws Exception {
        GenericWebApplicationContext ctx = new GenericWebApplicationContext(new MockServletContext());

        // 注册有会话路由的 4 个业务 Controller（mock 依赖——HandlerMapping 只读注解，不调方法）
        ctx.registerBean(AgentServiceProxyController.class, () -> newAgentServiceProxyController());
        ctx.registerBean(JiuwenServiceProxyController.class, () -> newJiuwenServiceProxyController());
        ctx.registerBean(ConversationHistoryApiController.class,
            ConversationHistoryApiController::new);
        ctx.registerBean(WorkflowRuntimeApiController.class,
            WorkflowRuntimeApiController::new);

        // 注册真实 RequestMappingHandlerMapping（setApplicationContext 在 refresh 时自动）
        ctx.registerBean(RequestMappingHandlerMapping.class, RequestMappingHandlerMapping::new);
        ctx.refresh();

        RequestMappingHandlerMapping hm = ctx.getBean(RequestMappingHandlerMapping.class);
        Map<RequestMappingInfo, HandlerMethod> methods = hm.getHandlerMethods();

        Set<String> conversationRoutes = new HashSet<>();
        for (RequestMappingInfo info : methods.keySet()) {
            String pattern = info.getPatternValues().iterator().hasNext()
                ? info.getPatternValues().iterator().next() : "";
            if (pattern.contains("{conversation_id}") || pattern.contains("{cid}")) {
                conversationRoutes.add(pattern);
            }
        }

        // 真实 HandlerMapping 注册的会话路由必须全部在 profile 注册表中（防遗漏）
        // 注册表不得有实际 MVC 未注册的陈旧项（防漂移）
        // 18 条唯一 pattern（17 conversation_id + 1 N2L cid）
        Set<String> registered = ConversationIdValidator.registeredPatterns();
        assertThat(conversationRoutes).isNotEmpty();
        assertThat(conversationRoutes).hasSize(18);
        assertThat(conversationRoutes).containsExactlyInAnyOrderElementsOf(registered);

        // 清理
        ctx.close();
    }

    private AgentServiceProxyController newAgentServiceProxyController() {
        return new AgentServiceProxyController(
            mock(com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient.class),
            mock(com.openjiuwen.studio.agent.common.redis.RedisClient.class),
            mock(com.openjiuwen.studio.agent.manager.mapper.AgentMapper.class),
            mock(com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper.class),
            mock(com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService.class),
            mock(com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService.class),
            mock(com.openjiuwen.studio.agent.manager.mapper.AppMapper.class),
            mock(com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService.class),
            mock(com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper.class),
            mock(com.openjiuwen.studio.agent.manager.service.WorkflowRuntimeService.class),
            mock(com.openjiuwen.studio.agent.manager.service.AgentRuntimeService.class));
    }

    private JiuwenServiceProxyController newJiuwenServiceProxyController() {
        return new JiuwenServiceProxyController(
            mock(com.openjiuwen.studio.agent.manager.rce.service.JiuWenService.class),
            mock(com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager.class),
            mock(com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper.class),
            mock(com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl.class),
            mock(com.openjiuwen.studio.agent.manager.service.plugin.PluginService.class),
            mock(com.openjiuwen.studio.agent.manager.service.WorkflowManagementService.class),
            mock(com.openjiuwen.studio.agent.manager.service.JiuwenRuntimeI18nService.class));
    }
}
