/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 插件鉴权凭证信息
 */
@ApiModel(description = "插件鉴权凭证信息")

@Validated

public class ToolCredential implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "凭证ID", example = "cred_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("tool_id")
    @Schema(description = "工具ID", example = "tool_001")
    @Length(max = 84)
    private String toolId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj_001")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("auth_keys")
    @Schema(description = "鉴权密钥列表", example = "[]")
    @Valid
    @Size()
    private List<AuthKeyInfo> authKeys = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user001")
    @Length(max = 64)
    private String creatorId = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2026-01-01T00:00:00Z")
    private Date createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2026-01-01T12:00:00Z")
    private Date updateTime = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    private String workspaceId = null;

    @JsonProperty("domain_id")
    @Schema(description = "域ID", example = "domain_001")
    private String domainId = null;

    public String getId() {
        return id;
    }

    public ToolCredential setId(String id) {
        this.id = id;
        return this;
    }

    public String getToolId() {
        return toolId;
    }

    public ToolCredential setToolId(String toolId) {
        this.toolId = toolId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ToolCredential setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public List<AuthKeyInfo> getAuthKeys() {
        return authKeys;
    }

    public ToolCredential setAuthKeys(List<AuthKeyInfo> authKeys) {
        this.authKeys = authKeys;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ToolCredential setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public ToolCredential setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public ToolCredential setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ToolCredential setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getDomainId() {
        return domainId;
    }

    public ToolCredential setDomainId(String domainId) {
        this.domainId = domainId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ToolCredential {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    toolId: ").append(toIndentedString(toolId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    authKeys: ").append(toIndentedString(authKeys)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    domainId: ").append(toIndentedString(domainId)).append("\n");
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
        ToolCredential toolCredential = (ToolCredential) o;
        return Objects.equals(this.id, toolCredential.id) && Objects.equals(this.toolId, toolCredential.toolId)
            && Objects.equals(this.projectId, toolCredential.projectId) && Objects.equals(this.authKeys,
            toolCredential.authKeys) && Objects.equals(this.creatorId, toolCredential.creatorId) && Objects.equals(
            this.createTime, toolCredential.createTime) && Objects.equals(this.updateTime, toolCredential.updateTime)
            && Objects.equals(this.workspaceId, toolCredential.workspaceId) && Objects.equals(this.domainId,
            toolCredential.domainId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, toolId, projectId, authKeys, creatorId, createTime, updateTime, workspaceId, domainId);
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
