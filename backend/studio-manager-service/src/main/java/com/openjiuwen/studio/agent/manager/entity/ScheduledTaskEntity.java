/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

/**
 * 自动化定时任务实体。
 */
@Data
public class ScheduledTaskEntity {
    @JsonProperty("id")
    private String id;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("creator_name")
    private String creatorName;

    @JsonProperty("name")
    private String name;

    @JsonProperty("description")
    private String description;

    /**
     * 状态：enabled / disabled
     */
    @JsonProperty("status")
    private String status;

    /**
     * 调度类型：cron / natural_language
     */
    @JsonProperty("schedule_type")
    private String scheduleType;

    /**
     * 调度配置JSON：{"expression": "...", "text": "...", "run_at": ...}
     */
    @JsonProperty("schedule_config")
    private String scheduleConfig;

    /**
     * 重复类型：once / always
     */
    @JsonProperty("repeat_type")
    private String repeatType;

    @JsonProperty("valid_from")
    private Long validFrom;

    @JsonProperty("valid_until")
    private Long validUntil;

    /**
     * 执行方式：llm_prompt / agent_run / workflow_run / http_call
     */
    @JsonProperty("executor_type")
    private String executorType;

    /**
     * 执行配置JSON：{"agent_id": "..", "query": ".."} / {"workflow_id": "..", "inputs": {...}} / {"url": ".."}
     */
    @JsonProperty("executor_config")
    private String executorConfig;

    @JsonProperty("model_id")
    private String modelId;

    @JsonProperty("prompt")
    private String prompt;

    @JsonProperty("max_retries")
    private Integer maxRetries;

    /**
     * 通知配置JSON：{"notify_on_success": true, "notify_on_failure": true, "channels": ["in_app"]}
     */
    @JsonProperty("notification")
    private String notification;

    @JsonProperty("last_run_at")
    private Long lastRunAt;

    @JsonProperty("next_run_at")
    private Long nextRunAt;

    @JsonProperty("last_run_status")
    private String lastRunStatus;

    @JsonProperty("run_count")
    private Long runCount;

    @JsonProperty("created_at")
    private Long createdAt;

    @JsonProperty("updated_at")
    private Long updatedAt;
}
