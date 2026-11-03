/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.examples.redis;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.contract.RedisContractTestBase;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderContext;

import java.util.Map;

/**
 * 演示 Provider 过契约套件（自证样板）：增强内存后端与默认 Redisson 实现
 * 跑同一套契约用例，企业接入时照此提供自己实现的子类即可复用全部验收。
 */
class DemoProviderContractTest extends RedisContractTestBase {

    @Override
    protected RedisClient createClient() {
        // 走工厂链路（含企业专属参数透传），与生产装配路径一致
        RedisProviderContext context = new RedisProviderContext.Builder()
            .singleNode("demo-local", 6379, 0)
            .rawConfig(Map.of("logCommands", false, "latencyMillis", 0))
            .build();
        return new DemoRedisProviderFactory().create(context);
    }
}
