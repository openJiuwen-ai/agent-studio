/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.scheduler;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 自动化任务响应体，与前端 ScheduledTask 结构对齐。
 */
@Data
@JsonInclude(JsonInclude.Include.ALWAYS)
public class ScheduledTaskRsp {
    @JsonProperty("id")
    private String id;

    @JsonProperty("tenant_id")
    private String tenantId;

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

    @JsonProperty("status")
    private String status;

    @JsonProperty("schedule_type")
    private String scheduleType;

    @JsonProperty("schedule_config")
    private Map<String, Object> scheduleConfig;

    @JsonProperty("schedule_description")
    private String scheduleDescription;

    @JsonProperty("repeat_type")
    private String repeatType;

    @JsonProperty("valid_from")
    private Long validFrom;

    @JsonProperty("valid_until")
    private Long validUntil;

    @JsonProperty("executor_type")
    private String executorType;

    @JsonProperty("executor_config")
    private Map<String, Object> executorConfig;

    @JsonProperty("model_id")
    private String modelId;

    @JsonProperty("prompt")
    private String prompt;

    @JsonProperty("skills")
    private List<String> skills;

    @JsonProperty("connector_type")
    private String connectorType;

    @JsonProperty("max_retries")
    private Integer maxRetries;

    @JsonProperty("notification")
    private Map<String, Object> notification;

    @JsonProperty("is_running")
    private Boolean isRunning;

    @JsonProperty("last_run_at")
    private Long lastRunAt;

    @JsonProperty("next_run_at")
    private Long nextRunAt;

    @JsonProperty("last_run_status")
    private String lastRunStatus;

    @JsonProperty("run_count")
    private Long runCount;

    @JsonProperty("total_credits_used")
    private Long totalCreditsUsed;

    @JsonProperty("created_at")
    private Long createdAt;

    @JsonProperty("updated_at")
    private Long updatedAt;
}
