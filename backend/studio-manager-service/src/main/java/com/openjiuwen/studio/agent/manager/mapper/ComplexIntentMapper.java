/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.ComplexIntentEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * Complex Intent
 *
 */
@Mapper
public interface ComplexIntentMapper {
    /**
     * 新增数据
     *
     * @param entity 数据
     * @return 影响的行数
     */
    int createEntity(@Param("entity") ComplexIntentEntity entity);

    /**
     * 更新数据
     *
     * @param entity 过滤条件
     * @return 影响的行数
     */
    int updateByKey(@Param("entity") ComplexIntentEntity entity);

    /**
     * 删除数据
     *
     * @param intentId 意图id
     * @param projectId 项目id
     * @return 影响的行数
     */
    int deleteByKey(@Param("intentId") String intentId, @Param("projectId") String projectId);

    /**
     * 获取单个数据
     *
     * @param intentId 意图id
     * @param projectId 项目id
     * @return 数据
     */
    ComplexIntentEntity getByKey(@Param("intentId") String intentId, @Param("projectId") String projectId);

    /**
     * 根据意图ID、项目ID和工作区ID获取复杂的意图实体。
     *
     * @param intentId    意图的唯一标识符。
     * @param projectId   项目ID，用于标识具体项目。
     * @param workspaceId 工作区ID，用于标识具体工作区。
     * @return 返回匹配的ComplexIntentEntity对象，如果未找到则返回null。
     */
    ComplexIntentEntity getByKeyAndWorkspaceId(@Param("intentId") String intentId,
        @Param("projectId") String projectId,
        @Param("workspaceId") String workspaceId);

    /**
     * 查询列表
     *
     * @param entity 过滤条件
     * @return 数据列表
     */
    List<ComplexIntentEntity> getEntities(@Param("entity") ComplexIntentEntity entity);

    /**
     * 查询数量
     *
     * @param entity 过滤条件
     * @return
     */
    int countByName(@Param("entity") ComplexIntentEntity entity);

    /**
     * 查询列表 name精确查找
     *
     * @param entity 过滤条件
     * @return 数据列表
     */
    List<ComplexIntentEntity> getEntitiesAccurate(@Param("entity") ComplexIntentEntity entity);
}
