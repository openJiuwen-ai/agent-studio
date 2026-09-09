/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * agentBuilder模型参数配置信息
 */
@ApiModel(description = "agentBuilder模型参数配置信息")

@Validated
public class ModelConfig implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("user")
    @Schema(description = "用户标识", example = "user-001")
    @Length(max = 255)
    private String user = null;

    @JsonProperty("temperature")
    @Schema(description = "温度参数，控制生成随机性，取值范围0-1", example = "0.7")
    @DecimalMin(value = "0")
    @DecimalMax(value = "1")
    private Double temperature = null;

    @JsonProperty("top_p")
    @Schema(description = "Top-P采样参数，取值范围0-1", example = "0.9")
    @DecimalMin(value = "0")
    @DecimalMax(value = "1")
    private Double topP = null;

    @JsonProperty("max_tokens")
    @Schema(description = "最大生成token数", example = "2048")
    @Range(min = 1L, max = 2147483647L)
    private Integer maxTokens = null;

    @JsonProperty("token")
    @Schema(description = "认证令牌", example = "sk-xxxx")
    private String token = null;

    @JsonProperty("presence_penalty")
    @Schema(description = "存在惩罚参数，取值范围-2到2", example = "0")
    @DecimalMin(value = "-2")
    @DecimalMax(value = "2")
    private Double presencePenalty = null;

    @JsonProperty("n")
    @Schema(description = "生成数量，取值范围1-2", example = "1")
    @Range(min = 1L, max = 2L)
    private Integer n = null;

    @JsonProperty("endpoint")
    @Schema(description = "模型服务端点地址", example = "https://api.example.com/v1")
    @Pattern(regexp = "^(https?://)([\\\\w.-]+)(:[0-9]{1,5})?(/.*)?$")
    @Length(max = 1000)
    private String endpoint = null;

    @JsonProperty("project_id")
    @Schema(description = "项目ID", example = "proj-001")
    @NotBlank
    private String projectId = null;

    @JsonProperty("deployment_id")
    @Schema(description = "部署ID", example = "deploy-001")
    @NotBlank
    private String deploymentId = null;

    @JsonProperty("model_id")
    @Schema(description = "模型ID（UUID格式）", example = "550e8400-e29b-41d4-a716-446655440000")
    @Pattern(regexp = "(^$)|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    private String modelId = null;

    @JsonProperty("model_source")
    @Schema(description = "模型来源", example = "maas")
    private String modelSource = null;

    @JsonProperty("id")
    @Schema(description = "标识ID", example = "config-001")
    private String id = null;

    public String getUser() {
        return user;
    }

    public ModelConfig setUser(String user) {
        this.user = user;
        return this;
    }

    public Double getTemperature() {
        return temperature;
    }

    public ModelConfig setTemperature(Double temperature) {
        this.temperature = temperature;
        return this;
    }

    public Double getTopP() {
        return topP;
    }

    public ModelConfig setTopP(Double topP) {
        this.topP = topP;
        return this;
    }

    public Integer getMaxTokens() {
        return maxTokens;
    }

    public ModelConfig setMaxTokens(Integer maxTokens) {
        this.maxTokens = maxTokens;
        return this;
    }

    public String getToken() {
        return token;
    }

    public ModelConfig setToken(String token) {
        this.token = token;
        return this;
    }

    public Double getPresencePenalty() {
        return presencePenalty;
    }

    public ModelConfig setPresencePenalty(Double presencePenalty) {
        this.presencePenalty = presencePenalty;
        return this;
    }

    public Integer getN() {
        return n;
    }

    public ModelConfig setN(Integer n) {
        this.n = n;
        return this;
    }

    public String getEndpoint() {
        return endpoint;
    }

    public ModelConfig setEndpoint(String endpoint) {
        this.endpoint = endpoint;
        return this;
    }

    public String getProjectId() {
        return projectId;
    }

    public ModelConfig setProjectId(String projectId) {
        this.projectId = projectId;
        return this;
    }

    public String getDeploymentId() {
        return deploymentId;
    }

    public ModelConfig setDeploymentId(String deploymentId) {
        this.deploymentId = deploymentId;
        return this;
    }

    public String getModelId() {
        return modelId;
    }

    public ModelConfig setModelId(String modelId) {
        this.modelId = modelId;
        return this;
    }

    public String getModelSource() {
        return modelSource;
    }

    public ModelConfig setModelSource(String modelSource) {
        this.modelSource = modelSource;
        return this;
    }

    public String getId() {
        return id;
    }

    public ModelConfig setId(String id) {
        this.id = id;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelConfig {\n");
        sb.append("    user: ").append(toIndentedString(user)).append("\n");
        sb.append("    temperature: ").append(toIndentedString(temperature)).append("\n");
        sb.append("    topP: ").append(toIndentedString(topP)).append("\n");
        sb.append("    maxTokens: ").append(toIndentedString(maxTokens)).append("\n");
        sb.append("    token: ").append(toIndentedString(token)).append("\n");
        sb.append("    presencePenalty: ").append(toIndentedString(presencePenalty)).append("\n");
        sb.append("    n: ").append(toIndentedString(n)).append("\n");
        sb.append("    endpoint: ").append(toIndentedString(endpoint)).append("\n");
        sb.append("    projectId: ").append(toIndentedString(projectId)).append("\n");
        sb.append("    deploymentId: ").append(toIndentedString(deploymentId)).append("\n");
        sb.append("    modelId: ").append(toIndentedString(modelId)).append("\n");
        sb.append("    modelSource: ").append(toIndentedString(modelSource)).append("\n");
        sb.append("    id: ").append(toIndentedString(id)).append("\n");
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
        ModelConfig modelConfig = (ModelConfig) o;
        return Objects.equals(this.user, modelConfig.user) && Objects.equals(this.temperature, modelConfig.temperature)
            && Objects.equals(this.topP, modelConfig.topP) && Objects.equals(this.maxTokens, modelConfig.maxTokens)
            && Objects.equals(this.token, modelConfig.token) && Objects.equals(this.presencePenalty,
            modelConfig.presencePenalty) && Objects.equals(this.n, modelConfig.n) && Objects.equals(this.endpoint,
            modelConfig.endpoint) && Objects.equals(this.projectId, modelConfig.projectId) && Objects.equals(
            this.deploymentId, modelConfig.deploymentId) && Objects.equals(this.modelId, modelConfig.modelId)
            && Objects.equals(this.modelSource, modelConfig.modelSource) && Objects.equals(this.id, modelConfig.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(user, temperature, topP, maxTokens, token, presencePenalty, n, endpoint, projectId,
            deploymentId, modelId, modelSource, id);
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
