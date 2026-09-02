/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 关联关系。
 */
@ApiModel(description = "关联关系。")

@Validated

public class Relation implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("relation_id")
    @Schema(description = "关联关系ID", example = "rel001")
    @Length(max = 64)
    private String relationId = null;

    @JsonProperty("app_id")
    @Schema(description = "应用ID", example = "app001")
    @Length(max = 64)
    private String appId = null;

    @JsonProperty("app_version")
    @Schema(description = "应用版本", example = "1.0.0")
    private String appVersion = null;

    @JsonProperty("app_type")
    @Schema(description = "应用类型", example = "agent")
    @Length(max = 32)
    private String appType = null;

    @JsonProperty("latest_version_app_sub_type")
    @Schema(description = "最新版本应用子类型", example = "workflow")
    @Length(max = 32)
    private String latestVersionAppSubType = null;

    @JsonProperty("app_name")
    @Schema(description = "应用名称", example = "天气助手")
    @Length(max = 64)
    private String appName = null;

    @JsonProperty("is_controller")
    @Schema(description = "是否为控制器", example = "false")
    private Boolean isController = null;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "res001")
    @Length(max = 64)
    private String resourceId = null;

    @JsonProperty("resource_version")
    @Schema(description = "资源版本", example = "1.0.0")
    private String resourceVersion = null;

    @JsonProperty("resource_version_name")
    @Schema(description = "资源版本名称", example = "v1.0.0")
    private String resourceVersionName = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "plugin")
    @Length(max = 32)
    private String resourceType = null;

    @JsonProperty("resource_name")
    @Schema(description = "资源名称", example = "天气查询插件")
    private String resourceName = null;

    @JsonProperty("valid")
    @Schema(description = "是否有效", example = "true")
    private Boolean valid = null;

    @JsonProperty("resource_latest_version")
    @Schema(description = "资源最新版本", example = "2.0.0")
    private String resourceLatestVersion = null;

    @JsonProperty("resource_latest_version_name")
    @Schema(description = "资源最新版本名称", example = "v2.0.0")
    private String resourceLatestVersionName = null;

    @JsonProperty("app_workspace_name")
    @Schema(description = "应用工作空间名称", example = "default")
    private String appWorkspaceName = null;

    @JsonProperty("app_workspace_id")
    @Schema(description = "应用工作空间ID", example = "ws001")
    private String appWorkspaceId = null;

    @JsonProperty("reference_type")
    @Schema(description = "引用类型", example = "direct")
    private String referenceType = null;

    public String getRelationId() {
        return relationId;
    }

    public Relation setRelationId(String relationId) {
        this.relationId = relationId;
        return this;
    }

    public String getAppId() {
        return appId;
    }

    public Relation setAppId(String appId) {
        this.appId = appId;
        return this;
    }

    public String getAppVersion() {
        return appVersion;
    }

    public Relation setAppVersion(String appVersion) {
        this.appVersion = appVersion;
        return this;
    }

    public String getAppType() {
        return appType;
    }

    public Relation setAppType(String appType) {
        this.appType = appType;
        return this;
    }

    public String getLatestVersionAppSubType() {
        return latestVersionAppSubType;
    }

    public Relation setLatestVersionAppSubType(String latestVersionAppSubType) {
        this.latestVersionAppSubType = latestVersionAppSubType;
        return this;
    }

    public String getAppName() {
        return appName;
    }

    public Relation setAppName(String appName) {
        this.appName = appName;
        return this;
    }

    public Relation setIsController(Boolean isController) {
        this.isController = isController;
        return this;
    }

    public Boolean isIsController() {
        return isController;
    }

    public String getResourceId() {
        return resourceId;
    }

    public Relation setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceVersion() {
        return resourceVersion;
    }

    public Relation setResourceVersion(String resourceVersion) {
        this.resourceVersion = resourceVersion;
        return this;
    }

    public String getResourceVersionName() {
        return resourceVersionName;
    }

    public Relation setResourceVersionName(String resourceVersionName) {
        this.resourceVersionName = resourceVersionName;
        return this;
    }

    public String getResourceType() {
        return resourceType;
    }

    public Relation setResourceType(String resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public Relation setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public Relation setValid(Boolean valid) {
        this.valid = valid;
        return this;
    }

    public Boolean isValid() {
        return valid;
    }

    public String getResourceLatestVersion() {
        return resourceLatestVersion;
    }

    public Relation setResourceLatestVersion(String resourceLatestVersion) {
        this.resourceLatestVersion = resourceLatestVersion;
        return this;
    }

    public String getResourceLatestVersionName() {
        return resourceLatestVersionName;
    }

    public Relation setResourceLatestVersionName(String resourceLatestVersionName) {
        this.resourceLatestVersionName = resourceLatestVersionName;
        return this;
    }

    public String getAppWorkspaceName() {
        return appWorkspaceName;
    }

    public Relation setAppWorkspaceName(String appWorkspaceName) {
        this.appWorkspaceName = appWorkspaceName;
        return this;
    }

    public String getAppWorkspaceId() {
        return appWorkspaceId;
    }

    public Relation setAppWorkspaceId(String appWorkspaceId) {
        this.appWorkspaceId = appWorkspaceId;
        return this;
    }

    public String getReferenceType() {
        return referenceType;
    }

    public Relation setReferenceType(String referenceType) {
        this.referenceType = referenceType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Relation {\n");

        sb.append("    relationId: ").append(toIndentedString(relationId)).append("\n");
        sb.append("    appId: ").append(toIndentedString(appId)).append("\n");
        sb.append("    appVersion: ").append(toIndentedString(appVersion)).append("\n");
        sb.append("    appType: ").append(toIndentedString(appType)).append("\n");
        sb.append("    latestVersionAppSubType: ").append(toIndentedString(latestVersionAppSubType)).append("\n");
        sb.append("    appName: ").append(toIndentedString(appName)).append("\n");
        sb.append("    isController: ").append(toIndentedString(isController)).append("\n");
        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceVersion: ").append(toIndentedString(resourceVersion)).append("\n");
        sb.append("    resourceVersionName: ").append(toIndentedString(resourceVersionName)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    valid: ").append(toIndentedString(valid)).append("\n");
        sb.append("    resourceLatestVersion: ").append(toIndentedString(resourceLatestVersion)).append("\n");
        sb.append("    resourceLatestVersionName: ").append(toIndentedString(resourceLatestVersionName)).append("\n");
        sb.append("    appWorkspaceName: ").append(toIndentedString(appWorkspaceName)).append("\n");
        sb.append("    appWorkspaceId: ").append(toIndentedString(appWorkspaceId)).append("\n");
        sb.append("    referenceType: ").append(toIndentedString(referenceType)).append("\n");
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
        Relation relation = (Relation) o;
        return Objects.equals(this.relationId, relation.relationId) && Objects.equals(this.appId, relation.appId)
            && Objects.equals(this.appVersion, relation.appVersion) && Objects.equals(this.appType, relation.appType)
            && Objects.equals(this.latestVersionAppSubType, relation.latestVersionAppSubType) && Objects.equals(
            this.appName, relation.appName) && Objects.equals(this.isController, relation.isController)
            && Objects.equals(this.resourceId, relation.resourceId) && Objects.equals(this.resourceVersion,
            relation.resourceVersion) && Objects.equals(this.resourceVersionName, relation.resourceVersionName)
            && Objects.equals(this.resourceType, relation.resourceType) && Objects.equals(this.resourceName,
            relation.resourceName) && Objects.equals(this.valid, relation.valid) && Objects.equals(
            this.resourceLatestVersion, relation.resourceLatestVersion) && Objects.equals(
            this.resourceLatestVersionName, relation.resourceLatestVersionName) && Objects.equals(this.appWorkspaceName,
            relation.appWorkspaceName) && Objects.equals(this.appWorkspaceId, relation.appWorkspaceId)
            && Objects.equals(this.referenceType, relation.referenceType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(relationId, appId, appVersion, appType, latestVersionAppSubType, appName, isController,
            resourceId, resourceVersion, resourceVersionName, resourceType, resourceName, valid, resourceLatestVersion,
            resourceLatestVersionName, appWorkspaceName, appWorkspaceId, referenceType);
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
