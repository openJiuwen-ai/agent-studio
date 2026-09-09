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

public class McpServerDetailInfoDto implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "服务ID", example = "mcp-server-001")
    @Pattern(regexp = "^[a-zA-Z0-9-]+$")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-server")
    private String icon = null;

    @JsonProperty("serverCode")
    @Schema(description = "服务编码", example = "weather-service")
    @Pattern(regexp = "^(?!_)(?!-)(?!\\d)[a-zA-Z0-9_\\-\\u4e00-\\u9fa5]{2,64}$")
    private String serverCode = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "天气服务")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "Weather Service")
    @Pattern(regexp = "^[a-zA-Z0-9\\s.,!?;:'\"()_（）-]{2,64}$")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "服务描述", example = "提供天气查询功能")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5_a-zA-Z0-9\\-,.?:;\"'：；“”‘’，。？、()（）/@!！*%# ]*$")
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "服务英文描述", example = "Provide weather query functionality")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5_a-zA-Z0-9\\-,.?:;\"'：；“”‘’，。？、()（）/@!！*%# ]*$")
    private String descriptionEn = null;

    @JsonProperty("url")
    @Schema(description = "服务URL", example = "https://api.weather.com")
    @Pattern(regexp = "(http|https)://[a-zA-Z0-9-.]+(:[0-9]+)?(/\\S*)?")
    private String url = null;

    @JsonProperty("type")
    @Schema(description = "服务类型", example = "local")
    private String type = null;

    @JsonProperty("org_type")
    @Schema(description = "组织类型", example = "personal")
    private String orgType = null;

    @JsonProperty("readme")
    @Schema(description = "README文档", example = "服务说明文档")
    private String readme = null;

    @JsonProperty("server_config")
    @Schema(description = "服务配置", example = "服务配置JSON")
    @Pattern(regexp = "^[\\u4e00-\\u9fa5_a-zA-Z0-9\\-,.?:;\"'：=；“”‘’//，。？、()（）\\[\\]{}/@!！*%# \\s]*$")
    private String serverConfig = null;

    @JsonProperty("tools")
    @Schema(description = "工具列表", example = "工具列表JSON")
    private String tools = null;

    @JsonProperty("view_times")
    @Schema(description = "浏览次数", example = "1024")
    private Long viewTimes = null;

    @JsonProperty("install_times")
    @Schema(description = "安装次数", example = "256")
    private Long installTimes = null;

    @JsonProperty("score")
    @Schema(description = "评分", example = "4.5")
    private Double score = null;

    @JsonProperty("score_avg")
    @Schema(description = "平均评分", example = "4.2")
    private Double scoreAvg = null;

    public String getId() {
        return id;
    }

    public McpServerDetailInfoDto setId(String id) {
        this.id = id;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServerDetailInfoDto setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getServerCode() {
        return serverCode;
    }

    public McpServerDetailInfoDto setServerCode(String serverCode) {
        this.serverCode = serverCode;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServerDetailInfoDto setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServerDetailInfoDto setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServerDetailInfoDto setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServerDetailInfoDto setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public McpServerDetailInfoDto setUrl(String url) {
        this.url = url;
        return this;
    }

    public String getType() {
        return type;
    }

    public McpServerDetailInfoDto setType(String type) {
        this.type = type;
        return this;
    }

    public String getOrgType() {
        return orgType;
    }

    public McpServerDetailInfoDto setOrgType(String orgType) {
        this.orgType = orgType;
        return this;
    }

    public String getReadme() {
        return readme;
    }

    public McpServerDetailInfoDto setReadme(String readme) {
        this.readme = readme;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServerDetailInfoDto setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getTools() {
        return tools;
    }

    public McpServerDetailInfoDto setTools(String tools) {
        this.tools = tools;
        return this;
    }

    public Long getViewTimes() {
        return viewTimes;
    }

    public McpServerDetailInfoDto setViewTimes(Long viewTimes) {
        this.viewTimes = viewTimes;
        return this;
    }

    public Long getInstallTimes() {
        return installTimes;
    }

    public McpServerDetailInfoDto setInstallTimes(Long installTimes) {
        this.installTimes = installTimes;
        return this;
    }

    public Double getScore() {
        return score;
    }

    public McpServerDetailInfoDto setScore(Double score) {
        this.score = score;
        return this;
    }

    public Double getScoreAvg() {
        return scoreAvg;
    }

    public McpServerDetailInfoDto setScoreAvg(Double scoreAvg) {
        this.scoreAvg = scoreAvg;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServerDetailInfoDto {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    serverCode: ").append(toIndentedString(serverCode)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    url: ").append(toIndentedString(url)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    orgType: ").append(toIndentedString(orgType)).append("\n");
        sb.append("    readme: ").append(toIndentedString(readme)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    tools: ").append(toIndentedString(tools)).append("\n");
        sb.append("    viewTimes: ").append(toIndentedString(viewTimes)).append("\n");
        sb.append("    installTimes: ").append(toIndentedString(installTimes)).append("\n");
        sb.append("    score: ").append(toIndentedString(score)).append("\n");
        sb.append("    scoreAvg: ").append(toIndentedString(scoreAvg)).append("\n");
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
        McpServerDetailInfoDto mcpServerDetailInfoDto = (McpServerDetailInfoDto) o;
        return Objects.equals(this.id, mcpServerDetailInfoDto.id) && Objects.equals(this.icon,
            mcpServerDetailInfoDto.icon) && Objects.equals(this.serverCode, mcpServerDetailInfoDto.serverCode)
            && Objects.equals(this.name, mcpServerDetailInfoDto.name) && Objects.equals(this.nameEn,
            mcpServerDetailInfoDto.nameEn) && Objects.equals(this.description, mcpServerDetailInfoDto.description)
            && Objects.equals(this.descriptionEn, mcpServerDetailInfoDto.descriptionEn) && Objects.equals(this.url,
            mcpServerDetailInfoDto.url) && Objects.equals(this.type, mcpServerDetailInfoDto.type) && Objects.equals(
            this.orgType, mcpServerDetailInfoDto.orgType) && Objects.equals(this.readme, mcpServerDetailInfoDto.readme)
            && Objects.equals(this.serverConfig, mcpServerDetailInfoDto.serverConfig) && Objects.equals(this.tools,
            mcpServerDetailInfoDto.tools) && Objects.equals(this.viewTimes, mcpServerDetailInfoDto.viewTimes)
            && Objects.equals(this.installTimes, mcpServerDetailInfoDto.installTimes) && Objects.equals(this.score,
            mcpServerDetailInfoDto.score) && Objects.equals(this.scoreAvg, mcpServerDetailInfoDto.scoreAvg);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, icon, serverCode, name, nameEn, description, descriptionEn, url, type, orgType, readme,
            serverConfig, tools, viewTimes, installTimes, score, scoreAvg);
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
