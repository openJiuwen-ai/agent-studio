/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 模型导出 JSONL 行 DTO：包装 {@link ModelExportEntity}，携带类型标识 {@code import_type}。
 *
 * <p>{@code @JsonIgnoreProperties(ignoreUnknown = true)} 用于前向兼容：导入时忽略文件中未知的额外字段，
 * 避免因导出端新增字段导致旧导入端解析失败。
 *
 * <p>{@code importType}（{@code import_type}）类型标识：导出端置 {@code MODEL_SERVICE}，导入端据此
 * 拒绝非模型文件（如工作流/agent 的 {@code import_type} 为 {@code workflow}/{@code agent}）。
 */
@Data
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ModelExportLine {
    @JsonProperty("import_type")
    private String importType;

    private ModelExportEntity payload;
}
