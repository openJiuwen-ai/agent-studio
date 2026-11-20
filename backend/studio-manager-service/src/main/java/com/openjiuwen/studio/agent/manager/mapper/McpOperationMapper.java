/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.sql.Timestamp;
import java.util.List;

/**
 * FEAT-134 MCP 操作表 mapper。
 */
@Mapper
public interface McpOperationMapper {

    int insertOperation(McpOperationEntity entity);

    int insertOperationItem(McpOperationItemEntity entity);

    McpOperationEntity selectOperationById(@Param("id") String id);

    /**
     * 按归属查询操作（任务仅接受同空间用户查询）。
     */
    McpOperationEntity selectOperationByIdAndScope(@Param("id") String id, @Param("tenantId") String tenantId,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    List<McpOperationItemEntity> selectOperationItems(@Param("operationId") String operationId);

    /**
     * 受理时声明活动操作（带归属条件；0=已有活动操作或归属不符）。
     */
    int claimOperationOnService(@Param("serviceId") String serviceId, @Param("tenantId") String tenantId,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("operationId") String operationId);

    /**
     * 按 operation_id 精确释放活动标记（不得清除另一次操作）。
     */
    int releaseOperationOnService(@Param("serviceId") String serviceId, @Param("operationId") String operationId);

    int finishOperation(@Param("id") String id, @Param("status") String status,
        @Param("createdCount") Integer createdCount, @Param("successCount") Integer successCount,
        @Param("failedCount") Integer failedCount, @Param("finishedDate") Timestamp finishedDate);

    int updateOperationStatus(@Param("id") String id, @Param("status") String status);

    int finishOperationItem(McpOperationItemEntity entity);

    /**
     * 超时扫描：终结超期 RUNNING 任务（deadline 回收）。
     */
    List<String> selectTimedOutRunningOperations(@Param("now") Timestamp now, @Param("limitCount") int limitCount);
}
