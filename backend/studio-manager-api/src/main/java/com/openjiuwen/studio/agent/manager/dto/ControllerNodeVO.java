/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 工作流节点定义。
 */
@ApiModel(description = "工作流节点定义。")

@Validated

public class ControllerNodeVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "节点唯一标识", example = "node_001", required = true)
    @NotBlank
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "节点名称", example = "LLM节点", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "节点类型", example = "llm", required = true)
    @NotBlank
    private String type = null;

    @JsonProperty("inputs")
    @Schema(description = "输入字段列表", example = "[{\"name\":\"question\",\"type\":\"string\"}]")
    @Valid
    @Size()
    private List<WorkflowFieldVO> inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出字段列表", example = "[{\"name\":\"answer\",\"type\":\"string\"}]")
    @Valid
    @Size()
    private List<WorkflowFieldVO> outputs = null;

    @JsonProperty("configs")
    @Schema(description = "节点配置对象", example = "{\"model\":\"gpt-4\",\"temperature\":0.7}")
    @Valid
    private Object configs = null;

    @JsonProperty("branches")
    @Schema(description = "分支列表", example = "[{\"condition\":\"x>0\",\"target\":\"node_002\"}]")
    @Valid
    @Size()
    private List<WorkflowBranchVO> branches = null;

    public String getId() {
        return id;
    }

    public ControllerNodeVO setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerNodeVO setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public ControllerNodeVO setType(String type) {
        this.type = type;
        return this;
    }

    public List<WorkflowFieldVO> getInputs() {
        return inputs;
    }

    public ControllerNodeVO setInputs(List<WorkflowFieldVO> inputs) {
        this.inputs = inputs;
        return this;
    }

    public List<WorkflowFieldVO> getOutputs() {
        return outputs;
    }

    public ControllerNodeVO setOutputs(List<WorkflowFieldVO> outputs) {
        this.outputs = outputs;
        return this;
    }

    public Object getConfigs() {
        return configs;
    }

    public ControllerNodeVO setConfigs(Object configs) {
        this.configs = configs;
        return this;
    }

    public List<WorkflowBranchVO> getBranches() {
        return branches;
    }

    public ControllerNodeVO setBranches(List<WorkflowBranchVO> branches) {
        this.branches = branches;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerNodeVO {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    type: ").append(toIndentedString(type)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    configs: ").append(toIndentedString(configs)).append("\n");
        sb.append("    branches: ").append(toIndentedString(branches)).append("\n");
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
        ControllerNodeVO controllerNodeVO = (ControllerNodeVO) o;
        return Objects.equals(this.id, controllerNodeVO.id) && Objects.equals(this.name, controllerNodeVO.name)
            && Objects.equals(this.type, controllerNodeVO.type) && Objects.equals(this.inputs, controllerNodeVO.inputs)
            && Objects.equals(this.outputs, controllerNodeVO.outputs) && Objects.equals(this.configs,
            controllerNodeVO.configs) && Objects.equals(this.branches, controllerNodeVO.branches);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, type, inputs, outputs, configs, branches);
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
