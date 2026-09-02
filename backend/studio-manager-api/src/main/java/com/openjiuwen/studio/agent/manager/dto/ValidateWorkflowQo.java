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
 * ValidateWorkflowQo: converted from multi query params
 */
@ApiModel(description = "ValidateWorkflowQo: converted from multi query params")

@Validated

public class ValidateWorkflowQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("version")
    @Schema(description = "版本号", example = "1")
    @Range(max = 9999999999999L)
    private Long version = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ValidateWorkflowQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public Long getVersion() {
        return version;
    }

    public ValidateWorkflowQo setVersion(Long version) {
        this.version = version;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ValidateWorkflowQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    version: ").append(toIndentedString(version)).append("\n");
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
        ValidateWorkflowQo validateWorkflowQo = (ValidateWorkflowQo) o;
        return Objects.equals(this.workspaceId, validateWorkflowQo.workspaceId) && Objects.equals(this.version,
            validateWorkflowQo.version);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, version);
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
