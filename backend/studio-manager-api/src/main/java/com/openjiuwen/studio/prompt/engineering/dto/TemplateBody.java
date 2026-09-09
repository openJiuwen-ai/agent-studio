/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 调用模型所需要的prompt信息
 */
@ApiModel(description = "调用模型所需要的prompt信息")

@Validated
public class TemplateBody implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("question")
    @Schema(description = "问题", example = "示例问题", required = true)
    @NotBlank
    @Length(max = 4000)
    private String question = null;

    @JsonProperty("model_config")
    @Schema(description = "模型配置", example = "", required = true)
    @Valid
    @NotNull
    private ModelConfig modelConfig = null;

    public String getQuestion() {
        return question;
    }

    public TemplateBody setQuestion(String question) {
        this.question = question;
        return this;
    }

    public ModelConfig getModelConfig() {
        return modelConfig;
    }

    public TemplateBody setModelConfig(ModelConfig modelConfig) {
        this.modelConfig = modelConfig;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TemplateBody {\n");
        sb.append("    question: ").append(toIndentedString(question)).append("\n");
        sb.append("    modelConfig: ").append(toIndentedString(modelConfig)).append("\n");
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
        TemplateBody templateBody = (TemplateBody) o;
        return Objects.equals(this.question, templateBody.question) && Objects.equals(this.modelConfig,
            templateBody.modelConfig);
    }

    @Override
    public int hashCode() {
        return Objects.hash(question, modelConfig);
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
