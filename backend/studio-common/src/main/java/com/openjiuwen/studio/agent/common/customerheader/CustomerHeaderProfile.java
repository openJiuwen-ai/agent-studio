/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;

import java.util.HashMap;
import java.util.Map;

/**
 * 客户 Header 配置 — 从环境变量加载
 *
 * <p>环境变量：
 * <ul>
 *   <li>{@code CUSTOMER_HEADER_ENABLED}: true/false</li>
 *   <li>{@code CUSTOMER_HEADER_MAPPINGS}: "cust-userid:userId,cust-token:token"</li>
 * </ul>
 */
@Component
public class CustomerHeaderProfile {

    @Value("${customer-header.enabled:false}")
    private String enabledStr;

    @Value("${customer-header.mappings:}")
    private String mappingsStr;

    private boolean enabled = false;
    private Map<String, String> mappings = new HashMap<>();

    @PostConstruct
    public void init() {
        this.enabled = "true".equalsIgnoreCase(enabledStr);
        parseMappings();
    }

    private void parseMappings() {
        if (mappingsStr == null || mappingsStr.isEmpty()) {
            return;
        }
        for (String pair : mappingsStr.split(",")) {
            pair = pair.trim();
            if (pair.isEmpty()) continue;
            int colon = pair.indexOf(':');
            if (colon > 0) {
                String from = pair.substring(0, colon).trim();
                String to = pair.substring(colon + 1).trim();
                mappings.put(from, to);
            }
        }
    }

    public boolean isEnabled() {
        return enabled;
    }

    public Map<String, String> getMappings() {
        return mappings;
    }

    public String[] getCaptureAllowList() {
        if (!enabled || mappings.isEmpty()) {
            return new String[0];
        }
        return mappings.keySet().toArray(new String[0]);
    }
}
