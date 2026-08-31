/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper.md;

import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderCondition;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Collection;
import java.util.List;

@Mapper
public interface UserModelServiceProviderMapper {
    // 插入记录
    int insert(ModelServiceProvider record);

    // 删除记录
    int deleteById(String id);

    // 更新记录
    int updateById(ModelServiceProvider record);

    // 根据ID查询
    ModelServiceProvider selectById(@Param("id") String id);

    // 根据PROJECT_ID查询
    List<ModelServiceProvider> selectByProjectId(@Param("projectId") String projectId);

    /**
     * 根据项目ID和空间ID 以及供应商名称 查询用户有权限的数据
     *
     * @param projectId 项目ID
     * @param workspaceId 空间ID
     * @param providerName 供应商名称
     * @return 供应商列表
     */
    List<ModelServiceProvider> selectUserDataByName(@Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId, @Param("providerName") String providerName);

    List<ModelServiceProviderDetail> queryByCondition(@Param("condition") ProviderCondition condition,
        @Param("limit") int limit, @Param("offset") int offset);

    /**
     * 数据备份
     */
    int insertBackup(ModelServiceProvider record);

    List<ModelServiceProvider> queryBackupByUpdateTime(@Param("lastUpdatedDate") Long lastUpdatedDate);

    void deleteBackupByIds(@Param("ids") List<String> ids);

    /**
     * 根据 ID 集合批量查询供应商信息
     */
    List<ModelServiceProvider> selectByIds(@Param("ids") Collection<String> ids);

    /**
     * 在指定项目+工作空间内按 id 集合查询供应商（workspace-scoped，用于跨工作空间 COPY 存在性判定）。
     */
    List<ModelServiceProvider> selectByProjectIdAndWorkspaceId(
        @Param("ids") Collection<String> ids,
        @Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId);

}
