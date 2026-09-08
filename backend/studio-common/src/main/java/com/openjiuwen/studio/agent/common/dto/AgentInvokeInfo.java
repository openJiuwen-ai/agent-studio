/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * AgentInvokeInfo
 */

@Validated

public class AgentInvokeInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    @Length(max = 128)
    private String nodeId = null;

    @JsonProperty("node_name")
    @Schema(description = "节点名称", example = "LLM调用节点")
    @Length(max = 128)
    private String nodeName = null;

    @JsonProperty("node_type")
    @Schema(description = "节点类型", example = "llm")
    @Length(max = 32)
    private String nodeType = null;

    @JsonProperty("node_status")
    @Schema(description = "节点状态", example = "success")
    private String nodeStatus = null;

    @JsonProperty("model_deployment_id")
    @Schema(description = "模型部署ID", example = "deploy-001")
    private String modelDeploymentId = null;

    @JsonProperty("error_message")
    @Schema(description = "错误信息", example = "null")
    @Length(max = 4096)
    private String errorMessage = null;

    @JsonProperty("inputs")
    @Schema(description = "输入信息", example = "{}")
    @Valid
    private Object inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出信息", example = "{}")
    @Valid
    private Object outputs = null;

    @JsonProperty("start_time")
    @Schema(description = "开始时间（时间戳，毫秒）", example = "1710000000000")
    private Long startTime = null;

    @JsonProperty("end_time")
    @Schema(description = "结束时间（时间戳，毫秒）", example = "1710000005000")
    private Long endTime = null;

    @JsonProperty("meta_data")
    @Schema(description = "元数据", example = "{}")
    @Valid
    private Object metaData = null;

    public String getNodeId() {
        return nodeId;
    }

    public AgentInvokeInfo setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getNodeName() {
        return nodeName;
    }

    public AgentInvokeInfo setNodeName(String nodeName) {
        this.nodeName = nodeName;
        return this;
    }

    public String getNodeType() {
        return nodeType;
    }

    public AgentInvokeInfo setNodeType(String nodeType) {
        this.nodeType = nodeType;
        return this;
    }

    public String getNodeStatus() {
        return nodeStatus;
    }

    public AgentInvokeInfo setNodeStatus(String nodeStatus) {
        this.nodeStatus = nodeStatus;
        return this;
    }

    public String getModelDeploymentId() {
        return modelDeploymentId;
    }

    public AgentInvokeInfo setModelDeploymentId(String modelDeploymentId) {
        this.modelDeploymentId = modelDeploymentId;
        return this;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public AgentInvokeInfo setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
        return this;
    }

    public Object getInputs() {
        return inputs;
    }

    public AgentInvokeInfo setInputs(Object inputs) {
        this.inputs = inputs;
        return this;
    }

    public Object getOutputs() {
        return outputs;
    }

    public AgentInvokeInfo setOutputs(Object outputs) {
        this.outputs = outputs;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public AgentInvokeInfo setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public AgentInvokeInfo setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public Object getMetaData() {
        return metaData;
    }

    public AgentInvokeInfo setMetaData(Object metaData) {
        this.metaData = metaData;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentInvokeInfo {\n");

        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    nodeName: ").append(toIndentedString(nodeName)).append("\n");
        sb.append("    nodeType: ").append(toIndentedString(nodeType)).append("\n");
        sb.append("    nodeStatus: ").append(toIndentedString(nodeStatus)).append("\n");
        sb.append("    modelDeploymentId: ").append(toIndentedString(modelDeploymentId)).append("\n");
        sb.append("    errorMessage: ").append(toIndentedString(errorMessage)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    metaData: ").append(toIndentedString(metaData)).append("\n");
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
        AgentInvokeInfo agentInvokeInfo = (AgentInvokeInfo) o;
        return Objects.equals(this.nodeId, agentInvokeInfo.nodeId) && Objects.equals(this.nodeName,
            agentInvokeInfo.nodeName) && Objects.equals(this.nodeType, agentInvokeInfo.nodeType) && Objects.equals(
            this.nodeStatus, agentInvokeInfo.nodeStatus) && Objects.equals(this.modelDeploymentId,
            agentInvokeInfo.modelDeploymentId) && Objects.equals(this.errorMessage, agentInvokeInfo.errorMessage)
            && Objects.equals(this.inputs, agentInvokeInfo.inputs) && Objects.equals(this.outputs,
            agentInvokeInfo.outputs) && Objects.equals(this.startTime, agentInvokeInfo.startTime) && Objects.equals(
            this.endTime, agentInvokeInfo.endTime) && Objects.equals(this.metaData, agentInvokeInfo.metaData);
    }

    @Override
    public int hashCode() {
        return Objects.hash(nodeId, nodeName, nodeType, nodeStatus, modelDeploymentId, errorMessage, inputs, outputs,
            startTime, endTime, metaData);
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
