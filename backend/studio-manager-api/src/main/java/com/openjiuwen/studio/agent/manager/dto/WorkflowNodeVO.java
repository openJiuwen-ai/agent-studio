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
import java.util.Map;
import java.util.Objects;

/**
 * 工作流节点定义。
 */
@ApiModel(description = "工作流节点定义。")
@Validated
public class WorkflowNodeVO implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "节点ID", example = "node_001", required = true)
    @NotBlank
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "节点名称", example = "开始节点", required = true)
    @NotBlank
    private String name = null;

    @JsonProperty("type")
    @Schema(description = "节点类型", example = "start", required = true)
    @NotBlank
    private String type = null;

    @JsonProperty("inputs")
    @Schema(description = "输入字段列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFieldVO> inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出字段列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFieldVO> outputs = null;

    @JsonProperty("configs")
    @Schema(description = "节点配置", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> configs = null;

    @JsonProperty("branches")
    @Schema(description = "分支列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowBranchVO> branches = null;

    public String getId() {
        return id;
    }

    public WorkflowNodeVO setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public WorkflowNodeVO setName(String name) {
        this.name = name;
        return this;
    }

    public String getType() {
        return type;
    }

    public WorkflowNodeVO setType(String type) {
        this.type = type;
        return this;
    }

    public List<WorkflowFieldVO> getInputs() {
        return inputs;
    }

    public WorkflowNodeVO setInputs(List<WorkflowFieldVO> inputs) {
        this.inputs = inputs;
        return this;
    }

    public List<WorkflowFieldVO> getOutputs() {
        return outputs;
    }

    public WorkflowNodeVO setOutputs(List<WorkflowFieldVO> outputs) {
        this.outputs = outputs;
        return this;
    }

    public Map<String, Object> getConfigs() {
        return configs;
    }

    public WorkflowNodeVO setConfigs(Map<String, Object> configs) {
        this.configs = configs;
        return this;
    }

    public List<WorkflowBranchVO> getBranches() {
        return branches;
    }

    public WorkflowNodeVO setBranches(List<WorkflowBranchVO> branches) {
        this.branches = branches;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowNodeVO {\n");

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
        WorkflowNodeVO workflowNodeVO = (WorkflowNodeVO) o;
        return Objects.equals(this.id, workflowNodeVO.id) && Objects.equals(this.name, workflowNodeVO.name)
            && Objects.equals(this.type, workflowNodeVO.type) && Objects.equals(this.inputs, workflowNodeVO.inputs)
            && Objects.equals(this.outputs, workflowNodeVO.outputs) && Objects.equals(this.configs,
            workflowNodeVO.configs) && Objects.equals(this.branches, workflowNodeVO.branches);
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
