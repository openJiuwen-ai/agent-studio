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
 * GetWorkflowEnvsQo: converted from multi query params
 */
@ApiModel(description = "GetWorkflowEnvsQo: converted from multi query params")

@Validated

public class GetWorkflowEnvsQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("nestedCheck")
    @Schema(description = "nested检查", example = "true")
    private Boolean nestedCheck = false;

    @JsonProperty("versionId")
    @Schema(description = "版本ID", example = "example-id-123")
    private String versionId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public GetWorkflowEnvsQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public GetWorkflowEnvsQo setNestedCheck(Boolean nestedCheck) {
        this.nestedCheck = nestedCheck;
        return this;
    }

    public Boolean isNestedCheck() {
        return nestedCheck;
    }

    public String getVersionId() {
        return versionId;
    }

    public GetWorkflowEnvsQo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class GetWorkflowEnvsQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    nestedCheck: ").append(toIndentedString(nestedCheck)).append("\n");
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
        GetWorkflowEnvsQo getWorkflowEnvsQo = (GetWorkflowEnvsQo) o;
        return Objects.equals(this.workspaceId, getWorkflowEnvsQo.workspaceId) && Objects.equals(this.nestedCheck,
            getWorkflowEnvsQo.nestedCheck) && Objects.equals(this.versionId, getWorkflowEnvsQo.versionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, nestedCheck, versionId);
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
