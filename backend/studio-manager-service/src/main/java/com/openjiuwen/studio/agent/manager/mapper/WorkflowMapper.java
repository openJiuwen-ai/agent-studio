/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.dto.ListWorkflowLastVersionsQo;
import com.openjiuwen.studio.agent.common.dto.agent.ListWorkflowsQo;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowVersionEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * workflow 数据库操作mapper
 *
 */
@Mapper
public interface WorkflowMapper {
    /**
     * 根据workflowEntity查询条件从数据库获取workflow
     *
     * @param workflowEntity workflowEntity
     * @return workflow列表
     */
    List<WorkflowEntity> getWorkflowEntityByFilter(@Param("workflowEntity") WorkflowEntity workflowEntity);

    /**
     * 根据发布状态 和 workflow id从数据库获取Workflow配置
     *
     * @param status status
     * @param id id
     * @return workflow配置
     */
    WorkflowEntity getWorkflowEntityByStatus(@Param("status") String status, @Param("id") String id);

    /**
     * 查询数据表中所有未被软删除的workflow
     *
     * @return workflow配置
     */
    List<WorkflowEntity> getAll();

    List<String> findWorkflowToBeDeleted(@Param("softDeleteTtl") Long softDeleteTtl);

    int deleteByPrimaryKeys(@Param("workflowIds") List<String> workflowIds);

    /**
     * 根据project id和 workflow id从数据库获取Workflow配置
     *
     * @param projectId projectId
     * @param id id
     * @return workflow配置
     */
    WorkflowEntity getWorkflowEntity(@Param("projectId") String projectId, @Param("opProjectId") String opProjectId,
        @Param("workspaceId") String workspaceId, @Param("id") String id);

    /**
     * 根据工作区ID获取WorkflowEntity对象。
     *
     * @param projectId 项目的唯一标识符
     * @param workspaceId 工作区的唯一标识符
     * @param id 工作流的唯一标识符
     * @return 返回匹配的WorkflowEntity对象
     */
    WorkflowEntity getWorkflowEntityByWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("id") String id);

    /**
     * 根据给定的项目ID、工作空间ID和ID列表，获取对应的WorkflowEntity列表。
     *
     * @param projectId 项目ID，用于标识特定的项目
     * @param workspaceId 工作空间ID，用于标识特定的工作空间
     * @param ids ID列表，包含需要查询的WorkflowEntity的ID
     * @return List<WorkflowEntity> 返回与给定ID匹配的WorkflowEntity对象列表
     */
    List<WorkflowEntity> getWorkflowEntityByIds(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("ids") List<String> ids);

    /**
     * 根据project id和 workflow id从数据库获取Workflow配置
     *
     * @param projectId projectId
     * @param id id
     * @return workflow配置
     */
    WorkflowEntity getAllWorkflowEntity(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("id") String id, @Param("creatorId") String creatorId);

    /**
     * 根据project id 和 workflow id更新Workflow配置
     *
     * @param projectId 用戶projectId
     * @param id id
     * @param workflowEntity 更新配置数据
     * @return int
     */
    int updateWorkflowEntity(@Param("projectId") String projectId, @Param("id") String id,
        @Param("workflowEntity") WorkflowEntity workflowEntity);

    /**
     * 删除工作流版本后回退最新版本指针：仅当当前 last_version_id 仍等于被删版本号（expectedLastVersionId）时，
     * 才将其更新为 newLastVersionId（剩余最新版本号，或版本全部删除时为null）。
     * 采用条件更新（CAS）语义，删除中间版本或并发发布新版本时条件不匹配，不会产生副作用。
     *
     * @param projectId 用戶projectId
     * @param id workflow id
     * @param expectedLastVersionId 被删除的版本号
     * @param newLastVersionId 回退后的版本号，可为null
     * @return int 更新行数，0表示条件未匹配（无需回退）
     */
    int updateLastVersionIdIfMatch(@Param("projectId") String projectId, @Param("id") String id,
        @Param("expectedLastVersionId") String expectedLastVersionId,
        @Param("newLastVersionId") String newLastVersionId);

    /**
     * 用于触发事务锁sql
     *
     * @param projectId 用戶projectId
     * @param id id
     * @return int
     */
    int updateWorkflowTransactionalId(@Param("projectId") String projectId, @Param("id") String id,
        @Param("workspaceId") String workspaceId);

    /**
     * 根据project id和 id更新Workflow配置
     *
     * @param workflowEntity 创建workflow
     * @return int
     */
    int createWorkflowEntity(WorkflowEntity workflowEntity);

    /**
     * 根据主键从数据库删除workflow
     *
     * @param id id
     * @param projectId projectId
     * @return int
     */
    int deleteByPrimaryKey(@Param("projectId") String projectId, @Param("id") String id);

    /**
     * 根据project id和查询条件从数据库获取workflow列表
     *
     * @param projectId projectId
     * @param listWorkflowsQo 查询条件
     * @return workflow列表
     */
    List<WorkflowEntity> selectByWorkflowSearchCriteria(@Param("projectId") String projectId,
        @Param("workflowSearchCriteria") ListWorkflowsQo listWorkflowsQo);

    /**
     * 根据project id和查询条件从数据库获取workflow最新版本列表
     *
     * @param projectId projectId
     * @param listWorkflowLastVersionsQo listWorkflowLastVersionsQo
     * @return workflow列表
     */
    List<WorkflowVersionEntity> selectLastVersionByWorkflowSearchCriteria(@Param("projectId") String projectId,
        @Param("workflowSearchCriteria") ListWorkflowLastVersionsQo listWorkflowLastVersionsQo);

    /**
     * 根据creator id和查询条件从数据库获取workflow列表
     *
     * @param creatorId creatorId
     * @param projectId projectId
     * @param listWorkflowsQo 查询条件
     * @return workflow列表
     */
    List<WorkflowEntity> selectByCreatorId(@Param("creatorId") String creatorId, @Param("projectId") String projectId,
        @Param("workflowSearchCriteria") ListWorkflowsQo listWorkflowsQo);

    /**
     * 根据creatorId从数据库获取workflow列表
     *
     * @param creatorId creatorId
     * @param projectId projectId
     * @return workflow列表
     */
    List<WorkflowEntity> getAvailableWorkflowEntity(@Param("creatorId") String creatorId,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    /**
     * 根据工作区ID获取可用的工作流实体列表。
     *
     * @param projectId 项目的唯一标识符
     * @param workspaceId 工作区的唯一标识符
     * @return 返回一个包含可用工作流实体的列表
     */
    List<WorkflowEntity> getAvailableWorkflowEntityByWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId);

    /**
     * 根据workflow id列表查询workflow信息
     *
     * @param projectId projectId
     * @param workflowIds workflowIds
     * @return
     */
    List<WorkflowEntity> selectByWorkflowIds(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("workflowIds") List<String> workflowIds);

    WorkflowEntity getWorkflowById(@Param("id") String id);

    List<WorkflowEntity> selectWithQuoteNums(@Param("projectId") String projectId,
        @Param("limitNums") Integer limitNums);

    WorkflowEntity selectByNameAndCreatorId(@Param("name") String name, @Param("creatorId") String creatorId);

    /**
     * 根据projectId查询发布为自定义节点的工作流数量
     *
     * @param projectId projectId
     * @return 发布为自定义节点的工作流数量
     */
    int selectCustomizeNodeCountByProjectId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId);

    List<WorkflowEntity> selectByTraceId(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("traceId") String traceId);

    int selectByWorkflowIdAndResourceId(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("resourceId") String resourceId, @Param("resourceType") String resourceType);

    WorkflowEntity selectByWorkflowId(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("id") String id);

    int insertWorkflowEntity(WorkflowEntity workflowEntity);

    int countWorkflowCountByDomainId(@Param("domainId") String domainId);

    List<WorkflowEntity> selectByWorkflowIdList(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("workflowIdList") List<String> workflowIdList);

    List<WorkflowEntity> queryWorkflowList(@Param("limit") int limit, @Param("offset") int offset);

    void updateWorkflowEntityByTraceId(@Param("projectId") String projectId, @Param("traceId") String traceId,
        @Param("workspaceId") String workspaceId, @Param("workflowEntity") WorkflowEntity workflowEntity);

    void updateProjectIdByIds(String opSvcProjectId, List<String> workflowIds);

    void updateWorkflowShareStatus(@Param("workflowId") String workflowId, @Param("status") int status);

    int countWorkflowIdInDb(@Param("workflowId") String workflowId);
}
