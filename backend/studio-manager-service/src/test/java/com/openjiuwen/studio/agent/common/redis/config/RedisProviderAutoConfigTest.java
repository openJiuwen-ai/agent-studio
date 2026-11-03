/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.common.redis.config;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisClientWrapper;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * 单点装配验证：redisClient Bean 经 RedisProviderResolver 解析，
 * 覆盖缺省 redisson、memory、custom 无实现、未知 provider-class 四条路径。
 */
@MockitoSettings(strictness = Strictness.LENIENT)
class RedisProviderAutoConfigTest {
    @InjectMocks
    private RedisProviderAutoConfig redisProviderAutoConfig;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(redisProviderAutoConfig, "enableLog", true);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_redisClient_default_redisson_should_return_not_null() throws Exception {
        try (MockedStatic<Redisson> mockedStaticRedisson = mockStatic(Redisson.class, RETURNS_DEEP_STUBS)) {
            // Given
            RedissonClient redissonClient = mock(RedissonClient.class, Answers.RETURNS_DEEP_STUBS);
            mockedStaticRedisson.when(() -> Redisson.create(any(Config.class))).thenReturn(redissonClient);

            RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));
            redisClientConfig.setClientType("redisson");

            // When
            RedisClient result = redisProviderAutoConfig.redisClient(redisClientConfig);

            // Then
            assertNotNull(result);
            assertTrue(result instanceof RedisClientWrapper);
        }
    }

    @Test
    void test_redisClient_memory_should_return_not_null() {
        // Given
        RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));
        redisClientConfig.setClientType("memory");

        // When
        RedisClient result = redisProviderAutoConfig.redisClient(redisClientConfig);

        // Then
        assertNotNull(result);
        assertTrue(result instanceof RedisClientWrapper);
    }

    @Test
    void test_redisClient_custom_without_factory_should_throw_with_hint() {
        // Given（classpath 上无任何 RedisProviderFactory 实现）
        RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));
        redisClientConfig.setClientType("custom");

        // When / Then（报错须自描述注入方式）
        RedisProviderException ex = assertThrows(RedisProviderException.class,
            () -> redisProviderAutoConfig.redisClient(redisClientConfig));
        assertTrue(ex.getMessage().contains("RedisProviderFactory"));
        assertTrue(ex.getMessage().contains("provider-class"));
    }

    @Test
    void test_redisClient_unknown_provider_class_should_throw_with_available_names() {
        // Given
        RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));
        redisClientConfig.setClientType("custom");
        redisClientConfig.setProviderClass("com.example.not.exists.RedisProvider");

        // When / Then（报错须列出可用实现名）
        RedisProviderException ex = assertThrows(RedisProviderException.class,
            () -> redisProviderAutoConfig.redisClient(redisClientConfig));
        assertTrue(ex.getMessage().contains("不存在"));
        assertTrue(ex.getMessage().contains("redisson"));
    }
}
