/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 节点意图配置，此字段为模型描述。
 */
@ApiModel(description = "节点意图配置，此字段为模型描述。")

@Validated

public class WorkflowNodeConfigVOIntent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("name")
    @Schema(description = "名称", example = "示例名称")
    @Length(max = 64)
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "描述", example = "示例描述")
    @Length(max = 4096)
    private String description = null;

    public String getName() {
        return name;
    }

    public WorkflowNodeConfigVOIntent setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public WorkflowNodeConfigVOIntent setDescription(String description) {
        this.description = description;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowNodeConfigVOIntent {\n");

        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
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
        WorkflowNodeConfigVOIntent workflowNodeConfigVOIntent = (WorkflowNodeConfigVOIntent) o;
        return Objects.equals(this.name, workflowNodeConfigVOIntent.name) && Objects.equals(this.description,
            workflowNodeConfigVOIntent.description);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name, description);
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
