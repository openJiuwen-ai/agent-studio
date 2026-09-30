/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.demo;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProvider;

/**
 * 演示用自研 Provider：验证不修改框架源码、以插件方式接入企业自研 Redis 实现。
 *
 * <p>接入方式（两种）：
 * <ul>
 *   <li>ServiceLoader 插件包：本类已注册到测试 classpath 的
 *       META-INF/services/...RedisClientProvider，配置 redis.provider.type=demo-custom 启用</li>
 *   <li>显式类名：配置 redis.provider.class=本类全限定名</li>
 * </ul>
 */
public class DemoRedisClientProvider implements RedisClientProvider {
    /**
     * 演示 provider 标识。
     */
    public static final String NAME = "demo-custom";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public RedisClient createClient(RedisClientConfig config) {
        return new DemoRedisClient();
    }
}
