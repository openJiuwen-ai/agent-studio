/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
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
 * ShareResourceResp
 */

@Validated

public class ShareResourceResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "res001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String resourceId = null;

    @JsonProperty("resource_name")
    @Schema(description = "资源名称", example = "天气查询插件")
    @Length(max = 64)
    private String resourceName = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "plugin")
    private String resourceType = null;

    @JsonProperty("resource_description")
    @Schema(description = "资源描述", example = "提供天气查询功能")
    private String resourceDescription = null;

    @JsonProperty("version_info_list")
    @Schema(description = "版本信息列表", example = "版本信息列表")
    @Valid
    @Size(min = 1, max = 50)
    private List<ResourceVersionInfo> versionInfoList = null;

    @JsonProperty("resource_workspace_id")
    @Schema(description = "资源工作空间ID", example = "ws001")
    private String resourceWorkspaceId = null;

    @JsonProperty("resource_workspace_name")
    @Schema(description = "资源工作空间名称", example = "default")
    private String resourceWorkspaceName = null;

    @JsonProperty("workspace_list")
    @Schema(description = "工作空间列表", example = "工作空间列表")
    @Valid
    @Size(min = 1, max = 100)
    private List<AuthWorkspaceInfo> workspaceList = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("tenant_id")
    @Schema(description = "租户ID", example = "tenant001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String tenantId = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user001")
    private String creatorId = null;

    @JsonProperty("share_time")
    @Schema(description = "分享时间", example = "2026-01-01T00:00:00.000+08:00")
    private Date shareTime = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-plugin")
    private String icon = null;

    @JsonProperty("agent_inputs")
    @Schema(description = "Agent输入参数", example = "Agent输入参数列表")
    @Valid
    @Size()
    private List<WorkflowFieldVO> agentInputs = null;

    @JsonProperty("workflow_inputs")
    @Schema(description = "工作流输入参数", example = "工作流输入参数列表")
    @Valid
    @Size()
    private List<WorkflowFieldVO> workflowInputs = null;

    @JsonProperty("controller_inputs")
    @Schema(description = "控制器输入参数", example = "控制器输入参数列表")
    @Valid
    @Size()
    private List<WorkflowFieldVO> controllerInputs = null;

    public String getResourceId() {
        return resourceId;
    }

    public ShareResourceResp setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public ShareResourceResp setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public ShareResourceResp setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public String getResourceDescription() {
        return resourceDescription;
    }

    public ShareResourceResp setResourceDescription(String resourceDescription) {
        this.resourceDescription = resourceDescription;
        return this;
    }

    public List<ResourceVersionInfo> getVersionInfoList() {
        return versionInfoList;
    }

    public ShareResourceResp setVersionInfoList(List<ResourceVersionInfo> versionInfoList) {
        this.versionInfoList = versionInfoList;
        return this;
    }

    public String getResourceWorkspaceId() {
        return resourceWorkspaceId;
    }

    public ShareResourceResp setResourceWorkspaceId(String resourceWorkspaceId) {
        this.resourceWorkspaceId = resourceWorkspaceId;
        return this;
    }

    public String getResourceWorkspaceName() {
        return resourceWorkspaceName;
    }

    public ShareResourceResp setResourceWorkspaceName(String resourceWorkspaceName) {
        this.resourceWorkspaceName = resourceWorkspaceName;
        return this;
    }

    public List<AuthWorkspaceInfo> getWorkspaceList() {
        return workspaceList;
    }

    public ShareResourceResp setWorkspaceList(List<AuthWorkspaceInfo> workspaceList) {
        this.workspaceList = workspaceList;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ShareResourceResp setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getTenantId() {
        return tenantId;
    }

    public ShareResourceResp setTenantId(String tenantId) {
        this.tenantId = tenantId;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public ShareResourceResp setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public ShareResourceResp setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getShareTime() {
        return shareTime;
    }

    public ShareResourceResp setShareTime(Date shareTime) {
        this.shareTime = shareTime;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public ShareResourceResp setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public List<WorkflowFieldVO> getAgentInputs() {
        return agentInputs;
    }

    public ShareResourceResp setAgentInputs(List<WorkflowFieldVO> agentInputs) {
        this.agentInputs = agentInputs;
        return this;
    }

    public List<WorkflowFieldVO> getWorkflowInputs() {
        return workflowInputs;
    }

    public ShareResourceResp setWorkflowInputs(List<WorkflowFieldVO> workflowInputs) {
        this.workflowInputs = workflowInputs;
        return this;
    }

    public List<WorkflowFieldVO> getControllerInputs() {
        return controllerInputs;
    }

    public ShareResourceResp setControllerInputs(List<WorkflowFieldVO> controllerInputs) {
        this.controllerInputs = controllerInputs;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShareResourceResp {\n");

        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    resourceDescription: ").append(toIndentedString(resourceDescription)).append("\n");
        sb.append("    versionInfoList: ").append(toIndentedString(versionInfoList)).append("\n");
        sb.append("    resourceWorkspaceId: ").append(toIndentedString(resourceWorkspaceId)).append("\n");
        sb.append("    resourceWorkspaceName: ").append(toIndentedString(resourceWorkspaceName)).append("\n");
        sb.append("    workspaceList: ").append(toIndentedString(workspaceList)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    tenantId: ").append(toIndentedString(tenantId)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    shareTime: ").append(toIndentedString(shareTime)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    agentInputs: ").append(toIndentedString(agentInputs)).append("\n");
        sb.append("    workflowInputs: ").append(toIndentedString(workflowInputs)).append("\n");
        sb.append("    controllerInputs: ").append(toIndentedString(controllerInputs)).append("\n");
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
        ShareResourceResp shareResourceResp = (ShareResourceResp) o;
        return Objects.equals(this.resourceId, shareResourceResp.resourceId) && Objects.equals(this.resourceName,
            shareResourceResp.resourceName) && Objects.equals(this.resourceType, shareResourceResp.resourceType)
            && Objects.equals(this.resourceDescription, shareResourceResp.resourceDescription) && Objects.equals(
            this.versionInfoList, shareResourceResp.versionInfoList) && Objects.equals(this.resourceWorkspaceId,
            shareResourceResp.resourceWorkspaceId) && Objects.equals(this.resourceWorkspaceName,
            shareResourceResp.resourceWorkspaceName) && Objects.equals(this.workspaceList,
            shareResourceResp.workspaceList) && Objects.equals(this.projectId, shareResourceResp.projectId)
            && Objects.equals(this.tenantId, shareResourceResp.tenantId) && Objects.equals(this.creator,
            shareResourceResp.creator) && Objects.equals(this.creatorId, shareResourceResp.creatorId) && Objects.equals(
            this.shareTime, shareResourceResp.shareTime) && Objects.equals(this.icon, shareResourceResp.icon)
            && Objects.equals(this.agentInputs, shareResourceResp.agentInputs) && Objects.equals(this.workflowInputs,
            shareResourceResp.workflowInputs) && Objects.equals(this.controllerInputs,
            shareResourceResp.controllerInputs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceName, resourceType, resourceDescription, versionInfoList,
            resourceWorkspaceId, resourceWorkspaceName, workspaceList, projectId, tenantId, creator, creatorId,
            shareTime, icon, agentInputs, workflowInputs, controllerInputs);
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
