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
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProviderConfig;

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

    private RedisClientProviderConfig providerConfig(String type, String className, String legacyType) {
        RedisClientProviderConfig config = new RedisClientProviderConfig();
        config.setProviderType(type);
        config.setProviderClass(className);
        config.setLegacyClientType(legacyType);
        return config;
    }

    @Test
    void test_redisClient_providerTypeRedisson_should_return_not_null() throws Exception {
        try (MockedStatic<Redisson> mockedStaticRedisson = mockStatic(Redisson.class, RETURNS_DEEP_STUBS)) {
            // Given
            RedissonClient redissonClient = mock(RedissonClient.class, Answers.RETURNS_DEEP_STUBS);
            mockedStaticRedisson.when(() -> Redisson.create(any(Config.class))).thenReturn(redissonClient);

            RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));

            // When：新式配置 redis.provider.type=redisson
            RedisClient result = redisClientAutoConfig.redisClient(
                providerConfig("redisson", null, null), redisClientConfig);

            // Then
            assertNotNull(result);
        }
    }

    @Test
    void test_redisClient_providerTypeMemory_should_return_not_null() throws Exception {
        RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));

        // When：新式配置 redis.provider.type=memory
        RedisClient result = redisClientAutoConfig.redisClient(
            providerConfig("memory", null, null), redisClientConfig);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_redisClient_legacyClientTypeMemory_should_return_not_null() throws Exception {
        RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));

        // When：存量配置 redis.client-type=memory（未配置 provider.type/class）
        RedisClient result = redisClientAutoConfig.redisClient(
            providerConfig(null, null, "memory"), redisClientConfig);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_redisClient_unknownProviderType_should_throw_clear_error() throws Exception {
        RedisClientConfig redisClientConfig = new RedisClientConfig(new Ciphers(null, null));

        // When / Then：未注册的 provider 标识应报清晰错误
        assertThrows(IllegalStateException.class,
            () -> redisClientAutoConfig.redisClient(providerConfig("not-exists", null, null), redisClientConfig));
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
