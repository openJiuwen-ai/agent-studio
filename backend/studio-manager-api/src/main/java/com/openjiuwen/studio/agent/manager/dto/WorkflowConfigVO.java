/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流节点扩展字段。
 */
@ApiModel(description = "工作流节点扩展字段。")

@Validated

public class WorkflowConfigVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("value")
    @Schema(description = "值", example = "{}")
    @Valid
    private Object value = null;

    public String getName() {
        return name;
    }

    public WorkflowConfigVO setName(String name) {
        this.name = name;
        return this;
    }

    public Object getValue() {
        return value;
    }

    public WorkflowConfigVO setValue(Object value) {
        this.value = value;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowConfigVO {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    value: ").append(toIndentedString(value)).append("\n");
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
        WorkflowConfigVO workflowConfigVO = (WorkflowConfigVO) o;
        return Objects.equals(this.name, workflowConfigVO.name) && Objects.equals(this.value, workflowConfigVO.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, value);
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
