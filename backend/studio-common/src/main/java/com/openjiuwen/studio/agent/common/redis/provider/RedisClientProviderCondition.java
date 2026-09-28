/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import org.springframework.context.annotation.Condition;
import org.springframework.context.annotation.ConditionContext;
import org.springframework.core.env.Environment;
import org.springframework.core.type.AnnotatedTypeMetadata;

/**
 * RedisClient Bean 激活条件。
 *
 * <p>保持存量 Bean 存在语义：以下任一满足时创建 RedisClient Bean，否则不创建
 * （与旧版 @ConditionalOnProperty(client-type=redisson/memory) + RedisClient3rd classpath 条件对齐）：
 * <ul>
 *   <li>配置了 {@code redis.provider.type} 或 {@code redis.provider.class}</li>
 *   <li>配置了 {@code redis.client-type}（任意值）</li>
 *   <li>classpath 存在存量 RedisClient3rd 扩展类</li>
 * </ul>
 */
public class RedisClientProviderCondition implements Condition {
    @Override
    public boolean matches(ConditionContext context, AnnotatedTypeMetadata metadata) {
        Environment env = context.getEnvironment();
        if (hasText(env.getProperty("redis.provider.type")) || hasText(env.getProperty("redis.provider.class"))) {
            return true;
        }
        if (hasText(env.getProperty("redis.client-type"))) {
            return true;
        }
        try {
            Class.forName(RedisClientProviderFactory.LEGACY_3RD_CLASS, false,
                RedisClientProviderCondition.class.getClassLoader());
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }
}
