/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作空间成员信息修改请求类。
 */
@ApiModel(description = "工作空间成员信息修改请求类。")

@Validated

public class UpdateWorkspaceMemberReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("member_id")
    @Schema(description = "成员ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String memberId = null;

    @JsonProperty("role")
    @Schema(description = "角色", example = "{}")
    private MemberRole role = null;

    public String getMemberId() {
        return memberId;
    }

    public UpdateWorkspaceMemberReq setMemberId(String memberId) {
        this.memberId = memberId;
        return this;
    }

    public MemberRole getRole() {
        return role;
    }

    public UpdateWorkspaceMemberReq setRole(MemberRole role) {
        this.role = role;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class UpdateWorkspaceMemberReq {\n");

        sb.append("    memberId: ").append(toIndentedString(memberId)).append("\n");
        sb.append("    role: ").append(toIndentedString(role)).append("\n");
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
        UpdateWorkspaceMemberReq updateWorkspaceMemberReq = (UpdateWorkspaceMemberReq) o;
        return Objects.equals(this.memberId, updateWorkspaceMemberReq.memberId) && Objects.equals(this.role,
            updateWorkspaceMemberReq.role);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memberId, role);
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
