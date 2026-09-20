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
import java.util.Date;
import java.util.Objects;

/**
 * 团队空间成员描述信息。
 */
@ApiModel(description = "团队空间成员描述信息。")

@Validated

public class WorkspaceMemberInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "成员记录ID", example = "member-record-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("workspaceId")
    @Schema(description = "工作空间ID", example = "workspace-123")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String workspaceId = null;

    @JsonProperty("memberName")
    @Schema(description = "成员名称", example = "张三")
    @Pattern(regexp = "^[a-zA-Z0-9\\u4e00-\\u9fa5._-][a-zA-Z0-9\\u4e00-\\u9fa5._\\- ]{0,63}$")
    @Length(min = 1, max = 64)
    private String memberName = null;

    @JsonProperty("memberId")
    @Schema(description = "成员ID", example = "user-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String memberId = null;

    @JsonProperty("memberSource")
    @Schema(description = "成员来源", example = "iam")
    @Length(min = 1, max = 128)
    private String memberSource = null;

    @JsonProperty("domainId")
    @Schema(description = "域ID", example = "domain-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String domainId = null;

    @JsonProperty("role")
    @Schema(description = "成员角色", example = "admin")
    @Length(min = 1, max = 64)
    private String role = null;

    @JsonProperty("createdOn")
    @Schema(description = "创建时间", example = "2026-01-01T00:00:00Z")
    private Date createdOn = null;

    @JsonProperty("updatedOn")
    @Schema(description = "更新时间", example = "2026-01-02T00:00:00Z")
    private Date updatedOn = null;

    @JsonProperty("creator")
    @Schema(description = "创建者名称", example = "管理员")
    @Length(min = 1, max = 128)
    private String creator = null;

    @JsonProperty("updater")
    @Schema(description = "更新者名称", example = "管理员")
    @Length(min = 1, max = 128)
    private String updater = null;

    @JsonProperty("creatorId")
    @Schema(description = "创建者ID", example = "user-456")
    @Length(min = 1, max = 128)
    private String creatorId = null;

    @JsonProperty("updaterId")
    @Schema(description = "更新者ID", example = "user-456")
    @Length(min = 1, max = 128)
    private String updaterId = null;

    public String getId() {
        return id;
    }

    public WorkspaceMemberInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public WorkspaceMemberInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getMemberName() {
        return memberName;
    }

    public WorkspaceMemberInfo setMemberName(String memberName) {
        this.memberName = memberName;
        return this;
    }

    public String getMemberId() {
        return memberId;
    }

    public WorkspaceMemberInfo setMemberId(String memberId) {
        this.memberId = memberId;
        return this;
    }

    public String getMemberSource() {
        return memberSource;
    }

    public WorkspaceMemberInfo setMemberSource(String memberSource) {
        this.memberSource = memberSource;
        return this;
    }

    public String getDomainId() {
        return domainId;
    }

    public WorkspaceMemberInfo setDomainId(String domainId) {
        this.domainId = domainId;
        return this;
    }

    public String getRole() {
        return role;
    }

    public WorkspaceMemberInfo setRole(String role) {
        this.role = role;
        return this;
    }

    public Date getCreatedOn() {
        return createdOn;
    }

    public WorkspaceMemberInfo setCreatedOn(Date createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public Date getUpdatedOn() {
        return updatedOn;
    }

    public WorkspaceMemberInfo setUpdatedOn(Date updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public WorkspaceMemberInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public WorkspaceMemberInfo setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public WorkspaceMemberInfo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public String getUpdaterId() {
        return updaterId;
    }

    public WorkspaceMemberInfo setUpdaterId(String updaterId) {
        this.updaterId = updaterId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkspaceMemberInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    memberName: ").append(toIndentedString(memberName)).append("\n");
        sb.append("    memberId: ").append(toIndentedString(memberId)).append("\n");
        sb.append("    memberSource: ").append(toIndentedString(memberSource)).append("\n");
        sb.append("    domainId: ").append(toIndentedString(domainId)).append("\n");
        sb.append("    role: ").append(toIndentedString(role)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    updaterId: ").append(toIndentedString(updaterId)).append("\n");
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
        WorkspaceMemberInfo workspaceMemberInfo = (WorkspaceMemberInfo) o;
        return Objects.equals(this.id, workspaceMemberInfo.id) && Objects.equals(this.workspaceId,
            workspaceMemberInfo.workspaceId) && Objects.equals(this.memberName, workspaceMemberInfo.memberName)
            && Objects.equals(this.memberId, workspaceMemberInfo.memberId) && Objects.equals(this.memberSource,
            workspaceMemberInfo.memberSource) && Objects.equals(this.domainId, workspaceMemberInfo.domainId)
            && Objects.equals(this.role, workspaceMemberInfo.role) && Objects.equals(this.createdOn,
            workspaceMemberInfo.createdOn) && Objects.equals(this.updatedOn, workspaceMemberInfo.updatedOn)
            && Objects.equals(this.creator, workspaceMemberInfo.creator) && Objects.equals(this.updater,
            workspaceMemberInfo.updater) && Objects.equals(this.creatorId, workspaceMemberInfo.creatorId)
            && Objects.equals(this.updaterId, workspaceMemberInfo.updaterId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, workspaceId, memberName, memberId, memberSource, domainId, role, createdOn, updatedOn,
            creator, updater, creatorId, updaterId);
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
