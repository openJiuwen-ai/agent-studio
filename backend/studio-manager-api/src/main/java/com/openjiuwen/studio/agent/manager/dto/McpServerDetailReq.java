/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
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

public class McpServerDetailReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "MCP服务ID", example = "mcp_001")
    @Pattern(regexp = "^[a-zA-Z0-9-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("serverCode")
    @Schema(description = "服务编码", example = "my_mcp_server")
    @Pattern(regexp = "^(?!_)(?!-)(?!\\d)[a-zA-Z0-9_\\-\\u4e00-\\u9fa5]{2,64}$")
    private String serverCode = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "我的MCP服务")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "英文名称", example = "My Mcp Server")
    @Pattern(regexp = "^[a-zA-Z0-9\\s.,!?;:'\"()_（）-]{2,64}$")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "这是一个MCP服务")
    @Length(max = 1024)
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "英文描述", example = "This is an MCP server")
    @Length(max = 2048)
    private String descriptionEn = null;

    @JsonProperty("url")
    @Schema(description = "服务地址", example = "https://example.com/mcp")
    @Pattern(regexp = "(http|https)://[a-zA-Z0-9-.]+(:[0-9]+)?(/\\S*)?")
    private String url = null;

    @JsonProperty("type")
    @Schema(description = "类型", example = "sse")
    private String type = null;

    @JsonProperty("deploy_type")
    @Schema(description = "部署类型", example = "remote")
    private String deployType = null;

    @JsonProperty("server_config")
    @Schema(description = "服务配置", example = "{}")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5_a-zA-Z0-9\\-,.?:;\"'：=；“”‘’//，。？、()（）\\[\\]{}/@!！*%# \\s]*$")
    private String serverConfig = null;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "[]")
    private String tools = null;

    public String getId() {
        return id;
    }

    public McpServerDetailReq setId(String id) {
        this.id = id;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServerDetailReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getServerCode() {
        return serverCode;
    }

    public McpServerDetailReq setServerCode(String serverCode) {
        this.serverCode = serverCode;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServerDetailReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServerDetailReq setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServerDetailReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServerDetailReq setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public McpServerDetailReq setUrl(String url) {
        this.url = url;
        return this;
    }

    public String getType() {
        return type;
    }

    public McpServerDetailReq setType(String type) {
        this.type = type;
        return this;
    }

    public String getDeployType() {
        return deployType;
    }

    public McpServerDetailReq setDeployType(String deployType) {
        this.deployType = deployType;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServerDetailReq setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getTools() {
        return tools;
    }

    public McpServerDetailReq setTools(String tools) {
        this.tools = tools;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerDetailReq {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    serverCode: ").append(toIndentedString(serverCode)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    deployType: ").append(toIndentedString(deployType)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
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
        McpServerDetailReq mcpServerDetailReq = (McpServerDetailReq) o;
        return Objects.equals(this.id, mcpServerDetailReq.id) && Objects.equals(this.icon, mcpServerDetailReq.icon)
            && Objects.equals(this.serverCode, mcpServerDetailReq.serverCode) && Objects.equals(this.name,
            mcpServerDetailReq.name) && Objects.equals(this.nameEn, mcpServerDetailReq.nameEn) && Objects.equals(
            this.description, mcpServerDetailReq.description) && Objects.equals(this.descriptionEn,
            mcpServerDetailReq.descriptionEn) && Objects.equals(this.url, mcpServerDetailReq.url) && Objects.equals(
            this.type, mcpServerDetailReq.type) && Objects.equals(this.deployType, mcpServerDetailReq.deployType)
            && Objects.equals(this.serverConfig, mcpServerDetailReq.serverConfig) && Objects.equals(this.tools,
            mcpServerDetailReq.tools);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, icon, serverCode, name, nameEn, description, descriptionEn, url, type, deployType,
            serverConfig, tools);
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
