/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.DatasourceExecuteResp;

import java.util.List;

public interface IDatasourceExecuteService {

    DatasourceExecuteResp executeSql(String datasourceId, String query, List<String> conditions);
}
