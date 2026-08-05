/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.common.utils.redis.config;

import lombok.Data;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

@Configuration
@Data
public class RedisClientConfig {
    @Value("${redis.host}")
    private String redisHost;

    @Value("${redis.port}")
    private int redisPort;

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
}
