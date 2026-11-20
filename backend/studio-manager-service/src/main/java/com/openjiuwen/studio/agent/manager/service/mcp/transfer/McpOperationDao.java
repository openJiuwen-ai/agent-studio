/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;
import com.openjiuwen.studio.agent.manager.mapper.McpOperationMapper;

import org.springframework.stereotype.Component;

import java.sql.Timestamp;
import java.util.List;

/**
 * FEAT-134 MCP 操作表 DAO 薄包装（事务边界由服务层组合管理）。
 */
@Component
public class McpOperationDao {
    private final McpOperationMapper mapper;

    public McpOperationDao(McpOperationMapper mapper) {
        this.mapper = mapper;
    }

    public void insertOperation(McpOperationEntity entity) {
        mapper.insertOperation(entity);
    }

    public void insertOperationItem(McpOperationItemEntity entity) {
        mapper.insertOperationItem(entity);
    }

    public McpOperationEntity getOperationById(String id) {
        return mapper.selectOperationById(id);
    }

    public McpOperationEntity getOperationByIdAndScope(String id, String tenantId, String projectId,
        String workspaceId) {
        return mapper.selectOperationByIdAndScope(id, tenantId, projectId, workspaceId);
    }

    public List<McpOperationItemEntity> getOperationItems(String operationId) {
        return mapper.selectOperationItems(operationId);
    }

    /**
     * 受理时声明活动操作。返回 false 表示已有活动操作或归属不符（调用方转 409/403）。
     */
    public boolean claimOperationOnService(String serviceId, String tenantId, String projectId,
        String workspaceId, String operationId) {
        return mapper.claimOperationOnService(serviceId, tenantId, projectId, workspaceId, operationId) == 1;
    }

    /**
     * 按 operation_id 精确释放活动标记。
     */
    public void releaseOperationOnService(String serviceId, String operationId) {
        mapper.releaseOperationOnService(serviceId, operationId);
    }

    public boolean finishOperation(String id, String status, Integer createdCount, Integer successCount,
        Integer failedCount) {
        return mapper.finishOperation(id, status, createdCount, successCount, failedCount,
            new Timestamp(System.currentTimeMillis())) == 1;
    }

    public boolean markOperationInterrupted(String id) {
        return mapper.updateOperationStatus(id, "INTERRUPTED") == 1;
    }

    public void finishOperationItem(McpOperationItemEntity entity) {
        mapper.finishOperationItem(entity);
    }

    public List<String> getTimedOutRunningOperations(int limitCount) {
        return mapper.selectTimedOutRunningOperations(new Timestamp(System.currentTimeMillis()), limitCount);
    }
}
