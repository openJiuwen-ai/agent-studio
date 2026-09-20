/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * JiuwenAgentEventData
 */

@Validated

public class JiuwenAgentEventData implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("think")
    @Schema(description = "思考内容", example = "正在分析用户问题...")
    private String think = null;

    @JsonProperty("answer")
    @Schema(description = "回答内容", example = "{}")
    @Valid
    private Object answer = null;

    @JsonProperty("code")
    @Schema(description = "状态码", example = "200")
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息", example = "success")
    private String message = null;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    private String nodeId = null;

    @JsonProperty("node_name")
    @Schema(description = "节点名称", example = "开始节点")
    private String nodeName = null;

    @JsonProperty("card")
    @Schema(description = "卡片数据", example = "{}")
    @Valid
    private Object card = null;

    @JsonProperty("card_code")
    @Schema(description = "卡片编码", example = "card-001")
    private String cardCode = null;

    @JsonProperty("instance_id")
    @Schema(description = "实例ID", example = "instance-001")
    private String instanceId = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1")
    private String versionId = null;

    @JsonProperty("pack")
    @Schema(description = "打包数据", example = "{}")
    @Valid
    private Object pack = null;

    @JsonProperty("origin_answer")
    @Schema(description = "原始回答", example = "{}")
    @Valid
    private Object originAnswer = null;

    @JsonProperty("node_type")
    @Schema(description = "节点类型", example = "start")
    private String nodeType = null;

    @JsonProperty("componentId")
    @Schema(description = "组件ID", example = "comp-001")
    private String componentId = null;

    @JsonProperty("traceId")
    @Schema(description = "追踪ID", example = "trace-001")
    private String traceId = null;

    @JsonProperty("componentType")
    @Schema(description = "组件类型", example = "llm")
    private String componentType = null;

    @JsonProperty("componentName")
    @Schema(description = "组件名称", example = "大语言模型")
    private String componentName = null;

    @JsonProperty("agentId")
    @Schema(description = "智能体ID", example = "agent-001")
    private String agentId = null;

    @JsonProperty("agentParentInvokeId")
    @Schema(description = "智能体父调用ID", example = "invoke-001")
    private String agentParentInvokeId = null;

    @JsonProperty("conversationId")
    @Schema(description = "会话ID", example = "conv-001")
    private String conversationId = null;

    @JsonProperty("inputs")
    @Schema(description = "输入数据", example = "{}")
    @Valid
    private Object inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出数据", example = "{}")
    @Valid
    private Object outputs = null;

    @JsonProperty("chainId")
    @Schema(description = "链路ID", example = "chain-001")
    private String chainId = null;

    @JsonProperty("invokeId")
    @Schema(description = "调用ID", example = "invoke-001")
    private String invokeId = null;

    @JsonProperty("parentInvokeId")
    @Schema(description = "父调用ID", example = "parent-invoke-001")
    private String parentInvokeId = null;

    @JsonProperty("onInvokeData")
    @Schema(description = "调用时数据", example = "[]")
    @Valid
    @Size()
    private List<Map<String, String>> onInvokeData = null;

    @JsonProperty("invokeType")
    @Schema(description = "调用类型", example = "sync")
    private String invokeType = null;

    @JsonProperty("error")
    @Schema(description = "错误信息", example = "请求超时")
    private String error = null;

    @JsonProperty("startTime")
    @Schema(description = "开始时间", example = "2026-01-01T00:00:00Z")
    private String startTime = null;

    @JsonProperty("endTime")
    @Schema(description = "结束时间", example = "2026-01-01T00:01:00Z")
    private String endTime = null;

    @JsonProperty("elapsedTime")
    @Schema(description = "耗时", example = "60s")
    private String elapsedTime = null;

    @JsonProperty("metaData")
    @Schema(description = "元数据", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> metaData = null;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "wf-001")
    private String workflowId = null;

    @JsonProperty("workflow_name")
    @Schema(description = "工作流名称", example = "智能问答工作流")
    private String workflowName = null;

    public String getThink() {
        return think;
    }

    public JiuwenAgentEventData setThink(String think) {
        this.think = think;
        return this;
    }

    public Object getAnswer() {
        return answer;
    }

    public JiuwenAgentEventData setAnswer(Object answer) {
        this.answer = answer;
        return this;
    }

    public Integer getCode() {
        return code;
    }

    public JiuwenAgentEventData setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public JiuwenAgentEventData setMessage(String message) {
        this.message = message;
        return this;
    }

    public String getNodeId() {
        return nodeId;
    }

    public JiuwenAgentEventData setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getNodeName() {
        return nodeName;
    }

    public JiuwenAgentEventData setNodeName(String nodeName) {
        this.nodeName = nodeName;
        return this;
    }

    public Object getCard() {
        return card;
    }

    public JiuwenAgentEventData setCard(Object card) {
        this.card = card;
        return this;
    }

    public String getCardCode() {
        return cardCode;
    }

    public JiuwenAgentEventData setCardCode(String cardCode) {
        this.cardCode = cardCode;
        return this;
    }

    public String getInstanceId() {
        return instanceId;
    }

    public JiuwenAgentEventData setInstanceId(String instanceId) {
        this.instanceId = instanceId;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public JiuwenAgentEventData setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public Object getPack() {
        return pack;
    }

    public JiuwenAgentEventData setPack(Object pack) {
        this.pack = pack;
        return this;
    }

    public Object getOriginAnswer() {
        return originAnswer;
    }

    public JiuwenAgentEventData setOriginAnswer(Object originAnswer) {
        this.originAnswer = originAnswer;
        return this;
    }

    public String getNodeType() {
        return nodeType;
    }

    public JiuwenAgentEventData setNodeType(String nodeType) {
        this.nodeType = nodeType;
        return this;
    }

    public String getComponentId() {
        return componentId;
    }

    public JiuwenAgentEventData setComponentId(String componentId) {
        this.componentId = componentId;
        return this;
    }

    public String getTraceId() {
        return traceId;
    }

    public JiuwenAgentEventData setTraceId(String traceId) {
        this.traceId = traceId;
        return this;
    }

    public String getComponentType() {
        return componentType;
    }

    public JiuwenAgentEventData setComponentType(String componentType) {
        this.componentType = componentType;
        return this;
    }

    public String getComponentName() {
        return componentName;
    }

    public JiuwenAgentEventData setComponentName(String componentName) {
        this.componentName = componentName;
        return this;
    }

    public String getAgentId() {
        return agentId;
    }

    public JiuwenAgentEventData setAgentId(String agentId) {
        this.agentId = agentId;
        return this;
    }

    public String getAgentParentInvokeId() {
        return agentParentInvokeId;
    }

    public JiuwenAgentEventData setAgentParentInvokeId(String agentParentInvokeId) {
        this.agentParentInvokeId = agentParentInvokeId;
        return this;
    }

    public String getConversationId() {
        return conversationId;
    }

    public JiuwenAgentEventData setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public Object getInputs() {
        return inputs;
    }

    public JiuwenAgentEventData setInputs(Object inputs) {
        this.inputs = inputs;
        return this;
    }

    public Object getOutputs() {
        return outputs;
    }

    public JiuwenAgentEventData setOutputs(Object outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getChainId() {
        return chainId;
    }

    public JiuwenAgentEventData setChainId(String chainId) {
        this.chainId = chainId;
        return this;
    }

    public String getInvokeId() {
        return invokeId;
    }

    public JiuwenAgentEventData setInvokeId(String invokeId) {
        this.invokeId = invokeId;
        return this;
    }

    public String getParentInvokeId() {
        return parentInvokeId;
    }

    public JiuwenAgentEventData setParentInvokeId(String parentInvokeId) {
        this.parentInvokeId = parentInvokeId;
        return this;
    }

    public List<Map<String, String>> getOnInvokeData() {
        return onInvokeData;
    }

    public JiuwenAgentEventData setOnInvokeData(List<Map<String, String>> onInvokeData) {
        this.onInvokeData = onInvokeData;
        return this;
    }

    public String getInvokeType() {
        return invokeType;
    }

    public JiuwenAgentEventData setInvokeType(String invokeType) {
        this.invokeType = invokeType;
        return this;
    }

    public String getError() {
        return error;
    }

    public JiuwenAgentEventData setError(String error) {
        this.error = error;
        return this;
    }

    public String getStartTime() {
        return startTime;
    }

    public JiuwenAgentEventData setStartTime(String startTime) {
        this.startTime = startTime;
        return this;
    }

    public String getEndTime() {
        return endTime;
    }

    public JiuwenAgentEventData setEndTime(String endTime) {
        this.endTime = endTime;
        return this;
    }

    public String getElapsedTime() {
        return elapsedTime;
    }

    public JiuwenAgentEventData setElapsedTime(String elapsedTime) {
        this.elapsedTime = elapsedTime;
        return this;
    }

    public Map<String, Object> getMetaData() {
        return metaData;
    }

    public JiuwenAgentEventData setMetaData(Map<String, Object> metaData) {
        this.metaData = metaData;
        return this;
    }

    public String getWorkflowId() {
        return workflowId;
    }

    public JiuwenAgentEventData setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowName() {
        return workflowName;
    }

    public JiuwenAgentEventData setWorkflowName(String workflowName) {
        this.workflowName = workflowName;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class JiuwenAgentEventData {\n");

        sb.append("    think: ").append(toIndentedString(think)).append("\n");
        sb.append("    answer: ").append(toIndentedString(answer)).append("\n");
        sb.append("    code: ").append(toIndentedString(code)).append("\n");
        sb.append("    message: ").append(toIndentedString(message)).append("\n");
        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    nodeName: ").append(toIndentedString(nodeName)).append("\n");
        sb.append("    card: ").append(toIndentedString(card)).append("\n");
        sb.append("    cardCode: ").append(toIndentedString(cardCode)).append("\n");
        sb.append("    instanceId: ").append(toIndentedString(instanceId)).append("\n");
        sb.append("    versionId: ").append(toIndentedString(versionId)).append("\n");
        sb.append("    pack: ").append(toIndentedString(pack)).append("\n");
        sb.append("    originAnswer: ").append(toIndentedString(originAnswer)).append("\n");
        sb.append("    nodeType: ").append(toIndentedString(nodeType)).append("\n");
        sb.append("    componentId: ").append(toIndentedString(componentId)).append("\n");
        sb.append("    traceId: ").append(toIndentedString(traceId)).append("\n");
        sb.append("    componentType: ").append(toIndentedString(componentType)).append("\n");
        sb.append("    componentName: ").append(toIndentedString(componentName)).append("\n");
        sb.append("    agentId: ").append(toIndentedString(agentId)).append("\n");
        sb.append("    agentParentInvokeId: ").append(toIndentedString(agentParentInvokeId)).append("\n");
        sb.append("    conversationId: ").append(toIndentedString(conversationId)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    chainId: ").append(toIndentedString(chainId)).append("\n");
        sb.append("    invokeId: ").append(toIndentedString(invokeId)).append("\n");
        sb.append("    parentInvokeId: ").append(toIndentedString(parentInvokeId)).append("\n");
        sb.append("    onInvokeData: ").append(toIndentedString(onInvokeData)).append("\n");
        sb.append("    invokeType: ").append(toIndentedString(invokeType)).append("\n");
        sb.append("    error: ").append(toIndentedString(error)).append("\n");
        sb.append("    startTime: ").append(toIndentedString(startTime)).append("\n");
        sb.append("    endTime: ").append(toIndentedString(endTime)).append("\n");
        sb.append("    elapsedTime: ").append(toIndentedString(elapsedTime)).append("\n");
        sb.append("    metaData: ").append(toIndentedString(metaData)).append("\n");
        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    workflowName: ").append(toIndentedString(workflowName)).append("\n");
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
        JiuwenAgentEventData jiuwenAgentEventData = (JiuwenAgentEventData) o;
        return Objects.equals(this.think, jiuwenAgentEventData.think) && Objects.equals(this.answer,
            jiuwenAgentEventData.answer) && Objects.equals(this.code, jiuwenAgentEventData.code) && Objects.equals(
            this.message, jiuwenAgentEventData.message) && Objects.equals(this.nodeId, jiuwenAgentEventData.nodeId)
            && Objects.equals(this.nodeName, jiuwenAgentEventData.nodeName) && Objects.equals(this.card,
            jiuwenAgentEventData.card) && Objects.equals(this.cardCode, jiuwenAgentEventData.cardCode)
            && Objects.equals(this.instanceId, jiuwenAgentEventData.instanceId) && Objects.equals(this.versionId,
            jiuwenAgentEventData.versionId) && Objects.equals(this.pack, jiuwenAgentEventData.pack) && Objects.equals(
            this.originAnswer, jiuwenAgentEventData.originAnswer) && Objects.equals(this.nodeType,
            jiuwenAgentEventData.nodeType) && Objects.equals(this.componentId, jiuwenAgentEventData.componentId)
            && Objects.equals(this.traceId, jiuwenAgentEventData.traceId) && Objects.equals(this.componentType,
            jiuwenAgentEventData.componentType) && Objects.equals(this.componentName,
            jiuwenAgentEventData.componentName) && Objects.equals(this.agentId, jiuwenAgentEventData.agentId)
            && Objects.equals(this.agentParentInvokeId, jiuwenAgentEventData.agentParentInvokeId) && Objects.equals(
            this.conversationId, jiuwenAgentEventData.conversationId) && Objects.equals(this.inputs,
            jiuwenAgentEventData.inputs) && Objects.equals(this.outputs, jiuwenAgentEventData.outputs)
            && Objects.equals(this.chainId, jiuwenAgentEventData.chainId) && Objects.equals(this.invokeId,
            jiuwenAgentEventData.invokeId) && Objects.equals(this.parentInvokeId, jiuwenAgentEventData.parentInvokeId)
            && Objects.equals(this.onInvokeData, jiuwenAgentEventData.onInvokeData) && Objects.equals(this.invokeType,
            jiuwenAgentEventData.invokeType) && Objects.equals(this.error, jiuwenAgentEventData.error)
            && Objects.equals(this.startTime, jiuwenAgentEventData.startTime) && Objects.equals(this.endTime,
            jiuwenAgentEventData.endTime) && Objects.equals(this.elapsedTime, jiuwenAgentEventData.elapsedTime)
            && Objects.equals(this.metaData, jiuwenAgentEventData.metaData) && Objects.equals(this.workflowId,
            jiuwenAgentEventData.workflowId) && Objects.equals(this.workflowName, jiuwenAgentEventData.workflowName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(think, answer, code, message, nodeId, nodeName, card, cardCode, instanceId, versionId, pack,
            originAnswer, nodeType, componentId, traceId, componentType, componentName, agentId, agentParentInvokeId,
            conversationId, inputs, outputs, chainId, invokeId, parentInvokeId, onInvokeData, invokeType, error,
            startTime, endTime, elapsedTime, metaData, workflowId, workflowName);
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
