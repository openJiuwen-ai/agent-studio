/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 查询资源可用版本参数。
 */
@ApiModel(description = "查询资源可用版本参数。")

@Validated

public class ListVersionsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Size(max = 64)
    private String workspaceId = null;

    @JsonProperty("resource_type")
    @NotBlank
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Size(max = 64)
    private String resourceType = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListVersionsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public ListVersionsQo setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListVersionsQo {\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        ListVersionsQo listVersionsQo = (ListVersionsQo) o;
        return Objects.equals(this.workspaceId, listVersionsQo.workspaceId) && Objects.equals(this.resourceType,
            listVersionsQo.resourceType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, resourceType);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
