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
 * ListComplexIntentBranchQo: converted from multi query params
 */
@ApiModel(description = "ListComplexIntentBranchQo: converted from multi query params")

@Validated

public class ListComplexIntentBranchQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Pattern(regexp = "^.{0,64}$")
    @Length(max = 192)
    private String name = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @NotBlank
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    public String getName() {
        return name;
    }

    public ListComplexIntentBranchQo setName(String name) {
        this.name = name;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ListComplexIntentBranchQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ListComplexIntentBranchQo {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        ListComplexIntentBranchQo listComplexIntentBranchQo = (ListComplexIntentBranchQo) o;
        return Objects.equals(this.name, listComplexIntentBranchQo.name) && Objects.equals(this.workspaceId,
            listComplexIntentBranchQo.workspaceId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, workspaceId);
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
