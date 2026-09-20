/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

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
 * 应用的相关信息。
 */
@ApiModel(description = "应用的相关信息。")

@Validated

public class AppInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("app_id")
    @Schema(description = "应用ID", example = "app-123456")
    private String appId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project-123")
    private String projectId = null;

    @JsonProperty("name")
    @Schema(description = "应用名称", example = "智能助手")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "应用描述", example = "这是一个智能助手应用")
    private String description = null;

    @JsonProperty("icon")
    @Schema(description = "应用图标URL", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("tags")
    @Schema(description = "应用标签列表", example = "[\"AI\",\"助手\"]")
    @Valid
    @Size()
    private List<@Length() String> tags = null;

    @JsonProperty("app_type")
    @Schema(description = "应用类型", example = "agent")
    private String appType = null;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "resource-123")
    private String resourceId = null;

    @JsonProperty("workflow_type")
    @Schema(description = "工作流类型", example = "standard")
    private String workflowType = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "app")
    private String resourceType = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("publish_time")
    @Schema(description = "发布时间", example = "2026-01-01T00:00:00Z")
    private Date publishTime = null;

    @JsonProperty("free_trial_quota")
    @Schema(description = "免费试用配额", example = "{}")
    @Valid
    private FreeTrialQuota freeTrialQuota = null;

    public String getAppId() {
        return appId;
    }

    public AppInfo setAppId(String appId) {
        this.appId = appId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public AppInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getName() {
        return name;
    }

    public AppInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public AppInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public AppInfo setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public List<String> getTags() {
        return tags;
    }

    public AppInfo setTags(List<String> tags) {
        this.tags = tags;
        return this;
    }

    public String getAppType() {
        return appType;
    }

    public AppInfo setAppType(String appType) {
        this.appType = appType;
        return this;
    }

    public String getResourceId() {
        return resourceId;
    }

    public AppInfo setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getWorkflowType() {
        return workflowType;
    }

    public AppInfo setWorkflowType(String workflowType) {
        this.workflowType = workflowType;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public AppInfo setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public AppInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public Date getPublishTime() {
        return publishTime;
    }

    public AppInfo setPublishTime(Date publishTime) {
        this.publishTime = publishTime;
        return this;
    }

    public FreeTrialQuota getFreeTrialQuota() {
        return freeTrialQuota;
    }

    public AppInfo setFreeTrialQuota(FreeTrialQuota freeTrialQuota) {
        this.freeTrialQuota = freeTrialQuota;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AppInfo {\n");

        sb.append("    appId: ").append(toIndentedString(appId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    tags: ").append(toIndentedString(tags)).append("\n");
        sb.append("    appType: ").append(toIndentedString(appType)).append("\n");
        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    workflowType: ").append(toIndentedString(workflowType)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    publishTime: ").append(toIndentedString(publishTime)).append("\n");
        sb.append("    freeTrialQuota: ").append(toIndentedString(freeTrialQuota)).append("\n");
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
        AppInfo appInfo = (AppInfo) o;
        return Objects.equals(this.appId, appInfo.appId) && Objects.equals(this.projectId, appInfo.projectId)
            && Objects.equals(this.name, appInfo.name) && Objects.equals(this.description, appInfo.description)
            && Objects.equals(this.icon, appInfo.icon) && Objects.equals(this.tags, appInfo.tags) && Objects.equals(
            this.appType, appInfo.appType) && Objects.equals(this.resourceId, appInfo.resourceId) && Objects.equals(
            this.workflowType, appInfo.workflowType) && Objects.equals(this.resourceType, appInfo.resourceType)
            && Objects.equals(this.creator, appInfo.creator) && Objects.equals(this.publishTime, appInfo.publishTime)
            && Objects.equals(this.freeTrialQuota, appInfo.freeTrialQuota);
    }

    @Override
    public int hashCode() {
        return Objects.hash(appId, projectId, name, description, icon, tags, appType, resourceId, workflowType,
            resourceType, creator, publishTime, freeTrialQuota);
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
