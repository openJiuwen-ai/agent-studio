/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.config;

import lombok.extern.slf4j.Slf4j;

import org.apache.ibatis.mapping.DatabaseIdProvider;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 功能描述
 *
 */
@Slf4j
@Configuration
@MapperScan(value = {
    "com.openjiuwen.studio.agent.manager.mapper", "com.openjiuwen.studio.prompt.engineering.mapper",
    "com.openjiuwen.studio.common.service.mapper"
})
public class RdsDatasourceConfiguration {

    /**
     * databaseIdProvider — 通过 JDBC URL 区分 openGauss / PostgreSQL / MySQL
     *
     * @return DatabaseIdProvider
     */
    @Bean
    public DatabaseIdProvider databaseIdProvider() {
        return new JdbcUrlDatabaseIdProvider();
    }

    public static class RdsAuthInfo {
        private String username;

        private String password;

        public RdsAuthInfo() {
        }

        public RdsAuthInfo(String username, String password) {
            this.username = username;
            this.password = password;
        }

        public String getUsername() {
            return username;
        }

        public void setUsername(String username) {
            this.username = username;
        }

        public String getPassword() {
            return password;
        }

        public void setPassword(String password) {
            this.password = password;
        }
    }
}
