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
 * 调用模型的返回体
 */
@ApiModel(description = "调用模型的返回体")

@Validated
public class TemplateResp implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("model_template")
    @Schema(description = "模型模板", example = "示例文本")
    private String modelTemplate = null;

    public String getModelTemplate() {
        return modelTemplate;
    }

    public TemplateResp setModelTemplate(String modelTemplate) {
        this.modelTemplate = modelTemplate;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class TemplateResp {\n");
        sb.append("    modelTemplate: ").append(toIndentedString(modelTemplate)).append("\n");
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
        TemplateResp templateResp = (TemplateResp) o;
        return Objects.equals(this.modelTemplate, templateResp.modelTemplate);
    }

    @Override
    public int hashCode() {
        return Objects.hash(modelTemplate);
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
