/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.manager.entity.ScheduledTaskEntity;

import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 自动化定时任务 Mapper。
 */
@Mapper
public interface ScheduledTaskMapper {
    @Insert("INSERT INTO t_scheduled_task (id, project_id, workspace_id, creator_id, creator_name, name, description,"
        + " status, schedule_type, schedule_config, repeat_type, valid_from, valid_until, executor_type,"
        + " executor_config, model_id, prompt, max_retries, notification, last_run_at, next_run_at,"
        + " last_run_status, run_count, created_at, updated_at) VALUES (#{id}, #{projectId}, #{workspaceId},"
        + " #{creatorId}, #{creatorName}, #{name}, #{description}, #{status}, #{scheduleType}, #{scheduleConfig},"
        + " #{repeatType}, #{validFrom}, #{validUntil}, #{executorType}, #{executorConfig}, #{modelId}, #{prompt},"
        + " #{maxRetries}, #{notification}, #{lastRunAt}, #{nextRunAt}, #{lastRunStatus}, #{runCount}, #{createdAt},"
        + " #{updatedAt})")
    int insert(ScheduledTaskEntity entity);

    @Update("UPDATE t_scheduled_task SET name = #{name}, description = #{description}, status = #{status},"
        + " schedule_type = #{scheduleType}, schedule_config = #{scheduleConfig}, repeat_type = #{repeatType},"
        + " valid_from = #{validFrom}, valid_until = #{validUntil}, executor_type = #{executorType},"
        + " executor_config = #{executorConfig}, model_id = #{modelId}, prompt = #{prompt},"
        + " max_retries = #{maxRetries}, notification = #{notification}, next_run_at = #{nextRunAt},"
        + " updated_at = #{updatedAt} WHERE id = #{id}")
    int updateById(ScheduledTaskEntity entity);

    @Select("SELECT * FROM t_scheduled_task WHERE id = #{id}")
    ScheduledTaskEntity selectById(@Param("id") String id);

    @Select("<script>SELECT * FROM t_scheduled_task WHERE project_id = #{projectId} AND workspace_id = #{workspaceId}"
        + "<if test='status != null and status != \"\"'> AND status = #{status}</if>"
        + "<if test='search != null and search != \"\"'> AND name LIKE CONCAT('%', #{search}, '%')</if>"
        + " ORDER BY created_at DESC LIMIT #{limit} OFFSET #{offset}</script>")
    List<ScheduledTaskEntity> selectPage(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("status") String status, @Param("search") String search, @Param("offset") int offset,
        @Param("limit") int limit);

    @Select("<script>SELECT COUNT(*) FROM t_scheduled_task WHERE project_id = #{projectId}"
        + " AND workspace_id = #{workspaceId}"
        + "<if test='status != null and status != \"\"'> AND status = #{status}</if>"
        + "<if test='search != null and search != \"\"'> AND name LIKE CONCAT('%', #{search}, '%')</if></script>")
    long selectCount(@Param("projectId") String projectId, @Param("workspaceId") String workspaceId,
        @Param("status") String status, @Param("search") String search);

    @Update("UPDATE t_scheduled_task SET status = #{status}, next_run_at = #{nextRunAt}, updated_at = #{updatedAt}"
        + " WHERE id = #{id}")
    int updateStatus(@Param("id") String id, @Param("status") String status, @Param("nextRunAt") Long nextRunAt,
        @Param("updatedAt") Long updatedAt);

    @Update("UPDATE t_scheduled_task SET last_run_at = #{lastRunAt}, next_run_at = #{nextRunAt},"
        + " last_run_status = #{lastRunStatus}, run_count = run_count + 1, updated_at = #{updatedAt} WHERE id = #{id}")
    int updateRunInfo(@Param("id") String id, @Param("lastRunAt") Long lastRunAt, @Param("nextRunAt") Long nextRunAt,
        @Param("lastRunStatus") String lastRunStatus, @Param("updatedAt") Long updatedAt);

    @Delete("DELETE FROM t_scheduled_task WHERE id = #{id}")
    int deleteById(@Param("id") String id);
}
