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
 * 环境变量列表
 */
@ApiModel(description = "环境变量列表")

@Validated

public class EnvironmentVariablesResp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("variables")
    @Schema(description = "变量列表", example = "[]")
    @Valid
    @Size()
    private List<EnvironmentVariableResp> variables = null;

    @JsonProperty("total")
    @Schema(description = "总数", example = "100")
    private Integer total = null;

    public List<EnvironmentVariableResp> getVariables() {
        return variables;
    }

    public EnvironmentVariablesResp setVariables(List<EnvironmentVariableResp> variables) {
        this.variables = variables;
        return this;
    }

    public Integer getTotal() {
        return total;
    }

    public EnvironmentVariablesResp setTotal(Integer total) {
        this.total = total;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class EnvironmentVariablesResp {\n");

        sb.append("    variables: ").append(toIndentedString(variables)).append("\n");
        sb.append("    total: ").append(toIndentedString(total)).append("\n");
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
        EnvironmentVariablesResp environmentVariablesResp = (EnvironmentVariablesResp) o;
        return Objects.equals(this.variables, environmentVariablesResp.variables) && Objects.equals(this.total,
            environmentVariablesResp.total);
    }

    @Override
    public int hashCode() {
        return Objects.hash(variables, total);
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
