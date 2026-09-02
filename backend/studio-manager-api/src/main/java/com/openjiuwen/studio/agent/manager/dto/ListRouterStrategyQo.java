/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListRouterStrategyQo: converted from multi query params
 */
@ApiModel(description = "ListRouterStrategyQo: converted from multi query params")

@Validated

public class ListRouterStrategyQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("page_size")
    @Schema(description = "每页大小", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer pageSize = 10;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "0")
    @Range(min = 0L)
    private Integer pageNum = 0;

    @JsonProperty("query")
    @Schema(description = "查询关键词", example = "搜索")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9._ /:|\\\\-]{0,64}$")
    @Length(max = 64)
    private String query = null;

    @JsonProperty("sort_by")
    @Schema(description = "排序字段", example = "name")
    @Length(max = 32)
    private String sortBy = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListRouterStrategyQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public ListRouterStrategyQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public ListRouterStrategyQo setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    public String getQuery() {
        return query;
    }

    public ListRouterStrategyQo setQuery(String query) {
        this.query = query;
        return this;
    }

    public String getSortBy() {
        return sortBy;
    }

    public ListRouterStrategyQo setSortBy(String sortBy) {
        this.sortBy = sortBy;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListRouterStrategyQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
        sb.append("    query: ").append(toIndentedString(query)).append("\n");
        sb.append("    sortBy: ").append(toIndentedString(sortBy)).append("\n");
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
        ListRouterStrategyQo listRouterStrategyQo = (ListRouterStrategyQo) o;
        return Objects.equals(this.workspaceId, listRouterStrategyQo.workspaceId) && Objects.equals(this.pageSize,
            listRouterStrategyQo.pageSize) && Objects.equals(this.pageNum, listRouterStrategyQo.pageNum)
            && Objects.equals(this.query, listRouterStrategyQo.query) && Objects.equals(this.sortBy,
            listRouterStrategyQo.sortBy);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, pageSize, pageNum, query, sortBy);
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
