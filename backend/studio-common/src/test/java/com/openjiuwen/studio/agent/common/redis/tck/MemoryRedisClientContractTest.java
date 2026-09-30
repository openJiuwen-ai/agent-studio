/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.tck;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.impl.RedisClientMemory;

/**
 * 内置内存实现跑批一致性测试套件（验收标准：原生默认实现通过 TCK）。
 */
class MemoryRedisClientContractTest extends AbstractRedisClientContractTest {
    @Override
    protected RedisClient createClient() {
        return new RedisClientMemory();
    }
}
