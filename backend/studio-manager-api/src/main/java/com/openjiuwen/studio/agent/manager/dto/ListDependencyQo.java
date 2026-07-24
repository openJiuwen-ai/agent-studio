/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 查询资源依赖的子资源参数。
 */
@ApiModel(description = "查询资源依赖的子资源参数。")

@Validated

public class ListDependencyQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Size(max = 64)
    private String workspaceId = null;

    @JsonProperty("version_id")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Size(max = 64)
    private String versionId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListDependencyQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public ListDependencyQo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListDependencyQo {\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
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
        ListDependencyQo listDependencyQo = (ListDependencyQo) o;
        return Objects.equals(this.workspaceId, listDependencyQo.workspaceId) && Objects.equals(this.versionId,
            listDependencyQo.versionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, versionId);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
