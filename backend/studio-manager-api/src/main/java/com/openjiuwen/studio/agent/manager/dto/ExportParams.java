/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 导出相关参数
 */
@ApiModel(description = "导出相关参数")

@Validated

public class ExportParams implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("tool_ids")
    @Schema(description = "工具ID列表", example = "[\"tool-1\",\"tool-2\"]")
    @Valid
    @Size()
    private List<@Length() String> toolIds = null;

    @JsonProperty("agent_ids")
    @Schema(description = "智能体ID列表", example = "[\"agent-1\",\"agent-2\"]")
    @Valid
    @Size()
    private List<@Length() String> agentIds = null;

    @JsonProperty("workflow_ids")
    @Schema(description = "工作流ID列表", example = "[\"wf-1\",\"wf-2\"]")
    @Valid
    @Size()
    private List<@Length() String> workflowIds = null;

    @JsonProperty("agents")
    @Schema(description = "智能体列表", example = "[]")
    @Valid
    @Size()
    private List<ExportAgent> agents = null;

    @JsonProperty("workflows")
    @Schema(description = "工作流列表", example = "[]")
    @Valid
    @Size()
    private List<ExportWorkflow> workflows = null;

    public List<String> getToolIds() {
        return toolIds;
    }

    public ExportParams setToolIds(List<String> toolIds) {
        this.toolIds = toolIds;
        return this;
    }

    public List<String> getAgentIds() {
        return agentIds;
    }

    public ExportParams setAgentIds(List<String> agentIds) {
        this.agentIds = agentIds;
        return this;
    }

    public List<String> getWorkflowIds() {
        return workflowIds;
    }

    public ExportParams setWorkflowIds(List<String> workflowIds) {
        this.workflowIds = workflowIds;
        return this;
    }

    public List<ExportAgent> getAgents() {
        return agents;
    }

    public ExportParams setAgents(List<ExportAgent> agents) {
        this.agents = agents;
        return this;
    }

    public List<ExportWorkflow> getWorkflows() {
        return workflows;
    }

    public ExportParams setWorkflows(List<ExportWorkflow> workflows) {
        this.workflows = workflows;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportParams {\n");

        sb.append("    toolIds: ").append(toIndentedString(toolIds)).append("\n");
        sb.append("    agentIds: ").append(toIndentedString(agentIds)).append("\n");
        sb.append("    workflowIds: ").append(toIndentedString(workflowIds)).append("\n");
        sb.append("    agents: ").append(toIndentedString(agents)).append("\n");
        sb.append("    workflows: ").append(toIndentedString(workflows)).append("\n");
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
        ExportParams exportParams = (ExportParams) o;
        return Objects.equals(this.toolIds, exportParams.toolIds) && Objects.equals(this.agentIds,
            exportParams.agentIds) && Objects.equals(this.workflowIds, exportParams.workflowIds) && Objects.equals(
            this.agents, exportParams.agents) && Objects.equals(this.workflows, exportParams.workflows);
    }

    @Override
    public int hashCode() {
        return Objects.hash(toolIds, agentIds, workflowIds, agents, workflows);
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
