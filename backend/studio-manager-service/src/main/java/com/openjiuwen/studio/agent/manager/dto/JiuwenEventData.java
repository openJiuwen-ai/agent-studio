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

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Validated
public class JiuwenEventData implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("memory")
    @Schema(description = "记忆信息", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> memory = null;

    @JsonProperty("answer")
    @Schema(description = "回答内容", example = "{}")
    @Valid
    private Object answer = null;

    @JsonProperty("origin_answer")
    @Schema(description = "原始回答内容", example = "{}")
    @Valid
    private Object originAnswer = null;

    @JsonProperty("think")
    @Schema(description = "思考过程", example = "正在思考中...")
    private String think = null;

    @JsonProperty("original_message")
    @Schema(description = "原始消息", example = "用户输入的原始消息")
    private String originalMessage = null;

    @JsonProperty("card")
    @Schema(description = "卡片内容", example = "{}")
    @Valid
    private Object card = null;

    @JsonProperty("card_code")
    @Schema(description = "卡片代码", example = "card-001")
    private String cardCode = null;

    @JsonProperty("resource_url")
    @Schema(description = "资源URL", example = "https://example.com/resource")
    private String resourceUrl = null;

    @JsonProperty("instance_id")
    @Schema(description = "实例ID", example = "instance-001")
    private String instanceId = null;

    @JsonProperty("version_id")
    @Schema(description = "版本ID", example = "v1")
    private String versionId = null;

    @JsonProperty("code")
    @Schema(description = "状态码", example = "200")
    private Integer code = null;

    @JsonProperty("message")
    @Schema(description = "消息内容", example = "操作成功")
    private String message = null;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    private String nodeId = null;

    @JsonProperty("node_name")
    @Schema(description = "节点名称", example = "开始节点")
    private String nodeName = null;

    @JsonProperty("node_type")
    @Schema(description = "节点类型", example = "start")
    private String nodeType = null;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "workflow-001")
    private String workflowId = null;

    @JsonProperty("workflow_name")
    @Schema(description = "工作流名称", example = "示例工作流")
    private String workflowName = null;

    @JsonProperty("parentNodeId")
    @Schema(description = "父节点ID", example = "parent-node-001")
    private String parentNodeId = null;

    @JsonProperty("componentId")
    @Schema(description = "组件ID", example = "component-001")
    private String componentId = null;

    @JsonProperty("traceId")
    @Schema(description = "链路追踪ID", example = "trace-001")
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
    @Schema(description = "智能体父调用ID", example = "parent-invoke-001")
    private String agentParentInvokeId = null;

    @JsonProperty("conversationId")
    @Schema(description = "会话ID", example = "conversation-001")
    private String conversationId = null;

    @JsonProperty("inputs")
    @Schema(description = "输入参数", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出参数", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> outputs = null;

    @JsonProperty("invokeId")
    @Schema(description = "调用ID", example = "invoke-001")
    private String invokeId = null;

    @JsonProperty("parentInvokeId")
    @Schema(description = "父调用ID", example = "parent-invoke-001")
    private String parentInvokeId = null;

    @JsonProperty("onInvokeData")
    @Schema(description = "调用数据列表", example = "[]")
    @Valid
    @Size()
    private List<Map<String, Object>> onInvokeData = null;

    @JsonProperty("error")
    @Schema(description = "错误信息", example = "{}")
    @Valid
    private JiuwenEventDataError error = null;

    @JsonProperty("status")
    @Schema(description = "状态", example = "running")
    private StatusEnum status = null;

    @JsonProperty("startTime")
    @Schema(description = "开始时间", example = "2026-01-01T00:00:00Z")
    private String startTime = null;

    @JsonProperty("endTime")
    @Schema(description = "结束时间", example = "2026-01-01T00:01:00Z")
    private String endTime = null;

    @JsonProperty("elapsedTime")
    @Schema(description = "耗时", example = "1000")
    private String elapsedTime = null;

    @JsonProperty("metaData")
    @Schema(description = "元数据", example = "{}")
    @Valid
    @Size()
    private Map<String, Object> metaData = null;

    @JsonProperty("pack")
    @Schema(description = "打包数据", example = "{}")
    @Valid
    private Object pack = null;

    @JsonProperty("loopIndex")
    @Schema(description = "循环索引", example = "0")
    private Integer loopIndex = null;

    @JsonProperty("loopNodeId")
    @Schema(description = "循环节点ID", example = "loop-node-001")
    private String loopNodeId = null;

    @JsonProperty("enable_history")
    @Schema(description = "是否启用历史记录", example = "true")
    private Boolean enableHistory = null;

    @JsonProperty("innerError")
    @Schema(description = "内部错误信息", example = "{}")
    @Valid
    private JiuwenEventDataInnerError innerError = null;

    public Map<String, Object> getMemory() {
        return memory;
    }

    public JiuwenEventData setMemory(Map<String, Object> memory) {
        this.memory = memory;
        return this;
    }

    public Object getAnswer() {
        return answer;
    }

    public JiuwenEventData setAnswer(Object answer) {
        this.answer = answer;
        return this;
    }

    public Object getOriginAnswer() {
        return originAnswer;
    }

    public JiuwenEventData setOriginAnswer(Object originAnswer) {
        this.originAnswer = originAnswer;
        return this;
    }

    public String getThink() {
        return think;
    }

    public JiuwenEventData setThink(String think) {
        this.think = think;
        return this;
    }

    public String getOriginalMessage() {
        return originalMessage;
    }

    public JiuwenEventData setOriginalMessage(String originalMessage) {
        this.originalMessage = originalMessage;
        return this;
    }

    public Object getCard() {
        return card;
    }

    public JiuwenEventData setCard(Object card) {
        this.card = card;
        return this;
    }

    public String getCardCode() {
        return cardCode;
    }

    public JiuwenEventData setCardCode(String cardCode) {
        this.cardCode = cardCode;
        return this;
    }

    public String getResourceUrl() {
        return resourceUrl;
    }

    public JiuwenEventData setResourceUrl(String resourceUrl) {
        this.resourceUrl = resourceUrl;
        return this;
    }

    public String getInstanceId() {
        return instanceId;
    }

    public JiuwenEventData setInstanceId(String instanceId) {
        this.instanceId = instanceId;
        return this;
    }

    public String getVersionId() {
        return versionId;
    }

    public JiuwenEventData setVersionId(String versionId) {
        this.versionId = versionId;
        return this;
    }

    public Integer getCode() {
        return code;
    }

    public JiuwenEventData setCode(Integer code) {
        this.code = code;
        return this;
    }

    public String getMessage() {
        return message;
    }

    public JiuwenEventData setMessage(String message) {
        this.message = message;
        return this;
    }

    public String getNodeId() {
        return nodeId;
    }

    public JiuwenEventData setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getNodeName() {
        return nodeName;
    }

    public JiuwenEventData setNodeName(String nodeName) {
        this.nodeName = nodeName;
        return this;
    }

    public String getNodeType() {
        return nodeType;
    }

    public JiuwenEventData setNodeType(String nodeType) {
        this.nodeType = nodeType;
        return this;
    }

    public String getWorkflowId() {
        return workflowId;
    }

    public JiuwenEventData setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowName() {
        return workflowName;
    }

    public JiuwenEventData setWorkflowName(String workflowName) {
        this.workflowName = workflowName;
        return this;
    }

    public String getParentNodeId() {
        return parentNodeId;
    }

    public JiuwenEventData setParentNodeId(String parentNodeId) {
        this.parentNodeId = parentNodeId;
        return this;
    }

    public String getComponentId() {
        return componentId;
    }

    public JiuwenEventData setComponentId(String componentId) {
        this.componentId = componentId;
        return this;
    }

    public String getTraceId() {
        return traceId;
    }

    public JiuwenEventData setTraceId(String traceId) {
        this.traceId = traceId;
        return this;
    }

    public String getComponentType() {
        return componentType;
    }

    public JiuwenEventData setComponentType(String componentType) {
        this.componentType = componentType;
        return this;
    }

    public String getComponentName() {
        return componentName;
    }

    public JiuwenEventData setComponentName(String componentName) {
        this.componentName = componentName;
        return this;
    }

    public String getAgentId() {
        return agentId;
    }

    public JiuwenEventData setAgentId(String agentId) {
        this.agentId = agentId;
        return this;
    }

    public String getAgentParentInvokeId() {
        return agentParentInvokeId;
    }

    public JiuwenEventData setAgentParentInvokeId(String agentParentInvokeId) {
        this.agentParentInvokeId = agentParentInvokeId;
        return this;
    }

    public String getConversationId() {
        return conversationId;
    }

    public JiuwenEventData setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public Map<String, Object> getInputs() {
        return inputs;
    }

    public JiuwenEventData setInputs(Map<String, Object> inputs) {
        this.inputs = inputs;
        return this;
    }

    public Map<String, Object> getOutputs() {
        return outputs;
    }

    public JiuwenEventData setOutputs(Map<String, Object> outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getInvokeId() {
        return invokeId;
    }

    public JiuwenEventData setInvokeId(String invokeId) {
        this.invokeId = invokeId;
        return this;
    }

    public String getParentInvokeId() {
        return parentInvokeId;
    }

    public JiuwenEventData setParentInvokeId(String parentInvokeId) {
        this.parentInvokeId = parentInvokeId;
        return this;
    }

    public List<Map<String, Object>> getOnInvokeData() {
        return onInvokeData;
    }

    public JiuwenEventData setOnInvokeData(List<Map<String, Object>> onInvokeData) {
        this.onInvokeData = onInvokeData;
        return this;
    }

    public JiuwenEventDataError getError() {
        return error;
    }

    public JiuwenEventData setError(JiuwenEventDataError error) {
        this.error = error;
        return this;
    }

    public StatusEnum getStatus() {
        return status;
    }

    public JiuwenEventData setStatus(StatusEnum status) {
        this.status = status;
        return this;
    }

    public String getStartTime() {
        return startTime;
    }

    public JiuwenEventData setStartTime(String startTime) {
        this.startTime = startTime;
        return this;
    }

    public String getEndTime() {
        return endTime;
    }

    public JiuwenEventData setEndTime(String endTime) {
        this.endTime = endTime;
        return this;
    }

    public String getElapsedTime() {
        return elapsedTime;
    }

    public JiuwenEventData setElapsedTime(String elapsedTime) {
        this.elapsedTime = elapsedTime;
        return this;
    }

    public Map<String, Object> getMetaData() {
        return metaData;
    }

    public JiuwenEventData setMetaData(Map<String, Object> metaData) {
        this.metaData = metaData;
        return this;
    }

    public Object getPack() {
        return pack;
    }

    public JiuwenEventData setPack(Object pack) {
        this.pack = pack;
        return this;
    }

    public Integer getLoopIndex() {
        return loopIndex;
    }

    public JiuwenEventData setLoopIndex(Integer loopIndex) {
        this.loopIndex = loopIndex;
        return this;
    }

    public String getLoopNodeId() {
        return loopNodeId;
    }

    public JiuwenEventData setLoopNodeId(String loopNodeId) {
        this.loopNodeId = loopNodeId;
        return this;
    }

    public JiuwenEventData setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    public JiuwenEventDataInnerError getInnerError() {
        return innerError;
    }

    public JiuwenEventData setInnerError(JiuwenEventDataInnerError innerError) {
        this.innerError = innerError;
        return this;
    }

    public enum StatusEnum {
        START("start"),
        ERROR("error"),
        RUNNING("running"),
        FINISH("finish");

        private String value;

        StatusEnum(String value) {
            this.value = value;
        }

        @JsonCreator
        public static StatusEnum fromValue(String text) {
            for (StatusEnum b : StatusEnum.values()) {
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

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        JiuwenEventData that = (JiuwenEventData) o;
        return Objects.equals(this.memory, that.memory) && Objects.equals(this.answer, that.answer)
            && Objects.equals(this.originAnswer, that.originAnswer) && Objects.equals(this.think, that.think)
            && Objects.equals(this.originalMessage, that.originalMessage) && Objects.equals(this.card, that.card)
            && Objects.equals(this.cardCode, that.cardCode) && Objects.equals(this.resourceUrl, that.resourceUrl)
            && Objects.equals(this.instanceId, that.instanceId) && Objects.equals(this.versionId, that.versionId)
            && Objects.equals(this.code, that.code) && Objects.equals(this.message, that.message)
            && Objects.equals(this.nodeId, that.nodeId) && Objects.equals(this.nodeName, that.nodeName)
            && Objects.equals(this.nodeType, that.nodeType) && Objects.equals(this.workflowId, that.workflowId)
            && Objects.equals(this.workflowName, that.workflowName) && Objects.equals(this.parentNodeId,
            that.parentNodeId) && Objects.equals(this.componentId, that.componentId)
            && Objects.equals(this.traceId, that.traceId) && Objects.equals(this.componentType, that.componentType)
            && Objects.equals(this.componentName, that.componentName) && Objects.equals(this.agentId, that.agentId)
            && Objects.equals(this.agentParentInvokeId, that.agentParentInvokeId) && Objects.equals(this.conversationId,
            that.conversationId) && Objects.equals(this.inputs, that.inputs) && Objects.equals(this.outputs,
            that.outputs) && Objects.equals(this.invokeId, that.invokeId) && Objects.equals(this.parentInvokeId,
            that.parentInvokeId) && Objects.equals(this.onInvokeData, that.onInvokeData)
            && Objects.equals(this.error, that.error) && Objects.equals(this.status, that.status)
            && Objects.equals(this.startTime, that.startTime) && Objects.equals(this.endTime, that.endTime)
            && Objects.equals(this.elapsedTime, that.elapsedTime) && Objects.equals(this.metaData, that.metaData)
            && Objects.equals(this.pack, that.pack) && Objects.equals(this.loopIndex, that.loopIndex)
            && Objects.equals(this.loopNodeId, that.loopNodeId) && Objects.equals(this.enableHistory,
            that.enableHistory) && Objects.equals(this.innerError, that.innerError);
    }

    @Override
    public int hashCode() {
        return Objects.hash(memory, answer, originAnswer, think, originalMessage, card, cardCode, resourceUrl,
            instanceId, versionId, code, message, nodeId, nodeName, nodeType, workflowId, workflowName, parentNodeId,
            componentId, traceId, componentType, componentName, agentId, agentParentInvokeId, conversationId, inputs,
            outputs, invokeId, parentInvokeId, onInvokeData, error, status, startTime, endTime, elapsedTime, metaData,
            pack, loopIndex, loopNodeId, enableHistory, innerError);
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class JiuwenEventData {\n");
        sb.append("    componentId: ").append(componentId).append("\n");
        sb.append("    componentName: ").append(componentName).append("\n");
        sb.append("    componentType: ").append(componentType).append("\n");
        sb.append("    status: ").append(status).append("\n");
        sb.append("}");
        return sb.toString();
    }
}
