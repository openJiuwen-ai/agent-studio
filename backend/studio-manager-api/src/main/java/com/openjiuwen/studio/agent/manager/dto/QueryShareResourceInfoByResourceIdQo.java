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
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * QueryShareResourceInfoByResourceIdQo: converted from multi query params
 */
@ApiModel(description = "QueryShareResourceInfoByResourceIdQo: converted from multi query params")

@Validated

public class QueryShareResourceInfoByResourceIdQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("release_version")
    @Schema(description = "发布版本", example = "1.0.0", required = true)
    @NotBlank
    private String releaseVersion = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "example-type")
    private String resourceType = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public QueryShareResourceInfoByResourceIdQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getReleaseVersion() {
        return releaseVersion;
    }

    public QueryShareResourceInfoByResourceIdQo setReleaseVersion(String releaseVersion) {
        this.releaseVersion = releaseVersion;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public QueryShareResourceInfoByResourceIdQo setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class QueryShareResourceInfoByResourceIdQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    releaseVersion: ").append(toIndentedString(releaseVersion)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
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
        QueryShareResourceInfoByResourceIdQo queryShareResourceInfoByResourceIdQo
            = (QueryShareResourceInfoByResourceIdQo) o;
        return Objects.equals(this.workspaceId, queryShareResourceInfoByResourceIdQo.workspaceId) && Objects.equals(
            this.releaseVersion, queryShareResourceInfoByResourceIdQo.releaseVersion) && Objects.equals(
            this.resourceType, queryShareResourceInfoByResourceIdQo.resourceType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, releaseVersion, resourceType);
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
