/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotEmpty;

public class BatchDeleteMemoryItemRequestBody {
    @NotEmpty(message = "memory_ids cannot be empty")
    @JsonProperty("memory_ids")
    @Schema(description = "记忆", example = "[]")
    private List<String> memoryIds;

    public List<String> getMemoryIds() {
        return memoryIds;
    }

    public void setMemoryIds(List<String> memoryIds) {
        this.memoryIds = memoryIds;
    }
}
