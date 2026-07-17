/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 工作流组件详细配置信息
 */
@ApiModel(description = "工作流组件详细配置信息")

@Validated

public class WorkflowComponent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @NotBlank
    @Length(max = 64)
    private String id = null;

    @JsonProperty("name")
    @NotBlank
    @Length(max = 64)
    private String name = null;

    @JsonProperty("type")
    @NotBlank
    @Length(max = 64)
    private String type = null;

    @JsonProperty("inputs")
    @Valid
    @Size()
    private List<WorkflowConfig> inputs = null;

    @JsonProperty("outputs")
    @Valid
    @Size()
    private List<WorkflowConfig> outputs = null;

    @JsonProperty("configs")
    @Valid
    @Size()
    private List<WorkflowConfig> configs = null;

    @JsonProperty("condition")
    @Valid
    private WorkflowComponentCondition condition = null;

    public String getId() {
        return id;
    }

    public WorkflowComponent setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkflowComponent setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowComponent setType(String type) {
        this.type = type;
        return this;
    }

    public List<WorkflowConfig> getInputs() {
        return inputs;
    }

    public WorkflowComponent setInputs(List<WorkflowConfig> inputs) {
        this.inputs = inputs;
        return this;
    }

    public List<WorkflowConfig> getOutputs() {
        return outputs;
    }

    public WorkflowComponent setOutputs(List<WorkflowConfig> outputs) {
        this.outputs = outputs;
        return this;
    }

    public List<WorkflowConfig> getConfigs() {
        return configs;
    }

    public WorkflowComponent setConfigs(List<WorkflowConfig> configs) {
        this.configs = configs;
        return this;
    }

    public WorkflowComponentCondition getCondition() {
        return condition;
    }

    public WorkflowComponent setCondition(WorkflowComponentCondition condition) {
        this.condition = condition;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowComponent {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    configs: ").append(toIndentedString(configs)).append("\n");
        sb.append("    condition: ").append(toIndentedString(condition)).append("\n");
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
        WorkflowComponent workflowComponent = (WorkflowComponent) o;
        return Objects.equals(this.id, workflowComponent.id) && Objects.equals(this.name, workflowComponent.name)
            && Objects.equals(this.type, workflowComponent.type) && Objects.equals(this.inputs,
            workflowComponent.inputs) && Objects.equals(this.outputs, workflowComponent.outputs) && Objects.equals(
            this.configs, workflowComponent.configs) && Objects.equals(this.condition, workflowComponent.condition);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type, inputs, outputs, configs, condition);
    }

    private String toIndentedString(Object o) {
        if (o == null) {
            return "null";
        }
        return o.toString().replace("\n", "\n    ");
    }
}
