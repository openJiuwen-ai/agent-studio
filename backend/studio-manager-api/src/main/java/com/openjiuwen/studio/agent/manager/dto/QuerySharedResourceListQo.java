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
 * QuerySharedResourceListQo: converted from multi query params
 */
@ApiModel(description = "QuerySharedResourceListQo: converted from multi query params")

@Validated

public class QuerySharedResourceListQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws-001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "agent", required = true)
    @NotBlank
    private String resourceType = null;

    @JsonProperty("resource_name")
    @Schema(description = "资源名称", example = "resource-name")
    @Length(max = 64)
    private String resourceName = null;

    @JsonProperty("offset")
    @Schema(description = "偏移量", example = "0")
    @Range(min = 0L, max = 10000L)
    private Integer offset = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 10;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public QuerySharedResourceListQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public QuerySharedResourceListQo setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public QuerySharedResourceListQo setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public Integer getOffset() {
        return offset;
    }

    public QuerySharedResourceListQo setOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public QuerySharedResourceListQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QuerySharedResourceListQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    offset: ").append(toIndentedString(offset)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
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
        QuerySharedResourceListQo querySharedResourceListQo = (QuerySharedResourceListQo) o;
        return Objects.equals(this.workspaceId, querySharedResourceListQo.workspaceId) && Objects.equals(
            this.resourceType, querySharedResourceListQo.resourceType) && Objects.equals(this.resourceName,
            querySharedResourceListQo.resourceName) && Objects.equals(this.offset, querySharedResourceListQo.offset)
            && Objects.equals(this.limit, querySharedResourceListQo.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, resourceType, resourceName, offset, limit);
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
