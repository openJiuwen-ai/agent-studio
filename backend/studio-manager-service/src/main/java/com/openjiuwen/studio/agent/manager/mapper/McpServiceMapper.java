/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * ws_mcp_service_def 表操作类
 *
 */
@Mapper
public interface McpServiceMapper {
    List<McpServiceEntity> selectByTenant(@Param("offset") int offset, @Param("limit") int limit,
        @Param("tenantId") String tenantId, @Param("deptCode") String deptCode);

    List<McpServiceEntity> selectByTenantAndName(@Param("offset") int offset, @Param("limit") int limit,
        @Param("name") String name, @Param("nameEn") String nameEn, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode);

    List<McpServiceEntity> selectByName(@Param("name") String name, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode, @Param("workspaceId") String workspaceId);

    List<McpServiceEntity> selectByNameEn(@Param("nameEn") String nameEn, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode, @Param("workspaceId") String workspaceId);

    List<McpServiceEntity> selectList(@Param("ids") List<String> ids, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode, @Param("workspaceId") String workspaceId);

    List<McpServiceEntity> selectListByTenant(@Param("tenantId") String tenantId, @Param("deptCode") String deptCode,
        @Param("workspaceId") String workspaceId);

    Long selectCount(@Param("tenantId") String tenantId, @Param("deptCode") String deptCode);

    int insert(McpServiceEntity serviceEntity);

    int update(McpServiceEntity entity);

    int updateStatus(Map<String, Object> params);

    int updateFcInstanceIdAndReadme(Map<String, Object> params);

    int updateFcInstanceUrlAndStatus(Map<String, Object> params);

    int updateTools(Map<String, Object> params);

    int updateToolsAndStatus(Map<String, Object> params);

    int updateFcInstanceInfo(Map<String, Object> params);

    int updateAuthInfo(Map<String, Object> params);

    int markAsDeleted(Map<String, Object> params);

    int updateFcInstanceStatus(Map<String, Object> params);

    List<McpServiceEntity> selectByIds(@Param("ids") List<String> ids);

    List<McpServiceEntity> selectByIdsAndWorkspace(@Param("ids") List<String> ids, @Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId);

    McpServiceEntity selectByPrimaryKey(@Param("id") String serverId,
        @Param("workspaceId") String workspaceId);

    List<McpServiceEntity> selectServiceWithPage(@Param("offset") int offset, @Param("limit") int limit,
        @Param("name") String name, @Param("nameEn") String nameEn, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode, @Param("orgType") String orgType, @Param("workspaceId") String workspaceId,
        @Param("fcInstanceStatus") String fcInstanceStatus);

    List<McpServiceEntity> selectVisibilityServiceWithPage(@Param("offset") int offset, @Param("limit") int limit,
        @Param("name") String name, @Param("nameEn") String nameEn, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode, @Param("orgType") String orgType, @Param("workspaceId") String workspaceId,
        @Param("fcInstanceStatus") String fcInstanceStatus, @Param("nodeType") String nodeType,
        @Param("visibility") String visibility);

    long selectServiceWithPageCount(@Param("name") String name, @Param("nameEn") String nameEn,
        @Param("tenantId") String tenantId, @Param("deptCode") String deptCode, @Param("orgType") String orgType,
        @Param("workspaceId") String workspaceId, @Param("fcInstanceStatus") String fcInstanceStatus,
        @Param("nodeType") String nodeType, @Param("visibility") String visibility);

    /**
     * 根据mcp主键、工作空间id、租户id、部门id 查询mcp服务信息
     *
     */
    McpServiceEntity selectById(@Param("id") String id, @Param("tenantId") String tenantId,
        @Param("deptCode") String deptCode, @Param("workspaceId") String workspaceId);

    McpServiceEntity selectByMcpId(@Param("id") String id);

    McpServiceEntity selectByIdAndWorkspaceId(@Param("workspaceId") String workspaceId, @Param("mcpId") String id);

    McpServiceEntity selectByTraceIdAndWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("traceId") String traceId);

    int updateById(@Param("mcpId") String id, @Param("entity") McpServiceEntity entity);

    void updateFcInstanceInfo2(Map<String, Object> params);

    void batchInsert(@Param("list") List<McpServiceEntity> target);

    void hardDeleteService(@Param("ids") List<String> ids);

    List<String> selectIdsToBeHardDeleted(LocalDateTime lastUpdatedDate, @Param("fcInstanceStatus") String fcInstanceStatus);

    void hardDeleteSingleService(@Param("id") String id, @Param("tenantId") String tenantId, @Param("deptCode") String deptCode);

    /**
     * 更新服务状态及失败原因
     */
    int updateStatusWithReason(@Param("id") String id,
                               @Param("status") String status,
                               @Param("failReason") String failReason,
                               @Param("tenantId") String tenantId);

    void updateMcpShareStatus(@Param("id") String id, @Param("status") int status);

    List<McpServiceEntity> listMcpServiceByIdAndProjectId(@Param("ids") List<String> mcpIds, @Param("projectId") String projectId);

    List<McpServiceEntity> listMcpServiceByShareResourceEntity(List<ShareResourceEntity> shareResourceEntities);

    /**
     * FEAT-134：重载原子提交——带归属、活动操作与修订号条件；影响行数必须为 1。
     */
    int commitToolSnapshot(@Param("serviceId") String serviceId, @Param("tenantId") String tenantId,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("operationId") String operationId, @Param("expectedRevision") long expectedRevision,
        @Param("tools") String tools);

    /**
     * FEAT-134：导入待补配标记清除（modify 确认后）。
     */
    int markImportConfigured(@Param("serviceId") String serviceId, @Param("tenantId") String tenantId,
        @Param("workspaceId") String workspaceId);

    /**
     * FEAT-134：导入待补配标记写入。
     */
    int markImportPending(@Param("serviceId") String serviceId, @Param("tenantId") String tenantId,
        @Param("workspaceId") String workspaceId, @Param("pending") boolean pending,
        @Param("paths") String paths);
}
