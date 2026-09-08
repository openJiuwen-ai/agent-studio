/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * mcp 服务信息
 */
@ApiModel(description = "mcp 服务信息")

@Validated

public class McpServiceBatchDeployItem implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("third_id")
    @Schema(description = "第三方ID", example = "third_001")
    @Length(max = 64)
    private String thirdId = null;

    @JsonProperty("third_version_id")
    @Schema(description = "第三方版本ID", example = "ver_001")
    private String thirdVersionId = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "天气查询服务")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "Weather Service")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "服务描述", example = "提供天气查询功能")
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "服务英文描述", example = "Provide weather query")
    private String descriptionEn = null;

    @JsonProperty("org_type")
    @Schema(description = "组织类型", example = "enterprise")
    private String orgType = null;

    @JsonProperty("server_config")
    @Schema(description = "服务配置", example = "{\"port\":8080}")
    private String serverConfig = null;

    @JsonProperty("icon")
    @Schema(description = "服务图标", example = "https://example.com/icon.png")
    private String icon = null;

    @JsonProperty("readme")
    @Schema(description = "服务说明文档", example = "服务使用说明")
    private String readme = null;

    public String getThirdId() {
        return thirdId;
    }

    public McpServiceBatchDeployItem setThirdId(String thirdId) {
        this.thirdId = thirdId;
        return this;
    }

    public String getThirdVersionId() {
        return thirdVersionId;
    }

    public McpServiceBatchDeployItem setThirdVersionId(String thirdVersionId) {
        this.thirdVersionId = thirdVersionId;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServiceBatchDeployItem setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServiceBatchDeployItem setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServiceBatchDeployItem setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServiceBatchDeployItem setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getOrgType() {
        return orgType;
    }

    public McpServiceBatchDeployItem setOrgType(String orgType) {
        this.orgType = orgType;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServiceBatchDeployItem setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServiceBatchDeployItem setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getReadme() {
        return readme;
    }

    public McpServiceBatchDeployItem setReadme(String readme) {
        this.readme = readme;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceBatchDeployItem {\n");

        sb.append("    thirdId: ").append(toIndentedString(thirdId)).append("\n");
        sb.append("    thirdVersionId: ").append(toIndentedString(thirdVersionId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    orgType: ").append(toIndentedString(orgType)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    readme: ").append(toIndentedString(readme)).append("\n");
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
        McpServiceBatchDeployItem mcpServiceBatchDeployItem = (McpServiceBatchDeployItem) o;
        return Objects.equals(this.thirdId, mcpServiceBatchDeployItem.thirdId) && Objects.equals(this.thirdVersionId,
            mcpServiceBatchDeployItem.thirdVersionId) && Objects.equals(this.name, mcpServiceBatchDeployItem.name)
            && Objects.equals(this.nameEn, mcpServiceBatchDeployItem.nameEn) && Objects.equals(this.description,
            mcpServiceBatchDeployItem.description) && Objects.equals(this.descriptionEn,
            mcpServiceBatchDeployItem.descriptionEn) && Objects.equals(this.orgType, mcpServiceBatchDeployItem.orgType)
            && Objects.equals(this.serverConfig, mcpServiceBatchDeployItem.serverConfig) && Objects.equals(this.icon,
            mcpServiceBatchDeployItem.icon) && Objects.equals(this.readme, mcpServiceBatchDeployItem.readme);
    }

    @Override
    public int hashCode() {
        return Objects.hash(thirdId, thirdVersionId, name, nameEn, description, descriptionEn, orgType, serverConfig,
            icon, readme);
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
