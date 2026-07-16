/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.support.DefaultListableBeanFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.ArrayList;
import java.util.List;

@Configuration
@ConditionalOnProperty(name = "storage.type", havingValue = "CUSTOM")
@EnableConfigurationProperties(StorageProperties.class)
@Slf4j
public class CustomStorageAutoConfiguration {

    @Bean
    public FileStore storageService(StorageProperties properties, ConfigurableApplicationContext context) {
        String className = properties.getCustomClass();
        if (className == null || className.isEmpty()) {
            throw new IllegalArgumentException("storage.custom-class must be specified when storage.type=CUSTOM");
        }

        try {
            ClassLoader classLoader = buildClassLoader(properties.getCustomClasspath());
            log.info("Loading custom FileStore: {}, classpath: {}", className, properties.getCustomClasspath());
            Class<?> clazz = Class.forName(className, true, classLoader);

            if (!FileStore.class.isAssignableFrom(clazz)) {
                throw new IllegalArgumentException("Class " + className + " does not implement FileStore interface");
            }

            @SuppressWarnings("unchecked")
            Class<? extends FileStore> storageClass = (Class<? extends FileStore>) clazz;

            FileStore instance = storageClass.getDeclaredConstructor().newInstance();

            DefaultListableBeanFactory beanFactory = (DefaultListableBeanFactory) context.getBeanFactory();
            beanFactory.autowireBean(instance);

            log.info("Custom FileStore initialized: {}", className);
            return instance;
        } catch (ClassNotFoundException e) {
            throw new IllegalArgumentException(
                "Custom FileStore class not found: " + className
                + ". Check storage.custom-class and storage.custom-classpath settings.", e);
        } catch (NoSuchMethodException e) {
            throw new IllegalStateException(
                "Custom FileStore must have a no-arg constructor: " + className, e);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load custom FileStore: " + className, e);
        }
    }

    private ClassLoader buildClassLoader(String customClasspath) {
        ClassLoader parent = getClass().getClassLoader();
        if (customClasspath == null || customClasspath.isEmpty()) {
            return parent;
        }

        String[] paths = customClasspath.split(File.pathSeparator);
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
}
