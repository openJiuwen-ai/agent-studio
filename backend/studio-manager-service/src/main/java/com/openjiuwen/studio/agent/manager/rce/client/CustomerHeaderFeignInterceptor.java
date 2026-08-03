/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.openjiuwen.studio.agent.common.customerheader.*;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import feign.Target;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Feign 客户 Header 透传拦截器 — manager→agent_runtime/agent_builder boundary 转发
 *
 * <p>仅在 boundary Feign client（agentRuntime / agentBuilder）上做
 * customer-passthrough，其余 Feign client（CssUniSearch、agent-builder[AgentSpaceClient=发布管理，
 * 只走 X-Auth-Token]、iamClient、elbClient 等下游云服务）一律跳过，避免原始 cust-* 泄漏到非 boundary下游
 *
 * <p>Profile 启用时使用配置驱动的 passthrough 白名单；
 * Profile 未启用时不添加客户 header
 */
@Component
public class CustomerHeaderFeignInterceptor implements RequestInterceptor {

    private static final Logger log = LoggerFactory.getLogger(CustomerHeaderFeignInterceptor.class);

    /**
     * boundary Feign client 白名单 —— 按 {@code @FeignClient(name=...)} 匹配，映射到对应 boundary target。
     * 仅含真正的 customer-identity boundary：agentRuntime、agentBuilder（builder 模型服务）。
     * 不在此表的 client（含 CssUniSearch、agent-builder[AgentSpaceClient=发布管理]）一律不做 passthrough。
     */
    private static final Map<String, InternalTarget> BOUNDARY_CLIENTS = Map.of(
        "agentRuntime", InternalTarget.AGENT_RUNTIME_INBOUND,
        "agentBuilder", InternalTarget.AGENT_BUILDER_INBOUND);

    @Override
    public void apply(RequestTemplate template) {
        CapturedCustomerHeaders captured = RequestContextUtils.getCustomerHeaders();
        if (captured == null || captured.isEmpty()) {
            return;
        }

        // 仅 boundary client 做 passthrough，其余下游 client直接跳过
        Target<?> feignTarget = template.feignTarget();
        String clientName = feignTarget == null ? null : feignTarget.name();
        InternalTarget target = clientName == null ? null : BOUNDARY_CLIENTS.get(clientName);
        if (target == null) {
            return;
        }

        CustomerHeaderProfile profile = SpringBeanUtils.getBean(CustomerHeaderProfile.class);
        if (profile == null || !profile.isEnabledInSimpleMode()) {
            return;
        }

        // 使用 HeaderProjectionEngine 的 passthrough 逻辑（配置驱动）
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        Map<String, HeaderValue> passthrough = engine.passthrough(target, captured);

        for (Map.Entry<String, HeaderValue> entry : passthrough.entrySet()) {
            // 不覆盖已有的平台 header（平台生成值优先）
            if (!template.headers().containsKey(entry.getKey())) {
                template.header(entry.getKey(), entry.getValue().value());
            }
        }

        if (!passthrough.isEmpty()) {
            log.info("[customer-header] Feign customer header passthrough: client={}, target={}, headers={}",
                clientName, target, passthrough.keySet());
        }
    }
}
