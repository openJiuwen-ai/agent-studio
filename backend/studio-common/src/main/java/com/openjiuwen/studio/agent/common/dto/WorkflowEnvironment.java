/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * 环境信息。
 */
@ApiModel(description = "环境信息。")

@Validated

public class WorkflowEnvironment implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "环境名称", example = "production")
    private String name = null;

    @JsonProperty("variables")
    @Schema(description = "环境变量", example = "{\"key\":\"value\"}")
    @Valid
    @Size()
    private Map<@Length() String, @Length() String> variables = null;

    public String getName() {
        return name;
    }

    public WorkflowEnvironment setName(String name) {
        this.name = name;
        return this;
    }

    public Map<String, String> getVariables() {
        return variables;
    }

    public WorkflowEnvironment setVariables(Map<String, String> variables) {
        this.variables = variables;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowEnvironment {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
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
        WorkflowEnvironment workflowEnvironment = (WorkflowEnvironment) o;
        return Objects.equals(this.name, workflowEnvironment.name) && Objects.equals(this.variables,
            workflowEnvironment.variables);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, variables);
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
