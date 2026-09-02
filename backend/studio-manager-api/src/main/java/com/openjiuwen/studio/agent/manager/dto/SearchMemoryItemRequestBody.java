/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import jakarta.validation.constraints.NotNull;

@Data
public class SearchMemoryItemRequestBody {
    @Schema(description = "检索查询语句", example = "如何配置Agent")
    @NotNull
    private String query;

    @JsonProperty("top_k")
    @Schema(description = "Top-K参数", example = "1")
    private Integer topK = 5;

    @Schema(description = "相似度阈值", example = "0.5")
    private Double threshold = 0.5;

    @JsonProperty("memory_ids")
    @Schema(description = "记忆", example = "[]")
    private List<String> memoryIds;
}
