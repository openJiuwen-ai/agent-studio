/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import feign.Target;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Set;

/**
 * Feign 客户 Header 透传拦截器 — manager→agent_runtime/agent_builder boundary 转发
 *
 * <p>仅在 boundary Feign client（agentRuntime / agentBuilder）上做
 * customer header 透传，其余 Feign client 一律跳过。
 */
@Component
public class CustomerHeaderFeignInterceptor implements RequestInterceptor {

    private static final Logger log = LoggerFactory.getLogger(CustomerHeaderFeignInterceptor.class);

    /** boundary Feign client 白名单 */
    private static final Set<String> BOUNDARY_CLIENTS = Set.of("agentRuntime", "agentBuilder");

    @Override
    public void apply(RequestTemplate template) {
        Map<String, String> captured = RequestContextUtils.getCustomerHeaders();
        if (captured == null || captured.isEmpty()) {
            return;
        }

        // 仅 boundary client 做透传
        Target<?> feignTarget = template.feignTarget();
        String clientName = feignTarget == null ? null : feignTarget.name();
        if (clientName == null || !BOUNDARY_CLIENTS.contains(clientName)) {
            return;
        }

        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        if (profile == null || !profile.isEnabled()) {
            return;
        }

        // 直接透传所有 captured customer headers
        for (Map.Entry<String, String> entry : captured.entrySet()) {
            if (!template.headers().containsKey(entry.getKey())) {
                template.header(entry.getKey(), entry.getValue());
            }
        }

        if (!captured.isEmpty()) {
            log.info("[customer-header] Feign customer header passthrough: client={}, headers={}",
                clientName, captured.keySet());
        }
    }
}
