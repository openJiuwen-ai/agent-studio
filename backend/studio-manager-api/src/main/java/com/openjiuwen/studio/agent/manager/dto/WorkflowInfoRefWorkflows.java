/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * WorkflowInfoRefWorkflows
 */

@Validated

public class WorkflowInfoRefWorkflows implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "example-id-123")
    private String workflowId = null;

    @JsonProperty("last_version_id")
    @Schema(description = "版本号", example = "example-id-123")
    private String lastVersionId = null;

    @JsonProperty("last_version_name")
    @Schema(description = "版本号", example = "示例名称")
    private String lastVersionName = null;

    public String getWorkflowId() {
        return workflowId;
    }

    public WorkflowInfoRefWorkflows setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getLastVersionId() {
        return lastVersionId;
    }

    public WorkflowInfoRefWorkflows setLastVersionId(String lastVersionId) {
        this.lastVersionId = lastVersionId;
        return this;
    }

    public String getLastVersionName() {
        return lastVersionName;
    }

    public WorkflowInfoRefWorkflows setLastVersionName(String lastVersionName) {
        this.lastVersionName = lastVersionName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowInfoRefWorkflows {\n");

        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    lastVersionId: ").append(toIndentedString(lastVersionId)).append("\n");
        sb.append("    lastVersionName: ").append(toIndentedString(lastVersionName)).append("\n");
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
        WorkflowInfoRefWorkflows workflowInfoRefWorkflows = (WorkflowInfoRefWorkflows) o;
        return Objects.equals(this.workflowId, workflowInfoRefWorkflows.workflowId) && Objects.equals(
            this.lastVersionId, workflowInfoRefWorkflows.lastVersionId) && Objects.equals(this.lastVersionName,
            workflowInfoRefWorkflows.lastVersionName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workflowId, lastVersionId, lastVersionName);
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
