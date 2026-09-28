/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisClient3rd;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.demo.DemoRedisClient;
import com.openjiuwen.studio.agent.common.redis.demo.DemoRedisClientProvider;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Provider 解析工厂测试：配置解析优先级、ServiceLoader 插件加载、存量兼容与错误报文。
 */
class RedisClientProviderFactoryTest {

    private final RedisClientProviderFactory factory = new RedisClientProviderFactory();

    private RedisClientProviderConfig config(String type, String className, String legacyType) {
        RedisClientProviderConfig config = new RedisClientProviderConfig();
        config.setProviderType(type);
        config.setProviderClass(className);
        config.setLegacyClientType(legacyType);
        return config;
    }

    private RedisClientConfig clientConfig() {
        RedisClientConfig config = new RedisClientConfig(new Ciphers(null, null));
        config.setRedisHost("redis.test.host");
        config.setRedisPassword("secret");
        config.setRedisPort(6380);
        return config;
    }

    @Test
    void resolve_explicitClass_loadsProviderWithoutFrameworkChange() {
        RedisClientProvider provider = factory.resolve(
            config(null, DemoRedisClientProvider.class.getName(), null));

        assertEquals(DemoRedisClientProvider.NAME, provider.name());
    }

    @Test
    void resolve_providerType_serviceLoaderPluginWinsOverBuiltIn() {
        // demo-custom 仅通过 ServiceLoader 注册（test classpath META-INF/services）
        RedisClientProvider provider = factory.resolve(config("demo-custom", null, null));

        assertInstanceOf(DemoRedisClientProvider.class, provider);
    }

    @Test
    void resolve_providerType_builtinMemory() {
        RedisClientProvider provider = factory.resolve(config("memory", null, null));
        assertEquals(MemoryClientProvider.NAME, provider.name());
    }

    @Test
    void resolve_providerType_builtinRedisson_overridesLegacy3rd() {
        // 显式新式配置优先于存量 RedisClient3rd 兼容路径
        RedisClientProvider provider = factory.resolve(config("redisson", null, null));
        assertEquals(RedissonClientProvider.NAME, provider.name());
    }

    @Test
    void resolve_unknownProviderType_throwsWithAvailableNames() {
        IllegalStateException ex = assertThrows(IllegalStateException.class,
            () -> factory.resolve(config("not-registered", null, null)));

        assertTrue(ex.getMessage().contains("not-registered"));
        assertTrue(ex.getMessage().contains("redisson") && ex.getMessage().contains("memory"),
            "报错应包含可用 provider 标识列表: " + ex.getMessage());
    }

    @Test
    void resolve_classLoadFailure_throwsClearError() {
        assertThrows(IllegalStateException.class,
            () -> factory.resolve(config(null, "com.not.exists.Provider", null)));
    }

    @Test
    void resolve_classNotProvider_throwsClearError() {
        assertThrows(IllegalStateException.class,
            () -> factory.resolve(config(null, "java.lang.String", null)));
    }

    @Test
    void resolve_legacyClientTypeMemory() {
        RedisClientProvider provider = factory.resolve(config(null, null, "memory"));
        assertEquals(MemoryClientProvider.NAME, provider.name());
    }

    @Test
    void resolve_noNewConfig_fallsBackToLegacy3rd() {
        // classpath 存在 RedisClient3rd（测试替身）且未配置新式 provider → 兼容启用
        RedisClientProvider provider = factory.resolve(config(null, null, "redisson"));
        assertEquals(RedisClientProviderFactory.LegacyThirdPartyClientProvider.NAME, provider.name());
    }

    @Test
    void resolve_noConfigNoLegacy3rd_defaultsToRedisson() {
        RedisClientProviderFactory factoryWithout3rd = new RedisClientProviderFactory() {
            @Override
            protected boolean isLegacy3rdAvailable() {
                return false;
            }
        };

        RedisClientProvider provider = factoryWithout3rd.resolve(config(null, null, null));
        assertEquals(RedissonClientProvider.NAME, provider.name());
        provider = factoryWithout3rd.resolve(config(null, null, "redisson"));
        assertEquals(RedissonClientProvider.NAME, provider.name());
    }

    @Test
    void createClient_legacy3rd_constructsWithHostPasswordPort() {
        RedisClientConfig redisConfig = clientConfig();
        RedisClient client = factory.createClient(config(null, null, "redisson"), redisConfig);

        assertInstanceOf(RedisClient3rd.class, client);
        assertEquals("redis.test.host:6380:secret", RedisClient3rd.CONSTRUCTED.get(
            RedisClient3rd.CONSTRUCTED.size() - 1));
    }

    @Test
    void createClient_providerTypeDemo() {
        RedisClient client = factory.createClient(config("demo-custom", null, "redisson"), clientConfig());
        DemoRedisClient demo = assertInstanceOf(DemoRedisClient.class, client);
        demo.set("tck", "value");
        assertEquals("value", demo.get("tck"));
        assertEquals(1, demo.getWriteOps());
    }
}
