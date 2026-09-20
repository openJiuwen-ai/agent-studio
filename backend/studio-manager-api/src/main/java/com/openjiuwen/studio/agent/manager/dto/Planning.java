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
 * 自主动态规划配置项。
 */
@ApiModel(description = "自主动态规划配置项。")

@Validated

public class Planning implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("max_step")
    @Schema(description = "最大步数", example = "10")
    private Integer maxStep = 10;

    @JsonProperty("allow_replanning")
    @Schema(description = "是否允许重新规划", example = "true")
    private Boolean allowReplanning = false;

    public Integer getMaxStep() {
        return maxStep;
    }

    public Planning setMaxStep(Integer maxStep) {
        this.maxStep = maxStep;
        return this;
    }

    public Planning setAllowReplanning(Boolean allowReplanning) {
        this.allowReplanning = allowReplanning;
        return this;
    }

    public Boolean isAllowReplanning() {
        return allowReplanning;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Planning {\n");

        sb.append("    maxStep: ").append(toIndentedString(maxStep)).append("\n");
        sb.append("    allowReplanning: ").append(toIndentedString(allowReplanning)).append("\n");
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
        Planning planning = (Planning) o;
        return Objects.equals(this.maxStep, planning.maxStep) && Objects.equals(this.allowReplanning,
            planning.allowReplanning);
    }

    @Override
    public int hashCode() {
        return Objects.hash(maxStep, allowReplanning);
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
