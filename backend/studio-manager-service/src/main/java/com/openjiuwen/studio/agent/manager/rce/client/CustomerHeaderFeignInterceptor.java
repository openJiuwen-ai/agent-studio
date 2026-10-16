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

        // 透传客户 Header，但排除三个关联 Header（COM-04 §4.3：关联 Header 由
        // CorrelationFeignInterceptor 权威注入并覆盖伪造值，客户透传不得重复写入或保留预置值）
        for (Map.Entry<String, String> entry : captured.entrySet()) {
            if (isCorrelationHeader(entry.getKey())) {
                continue;
            }
            if (!template.headers().containsKey(entry.getKey())) {
                template.header(entry.getKey(), entry.getValue());
            }
        }

        if (!captured.isEmpty()) {
            log.info("[customer-header] Feign customer header passthrough: client={}, headers={}",
                clientName, captured.keySet());
        }
    }

    /** 三个关联 Header 的大小写不敏感判定——客户透传排除，防覆盖权威值。 */
    static boolean isCorrelationHeader(String name) {
        return "X-Request-Id".equalsIgnoreCase(name) || "TraceID".equalsIgnoreCase(name)
            || "X-Execution-Id".equalsIgnoreCase(name);
    }
}
