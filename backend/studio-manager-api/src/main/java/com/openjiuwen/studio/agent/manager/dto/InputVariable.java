/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Pattern;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 智能体用户的入参变量定义。
 */
@ApiModel(description = "智能体用户的入参变量定义。")

@Validated

public class InputVariable implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("variable_key")
    @Schema(description = "入参变量键名", example = "user_name")
    @Pattern(regexp = "^[^\\^]*$")
    @Length(max = 100)
    private String variableKey = null;

    @JsonProperty("required")
    @Schema(description = "是否必填", example = "true")
    private Boolean required = false;

    @JsonProperty("description")
    @Schema(description = "变量描述", example = "用户名称")
    @Length(max = 200)
    private String description = null;

    @JsonProperty("default_value")
    @Schema(description = "变量默认值", example = "张三")
    @Valid
    private Object defaultValue = null;

    @JsonProperty("input_type")
    @Schema(description = "入参类型，可选值：string、integer、number、boolean", example = "string")
    @Pattern(regexp = "^(string|integer|number|boolean)$")
    @Length(max = 100)
    private String inputType = null;

    public String getVariableKey() {
        return variableKey;
    }

    public InputVariable setVariableKey(String variableKey) {
        this.variableKey = variableKey;
        return this;
    }

    public InputVariable setRequired(Boolean required) {
        this.required = required;
        return this;
    }

    public Boolean isRequired() {
        return required;
    }

    public String getDescription() {
        return description;
    }

    public InputVariable setDescription(String description) {
        this.description = description;
        return this;
    }

    public Object getDefaultValue() {
        return defaultValue;
    }

    public InputVariable setDefaultValue(Object defaultValue) {
        this.defaultValue = defaultValue;
        return this;
    }

    public String getInputType() {
        return inputType;
    }

    public InputVariable setInputType(String inputType) {
        this.inputType = inputType;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class InputVariable {\n");

        sb.append("    variableKey: ").append(toIndentedString(variableKey)).append("\n");
        sb.append("    required: ").append(toIndentedString(required)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    defaultValue: ").append(toIndentedString(defaultValue)).append("\n");
        sb.append("    inputType: ").append(toIndentedString(inputType)).append("\n");
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
        InputVariable inputVariable = (InputVariable) o;
        return Objects.equals(this.variableKey, inputVariable.variableKey) && Objects.equals(this.required,
            inputVariable.required) && Objects.equals(this.description, inputVariable.description) && Objects.equals(
            this.defaultValue, inputVariable.defaultValue) && Objects.equals(this.inputType, inputVariable.inputType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(variableKey, required, description, defaultValue, inputType);
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
