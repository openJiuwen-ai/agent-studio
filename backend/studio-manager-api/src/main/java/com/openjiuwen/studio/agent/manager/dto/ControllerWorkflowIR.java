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
 * Controller下workflow数据结构。
 */
@ApiModel(description = "Controller下workflow数据结构。")

@Validated

public class ControllerWorkflowIR implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("id")
    @Schema(description = "工作流ID", example = "wf_001")
    private String id = null;

    @JsonProperty("name")
    @Schema(description = "工作流名称", example = "问答工作流")
    private String name = null;

    @JsonProperty("description")
    @Schema(description = "工作流描述", example = "用于问答场景的工作流")
    private String description = null;

    @JsonProperty("intent")
    @Schema(description = "意图配置", example = "{}")
    @Valid
    private WorkflowNodeConfigVOIntent intent = null;

    @JsonProperty("workflow_type")
    @Schema(description = "工作流类型", example = "chat")
    private String workflowType = null;

    @JsonProperty("ir_path")
    @Schema(description = "IR路径", example = "/workflow/ir_001.json")
    private String irPath = null;

    @JsonProperty("arguments")
    @Schema(description = "参数列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFieldIR> arguments = null;

    @JsonProperty("response")
    @Schema(description = "响应字段列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowFieldIR> response = null;

    @JsonProperty("action_after_completion")
    @Schema(description = "完成后的动作", example = "close")
    private String actionAfterCompletion = null;

    public String getId() {
        return id;
    }

    public ControllerWorkflowIR setId(String id) {
        this.id = id;
        return this;
    }

    public String getName() {
        return name;
    }

    public ControllerWorkflowIR setName(String name) {
        this.name = name;
        return this;
    }

    public String getDescription() {
        return description;
    }

    public ControllerWorkflowIR setDescription(String description) {
        this.description = description;
        return this;
    }

    public WorkflowNodeConfigVOIntent getIntent() {
        return intent;
    }

    public ControllerWorkflowIR setIntent(WorkflowNodeConfigVOIntent intent) {
        this.intent = intent;
        return this;
    }

    public String getWorkflowType() {
        return workflowType;
    }

    public ControllerWorkflowIR setWorkflowType(String workflowType) {
        this.workflowType = workflowType;
        return this;
    }

    public String getIrPath() {
        return irPath;
    }

    public ControllerWorkflowIR setIrPath(String irPath) {
        this.irPath = irPath;
        return this;
    }

    public List<WorkflowFieldIR> getArguments() {
        return arguments;
    }

    public ControllerWorkflowIR setArguments(List<WorkflowFieldIR> arguments) {
        this.arguments = arguments;
        return this;
    }

    public List<WorkflowFieldIR> getResponse() {
        return response;
    }

    public ControllerWorkflowIR setResponse(List<WorkflowFieldIR> response) {
        this.response = response;
        return this;
    }

    public String getActionAfterCompletion() {
        return actionAfterCompletion;
    }

    public ControllerWorkflowIR setActionAfterCompletion(String actionAfterCompletion) {
        this.actionAfterCompletion = actionAfterCompletion;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerWorkflowIR {\n");

        sb.append("    id: ").append(toIndentedString(id)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    description: ").append(toIndentedString(description)).append("\n");
        sb.append("    intent: ").append(toIndentedString(intent)).append("\n");
        sb.append("    workflowType: ").append(toIndentedString(workflowType)).append("\n");
        sb.append("    irPath: ").append(toIndentedString(irPath)).append("\n");
        sb.append("    arguments: ").append(toIndentedString(arguments)).append("\n");
        sb.append("    response: ").append(toIndentedString(response)).append("\n");
        sb.append("    actionAfterCompletion: ").append(toIndentedString(actionAfterCompletion)).append("\n");
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
        ControllerWorkflowIR controllerWorkflowIR = (ControllerWorkflowIR) o;
        return Objects.equals(this.id, controllerWorkflowIR.id) && Objects.equals(this.name, controllerWorkflowIR.name)
            && Objects.equals(this.description, controllerWorkflowIR.description) && Objects.equals(this.intent,
            controllerWorkflowIR.intent) && Objects.equals(this.workflowType, controllerWorkflowIR.workflowType)
            && Objects.equals(this.irPath, controllerWorkflowIR.irPath) && Objects.equals(this.arguments,
            controllerWorkflowIR.arguments) && Objects.equals(this.response, controllerWorkflowIR.response)
            && Objects.equals(this.actionAfterCompletion, controllerWorkflowIR.actionAfterCompletion);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, intent, workflowType, irPath, arguments, response,
            actionAfterCompletion);
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
