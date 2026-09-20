/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * ShareResourceRequestInfo
 */

@Validated

public class ShareResourceRequestInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "res001", required = true)
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @NotBlank
    @Length(max = 64)
    private String resourceId = null;

    @JsonProperty("resource_name")
    @Schema(description = "资源名称", example = "搜索插件", required = true)
    @NotBlank
    @Length(min = 1, max = 64)
    private String resourceName = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "plugin", required = true)
    @NotNull
    private ResourceTypeEnum resourceType = null;

    @JsonProperty("version_list")
    @Schema(description = "版本列表", example = "[\"1.0.0\",\"1.1.0\"]", required = true)
    @Valid
    @NotNull
    @Size(max = 50)
    private List<@Length() String> versionList = new ArrayList<String>();

    @JsonProperty("auth_workspace_id_list")
    @Schema(description = "授权工作空间ID列表", example = "[\"ws001\",\"ws002\"]", required = true)
    @Valid
    @NotNull
    @Size(min = 1, max = 1000)
    private List<@Length() String> authWorkspaceIdList = new ArrayList<String>();

    public String getResourceId() {
        return resourceId;
    }

    public ShareResourceRequestInfo setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public String getResourceName() {
        return resourceName;
    }

    public ShareResourceRequestInfo setResourceName(String resourceName) {
        this.resourceName = resourceName;
        return this;
    }

    public ResourceTypeEnum getResourceType() {
        return resourceType;
    }

    public ShareResourceRequestInfo setResourceType(ResourceTypeEnum resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public List<String> getVersionList() {
        return versionList;
    }

    public ShareResourceRequestInfo setVersionList(List<String> versionList) {
        this.versionList = versionList;
        return this;
    }

    public List<String> getAuthWorkspaceIdList() {
        return authWorkspaceIdList;
    }

    public ShareResourceRequestInfo setAuthWorkspaceIdList(List<String> authWorkspaceIdList) {
        this.authWorkspaceIdList = authWorkspaceIdList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShareResourceRequestInfo {\n");

        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceName: ").append(toIndentedString(resourceName)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    versionList: ").append(toIndentedString(versionList)).append("\n");
        sb.append("    authWorkspaceIdList: ").append(toIndentedString(authWorkspaceIdList)).append("\n");
        sb.append("}");
        return sb.toString();
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        ShareResourceRequestInfo shareResourceRequestInfo = (ShareResourceRequestInfo) obj;
        return Objects.equals(this.resourceId, shareResourceRequestInfo.resourceId) && Objects.equals(this.resourceName,
            shareResourceRequestInfo.resourceName) && Objects.equals(this.resourceType,
            shareResourceRequestInfo.resourceType) && Objects.equals(this.versionList,
            shareResourceRequestInfo.versionList) && Objects.equals(this.authWorkspaceIdList,
            shareResourceRequestInfo.authWorkspaceIdList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceName, resourceType, versionList, authWorkspaceIdList);
    }

    private String toIndentedString(Object obj) {
        if (obj == null) {
            return "null";
        }
        return obj.toString().replace("\n", "\n    ");
    }

    /**
     * 资源类型，controller-多智能体、workflow-工作流、plugin-插件
     */
    public enum ResourceTypeEnum {
        CONTROLLER("controller"),

        WORKFLOW("workflow"),

        PLUGIN("plugin"),

        MCP("mcp"),

        PROMPT("prompt");

        private String value;

        ResourceTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ResourceTypeEnum fromValue(String text) {
            for (ResourceTypeEnum b : ResourceTypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
