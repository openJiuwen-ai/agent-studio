/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.tck;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.demo.DemoRedisClient;
import com.openjiuwen.studio.agent.common.redis.demo.DemoRedisClientProvider;

/**
 * 演示自研 Provider 跑批一致性测试套件（验收标准：demo Provider 通过 TCK，证明可替换性）。
 */
class DemoRedisClientProviderContractTest extends AbstractRedisClientContractTest {
    @Override
    protected RedisClient createClient() {
        return new DemoRedisClientProvider().createClient(null);
    }

    /**
     * 自研实现的自有能力（操作统计）在 TCK 之外单独验证。
     */
    @org.junit.jupiter.api.Test
    void demoClient_countsOperations() {
        DemoRedisClient demo = new DemoRedisClient();
        demo.set("demo:key", "value");
        demo.get("demo:key");
        org.junit.jupiter.api.Assertions.assertEquals(1, demo.getWriteOps());
        org.junit.jupiter.api.Assertions.assertEquals(1, demo.getReadOps());
    }
}
