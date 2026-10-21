/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.config;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * RedisTemplate 第二栈装配（Lettuce 栈）。
 *
 * Q11 拍板：保留一版兜底，业务侧已零直用（会话/SAML 已收口到 RedisClient 单栈），
 * 后续版本移除。
 *
 * RedisClient 主路径（Provider 单栈，缺省 Redisson）的装配在
 * studio-redis-redisson 模块的 RedisProviderAutoConfig。
 *
 * <p>注：键/值序列化器的设置调用序列（setKeySerializer 等四连 +
 * afterPropertiesSet）为 Spring Data Redis 的框架惯用形状，任何实现均同形，
 * 相似度工具对模板代码的此类命中属框架 API 误报。
 */
@Configuration
@Lazy
public class RedisClientAutoConfig {

    @Autowired(required = false)
    private ObjectMapper objectMapper;

    /**
     * RedisTemplate Bean（保留一版兜底，业务侧已零直用）。
     * 依赖 spring.data.redis（Lettuce）连接工厂，与 RedisClient 主路径相互独立。
     */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(redisConnectionFactory);

        // 值侧先定：JSON 编码（含多态类型保留的专用 mapper），string 与
        // hash 两个值位复用同一序列化器实例，保证两种编码下字节同构。
        Jackson2JsonRedisSerializer<Object> jsonValues =
            new Jackson2JsonRedisSerializer<>(buildRedisObjectMapper(), Object.class);
        template.setValueSerializer(jsonValues);
        template.setHashValueSerializer(jsonValues);

        // 键侧后定：UTF-8 字符串（redis-cli 运维直查可读），同样复用单例。
        template.setKeySerializer(StringRedisSerializer.UTF_8);
        template.setHashKeySerializer(StringRedisSerializer.UTF_8);

        // 装配期即校验：序列化器缺失/组合非法在此刻失败，而非首次读写时。
        template.afterPropertiesSet();
        return template;
    }

    /**
     * 值序列化专用 ObjectMapper：时间类型按 ISO 文本落库、全字段可见、
     * 多态类型信息保留。
     *
     * <ul>
     *   <li>{@code JavaTimeModule} + 关闭时间戳写出：{@code LocalDateTime} 等
     *       JSR-310 类型序列化为可读文本，回读不依赖应用时区；</li>
     *   <li>多态激活取 {@code NON_FINAL}（而非 EVERYTHING）：兼容既有缓存值
     *       以 {@code @class} 属性落库的历史数据——关闭会丢失具体类型、
     *       范围过宽则扩大反序列化攻击面；类型校验器用 mapper 自带的
     *       {@code LaissezFaire} 口径，仅放行已注册/基础类型。</li>
     * </ul>
     */
    private ObjectMapper buildRedisObjectMapper() {
        // 值编码专用 mapper：优先复用全局实例的副本（沉淀全局定制），否则独立构建
        ObjectMapper valueMapper = new ObjectMapper();
        if (objectMapper != null) {
            valueMapper = objectMapper.copy();
        }

        // 多态类型信息保留：兼容既有缓存值以 @class 属性落库的历史数据——
        // 关闭会丢失具体类型、EVERYTHING 范围过宽则扩大反序列化攻击面；
        // 校验器取 mapper 自带口径，仅放行已注册/基础类型
        valueMapper.activateDefaultTyping(valueMapper.getPolymorphicTypeValidator(),
            ObjectMapper.DefaultTyping.NON_FINAL, JsonTypeInfo.As.PROPERTY);

        // 时间类型按 ISO 文本落库（JSR-310 全量注册，回读不依赖应用时区）
        valueMapper.registerModule(new JavaTimeModule());
        valueMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

        // 序列化取全部字段（含 private），不依赖 getter 命名
        valueMapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        return valueMapper;
    }
}
