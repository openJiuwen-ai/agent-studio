/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 模型相关配置。
 */
@ApiModel(description = "模型相关配置。")

@Validated

public class ModelConfigVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("model_deployment_id")
    @Schema(description = "模型部署ID", example = "example-id-123")
    private String modelDeploymentId = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "示例名称")
    private String modelName = null;

    @JsonProperty("model_type")
    @Schema(description = "模型类型", example = "example-type")
    private String modelType = null;

    public String getModelDeploymentId() {
        return modelDeploymentId;
    }

    public ModelConfigVO setModelDeploymentId(String modelDeploymentId) {
        this.modelDeploymentId = modelDeploymentId;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public ModelConfigVO setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public String getModelType() {
        return modelType;
    }

    public ModelConfigVO setModelType(String modelType) {
        this.modelType = modelType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelConfigVO {\n");

        sb.append("    modelDeploymentId: ").append(toIndentedString(modelDeploymentId)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    modelType: ").append(toIndentedString(modelType)).append("\n");
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
        ModelConfigVO modelConfigVO = (ModelConfigVO) o;
        return Objects.equals(this.modelDeploymentId, modelConfigVO.modelDeploymentId) && Objects.equals(this.modelName,
            modelConfigVO.modelName) && Objects.equals(this.modelType, modelConfigVO.modelType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(modelDeploymentId, modelName, modelType);
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
