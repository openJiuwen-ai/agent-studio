/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.dto.DatasourceConnectionInfo;
import com.openjiuwen.studio.agent.manager.entity.DatasourceEntity;
import com.openjiuwen.studio.agent.manager.mapper.DatasourceMapper;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;

import jakarta.annotation.PostConstruct;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class DatasourceConnectionFactory {

    private final DatasourceMapper datasourceMapper;

    private Cache<String, HikariDataSource> connectionPoolCache;

    @Value("${datasource.cache.hours:24}")
    private int cacheHours;

    @Value("${datasource.cache.pool-size:150}")
    private int cachePoolSize;

    @Value("${datasource.max-connections-per-host:5}")
    private int maxConnectionsPerHost;

    private static final Map<String, String> DB_TYPE_ALIASES = Map.of(
        "postgresql", "postgresql",
        "gaussdb", "opengauss"
    );

    public DatasourceConnectionFactory(DatasourceMapper datasourceMapper) {
        this.datasourceMapper = datasourceMapper;
    }

    @PostConstruct
    public void init() {
        connectionPoolCache = Caffeine.newBuilder()
            .maximumSize(cachePoolSize)
            .expireAfterAccess(cacheHours, TimeUnit.HOURS)
            .removalListener((key, value, cause) -> {
                if (value instanceof HikariDataSource hikari) {
                    hikari.close();
                }
            })
            .build();
    }

    public HikariDataSource getConnectionPool(String datasourceId) {
        return connectionPoolCache.get(datasourceId, this::createConnectionPool);
    }

    private HikariDataSource createConnectionPool(String datasourceId) {
        DatasourceEntity entity = datasourceMapper.getById(datasourceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NOT_FOUND, datasourceId);
        }

        DatasourceConnectionInfo connInfo = JsonUtils.json2ObjQuietly(
            entity.getConnectionInfo(), DatasourceConnectionInfo.class);
        if (connInfo == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID);
        }

        String password = CryptoUtils.decrypt(connInfo.getPassword());

        String dbType = entity.getType().toLowerCase();
        dbType = DB_TYPE_ALIASES.getOrDefault(dbType, dbType);

        String jdbcUrl = buildJdbcUrl(dbType, connInfo);

        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(jdbcUrl);
        config.setUsername(connInfo.getUser());
        config.setPassword(password);
        config.setMaximumPoolSize(maxConnectionsPerHost);
        config.setMinimumIdle(2);
        config.setIdleTimeout(300000);
        config.setMaxLifetime(1800000);
        config.setKeepaliveTime(120000);
        config.setConnectionTimeout(10000);
        config.setPoolName("datasource-" + datasourceId);

        configureDriver(config, dbType);

        log.info("create connection pool for datasource: {}, type: {}", datasourceId, dbType);
        return new HikariDataSource(config);
    }

    private String buildJdbcUrl(String dbType, DatasourceConnectionInfo connInfo) {
        return switch (dbType) {
            case "mysql" -> String.format("jdbc:mariadb://%s:%s/%s",
                connInfo.getHost(), connInfo.getPort(), connInfo.getDatabaseName());
            case "postgresql" -> String.format("jdbc:postgresql://%s:%s/%s",
                connInfo.getHost(), connInfo.getPort(), connInfo.getDatabaseName());
            case "opengauss" -> String.format("jdbc:opengauss://%s:%s/%s",
                connInfo.getHost(), connInfo.getPort(), connInfo.getDatabaseName());
            default -> throw new AgentStudioException(StudioError.DATASOURCE_TYPE_UNSUPPORTED, dbType);
        };
    }

    private void configureDriver(HikariConfig config, String dbType) {
        switch (dbType) {
            case "mysql" -> {
                config.setDriverClassName("org.mariadb.jdbc.Driver");
                config.addDataSourceProperty("allowLoadLocalInfile", "false");
                config.addDataSourceProperty("allowUrlInLocalInfile", "false");
            }
            case "postgresql" -> config.setDriverClassName("org.postgresql.Driver");
            case "opengauss" -> config.setDriverClassName("com.huawei.opengauss.jdbc.Driver");
        }
    }

    public void removeConnectionPool(String datasourceId) {
        connectionPoolCache.invalidate(datasourceId);
    }
}
