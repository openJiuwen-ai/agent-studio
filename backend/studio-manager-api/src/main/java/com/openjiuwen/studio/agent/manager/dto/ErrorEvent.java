/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * ErrorEvent
 */

@Validated

public class ErrorEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("node_id")
    @Length(max = 128)
    private String nodeId = null;

    @JsonProperty("node_type")
    @Length(max = 32)
    private String nodeType = null;

    @JsonProperty("node_name")
    @Length(max = 64)
    private String nodeName = null;

    @JsonProperty("code")
    private String code = null;

    @JsonProperty("message")
    private String message = null;

    @JsonProperty("workflow_id")
    private String workflowId = null;

    @JsonProperty("workflow_name")
    private String workflowName = null;

    @JsonProperty("parent_workflow_id")
    @Length(max = 32)
    private String parentWorkflowId = null;

    @JsonProperty("error_msg")
    private String errorMsg = null;

    @JsonProperty("error_reason")
    private String errorReason = null;

    @JsonProperty("error_suggestion")
    private String errorSuggestion = null;

    @JsonProperty("error_code")
    private String errorCode = null;

    public String getNodeId() {
        return nodeId;
    }

    public ErrorEvent setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getNodeType() {
        return nodeType;
    }

    public ErrorEvent setNodeType(String nodeType) {
        this.nodeType = nodeType;
        return this;
    }

    public String getNodeName() {
        return nodeName;
    }

    public ErrorEvent setNodeName(String nodeName) {
        this.nodeName = nodeName;
        return this;
    }

    public String getCode() {
        return code;
    }

    public ErrorEvent setCode(String code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public ErrorEvent setMessage(String message) {
        this.message = message;
        return this;
    }

    public String getWorkflowId() {
        return workflowId;
    }

    public ErrorEvent setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowName() {
        return workflowName;
    }

    public ErrorEvent setWorkflowName(String workflowName) {
        this.workflowName = workflowName;
        return this;
    }

    public String getParentWorkflowId() {
        return parentWorkflowId;
    }

    public ErrorEvent setParentWorkflowId(String parentWorkflowId) {
        this.parentWorkflowId = parentWorkflowId;
        return this;
    }

    public String getErrorMsg() {
        return errorMsg;
    }

    public ErrorEvent setErrorMsg(String errorMsg) {
        this.errorMsg = errorMsg;
        return this;
    }

    public String getErrorReason() {
        return errorReason;
    }

    public ErrorEvent setErrorReason(String errorReason) {
        this.errorReason = errorReason;
        return this;
    }

    public String getErrorSuggestion() {
        return errorSuggestion;
    }

    public ErrorEvent setErrorSuggestion(String errorSuggestion) {
        this.errorSuggestion = errorSuggestion;
        return this;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public ErrorEvent setErrorCode(String errorCode) {
        this.errorCode = errorCode;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ErrorEvent {\n");

        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    nodeType: ").append(toIndentedString(nodeType)).append("\n");
        sb.append("    nodeName: ").append(toIndentedString(nodeName)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    workflowName: ").append(toIndentedString(workflowName)).append("\n");
        sb.append("    parentWorkflowId: ").append(toIndentedString(parentWorkflowId)).append("\n");
        sb.append("    errorMsg: ").append(toIndentedString(errorMsg)).append("\n");
        sb.append("    errorReason: ").append(toIndentedString(errorReason)).append("\n");
        sb.append("    errorSuggestion: ").append(toIndentedString(errorSuggestion)).append("\n");
        sb.append("    errorCode: ").append(toIndentedString(errorCode)).append("\n");
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
        ErrorEvent errorEvent = (ErrorEvent) o;
        return Objects.equals(this.nodeId, errorEvent.nodeId) && Objects.equals(this.nodeType, errorEvent.nodeType)
            && Objects.equals(this.nodeName, errorEvent.nodeName) && Objects.equals(this.code, errorEvent.code)
            && Objects.equals(this.message, errorEvent.message) && Objects.equals(this.workflowId,
            errorEvent.workflowId) && Objects.equals(this.workflowName, errorEvent.workflowName) && Objects.equals(
            this.parentWorkflowId, errorEvent.parentWorkflowId) && Objects.equals(this.errorMsg, errorEvent.errorMsg)
            && Objects.equals(this.errorReason, errorEvent.errorReason) && Objects.equals(this.errorSuggestion,
            errorEvent.errorSuggestion) && Objects.equals(this.errorCode, errorEvent.errorCode);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nodeId, nodeType, nodeName, code, message, workflowId, workflowName, parentWorkflowId,
            errorMsg, errorReason, errorSuggestion, errorCode);
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
