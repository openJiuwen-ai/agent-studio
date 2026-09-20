/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.DatasourceEntity;

import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface DatasourceMapper {

    int insert(DatasourceEntity entity);

    int update(DatasourceEntity entity);

    int deleteById(@Param("id") String id,
                    @Param("projectId") String projectId,
                    @Param("workspaceId") String workspaceId);

    DatasourceEntity getByPrimaryKeyAndWorkspaceId(@Param("id") String id,
                                                    @Param("projectId") String projectId,
                                                    @Param("workspaceId") String workspaceId);

    DatasourceEntity getById(@Param("id") String id);

    List<DatasourceEntity> listDatasource(@Param("projectId") String projectId,
                                          @Param("workspaceId") String workspaceId,
                                          @Param("name") String name,
                                          @Param("type") String type,
                                          @Param("status") String status,
                                          @Param("offset") int offset,
                                          @Param("limit") int limit);

    int countDatasource(@Param("projectId") String projectId,
                        @Param("workspaceId") String workspaceId,
                        @Param("name") String name,
                        @Param("type") String type,
                        @Param("status") String status);

    DatasourceEntity getByNameAndWorkspaceId(@Param("name") String name,
                                             @Param("projectId") String projectId,
                                             @Param("workspaceId") String workspaceId);
}
