/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.dto.DatasourceExecuteReq;
import com.openjiuwen.studio.agent.manager.dto.DatasourceExecuteResp;
import com.openjiuwen.studio.agent.manager.service.IDatasourceExecuteService;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/studio/datasources")
public class DatasourceExecuteController {

    @Autowired
    private IDatasourceExecuteService datasourceExecuteService;

    @PostMapping("/{datasource_id}/execute")
    public ResponseEntity<DatasourceExecuteResp> executeSql(
        @PathVariable("datasource_id") String datasourceId,
        @RequestBody DatasourceExecuteReq req) {
        return ResponseModel.success(
            datasourceExecuteService.executeSql(datasourceId, req.getQuery(), req.getConditions()));
    }
}
