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

public class McpServiceSkinnyEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "服务ID", example = "mcp-server-001")
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "服务名称", example = "天气服务")
    private String name = null;

    @JsonProperty("name_en")
    @Schema(description = "服务英文名称", example = "Weather Service")
    private String nameEn = null;

    @JsonProperty("description")
    @Schema(description = "服务描述", example = "提供天气查询功能")
    private String description = null;

    @JsonProperty("description_en")
    @Schema(description = "服务英文描述", example = "Provide weather query functionality")
    private String descriptionEn = null;

    @JsonProperty("fcInstanceUrl")
    @Schema(description = "FC实例URL", example = "https://fc.example.com/instance")
    private String fcInstanceUrl = null;

    @JsonProperty("fcRegion")
    @Schema(description = "FC区域", example = "cn-north-4")
    private String fcRegion = null;

    @JsonProperty("icon")
    @Schema(description = "图标", example = "icon-server")
    private String icon = null;

    @JsonProperty("deployType")
    @Schema(description = "部署类型", example = "cloud")
    private String deployType = null;

    @JsonProperty("serverConfig")
    @Schema(description = "服务配置", example = "服务配置JSON")
    private String serverConfig = null;

    @JsonProperty("fcInstanceStatus")
    @Schema(description = "FC实例状态", example = "running")
    private String fcInstanceStatus = null;

    @JsonProperty("createdByUserId")
    @Schema(description = "创建者用户ID", example = "user001")
    private String createdByUserId = null;

    @JsonProperty("tenant_id")
    @Schema(description = "租户ID", example = "tenant001")
    private String tenantId = null;

    @JsonProperty("last_updated_by_user_id")
    @Schema(description = "最后更新者用户ID", example = "user002")
    private String lastUpdatedByUserId = null;

    @JsonProperty("deleted")
    @Schema(description = "是否已删除", example = "false")
    private Boolean deleted = false;

    @JsonProperty("created_date")
    @Schema(description = "创建时间", example = "1704067200000")
    private Long createdDate = null;

    @JsonProperty("last_updated_date")
    @Schema(description = "最后更新时间", example = "1704067200000")
    private Long lastUpdatedDate = null;

    @JsonProperty("dept_code")
    @Schema(description = "部门编码", example = "dept001")
    private String deptCode = null;

    public String getId() {
        return id;
    }

    public McpServiceSkinnyEntity setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public McpServiceSkinnyEntity setName(String name) {
        this.name = name;
        return this;
    }

    public String getNameEn() {
        return nameEn;
    }

    public McpServiceSkinnyEntity setNameEn(String nameEn) {
        this.nameEn = nameEn;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public McpServiceSkinnyEntity setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getDescriptionEn() {
        return descriptionEn;
    }

    public McpServiceSkinnyEntity setDescriptionEn(String descriptionEn) {
        this.descriptionEn = descriptionEn;
        return this;
    }

    public String getFcInstanceUrl() {
        return fcInstanceUrl;
    }

    public McpServiceSkinnyEntity setFcInstanceUrl(String fcInstanceUrl) {
        this.fcInstanceUrl = fcInstanceUrl;
        return this;
    }

    public String getFcRegion() {
        return fcRegion;
    }

    public McpServiceSkinnyEntity setFcRegion(String fcRegion) {
        this.fcRegion = fcRegion;
        return this;
    }

    public String getIcon() {
        return icon;
    }

    public McpServiceSkinnyEntity setIcon(String icon) {
        this.icon = icon;
        return this;
    }

    public String getDeployType() {
        return deployType;
    }

    public McpServiceSkinnyEntity setDeployType(String deployType) {
        this.deployType = deployType;
        return this;
    }

    public String getServerConfig() {
        return serverConfig;
    }

    public McpServiceSkinnyEntity setServerConfig(String serverConfig) {
        this.serverConfig = serverConfig;
        return this;
    }

    public String getFcInstanceStatus() {
        return fcInstanceStatus;
    }

    public McpServiceSkinnyEntity setFcInstanceStatus(String fcInstanceStatus) {
        this.fcInstanceStatus = fcInstanceStatus;
        return this;
    }

    public String getCreatedByUserId() {
        return createdByUserId;
    }

    public McpServiceSkinnyEntity setCreatedByUserId(String createdByUserId) {
        this.createdByUserId = createdByUserId;
        return this;
    }

    public String getTenantId() {
        return tenantId;
    }

    public McpServiceSkinnyEntity setTenantId(String tenantId) {
        this.tenantId = tenantId;
        return this;
    }

    public String getLastUpdatedByUserId() {
        return lastUpdatedByUserId;
    }

    public McpServiceSkinnyEntity setLastUpdatedByUserId(String lastUpdatedByUserId) {
        this.lastUpdatedByUserId = lastUpdatedByUserId;
        return this;
    }

    public McpServiceSkinnyEntity setDeleted(Boolean deleted) {
        this.deleted = deleted;
        return this;
    }

    public Boolean isDeleted() {
        return deleted;
    }

    public Long getCreatedDate() {
        return createdDate;
    }

    public McpServiceSkinnyEntity setCreatedDate(Long createdDate) {
        this.createdDate = createdDate;
        return this;
    }

    public Long getLastUpdatedDate() {
        return lastUpdatedDate;
    }

    public McpServiceSkinnyEntity setLastUpdatedDate(Long lastUpdatedDate) {
        this.lastUpdatedDate = lastUpdatedDate;
        return this;
    }

    public String getDeptCode() {
        return deptCode;
    }

    public McpServiceSkinnyEntity setDeptCode(String deptCode) {
        this.deptCode = deptCode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class McpServiceSkinnyEntity {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    nameEn: ").append(toIndentedString(nameEn)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    descriptionEn: ").append(toIndentedString(descriptionEn)).append("\n");
        sb.append("    fcInstanceUrl: ").append(toIndentedString(fcInstanceUrl)).append("\n");
        sb.append("    fcRegion: ").append(toIndentedString(fcRegion)).append("\n");
        sb.append("    icon: ").append(toIndentedString(icon)).append("\n");
        sb.append("    deployType: ").append(toIndentedString(deployType)).append("\n");
        sb.append("    serverConfig: ").append(toIndentedString(serverConfig)).append("\n");
        sb.append("    fcInstanceStatus: ").append(toIndentedString(fcInstanceStatus)).append("\n");
        sb.append("    createdByUserId: ").append(toIndentedString(createdByUserId)).append("\n");
        sb.append("    tenantId: ").append(toIndentedString(tenantId)).append("\n");
        sb.append("    lastUpdatedByUserId: ").append(toIndentedString(lastUpdatedByUserId)).append("\n");
        sb.append("    deleted: ").append(toIndentedString(deleted)).append("\n");
        sb.append("    createdDate: ").append(toIndentedString(createdDate)).append("\n");
        sb.append("    lastUpdatedDate: ").append(toIndentedString(lastUpdatedDate)).append("\n");
        sb.append("    deptCode: ").append(toIndentedString(deptCode)).append("\n");
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
        McpServiceSkinnyEntity mcpServiceSkinnyEntity = (McpServiceSkinnyEntity) o;
        return Objects.equals(this.id, mcpServiceSkinnyEntity.id) && Objects.equals(this.name,
            mcpServiceSkinnyEntity.name) && Objects.equals(this.nameEn, mcpServiceSkinnyEntity.nameEn)
            && Objects.equals(this.description, mcpServiceSkinnyEntity.description) && Objects.equals(
            this.descriptionEn, mcpServiceSkinnyEntity.descriptionEn) && Objects.equals(this.fcInstanceUrl,
            mcpServiceSkinnyEntity.fcInstanceUrl) && Objects.equals(this.fcRegion, mcpServiceSkinnyEntity.fcRegion)
            && Objects.equals(this.icon, mcpServiceSkinnyEntity.icon) && Objects.equals(this.deployType,
            mcpServiceSkinnyEntity.deployType) && Objects.equals(this.serverConfig, mcpServiceSkinnyEntity.serverConfig)
            && Objects.equals(this.fcInstanceStatus, mcpServiceSkinnyEntity.fcInstanceStatus) && Objects.equals(
            this.createdByUserId, mcpServiceSkinnyEntity.createdByUserId) && Objects.equals(this.tenantId,
            mcpServiceSkinnyEntity.tenantId) && Objects.equals(this.lastUpdatedByUserId,
            mcpServiceSkinnyEntity.lastUpdatedByUserId) && Objects.equals(this.deleted, mcpServiceSkinnyEntity.deleted)
            && Objects.equals(this.createdDate, mcpServiceSkinnyEntity.createdDate) && Objects.equals(
            this.lastUpdatedDate, mcpServiceSkinnyEntity.lastUpdatedDate) && Objects.equals(this.deptCode,
            mcpServiceSkinnyEntity.deptCode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, nameEn, description, descriptionEn, fcInstanceUrl, fcRegion, icon, deployType,
            serverConfig, fcInstanceStatus, createdByUserId, tenantId, lastUpdatedByUserId, deleted, createdDate,
            lastUpdatedDate, deptCode);
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
