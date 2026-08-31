/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2020-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.space.dao.application;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.openjiuwen.studio.agent.space.common.utils.CollectionUtil;
import com.openjiuwen.studio.agent.space.dao.entity.AgentBuilderFileEntity;

import org.apache.ibatis.annotations.Mapper;

import java.util.ArrayList;
import java.util.List;

/**
 * 任务相关文件表操作类
 */
@Mapper
public interface AgentBuilderFileMapper extends BaseMapper<AgentBuilderFileEntity> {
    int insertBatchSomeColumn(List<AgentBuilderFileEntity> fileEntityList);

    default List<AgentBuilderFileEntity> selectFilesByTaskId(String taskId) {
        List<AgentBuilderFileEntity> results = selectList(
            new LambdaQueryWrapper<AgentBuilderFileEntity>().in(AgentBuilderFileEntity::getTaskId, taskId));
        if (CollectionUtil.isEmpty(results)) {
            return new ArrayList<>();
        }
        return results;
    }

    default List<AgentBuilderFileEntity> selectFilesByFileIds(List<String> ids) {
        List<AgentBuilderFileEntity> results = selectList(
            new LambdaQueryWrapper<AgentBuilderFileEntity>().in(AgentBuilderFileEntity::getId, ids));
        if (CollectionUtil.isEmpty(results)) {
            return new ArrayList<>();
        }
        return results;
    }

    default int updateTaskId(List<String> fileIds, String taskId) {
        if (CollectionUtil.isEmpty(fileIds)) {
            return 0;
        }
        return update(new UpdateWrapper<AgentBuilderFileEntity>().in("id", fileIds).set("task_id", taskId));
    }

    default int updateMessageId(List<String> fileIds, String messageId) {
        if (CollectionUtil.isEmpty(fileIds)) {
            return 0;
        }
        return update(new UpdateWrapper<AgentBuilderFileEntity>().in("id", fileIds).set("message_id", messageId));
    }

    default int softDeleteFiles(List<String> fileIds, String taskId) {
        return update(
            new UpdateWrapper<AgentBuilderFileEntity>().in("id", fileIds).in("task_id", taskId).set("deleted", true));
    }
}
