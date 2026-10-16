/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import lombok.Data;

/**
 * 运行时资产导出请求参数（对应 SDD 4.4.2）。
 * resource_type 取值对齐现有 ResourceTypeEnum：agent / controller / workflow。
 */
@Data
public class RuntimeAssetExportParams {

    @NotBlank
    @Pattern(regexp = "^(agent|controller|workflow)$",
        message = "resource_type 只支持 agent / controller / workflow")
    @JsonProperty("resource_type")
    @Schema(description = "导出类型：agent(单智能体) / controller(多智能体) / workflow(工作流)",
        example = "agent", required = true)
    private String resourceType;

    @NotBlank
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$", message = "resource_id 只支持字母、数字、下划线、短横线")
    @JsonProperty("resource_id")
    @Schema(description = "要导出的应用 ID（智能体 ID 或工作流 ID）", example = "agent-uuid-001",
        required = true)
    private String resourceId;

    @JsonProperty("version")
    @Schema(description = "版本号，缺省或 \"latest\" 导出当前发布版本", example = "1728465600000")
    private String version;
}
