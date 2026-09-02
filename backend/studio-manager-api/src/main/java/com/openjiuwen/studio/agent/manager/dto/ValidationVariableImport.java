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
 * 环境变量
 */
@ApiModel(description = "环境变量")

@Validated

public class ValidationVariableImport implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("variableName")
    @Schema(description = "变量名称", example = "api_key")
    private String variableName = null;

    @JsonProperty("validateResult")
    @Schema(description = "校验结果", example = "success")
    private String validateResult = null;

    @JsonProperty("variableValue")
    @Schema(description = "变量值", example = "sk-123456")
    private String variableValue = null;

    @JsonProperty("variableType")
    @Schema(description = "变量类型", example = "string")
    private String variableType = null;

    @JsonProperty("isSecret")
    @Schema(description = "是否为密钥", example = "false")
    private Boolean isSecret = null;

    public String getVariableName() {
        return variableName;
    }

    public ValidationVariableImport setVariableName(String variableName) {
        this.variableName = variableName;
        return this;
    }

    public String getValidateResult() {
        return validateResult;
    }

    public ValidationVariableImport setValidateResult(String validateResult) {
        this.validateResult = validateResult;
        return this;
    }

    public String getVariableValue() {
        return variableValue;
    }

    public ValidationVariableImport setVariableValue(String variableValue) {
        this.variableValue = variableValue;
        return this;
    }

    public String getVariableType() {
        return variableType;
    }

    public ValidationVariableImport setVariableType(String variableType) {
        this.variableType = variableType;
        return this;
    }

    public ValidationVariableImport setIsSecret(Boolean isSecret) {
        this.isSecret = isSecret;
        return this;
    }

    public Boolean isIsSecret() {
        return isSecret;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ValidationVariableImport {\n");

        sb.append("    variableName: ").append(toIndentedString(variableName)).append("\n");
        sb.append("    validateResult: ").append(toIndentedString(validateResult)).append("\n");
        sb.append("    variableValue: ").append(toIndentedString(variableValue)).append("\n");
        sb.append("    variableType: ").append(toIndentedString(variableType)).append("\n");
        sb.append("    isSecret: ").append(toIndentedString(isSecret)).append("\n");
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
        ValidationVariableImport validationVariableImport = (ValidationVariableImport) o;
        return Objects.equals(this.variableName, validationVariableImport.variableName) && Objects.equals(
            this.validateResult, validationVariableImport.validateResult) && Objects.equals(this.variableValue,
            validationVariableImport.variableValue) && Objects.equals(this.variableType,
            validationVariableImport.variableType) && Objects.equals(this.isSecret, validationVariableImport.isSecret);
    }

    @Override
    public int hashCode() {
        return Objects.hash(variableName, validateResult, variableValue, variableType, isSecret);
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
