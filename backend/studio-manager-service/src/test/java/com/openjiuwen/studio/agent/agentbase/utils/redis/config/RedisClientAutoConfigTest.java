/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.utils.redis.config;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;

import com.openjiuwen.studio.agent.common.redis.config.RedisClientAutoConfig;

import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;

/**
 * RedisTemplate 第二栈装配验证（Q11 拍板：Bean 保留一版兜底，业务侧已零直用）。
 * RedisClient 主路径（Provider 单栈）的装配验证见
 * studio-manager-service 模块的 RedisProviderAutoConfigTest。
 */
@MockitoSettings(strictness = Strictness.LENIENT)
class RedisClientAutoConfigTest {

    @InjectMocks
    private RedisClientAutoConfig redisClientAutoConfig;

    @Test
    void test_redisTemplate_should_return_not_null() {
        // Given
        RedisConnectionFactory redisConnectionFactory = mock(RedisConnectionFactory.class, Answers.RETURNS_DEEP_STUBS);

        // When
        RedisTemplate<String, Object> result = redisClientAutoConfig.redisTemplate(redisConnectionFactory);

        // Then
        assertNotNull(result.getConnectionFactory());
    }
}
