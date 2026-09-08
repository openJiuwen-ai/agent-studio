/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * JiuwenAgentEvent
 */

@Validated

public class JiuwenAgentEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("event")
    @Schema(description = "事件类型", example = "message")
    private String event = null;

    @JsonProperty("executionId")
    @Schema(description = "执行ID", example = "exec_001")
    private String executionId = null;

    @JsonProperty("conversationId")
    @Schema(description = "会话ID", example = "conv_001")
    private String conversationId = null;

    @JsonProperty("createdTime")
    @Schema(description = "创建时间戳", example = "1717200000000")
    private Long createdTime = null;

    @JsonProperty("index")
    @Schema(description = "事件索引", example = "0")
    private Integer index = null;

    @JsonProperty("isStructMessage")
    @Schema(description = "是否为结构化消息", example = "false")
    private Boolean isStructMessage = false;

    @JsonProperty("data")
    @Schema(description = "事件数据", example = "{}")
    @Valid
    private JiuwenAgentEventData data = null;

    public String getEvent() {
        return event;
    }

    public JiuwenAgentEvent setEvent(String event) {
        this.event = event;
        return this;
    }

    public String getExecutionId() {
        return executionId;
    }

    public JiuwenAgentEvent setExecutionId(String executionId) {
        this.executionId = executionId;
        return this;
    }

    public String getConversationId() {
        return conversationId;
    }

    public JiuwenAgentEvent setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public Long getCreatedTime() {
        return createdTime;
    }

    public JiuwenAgentEvent setCreatedTime(Long createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    public Integer getIndex() {
        return index;
    }

    public JiuwenAgentEvent setIndex(Integer index) {
        this.index = index;
        return this;
    }

    public JiuwenAgentEvent setIsStructMessage(Boolean isStructMessage) {
        this.isStructMessage = isStructMessage;
        return this;
    }

    public Boolean isIsStructMessage() {
        return isStructMessage;
    }

    public JiuwenAgentEventData getData() {
        return data;
    }

    public JiuwenAgentEvent setData(JiuwenAgentEventData data) {
        this.data = data;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class JiuwenAgentEvent {\n");

        sb.append("    event: ").append(toIndentedString(event)).append("\n");
        sb.append("    executionId: ").append(toIndentedString(executionId)).append("\n");
        sb.append("    conversationId: ").append(toIndentedString(conversationId)).append("\n");
        sb.append("    createdTime: ").append(toIndentedString(createdTime)).append("\n");
        sb.append("    index: ").append(toIndentedString(index)).append("\n");
        sb.append("    isStructMessage: ").append(toIndentedString(isStructMessage)).append("\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
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
        JiuwenAgentEvent jiuwenAgentEvent = (JiuwenAgentEvent) o;
        return Objects.equals(this.event, jiuwenAgentEvent.event) && Objects.equals(this.executionId,
            jiuwenAgentEvent.executionId) && Objects.equals(this.conversationId, jiuwenAgentEvent.conversationId)
            && Objects.equals(this.createdTime, jiuwenAgentEvent.createdTime) && Objects.equals(this.index,
            jiuwenAgentEvent.index) && Objects.equals(this.isStructMessage, jiuwenAgentEvent.isStructMessage)
            && Objects.equals(this.data, jiuwenAgentEvent.data);
    }

    @Override
    public int hashCode() {
        return Objects.hash(event, executionId, conversationId, createdTime, index, isStructMessage, data);
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
