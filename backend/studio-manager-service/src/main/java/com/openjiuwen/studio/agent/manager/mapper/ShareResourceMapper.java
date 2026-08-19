/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 资源共享范围管理Mapper
 *
 */
@Mapper
public interface ShareResourceMapper {

    /**
     * 插入共享资源实体。
     *
     * @param shareResourceEntity 共享资源实体对象
     * @return 返回插入的记录数
     */
    int insert(ShareResourceEntity shareResourceEntity);

    /**
     * 根据给定的项目ID、工作区ID和资源ID，查询并返回对应的共享资源实体。
     *
     * @param projectId 项目ID，用于标识特定的项目
     * @param workspaceId 工作区ID，用于标识项目中的特定工作区
     * @param resourceId 资源ID，用于标识要查询的资源
     * @return 返回查找到的ShareResourceEntity对象，如果未找到则返回null
     */
    ShareResourceEntity selectShareResourceEntityById(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("resourceId") String resourceId);

    /**
     * 查询共享给指定空间的资源
     */
    List<ShareResourceEntity> selectSharedResourceByAuthWorkspaceIdAndType(@Param("projectId") String projectId,
        @Param("authWorkspaceId") String authWorkspaceId, @Param("resourceType") String resourceType, @Param("resourceName") String resourceName);

    /**
     * 根据资源ID查询共享资源列表
     * 
     * @param resourceIds 资源ID列表
     * @return 共享资源列表
     */
    List<ShareResourceEntity> selectShareResourceByResourceIds(@Param("resourceIds") List<String> resourceIds);

    /**
     * 更新共享资源实体。
     *
     * @param shareResourceEntity 要更新的共享资源实体对象
     * @return 更新操作的结果，通常返回更新的记录数
     */
    int updateShareResourceEntity(ShareResourceEntity shareResourceEntity);

    /**
     * 根据给定的ID删除共享资源实体。
     *
     * @param resourceId 要删除的共享资源实体的唯一标识符。
     * @return 被删除的共享资源实体的数量，通常为1，如果未找到则为0。
     */
    int deleteByPrimaryKey(@Param("resourceId") String resourceId);

    ShareResourceEntity selectShareResourceEntityByResourceId(@Param("resourceId") String resourceId);

    /**
     * 宽松模式导入：按 traceId + 资源类型 查询共享给指定工作空间的共享资源（含团队共享 'all'）。
     * 用于目标空间本地查不到子资源时，按 traceId 跨空间匹配已授权的共享资源。
     *
     * @param projectId 项目ID
     * @param authWorkspaceId 授权工作空间ID（当前导入目标空间）
     * @param resourceType 资源类型（小写 controller/workflow）
     * @param traceId 源空间资源traceId
     * @return 命中的共享资源实体列表，按 update_time 降序
     */
    List<ShareResourceEntity> selectSharedResourceByTraceIdAndAuthWorkspace(@Param("projectId") String projectId,
        @Param("authWorkspaceId") String authWorkspaceId, @Param("resourceType") String resourceType,
        @Param("traceId") String traceId);

    List<ShareResourceEntity> selectSharResourceEntityByWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("resourceType") String resourceType,
        @Param("resourceName") String resourceName);

    int countResourceByResourceId(@Param("projectId") String projectId, @Param("resourceId") String resourceId);
}
