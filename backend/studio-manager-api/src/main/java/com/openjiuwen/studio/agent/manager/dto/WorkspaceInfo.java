/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 团队空间描述信息。
 */
@ApiModel(description = "团队空间描述信息。")

@Validated

public class WorkspaceInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "工作空间ID", example = "ws001")
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$")
    @Length(min = 1, max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "工作空间名称", example = "default")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$")
    @Length(min = 1, max = 64)
    private String name = null;

    @JsonProperty("projectId")
    @Schema(description = "项目ID", example = "proj001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String projectId = null;

    @JsonProperty("flag")
    @Schema(description = "标识", example = "flag001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 64)
    private String flag = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-workspace")
    private String icon = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "团队空间描述信息")
    @Length(max = 256)
    private String description = null;

    @JsonProperty("tenantId")
    @Schema(description = "租户ID", example = "tenant001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 128)
    private String tenantId = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "team")
    @Length(min = 1, max = 32)
    private String type = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "active")
    @Length(min = 1, max = 64)
    private String status = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("creatorId")
    @Schema(description = "创建者ID", example = "user001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 128)
    private String creatorId = null;

    @JsonProperty("createdOn")
    @Schema(description = "创建时间", example = "2026-01-01T00:00:00.000+08:00")
    private Date createdOn = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "李四")
    private String updater = null;

    @JsonProperty("updaterId")
    @Schema(description = "更新者ID", example = "user002")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(min = 1, max = 128)
    private String updaterId = null;

    @JsonProperty("updatedOn")
    @Schema(description = "更新时间", example = "2026-01-01T00:00:00.000+08:00")
    private Date updatedOn = null;

    @JsonProperty("role")
    @Schema(description = "角色", example = "admin")
    private String role = null;

    @JsonProperty("externalMappingInfo")
    @Schema(description = "外部映射信息", example = "外部映射信息列表")
    @Valid
    @Size()
    private List<ExternalMappingInfo> externalMappingInfo = null;

    public String getId() {
        return id;
    }

    public WorkspaceInfo setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkspaceInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public WorkspaceInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getFlag() {
        return flag;
    }

    public WorkspaceInfo setFlag(String flag) {
        this.flag = flag;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public WorkspaceInfo setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkspaceInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getTenantId() {
        return tenantId;
    }

    public WorkspaceInfo setTenantId(String tenantId) {
        this.tenantId = tenantId;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkspaceInfo setType(String type) {
        this.type = type;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public WorkspaceInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public WorkspaceInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public WorkspaceInfo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getCreatedOn() {
        return createdOn;
    }

    public WorkspaceInfo setCreatedOn(Date createdOn) {
        this.createdOn = createdOn;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public WorkspaceInfo setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    public String getUpdaterId() {
        return updaterId;
    }

    public WorkspaceInfo setUpdaterId(String updaterId) {
        this.updaterId = updaterId;
        return this;
    }

    public Date getUpdatedOn() {
        return updatedOn;
    }

    public WorkspaceInfo setUpdatedOn(Date updatedOn) {
        this.updatedOn = updatedOn;
        return this;
    }

    public String getRole() {
        return role;
    }

    public WorkspaceInfo setRole(String role) {
        this.role = role;
        return this;
    }

    public List<ExternalMappingInfo> getExternalMappingInfo() {
        return externalMappingInfo;
    }

    public WorkspaceInfo setExternalMappingInfo(List<ExternalMappingInfo> externalMappingInfo) {
        this.externalMappingInfo = externalMappingInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkspaceInfo {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    flag: ").append(toIndentedString(flag)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    tenantId: ").append(toIndentedString(tenantId)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createdOn: ").append(toIndentedString(createdOn)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
        sb.append("    updaterId: ").append(toIndentedString(updaterId)).append("\n");
        sb.append("    updatedOn: ").append(toIndentedString(updatedOn)).append("\n");
        sb.append("    role: ").append(toIndentedString(role)).append("\n");
        sb.append("    externalMappingInfo: ").append(toIndentedString(externalMappingInfo)).append("\n");
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
        WorkspaceInfo workspaceInfo = (WorkspaceInfo) o;
        return Objects.equals(this.id, workspaceInfo.id) && Objects.equals(this.name, workspaceInfo.name)
            && Objects.equals(this.projectId, workspaceInfo.projectId) && Objects.equals(this.flag, workspaceInfo.flag)
            && Objects.equals(this.icon, workspaceInfo.icon) && Objects.equals(this.description,
            workspaceInfo.description) && Objects.equals(this.tenantId, workspaceInfo.tenantId) && Objects.equals(
            this.type, workspaceInfo.type) && Objects.equals(this.status, workspaceInfo.status) && Objects.equals(
            this.creator, workspaceInfo.creator) && Objects.equals(this.creatorId, workspaceInfo.creatorId)
            && Objects.equals(this.createdOn, workspaceInfo.createdOn) && Objects.equals(this.updater,
            workspaceInfo.updater) && Objects.equals(this.updaterId, workspaceInfo.updaterId) && Objects.equals(
            this.updatedOn, workspaceInfo.updatedOn) && Objects.equals(this.role, workspaceInfo.role) && Objects.equals(
            this.externalMappingInfo, workspaceInfo.externalMappingInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, projectId, flag, icon, description, tenantId, type, status, creator, creatorId,
            createdOn, updater, updaterId, updatedOn, role, externalMappingInfo);
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
