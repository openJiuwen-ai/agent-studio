/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.space.app.config;

import lombok.extern.slf4j.Slf4j;

import org.apache.ibatis.mapping.DatabaseIdProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Slf4j
@Configuration
public class RdsDatasourceConfiguration {

    @Bean
    public DatabaseIdProvider databaseIdProvider() {
        return new JdbcUrlDatabaseIdProvider();
    }
}
