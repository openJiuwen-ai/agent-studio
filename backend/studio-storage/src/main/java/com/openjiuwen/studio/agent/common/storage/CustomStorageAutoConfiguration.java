/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import com.openjiuwen.studio.agent.common.common.ExternalJarLoader;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConditionalOnProperty(name = "storage.type", havingValue = "CUSTOM")
@EnableConfigurationProperties(StorageProperties.class)
public class CustomStorageAutoConfiguration {

    @Bean
    public FileStore storageService(StorageProperties properties, ConfigurableApplicationContext context) {
        String className = properties.getCustomClass();
        if (className == null || className.isEmpty()) {
            throw new IllegalArgumentException("storage.custom-class must be specified when storage.type=CUSTOM");
        }

        ClassLoader classLoader = ExternalJarLoader.buildClassLoaderFromClasspath(properties.getCustomClasspath());

        return ExternalJarLoader.loadAndInject(className, FileStore.class, classLoader, context);
    }
}
