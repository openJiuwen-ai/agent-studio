/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

/**
 * 内部请求目标枚举 — 区分 boundary 转发和下游 rename 的 Target
 *
 * <p>平台完整枚举（代码类），本期必须实现的核心集标注 R/CR 编号。
 */
public enum InternalTarget {
    // ── boundary 转发 ──
    /** manager→agent_runtime 入站 boundary */
    AGENT_RUNTIME_INBOUND,
    /** manager→agent_builder 入站 boundary */
    AGENT_BUILDER_INBOUND,

    // ── 核心必须启用集 ──
    /** LakeSearch 下游 rename */
    LAKESEARCH,
    /** runtime LLM Chat 下游 rename */
    RUNTIME_LLM_CHAT,
    /**
     * runtime MCP 外部服务调用下游 rename（同构，剥 auth_keys 的 cust- 前缀 + captured 覆盖）。
     *
     * <p>读取方：studio-runtime（MCP client 出站）与 studio-manager（{@code McpClientService} 调测出站——
     * 调测不经 runtime，由 manager 自身剥前缀）。mappings 来自共享 {@code deploy/config/customer-header.yml}。
     */
    RUNTIME_MCP_CALL,
    /** IR auth_keys forward-list 声明 */
    IR_AUTH_KEYS,

    // ── 条件启用集 ──
    /** runtime Search */
    RUNTIME_SEARCH,
    /** Builder Chat */
    BUILDER_LLM_CHAT,
    /** Builder Embedding */
    BUILDER_MODEL_EMBEDDING,
    /** Builder Rerank */
    BUILDER_MODEL_RERANK,
    /** CUSTOM_APIKEY 探针 */
    MODEL_AUTH_CHECK,

    // ── 补充集（enabled=true 时） ──
    /** Memory 入站 */
    MEMORY_INBOUND,
    /** Memory 内部 LLM */
    MEMORY_LLM
}
