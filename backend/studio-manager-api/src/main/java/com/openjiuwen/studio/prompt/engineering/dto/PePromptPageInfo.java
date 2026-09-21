/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * PePromptPageInfo
 */

@Validated
public class PePromptPageInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("data")
    @Schema(description = "数据列表", example = "")
    @Valid
    private List<PePromptVo> data = null;

    @JsonProperty("total_page")
    @Schema(description = "总页数", example = "10")
    private Integer totalPage = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "10")
    private Integer count = null;

    @JsonProperty("has_next_page")
    @Schema(description = "是否有下一页", example = "false")
    private Boolean hasNextPage = false;

    public List<PePromptVo> getData() {
        return data;
    }

    public PePromptPageInfo setData(List<PePromptVo> data) {
        this.data = data;
        return this;
    }

    public Integer getTotalPage() {
        return totalPage;
    }

    public PePromptPageInfo setTotalPage(Integer totalPage) {
        this.totalPage = totalPage;
        return this;
    }

    public Integer getCount() {
        return count;
    }

    public PePromptPageInfo setCount(Integer count) {
        this.count = count;
        return this;
    }

    public PePromptPageInfo setHasNextPage(Boolean hasNextPage) {
        this.hasNextPage = hasNextPage;
        return this;
    }

    public Boolean isHasNextPage() {
        return hasNextPage;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class PePromptPageInfo {\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    totalPage: ").append(toIndentedString(totalPage)).append("\n");
        sb.append("    count: ").append(toIndentedString(count)).append("\n");
        sb.append("    hasNextPage: ").append(toIndentedString(hasNextPage)).append("\n");
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
        PePromptPageInfo pePromptPageInfo = (PePromptPageInfo) o;
        return Objects.equals(this.data, pePromptPageInfo.data) && Objects.equals(this.totalPage,
            pePromptPageInfo.totalPage) && Objects.equals(this.count, pePromptPageInfo.count) && Objects.equals(
            this.hasNextPage, pePromptPageInfo.hasNextPage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(data, totalPage, count, hasNextPage);
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
