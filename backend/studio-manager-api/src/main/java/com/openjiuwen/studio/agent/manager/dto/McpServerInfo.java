/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;
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
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServerInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("server_id")
    @Schema(description = "服务ID", example = "550e8400-e29b-41d4-a716-446655440000")
    @Length(max = 64)
    private String serverId = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "project-001")
    @Length(max = 64)
    private String projectId = null;

    @JsonProperty("workspace_id")
    @Schema(description = "工作空间ID", example = "workspace-001")
    @Length(max = 64)
    private String workspaceId = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "my-mcp-server")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "my-mcp-server")
    private String nameEn = null;

    @JsonProperty("desc")
    @Schema(description = "服务描述", example = "这是一个MCP服务")
    @Length(max = 1000)
    private String desc = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-url")
    private String icon = null;

    @JsonProperty("icon_name")
    @Schema(description = "图标名称", example = "550e8400-e29b-41d4-a716-446655440000.png")
    @Pattern(
        regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\\.[a-zA-Z]+$")
    private String iconName = null;

    @JsonProperty("tools")
    @Schema(description = "工具配置", example = "{}")
    @Valid
    private McpServerTools tools = null;

    @JsonProperty("visibility")
    @Schema(description = "可见性", example = "public")
    @Length(max = 32)
    private String visibility = null;

    @JsonProperty("url")
    @Schema(description = "服务URL", example = "https://example.com/mcp")
    @Length(max = 256)
    private String url = null;

    @JsonProperty("auth")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo auth = null;

    @JsonProperty("type")
    @Schema(description = "服务类型", example = "mcp")
    @Length(max = 32)
    private String type = null;

    @JsonProperty("category")
    @Schema(description = "服务分类", example = "tool")
    @Length(max = 32)
    private String category = null;

    @JsonProperty("configs")
    @Schema(description = "服务配置", example = "{}")
    @Valid
    private McpServerConfig configs = null;

    @JsonProperty("config_status")
    @Schema(description = "配置状态", example = "configured")
    @Length(max = 32)
    private String configStatus = null;

    @JsonProperty("binding")
    @Schema(description = "是否绑定", example = "true")
    private Boolean binding = null;

    @JsonProperty("creator")
    @Schema(description = "创建者", example = "user001")
    @Length(max = 64)
    private String creator = null;

    @JsonProperty("creator_id")
    @Schema(description = "创建者ID", example = "user-001")
    @Length(max = 64)
    private String creatorId = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "2024-05-01T00:00:00.000Z")
    private Date createTime = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "2024-05-01T00:00:00.000Z")
    private Date updateTime = null;

    @JsonProperty("service_config")
    @Schema(description = "服务配置", example = "{}")
    @Length(max = 30000)
    private String serviceConfig = null;

    @JsonProperty("mcp_tool")
    @Schema(description = "MCP工具", example = "[]")
    @Length(max = 500000)
    private String mcpTool = null;

    @JsonProperty("org_type")
    @Schema(description = "组织类型", example = "enterprise")
    private String orgType = null;

    @JsonProperty("deploy_type")
    @Schema(description = "部署类型", example = "function")
    private String deployType = null;

    @JsonProperty("trace_id")
    @Schema(description = "链路追踪ID", example = "trace-001")
    @Length(max = 64)
    private String traceId = null;

    @JsonProperty("share_info")
    @Schema(description = "分享信息", example = "{}")
    @Valid
    private ShareInfo shareInfo = null;

    @JsonProperty("share_reference")
    @Schema(description = "分享引用列表", example = "[]")
    @Valid
    @Size()
    private List<MappingEntity> shareReference = null;

    @JsonProperty("origin")
    @Schema(description = "来源", example = "0")
    private Integer origin = null;

    public String getServerId() {
        return serverId;
    }

    public McpServerInfo setServerId(String serverId) {
        this.serverId = serverId;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public McpServerInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getWorkspaceId() {
        return workspaceId;
    }

    public McpServerInfo setWorkspaceId(String workspaceId) {
        this.workspaceId = workspaceId;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServerInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServerInfo setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public McpServerInfo setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServerInfo setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getIconName() {
        return iconName;
    }

    public McpServerInfo setIconName(String iconName) {
        this.iconName = iconName;
        return this;
    }

    public McpServerTools getTools() {
        return tools;
    }

    public McpServerInfo setTools(McpServerTools tools) {
        this.tools = tools;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public McpServerInfo setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public McpServerInfo setUrl(String url) {
        this.url = url;
        return this;
    }

    public AuthInfo getAuth() {
        return auth;
    }

    public McpServerInfo setAuth(AuthInfo auth) {
        this.auth = auth;
        return this;
    }

    public String getType() {
        return type;
    }

    public McpServerInfo setType(String type) {
        this.type = type;
        return this;
    }

    public String getCategory() {
        return category;
    }

    public McpServerInfo setCategory(String category) {
        this.category = category;
        return this;
    }

    public McpServerConfig getConfigs() {
        return configs;
    }

    public McpServerInfo setConfigs(McpServerConfig configs) {
        this.configs = configs;
        return this;
    }

    public String getConfigStatus() {
        return configStatus;
    }

    public McpServerInfo setConfigStatus(String configStatus) {
        this.configStatus = configStatus;
        return this;
    }

    public McpServerInfo setBinding(Boolean binding) {
        this.binding = binding;
        return this;
    }

    public Boolean isBinding() {
        return binding;
    }

    public String getCreator() {
        return creator;
    }

    public McpServerInfo setCreator(String creator) {
        this.creator = creator;
        return this;
    }

    public String getCreatorId() {
        return creatorId;
    }

    public McpServerInfo setCreatorId(String creatorId) {
        this.creatorId = creatorId;
        return this;
    }

    public Date getCreateTime() {
        return createTime;
    }

    public McpServerInfo setCreateTime(Date createTime) {
        this.createTime = createTime;
        return this;
    }

    public Date getUpdateTime() {
        return updateTime;
    }

    public McpServerInfo setUpdateTime(Date updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public String getServiceConfig() {
        return serviceConfig;
    }

    public McpServerInfo setServiceConfig(String serviceConfig) {
        this.serviceConfig = serviceConfig;
        return this;
    }

    public String getMcpTool() {
        return mcpTool;
    }

    public McpServerInfo setMcpTool(String mcpTool) {
        this.mcpTool = mcpTool;
        return this;
    }

    public String getOrgType() {
        return orgType;
    }

    public McpServerInfo setOrgType(String orgType) {
        this.orgType = orgType;
        return this;
    }

    public String getDeployType() {
        return deployType;
    }

    public McpServerInfo setDeployType(String deployType) {
        this.deployType = deployType;
        return this;
    }

    public String getTraceId() {
        return traceId;
    }

    public McpServerInfo setTraceId(String traceId) {
        this.traceId = traceId;
        return this;
    }

    public ShareInfo getShareInfo() {
        return shareInfo;
    }

    public McpServerInfo setShareInfo(ShareInfo shareInfo) {
        this.shareInfo = shareInfo;
        return this;
    }

    public List<MappingEntity> getShareReference() {
        return shareReference;
    }

    public McpServerInfo setShareReference(List<MappingEntity> shareReference) {
        this.shareReference = shareReference;
        return this;
    }

    public Integer getOrigin() {
        return origin;
    }

    public McpServerInfo setOrigin(Integer origin) {
        this.origin = origin;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerInfo {\n");

        sb.append("    serverId: ").append(toIndentedString(serverId)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    workspaceId: ").append(toIndentedString(workspaceId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    iconName: ").append(toIndentedString(iconName)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
        sb.append("    visibility: ").append(toIndentedString(visibility)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    auth: ").append(toIndentedString(auth)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    category: ").append(toIndentedString(category)).append("\n");
        sb.append("    configs: ").append(toIndentedString(configs)).append("\n");
        sb.append("    configStatus: ").append(toIndentedString(configStatus)).append("\n");
        sb.append("    binding: ").append(toIndentedString(binding)).append("\n");
        sb.append("    creator: ").append(toIndentedString(creator)).append("\n");
        sb.append("    creatorId: ").append(toIndentedString(creatorId)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    serviceConfig: ").append(toIndentedString(serviceConfig)).append("\n");
        sb.append("    mcpTool: ").append(toIndentedString(mcpTool)).append("\n");
        sb.append("    orgType: ").append(toIndentedString(orgType)).append("\n");
        sb.append("    deployType: ").append(toIndentedString(deployType)).append("\n");
        sb.append("    traceId: ").append(toIndentedString(traceId)).append("\n");
        sb.append("    shareInfo: ").append(toIndentedString(shareInfo)).append("\n");
        sb.append("    shareReference: ").append(toIndentedString(shareReference)).append("\n");
        sb.append("    origin: ").append(toIndentedString(origin)).append("\n");
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
        McpServerInfo mcpServerInfo = (McpServerInfo) o;
        return Objects.equals(this.serverId, mcpServerInfo.serverId) && Objects.equals(this.projectId,
            mcpServerInfo.projectId) && Objects.equals(this.workspaceId, mcpServerInfo.workspaceId) && Objects.equals(
            this.name, mcpServerInfo.name) && Objects.equals(this.nameEn, mcpServerInfo.nameEn) && Objects.equals(
            this.desc, mcpServerInfo.desc) && Objects.equals(this.icon, mcpServerInfo.icon) && Objects.equals(
            this.iconName, mcpServerInfo.iconName) && Objects.equals(this.tools, mcpServerInfo.tools) && Objects.equals(
            this.visibility, mcpServerInfo.visibility) && Objects.equals(this.url, mcpServerInfo.url) && Objects.equals(
            this.auth, mcpServerInfo.auth) && Objects.equals(this.type, mcpServerInfo.type) && Objects.equals(
            this.category, mcpServerInfo.category) && Objects.equals(this.configs, mcpServerInfo.configs)
            && Objects.equals(this.configStatus, mcpServerInfo.configStatus) && Objects.equals(this.binding,
            mcpServerInfo.binding) && Objects.equals(this.creator, mcpServerInfo.creator) && Objects.equals(
            this.creatorId, mcpServerInfo.creatorId) && Objects.equals(this.createTime, mcpServerInfo.createTime)
            && Objects.equals(this.updateTime, mcpServerInfo.updateTime) && Objects.equals(this.serviceConfig,
            mcpServerInfo.serviceConfig) && Objects.equals(this.mcpTool, mcpServerInfo.mcpTool) && Objects.equals(
            this.orgType, mcpServerInfo.orgType) && Objects.equals(this.deployType, mcpServerInfo.deployType)
            && Objects.equals(this.traceId, mcpServerInfo.traceId) && Objects.equals(this.shareInfo,
            mcpServerInfo.shareInfo) && Objects.equals(this.shareReference, mcpServerInfo.shareReference)
            && Objects.equals(this.origin, mcpServerInfo.origin);
    }

    @Override
    public int hashCode() {
        return Objects.hash(serverId, projectId, workspaceId, name, nameEn, desc, icon, iconName, tools, visibility,
            url, auth, type, category, configs, configStatus, binding, creator, creatorId, createTime, updateTime,
            serviceConfig, mcpTool, orgType, deployType, traceId, shareInfo, shareReference, origin);
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
