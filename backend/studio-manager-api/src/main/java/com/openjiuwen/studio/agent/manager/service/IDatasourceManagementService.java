/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.DatasourceBatchDeleteReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceInfoReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceInfoRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceListRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceTableColumnsRsp;
import com.openjiuwen.studio.agent.manager.dto.DatasourceTablesRsp;

import java.util.List;

public interface IDatasourceManagementService {

    DatasourceBriefRsp createDatasource(String projectId, String workspaceId, DatasourceInfoReq req);

    DatasourceBriefRsp modifyDatasource(String projectId, String workspaceId,
                                        String datasourceId, DatasourceInfoReq req);

    void deleteDatasource(String projectId, String workspaceId, String datasourceId);

    void batchDeleteDatasource(String projectId, String workspaceId, DatasourceBatchDeleteReq req);

    DatasourceListRsp listDatasource(String projectId, String workspaceId,
                                    int page, int pageSize,
                                    String name, String type, String status);

    DatasourceInfoRsp retrieveDatasource(String projectId, String workspaceId, String datasourceId);

    DatasourceTablesRsp retrieveTables(String projectId, String workspaceId, String datasourceId);

    DatasourceTableColumnsRsp retrieveTableColumns(String projectId, String workspaceId,
                                                   String datasourceId, String tableName);
}
