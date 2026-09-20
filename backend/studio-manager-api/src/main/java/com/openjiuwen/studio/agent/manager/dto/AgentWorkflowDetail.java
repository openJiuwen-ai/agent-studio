/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流详情。
 */
@ApiModel(description = "工作流详情。")

@Validated

public class AgentWorkflowDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "wf_001")
    private String workflowId = null;

    @JsonProperty("workflow_version")
    @Schema(description = "工作流版本", example = "v1.0.0")
    private String workflowVersion = null;

    @JsonProperty("workflow_param")
    @Schema(description = "工作流参数", example = "{\"key\":\"value\"}")
    private String workflowParam = null;

    public String getWorkflowId() {
        return workflowId;
    }

    public AgentWorkflowDetail setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowVersion() {
        return workflowVersion;
    }

    public AgentWorkflowDetail setWorkflowVersion(String workflowVersion) {
        this.workflowVersion = workflowVersion;
        return this;
    }

    public String getWorkflowParam() {
        return workflowParam;
    }

    public AgentWorkflowDetail setWorkflowParam(String workflowParam) {
        this.workflowParam = workflowParam;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentWorkflowDetail {\n");

        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    workflowVersion: ").append(toIndentedString(workflowVersion)).append("\n");
        sb.append("    workflowParam: ").append(toIndentedString(workflowParam)).append("\n");
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
        AgentWorkflowDetail agentWorkflowDetail = (AgentWorkflowDetail) o;
        return Objects.equals(this.workflowId, agentWorkflowDetail.workflowId) && Objects.equals(this.workflowVersion,
            agentWorkflowDetail.workflowVersion) && Objects.equals(this.workflowParam,
            agentWorkflowDetail.workflowParam);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workflowId, workflowVersion, workflowParam);
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
