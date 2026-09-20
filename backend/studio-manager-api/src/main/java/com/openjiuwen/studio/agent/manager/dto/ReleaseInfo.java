/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 应用发布信息。
 */
@ApiModel(description = "应用发布信息。")

@Validated

public class ReleaseInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("app_id")
    @Schema(description = "应用ID", example = "app_001", required = true)
    @NotBlank
    private String appId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj_001")
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    private String workspaceId = null;

    @JsonProperty("app_type")
    @Schema(description = "应用类型", example = "chat", required = true)
    @NotBlank
    private String appType = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1.0.0", required = true)
    @NotBlank
    private String versionId = null;

    @JsonProperty("channel_type")
    @Schema(description = "渠道类型", example = "web")
    private String channelType = null;

    @JsonProperty("short_code")
    @Schema(description = "短码", example = "abc123")
    private String shortCode = null;

    @JsonProperty("visibility_scope")
    @Schema(description = "可见范围", example = "public")
    private String visibilityScope = null;

    @JsonProperty("call_count")
    @Schema(description = "调用次数", example = "100")
    private Integer callCount = null;

    public String getAppId() {
        return appId;
    }

    public ReleaseInfo setAppId(String appId) {
        this.appId = appId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ReleaseInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ReleaseInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getAppType() {
        return appType;
    }

    public ReleaseInfo setAppType(String appType) {
        this.appType = appType;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public ReleaseInfo setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public String getChannelType() {
        return channelType;
    }

    public ReleaseInfo setChannelType(String channelType) {
        this.channelType = channelType;
        return this;
    }

    public String getShortCode() {
        return shortCode;
    }

    public ReleaseInfo setShortCode(String shortCode) {
        this.shortCode = shortCode;
        return this;
    }

    public String getVisibilityScope() {
        return visibilityScope;
    }

    public ReleaseInfo setVisibilityScope(String visibilityScope) {
        this.visibilityScope = visibilityScope;
        return this;
    }

    public Integer getCallCount() {
        return callCount;
    }

    public ReleaseInfo setCallCount(Integer callCount) {
        this.callCount = callCount;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ReleaseInfo {\n");

        sb.append("    appId: ").append(toIndentedString(appId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    appType: ").append(toIndentedString(appType)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    channelType: ").append(toIndentedString(channelType)).append("\n");
        sb.append("    shortCode: ").append(toIndentedString(shortCode)).append("\n");
        sb.append("    visibilityScope: ").append(toIndentedString(visibilityScope)).append("\n");
        sb.append("    callCount: ").append(toIndentedString(callCount)).append("\n");
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
        ReleaseInfo releaseInfo = (ReleaseInfo) o;
        return Objects.equals(this.appId, releaseInfo.appId) && Objects.equals(this.projectId, releaseInfo.projectId)
            && Objects.equals(this.workspaceId, releaseInfo.workspaceId) && Objects.equals(this.appType,
            releaseInfo.appType) && Objects.equals(this.versionId, releaseInfo.versionId) && Objects.equals(
            this.channelType, releaseInfo.channelType) && Objects.equals(this.shortCode, releaseInfo.shortCode)
            && Objects.equals(this.visibilityScope, releaseInfo.visibilityScope) && Objects.equals(this.callCount,
            releaseInfo.callCount);
    }

    @Override
    public int hashCode() {
        return Objects.hash(appId, projectId, workspaceId, appType, versionId, channelType, shortCode, visibilityScope,
            callCount);
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
