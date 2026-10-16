/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryServiceInstancesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ShowMemoryServiceInstanceResponseBody;
import com.openjiuwen.studio.agent.manager.service.IMemoryServiceInstanceService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

/**
 * MemoryServiceInstanceManagement controller
 */
@RestController
public class MemoryServiceInstanceManagementApiController implements MemoryServiceInstanceManagementApi {
    private static final Logger log = LoggerFactory.getLogger(MemoryServiceInstanceManagementApiController.class);

    @Autowired
    private IMemoryServiceInstanceService memoryServiceInstanceService;

    @Override
    public ResponseEntity<CreateMemoryServiceInstanceResponseBody> createMemoryServiceInstance(
        String projectId, String workspaceId, CreateMemoryServiceInstanceRequestBody body) {
        return ResponseModel.success(
            memoryServiceInstanceService.createInstance(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Void> deleteMemoryServiceInstance(String projectId, String instanceId,
        String workspaceId) {
        memoryServiceInstanceService.deleteInstance(projectId, instanceId, workspaceId);
        return ResponseModel.success(null);
    }

    @Override
    public ResponseEntity<Void> modifyMemoryServiceInstance(String projectId, String instanceId,
        String workspaceId, ModifyMemoryServiceInstanceRequestBody body) {
        memoryServiceInstanceService.modifyInstance(projectId, instanceId, workspaceId, body);
        return ResponseModel.success(null);
    }

    @Override
    public ResponseEntity<ListMemoryServiceInstancesResponseBody> listMemoryServiceInstances(
        String projectId, String workspaceId, String name) {
        return ResponseModel.success(
            memoryServiceInstanceService.listInstances(projectId, workspaceId, name));
    }

    @Override
    public ResponseEntity<ShowMemoryServiceInstanceResponseBody> showMemoryServiceInstance(
        String projectId, String instanceId, String workspaceId) {
        return ResponseModel.success(
            memoryServiceInstanceService.showInstance(projectId, instanceId, workspaceId));
    }

    @Override
    public ResponseEntity<ShowMemoryServiceInstanceResponseBody> healthCheckMemoryServiceInstance(
        String projectId, String instanceId, String workspaceId) {
        return ResponseModel.success(
            memoryServiceInstanceService.healthCheck(projectId, instanceId, workspaceId));
    }
}
