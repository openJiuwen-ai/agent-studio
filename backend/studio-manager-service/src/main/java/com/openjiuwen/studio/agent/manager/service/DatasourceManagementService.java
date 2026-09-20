/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.DatasourceBatchDeleteReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceConnectionInfo;
import com.openjiuwen.studio.agent.manager.dto.DatasourceExecuteResp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceInfoReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceInfoRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceListRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceTableColumnsRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceTablesRsp;
import com.openjiuwen.studio.agent.manager.entity.DatasourceEntity;
import com.openjiuwen.studio.agent.manager.mapper.DatasourceMapper;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
public class DatasourceManagementService implements IDatasourceManagementService {

    private static final String PASSWORD_MASK = "******";
    private static final String STATUS_AVAILABLE = "AVAILABLE";
    private static final String STATUS_UNAVAILABLE = "UNAVAILABLE";

    private final DatasourceMapper datasourceMapper;
    private final DatasourceExecuteService executeService;
    private final DatasourceConnectionFactory connectionFactory;

    public DatasourceManagementService(DatasourceMapper datasourceMapper,
                                      DatasourceExecuteService executeService,
                                      DatasourceConnectionFactory connectionFactory) {
        this.datasourceMapper = datasourceMapper;
        this.executeService = executeService;
        this.connectionFactory = connectionFactory;
    }

    public DatasourceBriefRsp createDatasource(String projectId, String workspaceId, DatasourceInfoReq req) {
        DatasourceEntity existing = datasourceMapper.getByNameAndWorkspaceId(
            req.getName(), projectId, workspaceId);
        if (existing != null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NAME_DUPLICATE, req.getName());
        }

        validateConnectionInfo(req.getConnectionInfo());

        String currentUser = RequestContextUtils.getRequestUserName();
        DatasourceEntity entity = new DatasourceEntity()
            .setId(UUID.randomUUID().toString().replace("-", ""))
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setName(req.getName())
            .setType(req.getType())
            .setDesc(req.getDesc())
            .setCreatedBy(currentUser)
            .setUpdatedBy(currentUser);

        DatasourceConnectionInfo connInfo = req.getConnectionInfo();
        connInfo.setPassword(CryptoUtils.encrypt(connInfo.getPassword()));
        entity.setConnectionInfo(JsonUtils.toJson(connInfo));

        String status = STATUS_UNAVAILABLE;
        String lastError = null;
        try {
            datasourceMapper.insert(entity);
            DatasourceExecuteResp resp = executeService.executeSql(entity.getId(), "SELECT 1", null);
            status = resp.getRowNum() >= 0 ? STATUS_AVAILABLE : STATUS_UNAVAILABLE;
        } catch (Exception e) {
            log.error("datasource connectivity check failed: {}", e.getMessage());
            lastError = e.getMessage();
        }
        entity.setStatus(status);
        entity.setLastErrorMessage(lastError);
        datasourceMapper.update(entity);

        return toBriefRsp(entity);
    }

    public DatasourceBriefRsp modifyDatasource(String projectId, String workspaceId,
                                                 String datasourceId, DatasourceInfoReq req) {
        DatasourceEntity entity = datasourceMapper.getByPrimaryKeyAndWorkspaceId(
            datasourceId, projectId, workspaceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NOT_FOUND, datasourceId);
        }

        if (StringUtils.isNotEmpty(req.getName()) && !req.getName().equals(entity.getName())) {
            DatasourceEntity existing = datasourceMapper.getByNameAndWorkspaceId(
                req.getName(), projectId, workspaceId);
            if (existing != null) {
                throw new AgentStudioException(StudioError.DATASOURCE_NAME_DUPLICATE, req.getName());
            }
            entity.setName(req.getName());
        }

        if (StringUtils.isNotEmpty(req.getType())) {
            entity.setType(req.getType());
        }
        if (req.getDesc() != null) {
            entity.setDesc(req.getDesc());
        }

        if (req.getConnectionInfo() != null) {
            DatasourceConnectionInfo connInfo = req.getConnectionInfo();
            if (PASSWORD_MASK.equals(connInfo.getPassword())) {
                DatasourceConnectionInfo oldConn = JsonUtils.json2ObjQuietly(
                    entity.getConnectionInfo(), DatasourceConnectionInfo.class);
                connInfo.setPassword(oldConn.getPassword());
            } else {
                validateConnectionInfo(connInfo);
                connInfo.setPassword(CryptoUtils.encrypt(connInfo.getPassword()));
            }
            entity.setConnectionInfo(JsonUtils.toJson(connInfo));
            connectionFactory.removeConnectionPool(datasourceId);
        }

        String status = STATUS_UNAVAILABLE;
        String lastError = null;
        try {
            DatasourceExecuteResp resp = executeService.executeSql(datasourceId, "SELECT 1", null);
            status = resp.getRowNum() >= 0 ? STATUS_AVAILABLE : STATUS_UNAVAILABLE;
        } catch (Exception e) {
            log.error("datasource connectivity check failed: {}", e.getMessage());
            lastError = e.getMessage();
        }
        entity.setStatus(status);
        entity.setLastErrorMessage(lastError);
        entity.setUpdatedBy(RequestContextUtils.getRequestUserName());

        datasourceMapper.update(entity);
        return toBriefRsp(entity);
    }

    public void deleteDatasource(String projectId, String workspaceId, String datasourceId) {
        DatasourceEntity entity = datasourceMapper.getByPrimaryKeyAndWorkspaceId(
            datasourceId, projectId, workspaceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NOT_FOUND, datasourceId);
        }
        datasourceMapper.deleteById(datasourceId, projectId, workspaceId);
        connectionFactory.removeConnectionPool(datasourceId);
    }

    public void batchDeleteDatasource(String projectId, String workspaceId, DatasourceBatchDeleteReq req) {
        if (req.getDatasourceIds() == null || req.getDatasourceIds().isEmpty()) {
            return;
        }
        for (String id : req.getDatasourceIds()) {
            try {
                deleteDatasource(projectId, workspaceId, id);
            } catch (Exception e) {
                log.warn("delete datasource {} failed: {}", id, e.getMessage());
            }
        }
    }

    public DatasourceListRsp listDatasource(String projectId, String workspaceId,
                                            int page, int pageSize,
                                            String name, String type, String status) {
        int offset = (page - 1) * pageSize;
        List<DatasourceEntity> entities = datasourceMapper.listDatasource(
            projectId, workspaceId, name, type, status, offset, pageSize);
        int total = datasourceMapper.countDatasource(projectId, workspaceId, name, type, status);

        DatasourceListRsp rsp = new DatasourceListRsp();
        rsp.setTotal(total);
        rsp.setDatasources(entities.stream()
            .map(this::toInfoRsp)
            .collect(Collectors.toList()));
        return rsp;
    }

    public DatasourceInfoRsp retrieveDatasource(String projectId, String workspaceId, String datasourceId) {
        DatasourceEntity entity = datasourceMapper.getByPrimaryKeyAndWorkspaceId(
            datasourceId, projectId, workspaceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NOT_FOUND, datasourceId);
        }
        return toInfoRsp(entity);
    }

    public DatasourceTablesRsp retrieveTables(String projectId, String workspaceId, String datasourceId) {
        DatasourceEntity entity = datasourceMapper.getByPrimaryKeyAndWorkspaceId(
            datasourceId, projectId, workspaceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NOT_FOUND, datasourceId);
        }
        DatasourceConnectionInfo connInfo = JsonUtils.json2ObjQuietly(
            entity.getConnectionInfo(), DatasourceConnectionInfo.class);
        String sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = ?";
        DatasourceExecuteResp resp = executeService.executeSql(
            datasourceId, sql, List.of(connInfo.getDatabaseName()));

        DatasourceTablesRsp rsp = new DatasourceTablesRsp();
        List<String> tables = new ArrayList<>();
        for (Object row : resp.getOutputList()) {
            if (row instanceof java.util.Map<?, ?> map) {
                Object tableName = map.get("table_name");
                if (tableName != null) {
                    tables.add(tableName.toString());
                }
            }
        }
        rsp.setTables(tables);
        return rsp;
    }

    public DatasourceTableColumnsRsp retrieveTableColumns(String projectId, String workspaceId,
                                                            String datasourceId, String tableName) {
        DatasourceEntity entity = datasourceMapper.getByPrimaryKeyAndWorkspaceId(
            datasourceId, projectId, workspaceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_NOT_FOUND, datasourceId);
        }
        DatasourceConnectionInfo connInfo = JsonUtils.json2ObjQuietly(
            entity.getConnectionInfo(), DatasourceConnectionInfo.class);
        String sql = "SELECT column_name, data_type FROM information_schema.columns "
            + "WHERE table_schema = ? AND table_name = ?";
        DatasourceExecuteResp resp = executeService.executeSql(
            datasourceId, sql, List.of(connInfo.getDatabaseName(), tableName));

        DatasourceTableColumnsRsp rsp = new DatasourceTableColumnsRsp();
        List<DatasourceTableColumnsRsp.ColumnInfo> columns = new ArrayList<>();
        for (Object row : resp.getOutputList()) {
            if (row instanceof java.util.Map<?, ?> map) {
                DatasourceTableColumnsRsp.ColumnInfo col = new DatasourceTableColumnsRsp.ColumnInfo();
                col.setColumnName(map.get("column_name") != null ? map.get("column_name").toString() : null);
                col.setDataType(map.get("data_type") != null ? map.get("data_type").toString() : null);
                columns.add(col);
            }
        }
        rsp.setColumns(columns);
        return rsp;
    }

    private void validateConnectionInfo(DatasourceConnectionInfo connInfo) {
        if (connInfo == null) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID, "connectionInfo is null");
        }
        if (StringUtils.isBlank(connInfo.getHost())) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID, "host is required");
        }
        if (StringUtils.isBlank(connInfo.getPort())) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID, "port is required");
        }
        if (StringUtils.isBlank(connInfo.getDatabaseName())) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID, "databaseName is required");
        }
        if (StringUtils.isBlank(connInfo.getUser())) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID, "user is required");
        }
        if (StringUtils.isBlank(connInfo.getPassword())) {
            throw new AgentStudioException(StudioError.DATASOURCE_PARAM_INVALID, "password is required");
        }
    }

    private DatasourceBriefRsp toBriefRsp(DatasourceEntity entity) {
        DatasourceBriefRsp rsp = new DatasourceBriefRsp();
        rsp.setId(entity.getId());
        rsp.setName(entity.getName());
        rsp.setType(entity.getType());
        rsp.setStatus(entity.getStatus());
        rsp.setLastErrorMessage(entity.getLastErrorMessage());
        return rsp;
    }

    private DatasourceInfoRsp toInfoRsp(DatasourceEntity entity) {
        DatasourceInfoRsp rsp = new DatasourceInfoRsp();
        rsp.setId(entity.getId());
        rsp.setName(entity.getName());
        rsp.setType(entity.getType());
        rsp.setDesc(entity.getDesc());
        rsp.setStatus(entity.getStatus());
        rsp.setLastErrorMessage(entity.getLastErrorMessage());
        rsp.setCreatedBy(entity.getCreatedBy());
        rsp.setCreatedOn(entity.getCreatedOn());
        rsp.setUpdatedBy(entity.getUpdatedBy());
        rsp.setUpdatedOn(entity.getUpdatedOn());

        DatasourceConnectionInfo connInfo = JsonUtils.json2ObjQuietly(
            entity.getConnectionInfo(), DatasourceConnectionInfo.class);
        if (connInfo != null) {
            connInfo.setPassword(PASSWORD_MASK);
        }
        rsp.setConnectionInfo(connInfo);
        return rsp;
    }
}
