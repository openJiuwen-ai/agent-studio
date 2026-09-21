/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * ParamExtractionExceptionConfig
 */

@Validated

public class ParamExtractionExceptionConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("max_iteration")
    @Schema(description = "maxiteration", example = "10")
    private Integer maxIteration = null;

    @JsonProperty("exception_condition")
    @Schema(description = "exceptioncondition", example = "示例字符串")
    @Valid
    @Size()
    private Map<String, Object> exceptionCondition = null;

    public Integer getMaxIteration() {
        return maxIteration;
    }

    public ParamExtractionExceptionConfig setMaxIteration(Integer maxIteration) {
        this.maxIteration = maxIteration;
        return this;
    }

    public Map<String, Object> getExceptionCondition() {
        return exceptionCondition;
    }

    public ParamExtractionExceptionConfig setExceptionCondition(Map<String, Object> exceptionCondition) {
        this.exceptionCondition = exceptionCondition;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ParamExtractionExceptionConfig {\n");

        sb.append("    maxIteration: ").append(toIndentedString(maxIteration)).append("\n");
        sb.append("    exceptionCondition: ").append(toIndentedString(exceptionCondition)).append("\n");
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
        ParamExtractionExceptionConfig paramExtractionExceptionConfig = (ParamExtractionExceptionConfig) o;
        return Objects.equals(this.maxIteration, paramExtractionExceptionConfig.maxIteration) && Objects.equals(
            this.exceptionCondition, paramExtractionExceptionConfig.exceptionCondition);
    }

    @Override
    public int hashCode() {
        return Objects.hash(maxIteration, exceptionCondition);
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
