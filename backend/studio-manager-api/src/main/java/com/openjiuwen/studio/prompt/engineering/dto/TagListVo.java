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
 * TagListVo
 */

@Validated
public class TagListVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("total_page")
    @Schema(description = "总页数", example = "10")
    private Integer totalPage = null;

    @JsonProperty("data")
    @Schema(description = "数据列表", example = "")
    @Valid
    private List<TagVo> data = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "100")
    private Long count = null;

    @JsonProperty("has_next_page")
    @Schema(description = "是否有下一页", example = "false")
    private Boolean hasNextPage = false;

    public Integer getTotalPage() {
        return totalPage;
    }

    public TagListVo setTotalPage(Integer totalPage) {
        this.totalPage = totalPage;
        return this;
    }

    public List<TagVo> getData() {
        return data;
    }

    public TagListVo setData(List<TagVo> data) {
        this.data = data;
        return this;
    }

    public Long getCount() {
        return count;
    }

    public TagListVo setCount(Long count) {
        this.count = count;
        return this;
    }

    public TagListVo setHasNextPage(Boolean hasNextPage) {
        this.hasNextPage = hasNextPage;
        return this;
    }

    public Boolean isHasNextPage() {
        return hasNextPage;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TagListVo {\n");
        sb.append("    totalPage: ").append(toIndentedString(totalPage)).append("\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
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
        TagListVo tagListVo = (TagListVo) o;
        return Objects.equals(this.totalPage, tagListVo.totalPage) && Objects.equals(this.data, tagListVo.data)
            && Objects.equals(this.count, tagListVo.count) && Objects.equals(this.hasNextPage, tagListVo.hasNextPage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(totalPage, data, count, hasNextPage);
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
