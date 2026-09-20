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
 * Controller下agent数据结构。
 */
@ApiModel(description = "Controller下agent数据结构。")

@Validated

public class ControllerAgentIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "Agent唯一标识", example = "agent_001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "Agent名称", example = "my_agent")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "Agent描述信息", example = "这是一个智能助手Agent")
    private String description = null;

    @JsonProperty("intent")
    @Schema(description = "意图配置对象", example = "{\"type\":\"chat\"}")
    @Valid
    private WorkflowNodeConfigVOIntent intent = null;

    @JsonProperty("ir_path")
    @Schema(description = "IR文件路径", example = "/agents/agent_001/ir.json")
    private String irPath = null;

    @JsonProperty("arguments")
    @Schema(description = "输入参数列表", example = "[{\"name\":\"input1\",\"type\":\"string\"}]")
    @Valid
    @Size()
    private List<WorkflowFieldIR> arguments = null;

    @JsonProperty("response")
    @Schema(description = "输出响应列表", example = "[{\"name\":\"output1\",\"type\":\"string\"}]")
    @Valid
    @Size()
    private List<WorkflowFieldIR> response = null;

    @JsonProperty("mode")
    @Schema(description = "运行模式", example = "auto")
    private String mode = null;

    public String getId() {
        return id;
    }

    public ControllerAgentIR setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerAgentIR setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerAgentIR setDescription(String description) {
        this.description = description;
        return this;
    }

    public WorkflowNodeConfigVOIntent getIntent() {
        return intent;
    }

    public ControllerAgentIR setIntent(WorkflowNodeConfigVOIntent intent) {
        this.intent = intent;
        return this;
    }

    public String getIrPath() {
        return irPath;
    }

    public ControllerAgentIR setIrPath(String irPath) {
        this.irPath = irPath;
        return this;
    }

    public List<WorkflowFieldIR> getArguments() {
        return arguments;
    }

    public ControllerAgentIR setArguments(List<WorkflowFieldIR> arguments) {
        this.arguments = arguments;
        return this;
    }

    public List<WorkflowFieldIR> getResponse() {
        return response;
    }

    public ControllerAgentIR setResponse(List<WorkflowFieldIR> response) {
        this.response = response;
        return this;
    }

    public String getMode() {
        return mode;
    }

    public ControllerAgentIR setMode(String mode) {
        this.mode = mode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerAgentIR {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    intent: ").append(toIndentedString(intent)).append("\n");
        sb.append("    irPath: ").append(toIndentedString(irPath)).append("\n");
        sb.append("    arguments: ").append(toIndentedString(arguments)).append("\n");
        sb.append("    response: ").append(toIndentedString(response)).append("\n");
        sb.append("    mode: ").append(toIndentedString(mode)).append("\n");
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
        ControllerAgentIR controllerAgentIR = (ControllerAgentIR) o;
        return Objects.equals(this.id, controllerAgentIR.id) && Objects.equals(this.name, controllerAgentIR.name)
            && Objects.equals(this.description, controllerAgentIR.description) && Objects.equals(this.intent,
            controllerAgentIR.intent) && Objects.equals(this.irPath, controllerAgentIR.irPath) && Objects.equals(
            this.arguments, controllerAgentIR.arguments) && Objects.equals(this.response, controllerAgentIR.response)
            && Objects.equals(this.mode, controllerAgentIR.mode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, intent, irPath, arguments, response, mode);
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
