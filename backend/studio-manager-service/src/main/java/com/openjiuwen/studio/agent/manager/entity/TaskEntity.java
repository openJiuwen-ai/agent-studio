/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Builder;
import lombok.Data;

import java.util.Date;

/**
 * 任务实体
 */
@Data
@Builder
public class TaskEntity {
    private String id;
    private String name;
    @JsonProperty("conversation_id")
    private String conversationId;
    @JsonProperty("user_id")
    private String userId;
    @JsonProperty("domain_id")
    private String domainId;
    @JsonProperty("workspace_id")
    private String workspaceId;
    @JsonProperty("project_id")
    private String projectId;
    private String type;
    private String mode;
    @JsonProperty("app_id")
    private String appId;
    @JsonProperty("app_version")
    private String appVersion;
    @JsonProperty("is_published")
    private Boolean isPublished;
    private String status;
    private String inputs;
    private String outputs;
    private Integer timeout;
    private String message;
    @JsonProperty("create_time")
    private Date createTime;
    @JsonProperty("start_time")
    private Date startTime;
    @JsonProperty("update_time")
    private Date updateTime;
    @JsonProperty("finish_time")
    private Date finishTime;
}