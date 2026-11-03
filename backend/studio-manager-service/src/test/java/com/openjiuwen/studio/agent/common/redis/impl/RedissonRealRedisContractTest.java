/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.impl;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.contract.RedisContractTestBase;

import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

/**
 * 默认实现（Redisson）× 真实 Redis 的契约验收（黄金标准）。
 *
 * 门控：设置 REDIS_CONTRACT_TARGET 环境变量后启用（与 Python 侧契约套件口径一致），
 * 形如 host:port 或 redis://host:port；密码取 REDIS_CONTRACT_PASSWORD（未设置视为无密码）。
 * 未设置时本类跳过，不阻塞常规 CI。
 */
@EnabledIfEnvironmentVariable(named = "REDIS_CONTRACT_TARGET", matches = ".+")
class RedissonRealRedisContractTest extends RedisContractTestBase {

    @Override
    protected RedisClient createClient() {
        String target = System.getenv("REDIS_CONTRACT_TARGET").replaceFirst("^redis://", "");
        String[] hostPort = target.split(":");
        String host = hostPort[0];
        int port = hostPort.length > 1 ? Integer.parseInt(hostPort[1]) : 6379;
        String password = System.getenv("REDIS_CONTRACT_PASSWORD");

        RedisClientConfig config = new RedisClientConfig(new Ciphers(null, null));
        config.setRedisHost(host);
        config.setRedisPort(port);
        if (password != null && !password.isBlank()) {
            config.setRedisPassword(password);
        }
        // 与生产 yml 缺省一致（@Value 无缺省，纯构造时为 0 会导致所有读触发流长度约束异常）
        config.setJsonMaxStringLength(100_000_000);
        config.setConnectionMinimumIdleSize(1);
        config.setConnectionPoolSize(4);
        return new RedisClientRedisson(config);
    }

    @Override
    protected void disposeClient(RedisClient client) {
        if (client instanceof RedisClientRedisson redisson) {
            redisson.shutdown();
        }
    }
}
