/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.MemoryServiceInstanceEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 外部记忆服务实例数据访问层
 */
@Mapper
public interface MemoryServiceInstanceMapper {

    /**
     * 插入实例记录
     */
    int insert(MemoryServiceInstanceEntity entity);

    /**
     * 根据ID删除实例
     */
    int deleteById(@Param("id") String id);

    /**
     * 更新实例信息
     */
    int updateById(MemoryServiceInstanceEntity entity);

    /**
     * 根据ID查询实例
     */
    MemoryServiceInstanceEntity selectById(@Param("id") String id);

    /**
     * 根据ID和项目空间查询实例
     */
    MemoryServiceInstanceEntity selectByIdAndWorkspaceId(@Param("id") String id,
                                                          @Param("workspaceId") String workspaceId);

    /**
     * 条件查询实例列表
     */
    List<MemoryServiceInstanceEntity> selectByCondition(@Param("projectId") String projectId,
                                                        @Param("workspaceId") String workspaceId,
                                                        @Param("domainId") String domainId,
                                                        @Param("name") String name);

    /**
     * 查询绑定了指定实例的记忆库数量（用于删除前校验）
     */
    int countReposByInstanceId(@Param("instanceId") String instanceId);
}
