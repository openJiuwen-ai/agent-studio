/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.config;

import lombok.Data;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * RDC (Registry & Discovery Center) 接入配置
 *
 * <p>FEAT-131: 低码发布即可被高码调用（被调方向）</p>
 * <p>配置前缀: rdc</p>
 */
@Data
@Component
@ConfigurationProperties(prefix = "rdc")
public class RdcProperties {

    /**
     * 是否启用 A2A 注册（灰度开关，默认关闭）
     */
    private boolean enabled = false;

    /**
     * RDC 服务地址
     */
    private String baseUrl;

    /**
     * 平台级统一租户 ID（manager 与 RDC 内部交互携带，不构成对外契约）
     */
    private String tenantId;

    /**
     * RDC 认证 Bearer Token
     */
    private String token;

    /**
     * HTTP 调用超时（毫秒）
     */
    private int timeoutMs = 10000;

    /**
     * runtime 对外可达地址（用于 Agent Card 的 url 字段）
     */
    private String runtimeBaseUrl;

    /**
     * runtime 监听端口
     */
    private int runtimePort;

    /**
     * A2A 服务面路径（默认 /a2a）
     */
    private String endpointPath = "/a2a";

    /**
     * 判断配置是否完整可用
     */
    public boolean isConfigured() {
        return enabled && baseUrl != null && !baseUrl.isBlank()
            && tenantId != null && !tenantId.isBlank()
            && token != null && !token.isBlank()
            && runtimePort > 0
            && runtimeBaseUrl != null && !runtimeBaseUrl.isBlank();
    }
}
