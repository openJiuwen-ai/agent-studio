/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * MemberOwnershipBody
 */

@Validated

public class MemberOwnershipBody implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("next_owner_id")
    @Schema(description = "下一页", example = "example-id-123", required = true)
    @NotBlank
    private String nextOwnerId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public MemberOwnershipBody setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getNextOwnerId() {
        return nextOwnerId;
    }

    public MemberOwnershipBody setNextOwnerId(String nextOwnerId) {
        this.nextOwnerId = nextOwnerId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MemberOwnershipBody {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    nextOwnerId: ").append(toIndentedString(nextOwnerId)).append("\n");
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
        MemberOwnershipBody memberOwnershipBody = (MemberOwnershipBody) o;
        return Objects.equals(this.workspaceId, memberOwnershipBody.workspaceId) && Objects.equals(this.nextOwnerId,
            memberOwnershipBody.nextOwnerId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, nextOwnerId);
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
