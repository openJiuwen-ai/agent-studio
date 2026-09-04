/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class ListMemoryItemResponseBody {
    @JsonProperty("items")
    private List<MemoryItemInfo> items;
    @JsonProperty("total")
    private Integer total;
    @JsonProperty("page_num")
    private Integer pageNum;
    @JsonProperty("page_size")
    private Integer pageSize;

    @Data
    public static class MemoryItemInfo {
        @JsonProperty("id")
        private String id;
        @JsonProperty("content")
        private String content;
        @JsonProperty("type")
        private String type;
        @JsonProperty("last_update_time")
        private String lastUpdateTime;
        @JsonProperty("score")
        private Float score;
        @JsonProperty("user_id")
        private String userId;
        @JsonProperty("agent_id")
        private String agentId;
    }
}
