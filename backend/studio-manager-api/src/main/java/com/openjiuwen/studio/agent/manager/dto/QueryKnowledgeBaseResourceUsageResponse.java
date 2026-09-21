/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 查询知识库资源使用返回体
 */
@ApiModel(description = "查询知识库资源使用返回体")

@Validated

public class QueryKnowledgeBaseResourceUsageResponse implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("max_value")
    @Schema(description = "值", example = "1")
    private Long maxValue = null;

    @JsonProperty("used_value")
    @Schema(description = "已使用", example = "1")
    private Long usedValue = null;

    public Long getMaxValue() {
        return maxValue;
    }

    public QueryKnowledgeBaseResourceUsageResponse setMaxValue(Long maxValue) {
        this.maxValue = maxValue;
        return this;
    }

    public Long getUsedValue() {
        return usedValue;
    }

    public QueryKnowledgeBaseResourceUsageResponse setUsedValue(Long usedValue) {
        this.usedValue = usedValue;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryKnowledgeBaseResourceUsageResponse {\n");

        sb.append("    maxValue: ").append(toIndentedString(maxValue)).append("\n");
        sb.append("    usedValue: ").append(toIndentedString(usedValue)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        QueryKnowledgeBaseResourceUsageResponse queryKnowledgeBaseResourceUsageResponse
            = (QueryKnowledgeBaseResourceUsageResponse) o;
        return Objects.equals(this.maxValue, queryKnowledgeBaseResourceUsageResponse.maxValue) && Objects.equals(
            this.usedValue, queryKnowledgeBaseResourceUsageResponse.usedValue);
    }

    @Override
    public int hashCode() {
        return Objects.hash(maxValue, usedValue);
    }

    /**
     * Convert the given object to string with each line indented by 4 spaces
     * (except the first line).
     */
    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
