/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 关联插件对象。
 */
@ApiModel(description = "关联插件对象。")

@Validated

public class ToolReference implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_id")
    @Schema(description = "工具ID", example = "tool001")
    private String toolId = null;

    @JsonProperty("plugin_display_name")
    @Schema(description = "插件显示名称", example = "weather_plugin")
    private String pluginDisplayName = null;

    @JsonProperty("plugin_chinese_name")
    @Schema(description = "插件中文名称", example = "天气插件")
    private String pluginChineseName = null;

    @JsonProperty("tool_display_name")
    @Schema(description = "工具显示名称", example = "weather_tool")
    private String toolDisplayName = null;

    @JsonProperty("tool_chinese_name")
    @Schema(description = "工具中文名称", example = "天气查询")
    private String toolChineseName = null;

    @JsonProperty("tool_parameter")
    @Schema(description = "工具参数", example = "工具参数信息")
    private String toolParameter = null;

    @JsonProperty("tool_icon")
    @Schema(description = "工具图标", example = "icon-tool")
    private String toolIcon = null;

    @JsonProperty("limit")
    @Schema(description = "限制次数", example = "100")
    private Integer limit = null;

    @JsonProperty("usage")
    @Schema(description = "使用次数", example = "50")
    private Integer usage = null;

    @JsonProperty("is_free")
    @Schema(description = "是否免费", example = "1")
    private Integer isFree = null;

    @JsonProperty("credential_status")
    @Schema(description = "凭证状态", example = "valid")
    private String credentialStatus = null;

    @JsonProperty("desc")
    @Schema(description = "描述", example = "工具描述信息")
    @Length(min = 1, max = 600)
    private String desc = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "认证配置信息")
    @Valid
    private AuthInfo authInfo = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "元数据信息")
    private String metadata = null;

    @JsonProperty("last_version_id")
    @Schema(description = "最新版本ID", example = "v002")
    private String lastVersionId = null;

    @JsonProperty("last_version_name")
    @Schema(description = "最新版本名称", example = "v2.0.0")
    private String lastVersionName = null;

    public String getToolId() {
        return toolId;
    }

    public ToolReference setToolId(String toolId) {
        this.toolId = toolId;
        return this;
    }

    public String getPluginDisplayName() {
        return pluginDisplayName;
    }

    public ToolReference setPluginDisplayName(String pluginDisplayName) {
        this.pluginDisplayName = pluginDisplayName;
        return this;
    }

    public String getPluginChineseName() {
        return pluginChineseName;
    }

    public ToolReference setPluginChineseName(String pluginChineseName) {
        this.pluginChineseName = pluginChineseName;
        return this;
    }

    public String getToolDisplayName() {
        return toolDisplayName;
    }

    public ToolReference setToolDisplayName(String toolDisplayName) {
        this.toolDisplayName = toolDisplayName;
        return this;
    }

    public String getToolChineseName() {
        return toolChineseName;
    }

    public ToolReference setToolChineseName(String toolChineseName) {
        this.toolChineseName = toolChineseName;
        return this;
    }

    public String getToolParameter() {
        return toolParameter;
    }

    public ToolReference setToolParameter(String toolParameter) {
        this.toolParameter = toolParameter;
        return this;
    }

    public String getToolIcon() {
        return toolIcon;
    }

    public ToolReference setToolIcon(String toolIcon) {
        this.toolIcon = toolIcon;
        return this;
    }

    public Integer getLimit() {
        return limit;
    }

    public ToolReference setLimit(Integer limit) {
        this.limit = limit;
        return this;
    }

    public Integer getUsage() {
        return usage;
    }

    public ToolReference setUsage(Integer usage) {
        this.usage = usage;
        return this;
    }

    public Integer getIsFree() {
        return isFree;
    }

    public ToolReference setIsFree(Integer isFree) {
        this.isFree = isFree;
        return this;
    }

    public String getCredentialStatus() {
        return credentialStatus;
    }

    public ToolReference setCredentialStatus(String credentialStatus) {
        this.credentialStatus = credentialStatus;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public ToolReference setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public ToolReference setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    public String getMetadata() {
        return metadata;
    }

    public ToolReference setMetadata(String metadata) {
        this.metadata = metadata;
        return this;
    }

    public String getLastVersionId() {
        return lastVersionId;
    }

    public ToolReference setLastVersionId(String lastVersionId) {
        this.lastVersionId = lastVersionId;
        return this;
    }

    public String getLastVersionName() {
        return lastVersionName;
    }

    public ToolReference setLastVersionName(String lastVersionName) {
        this.lastVersionName = lastVersionName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ToolReference {\n");

        sb.append("    toolId: ").append(toIndentedString(toolId)).append("\n");
        sb.append("    pluginDisplayName: ").append(toIndentedString(pluginDisplayName)).append("\n");
        sb.append("    pluginChineseName: ").append(toIndentedString(pluginChineseName)).append("\n");
        sb.append("    toolDisplayName: ").append(toIndentedString(toolDisplayName)).append("\n");
        sb.append("    toolChineseName: ").append(toIndentedString(toolChineseName)).append("\n");
        sb.append("    toolParameter: ").append(toIndentedString(toolParameter)).append("\n");
        sb.append("    toolIcon: ").append(toIndentedString(toolIcon)).append("\n");
        sb.append("    limit: ").append(toIndentedString(limit)).append("\n");
        sb.append("    usage: ").append(toIndentedString(usage)).append("\n");
        sb.append("    isFree: ").append(toIndentedString(isFree)).append("\n");
        sb.append("    credentialStatus: ").append(toIndentedString(credentialStatus)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    lastVersionId: ").append(toIndentedString(lastVersionId)).append("\n");
        sb.append("    lastVersionName: ").append(toIndentedString(lastVersionName)).append("\n");
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
        ToolReference toolReference = (ToolReference) o;
        return Objects.equals(this.toolId, toolReference.toolId) && Objects.equals(this.pluginDisplayName,
            toolReference.pluginDisplayName) && Objects.equals(this.pluginChineseName, toolReference.pluginChineseName)
            && Objects.equals(this.toolDisplayName, toolReference.toolDisplayName) && Objects.equals(
            this.toolChineseName, toolReference.toolChineseName) && Objects.equals(this.toolParameter,
            toolReference.toolParameter) && Objects.equals(this.toolIcon, toolReference.toolIcon) && Objects.equals(
            this.limit, toolReference.limit) && Objects.equals(this.usage, toolReference.usage) && Objects.equals(
            this.isFree, toolReference.isFree) && Objects.equals(this.credentialStatus, toolReference.credentialStatus)
            && Objects.equals(this.desc, toolReference.desc) && Objects.equals(this.authInfo, toolReference.authInfo)
            && Objects.equals(this.metadata, toolReference.metadata) && Objects.equals(this.lastVersionId,
            toolReference.lastVersionId) && Objects.equals(this.lastVersionName, toolReference.lastVersionName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolId, pluginDisplayName, pluginChineseName, toolDisplayName, toolChineseName,
            toolParameter, toolIcon, limit, usage, isFree, credentialStatus, desc, authInfo, metadata, lastVersionId,
            lastVersionName);
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
