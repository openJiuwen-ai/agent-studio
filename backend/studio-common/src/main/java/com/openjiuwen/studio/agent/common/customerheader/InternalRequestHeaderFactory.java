/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 内部请求 Header 工厂 — boundary 转发
 *
 * <p>构建 manager→runtime / manager→agent_builder 的出站 header：
 * <ul>
 *   <li>平台协议 header（X-Auth-Token、X-Language 等，manager 可信生成）</li>
 *   <li>Profile customer-passthrough（cust-userid、cust-token，来自入站白名单捕获）</li>
 *   <li>平台生成值覆盖外部同名值（防 X-Execution-Id 注入）</li>
 * </ul>
 *
 * <p>不负责下游 rename（由 {@link HeaderProjectionEngine} 处理）和身份校验。
 */
public class InternalRequestHeaderFactory {

    private final HeaderProjectionEngine engine;

    public InternalRequestHeaderFactory(HeaderProjectionEngine engine) {
        this.engine = engine;
    }

    /**
     * 构建 boundary 出站 header
     *
     * @param boundaryTarget boundary target（AGENT_RUNTIME_INBOUND / AGENT_BUILDER_INBOUND）
     * @param captured       入站捕获的客户 headers
     * @param generated      manager 可信生成的平台 header（X-Auth-Token、X-Language 等）
     * @return 合并后的出站 header 映射（平台生成覆盖外部同名值）
     */
    public Map<String, String> build(InternalTarget boundaryTarget,
                                     CapturedCustomerHeaders captured,
                                     Map<String, String> generated) {
        Map<String, String> result = new LinkedHashMap<>();

        // 1. 放入 customer-passthrough（来自入站白名单捕获，provenance=CUSTOMER_CAPTURED）
        Map<String, HeaderValue> passthrough = engine.passthrough(boundaryTarget, captured);
        for (Map.Entry<String, HeaderValue> entry : passthrough.entrySet()) {
            result.put(entry.getKey(), entry.getValue().value());
        }

        // 2. 放入平台生成 header（覆盖外部同名值，provenance=PLATFORM_GENERATED）
        if (generated != null) {
            for (Map.Entry<String, String> entry : generated.entrySet()) {
                if (entry.getKey() != null && entry.getValue() != null) {
                    result.put(entry.getKey().toLowerCase(), entry.getValue());
                }
            }
        }

        return result;
    }
}
