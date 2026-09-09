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
 * 新增空间成员信息定义类。
 */
@ApiModel(description = "新增空间成员信息定义类。")

@Validated

public class AddWorkspaceMemberReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("member_id")
    @Schema(description = "成员ID", example = "user_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String memberId = null;

    @JsonProperty("member_name")
    @Schema(description = "成员名称", example = "张三")
    @Pattern(regexp = "^[a-zA-Z0-9\\u4e00-\\u9fa5._-][a-zA-Z0-9\\u4e00-\\u9fa5._\\- ]{0,63}$")
    @Length(min = 1, max = 64)
    private String memberName = null;

    @JsonProperty("member_source")
    @Schema(description = "成员来源", example = "IAM")
    @Length(min = 1, max = 128)
    private String memberSource = "IAM";

    @JsonProperty("role")
    @Schema(description = "成员角色", example = "admin")
    private MemberRole role = null;

    public String getMemberId() {
        return memberId;
    }

    public AddWorkspaceMemberReq setMemberId(String memberId) {
        this.memberId = memberId;
        return this;
    }

    public String getMemberName() {
        return memberName;
    }

    public AddWorkspaceMemberReq setMemberName(String memberName) {
        this.memberName = memberName;
        return this;
    }

    public String getMemberSource() {
        return memberSource;
    }

    public AddWorkspaceMemberReq setMemberSource(String memberSource) {
        this.memberSource = memberSource;
        return this;
    }

    public MemberRole getRole() {
        return role;
    }

    public AddWorkspaceMemberReq setRole(MemberRole role) {
        this.role = role;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AddWorkspaceMemberReq {\n");

        sb.append("    memberId: ").append(toIndentedString(memberId)).append("\n");
        sb.append("    memberName: ").append(toIndentedString(memberName)).append("\n");
        sb.append("    memberSource: ").append(toIndentedString(memberSource)).append("\n");
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
        AddWorkspaceMemberReq addWorkspaceMemberReq = (AddWorkspaceMemberReq) o;
        return Objects.equals(this.memberId, addWorkspaceMemberReq.memberId) && Objects.equals(this.memberName,
            addWorkspaceMemberReq.memberName) && Objects.equals(this.memberSource, addWorkspaceMemberReq.memberSource)
            && Objects.equals(this.role, addWorkspaceMemberReq.role);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memberId, memberName, memberSource, role);
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
