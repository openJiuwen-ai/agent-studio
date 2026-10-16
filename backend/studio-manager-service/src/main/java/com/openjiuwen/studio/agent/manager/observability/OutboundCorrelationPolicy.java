/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import java.util.List;

/**
 * Manager 出站关联 Header 策略（COM-04 §4.1）。
 *
 * <p>三种显式策略对应唯一允许的关联 Header 集合；未知目标不是第四种"宽松策略"——
 * 未知目标不得调用 Provider，适配器也不得注入三个关联 Header。
 *
 * <ul>
 *   <li>{@code RUNTIME_EXECUTION}：Runtime Agent/Workflow/网页执行/节点执行——
 *       request + trace + execution；</li>
 *   <li>{@code RUNTIME_NON_EXECUTION}：Runtime 查询、管理、代理 Tool/MCP 等——
 *       request + trace，明确删除 execution；</li>
 *   <li>{@code BUILDER}：Builder——request + trace，明确删除 execution。</li>
 * </ul>
 */
public enum OutboundCorrelationPolicy {

    /** Runtime 执行（Agent/Workflow/网页执行/节点）。必需 MDC：request-id、trace_id、execution-id。 */
    RUNTIME_EXECUTION(MdcKeys.REQUEST_ID, MdcKeys.TRACE_ID, MdcKeys.EXECUTION_ID),

    /** Runtime 非执行（查询/管理/代理 Tool/MCP）。必需 MDC：request-id、trace_id。 */
    RUNTIME_NON_EXECUTION(MdcKeys.REQUEST_ID, MdcKeys.TRACE_ID),

    /** Builder。必需 MDC：request-id、trace_id。 */
    BUILDER(MdcKeys.REQUEST_ID, MdcKeys.TRACE_ID);

    private final List<String> requiredMdcKeys;

    OutboundCorrelationPolicy(String... requiredMdcKeys) {
        this.requiredMdcKeys = List.of(requiredMdcKeys);
    }

    /** 该策略必需的 MDC key（按序）。 */
    public List<String> requiredMdcKeys() {
        return requiredMdcKeys;
    }
}
