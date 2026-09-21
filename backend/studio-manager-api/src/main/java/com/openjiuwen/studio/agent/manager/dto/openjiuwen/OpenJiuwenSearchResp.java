/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 检索 openjiuwen 知识库响应。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenSearchResp {

    @Schema(description = "检索结果列表", example = "[]")
    private List<SearchResultItem> results;

    /**
     * 单条检索结果。
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchResultItem {

        @Schema(description = "检索文本内容", example = "Agent是一种智能助手")
        private String text;

        @Schema(description = "相似度得分", example = "0.95")
        private Double score;

        @Schema(description = "元数据", example = "{}")
        private Map<String, Object> metadata;
    }
}
