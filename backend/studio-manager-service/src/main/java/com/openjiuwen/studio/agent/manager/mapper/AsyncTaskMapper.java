/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.TaskEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Date;
import java.util.List;

/**
 * 任务数据库mapper
 */
@Mapper
public interface AsyncTaskMapper {
    int createEntity(@Param("entity") TaskEntity entity);

    List<TaskEntity> getTaskEntity(@Param("entity") TaskEntity entity, @Param("sort") String sort,
        @Param("order") String order);

    int updateByPrimaryKey(@Param("entity") TaskEntity entity);

    List<TaskEntity> getInitWorkflowTaskEntity(@Param("limit") int limit);

    List<TaskEntity> getExpiredTaskEntity(@Param("expireTime") Date expireTime);

    int deleteByIds(@Param("ids") List<String> ids);
}