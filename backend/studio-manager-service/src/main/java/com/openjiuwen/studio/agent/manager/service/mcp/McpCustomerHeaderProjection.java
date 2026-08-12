/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp;

import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.HeaderRename;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * MCP 调测出站 customer header rename
 *
 * <p>manager 调测 MCP 不经 agent-runtime，直接连 MCP server。
 * 出站前对 auth_keys 的 cust-* 做配置驱动 rename。
 */
public final class McpCustomerHeaderProjection {
    private static final Logger log = LoggerFactory.getLogger(McpCustomerHeaderProjection.class);

    private static final String CUST_PREFIX = "cust-";

    private McpCustomerHeaderProjection() {
    }

    /**
     * 就地改写出站 headers：剥 cust- 前缀
     *
     * @param headers        出站 header
     * @param mcpServiceName MCP 服务名（仅用于日志）
     */
    public static void renameOutboundCustomerHeaders(Map<String, String> headers, String mcpServiceName) {
        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        renameOutboundCustomerHeaders(headers, mcpServiceName, profile);
    }

    static void renameOutboundCustomerHeaders(Map<String, String> headers, String mcpServiceName,
                                               CustomerHeaderProfile profile) {
        if (CollectionUtils.isEmpty(headers)) {
            return;
        }

        // 收集静态 auth_keys 的 cust-*
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

        Map<String, String> renamed = new LinkedHashMap<>();
        if (profile != null && profile.isEnabled()) {
            renamed.putAll(HeaderRename.resolve(custHeaders, profile));
        }

        if (renamed.isEmpty()) {
            return;
        }

        // 删原 cust-*
        for (String key : new ArrayList<>(headers.keySet())) {
            if (key != null && key.toLowerCase().startsWith(CUST_PREFIX)) {
                headers.remove(key);
            }
        }
        headers.putAll(renamed);

        log.info("[customer-header] MCP customer header rename: service={}, static_cust_keys={}, renamed_keys={}",
            mcpServiceName, custHeaders.keySet(), renamed.keySet());
    }
}
