/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.ScheduledTaskExecutionEntity;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 自动化定时任务执行日志 Mapper。
 */
@Mapper
public interface ScheduledTaskExecutionMapper {
    @Insert("INSERT INTO t_scheduled_task_execution (id, task_id, project_id, workspace_id, status, trigger_type,"
        + " started_at, finished_at, duration_ms, error_message, model_output, retry_count) VALUES (#{id}, #{taskId},"
        + " #{projectId}, #{workspaceId}, #{status}, #{triggerType}, #{startedAt}, #{finishedAt}, #{durationMs},"
        + " #{errorMessage}, #{modelOutput}, #{retryCount})")
    int insert(ScheduledTaskExecutionEntity entity);

    @Update("UPDATE t_scheduled_task_execution SET status = #{status}, finished_at = #{finishedAt},"
        + " duration_ms = #{durationMs}, error_message = #{errorMessage}, model_output = #{modelOutput},"
        + " retry_count = #{retryCount} WHERE id = #{id}")
    int updateFinish(ScheduledTaskExecutionEntity entity);

    @Select("<script>SELECT * FROM t_scheduled_task_execution WHERE task_id = #{taskId}"
        + "<if test='status != null and status != \"\"'> AND status = #{status}</if>"
        + " ORDER BY started_at DESC LIMIT #{limit} OFFSET #{offset}</script>")
    List<ScheduledTaskExecutionEntity> selectPageByTaskId(@Param("taskId") String taskId,
        @Param("status") String status, @Param("offset") int offset, @Param("limit") int limit);

    @Select("<script>SELECT COUNT(*) FROM t_scheduled_task_execution WHERE task_id = #{taskId}"
        + "<if test='status != null and status != \"\"'> AND status = #{status}</if></script>")
    long selectCountByTaskId(@Param("taskId") String taskId, @Param("status") String status);

    @Delete("DELETE FROM t_scheduled_task_execution WHERE task_id = #{taskId}")
    int deleteByTaskId(@Param("taskId") String taskId);
}
