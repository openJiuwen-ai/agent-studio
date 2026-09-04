/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.scheduler;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.List;

/**
 * 自动化任务执行日志响应体，与前端 ExecutionLog 结构对齐。
 */
@Data
@JsonInclude(JsonInclude.Include.ALWAYS)
public class ScheduledExecutionRsp {
    @JsonProperty("id")
    private String id;

    @JsonProperty("task_id")
    private String taskId;

    @JsonProperty("task_name")
    private String taskName;

    @JsonProperty("status")
    private String status;

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

    @JsonProperty("credits_used")
    private Long creditsUsed;

    @JsonProperty("retry_count")
    private Integer retryCount;

    @JsonProperty("artifacts")
    private List<Object> artifacts;
}
