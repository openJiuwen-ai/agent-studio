/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.impl.RedisClientMemory;

/**
 * 内置 Provider：内存实现（仅用于单元测试，语义与 RedisClient 契约对齐）。
 */
public class MemoryClientProvider implements RedisClientProvider {
    /**
     * 内置 provider 标识。
     */
    public static final String NAME = "memory";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public RedisClient createClient(RedisClientConfig config) {
        return new RedisClientMemory();
    }
}
