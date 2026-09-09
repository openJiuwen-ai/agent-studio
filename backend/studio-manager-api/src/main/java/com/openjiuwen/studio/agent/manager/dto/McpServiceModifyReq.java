/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 已部署的mcp服务变更
 */
@ApiModel(description = "已部署的mcp服务变更")

@Validated

public class McpServiceModifyReq implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "服务ID", example = "svc_001")
    @Pattern(regexp = "^[a-zA-Z0-9-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "天气查询服务")
    @NotEmpty
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "Weather Service")
    @Pattern(regexp = "^[a-zA-Z0-9\\s.,!?;:'\"()_（）-]{2,64}$")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "服务描述", example = "提供天气查询功能")
    @Length(min = 1, max = 1024)
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "服务英文描述", example = "Provide weather query")
    @Length(min = 1, max = 2048)
    private String descriptionEn = null;

    @JsonProperty("icon")
    @Schema(description = "服务图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("server_config")
    @Schema(description = "服务配置", example = "{\"port\":8080}")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5_a-zA-Z0-9\\-,.?:;\"'：=；“”‘’//，。？、()（）\\[\\]{}/@!！*%# \\s]*$")
    private String serverConfig = null;

    @JsonProperty("readme")
    @Schema(description = "服务说明文档", example = "服务使用说明")
    private String readme = null;

    @JsonProperty("auth_info")
    @Schema(description = "认证信息", example = "{}")
    @Valid
    private AuthInfo authInfo = null;

    public String getId() {
        return id;
    }

    public McpServiceModifyReq setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServiceModifyReq setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServiceModifyReq setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServiceModifyReq setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServiceModifyReq setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServiceModifyReq setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServiceModifyReq setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getReadme() {
        return readme;
    }

    public McpServiceModifyReq setReadme(String readme) {
        this.readme = readme;
        return this;
    }

    public AuthInfo getAuthInfo() {
        return authInfo;
    }

    public McpServiceModifyReq setAuthInfo(AuthInfo authInfo) {
        this.authInfo = authInfo;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceModifyReq {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    readme: ").append(toIndentedString(readme)).append("\n");
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
        McpServiceModifyReq mcpServiceModifyReq = (McpServiceModifyReq) o;
        return Objects.equals(this.id, mcpServiceModifyReq.id) && Objects.equals(this.name, mcpServiceModifyReq.name)
            && Objects.equals(this.nameEn, mcpServiceModifyReq.nameEn) && Objects.equals(this.description,
            mcpServiceModifyReq.description) && Objects.equals(this.descriptionEn, mcpServiceModifyReq.descriptionEn)
            && Objects.equals(this.icon, mcpServiceModifyReq.icon) && Objects.equals(this.serverConfig,
            mcpServiceModifyReq.serverConfig) && Objects.equals(this.readme, mcpServiceModifyReq.readme)
            && Objects.equals(this.authInfo, mcpServiceModifyReq.authInfo);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description, descriptionEn, icon, serverConfig, readme, authInfo);
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
