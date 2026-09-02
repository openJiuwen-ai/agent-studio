/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ListDeveloperAgentsQo: converted from multi query params
 */
@ApiModel(description = "ListDeveloperAgentsQo: converted from multi query params")

@Validated

public class ListDeveloperAgentsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("marker")
    @Schema(description = "marker", example = "1")
    @Range(min = 0L, max = 10000L)
    private Integer marker = 0;

    @JsonProperty("limit")
    @Schema(description = "每页数量", example = "10")
    @Range(min = 1L, max = 1000L)
    private Integer limit = 100;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListDeveloperAgentsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Integer getMarker() {
        return marker;
    }

    public ListDeveloperAgentsQo setMarker(Integer marker) {
        this.marker = marker;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ListDeveloperAgentsQo setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListDeveloperAgentsQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    marker: ").append(toIndentedString(marker)).append("\n");
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
        ListDeveloperAgentsQo listDeveloperAgentsQo = (ListDeveloperAgentsQo) o;
        return Objects.equals(this.workspaceId, listDeveloperAgentsQo.workspaceId) && Objects.equals(this.marker,
            listDeveloperAgentsQo.marker) && Objects.equals(this.limit, listDeveloperAgentsQo.limit);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, marker, limit);
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
