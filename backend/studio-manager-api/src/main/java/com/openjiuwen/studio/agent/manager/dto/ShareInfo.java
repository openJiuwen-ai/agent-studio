/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * 共享信息。
 */
@ApiModel(description = "共享信息。")

@Validated

public class ShareInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "resource-001")
    private String resourceId = null;

    @JsonProperty("resource_name")
    @Schema(description = "资源名称", example = "我的应用")
    private String resourceName = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "app")
    private String resourceType = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-001")
    private String workspaceId = null;

    @JsonProperty("trace_id")
    @Schema(description = "链路追踪ID", example = "trace-001")
    private String traceId = null;

    @JsonProperty("version_list")
    @Schema(description = "版本列表", example = "v1.0,v2.0")
    private String versionList = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project-001")
    private String projectId = null;

    @JsonProperty("tenant_id")
    @Schema(description = "租户ID", example = "tenant-001")
    private String tenantId = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user-001")
    private String creatorId = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2024-01-01T00:00:00.000+08:00")
    private Date createTime = null;

    @JsonProperty("updater_id")
    @Schema(description = "更新者ID", example = "user-002")
    private String updaterId = null;

    @JsonProperty("updater")
    @Schema(description = "更新者", example = "李四")
    private String updater = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2024-01-02T00:00:00.000+08:00")
    private Date updateTime = null;

    @JsonProperty("shareScopeEntityList")
    @Schema(description = "共享范围实体列表", example = "[]")
    @Valid
    @Size()
    private List<ShareScopeEntity> shareScopeEntityList = null;

    public String getResourceId() {
        return resourceId;
    }

    public ShareInfo setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public ShareInfo setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public ShareInfo setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ShareInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getTraceId() {
        return traceId;
    }

    public ShareInfo setTraceId(String traceId) {
        this.traceId = traceId;
        return this;
    }

    public String getVersionList() {
        return versionList;
    }

    public ShareInfo setVersionList(String versionList) {
        this.versionList = versionList;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ShareInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getTenantId() {
        return tenantId;
    }

    public ShareInfo setTenantId(String tenantId) {
        this.tenantId = tenantId;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ShareInfo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public ShareInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public ShareInfo setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getUpdaterId() {
        return updaterId;
    }

    public ShareInfo setUpdaterId(String updaterId) {
        this.updaterId = updaterId;
        return this;
    }

    public String getUpdater() {
        return updater;
    }

    public ShareInfo setUpdater(String updater) {
        this.updater = updater;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public ShareInfo setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public List<ShareScopeEntity> getShareScopeEntityList() {
        return shareScopeEntityList;
    }

    public ShareInfo setShareScopeEntityList(List<ShareScopeEntity> shareScopeEntityList) {
        this.shareScopeEntityList = shareScopeEntityList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShareInfo {\n");

        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    traceId: ").append(toIndentedString(traceId)).append("\n");
        sb.append("    versionList: ").append(toIndentedString(versionList)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    tenantId: ").append(toIndentedString(tenantId)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updaterId: ").append(toIndentedString(updaterId)).append("\n");
        sb.append("    updater: ").append(toIndentedString(updater)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    shareScopeEntityList: ").append(toIndentedString(shareScopeEntityList)).append("\n");
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
        ShareInfo shareInfo = (ShareInfo) o;
        return Objects.equals(this.resourceId, shareInfo.resourceId) && Objects.equals(this.resourceName,
            shareInfo.resourceName) && Objects.equals(this.resourceType, shareInfo.resourceType) && Objects.equals(
            this.workspaceId, shareInfo.workspaceId) && Objects.equals(this.traceId, shareInfo.traceId)
            && Objects.equals(this.versionList, shareInfo.versionList) && Objects.equals(this.projectId,
            shareInfo.projectId) && Objects.equals(this.tenantId, shareInfo.tenantId) && Objects.equals(this.creatorId,
            shareInfo.creatorId) && Objects.equals(this.creator, shareInfo.creator) && Objects.equals(this.createTime,
            shareInfo.createTime) && Objects.equals(this.updaterId, shareInfo.updaterId) && Objects.equals(this.updater,
            shareInfo.updater) && Objects.equals(this.updateTime, shareInfo.updateTime) && Objects.equals(
            this.shareScopeEntityList, shareInfo.shareScopeEntityList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceName, resourceType, workspaceId, traceId, versionList, projectId,
            tenantId, creatorId, creator, createTime, updaterId, updater, updateTime, shareScopeEntityList);
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
