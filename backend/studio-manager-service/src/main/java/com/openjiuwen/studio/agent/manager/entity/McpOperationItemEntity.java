/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

import java.sql.Timestamp;

/**
 * FEAT-134 MCP 导入/重载操作逐项表（ws_mcp_operation_item）。
 */
@Data
public class McpOperationItemEntity {
    @JsonProperty("operation_id")
    private String operationId;

    @JsonProperty("item_index")
    private Integer itemIndex;

    @JsonProperty("service_id")
    private String serviceId;

    @JsonProperty("original_name")
    private String originalName;

    @JsonProperty("actual_name")
    private String actualName;

    private String status;

    @JsonProperty("refresh_status")
    private String refreshStatus;

    @JsonProperty("source_snapshot")
    private String sourceSnapshot;

    @JsonProperty("result_json")
    private String resultJson;

    @JsonProperty("error_code")
    private String errorCode;

    @JsonProperty("safe_reason")
    private String safeReason;

    @JsonProperty("started_date")
    private Timestamp startedDate;

    @JsonProperty("finished_date")
    private Timestamp finishedDate;
}
