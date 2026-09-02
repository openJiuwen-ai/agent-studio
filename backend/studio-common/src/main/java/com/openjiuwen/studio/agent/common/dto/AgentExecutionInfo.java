/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * Agent对话insight信息。
 */
@ApiModel(description = "Agent对话insight信息。")

@Validated

public class AgentExecutionInfo implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("conversation_id")
    @Schema(description = "会话ID", example = "conv-123456")
    private String conversationId = null;

    @JsonProperty("execution_id")
    @Schema(description = "执行ID", example = "exec-789012")
    private String executionId = null;

    @JsonProperty("inputs")
    @Schema(description = "输入信息", example = "{\"question\":\"你好\"}")
    private String inputs = null;

    @JsonProperty("outputs")
    @Schema(description = "输出信息", example = "{\"answer\":\"你好，有什么可以帮您？\"}")
    private String outputs = null;

    @JsonProperty("error_info")
    @Schema(description = "错误信息", example = "null")
    private String errorInfo = null;

    @JsonProperty("invoke_list")
    @Schema(description = "调用列表", example = "[]")
    @Valid
    @Size()
    private List<AgentInvokeInfo> invokeList = null;

    @JsonProperty("status")
    @Schema(description = "执行状态", example = "success")
    private String status = null;

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

    public String getConversationId() {
        return conversationId;
    }

    public AgentExecutionInfo setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public String getExecutionId() {
        return executionId;
    }

    public AgentExecutionInfo setExecutionId(String executionId) {
        this.executionId = executionId;
        return this;
    }

    public String getInputs() {
        return inputs;
    }

    public AgentExecutionInfo setInputs(String inputs) {
        this.inputs = inputs;
        return this;
    }

    public String getOutputs() {
        return outputs;
    }

    public AgentExecutionInfo setOutputs(String outputs) {
        this.outputs = outputs;
        return this;
    }

    public String getErrorInfo() {
        return errorInfo;
    }

    public AgentExecutionInfo setErrorInfo(String errorInfo) {
        this.errorInfo = errorInfo;
        return this;
    }

    public List<AgentInvokeInfo> getInvokeList() {
        return invokeList;
    }

    public AgentExecutionInfo setInvokeList(List<AgentInvokeInfo> invokeList) {
        this.invokeList = invokeList;
        return this;
    }

    public String getStatus() {
        return status;
    }

    public AgentExecutionInfo setStatus(String status) {
        this.status = status;
        return this;
    }

    public Long getStartTime() {
        return startTime;
    }

    public AgentExecutionInfo setStartTime(Long startTime) {
        this.startTime = startTime;
        return this;
    }

    public Long getEndTime() {
        return endTime;
    }

    public AgentExecutionInfo setEndTime(Long endTime) {
        this.endTime = endTime;
        return this;
    }

    public Object getMetaData() {
        return metaData;
    }

    public AgentExecutionInfo setMetaData(Object metaData) {
        this.metaData = metaData;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class AgentExecutionInfo {\n");

        sb.append("    conversationId: ").append(toIndentedString(conversationId)).append("\n");
        sb.append("    executionId: ").append(toIndentedString(executionId)).append("\n");
        sb.append("    inputs: ").append(toIndentedString(inputs)).append("\n");
        sb.append("    outputs: ").append(toIndentedString(outputs)).append("\n");
        sb.append("    errorInfo: ").append(toIndentedString(errorInfo)).append("\n");
        sb.append("    invokeList: ").append(toIndentedString(invokeList)).append("\n");
        sb.append("    status: ").append(toIndentedString(status)).append("\n");
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
        AgentExecutionInfo agentExecutionInfo = (AgentExecutionInfo) o;
        return Objects.equals(this.conversationId, agentExecutionInfo.conversationId) && Objects.equals(
            this.executionId, agentExecutionInfo.executionId) && Objects.equals(this.inputs, agentExecutionInfo.inputs)
            && Objects.equals(this.outputs, agentExecutionInfo.outputs) && Objects.equals(this.errorInfo,
            agentExecutionInfo.errorInfo) && Objects.equals(this.invokeList, agentExecutionInfo.invokeList)
            && Objects.equals(this.status, agentExecutionInfo.status) && Objects.equals(this.startTime,
            agentExecutionInfo.startTime) && Objects.equals(this.endTime, agentExecutionInfo.endTime) && Objects.equals(
            this.metaData, agentExecutionInfo.metaData);
    }

    @Override
    public int hashCode() {
        return Objects.hash(conversationId, executionId, inputs, outputs, errorInfo, invokeList, status, startTime,
            endTime, metaData);
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
