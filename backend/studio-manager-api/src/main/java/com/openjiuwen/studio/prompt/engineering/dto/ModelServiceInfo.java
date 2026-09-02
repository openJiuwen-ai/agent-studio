/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 模型信息
 */
@ApiModel(description = "模型信息")

@Validated
public class ModelServiceInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("deployment_id")
    @Schema(description = "部署ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String deploymentId = null;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    private String name = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String projectId = null;

    @JsonProperty("model_id")
    @Schema(description = "模型ID", example = "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    private String modelId = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "LLM")
    private String modelType = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "示例名称")
    private String modelName = null;

    @JsonProperty("endpoint")
    @Schema(description = "服务端点", example = "https://example.com")
    private String endpoint = null;

    @JsonProperty("enable_status")
    @Schema(description = "启用状态", example = "ENABLED")
    private String enableStatus = null;

    @JsonProperty("enable_model")
    @Schema(description = "启用模型", example = "ENABLED")
    private String enableModel = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "")
    @Valid
    private ModelMetadata metadata = null;

    @JsonProperty("is_preset")
    @Schema(description = "是否预置", example = "false")
    private Boolean isPreset = null;

    public String getDeploymentId() {
        return deploymentId;
    }

    public ModelServiceInfo setDeploymentId(String deploymentId) {
        this.deploymentId = deploymentId;
        return this;
    }

    public String getName() {
        return name;
    }

    public ModelServiceInfo setName(String name) {
        this.name = name;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ModelServiceInfo setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getModelId() {
        return modelId;
    }

    public ModelServiceInfo setModelId(String modelId) {
        this.modelId = modelId;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public ModelServiceInfo setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public ModelServiceInfo setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getEndpoint() {
        return endpoint;
    }

    public ModelServiceInfo setEndpoint(String endpoint) {
        this.endpoint = endpoint;
        return this;
    }

    public String getEnableStatus() {
        return enableStatus;
    }

    public ModelServiceInfo setEnableStatus(String enableStatus) {
        this.enableStatus = enableStatus;
        return this;
    }

    public String getEnableModel() {
        return enableModel;
    }

    public ModelServiceInfo setEnableModel(String enableModel) {
        this.enableModel = enableModel;
        return this;
    }

    public ModelMetadata getMetadata() {
        return metadata;
    }

    public ModelServiceInfo setMetadata(ModelMetadata metadata) {
        this.metadata = metadata;
        return this;
    }

    public ModelServiceInfo setIsPreset(Boolean isPreset) {
        this.isPreset = isPreset;
        return this;
    }

    public Boolean isIsPreset() {
        return isPreset;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelServiceInfo {\n");
        sb.append("    deploymentId: ").append(toIndentedString(deploymentId)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    modelId: ").append(toIndentedString(modelId)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    endpoint: ").append(toIndentedString(endpoint)).append("\n");
        sb.append("    enableStatus: ").append(toIndentedString(enableStatus)).append("\n");
        sb.append("    enableModel: ").append(toIndentedString(enableModel)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    isPreset: ").append(toIndentedString(isPreset)).append("\n");
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
        ModelServiceInfo modelServiceInfo = (ModelServiceInfo) o;
        return Objects.equals(this.deploymentId, modelServiceInfo.deploymentId) && Objects.equals(this.name,
            modelServiceInfo.name) && Objects.equals(this.projectId, modelServiceInfo.projectId) && Objects.equals(
            this.modelId, modelServiceInfo.modelId) && Objects.equals(this.modelType, modelServiceInfo.modelType)
            && Objects.equals(this.modelName, modelServiceInfo.modelName) && Objects.equals(this.endpoint,
            modelServiceInfo.endpoint) && Objects.equals(this.enableStatus, modelServiceInfo.enableStatus)
            && Objects.equals(this.enableModel, modelServiceInfo.enableModel) && Objects.equals(this.metadata,
            modelServiceInfo.metadata) && Objects.equals(this.isPreset, modelServiceInfo.isPreset);
    }

    @Override
    public int hashCode() {
        return Objects.hash(deploymentId, name, projectId, modelId, modelType, modelName, endpoint, enableStatus,
            enableModel, metadata, isPreset);
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
