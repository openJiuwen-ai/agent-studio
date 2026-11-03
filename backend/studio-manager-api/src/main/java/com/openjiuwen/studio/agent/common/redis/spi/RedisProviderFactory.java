/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.spi;

/**
 * Redis Provider 工厂接口——企业自研实现的标准入口。
 *
 * 实现方式（三选一，推荐 A）：
 * A. 实现 RedisProviderFactory，由框架调用 create(context) 创建客户端
 * B. 直接实现 RedisClient 并提供无参构造 + void init(RedisProviderContext) 方法
 * C. 兼容旧接缝：保留 (String host, String password, int port) 三参构造器（过渡期）
 *
 * 注册方式：
 * 1. 显式配置：redis.provider-class = com.acme.NosRedisProviderFactory
 * 2. ServiceLoader：META-INF/services/...RedisProviderFactory 声明后自动发现
 *
 * @see RedisProviderContext
 * @see com.openjiuwen.studio.agent.common.redis.RedisClient
 */
public interface RedisProviderFactory {

    /**
     * 创建 Redis 客户端实例。
     *
     * @param context 配置上下文（连接参数 + 集群/哨兵配置 + 企业专属参数透传）
     * @return RedisClient 客户端实例
     * @throws RedisProviderException 创建失败（配置缺失、连接不通等）
     */
    com.openjiuwen.studio.agent.common.redis.RedisClient create(RedisProviderContext context);
}
