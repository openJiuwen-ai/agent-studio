/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * AuthWorkspaceInfo
 */

@Validated

public class AuthWorkspaceInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123")
    private String workspaceId = null;

    @JsonProperty("workspace_name")
    @Schema(description = "工作空间名称", example = "示例名称")
    private String workspaceName = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public AuthWorkspaceInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getWorkspaceName() {
        return workspaceName;
    }

    public AuthWorkspaceInfo setWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AuthWorkspaceInfo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    workspaceName: ").append(toIndentedString(workspaceName)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        AuthWorkspaceInfo authWorkspaceInfo = (AuthWorkspaceInfo) obj;
        return Objects.equals(this.workspaceId, authWorkspaceInfo.workspaceId) && Objects.equals(this.workspaceName,
            authWorkspaceInfo.workspaceName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, workspaceName);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }
}
