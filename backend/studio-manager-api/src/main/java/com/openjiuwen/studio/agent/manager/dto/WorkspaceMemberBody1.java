/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * WorkspaceMemberBody1
 */

@Validated

public class WorkspaceMemberBody1 implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("members")
    @Schema(description = "成员列表", example = "[]", required = true)
    @Valid
    @NotNull
    @Size()
    private List<UpdateWorkspaceMemberReq> members = new ArrayList<UpdateWorkspaceMemberReq>();

    public List<UpdateWorkspaceMemberReq> getMembers() {
        return members;
    }

    public WorkspaceMemberBody1 setMembers(List<UpdateWorkspaceMemberReq> members) {
        this.members = members;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkspaceMemberBody1 {\n");

        sb.append("    members: ").append(toIndentedString(members)).append("\n");
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
        WorkspaceMemberBody1 workspaceMemberBody1 = (WorkspaceMemberBody1) o;
        return Objects.equals(this.members, workspaceMemberBody1.members);
    }

    @Override
    public int hashCode() {
        return Objects.hash(members);
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
