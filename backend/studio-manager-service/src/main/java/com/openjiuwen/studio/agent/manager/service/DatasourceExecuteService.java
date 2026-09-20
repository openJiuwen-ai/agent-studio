/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.DatasourceExecuteResp;

import com.zaxxer.hikari.HikariDataSource;

import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Pattern;

@Slf4j
@Service
public class DatasourceExecuteService implements IDatasourceExecuteService {

    private final DatasourceConnectionFactory connectionFactory;

    @Value("${datasource.execute.timeout:25}")
    private int executeTimeout;

    @Value("${datasource.execute.max-response:1000}")
    private int maxResponse;

    @Value("${datasource.execute.sql-limit:8000}")
    private int sqlLimit;

    @Value("${datasource.execute.allowed-operations:SELECT,INSERT,UPDATE}")
    private String allowedOperations;

    private static final Pattern COMMENT_PATTERN = Pattern.compile("--|/\\*|\\*/");
    private static final Pattern CONDITION_INJECTION_PATTERN =
        Pattern.compile("\\bOR\\s+1\\s*=\\s*1\\b|\\bAND\\s+1\\s*=\\s*1\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern HEX_PATTERN = Pattern.compile("0x[0-9a-fA-F]+");
    private static final Pattern DANGEROUS_FUNCTIONS_PATTERN =
        Pattern.compile("\\bLOAD_FILE\\b|\\bINTO\\s+OUTFILE\\b|\\bSLEEP\\b|\\bBENCHMARK\\b",
            Pattern.CASE_INSENSITIVE);

    public DatasourceExecuteService(DatasourceConnectionFactory connectionFactory) {
        this.connectionFactory = connectionFactory;
    }

    public DatasourceExecuteResp executeSql(String datasourceId, String query, List<String> conditions) {
        validateSqlStatement(query);

        HikariDataSource dataSource = connectionFactory.getConnectionPool(datasourceId);
        return doExecute(query, dataSource, conditions);
    }

    private void validateSqlStatement(String query) {
        if (query == null || query.trim().isEmpty()) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION, "empty sql");
        }

        if (query.length() > sqlLimit) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                "sql exceeds max length: " + sqlLimit);
        }

        String trimmedQuery = query.trim();
        if (trimmedQuery.contains(";")) {
            if (trimmedQuery.indexOf(';') != trimmedQuery.length() - 1
                || trimmedQuery.substring(0, trimmedQuery.length() - 1).contains(";")) {
                throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                    "multiple statements not allowed");
            }
        }

        String upperQuery = trimmedQuery.toUpperCase(Locale.ROOT);
        String[] allowedOps = allowedOperations.split(",");
        boolean isAllowed = false;
        for (String op : allowedOps) {
            if (upperQuery.startsWith(op.trim().toUpperCase(Locale.ROOT))) {
                isAllowed = true;
                break;
            }
        }
        if (!isAllowed) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                "operation not allowed, only " + allowedOperations + " permitted");
        }

        if (COMMENT_PATTERN.matcher(query).find()) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                "sql comments not allowed");
        }

        if (CONDITION_INJECTION_PATTERN.matcher(query).find()) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                "condition injection detected");
        }

        if (HEX_PATTERN.matcher(query).find()) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                "hexadecimal encoding not allowed");
        }

        if (DANGEROUS_FUNCTIONS_PATTERN.matcher(query).find()) {
            throw new AgentStudioException(StudioError.DATASOURCE_SQL_SECURITY_VIOLATION,
                "dangerous function detected");
        }
    }

    private DatasourceExecuteResp doExecute(String query, HikariDataSource dataSource, List<String> conditions) {
        DatasourceExecuteResp resp = new DatasourceExecuteResp();
        try (Connection connection = dataSource.getConnection()) {
            try (PreparedStatement statement = connection.prepareStatement(query)) {
                if (conditions != null && !conditions.isEmpty()) {
                    AtomicInteger index = new AtomicInteger(1);
                    for (String condition : conditions) {
                        statement.setString(index.getAndIncrement(), condition);
                    }
                }

                statement.setQueryTimeout(executeTimeout);

                String upperQuery = query.trim().toUpperCase(Locale.ROOT);
                if (upperQuery.startsWith("SELECT")) {
                    try (ResultSet rs = statement.executeQuery()) {
                        convertResultSetToResp(rs, resp);
                    }
                } else {
                    int affectedRows = statement.executeUpdate();
                    Map<String, Object> result = new HashMap<>();
                    result.put("affectedRows", affectedRows);
                    resp.getOutputList().add(result);
                }

                resp.setRowNum(resp.getOutputList().size());
                return resp;
            }
        } catch (SQLException e) {
            log.error("execute sql failed: {}", e.getMessage());
            throw new AgentStudioException(StudioError.DATASOURCE_EXECUTE_FAILED, e.getMessage());
        }
    }

    private void convertResultSetToResp(ResultSet rs, DatasourceExecuteResp resp) throws SQLException {
        ResultSetMetaData metaData = rs.getMetaData();
        int columnCount = metaData.getColumnCount();
        int rowCount = 0;
        while (rs.next() && rowCount < maxResponse) {
            Map<String, Object> row = new HashMap<>();
            for (int i = 1; i <= columnCount; i++) {
                String columnName = metaData.getColumnLabel(i);
                String columnType = metaData.getColumnTypeName(i);
                if ("BIGINT".equalsIgnoreCase(columnType)
                    || "NUMERIC".equalsIgnoreCase(columnType)
                    || "DECIMAL".equalsIgnoreCase(columnType)) {
                    row.put(columnName, rs.getString(i));
                } else {
                    row.put(columnName, rs.getObject(i));
                }
            }
            resp.getOutputList().add(row);
            rowCount++;
        }
    }
}
