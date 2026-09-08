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
 * 自主动态规划模式指南间依赖关系。
 */
@ApiModel(description = "自主动态规划模式指南间依赖关系。")

@Validated

public class RelationInGuideLine implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("type")
    @Schema(description = "类型", example = "example-type")
    private String type = null;

    @JsonProperty("src")
    @Schema(description = "src", example = "1")
    private Integer src = null;

    @JsonProperty("tgt")
    @Schema(description = "tgt", example = "1")
    private Integer tgt = null;

    public String getType() {
        return type;
    }

    public RelationInGuideLine setType(String type) {
        this.type = type;
        return this;
    }

    public Integer getSrc() {
        return src;
    }

    public RelationInGuideLine setSrc(Integer src) {
        this.src = src;
        return this;
    }

    public Integer getTgt() {
        return tgt;
    }

    public RelationInGuideLine setTgt(Integer tgt) {
        this.tgt = tgt;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class RelationInGuideLine {\n");

        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    src: ").append(toIndentedString(src)).append("\n");
        sb.append("    tgt: ").append(toIndentedString(tgt)).append("\n");
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
        RelationInGuideLine relationInGuideLine = (RelationInGuideLine) o;
        return Objects.equals(this.type, relationInGuideLine.type) && Objects.equals(this.src, relationInGuideLine.src)
            && Objects.equals(this.tgt, relationInGuideLine.tgt);
    }

    @Override
    public int hashCode() {
        return Objects.hash(type, src, tgt);
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
