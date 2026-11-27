/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.agentbase.config;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.Set;

@Slf4j
@Component
public class SSRFStaticConfig {

    @Getter
    private static boolean ssrfValidationEnabled;

    @Getter
    private static Set<String> blockedInternalDomains = Collections.emptySet();

    @Getter
    private static Set<String> allowedInternalDomains = Collections.emptySet();

    @Getter
    private static Set<String> allowedProtocols = Collections.emptySet();

    @Value("${knowledge.ssrf.validation.enabled}")
    public void setSsrfValidationEnabled(boolean value) {
        ssrfValidationEnabled = value;
        if (!value) {
            log.warn("knowledge.ssrf.validation.enabled=false: internal-address check for knowledge base "
                + "connections is disabled. The allowed-protocols whitelist still applies. "
                + "Set SSRF_VALIDATION_ENABLED=true to enable it.");
        }
    }

    @Value("${knowledge.ssrf.blocked-domains}")
    public void setBlockedInternalDomains(Set<String> value) {
        blockedInternalDomains = value;
    }

    @Value("${knowledge.ssrf.allowed-domains}")
    public void setAllowedInternalDomains(Set<String> value) {
        allowedInternalDomains = value;
    }

    // 注入 List<String> 类型的协议白名单
    @Value("${knowledge.ssrf.allowed-protocols:http,https}")
    public void setAllowedProtocols(Set<String> value) {
        allowedProtocols = value;
    }

}