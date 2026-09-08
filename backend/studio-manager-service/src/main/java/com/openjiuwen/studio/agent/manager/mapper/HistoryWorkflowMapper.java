/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * workflow 数据库操作mapper
 *
 */
@Mapper
public interface HistoryWorkflowMapper {

    /**
     * 工作流插入历史库
     *
     * @param workflowEntity 待插入工作流
     * @return 插入成功数量
     */
    int insert(WorkflowEntity workflowEntity);

    /**
     * 查询小于某个时间的工作流ID集合
     * @param time epoch毫秒时间戳
     * @return 小于某个时间的工作流ID集合
     */
    List<String> findByUpdatedOnLessThan(@Param("time") Long time);

    /**
     * 删除的数量
     * @param workflowIds 需要删除的工作流ID列表
     * @return 删除的数量
     */
    int deleteByPrimaryKeys(@Param("workflowIds") List<String> workflowIds);

    /**
     * 根据workflow id列表查询workflow信息
     *
     * @param projectId projectId
     * @param workflowIds workflowIds
     * @return 符合条件的工作流列表
     */
    List<WorkflowEntity> selectByWorkflowIds(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId, @Param("workflowIds") List<String> workflowIds);
}
