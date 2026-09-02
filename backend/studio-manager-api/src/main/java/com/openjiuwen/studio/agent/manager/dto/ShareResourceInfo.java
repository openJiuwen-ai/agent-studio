/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import io.swagger.v3.oas.annotations.media.Schema;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * ShareResourceInfo
 */

@Validated

public class ShareResourceInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("resource_id")
    @Schema(description = "资源ID", example = "res_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String resourceId = null;

    @JsonProperty("resource_type")
    @Schema(description = "资源类型", example = "workflow")
    private ResourceTypeEnum resourceType = null;

    @JsonProperty("version_info_list")
    @Schema(description = "版本信息列表", example = "[]")
    @Valid
    @Size(min = 1, max = 50)
    private List<ResourceVersionInfo> versionInfoList = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "ws_001")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("workspace_name")
    @Schema(description = "工作空间名称", example = "我的工作空间")
    @Length(max = 64)
    private String workspaceName = null;

    @JsonProperty("resource_name_ch")
    @Schema(description = "资源中文名称", example = "我的工作流")
    @Length(max = 128)
    private String resourceNameCh = null;

    @JsonProperty("resource_name_en")
    @Schema(description = "资源英文名称", example = "My Workflow")
    @Length(max = 128)
    private String resourceNameEn = null;

    @JsonProperty("resource_desc")
    @Schema(description = "资源描述", example = "这是一个共享资源")
    @Length(max = 256)
    private String resourceDesc = null;

    @JsonProperty("resource_icon")
    @Schema(description = "资源图标", example = "https://example.com/icon.png")
    private String resourceIcon = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "张三")
    private String creator = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "workflow")
    private String type = null;

    @JsonProperty("extend_attribute")
    @Schema(description = "扩展属性", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> extendAttribute = null;

    public String getResourceId() {
        return resourceId;
    }

    public ShareResourceInfo setResourceId(String resourceId) {
        this.resourceId = resourceId;
        return this;
    }

    public ResourceTypeEnum getResourceType() {
        return resourceType;
    }

    public ShareResourceInfo setResourceType(ResourceTypeEnum resourceType) {
        this.resourceType = resourceType;
        return this;
    }

    public List<ResourceVersionInfo> getVersionInfoList() {
        return versionInfoList;
    }

    public ShareResourceInfo setVersionInfoList(List<ResourceVersionInfo> versionInfoList) {
        this.versionInfoList = versionInfoList;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public ShareResourceInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getWorkspaceName() {
        return workspaceName;
    }

    public ShareResourceInfo setWorkspaceName(String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    public String getResourceNameCh() {
        return resourceNameCh;
    }

    public ShareResourceInfo setResourceNameCh(String resourceNameCh) {
        this.resourceNameCh = resourceNameCh;
        return this;
    }

    public String getResourceNameEn() {
        return resourceNameEn;
    }

    public ShareResourceInfo setResourceNameEn(String resourceNameEn) {
        this.resourceNameEn = resourceNameEn;
        return this;
    }

    public String getResourceDesc() {
        return resourceDesc;
    }

    public ShareResourceInfo setResourceDesc(String resourceDesc) {
        this.resourceDesc = resourceDesc;
        return this;
    }

    public String getResourceIcon() {
        return resourceIcon;
    }

    public ShareResourceInfo setResourceIcon(String resourceIcon) {
        this.resourceIcon = resourceIcon;
        return this;
    }

    public String getCreator() {
        return creator;
    }

    public ShareResourceInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getType() {
        return type;
    }

    public ShareResourceInfo setType(String type) {
        this.type = type;
        return this;
    }

    public Map<String, Object> getExtendAttribute() {
        return extendAttribute;
    }

    public ShareResourceInfo setExtendAttribute(Map<String, Object> extendAttribute) {
        this.extendAttribute = extendAttribute;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ShareResourceInfo {\n");

        sb.append("    resourceId: ").append(toIndentedString(resourceId)).append("\n");
        sb.append("    resourceType: ").append(toIndentedString(resourceType)).append("\n");
        sb.append("    versionInfoList: ").append(toIndentedString(versionInfoList)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    workspaceName: ").append(toIndentedString(workspaceName)).append("\n");
        sb.append("    resourceNameCh: ").append(toIndentedString(resourceNameCh)).append("\n");
        sb.append("    resourceNameEn: ").append(toIndentedString(resourceNameEn)).append("\n");
        sb.append("    resourceDesc: ").append(toIndentedString(resourceDesc)).append("\n");
        sb.append("    resourceIcon: ").append(toIndentedString(resourceIcon)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    extendAttribute: ").append(toIndentedString(extendAttribute)).append("\n");
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
        ShareResourceInfo shareResourceInfo = (ShareResourceInfo) obj;
        return Objects.equals(this.resourceId, shareResourceInfo.resourceId) && Objects.equals(this.resourceType,
            shareResourceInfo.resourceType) && Objects.equals(this.versionInfoList, shareResourceInfo.versionInfoList)
            && Objects.equals(this.workspaceId, shareResourceInfo.workspaceId) && Objects.equals(this.workspaceName,
            shareResourceInfo.workspaceName) && Objects.equals(this.resourceNameCh, shareResourceInfo.resourceNameCh)
            && Objects.equals(this.resourceNameEn, shareResourceInfo.resourceNameEn) && Objects.equals(
            this.resourceDesc, shareResourceInfo.resourceDesc) && Objects.equals(this.resourceIcon,
            shareResourceInfo.resourceIcon) && Objects.equals(this.creator, shareResourceInfo.creator)
            && Objects.equals(this.type, shareResourceInfo.type) && Objects.equals(this.extendAttribute,
            shareResourceInfo.extendAttribute);
    }

    @Override
    public int hashCode() {
        return Objects.hash(resourceId, resourceType, versionInfoList, workspaceId, workspaceName, resourceNameCh,
            resourceNameEn, resourceDesc, resourceIcon, creator, type, extendAttribute);
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
