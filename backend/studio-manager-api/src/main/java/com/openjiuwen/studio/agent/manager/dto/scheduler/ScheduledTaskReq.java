/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.scheduler;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.util.Map;

/**
 * 自动化任务创建/更新请求体。
 */
@Data
public class ScheduledTaskReq {
    @JsonProperty("name")
    private String name;

    @JsonProperty("description")
    private String description;

    @JsonProperty("workspace_id")
    private String workspaceId;

    /**
     * 调度配置：{"type": "cron", "config": {"expression": "..."}} /
     * {"type": "natural_language", "config": {"text": "..."}}
     */
    @JsonProperty("schedule")
    private ScheduleInfo schedule;

    /**
     * 重复配置：{"type": "once" | "always"}
     */
    @JsonProperty("repeat")
    private RepeatInfo repeat;

    /**
     * 生效时间，ISO8601 字符串或毫秒时间戳
     */
    @JsonProperty("valid_from")
    private Object validFrom;

    /**
     * 截止时间，ISO8601 字符串或毫秒时间戳
     */
    @JsonProperty("valid_until")
    private Object validUntil;

    /**
     * 执行器：{"type": "llm_prompt|agent_run|workflow_run|http_call", "config": {...}}
     */
    @JsonProperty("executor")
    private ExecutorInfo executor;

    @JsonProperty("model_id")
    private String modelId;

    @JsonProperty("prompt")
    private String prompt;

    @JsonProperty("notification")
    private NotificationInfo notification;

    @JsonProperty("max_retries")
    private Integer maxRetries;

    /**
     * 调度配置。
     */
    @Data
    public static class ScheduleInfo {
        @JsonProperty("type")
        private String type;

        @JsonProperty("config")
        private Map<String, Object> config;
    }

    /**
     * 重复配置。
     */
    @Data
    public static class RepeatInfo {
        @JsonProperty("type")
        private String type;
    }

    /**
     * 执行器配置。
     */
    @Data
    public static class ExecutorInfo {
        @JsonProperty("type")
        private String type;

        @JsonProperty("config")
        private Map<String, Object> config;
    }

    /**
     * 通知配置。
     */
    @Data
    public static class NotificationInfo {
        @JsonProperty("notify_on_success")
        private Boolean notifyOnSuccess;

        @JsonProperty("notify_on_failure")
        private Boolean notifyOnFailure;

        @JsonProperty("channels")
        private Object channels;
    }
}
