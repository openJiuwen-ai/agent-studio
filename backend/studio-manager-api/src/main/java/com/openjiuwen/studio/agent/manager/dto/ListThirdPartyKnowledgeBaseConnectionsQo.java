/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

@ApiModel(description = "ListThirdPartyKnowledgeBaseConnectionsQo: converted from multi query params")

@Validated
@Data
public class ListThirdPartyKnowledgeBaseConnectionsQo {

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("name")
    @Schema(description = "连接名称", example = "我的知识库连接")
    @Length(max = 50)
    private String name = null;

    @JsonProperty("status")
    @Schema(description = "连接状态", example = "active")
    private String status = null;

    @JsonProperty("connector_id")
    @Schema(description = "连接器ID", example = "connector-001")
    @Length(max = 100)
    private String connectorId = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

}
