/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.openjiuwen.studio.agent.common.dto.agent.Status;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Map;
import java.util.Objects;

/**
 * WorkflowRunInfo
 */
@Validated

public class WorkflowRunInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("parent_workflow_id")
    @Length(max = 32)
    private String parentWorkflowId = null;

    @JsonProperty("status")
    @Valid
    private Status status = null;

    @JsonProperty("error_code")
    @Length(max = 256)
    private String errorCode = null;

    @JsonProperty("error_message")
    @Length(max = 4096)
    private String errorMessage = null;

    @JsonProperty("outputs")
    @Valid
    @Size()
    private Map<String, Object> outputs = null;

    @JsonProperty("metadata")
    @Valid
    @Size()
    private Map<String, Object> metadata = null;

    @JsonProperty("start_time")
    private Long startTime = null;

    @JsonProperty("end_time")
    private Long endTime = null;

    @JsonProperty("execution_id")
    @Length(max = 256)
    private String executionId = null;

    public String getParentWorkflowId() {
        return parentWorkflowId;
    }

    public WorkflowRunInfo setParentWorkflowId(String parentWorkflowId) {
        this.parentWorkflowId = parentWorkflowId;
        return this;
    }

    public Status getStatus() {
        return status;
    }

    public WorkflowRunInfo setStatus(Status status) {
        this.status = status;
        return this;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public WorkflowRunInfo setErrorCode(String errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public WorkflowRunInfo setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
        return this;
    }

    public Map<String, Object> getOutputs() {
        return outputs;
    }

    public WorkflowRunInfo setOutputs(Map<String, Object> outputs) {
        this.outputs = outputs;
        return this;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public WorkflowRunInfo setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public WorkflowRunInfo setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public WorkflowRunInfo setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public String getExecutionId() {
        return executionId;
    }

    public WorkflowRunInfo setExecutionId(String executionId) {
        this.executionId = executionId;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowRunInfo {\n");

        sb.append("    parentWorkflowId: ").append(toIndentedString(parentWorkflowId)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    errorCode: ").append(toIndentedString(errorCode)).append("\n");
        sb.append("    errorMessage: ").append(toIndentedString(errorMessage)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    executionId: ").append(toIndentedString(executionId)).append("\n");
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
        WorkflowRunInfo workflowRunInfo = (WorkflowRunInfo) o;
        return Objects.equals(this.parentWorkflowId, workflowRunInfo.parentWorkflowId) && Objects.equals(this.status,
            workflowRunInfo.status) && Objects.equals(this.errorCode, workflowRunInfo.errorCode) && Objects.equals(
            this.errorMessage, workflowRunInfo.errorMessage) && Objects.equals(this.outputs, workflowRunInfo.outputs)
            && Objects.equals(this.metadata, workflowRunInfo.metadata) && Objects.equals(this.startTime,
            workflowRunInfo.startTime) && Objects.equals(this.endTime, workflowRunInfo.endTime) && Objects.equals(
            this.executionId, workflowRunInfo.executionId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(parentWorkflowId, status, errorCode, errorMessage, outputs, metadata, startTime, endTime,
            executionId);
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
