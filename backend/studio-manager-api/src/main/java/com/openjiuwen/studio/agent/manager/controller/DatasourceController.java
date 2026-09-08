/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.dto.DatasourceBatchDeleteReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceInfoReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceInfoRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceListRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceTableColumnsRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceTablesRsp;
import com.openjiuwen.studio.agent.manager.dto.ListDatasourceQo;
import com.openjiuwen.studio.agent.manager.service.IDatasourceManagementService;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/{project_id}/agent-manager/datasource")
public class DatasourceController {

    @Autowired
    private IDatasourceManagementService datasourceManagementService;

    @PostMapping
    public ResponseEntity<DatasourceBriefRsp> createDatasource(
        @PathVariable("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId,
        @RequestBody DatasourceInfoReq req) {
        return ResponseModel.success(datasourceManagementService.createDatasource(projectId, workspaceId, req));
    }

    @GetMapping
    public ResponseEntity<DatasourceListRsp> listDatasource(
        @PathVariable("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId,
        ListDatasourceQo qo) {
        return ResponseModel.success(datasourceManagementService.listDatasource(
            projectId, workspaceId,
            qo.getPage() != null ? qo.getPage() : 1,
            qo.getPageSize() != null ? qo.getPageSize() : 20,
            qo.getName(), qo.getType(), qo.getStatus()));
    }

    @GetMapping("/{datasource_id}")
    public ResponseEntity<DatasourceInfoRsp> retrieveDatasource(
        @PathVariable("project_id") String projectId,
        @PathVariable("datasource_id") String datasourceId,
        @RequestParam("workspace_id") String workspaceId) {
        return ResponseModel.success(
            datasourceManagementService.retrieveDatasource(projectId, workspaceId, datasourceId));
    }

    @PutMapping("/{datasource_id}")
    public ResponseEntity<DatasourceBriefRsp> modifyDatasource(
        @PathVariable("project_id") String projectId,
        @PathVariable("datasource_id") String datasourceId,
        @RequestParam("workspace_id") String workspaceId,
        @RequestBody DatasourceInfoReq req) {
        return ResponseModel.success(
            datasourceManagementService.modifyDatasource(projectId, workspaceId, datasourceId, req));
    }

    @DeleteMapping("/{datasource_id}")
    public ResponseEntity<Void> deleteDatasource(
        @PathVariable("project_id") String projectId,
        @PathVariable("datasource_id") String datasourceId,
        @RequestParam("workspace_id") String workspaceId) {
        datasourceManagementService.deleteDatasource(projectId, workspaceId, datasourceId);
        return ResponseModel.success(null);
    }

    @PostMapping("/batch-delete")
    public ResponseEntity<Void> batchDeleteDatasource(
        @PathVariable("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId,
        @RequestBody DatasourceBatchDeleteReq req) {
        datasourceManagementService.batchDeleteDatasource(projectId, workspaceId, req);
        return ResponseModel.success(null);
    }

    @GetMapping("/{datasource_id}/tables")
    public ResponseEntity<DatasourceTablesRsp> retrieveTables(
        @PathVariable("project_id") String projectId,
        @PathVariable("datasource_id") String datasourceId,
        @RequestParam("workspace_id") String workspaceId) {
        return ResponseModel.success(
            datasourceManagementService.retrieveTables(projectId, workspaceId, datasourceId));
    }

    @GetMapping("/{datasource_id}/tables/{table_name}/columns")
    public ResponseEntity<DatasourceTableColumnsRsp> retrieveTableColumns(
        @PathVariable("project_id") String projectId,
        @PathVariable("datasource_id") String datasourceId,
        @PathVariable("table_name") String tableName,
        @RequestParam("workspace_id") String workspaceId) {
        return ResponseModel.success(datasourceManagementService.retrieveTableColumns(
            projectId, workspaceId, datasourceId, tableName));
    }
}
