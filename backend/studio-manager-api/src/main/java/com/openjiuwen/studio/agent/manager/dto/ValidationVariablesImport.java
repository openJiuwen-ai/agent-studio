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
import java.util.List;
import java.util.Objects;

/**
 * 环境变量
 */
@ApiModel(description = "环境变量")

@Validated

public class ValidationVariablesImport implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("result")
    @Schema(description = "结果", example = "true")
    private Boolean result = null;

    @JsonProperty("reason")
    @Schema(description = "原因", example = "原因示例")
    private String reason = null;

    @JsonProperty("variables")
    @Schema(description = "变量列表", example = "[]")
    @Valid
    @Size()
    private List<ValidationVariableImport> variables = null;

    public ValidationVariablesImport setResult(Boolean result) {
        this.result = result;
        return this;
    }

    public Boolean isResult() {
        return result;
    }

    public String getReason() {
        return reason;
    }

    public ValidationVariablesImport setReason(String reason) {
        this.reason = reason;
        return this;
    }

    public List<ValidationVariableImport> getVariables() {
        return variables;
    }

    public ValidationVariablesImport setVariables(List<ValidationVariableImport> variables) {
        this.variables = variables;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ValidationVariablesImport {\n");

        sb.append("    result: ").append(toIndentedString(result)).append("\n");
        sb.append("    reason: ").append(toIndentedString(reason)).append("\n");
        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
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
        ValidationVariablesImport validationVariablesImport = (ValidationVariablesImport) o;
        return Objects.equals(this.result, validationVariablesImport.result) && Objects.equals(this.reason,
            validationVariablesImport.reason) && Objects.equals(this.variables, validationVariablesImport.variables);
    }

    @Override
    public int hashCode() {
        return Objects.hash(result, reason, variables);
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
