/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.config;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;

import lombok.Data;
import lombok.ToString;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

import jakarta.annotation.PostConstruct;

@Configuration
@Data
public class RedisClientConfig {
    @Value("${redis.host}")
    private String redisHost;

    @Value("${redis.port}")
    private int redisPort;

    /** 已解密明文——排除出 toString，防止未来误打印泄入日志 */
    @ToString.Exclude
    @Value("${redis.password}")
    private String redisPassword;

    @Value("${redis.connection.minimum.idle.size:24}")
    private int connectionMinimumIdleSize;

    @Value("${redis.connection.pool.size:64}")
    private int connectionPoolSize;

    @Value("${redis.node_addr_list}")
    private String nodeAddrList;

    @Value("${redis.master}")
    private String masterName;

    @Value("${redis.sentinel_ports}")
    private String sentinelPorts;

    @Value("${redis.target_ports}")
    private String targetPorts;

    @Value("${redis.cluster_node_list}")
    private String clusterNodeList;

    @Value("${redis.max-string-length}")
    private int jsonMaxStringLength;

    @Value("${redis.max-single-message-length:-1}")
    private int maxSingleMessageLength;

    @Value("${redis.history-eviction-threshold:0.75}")
    private double historyEvictionThreshold;

    // ---- Redis Provider SPI 配置（Phase 2 新增，全部可选，不配置=既有行为不变）----

    /** 客户端类型：redisson（缺省）/ memory（测试）/ custom（企业 Provider） */
    @Value("${redis.client-type:redisson}")
    private String clientType;

    /** custom 时的实现入口：全限定类名或 ServiceLoader 注册名 */
    @Value("${redis.provider-class:}")
    private String providerClass;

    /** Provider 专属参数透传（可能含企业凭证）——排除出 toString */
    @ToString.Exclude
    @Value("${redis.provider-config:}")
    private String providerConfig;

    /** Provider 专属参数文件路径（替代内联，框架不解析内部字段） */
    @Value("${redis.provider-config-file:}")
    private String providerConfigFile;

    private final Ciphers ciphers;

    @PostConstruct
    public void decryptSensitiveFields() {
        redisPassword = ciphers.decrypt(redisPassword);
    }
}
