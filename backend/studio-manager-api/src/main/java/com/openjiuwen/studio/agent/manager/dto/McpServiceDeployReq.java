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

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceDeployReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "MCP服务ID", example = "mcp_001")
    @Pattern(regexp = "^[a-zA-Z0-9-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "MCP服务名称", example = "我的MCP服务")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "MCP服务英文名称", example = "MyMcpService")
    @Pattern(regexp = "^[a-zA-Z0-9\\s.,!?;:'\"()_（）-]{2,64}$")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "MCP服务描述", example = "这是一个MCP服务")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "MCP服务英文描述", example = "This is an MCP service")
    @Length(max = 2048)
    private String descriptionEn = null;

    @JsonProperty("org_type")
    @Schema(description = "组织类型", example = "TEAM")
    private String orgType = null;

    @JsonProperty("server_config")
    @Schema(description = "服务端配置", example = "{}")
    private String serverConfig = null;

    @JsonProperty("readme")
    @Schema(description = "说明文档", example = "README内容")
    private String readme = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-url")
    private String icon = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo authInfo = null;

    public String getId() {
        return id;
    }

    public McpServiceDeployReq setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServiceDeployReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServiceDeployReq setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServiceDeployReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServiceDeployReq setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getOrgType() {
        return orgType;
    }

    public McpServiceDeployReq setOrgType(String orgType) {
        this.orgType = orgType;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServiceDeployReq setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getReadme() {
        return readme;
    }

    public McpServiceDeployReq setReadme(String readme) {
        this.readme = readme;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServiceDeployReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public McpServiceDeployReq setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceDeployReq {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    orgType: ").append(toIndentedString(orgType)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    readme: ").append(toIndentedString(readme)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    authInfo: ").append(toIndentedString(authInfo)).append("\n");
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
        McpServiceDeployReq mcpServiceDeployReq = (McpServiceDeployReq) o;
        return Objects.equals(this.id, mcpServiceDeployReq.id) && Objects.equals(this.name, mcpServiceDeployReq.name)
            && Objects.equals(this.nameEn, mcpServiceDeployReq.nameEn) && Objects.equals(this.description,
            mcpServiceDeployReq.description) && Objects.equals(this.descriptionEn, mcpServiceDeployReq.descriptionEn)
            && Objects.equals(this.orgType, mcpServiceDeployReq.orgType) && Objects.equals(this.serverConfig,
            mcpServiceDeployReq.serverConfig) && Objects.equals(this.readme, mcpServiceDeployReq.readme)
            && Objects.equals(this.icon, mcpServiceDeployReq.icon) && Objects.equals(this.authInfo,
            mcpServiceDeployReq.authInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description, descriptionEn, orgType, serverConfig, readme, icon,
            authInfo);
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
