/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.config;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisClientWrapper;
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProviderCondition;
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProviderConfig;
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProviderFactory;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * Redis 客户端自动装配。
 *
 * <p>通过 {@link RedisClientProviderFactory} 按 Provider 插件机制解析实现：
 * 内置 redisson/memory、ServiceLoader 插件包、显式类名（{@code redis.provider.class}），
 * 并兼容存量 redis.client-type 与 RedisClient3rd 扩展点（见 provider 包契约文档）。
 */
@Configuration
@Lazy
@Slf4j
public class RedisClientAutoConfig {

    @Value("${redis.enable-log}")
    private boolean enableLog;

    @Autowired(required = false)
    private ObjectMapper objectMapper;

    /**
     * 按配置解析并加载 RedisClient（统一套 Wrapper：耗时日志 + 错误分类降级）。
     *
     * @param providerConfig provider 配置（type / class / 存量 client-type）
     * @param redisClientConfig redis 连接配置
     * @return RedisClient
     */
    @Bean
    @org.springframework.context.annotation.Conditional(RedisClientProviderCondition.class)
    public RedisClient redisClient(RedisClientProviderConfig providerConfig,
        RedisClientConfig redisClientConfig) {
        RedisClient client = new RedisClientProviderFactory().createClient(providerConfig, redisClientConfig);
        return new RedisClientWrapper(client, enableLog);
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(redisConnectionFactory);

        // 使用 Spring 容器中的 ObjectMapper（已配置 StreamReadConstraints），若不存在则新建
        ObjectMapper redisObjectMapper = objectMapper != null ? objectMapper.copy() : new ObjectMapper();

        redisObjectMapper.registerModule(new JavaTimeModule());
        redisObjectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

        // 其他配置
        redisObjectMapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        redisObjectMapper.activateDefaultTyping(redisObjectMapper.getPolymorphicTypeValidator(),
            ObjectMapper.DefaultTyping.NON_FINAL, JsonTypeInfo.As.PROPERTY);

        Jackson2JsonRedisSerializer<Object> serializer = new Jackson2JsonRedisSerializer<>(redisObjectMapper, Object.class);

        // 设置序列化器
        template.setKeySerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(serializer);
        template.setHashValueSerializer(serializer);

        template.afterPropertiesSet();
        return template;
    }
}
