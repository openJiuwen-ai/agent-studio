/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Manager 会话 ID 校验 profile、共享编译期常量与路由映射（COM-05 §12.2）。
 *
 * <p>三类 profile 按逐路由注解审计冻结（不按 Controller 家族推断——Workflow 家族中
 * 会话列表 GET、abort、executions 用 STANDARD，只有执行/资产/网页 chat 用 WORKFLOW）：
 *
 * <ul>
 *   <li>{@code STANDARD_CONVERSATION}：{@code [A-Za-z0-9_-]}，1～64；</li>
 *   <li>{@code WORKFLOW_CONVERSATION}：{@code [A-Za-z0-9_()-]}，1～64（允许括号）；</li>
 *   <li>{@code N2L_CONVERSATION}：{@code [A-Za-z0-9._:-]}，1～128（冻结契约）。</li>
 * </ul>
 *
 * <p>共享常量同时供拦截器与 Controller {@code @Pattern} 注解使用，防止两份规则漂移；
 * 拦截器接受范围不得宽于对应 Controller 注解。非法值不写 MDC，由 Controller 既有
 * 参数校验（ConstraintViolationException 链路）安全拒绝。
 */
public final class ConversationIdValidator {

    /** 会话校验 profile。 */
    public enum Profile {
        STANDARD_CONVERSATION,
        WORKFLOW_CONVERSATION,
        N2L_CONVERSATION
    }

    /** 共享编译期常量：普通 Agent/查询类会话约束（值来自 api 模块 {@code ConversationIdPatterns}）。 */
    public static final String STANDARD_CONVERSATION_REGEXP =
        com.openjiuwen.studio.agent.manager.utils.ConversationIdPatterns.STANDARD_CONVERSATION_REGEXP;

    /** 共享编译期常量：Workflow 执行/资产/网页 chat 会话约束（允许括号）。 */
    public static final String WORKFLOW_CONVERSATION_REGEXP =
        com.openjiuwen.studio.agent.manager.utils.ConversationIdPatterns.WORKFLOW_CONVERSATION_REGEXP;

    /** 共享编译期常量：N2L {cid}（冻结契约 1～128）。 */
    public static final String N2L_CONVERSATION_REGEXP =
        com.openjiuwen.studio.agent.manager.utils.ConversationIdPatterns.N2L_CONVERSATION_REGEXP;

    private static final Pattern STANDARD = Pattern.compile(STANDARD_CONVERSATION_REGEXP);
    private static final Pattern WORKFLOW = Pattern.compile(WORKFLOW_CONVERSATION_REGEXP);
    private static final Pattern N2L = Pattern.compile(N2L_CONVERSATION_REGEXP);

    /** 已匹配路由 pattern（BEST_MATCHING_PATTERN）→ profile；由对账测试与源码保持一致。 */
    private static final Map<String, Profile> ROUTE_PROFILES;

    static {
        Map<String, Profile> routes = new HashMap<>();
        // STANDARD_CONVERSATION
        routes.put("/v1/{project_id}/agent-manager/agents-assets/{agent_id}/conversations/{conversation_id}",
            Profile.STANDARD_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
            Profile.STANDARD_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/memory-variables/reset",
            Profile.STANDARD_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/memory-variables",
            Profile.STANDARD_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/history",
            Profile.STANDARD_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/apps/{app_id}/conversions/{conversation_id}/messages"
                + "/{message_id}/feedback",
            Profile.STANDARD_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}/abort",
            Profile.STANDARD_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/controller/{agent_id}/conversations/{conversation_id}/executions",
            Profile.STANDARD_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}/executions",
            Profile.STANDARD_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/execution-queries",
            Profile.STANDARD_CONVERSATION);
        routes.put("/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/executions",
            Profile.STANDARD_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/additional-questions",
            Profile.STANDARD_CONVERSATION);
        // WORKFLOW_CONVERSATION
        routes.put(
            "/v1/{project_id}/agent-manager/workflows-assets/{workflow_id}/conversations/{conversation_id}",
            Profile.WORKFLOW_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}",
            Profile.WORKFLOW_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}"
                + "/node_execute/{node_id}",
            Profile.WORKFLOW_CONVERSATION);
        routes.put("/v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}",
            Profile.WORKFLOW_CONVERSATION);
        routes.put(
            "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}"
                + "/additional-questions",
            Profile.WORKFLOW_CONVERSATION);
        // N2L_CONVERSATION
        routes.put("/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat",
            Profile.N2L_CONVERSATION);
        ROUTE_PROFILES = Collections.unmodifiableMap(routes);
    }

    private ConversationIdValidator() {
    }

    /** 校验候选值是否满足指定 profile；{@code null}/空/非法返回 {@code false}。 */
    public static boolean isValid(Profile profile, String value) {
        if (value == null || value.isEmpty()) {
            return false;
        }
        Pattern pattern = switch (profile) {
            case STANDARD_CONVERSATION -> STANDARD;
            case WORKFLOW_CONVERSATION -> WORKFLOW;
            case N2L_CONVERSATION -> N2L;
        };
        return pattern.matcher(value).matches();
    }

    /** 已匹配路由 pattern（{@code BEST_MATCHING_PATTERN}）→ profile；未登记返回 {@code null}。 */
    public static Profile profileFor(String bestMatchingPattern) {
        if (bestMatchingPattern == null) {
            return null;
        }
        return ROUTE_PROFILES.get(bestMatchingPattern);
    }

    /** 注册表全部路由 pattern（对账测试用）。 */
    public static Set<String> registeredPatterns() {
        return ROUTE_PROFILES.keySet();
    }
}
