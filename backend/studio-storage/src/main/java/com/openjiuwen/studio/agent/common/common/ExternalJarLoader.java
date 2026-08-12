/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.common;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.config.AutowireCapableBeanFactory;
import org.springframework.context.ConfigurableApplicationContext;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.List;

/**
 * 外部 JAR 加载工具类，提供统一的 ClassLoader 构建和反射实例化能力。
 *
 * <p>通过 {@link #buildClassLoaderFromClasspath} 解析路径分隔符分隔的 JAR/目录列表构建 URLClassLoader，
 * 通过 {@link #loadAndInject} 统一完成反射实例化和 Spring 依赖注入。</p>
 */
@Slf4j
public final class ExternalJarLoader {

    private ExternalJarLoader() {
    }

    /**
     * 解析路径分隔符分隔的路径列表构建 URLClassLoader。
     *
     * @param classpath 路径分隔符分隔的 JAR/目录路径
     * @return 包含所有有效路径的 ClassLoader，路径无效时返回父 ClassLoader
     */
    public static ClassLoader buildClassLoaderFromClasspath(String classpath) {
        ClassLoader parent = ExternalJarLoader.class.getClassLoader();
        if (classpath == null || classpath.isEmpty()) {
            return parent;
        }

        String[] paths = classpath.split(File.pathSeparator);
        List<URL> urls = new ArrayList<>();
        for (String path : paths) {
            File file = new File(path.trim());
            if (!file.exists()) {
                log.warn("Custom classpath entry does not exist: {}", path);
                continue;
            }
            try {
                urls.add(file.toURI().toURL());
                log.info("Added custom classpath entry: {}", path);
            } catch (Exception e) {
                log.warn("Failed to add classpath entry: {}", path, e);
            }
        }

        if (urls.isEmpty()) {
            return parent;
        }

        return new URLClassLoader(urls.toArray(new URL[0]), parent);
    }

    /**
     * 通过反射加载并实例化指定类，同时完成 Spring 依赖注入。
     *
     * @param className       实现类全限定名
     * @param interfaceType   期望实现的接口类型
     * @param classLoader     用于加载类的 ClassLoader
     * @param context         Spring 上下文，用于依赖注入
     * @param <T>             接口类型
     * @return 实例化并注入完成的对象
     * @throws IllegalArgumentException 类未找到或未实现指定接口
     * @throws IllegalStateException    实例化失败
     */
    public static <T> T loadAndInject(String className, Class<T> interfaceType,
        ClassLoader classLoader, ConfigurableApplicationContext context) {
        try {
            log.info("Loading custom {}: {}", interfaceType.getSimpleName(), className);
            Class<?> clazz = Class.forName(className, true, classLoader);

            if (!interfaceType.isAssignableFrom(clazz)) {
                throw new IllegalArgumentException(
                    "Class " + className + " does not implement " + interfaceType.getName() + " interface");
            }

            @SuppressWarnings("unchecked")
            Class<? extends T> implClass = (Class<? extends T>) clazz;

            T instance = implClass.getDeclaredConstructor().newInstance();

            AutowireCapableBeanFactory beanFactory = context.getAutowireCapableBeanFactory();
            beanFactory.autowireBean(instance);
            beanFactory.initializeBean(instance, className);

            log.info("Custom {} initialized: {}", interfaceType.getSimpleName(), className);
            return instance;
        } catch (ClassNotFoundException e) {
            throw new IllegalArgumentException(
                "Custom " + interfaceType.getSimpleName() + " class not found: " + className, e);
        } catch (NoSuchMethodException e) {
            throw new IllegalStateException(
                "Custom " + interfaceType.getSimpleName() + " must have a no-arg constructor: " + className, e);
        } catch (Exception e) {
            throw new IllegalStateException(
                "Failed to load custom " + interfaceType.getSimpleName() + ": " + className, e);
        }
    }
}
