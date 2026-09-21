/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;

/**
 * 批量修改记忆条目请求体。
 * 保持前端既有的一次提交多条已编辑条目的语义。
 */
public class UpdateMemoryItemRequestBody {
    @NotEmpty(message = "memories cannot be empty")
    @Valid
    @JsonProperty("memories")
    private List<UpdateMemoryItem> memories;

    public List<UpdateMemoryItem> getMemories() {
        return memories;
    }

    public void setMemories(List<UpdateMemoryItem> memories) {
        this.memories = memories;
    }

    /**
     * 单条待修改记忆：memory_id + 新内容。
     */
    public static class UpdateMemoryItem {
        @NotBlank(message = "memory_id cannot be blank")
        @JsonProperty("memory_id")
        private String memoryId;

        @NotBlank(message = "content cannot be blank")
        @JsonProperty("content")
        private String content;

        public String getMemoryId() {
            return memoryId;
        }

        public void setMemoryId(String memoryId) {
            this.memoryId = memoryId;
        }

        public String getContent() {
            return content;
        }

        public void setContent(String content) {
            this.content = content;
        }
    }
}
