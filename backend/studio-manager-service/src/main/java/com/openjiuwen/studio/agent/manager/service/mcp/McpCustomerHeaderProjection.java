/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp;

import com.openjiuwen.studio.agent.common.customerheader.CapturedCustomerHeaders;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.HeaderProjectionEngine;
import com.openjiuwen.studio.agent.common.customerheader.HeaderValue;
import com.openjiuwen.studio.agent.common.customerheader.InternalTarget;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * MCP 调测出站 customer header rename — 与 LakeSearch {@code getHeaders}同构。
 *
 * <p>manager 调测 MCP（{@code McpClientService} 查/调工具列表）不经 agent-runtime，直接连 MCP server。
 * 出站前对 auth_keys 的 {@code cust-*} 做配置驱动 rename，由 customer-header 功能开关 gated：
 * <ul>
 *   <li>profile 启用（{@link CustomerHeaderProfile#isEnabledInSimpleMode}）：{@link HeaderProjectionEngine#project}
 *       按 {@link InternalTarget#RUNTIME_MCP_CALL} 的共享 YAML mappings 改名（{@code cust-token}→{@code token}、
 *       {@code cust-userid}→{@code userid}），仅使用自身配置的 auth_keys，不透传上游 captured。
 *       <b>无硬编码</b>——from→to 全部来自配置。</li>
 *   <li>profile 未启用 / 无配置：<b>原样透传</b>（向后兼容，不 rename、不删 {@code cust-*}，业务语义不变）。</li>
 * </ul>
 *
 * <p>功能开关：{@code customer-header.enabled}（env {@code CUSTOMER_HEADER_ENABLED} 覆盖）。关闭即透传、
 * 开启即配置驱动 rename。agent-runtime 实际运行路径不经本类（由 runtime 自身
 * {@code inject_customer_headers_to_mcp} 剥前缀）。
 */
public final class McpCustomerHeaderProjection {
    private static final Logger log = LoggerFactory.getLogger(McpCustomerHeaderProjection.class);

    private static final String CUST_PREFIX = "cust-";

    private McpCustomerHeaderProjection() {
    }

    /**
     * 就地改写出站 headers：剥 {@code cust-} 前缀。仅使用自身配置的 auth_keys，不透传上游 captured。profile 取自 Spring 上下文。
     *
     * @param headers        出站 header（{@code McpClientService} 的 safeHeaders，大小写不敏感）
     * @param mcpServiceName MCP 服务名（仅用于日志）
     */
    public static void renameOutboundCustomerHeaders(Map<String, String> headers, String mcpServiceName) {
        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        renameOutboundCustomerHeaders(headers, mcpServiceName, profile);
    }

    /**
     * 就地改写出站 headers，可注入 profile 便于单测。
     *
     * @param headers        出站 header
     * @param mcpServiceName MCP 服务名（仅用于日志）
     * @param profile        customer header profile（可为 null，无配置时不重命名）
     */
    static void renameOutboundCustomerHeaders(Map<String, String> headers, String mcpServiceName,
        CustomerHeaderProfile profile) {
        if (CollectionUtils.isEmpty(headers)) {
            return;
        }
        // 收集静态 auth_keys 的 cust-*（key 小写化，便于与 captured / mappings 比对）
        Map<String, String> custHeaders = new LinkedHashMap<>();
        for (Map.Entry<String, String> e : headers.entrySet()) {
            String key = e.getKey();
            if (key != null && key.toLowerCase().startsWith(CUST_PREFIX)) {
                custHeaders.put(key.toLowerCase(), e.getValue());
            }
        }
        if (custHeaders.isEmpty()) {
            return;
        }

        Map<String, String> projected = new LinkedHashMap<>();

        if (profile != null && profile.isEnabledInSimpleMode()) {
            // 配置驱动主路：仅使用自身配置的 auth_keys 做 rename，不透传上游 captured
            Map<String, HeaderValue> asCaptured = new LinkedHashMap<>();
            for (Map.Entry<String, String> e : custHeaders.entrySet()) {
                asCaptured.put(e.getKey(), HeaderValue.customerCaptured(e.getKey(), e.getValue()));
            }
            projected.putAll(new HeaderProjectionEngine(profile)
                .project(InternalTarget.RUNTIME_MCP_CALL, CapturedCustomerHeaders.from(asCaptured)));
        }
        // profile 未启用 / null：原样透传（向后兼容，不 rename、不删 cust-*；projected 为空 → 下方 return）

        // 无可剥配置（profile 未启用 / 无 mappings / 无匹配 cust-*）：原样不动，不删 cust-*
        if (projected.isEmpty()) {
            return;
        }

        // 删原 cust-*（key 副本遍历避免 ConcurrentModificationException），再追加剥前缀后的 token/userid
        for (String key : new ArrayList<>(headers.keySet())) {
            if (key != null && key.toLowerCase().startsWith(CUST_PREFIX)) {
                headers.remove(key);
            }
        }
        headers.putAll(projected);

        log.info("[customer-header] MCP customer header rename: service={}, static_cust_keys={}, projected_keys={}",
            mcpServiceName, custHeaders.keySet(), projected.keySet());
    }

}
