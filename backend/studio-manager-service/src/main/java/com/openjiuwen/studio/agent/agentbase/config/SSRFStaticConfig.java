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

    /**
     * 开关关闭时的启动告警文案（包内可见，便于单测锁定文案与环境变量名）。
     *
     * <p>文案刻意只陈述本开关直接控制的语义——回环/私网/链路本地地址与 blocked-domains 不再拦截，
     * 不断言 allowed-protocols 白名单是否仍生效：协议白名单与总开关是否解耦由 {@code SSRFValidator} 决定，
     * 告警在任一合并顺序下都必须成立。
     *
     * <p>环境变量：application-manager.yml 中该键的占位符为 {@code ${SSRF_VALIDATION_ENABLED:false}}；
     * Spring 宽松绑定同时接受 {@code KNOWLEDGE_SSRF_VALIDATION_ENABLED}，两种写法都要在文案里给出，
     * 否则运维按错误的变量名配置后会以为已开启校验。
     */
    static final String SSRF_VALIDATION_DISABLED_WARNING = "knowledge.ssrf.validation.enabled=false "
        + "(env SSRF_VALIDATION_ENABLED): SSRF protection for knowledge base connections is disabled - "
        + "loopback/private/link-local addresses and blocked internal domains are no longer blocked. "
        + "Set knowledge.ssrf.validation.enabled=true (env SSRF_VALIDATION_ENABLED or "
        + "KNOWLEDGE_SSRF_VALIDATION_ENABLED) to enable it.";

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
            log.warn(SSRF_VALIDATION_DISABLED_WARNING);
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