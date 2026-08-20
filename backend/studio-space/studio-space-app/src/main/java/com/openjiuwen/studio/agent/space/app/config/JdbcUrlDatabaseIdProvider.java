/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.space.app.config;

import lombok.extern.slf4j.Slf4j;

import org.apache.ibatis.mapping.DatabaseIdProvider;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Properties;

/**
 * 通过 JDBC URL 区分 openGauss / PostgreSQL / MySQL。
 * openGauss 驱动报告 DatabaseProductName 为 "PostgreSQL"，无法用 VendorDatabaseIdProvider 区分。
 * openGauss MySQL 兼容模式使用 MySQL 语法，因此映射为 "mysql"。
 */
@Slf4j
public class JdbcUrlDatabaseIdProvider implements DatabaseIdProvider {

    private Properties properties;

    @Override
    public void setProperties(Properties p) {
        this.properties = p;
    }

    @Override
    public String getDatabaseId(DataSource dataSource) throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            String url = conn.getMetaData().getURL();
            log.info("JdbcUrlDatabaseIdProvider: JDBC URL = {}", url);
            if (url != null) {
                if (url.contains("opengauss")) {
                    return "mysql";
                }
                if (url.contains("postgresql")) {
                    return "postgres";
                }
                if (url.contains("mysql") || url.contains("mariadb")) {
                    return "mysql";
                }
            }
            String productName = conn.getMetaData().getDatabaseProductName();
            log.info("JdbcUrlDatabaseIdProvider: fallback to product name = {}", productName);
            if (properties != null) {
                for (String key : properties.stringPropertyNames()) {
                    if (productName.contains(key)) {
                        return properties.getProperty(key);
                    }
                }
            }
            return null;
        }
    }
}
