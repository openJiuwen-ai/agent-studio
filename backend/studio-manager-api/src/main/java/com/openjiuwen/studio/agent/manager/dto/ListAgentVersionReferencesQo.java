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
 * ListAgentVersionReferencesQo: converted from multi query params
 */
@ApiModel(description = "ListAgentVersionReferencesQo: converted from multi query params")

@Validated

public class ListAgentVersionReferencesQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID，不传则返回全部版本", example = "1787901244768")
    @Pattern(regexp = "^[0-9]+$")
    @Length(min = 1, max = 64)
    private String versionId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListAgentVersionReferencesQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public ListAgentVersionReferencesQo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListAgentVersionReferencesQo {\n");

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
        ListAgentVersionReferencesQo listAgentVersionReferencesQo = (ListAgentVersionReferencesQo) o;
        return Objects.equals(this.workspaceId, listAgentVersionReferencesQo.workspaceId)
            && Objects.equals(this.versionId, listAgentVersionReferencesQo.versionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, versionId);
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
