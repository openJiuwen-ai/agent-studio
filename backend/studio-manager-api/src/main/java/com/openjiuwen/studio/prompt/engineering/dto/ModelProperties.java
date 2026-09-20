/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * Model
 */
@ApiModel(description = "Model")

@Validated
public class ModelProperties implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("model")
    @Schema(description = "模型名称", example = "gpt-4")
    private String model = null;

    @JsonProperty("model_source")
    @Schema(description = "模型来源", example = "示例文本")
    private String modelSource = null;

    @JsonProperty("url")
    @Schema(description = "接口地址", example = "https://example.com")
    private String url = null;

    @JsonProperty("api_key")
    @Schema(description = "API密钥", example = "sk-xxxxxxxxxxxxxxxx")
    private String apiKey = null;

    @JsonProperty("temperature")
    @Schema(description = "温度参数", example = "0.0")
    private Double temperature = null;

    @JsonProperty("top_p")
    @Schema(description = "Top-P参数", example = "1.0")
    private Double topP = null;

    public String getModel() {
        return model;
    }

    public ModelProperties setModel(String model) {
        this.model = model;
        return this;
    }

    public String getModelSource() {
        return modelSource;
    }

    public ModelProperties setModelSource(String modelSource) {
        this.modelSource = modelSource;
        return this;
    }

    public String getUrl() {
        return url;
    }

    public ModelProperties setUrl(String url) {
        this.url = url;
        return this;
    }

    public String getApiKey() {
        return apiKey;
    }

    public ModelProperties setApiKey(String apiKey) {
        this.apiKey = apiKey;
        return this;
    }

    public Double getTemperature() {
        return temperature;
    }

    public ModelProperties setTemperature(Double temperature) {
        this.temperature = temperature;
        return this;
    }

    public Double getTopP() {
        return topP;
    }

    public ModelProperties setTopP(Double topP) {
        this.topP = topP;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("ModelProperties{");
        sb.append("model=").append(model);
        sb.append(", modelSource=").append(modelSource);
        sb.append(", url=").append(url);
        sb.append(", apiKey=").append(apiKey);
        sb.append(", temperature=").append(temperature);
        sb.append(", topP=").append(topP);
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
        ModelProperties modelProperties = (ModelProperties) o;
        return Objects.equals(this.model, modelProperties.model) && Objects.equals(this.modelSource,
            modelProperties.modelSource) && Objects.equals(this.url, modelProperties.url) && Objects.equals(
            this.apiKey, modelProperties.apiKey) && Objects.equals(this.temperature, modelProperties.temperature)
            && Objects.equals(this.topP, modelProperties.topP);
    }

    @Override
    public int hashCode() {
        return Objects.hash(model, modelSource, url, apiKey, temperature, topP);
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
