/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

/**
 * 自动化定时任务执行日志实体。
 */
@Data
public class ScheduledTaskExecutionEntity {
    @JsonProperty("id")
    private String id;

    @JsonProperty("task_id")
    private String taskId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    /**
     * 执行状态：pending / running / success / failed / retrying
     */
    @JsonProperty("status")
    private String status;

    /**
     * 触发方式：scheduled / manual / retry
     */
    @JsonProperty("trigger_type")
    private String triggerType;

    @JsonProperty("started_at")
    private Long startedAt;

    @JsonProperty("finished_at")
    private Long finishedAt;

    @JsonProperty("duration_ms")
    private Long durationMs;

    @JsonProperty("error_message")
    private String errorMessage;

    @JsonProperty("model_output")
    private String modelOutput;

    @JsonProperty("retry_count")
    private Integer retryCount;
}
