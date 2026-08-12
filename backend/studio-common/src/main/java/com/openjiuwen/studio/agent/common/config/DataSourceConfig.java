/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.config;

import com.openjiuwen.studio.agent.common.datasource.DataSourcePasswordProvider;

import com.zaxxer.hikari.HikariDataSource;

import lombok.extern.slf4j.Slf4j;

import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;

/**
 * 数据源配置，通过 {@link DataSourcePasswordProvider} 获取数据库密码。
 */
@Slf4j
@Configuration
public class DataSourceConfig {

    @Bean
    @Primary
    public DataSource dataSource(DataSourceProperties properties,
        DataSourcePasswordProvider passwordProvider) {
        HikariDataSource dataSource = properties.initializeDataSourceBuilder()
                .type(HikariDataSource.class)
                .build();
        String originalPassword = dataSource.getPassword();
        if (originalPassword != null && !originalPassword.isEmpty()) {
            String resolvedPassword = passwordProvider.getPassword(originalPassword);
            if (resolvedPassword == null) {
                log.warn("DataSourcePasswordProvider returned null, falling back to original password");
                resolvedPassword = originalPassword;
            }
            dataSource.setPassword(resolvedPassword);
        }
        return dataSource;
    }
}