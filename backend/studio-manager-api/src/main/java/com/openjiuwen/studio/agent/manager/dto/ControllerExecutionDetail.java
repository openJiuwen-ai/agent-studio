/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 多智能体会话的对话详情
 */
@ApiModel(description = "多智能体会话的对话详情")

@Validated

public class ControllerExecutionDetail implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("conversation_id")
    private String conversationId = null;

    @JsonProperty("execution_id")
    private String executionId = null;

    @JsonProperty("inputs")
    private String inputs = null;

    @JsonProperty("outputs")
    private String outputs = null;

    @JsonProperty("error_info")
    private String errorInfo = null;

    @JsonProperty("invocations")
    @Valid
    @Size()
    private List<ControllerInvokeInfo> invocations = null;

    @JsonProperty("status")
    private String status = null;

    @JsonProperty("start_time")
    private Long startTime = null;

    @JsonProperty("end_time")
    private Long endTime = null;

    @JsonProperty("nestedWorkflows")
    @Valid
    @Size()
    private List<WorkflowBaseData> nestedWorkflows = null;

    public String getConversationId() {
        return conversationId;
    }

    public ControllerExecutionDetail setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public String getExecutionId() {
        return executionId;
    }

    public ControllerExecutionDetail setExecutionId(String executionId) {
        this.executionId = executionId;
        return this;
    }

    public String getInputs() {
        return inputs;
    }

    public ControllerExecutionDetail setInputs(String inputs) {
        this.inputs = inputs;
        return this;
    }

    public String getOutputs() {
        return outputs;
    }

    public ControllerExecutionDetail setOutputs(String outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getErrorInfo() {
        return errorInfo;
    }

    public ControllerExecutionDetail setErrorInfo(String errorInfo) {
        this.errorInfo = errorInfo;
        return this;
    }

    public List<ControllerInvokeInfo> getInvocations() {
        return invocations;
    }

    public ControllerExecutionDetail setInvocations(List<ControllerInvokeInfo> invocations) {
        this.invocations = invocations;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public ControllerExecutionDetail setStatus(String status) {
        this.status = status;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public ControllerExecutionDetail setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public ControllerExecutionDetail setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public List<WorkflowBaseData> getNestedWorkflows() {
        return nestedWorkflows;
    }

    public ControllerExecutionDetail setNestedWorkflows(List<WorkflowBaseData> nestedWorkflows) {
        this.nestedWorkflows = nestedWorkflows;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerExecutionDetail {\n");

        sb.append("    conversationId: ").append(toIndentedString(conversationId)).append("\n");
        sb.append("    executionId: ").append(toIndentedString(executionId)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    errorInfo: ").append(toIndentedString(errorInfo)).append("\n");
        sb.append("    invocations: ").append(toIndentedString(invocations)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    nestedWorkflows: ").append(toIndentedString(nestedWorkflows)).append("\n");
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
        ControllerExecutionDetail controllerExecutionDetail = (ControllerExecutionDetail) o;
        return Objects.equals(this.conversationId, controllerExecutionDetail.conversationId) && Objects.equals(
            this.executionId, controllerExecutionDetail.executionId) && Objects.equals(this.inputs,
            controllerExecutionDetail.inputs) && Objects.equals(this.outputs, controllerExecutionDetail.outputs)
            && Objects.equals(this.errorInfo, controllerExecutionDetail.errorInfo) && Objects.equals(this.invocations,
            controllerExecutionDetail.invocations) && Objects.equals(this.status, controllerExecutionDetail.status)
            && Objects.equals(this.startTime, controllerExecutionDetail.startTime) && Objects.equals(this.endTime,
            controllerExecutionDetail.endTime) && Objects.equals(this.nestedWorkflows,
            controllerExecutionDetail.nestedWorkflows);
    }

    @Override
    public int hashCode() {
        return Objects.hash(conversationId, executionId, inputs, outputs, errorInfo, invocations, status, startTime,
            endTime, nestedWorkflows);
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
