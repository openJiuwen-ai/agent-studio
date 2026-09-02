/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import com.openjiuwen.studio.agent.common.dto.agent.FeedbackReason;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.Range;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * WorkflowMessage
 */

@Validated

public class WorkflowMessage implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("role")
    @Schema(description = "消息角色", example = "user")
    @Length(min = 1, max = 64)
    private String role = null;

    @JsonProperty("content")
    @Schema(description = "消息内容", example = "你好")
    private String content = null;

    @JsonProperty("create_time")
    @Schema(description = "创建时间", example = "1700000000000")
    private Long createTime = null;

    @JsonProperty("name")
    @Schema(description = "名称")
    @Valid
    private Object name = null;

    @JsonProperty("function_call")
    @Schema(description = "函数调用")
    @Valid
    private Object functionCall = null;

    @JsonProperty("tool_calls")
    @Schema(description = "工具调用列表")
    @Valid
    private Object toolCalls = null;

    @JsonProperty("tool_call_id")
    @Schema(description = "工具调用ID")
    @Valid
    private Object toolCallId = null;

    @JsonProperty("enable_history")
    @Schema(description = "是否启用历史记录", example = "true")
    private Boolean enableHistory = null;

    @JsonProperty("intent")
    @Schema(description = "意图列表", example = "[]")
    @Valid
    @Size()
    private List<@Length() String> intent = null;

    @JsonProperty("execution_id")
    @Schema(description = "执行ID", example = "exec_001")
    private String executionId = null;

    @JsonProperty("node_id")
    @Schema(description = "节点ID", example = "node_001")
    private String nodeId = null;

    @JsonProperty("agent_id")
    @Schema(description = "智能体ID", example = "agent_001")
    private String agentId = null;

    @JsonProperty("rating")
    @Schema(description = "评分", example = "1")
    @Range(min = -1L, max = 1L)
    private Integer rating = null;

    @JsonProperty("files")
    @Schema(description = "文件列表", example = "[]")
    @Valid
    @Size()
    private List<Object> files = null;

    @JsonProperty("reason")
    @Schema(description = "反馈原因")
    @Valid
    private FeedbackReason reason = null;

    public String getRole() {
        return role;
    }

    public WorkflowMessage setRole(String role) {
        this.role = role;
        return this;
    }

    public String getContent() {
        return content;
    }

    public WorkflowMessage setContent(String content) {
        this.content = content;
        return this;
    }

    public Long getCreateTime() {
        return createTime;
    }

    public WorkflowMessage setCreateTime(Long createTime) {
        this.createTime = createTime;
        return this;
    }

    public Object getName() {
        return name;
    }

    public WorkflowMessage setName(Object name) {
        this.name = name;
        return this;
    }

    public Object getFunctionCall() {
        return functionCall;
    }

    public WorkflowMessage setFunctionCall(Object functionCall) {
        this.functionCall = functionCall;
        return this;
    }

    public Object getToolCalls() {
        return toolCalls;
    }

    public WorkflowMessage setToolCalls(Object toolCalls) {
        this.toolCalls = toolCalls;
        return this;
    }

    public Object getToolCallId() {
        return toolCallId;
    }

    public WorkflowMessage setToolCallId(Object toolCallId) {
        this.toolCallId = toolCallId;
        return this;
    }

    public WorkflowMessage setEnableHistory(Boolean enableHistory) {
        this.enableHistory = enableHistory;
        return this;
    }

    public Boolean isEnableHistory() {
        return enableHistory;
    }

    public List<String> getIntent() {
        return intent;
    }

    public WorkflowMessage setIntent(List<String> intent) {
        this.intent = intent;
        return this;
    }

    public String getExecutionId() {
        return executionId;
    }

    public WorkflowMessage setExecutionId(String executionId) {
        this.executionId = executionId;
        return this;
    }

    public String getNodeId() {
        return nodeId;
    }

    public WorkflowMessage setNodeId(String nodeId) {
        this.nodeId = nodeId;
        return this;
    }

    public String getAgentId() {
        return agentId;
    }

    public WorkflowMessage setAgentId(String agentId) {
        this.agentId = agentId;
        return this;
    }

    public Integer getRating() {
        return rating;
    }

    public WorkflowMessage setRating(Integer rating) {
        this.rating = rating;
        return this;
    }

    public List<Object> getFiles() {
        return files;
    }

    public WorkflowMessage setFiles(List<Object> files) {
        this.files = files;
        return this;
    }

    public FeedbackReason getReason() {
        return reason;
    }

    public WorkflowMessage setReason(FeedbackReason reason) {
        this.reason = reason;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowMessage {\n");

        sb.append("    role: ").append(toIndentedString(role)).append("\n");
        sb.append("    content: ").append(toIndentedString(content)).append("\n");
        sb.append("    createTime: ").append(toIndentedString(createTime)).append("\n");
        sb.append("    name: ").append(toIndentedString(name)).append("\n");
        sb.append("    functionCall: ").append(toIndentedString(functionCall)).append("\n");
        sb.append("    toolCalls: ").append(toIndentedString(toolCalls)).append("\n");
        sb.append("    toolCallId: ").append(toIndentedString(toolCallId)).append("\n");
        sb.append("    enableHistory: ").append(toIndentedString(enableHistory)).append("\n");
        sb.append("    intent: ").append(toIndentedString(intent)).append("\n");
        sb.append("    executionId: ").append(toIndentedString(executionId)).append("\n");
        sb.append("    nodeId: ").append(toIndentedString(nodeId)).append("\n");
        sb.append("    agentId: ").append(toIndentedString(agentId)).append("\n");
        sb.append("    rating: ").append(toIndentedString(rating)).append("\n");
        sb.append("    files: ").append(toIndentedString(files)).append("\n");
        sb.append("    reason: ").append(toIndentedString(reason)).append("\n");
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
        WorkflowMessage workflowMessage = (WorkflowMessage) o;
        return Objects.equals(this.role, workflowMessage.role) && Objects.equals(this.content, workflowMessage.content)
            && Objects.equals(this.createTime, workflowMessage.createTime) && Objects.equals(this.name,
            workflowMessage.name) && Objects.equals(this.functionCall, workflowMessage.functionCall) && Objects.equals(
            this.toolCalls, workflowMessage.toolCalls) && Objects.equals(this.toolCallId, workflowMessage.toolCallId)
            && Objects.equals(this.enableHistory, workflowMessage.enableHistory) && Objects.equals(this.intent,
            workflowMessage.intent) && Objects.equals(this.executionId, workflowMessage.executionId) && Objects.equals(
            this.nodeId, workflowMessage.nodeId) && Objects.equals(this.agentId, workflowMessage.agentId)
            && Objects.equals(this.rating, workflowMessage.rating) && Objects.equals(this.files, workflowMessage.files)
            && Objects.equals(this.reason, workflowMessage.reason);
    }

    @Override
    public int hashCode() {
        return Objects.hash(role, content, createTime, name, functionCall, toolCalls, toolCallId, enableHistory, intent,
            executionId, nodeId, agentId, rating, files, reason);
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
