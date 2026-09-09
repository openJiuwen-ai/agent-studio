/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryItemResponseBody;
import com.openjiuwen.studio.agent.manager.dto.SearchMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.service.IMemoryItemManagementService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class MemoryItemManagementApiController implements MemoryItemManagementApi {
    private static final Logger log = LoggerFactory.getLogger(MemoryItemManagementApiController.class);

    @Autowired
    private IMemoryItemManagementService memoryItemManagementService;

    @Override
    public ResponseEntity<ListMemoryItemResponseBody> listMemoryItems(String projectId, String memoryRepoId,
        Integer pageNum, Integer pageSize, String memoryType) {
        return ResponseModel.success(
            memoryItemManagementService.listMemoryItems(projectId, memoryRepoId, pageNum, pageSize, memoryType));
    }

    @Override
    public ResponseEntity<Void> deleteMemoryItem(String projectId, String memoryRepoId, String memoryId) {
        memoryItemManagementService.deleteMemoryItem(projectId, memoryRepoId, memoryId);
        return ResponseModel.success(null);
    }

    @Override
    public ResponseEntity<Void> batchDeleteMemoryItems(String projectId, String memoryRepoId,
        BatchDeleteMemoryItemRequestBody body) {
        memoryItemManagementService.batchDeleteMemoryItems(projectId, memoryRepoId, body);
        return ResponseModel.success(null);
    }

    @Override
    public ResponseEntity<ListMemoryItemResponseBody> searchMemoryItems(String projectId, String memoryRepoId,
        SearchMemoryItemRequestBody body) {
        return ResponseModel.success(memoryItemManagementService.searchMemoryItems(projectId, memoryRepoId, body));
    }

    @Override
    public ResponseEntity<Void> updateMemoryItems(String projectId, String memoryRepoId,
        UpdateMemoryItemRequestBody body) {
        memoryItemManagementService.updateMemoryItems(projectId, memoryRepoId, body);
        return ResponseModel.success(null);
    }

    @Override
    public ResponseEntity<Void> clearUserMemoryItems(String projectId, String memoryRepoId) {
        memoryItemManagementService.clearUserMemoryItems(projectId, memoryRepoId);
        return ResponseModel.success(null);
    }
}
