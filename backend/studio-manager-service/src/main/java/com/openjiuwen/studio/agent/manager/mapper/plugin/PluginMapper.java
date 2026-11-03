/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.mapper.plugin;

import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;

@Mapper
public interface PluginMapper {

    int insert(PluginEntity record);

    int selectByChineseNameAndWorkspaceIdAndProjectId(@Param("pluginChineseName") String pluginChineseName,
        @Param("workspaceId") String workspaceId, @Param("toolId") String toolId);

    int selectByDisplayNameAndWorkspaceId(@Param("pluginDisplayName") String pluginDisplayName,
        @Param("workspaceId") String workspaceId);

    int selectByDisplayNameAndWorkspaceIdAndProjectId(@Param("pluginDisplayName") String pluginDisplayName,
        @Param("workspaceId") String workspaceId, @Param("toolId") String toolId);

    List<PluginEntity> selectByWorkspaceIdAndProjectId(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("pluginId") String pluginId);

    PluginEntity selectByPrimaryKeyAndWorkspace(@Param("pluginId") String pluginId,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    List<PluginEntity> batchSelectByPrimaryKeyAndWorkspace(@Param("pluginIds") Set<String> pluginIds,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    PluginEntity selectByPrimaryKeyAndWorkspaceAndCredential(@Param("pluginId") String pluginId,
                                                @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);
    int updateByPrimaryKeySelective(PluginEntity record);

    int updateNameByPrimaryKey(@Param("pluginId") String pluginId, @Param("pluginChineseName") String pluginChineseName, @Param("pluginDisplayName") String pluginDisplayName);

    int deleteByPrimaryKey(@Param("pluginId") String pluginId, @Param("projectId") String projectId);
    
    int deleteByPrimaryKeys(@Param("pluginIds") List<String> pluginIds);

    void copyToHistoryTool(@Param("toolId") String toolId, @Param("projectId") String projectId,
                                     @Param("historyId") String historyId);

    List<String> findPluginToBeDeleted(@Param("twoYearsAgo") LocalDateTime twoYearsAgo);
    
    List<PluginEntity> selectAllBySearchCriteria(@Param("projectId") String projectId,
        @Param("opProjectId") String opProjectId, @Param("workspaceId") String workspaceId,
        @Param("userId") String userId, @Param("searchCriteria") SearchCriteria searchCriteria);

    List<PluginEntity> selectByPrimaryIdAndPluginIdsWithSearchCriteria(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("toolIds") List<String> toolIds,
        @Param("searchCriteria") SearchCriteria searchCriteria);

    List<PluginEntity> selectByProjectIdAndSearchCriteria(@Param("projectId") String projectId,
        @Param("userId") String userId, @Param("searchCriteria") SearchCriteria searchCriteria,
        @Param("workspaceId") String workspaceId);

    PluginEntity selectByPrimaryKey(@Param("pluginId") String pluginId, @Param("projectId") String projectId);

    PluginEntity selectByNameAndWorkspaceIdAndProjectId(@Param("pluginDisplayName") String pluginDisplayName,
        @Param("workspaceId") String workspaceId, @Param("projectId") String projectId);

    List<PluginEntity> selectByPrimaryIdAndToolIdsWithSearchCriteria(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("toolIds") List<String> toolIds,
        @Param("searchCriteria") SearchCriteria searchCriteria);

    PluginEntity selectPluginEntityWithCredential(@Param("toolId") String toolId, @Param("projectId") String projectId,
        @Param("userId") String userId);

    List<PluginEntity> selectByIds(@Param("toolIds") List<String> list);

    List<PluginEntity> selectByTraceIdAndWorkspaceId(@Param("projectId") String projectId,
        @Param("workspaceId") String targetWorkspaceId, @Param("traceId") String traceId);

    PluginEntity selectStatueByPrimaryKeyAndWorkspace(@Param("pluginId") String toolId,
        @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    PluginEntity selectInfo(@Param("pluginId") String pluginId);

    void updatePluginShareStatus(@Param("toolId") String resourceId, @Param("status") int status);

    void updateIdAndName(@Param("toolId") String pluginId, @Param("uuid") String uuid);

    void updateProjectIdByIds(@Param("opSvcProjectId") String opSvcProjectId, @Param("pluginIds") List<String> pluginIds);

    String selectVersionByPluginId(@Param("pluginId") String pluginId);
}
