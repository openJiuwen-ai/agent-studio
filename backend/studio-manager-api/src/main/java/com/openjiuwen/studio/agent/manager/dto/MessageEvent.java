/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * MessageEvent
 */

@Validated

public class MessageEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("text")
    @Schema(description = "文本内容", example = "你好，请帮我查询天气")
    private String text = null;

    @JsonProperty("card")
    @Schema(description = "卡片内容", example = "{}")
    @Valid
    private Object card = null;

    @JsonProperty("metaData")
    @Schema(description = "元数据", example = "{}")
    @Valid
    private Object metaData = null;

    @JsonProperty("pack")
    @Schema(description = "打包数据", example = "{}")
    @Valid
    private Object pack = null;

    @JsonProperty("instance_id")
    @Schema(description = "实例ID", example = "instance-001")
    private String instanceId = null;

    @JsonProperty("card_code")
    @Schema(description = "卡片编码", example = "card-001")
    private String cardCode = null;

    @JsonProperty("resource_url")
    @Schema(description = "资源URL", example = "https://example.com/resource")
    private String resourceUrl = null;

    @JsonProperty("version")
    @Schema(description = "版本号", example = "1.0.0")
    private String version = null;

    @JsonProperty("summary")
    @Schema(description = "摘要", example = "这是一条消息摘要")
    private String summary = null;

    @JsonProperty("origin")
    @Schema(description = "来源", example = "user")
    private String origin = null;

    @JsonProperty("reasoning_content")
    @Schema(description = "推理内容", example = "正在思考中...")
    private String reasoningContent = null;

    @JsonProperty("original")
    @Schema(description = "原始内容", example = "原始消息文本")
    private String original = null;

    @JsonProperty("index")
    @Schema(description = "索引", example = "0")
    private Integer index = null;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node-001")
    @Length(max = 128)
    private String nodeId = null;

    @JsonProperty("node_type")
    @Schema(description = "节点类型", example = "llm")
    @Length(max = 32)
    private String nodeType = null;

    @JsonProperty("node_name")
    @Schema(description = "节点名称", example = "大语言模型节点")
    @Length(max = 64)
    private String nodeName = null;

    @JsonProperty("is_finished")
    @Schema(description = "是否已完成", example = "false")
    private Boolean isFinished = null;

    @JsonProperty("parent_workflow_id")
    @Schema(description = "父工作流ID", example = "parent-workflow-001")
    @Length(max = 32)
    private String parentWorkflowId = null;

    @JsonProperty("workflow_id")
    @Schema(description = "工作流ID", example = "workflow-001")
    @Length(max = 64)
    private String workflowId = null;

    @JsonProperty("workflow_name")
    @Schema(description = "工作流名称", example = "我的工作流")
    private String workflowName = null;

    @JsonProperty("createdTime")
    @Schema(description = "创建时间（毫秒时间戳）", example = "1714521600000")
    private Long createdTime = null;

    @JsonProperty("enable_history")
    @Schema(description = "是否启用历史记录", example = "true")
    private Boolean enableHistory = null;

    public String getText() {
        return text;
    }

    public MessageEvent setText(String text) {
        this.text = text;
        return this;
    }

    public Object getCard() {
        return card;
    }

    public MessageEvent setCard(Object card) {
        this.card = card;
        return this;
    }

    public Object getMetaData() {
        return metaData;
    }

    public MessageEvent setMetaData(Object metaData) {
        this.metaData = metaData;
        return this;
    }

    public Object getPack() {
        return pack;
    }

    public MessageEvent setPack(Object pack) {
        this.pack = pack;
        return this;
    }

    public String getInstanceId() {
        return instanceId;
    }

    public MessageEvent setInstanceId(String instanceId) {
        this.instanceId = instanceId;
        return this;
    }

    public String getCardCode() {
        return cardCode;
    }

    public MessageEvent setCardCode(String cardCode) {
        this.cardCode = cardCode;
        return this;
    }

    public String getResourceUrl() {
        return resourceUrl;
    }

    public MessageEvent setResourceUrl(String resourceUrl) {
        this.resourceUrl = resourceUrl;
        return this;
    }

    public String getVersion() {
        return version;
    }

    public MessageEvent setVersion(String version) {
        this.version = version;
        return this;
    }

    public String getSummary() {
        return summary;
    }

    public MessageEvent setSummary(String summary) {
        this.summary = summary;
        return this;
    }

    public String getOrigin() {
        return origin;
    }

    public MessageEvent setOrigin(String origin) {
        this.origin = origin;
        return this;
    }

    public String getReasoningContent() {
        return reasoningContent;
    }

    public MessageEvent setReasoningContent(String reasoningContent) {
        this.reasoningContent = reasoningContent;
        return this;
    }

    public String getOriginal() {
        return original;
    }

    public MessageEvent setOriginal(String original) {
        this.original = original;
        return this;
    }

    public Integer getIndex() {
        return index;
    }

    public MessageEvent setIndex(Integer index) {
        this.index = index;
        return this;
    }

    public String getNodeId() {
        return nodeId;
    }

    public MessageEvent setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getNodeType() {
        return nodeType;
    }

    public MessageEvent setNodeType(String nodeType) {
        this.nodeType = nodeType;
        return this;
    }

    public String getNodeName() {
        return nodeName;
    }

    public MessageEvent setNodeName(String nodeName) {
        this.nodeName = nodeName;
        return this;
    }

    public MessageEvent setIsFinished(Boolean isFinished) {
        this.isFinished = isFinished;
        return this;
    }

    public Boolean isIsFinished() {
        return isFinished;
    }

    public String getParentWorkflowId() {
        return parentWorkflowId;
    }

    public MessageEvent setParentWorkflowId(String parentWorkflowId) {
        this.parentWorkflowId = parentWorkflowId;
        return this;
    }

    public String getWorkflowId() {
        return workflowId;
    }

    public MessageEvent setWorkflowId(String workflowId) {
        this.workflowId = workflowId;
        return this;
    }

    public String getWorkflowName() {
        return workflowName;
    }

    public MessageEvent setWorkflowName(String workflowName) {
        this.workflowName = workflowName;
        return this;
    }

    public Long getCreatedTime() {
        return createdTime;
    }

    public MessageEvent setCreatedTime(Long createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    public MessageEvent setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class MessageEvent {\n");

        sb.append("    text: ").append(toIndentedString(text)).append("\n");
        sb.append("    card: ").append(toIndentedString(card)).append("\n");
        sb.append("    metaData: ").append(toIndentedString(metaData)).append("\n");
        sb.append("    pack: ").append(toIndentedString(pack)).append("\n");
        sb.append("    instanceId: ").append(toIndentedString(instanceId)).append("\n");
        sb.append("    cardCode: ").append(toIndentedString(cardCode)).append("\n");
        sb.append("    resourceUrl: ").append(toIndentedString(resourceUrl)).append("\n");
        sb.append("    version: ").append(toIndentedString(version)).append("\n");
        sb.append("    summary: ").append(toIndentedString(summary)).append("\n");
        sb.append("    origin: ").append(toIndentedString(origin)).append("\n");
        sb.append("    reasoningContent: ").append(toIndentedString(reasoningContent)).append("\n");
        sb.append("    original: ").append(toIndentedString(original)).append("\n");
        sb.append("    index: ").append(toIndentedString(index)).append("\n");
        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    nodeType: ").append(toIndentedString(nodeType)).append("\n");
        sb.append("    nodeName: ").append(toIndentedString(nodeName)).append("\n");
        sb.append("    isFinished: ").append(toIndentedString(isFinished)).append("\n");
        sb.append("    parentWorkflowId: ").append(toIndentedString(parentWorkflowId)).append("\n");
        sb.append("    workflowId: ").append(toIndentedString(workflowId)).append("\n");
        sb.append("    workflowName: ").append(toIndentedString(workflowName)).append("\n");
        sb.append("    createdTime: ").append(toIndentedString(createdTime)).append("\n");
        sb.append("    enableHistory: ").append(toIndentedString(enableHistory)).append("\n");
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
        MessageEvent messageEvent = (MessageEvent) o;
        return Objects.equals(this.text, messageEvent.text) && Objects.equals(this.card, messageEvent.card)
            && Objects.equals(this.metaData, messageEvent.metaData) && Objects.equals(this.pack, messageEvent.pack)
            && Objects.equals(this.instanceId, messageEvent.instanceId) && Objects.equals(this.cardCode,
            messageEvent.cardCode) && Objects.equals(this.resourceUrl, messageEvent.resourceUrl) && Objects.equals(
            this.version, messageEvent.version) && Objects.equals(this.summary, messageEvent.summary) && Objects.equals(
            this.origin, messageEvent.origin) && Objects.equals(this.reasoningContent, messageEvent.reasoningContent)
            && Objects.equals(this.original, messageEvent.original) && Objects.equals(this.index, messageEvent.index)
            && Objects.equals(this.nodeId, messageEvent.nodeId) && Objects.equals(this.nodeType, messageEvent.nodeType)
            && Objects.equals(this.nodeName, messageEvent.nodeName) && Objects.equals(this.isFinished,
            messageEvent.isFinished) && Objects.equals(this.parentWorkflowId, messageEvent.parentWorkflowId)
            && Objects.equals(this.workflowId, messageEvent.workflowId) && Objects.equals(this.workflowName,
            messageEvent.workflowName) && Objects.equals(this.createdTime, messageEvent.createdTime) && Objects.equals(
            this.enableHistory, messageEvent.enableHistory);
    }

    @Override
    public int hashCode() {
        return Objects.hash(text, card, metaData, pack, instanceId, cardCode, resourceUrl, version, summary, origin,
            reasoningContent, original, index, nodeId, nodeType, nodeName, isFinished, parentWorkflowId, workflowId,
            workflowName, createdTime, enableHistory);
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
