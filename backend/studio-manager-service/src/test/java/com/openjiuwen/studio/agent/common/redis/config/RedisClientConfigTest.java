/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.redis.config;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RedisClientConfigTest {

    private final Ciphers ciphers = new Ciphers(null, null);

    @Test
    void testGettersAndSetters() {
        RedisClientConfig config = newConfig();
        config.setRedisHost("localhost");
        config.setRedisPort(6379);
        config.setRedisPassword("password");
        config.setConnectionMinimumIdleSize(10);
        config.setConnectionPoolSize(50);
        config.setNodeAddrList("node1,node2");
        config.setMasterName("master");
        config.setSentinelPorts("26379,26380");
        config.setTargetPorts("6379,6380");
        config.setClusterNodeList("cluster1,cluster2");

        assertEquals("localhost", config.getRedisHost());
        assertEquals(6379, config.getRedisPort());
        assertEquals("password", config.getRedisPassword());
        assertEquals(10, config.getConnectionMinimumIdleSize());
        assertEquals(50, config.getConnectionPoolSize());
        assertEquals("node1,node2", config.getNodeAddrList());
        assertEquals("master", config.getMasterName());
        assertEquals("26379,26380", config.getSentinelPorts());
        assertEquals("6379,6380", config.getTargetPorts());
        assertEquals("cluster1,cluster2", config.getClusterNodeList());
    }

    @Test
    void testDefaultValues() {
        RedisClientConfig config = newConfig();
        assertEquals(0, config.getRedisPort());
        assertEquals(0, config.getConnectionMinimumIdleSize());
        assertEquals(0, config.getConnectionPoolSize());
    }

    @Test
    void testEqualsAndHashCode() {
        RedisClientConfig config1 = newConfig();
        config1.setRedisHost("localhost");
        config1.setRedisPort(6379);

        RedisClientConfig config2 = newConfig();
        config2.setRedisHost("localhost");
        config2.setRedisPort(6379);

        assertEquals(config1, config2);
        assertEquals(config1.hashCode(), config2.hashCode());
    }

    @Test
    void testToString() {
        RedisClientConfig config = newConfig();
        config.setRedisHost("localhost");
        String str = config.toString();
        assertEquals(true, str.contains("localhost"));
    }

    private RedisClientConfig newConfig() {
        return new RedisClientConfig(ciphers);
    }
}
