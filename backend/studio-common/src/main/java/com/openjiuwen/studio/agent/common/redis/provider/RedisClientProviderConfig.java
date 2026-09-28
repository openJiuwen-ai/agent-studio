/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;

import lombok.Data;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

/**
 * Redis Provider 配置项（插件化注册入口）。
 *
 * <p>配置解析优先级（高 → 低）：
 * <ol>
 *   <li>{@code redis.provider.class}：Provider 实现类全限定名（无参构造），企业插件包直接指定</li>
 *   <li>{@code redis.provider.type}：Provider 标识（ServiceLoader 注册表 + 内置 redisson/memory 按名匹配）</li>
 *   <li>{@code redis.client-type}（存量兼容）：memory → 内存实现；其余值按 redisson 处理前的
 *       legacy RedisClient3rd 扩展点兼容（类存在时）</li>
 * </ol>
 */
@Configuration
@Data
public class RedisClientProviderConfig {
    /**
     * Provider 标识（如 redisson / memory / ServiceLoader 注册的企业自定义标识）。
     */
    @Value("${redis.provider.type:}")
    private String providerType;

    /**
     * Provider 实现类全限定名（优先级高于 provider-type）。
     */
    @Value("${redis.provider.class:}")
    private String providerClass;

    /**
     * 存量配置 redis.client-type（兼容保留，provider-type 优先）。
     */
    @Value("${redis.client-type:}")
    private String legacyClientType;
}
