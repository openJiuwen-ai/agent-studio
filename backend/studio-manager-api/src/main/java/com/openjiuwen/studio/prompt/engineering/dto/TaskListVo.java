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
 * TaskListVo
 */

@Validated
public class TaskListVo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("total_page")
    @Schema(description = "总页数", example = "10")
    private Integer totalPage = null;

    @JsonProperty("data")
    @Schema(description = "数据列表", example = "")
    @Valid
    private List<TaskVo> data = null;

    @JsonProperty("count")
    @Schema(description = "数量", example = "100")
    private Long count = null;

    @JsonProperty("has_next_page")
    @Schema(description = "是否有下一页", example = "false")
    private Boolean hasNextPage = false;

    public Integer getTotalPage() {
        return totalPage;
    }

    public TaskListVo setTotalPage(Integer totalPage) {
        this.totalPage = totalPage;
        return this;
    }

    public List<TaskVo> getData() {
        return data;
    }

    public TaskListVo setData(List<TaskVo> data) {
        this.data = data;
        return this;
    }

    public Long getCount() {
        return count;
    }

    public TaskListVo setCount(Long count) {
        this.count = count;
        return this;
    }

    public TaskListVo setHasNextPage(Boolean hasNextPage) {
        this.hasNextPage = hasNextPage;
        return this;
    }

    public Boolean isHasNextPage() {
        return hasNextPage;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TaskListVo {\n");
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
        TaskListVo taskListVo = (TaskListVo) o;
        return Objects.equals(this.totalPage, taskListVo.totalPage) && Objects.equals(this.data, taskListVo.data)
            && Objects.equals(this.count, taskListVo.count) && Objects.equals(this.hasNextPage, taskListVo.hasNextPage);
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
