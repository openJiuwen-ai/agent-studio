/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.utils.redis.config;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientAutoConfig;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;

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
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.util.ReflectionTestUtils;

@MockitoSettings(strictness = Strictness.LENIENT)
class RedisClientAutoConfigTest {
    @InjectMocks
    private RedisClientAutoConfig redisClientAutoConfig;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(redisClientAutoConfig, "enableLog", true);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_redissionClient_should_return_not_null() throws Exception {
        try (MockedStatic<Redisson> mockedStaticRedisson = mockStatic(Redisson.class, RETURNS_DEEP_STUBS)) {
            // Given
            RedissonClient redissonClient = mock(RedissonClient.class, Answers.RETURNS_DEEP_STUBS);
            mockedStaticRedisson.when(() -> Redisson.create(any(Config.class))).thenReturn(redissonClient);

            RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));

            // When
            RedisClient result = redisClientAutoConfig.redissionClient(redisClientConfig);

            // Then
            assertNotNull(result);
        }
    }

    @Test
    void test_redissionClient_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            try (MockedStatic<Redisson> mockedStaticRedisson = mockStatic(Redisson.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticRedisson.when(() -> Redisson.create(any(Config.class))).thenReturn(null);

                // When
                RedisClient result = redisClientAutoConfig.redissionClient(null);
            }
        });
    }

    @Test
    void test_memoryClient_should_return_not_null() throws Exception {

        // When
        RedisClient result = redisClientAutoConfig.memoryClient();

        // Then
        assertNotNull(result);
    }

    @Test
    void test_redisTemplate_should_return_not_null() throws Exception {
        // Given
        RedisConnectionFactory redisConnectionFactory = mock(RedisConnectionFactory.class, Answers.RETURNS_DEEP_STUBS);

        // When
        RedisTemplate<String, Object> result = redisClientAutoConfig.redisTemplate(redisConnectionFactory);

        // Then
        assertNotNull(result.getConnectionFactory());
    }
}
