/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import com.fasterxml.jackson.annotation.JsonValue;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * ControllerInvokeInfo
 */

@Validated

public class ControllerInvokeInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("invoke_id")
    @Schema(description = "调用ID", example = "invoke-001")
    @Length(max = 128)
    private String invokeId = null;

    @JsonProperty("parent_invoke_id")
    @Schema(description = "父调用ID", example = "parent-invoke-001")
    @Length(max = 128)
    private String parentInvokeId = null;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    @Length(max = 128)
    private String nodeId = null;

    @JsonProperty("node_name")
    @Schema(description = "节点名称", example = "开始节点")
    @Length(max = 128)
    private String nodeName = null;

    @JsonProperty("node_type")
    @Schema(description = "节点类型", example = "START")
    @Length(max = 32)
    private String nodeType = null;

    @JsonProperty("node_status")
    @Schema(description = "节点状态", example = "RUNNING")
    private String nodeStatus = null;

    @JsonProperty("parent_node_id")
    @Schema(description = "父节点ID", example = "parent-node-001")
    @Length(max = 128)
    private String parentNodeId = null;

    @JsonProperty("model_deployment_id")
    @Schema(description = "模型部署ID", example = "deployment-001")
    private String modelDeploymentId = null;

    @JsonProperty("error_message")
    @Schema(description = "错误信息", example = "调用失败")
    @Length(max = 4096)
    private String errorMessage = null;

    @JsonProperty("status")
    @Schema(description = "调用状态", example = "{}")
    @Valid
    private ControllerInvokeInfoStatus status = null;

    @JsonProperty("messages")
    @Schema(description = "消息列表", example = "[]")
    @Valid
    @Size()
    private List<com.openjiuwen.studio.agent.common.dto.agent.Message> messages = null;

    @JsonProperty("inputs")
    @Schema(description = "输入参数", example = "{}")
    @Valid
    private Object inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出结果", example = "{}")
    @Valid
    private Object outputs = null;

    @JsonProperty("start_time")
    @Schema(description = "开始时间", example = "1700000000000")
    private Long startTime = null;

    @JsonProperty("end_time")
    @Schema(description = "结束时间", example = "1700000001000")
    private Long endTime = null;

    @JsonProperty("application_id")
    @Schema(description = "应用ID", example = "app-001")
    @Length(max = 128)
    private String applicationId = null;

    @JsonProperty("application_type")
    @Schema(description = "应用类型", example = "AGENT")
    private ApplicationTypeEnum applicationType = null;

    @JsonProperty("parent_application_id")
    @Schema(description = "父应用ID", example = "parent-app-001")
    @Length(max = 128)
    private String parentApplicationId = null;

    @JsonProperty("metadata")
    @Schema(description = "元数据", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> metadata = null;

    public String getInvokeId() {
        return invokeId;
    }

    public ControllerInvokeInfo setInvokeId(String invokeId) {
        this.invokeId = invokeId;
        return this;
    }

    public String getParentInvokeId() {
        return parentInvokeId;
    }

    public ControllerInvokeInfo setParentInvokeId(String parentInvokeId) {
        this.parentInvokeId = parentInvokeId;
        return this;
    }

    public String getNodeId() {
        return nodeId;
    }

    public ControllerInvokeInfo setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getNodeName() {
        return nodeName;
    }

    public ControllerInvokeInfo setNodeName(String nodeName) {
        this.nodeName = nodeName;
        return this;
    }

    public String getNodeType() {
        return nodeType;
    }

    public ControllerInvokeInfo setNodeType(String nodeType) {
        this.nodeType = nodeType;
        return this;
    }

    public String getNodeStatus() {
        return nodeStatus;
    }

    public ControllerInvokeInfo setNodeStatus(String nodeStatus) {
        this.nodeStatus = nodeStatus;
        return this;
    }

    public String getParentNodeId() {
        return parentNodeId;
    }

    public ControllerInvokeInfo setParentNodeId(String parentNodeId) {
        this.parentNodeId = parentNodeId;
        return this;
    }

    public String getModelDeploymentId() {
        return modelDeploymentId;
    }

    public ControllerInvokeInfo setModelDeploymentId(String modelDeploymentId) {
        this.modelDeploymentId = modelDeploymentId;
        return this;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public ControllerInvokeInfo setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
        return this;
    }

    public ControllerInvokeInfoStatus getStatus() {
        return status;
    }

    public ControllerInvokeInfo setStatus(ControllerInvokeInfoStatus status) {
        this.status = status;
        return this;
    }

    public List<com.openjiuwen.studio.agent.common.dto.agent.Message> getMessages() {
        return messages;
    }

    public ControllerInvokeInfo setMessages(List<com.openjiuwen.studio.agent.common.dto.agent.Message> messages) {
        this.messages = messages;
        return this;
    }

    public Object getInputs() {
        return inputs;
    }

    public ControllerInvokeInfo setInputs(Object inputs) {
        this.inputs = inputs;
        return this;
    }

    public Object getOutputs() {
        return outputs;
    }

    public ControllerInvokeInfo setOutputs(Object outputs) {
        this.outputs = outputs;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public ControllerInvokeInfo setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public ControllerInvokeInfo setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public String getApplicationId() {
        return applicationId;
    }

    public ControllerInvokeInfo setApplicationId(String applicationId) {
        this.applicationId = applicationId;
        return this;
    }

    public ApplicationTypeEnum getApplicationType() {
        return applicationType;
    }

    public ControllerInvokeInfo setApplicationType(ApplicationTypeEnum applicationType) {
        this.applicationType = applicationType;
        return this;
    }

    public String getParentApplicationId() {
        return parentApplicationId;
    }

    public ControllerInvokeInfo setParentApplicationId(String parentApplicationId) {
        this.parentApplicationId = parentApplicationId;
        return this;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public ControllerInvokeInfo setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class ControllerInvokeInfo {\n");

        sb.append("    invokeId: ").append(toIndentedString(invokeId)).append("\n");
        sb.append("    parentInvokeId: ").append(toIndentedString(parentInvokeId)).append("\n");
        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    nodeName: ").append(toIndentedString(nodeName)).append("\n");
        sb.append("    nodeType: ").append(toIndentedString(nodeType)).append("\n");
        sb.append("    nodeStatus: ").append(toIndentedString(nodeStatus)).append("\n");
        sb.append("    parentNodeId: ").append(toIndentedString(parentNodeId)).append("\n");
        sb.append("    modelDeploymentId: ").append(toIndentedString(modelDeploymentId)).append("\n");
        sb.append("    errorMessage: ").append(toIndentedString(errorMessage)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
        sb.append("    messages: ").append(toIndentedString(messages)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    applicationId: ").append(toIndentedString(applicationId)).append("\n");
        sb.append("    applicationType: ").append(toIndentedString(applicationType)).append("\n");
        sb.append("    parentApplicationId: ").append(toIndentedString(parentApplicationId)).append("\n");
        sb.append("    metadata: ").append(toIndentedString(metadata)).append("\n");
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
        ControllerInvokeInfo controllerInvokeInfo = (ControllerInvokeInfo) o;
        return Objects.equals(this.invokeId, controllerInvokeInfo.invokeId) && Objects.equals(this.parentInvokeId,
            controllerInvokeInfo.parentInvokeId) && Objects.equals(this.nodeId, controllerInvokeInfo.nodeId)
            && Objects.equals(this.nodeName, controllerInvokeInfo.nodeName) && Objects.equals(this.nodeType,
            controllerInvokeInfo.nodeType) && Objects.equals(this.nodeStatus, controllerInvokeInfo.nodeStatus)
            && Objects.equals(this.parentNodeId, controllerInvokeInfo.parentNodeId) && Objects.equals(
            this.modelDeploymentId, controllerInvokeInfo.modelDeploymentId) && Objects.equals(this.errorMessage,
            controllerInvokeInfo.errorMessage) && Objects.equals(this.status, controllerInvokeInfo.status)
            && Objects.equals(this.messages, controllerInvokeInfo.messages) && Objects.equals(this.inputs,
            controllerInvokeInfo.inputs) && Objects.equals(this.outputs, controllerInvokeInfo.outputs)
            && Objects.equals(this.startTime, controllerInvokeInfo.startTime) && Objects.equals(this.endTime,
            controllerInvokeInfo.endTime) && Objects.equals(this.applicationId, controllerInvokeInfo.applicationId)
            && Objects.equals(this.applicationType, controllerInvokeInfo.applicationType) && Objects.equals(
            this.parentApplicationId, controllerInvokeInfo.parentApplicationId) && Objects.equals(this.metadata,
            controllerInvokeInfo.metadata);
    }

    @Override
    public int hashCode() {
        return Objects.hash(invokeId, parentInvokeId, nodeId, nodeName, nodeType, nodeStatus, parentNodeId,
            modelDeploymentId, errorMessage, status, messages, inputs, outputs, startTime, endTime, applicationId,
            applicationType, parentApplicationId, metadata);
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

    /**
     * 节点归属的应用的类型
     */
    public enum ApplicationTypeEnum {
        AGENT("AGENT"),

        WORKFLOW("WORKFLOW"),

        LLM("LLM"),

        CONTROLLER("CONTROLLER");

        private String value;

        ApplicationTypeEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static ApplicationTypeEnum fromValue(String text) {
            for (ApplicationTypeEnum b : ApplicationTypeEnum.values()) {
                if (String.valueOf(b.value).equals(text)) {
                    return b;
                }
            }
            return null;
        }

        @Override
        @JsonValue
        public String toString() {
            return String.valueOf(value);
        }
    }
}
