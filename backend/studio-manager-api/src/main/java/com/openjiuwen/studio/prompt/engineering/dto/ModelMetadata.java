/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 模型最大token数量
 */
@ApiModel(description = "模型最大token数量")

@Validated
public class ModelMetadata implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("max_tokens")
    @Schema(description = "最大Token数", example = "1024")
    private Integer maxTokens = null;

    public Integer getMaxTokens() {
        return maxTokens;
    }

    public ModelMetadata setMaxTokens(Integer maxTokens) {
        this.maxTokens = maxTokens;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelMetadata {\n");
        sb.append("    maxTokens: ").append(toIndentedString(maxTokens)).append("\n");
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
        ModelMetadata modelMetadata = (ModelMetadata) o;
        return Objects.equals(this.maxTokens, modelMetadata.maxTokens);
    }

    @Override
    public int hashCode() {
        return Objects.hash(maxTokens);
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
