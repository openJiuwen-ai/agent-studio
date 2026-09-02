/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryApiKeysQo: converted from multi query params
 */
@ApiModel(description = "QueryApiKeysQo: converted from multi query params")

@Validated

public class QueryApiKeysQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("page_size")
    @Schema(description = "每页数量", example = "0")
    @Range(min = 1L, max = 1000L)
    private Integer pageSize = 10;

    @JsonProperty("page_num")
    @Schema(description = "页码", example = "0")
    @Range(min = 0L)
    private Integer pageNum = 0;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public QueryApiKeysQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getPageSize() {
        return pageSize;
    }

    public QueryApiKeysQo setPageSize(Integer pageSize) {
        this.pageSize = pageSize;
        return this;
    }

    public Integer getPageNum() {
        return pageNum;
    }

    public QueryApiKeysQo setPageNum(Integer pageNum) {
        this.pageNum = pageNum;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryApiKeysQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    pageSize: ").append(toIndentedString(pageSize)).append("\n");
        sb.append("    pageNum: ").append(toIndentedString(pageNum)).append("\n");
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
        QueryApiKeysQo queryApiKeysQo = (QueryApiKeysQo) o;
        return Objects.equals(this.workspaceId, queryApiKeysQo.workspaceId) && Objects.equals(this.pageSize,
            queryApiKeysQo.pageSize) && Objects.equals(this.pageNum, queryApiKeysQo.pageNum);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, pageSize, pageNum);
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
