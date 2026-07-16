/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.storage;

import lombok.extern.slf4j.Slf4j;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConditionalOnProperty(name = "storage.type", havingValue = "LOCAL", matchIfMissing = false)
@EnableConfigurationProperties(StorageProperties.class)
@Slf4j
public class LocalStorageAutoConfiguration {

    @Bean
    public FileStore storageService(StorageProperties properties) {
        log.info("Initializing Local StorageService, basePath: {}", properties.getLocal().getBasePath());
        return new LocalFileStoreImpl(properties.getLocal());
    }
}
