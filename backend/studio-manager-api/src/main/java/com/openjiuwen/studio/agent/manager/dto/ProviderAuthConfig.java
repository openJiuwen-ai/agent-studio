/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ProviderAuthConfig
 */

@Validated

public class ProviderAuthConfig implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("metadata_id")
    @Schema(description = "元数据ID", example = "meta_001")
    private String metadataId = null;

    @JsonProperty("auth_type")
    @Schema(description = "认证类型", example = "API_KEY")
    private String authType = null;

    @JsonProperty("auth_id")
    @Schema(description = "认证ID", example = "auth_001")
    private String authId = null;

    @JsonProperty("model_names")
    @Schema(description = "模型名称", example = "gpt-4")
    @Pattern(
        regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9](?:[\\u4e00-\\u9fa5a-zA-Z0-9_.\\/:|\\ -]{0,62}[\\u4e00-\\u9fa5a-zA-Z0-9_-])?$")
    private String modelNames = null;

    @JsonProperty("provider_id")
    @Schema(description = "供应商ID", example = "provider_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    private String providerId = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{}")
    private String authInfo = null;

    @JsonProperty("auth_url")
    @Schema(description = "认证URL", example = "https://example.com/auth")
    private String authUrl = null;

    @JsonProperty("is_record")
    @Schema(description = "是否记录", example = "true")
    private Boolean isRecord = null;

    @JsonProperty("domain_id")
    @Schema(description = "域ID", example = "domain_001")
    private String domainId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    private String workspaceId = null;

    public String getMetadataId() {
        return metadataId;
    }

    public ProviderAuthConfig setMetadataId(String metadataId) {
        this.metadataId = metadataId;
        return this;
    }

    public String getAuthType() {
        return authType;
    }

    public ProviderAuthConfig setAuthType(String authType) {
        this.authType = authType;
        return this;
    }

    public String getAuthId() {
        return authId;
    }

    public ProviderAuthConfig setAuthId(String authId) {
        this.authId = authId;
        return this;
    }

    public String getModelNames() {
        return modelNames;
    }

    public ProviderAuthConfig setModelNames(String modelNames) {
        this.modelNames = modelNames;
        return this;
    }

    public String getProviderId() {
        return providerId;
    }

    public ProviderAuthConfig setProviderId(String providerId) {
        this.providerId = providerId;
        return this;
    }

    public String getAuthInfo() {
        return authInfo;
    }

    public ProviderAuthConfig setAuthInfo(String authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getAuthUrl() {
        return authUrl;
    }

    public ProviderAuthConfig setAuthUrl(String authUrl) {
        this.authUrl = authUrl;
        return this;
    }

    public ProviderAuthConfig setIsRecord(Boolean isRecord) {
        this.isRecord = isRecord;
        return this;
    }

    public Boolean isIsRecord() {
        return isRecord;
    }

    public String getDomainId() {
        return domainId;
    }

    public ProviderAuthConfig setDomainId(String domainId) {
        this.domainId = domainId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ProviderAuthConfig setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ProviderAuthConfig setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ProviderAuthConfig {\n");

        sb.append("    metadataId: ").append(toIndentedString(metadataId)).append("\n");
        sb.append("    authType: ").append(toIndentedString(authType)).append("\n");
        sb.append("    authId: ").append(toIndentedString(authId)).append("\n");
        sb.append("    modelNames: ").append(toIndentedString(modelNames)).append("\n");
        sb.append("    providerId: ").append(toIndentedString(providerId)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    authUrl: ").append(toIndentedString(authUrl)).append("\n");
        sb.append("    isRecord: ").append(toIndentedString(isRecord)).append("\n");
        sb.append("    domainId: ").append(toIndentedString(domainId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
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
        ProviderAuthConfig providerAuthConfig = (ProviderAuthConfig) o;
        return Objects.equals(this.metadataId, providerAuthConfig.metadataId) && Objects.equals(this.authType,
            providerAuthConfig.authType) && Objects.equals(this.authId, providerAuthConfig.authId) && Objects.equals(
            this.modelNames, providerAuthConfig.modelNames) && Objects.equals(this.providerId,
            providerAuthConfig.providerId) && Objects.equals(this.authInfo, providerAuthConfig.authInfo)
            && Objects.equals(this.authUrl, providerAuthConfig.authUrl) && Objects.equals(this.isRecord,
            providerAuthConfig.isRecord) && Objects.equals(this.domainId, providerAuthConfig.domainId)
            && Objects.equals(this.projectId, providerAuthConfig.projectId) && Objects.equals(this.workspaceId,
            providerAuthConfig.workspaceId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(metadataId, authType, authId, modelNames, providerId, authInfo, authUrl, isRecord, domainId,
            projectId, workspaceId);
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
