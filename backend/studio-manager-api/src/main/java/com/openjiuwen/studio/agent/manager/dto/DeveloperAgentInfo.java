/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * 开发者空间agent资产信息
 */
@ApiModel(description = "开发者空间agent资产信息")

@Validated

public class DeveloperAgentInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "资产名称", example = "我的智能体")
    private String name = null;

    @JsonProperty("asset_id")
    @Schema(description = "资产ID", example = "asset_001")
    private String assetId = null;

    @JsonProperty("asset_type_name")
    @Schema(description = "资产类型名称", example = "agent")
    private String assetTypeName = null;

    @JsonProperty("asset_type_display_name")
    @Schema(description = "资产类型展示名称", example = "智能体")
    private String assetTypeDisplayName = null;

    @JsonProperty("description")
    @Schema(description = "资产描述", example = "这是一个智能助手")
    private String description = null;

    @JsonProperty("created_by")
    @Schema(description = "创建者", example = "user001")
    private String createdBy = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1717200000000")
    private Long createTime = null;

    @JsonProperty("updated_by")
    @Schema(description = "更新者", example = "user002")
    private String updatedBy = null;

    @JsonProperty("update_time")
    @Schema(description = "更新时间", example = "1717200000000")
    private Long updateTime = null;

    @JsonProperty("properties")
    @Schema(description = "扩展属性", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<String, Object> properties = null;

    public String getName() {
        return name;
    }

    public DeveloperAgentInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getAssetId() {
        return assetId;
    }

    public DeveloperAgentInfo setAssetId(String assetId) {
        this.assetId = assetId;
        return this;
    }

    public String getAssetTypeName() {
        return assetTypeName;
    }

    public DeveloperAgentInfo setAssetTypeName(String assetTypeName) {
        this.assetTypeName = assetTypeName;
        return this;
    }

    public String getAssetTypeDisplayName() {
        return assetTypeDisplayName;
    }

    public DeveloperAgentInfo setAssetTypeDisplayName(String assetTypeDisplayName) {
        this.assetTypeDisplayName = assetTypeDisplayName;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public DeveloperAgentInfo setDescription(String description) {
        this.description = description;
        return this;
    }

    public String getCreatedBy() {
        return createdBy;
    }

    public DeveloperAgentInfo setCreatedBy(String createdBy) {
        this.createdBy = createdBy;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public DeveloperAgentInfo setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public String getUpdatedBy() {
        return updatedBy;
    }

    public DeveloperAgentInfo setUpdatedBy(String updatedBy) {
        this.updatedBy = updatedBy;
        return this;
    }

    public Long getUpdateTime() {
        return updateTime;
    }

    public DeveloperAgentInfo setUpdateTime(Long updateTime) {
        this.updateTime = updateTime;
        return this;
    }

    public Map<String, Object> getProperties() {
        return properties;
    }

    public DeveloperAgentInfo setProperties(Map<String, Object> properties) {
        this.properties = properties;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class DeveloperAgentInfo {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    assetId: ").append(toIndentedString(assetId)).append("\n");
        sb.append("    assetTypeName: ").append(toIndentedString(assetTypeName)).append("\n");
        sb.append("    assetTypeDisplayName: ").append(toIndentedString(assetTypeDisplayName)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    createdBy: ").append(toIndentedString(createdBy)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    updatedBy: ").append(toIndentedString(updatedBy)).append("\n");
        sb.append("    updateTime: ").append(toIndentedString(updateTime)).append("\n");
        sb.append("    properties: ").append(toIndentedString(properties)).append("\n");
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
        DeveloperAgentInfo developerAgentInfo = (DeveloperAgentInfo) o;
        return Objects.equals(this.name, developerAgentInfo.name) && Objects.equals(this.assetId,
            developerAgentInfo.assetId) && Objects.equals(this.assetTypeName, developerAgentInfo.assetTypeName)
            && Objects.equals(this.assetTypeDisplayName, developerAgentInfo.assetTypeDisplayName) && Objects.equals(
            this.description, developerAgentInfo.description) && Objects.equals(this.createdBy,
            developerAgentInfo.createdBy) && Objects.equals(this.createTime, developerAgentInfo.createTime)
            && Objects.equals(this.updatedBy, developerAgentInfo.updatedBy) && Objects.equals(this.updateTime,
            developerAgentInfo.updateTime) && Objects.equals(this.properties, developerAgentInfo.properties);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, assetId, assetTypeName, assetTypeDisplayName, description, createdBy, createTime,
            updatedBy, updateTime, properties);
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
