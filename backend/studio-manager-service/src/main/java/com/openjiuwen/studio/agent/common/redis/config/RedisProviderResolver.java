/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.config;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderContext;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderException;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderFactory;

import lombok.extern.slf4j.Slf4j;

import org.springframework.util.StringUtils;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.ServiceLoader;
import java.util.stream.Collectors;

/**
 * Redis Provider 解析器——所有实现的唯一装配入口（替代 AutoConfig 多条件 Bean 分叉）。
 *
 * 解析优先级（高 → 低）：
 * 1. redis.provider-class 显式指定（全限定类名或 ServiceLoader 注册名）
 * 2. redis.client-type = custom → ServiceLoader 自动发现（classpath 仅一个 Provider 时自动选取）
 * 3. redis.client-type = memory（存量值，测试用）
 * 4. redis.client-type 显式 = redisson → 直接缺省实现（短路，不被 legacy 兼容覆盖）
 * 5. 存量 RedisClient3rd classpath 自动兼容（过渡期，仅在未显式指定实现时）
 * 6. redis.client-type = redisson（缺省）
 *
 * 名字解析失败必须自描述：报错列出全部可用实现名与注入方式提示。
 */
@Slf4j
public final class RedisProviderResolver {

    private static final String LEGACY_3RD_CLASS =
        "com.openjiuwen.studio.agent.common.redis.RedisClient3rd";

    private RedisProviderResolver() {
    }

    /**
     * 解析并创建 Redis 客户端（不含日志装饰，由调用方包装）。
     *
     * @param config Spring 管理的完整配置（含已解密密码；缺省 Redisson 路径直接使用）
     * @param context Provider 配置上下文（custom 路径使用；含企业专属参数透传）
     * @return RedisClient 客户端实例
     * @throws RedisProviderException 解析或创建失败
     */
    public static RedisClient resolve(RedisClientConfig config, RedisProviderContext context) {
        String providerClass = config.getProviderClass();
        String clientType = config.getClientType();

        // 1. 显式 provider-class（最高优先）
        if (StringUtils.hasText(providerClass)) {
            return createFromSpec(providerClass.trim(), context);
        }

        // 2. client-type = custom → ServiceLoader 自动发现
        if ("custom".equals(clientType)) {
            return createFromServiceLoader(context);
        }

        // 3. client-type = memory（存量值，测试用）
        if ("memory".equals(clientType)) {
            return createMemory();
        }

        // 4. 显式 redisson：短路，不被 classpath 上的存量 RedisClient3rd 自动兼容覆盖
        //    （operator 明确选择缺省实现时应尊重该选择；legacy 兼容仅兜未显式指定的场景）
        if ("redisson".equals(clientType)) {
            return createDefaultRedisson(config);
        }

        // 5. 存量 RedisClient3rd classpath 自动兼容（过渡期）
        if (isLegacyThirdPartyPresent()) {
            log.warn("检测到存量 RedisClient3rd 类，将自动兼容启用。"
                + "请迁移到 RedisProvider SPI（redis.provider-class 配置项）。");
            return createLegacyThirdParty(config);
        }

        // 6. 缺省 redisson（直接使用 Spring 管理的完整配置）
        return createDefaultRedisson(config);
    }

    /**
     * 获取全部可用实现名（用于报错自描述）。
     */
    public static List<String> getAvailableNames() {
        List<String> names = new ArrayList<>(List.of("redisson", "memory"));
        ServiceLoader<RedisProviderFactory> loader =
            ServiceLoader.load(RedisProviderFactory.class);
        loader.forEach(f -> names.add(f.getClass().getName()));
        return names;
    }

    // ---------------------------------------------------------------- internal

    private static RedisClient createFromSpec(String spec, RedisProviderContext context) {
        // 尝试 ServiceLoader 注册名解析
        RedisClient fromRegistry = tryServiceLoaderByName(spec, context);
        if (fromRegistry != null) {
            return fromRegistry;
        }
        // 尝试全限定类名反射加载
        return createByClassName(spec, context);
    }

    private static RedisClient createFromServiceLoader(RedisProviderContext context) {
        ServiceLoader<RedisProviderFactory> loader =
            ServiceLoader.load(RedisProviderFactory.class);
        List<RedisProviderFactory> factories = new ArrayList<>();
        loader.forEach(factories::add);

        if (factories.isEmpty()) {
            throw new RedisProviderException(
                "redis.client-type=custom 但 classpath 上未发现任何 RedisProviderFactory 实现。"
                + "请在 META-INF/services/"
                + RedisProviderFactory.class.getName()
                + " 中声明实现，或使用 redis.provider-class 显式指定类名。");
        }

        if (factories.size() == 1) {
            return createFromFactory(factories.get(0), context);
        }

        String available = factories.stream()
            .map(f -> f.getClass().getName())
            .collect(Collectors.joining(", "));
        throw new RedisProviderException(
            "redis.client-type=custom 且 classpath 上发现多个 RedisProviderFactory 实现（"
            + available + "），请使用 redis.provider-class 显式指定其中一个。");
    }

    private static RedisClient tryServiceLoaderByName(String name, RedisProviderContext context) {
        ServiceLoader<RedisProviderFactory> loader =
            ServiceLoader.load(RedisProviderFactory.class);
        for (RedisProviderFactory factory : loader) {
            String className = factory.getClass().getName();
            String simpleName = factory.getClass().getSimpleName();
            if (className.equals(name) || simpleName.equals(name)) {
                return createFromFactory(factory, context);
            }
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private static RedisClient createByClassName(String className, RedisProviderContext context) {
        Class<?> clazz;
        try {
            clazz = Class.forName(className);
        } catch (ClassNotFoundException e) {
            throw new RedisProviderException(
                "redis.provider-class 指定的类不存在: " + className
                + "。可用实现: " + getAvailableNames(), e);
        }

        // 优先：RedisProviderFactory 实现
        if (RedisProviderFactory.class.isAssignableFrom(clazz)) {
            try {
                RedisProviderFactory factory =
                    (RedisProviderFactory) clazz.getDeclaredConstructor().newInstance();
                return createFromFactory(factory, context);
            } catch (Exception e) {
                throw new RedisProviderException(
                    "RedisProviderFactory 实例化失败: " + className, e);
            }
        }

        // 兼容：直接实现 RedisClient 且带 init(RedisProviderContext)
        if (RedisClient.class.isAssignableFrom(clazz)) {
            return createBeanStyle(clazz, context);
        }

        throw new RedisProviderException(
            "redis.provider-class 指定的类 " + className
            + " 既不是 RedisProviderFactory 也不是 RedisClient 实现。");
    }

    private static RedisClient createBeanStyle(Class<?> clazz, RedisProviderContext context) {
        try {
            Object instance = clazz.getDeclaredConstructor().newInstance();
            try {
                Method initMethod = clazz.getMethod("init", RedisProviderContext.class);
                initMethod.invoke(instance, context);
            } catch (NoSuchMethodException e) {
                log.debug("类 {} 无 init(RedisProviderContext) 方法，跳过初始化调用",
                    clazz.getName());
            }
            return (RedisClient) instance;
        } catch (Exception e) {
            throw new RedisProviderException(
                "RedisClient Bean 风格实现实例化失败: " + clazz.getName(), e);
        }
    }

    private static RedisClient createFromFactory(RedisProviderFactory factory,
            RedisProviderContext context) {
        try {
            RedisClient client = factory.create(context);
            if (client == null) {
                throw new RedisProviderException(
                    "RedisProviderFactory.create() 返回 null: " + factory.getClass().getName());
            }
            log.info("Redis Provider 已装配: {}", factory.getClass().getName());
            return client;
        } catch (RedisProviderException e) {
            throw e;
        } catch (Exception e) {
            throw new RedisProviderException(
                "RedisProviderFactory.create() 失败: " + factory.getClass().getName(), e);
        }
    }

    private static RedisClient createMemory() {
        com.openjiuwen.studio.agent.common.redis.impl.RedisClientMemory memory =
            new com.openjiuwen.studio.agent.common.redis.impl.RedisClientMemory();
        log.info("Redis Provider 已装配: memory (测试用)");
        return memory;
    }

    private static boolean isLegacyThirdPartyPresent() {
        try {
            Class.forName(LEGACY_3RD_CLASS, false,
                RedisProviderResolver.class.getClassLoader());
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }

    private static RedisClient createLegacyThirdParty(RedisClientConfig config) {
        try {
            Class<?> clazz = Class.forName(LEGACY_3RD_CLASS);
            Constructor<?> constructor =
                clazz.getConstructor(String.class, String.class, int.class);
            RedisClient client = (RedisClient) constructor.newInstance(
                config.getRedisHost(), config.getRedisPassword(), config.getRedisPort());
            log.info("Redis Provider 已装配: legacy RedisClient3rd (兼容模式)");
            return client;
        } catch (Exception e) {
            throw new RedisProviderException("存量 RedisClient3rd 兼容加载失败", e);
        }
    }

    private static RedisClient createDefaultRedisson(RedisClientConfig config) {
        com.openjiuwen.studio.agent.common.redis.impl.RedisClientRedisson redisson =
            new com.openjiuwen.studio.agent.common.redis.impl.RedisClientRedisson(config);
        log.info("Redis Provider 已装配: redisson (缺省)");
        return redisson;
    }
}
