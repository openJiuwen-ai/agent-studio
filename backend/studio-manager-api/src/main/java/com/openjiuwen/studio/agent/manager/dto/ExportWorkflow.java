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
 * ExportWorkflow
 */

@Validated

public class ExportWorkflow implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "example-id-123")
    private String workflowId = null;

    @JsonProperty("workflow_version")
    @Schema(description = "工作流版本", example = "1.0.0")
    private String workflowVersion = null;

    public String getWorkflowId() {
        return workflowId;
    }

    public ExportWorkflow setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowVersion() {
        return workflowVersion;
    }

    public ExportWorkflow setWorkflowVersion(String workflowVersion) {
        this.workflowVersion = workflowVersion;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ExportWorkflow {\n");

        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    workflowVersion: ").append(toIndentedString(workflowVersion)).append("\n");
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
        ExportWorkflow exportWorkflow = (ExportWorkflow) o;
        return Objects.equals(this.workflowId, exportWorkflow.workflowId) && Objects.equals(this.workflowVersion,
            exportWorkflow.workflowVersion);
    }

    @Override
    public int hashCode() {
        return Objects.hash(workflowId, workflowVersion);
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
