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
 * mcp 服务请求体
 */
@ApiModel(description = "mcp 服务请求体")

@Validated

public class McpServerReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "MCP服务ID", example = "mcp_001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "MCP服务名称", example = "天气查询服务")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "MCP服务英文名称", example = "weather_service")
    @Pattern(regexp = "^[a-zA-Z0-9_-]+$")
    @Length(max = 64)
    private String nameEn = null;

    @JsonProperty("desc")
    @Schema(description = "MCP服务描述", example = "提供天气信息查询服务")
    @Length(max = 1000)
    private String desc = null;

    @JsonProperty("icon")
    @Schema(description = "MCP服务图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("visibility")
    @Schema(description = "可见性", example = "private")
    @Length(max = 32)
    private String visibility = null;

    @JsonProperty("url")
    @Schema(description = "MCP服务URL", example = "https://mcp.example.com/api")
    @Length(max = 256)
    private String url = null;

    @JsonProperty("auth")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo auth = null;

    @JsonProperty("is_template")
    @Schema(description = "是否为模板", example = "false")
    private Boolean isTemplate = false;

    public String getId() {
        return id;
    }

    public McpServerReq setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServerReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServerReq setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDesc() {
        return desc;
    }

    public McpServerReq setDesc(String desc) {
        this.desc = desc;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServerReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getVisibility() {
        return visibility;
    }

    public McpServerReq setVisibility(String visibility) {
        this.visibility = visibility;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public McpServerReq setUrl(String url) {
        this.url = url;
        return this;
    }

    public AuthInfo getAuth() {
        return auth;
    }

    public McpServerReq setAuth(AuthInfo auth) {
        this.auth = auth;
        return this;
    }

    public McpServerReq setIsTemplate(Boolean isTemplate) {
        this.isTemplate = isTemplate;
        return this;
    }

    public Boolean isIsTemplate() {
        return isTemplate;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerReq {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    desc: ").append(toIndentedString(desc)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    visibility: ").append(toIndentedString(visibility)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    auth: ").append(toIndentedString(auth)).append("\n");
        sb.append("    isTemplate: ").append(toIndentedString(isTemplate)).append("\n");
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
        McpServerReq mcpServerReq = (McpServerReq) o;
        return Objects.equals(this.id, mcpServerReq.id) && Objects.equals(this.name, mcpServerReq.name)
            && Objects.equals(this.nameEn, mcpServerReq.nameEn) && Objects.equals(this.desc, mcpServerReq.desc)
            && Objects.equals(this.icon, mcpServerReq.icon) && Objects.equals(this.visibility, mcpServerReq.visibility)
            && Objects.equals(this.url, mcpServerReq.url) && Objects.equals(this.auth, mcpServerReq.auth)
            && Objects.equals(this.isTemplate, mcpServerReq.isTemplate);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, desc, icon, visibility, url, auth, isTemplate);
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
