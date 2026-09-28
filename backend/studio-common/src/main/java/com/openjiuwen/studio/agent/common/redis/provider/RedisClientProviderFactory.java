/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;

import lombok.extern.slf4j.Slf4j;

import java.lang.reflect.Constructor;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.ServiceLoader;

/**
 * Redis Provider 解析工厂。
 *
 * <p>解析优先级（高 → 低，见 {@link RedisClientProviderConfig} 契约）：
 * <ol>
 *   <li>{@code redis.provider.class}：显式实现类全限定名</li>
 *   <li>{@code redis.provider.type}：ServiceLoader 注册表（企业插件包）+ 内置注册表按名匹配，
 *       同名时 ServiceLoader 优先（允许覆盖内置实现）</li>
 *   <li>存量 {@code redis.client-type=memory}：内存实现</li>
 *   <li>存量 RedisClient3rd 扩展点（类在 classpath 且未配置新式 Provider 时兼容启用）</li>
 *   <li>默认 redisson</li>
 * </ol>
 *
 * <p>配置错误（类加载失败、标识未注册等）抛出 {@link IllegalStateException}，报错信息包含
 * 可用的 Provider 标识列表，便于部署排查。
 */
@Slf4j
public class RedisClientProviderFactory {
    /**
     * 存量第三方扩展点类名（构造签名固定 host/password/port，兼容保留）。
     */
    public static final String LEGACY_3RD_CLASS = "com.openjiuwen.studio.agent.common.redis.RedisClient3rd";

    private static final Map<String, RedisClientProvider> BUILT_IN_PROVIDERS = buildInProviders();

    /**
     * 按 {@link RedisClientProviderConfig} 契约解析 Provider。
     *
     * @param config provider 配置
     * @return 匹配的 Provider（非 null）
     * @throws IllegalStateException 配置错误或 Provider 加载失败
     */
    public RedisClientProvider resolve(RedisClientProviderConfig config) {
        RedisClientProviderConfig safeConfig = config == null ? new RedisClientProviderConfig() : config;

        // 1. 显式实现类
        String providerClass = trimToNull(safeConfig.getProviderClass());
        if (providerClass != null) {
            return loadByClassName(providerClass);
        }

        // 2. Provider 标识（ServiceLoader 注册表优先于内置注册表）
        String providerType = trimToNull(safeConfig.getProviderType());
        if (providerType != null) {
            return resolveByName(providerType);
        }

        // 3. 存量 client-type=memory（显式 memory 优先于 legacy 3rd 兼容）
        if (MemoryClientProvider.NAME.equalsIgnoreCase(trimToNull(safeConfig.getLegacyClientType()))) {
            return new MemoryClientProvider();
        }

        // 4. 存量 RedisClient3rd 扩展点兼容（类在 classpath 且未配置新式 Provider）
        if (isLegacy3rdAvailable()) {
            log.warn("RedisClient3rd legacy extension detected, "
                + "please migrate to RedisClientProvider SPI (see docs: redis-provider).");
            return new LegacyThirdPartyClientProvider();
        }

        // 5. 默认 redisson
        return new RedissonClientProvider();
    }

    /**
     * 创建客户端（便捷入口：解析 + 创建）。
     */
    public RedisClient createClient(RedisClientProviderConfig providerConfig, RedisClientConfig clientConfig) {
        RedisClientProvider provider = resolve(providerConfig);
        log.info("Redis client provider resolved: {}", provider.name());
        return provider.createClient(clientConfig);
    }

    /**
     * 按名解析：ServiceLoader 注册表（允许覆盖内置）→ 内置注册表。
     */
    private RedisClientProvider resolveByName(String name) {
        Map<String, RedisClientProvider> registered = loadServiceLoaderProviders();
        RedisClientProvider provider = registered.get(normalize(name));
        if (provider != null) {
            return provider;
        }
        provider = BUILT_IN_PROVIDERS.get(normalize(name));
        if (provider != null) {
            return provider;
        }
        throw new IllegalStateException("Unknown redis provider type: '" + name
            + "', registered providers: " + availableNames(registered)
            + ". Check config 'redis.provider.type' or register it via ServiceLoader"
            + " (META-INF/services/" + RedisClientProvider.class.getName() + ").");
    }

    private RedisClientProvider loadByClassName(String providerClass) {
        try {
            Class<?> clazz = Class.forName(providerClass);
            if (!RedisClientProvider.class.isAssignableFrom(clazz)) {
                throw new IllegalStateException("Class " + providerClass
                    + " does not implement " + RedisClientProvider.class.getName());
            }
            Constructor<?> constructor = clazz.getDeclaredConstructor();
            constructor.setAccessible(true);
            RedisClientProvider provider = (RedisClientProvider) constructor.newInstance();
            if (provider.name() == null || provider.name().isBlank()) {
                throw new IllegalStateException("Provider " + providerClass + " returns blank name()");
            }
            return provider;
        } catch (IllegalStateException e) {
            throw e;
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Failed to load redis provider class: " + providerClass
                + " (check 'redis.provider.class', requires public no-arg constructor)", e);
        }
    }

    private Map<String, RedisClientProvider> loadServiceLoaderProviders() {
        Map<String, RedisClientProvider> providers = new LinkedHashMap<>();
        try {
            for (RedisClientProvider provider : ServiceLoader.load(RedisClientProvider.class)) {
                providers.put(normalize(provider.name()), provider);
            }
        } catch (Throwable t) {
            throw new IllegalStateException("Failed to load RedisClientProvider via ServiceLoader, "
                + "check plugin jar and META-INF/services registration", t);
        }
        return providers;
    }

    /**
     * 存量 RedisClient3rd 扩展点是否可用（protected 便于测试覆写模拟无 3rd 场景）。
     */
    protected boolean isLegacy3rdAvailable() {
        try {
            Class.forName(LEGACY_3RD_CLASS, false, getClass().getClassLoader());
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }

    private String availableNames(Map<String, RedisClientProvider> registered) {
        var names = new java.util.ArrayList<>(registered.keySet());
        names.addAll(BUILT_IN_PROVIDERS.keySet());
        return names.toString();
    }

    private String normalize(String name) {
        return name == null ? "" : name.trim().toLowerCase();
    }

    private String trimToNull(String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }
        return value.trim();
    }

    private static Map<String, RedisClientProvider> buildInProviders() {
        Map<String, RedisClientProvider> providers = new LinkedHashMap<>();
        providers.put(RedissonClientProvider.NAME, new RedissonClientProvider());
        providers.put(MemoryClientProvider.NAME, new MemoryClientProvider());
        return providers;
    }

    /**
     * 存量 RedisClient3rd 扩展点适配器（构造签名固定 host/password/port，已废弃，建议迁移 SPI）。
     */
    static class LegacyThirdPartyClientProvider implements RedisClientProvider {
        static final String NAME = "legacy-3rd";

        @Override
        public String name() {
            return NAME;
        }

        @Override
        public RedisClient createClient(RedisClientConfig config) {
            try {
                Class<?> clazz = Class.forName(LEGACY_3RD_CLASS);
                Constructor<?> constructor = clazz.getConstructor(String.class, String.class, int.class);
                return (RedisClient) constructor.newInstance(config.getRedisHost(),
                    config.getRedisPassword(), config.getRedisPort());
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException("Failed to create legacy RedisClient3rd instance, "
                    + "constructor (String host, String password, int port) is required", e);
            }
        }
    }
}
