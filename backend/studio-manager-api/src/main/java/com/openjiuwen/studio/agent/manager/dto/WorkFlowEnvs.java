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
 * 工作流中的渠道变量列表。
 */
@ApiModel(description = "工作流中的渠道变量列表。")

@Validated

public class WorkFlowEnvs implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("variables")
    @Schema(description = "变量列表", example = "[]")
    @Valid
    @Size(max = 300)
    private List<WorkFlowEnv> variables = null;

    public List<WorkFlowEnv> getVariables() {
        return variables;
    }

    public WorkFlowEnvs setVariables(List<WorkFlowEnv> variables) {
        this.variables = variables;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkFlowEnvs {\n");

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
        WorkFlowEnvs workFlowEnvs = (WorkFlowEnvs) o;
        return Objects.equals(this.variables, workFlowEnvs.variables);
    }

    @Override
    public int hashCode() {
        return Objects.hash(variables);
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
