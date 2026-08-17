/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto.openjiuwen;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

/**
 * 检索 openjiuwen 知识库响应。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OpenJiuwenSearchResp implements Serializable {

    private static final long serialVersionUID = 1L;

    private List<SearchResultItem> results;

    /**
     * 单条检索结果。
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SearchResultItem implements Serializable {

        private static final long serialVersionUID = 1L;

        private String text;

        private Double score;

        private Map<String, Object> metadata;
    }
}
