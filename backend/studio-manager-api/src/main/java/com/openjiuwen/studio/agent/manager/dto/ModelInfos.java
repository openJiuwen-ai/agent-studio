/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

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

public class ModelInfos implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("model")
    @Schema(description = "模型标识", example = "gpt-4")
    private String model = null;

    @JsonProperty("model_source")
    @Schema(description = "模型来源", example = "openai")
    private String modelSource = null;

    @JsonProperty("model_name")
    @Schema(description = "模型名称", example = "GPT-4")
    private String modelName = null;

    @JsonProperty("headers")
    @Schema(description = "请求头信息", example = "{\"Content-Type\":\"application/json\"}")
    @Valid
    private Object headers = null;

    public String getModel() {
        return model;
    }

    public ModelInfos setModel(String model) {
        this.model = model;
        return this;
    }

    public String getModelSource() {
        return modelSource;
    }

    public ModelInfos setModelSource(String modelSource) {
        this.modelSource = modelSource;
        return this;
    }

    public String getModelName() {
        return modelName;
    }

    public ModelInfos setModelName(String modelName) {
        this.modelName = modelName;
        return this;
    }

    public Object getHeaders() {
        return headers;
    }

    public ModelInfos setHeaders(Object headers) {
        this.headers = headers;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ModelInfos {\n");

        sb.append("    model: ").append(toIndentedString(model)).append("\n");
        sb.append("    modelSource: ").append(toIndentedString(modelSource)).append("\n");
        sb.append("    modelName: ").append(toIndentedString(modelName)).append("\n");
        sb.append("    headers: ").append(toIndentedString(headers)).append("\n");
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
        ModelInfos modelInfos = (ModelInfos) o;
        return Objects.equals(this.model, modelInfos.model) && Objects.equals(this.modelSource, modelInfos.modelSource)
            && Objects.equals(this.modelName, modelInfos.modelName) && Objects.equals(this.headers, modelInfos.headers);
    }

    @Override
    public int hashCode() {
        return Objects.hash(model, modelSource, modelName, headers);
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
