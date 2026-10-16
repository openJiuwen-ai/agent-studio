/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.util.Map;

import org.slf4j.MDC;
import org.springframework.web.servlet.AsyncHandlerInterceptor;
import org.springframework.web.servlet.HandlerMapping;

/**
 * Manager 路径会话 scope 拦截器（COM-05 §12.2）。
 *
 * <p>{@code preHandle()} 从 {@code URI_TEMPLATE_VARIABLES_ATTRIBUTE} 读取已匹配路径变量
 * （不用 URI 子串或正则猜测），按注册表 profile 校验后用
 * {@link MdcScope#open(Map)} 建立部分覆盖 scope 并保存到 request attribute。
 * 非法值不写 MDC、拦截器不自行返回错误——交由 Controller 既有
 * {@code ConstraintViolationException} 参数校验链路安全拒绝。
 *
 * <p>关闭时机：同步请求在 {@code afterCompletion()}；进入 MVC 异步处理（SseEmitter）时在
 * {@code afterConcurrentHandlingStarted()} 关闭当前 Servlet 线程 scope，避免持有期间污染
 * 容器线程。ERROR/ASYNC 再派发重新进入 MVC 时新建自己的 scope，不跨线程 close。
 * 关闭幂等：scope 消费后即从 attribute 移除，重复关闭为 no-op。
 */
public class ConversationContextInterceptor implements AsyncHandlerInterceptor {

    /** preHandle 建立的 scope 保存位置（关闭后移除，保证幂等）。 */
    public static final String SCOPE_ATTRIBUTE = ConversationContextInterceptor.class.getName() + ".SCOPE";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String pattern = (String) request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
        ConversationIdValidator.Profile profile = ConversationIdValidator.profileFor(pattern);
        if (profile == null) {
            // 未登记会话来源的路由：保持外层空 conversation-id，不猜 URL
            return true;
        }
        @SuppressWarnings("unchecked")
        Map<String, String> vars =
            (Map<String, String>) request.getAttribute(HandlerMapping.URI_TEMPLATE_VARIABLES_ATTRIBUTE);
        if (vars == null) {
            return true;
        }
        String value = vars.get(profile == ConversationIdValidator.Profile.N2L_CONVERSATION
            ? "cid" : "conversation_id");
        if (!ConversationIdValidator.isValid(profile, value)) {
            // 缺失或非法：不写 MDC、不记原值，交由 Controller 既有校验拒绝
            return true;
        }
        MdcScope scope = MdcScope.open(Map.of(MdcKeys.CONVERSATION_ID, value));
        request.setAttribute(SCOPE_ATTRIBUTE, scope);
        return true;
    }

    @Override
    public void afterConcurrentHandlingStarted(HttpServletRequest request, HttpServletResponse response,
        Object handler) {
        closeScope(request);
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler,
        Exception ex) {
        closeScope(request);
    }

    private static void closeScope(HttpServletRequest request) {
        MdcScope scope = (MdcScope) request.getAttribute(SCOPE_ATTRIBUTE);
        if (scope != null) {
            request.removeAttribute(SCOPE_ATTRIBUTE);
            scope.close();
        }
    }
}
