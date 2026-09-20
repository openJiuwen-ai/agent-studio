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
 * 开发者空间查询分页信息
 */
@ApiModel(description = "开发者空间查询分页信息")

@Validated

public class DeveloperSpacePage implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("next_marker")
    @Schema(description = "下一页", example = "示例字符串")
    private String nextMarker = null;

    @JsonProperty("previous_marker")
    @Schema(description = "上一页", example = "示例字符串")
    private String previousMarker = null;

    @JsonProperty("current_count")
    @Schema(description = "数量", example = "10")
    private Integer currentCount = null;

    public String getNextMarker() {
        return nextMarker;
    }

    public DeveloperSpacePage setNextMarker(String nextMarker) {
        this.nextMarker = nextMarker;
        return this;
    }

    public String getPreviousMarker() {
        return previousMarker;
    }

    public DeveloperSpacePage setPreviousMarker(String previousMarker) {
        this.previousMarker = previousMarker;
        return this;
    }

    public Integer getCurrentCount() {
        return currentCount;
    }

    public DeveloperSpacePage setCurrentCount(Integer currentCount) {
        this.currentCount = currentCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DeveloperSpacePage {\n");

        sb.append("    nextMarker: ").append(toIndentedString(nextMarker)).append("\n");
        sb.append("    previousMarker: ").append(toIndentedString(previousMarker)).append("\n");
        sb.append("    currentCount: ").append(toIndentedString(currentCount)).append("\n");
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
        DeveloperSpacePage developerSpacePage = (DeveloperSpacePage) o;
        return Objects.equals(this.nextMarker, developerSpacePage.nextMarker) && Objects.equals(this.previousMarker,
            developerSpacePage.previousMarker) && Objects.equals(this.currentCount, developerSpacePage.currentCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nextMarker, previousMarker, currentCount);
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
