/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * AuthConfigListQo: converted from multi query params
 */
@ApiModel(description = "AuthConfigListQo: converted from multi query params")

@Validated

public class AuthConfigListQo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "example-id-123", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
    @NotBlank
    private String workspaceId = null;

    @JsonProperty("provider_id")
    @Schema(description = "提供者ID", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    private String providerId = null;

    @JsonProperty("metadata_id")
    @Schema(description = "元数据", example = "example-id-123")
    @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
    private String metadataId = null;

    public String getWorkspaceId() {
        return workspaceId;
    }

    public AuthConfigListQo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getProviderId() {
        return providerId;
    }

    public AuthConfigListQo setProviderId(String providerId) {
        this.providerId = providerId;
        return this;
    }

    public String getMetadataId() {
        return metadataId;
    }

    public AuthConfigListQo setMetadataId(String metadataId) {
        this.metadataId = metadataId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AuthConfigListQo {\n");

        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    providerId: ").append(toIndentedString(providerId)).append("\n");
        sb.append("    metadataId: ").append(toIndentedString(metadataId)).append("\n");
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
        AuthConfigListQo authConfigListQo = (AuthConfigListQo) o;
        return Objects.equals(this.workspaceId, authConfigListQo.workspaceId) && Objects.equals(this.providerId,
            authConfigListQo.providerId) && Objects.equals(this.metadataId, authConfigListQo.metadataId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workspaceId, providerId, metadataId);
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
