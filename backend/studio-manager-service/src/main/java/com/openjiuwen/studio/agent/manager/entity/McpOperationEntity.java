/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.sql.Timestamp;

/**
 * FEAT-134 MCP 导入/重载操作主表（ws_mcp_operation）。
 */
@Data
public class McpOperationEntity {
    private String id;

    @JsonProperty("operation_type")
    private String operationType;

    @JsonProperty("tenant_id")
    private String tenantId;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("creator_id")
    private String creatorId;

    private String status;

    private Integer total;

    @JsonProperty("created_count")
    private Integer createdCount;

    @JsonProperty("success_count")
    private Integer successCount;

    @JsonProperty("failed_count")
    private Integer failedCount;

    @JsonProperty("created_date")
    private Timestamp createdDate;

    @JsonProperty("finished_date")
    private Timestamp finishedDate;

    @JsonProperty("deadline_date")
    private Timestamp deadlineDate;
}
