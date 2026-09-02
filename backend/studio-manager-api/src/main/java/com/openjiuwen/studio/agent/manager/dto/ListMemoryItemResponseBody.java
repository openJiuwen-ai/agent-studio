/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class ListMemoryItemResponseBody {
    @JsonProperty("items")
    @Schema(description = "记忆项列表", example = "[]")
    private List<MemoryItemInfo> items;
    @JsonProperty("total")
    @Schema(description = "总数", example = "100")
    private Integer total;
    @JsonProperty("page_num")
    @Schema(description = "页码", example = "1")
    private Integer pageNum;
    @JsonProperty("page_size")
    @Schema(description = "每页数量", example = "10")
    private Integer pageSize;

    @Data
    public static class MemoryItemInfo {
        @JsonProperty("id")
        @Schema(description = "记忆项ID", example = "mem_001")
        private String id;
        @JsonProperty("content")
        @Schema(description = "记忆内容", example = "用户偏好设置")
        private String content;
        @JsonProperty("score")
        @Schema(description = "相关性分数", example = "0.95")
        private Float score;
        @JsonProperty("user_id")
        @Schema(description = "用户ID", example = "user001")
        private String userId;
        @JsonProperty("agent_id")
        @Schema(description = "Agent ID", example = "agent_001")
        private String agentId;
    }
}
