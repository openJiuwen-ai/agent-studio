/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.impl.RedisClientRedisson;

/**
 * 内置原生 Provider：Redisson 实现（单机/集群/哨兵，平台默认）。
 */
public class RedissonClientProvider implements RedisClientProvider {
    /**
     * 内置 provider 标识。
     */
    public static final String NAME = "redisson";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public RedisClient createClient(RedisClientConfig config) {
        return new RedisClientRedisson(config);
    }
}
