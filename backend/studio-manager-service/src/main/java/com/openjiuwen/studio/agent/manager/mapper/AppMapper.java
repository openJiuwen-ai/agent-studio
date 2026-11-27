/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.entity.App;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
 * app 数据库操作mapper
 *
 */
@Mapper
public interface AppMapper {
    /**
     * 插入一条app到数据库
     *
     * @param app app
     * @return int
     */
    int insert(App app);

    /**
     * 根据app关联的资源ID查询应用
     *
     * @param resourceId resourceId
     * @return int
     */
    App selectByResourceId(@Param("resourceId") String resourceId);

    /**
     * 根据查询条件从数据库获取app列表
     *
     * @param searchCriteria searchCriteria
     * @return app列表
     */
    List<App> selectBySearchCriteria(@Param("searchCriteria") SearchCriteria searchCriteria);

    /**
     * 根据app关联的资源ID从数据库删除app
     *
     * @param resourceId resourceId
     * @param projectId projectId
     * @return int
     */
    int deleteByResourceId(@Param("resourceId") String resourceId, @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    /**
     * 根据app关联的资源ID从数据库软删除app
     *
     * @param resourceId resourceId
     * @param projectId projectId
     * @return int
     */
    int softDeleteByResourceId(@Param("resourceId") String resourceId, @Param("projectId") String projectId, @Param("workspaceId") String workspaceId);

    List<String> findAppToBeDeleted(@Param("softDeleteTtl") LocalDateTime softDeleteTtl);

    int deleteByPrimaryKeys(@Param("appIds") List<String> appIds);

    void updateProjectIdByAppIds(@Param("opSvcProjectId") String opSvcProjectId, @Param("appIds") List<String> appIds);

    /**
     * 根据 resource ids 从数据库获取apps信息
     * @param resourceIds
     * @return
     */
    List<App> selectByResourceIds(@Param("resourceIds") List<String> resourceIds);

    /**
     * 获取特定 resource type 中的任意一个 app 信息
     * @param resourceType
     * @return
     */
    App selectRandomAppByResourceType(@Param("resourceType") String resourceType);
}
