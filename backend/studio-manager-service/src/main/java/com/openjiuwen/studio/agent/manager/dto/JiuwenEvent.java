/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.Valid;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

@Validated
public class JiuwenEvent implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("event")
    private String event = null;

    @JsonProperty("executionId")
    private String executionId = null;

    @JsonProperty("conversationId")
    private String conversationId = null;

    @JsonProperty("createdTime")
    private Long createdTime = null;

    @JsonProperty("index")
    private Integer index = null;

    @JsonProperty("isStructMessage")
    private Boolean isStructMessage = false;

    @JsonProperty("data")
    @Valid
    private JiuwenEventData data = null;

    @JsonProperty("dataException")
    private String dataException = null;

    public String getEvent() {
        return event;
    }

    public JiuwenEvent setEvent(String event) {
        this.event = event;
        return this;
    }

    public String getExecutionId() {
        return executionId;
    }

    public JiuwenEvent setExecutionId(String executionId) {
        this.executionId = executionId;
        return this;
    }

    public String getConversationId() {
        return conversationId;
    }

    public JiuwenEvent setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public Long getCreatedTime() {
        return createdTime;
    }

    public JiuwenEvent setCreatedTime(Long createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    public Integer getIndex() {
        return index;
    }

    public JiuwenEvent setIndex(Integer index) {
        this.index = index;
        return this;
    }

    public JiuwenEvent setIsStructMessage(Boolean isStructMessage) {
        this.isStructMessage = isStructMessage;
        return this;
    }

    public Boolean isIsStructMessage() {
        return isStructMessage;
    }

    public JiuwenEventData getData() {
        return data;
    }

    public JiuwenEvent setData(JiuwenEventData data) {
        this.data = data;
        return this;
    }

    public String getDataException() {
        return dataException;
    }

    public JiuwenEvent setDataException(String dataException) {
        this.dataException = dataException;
        return this;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        JiuwenEvent jiuwenEvent = (JiuwenEvent) o;
        return Objects.equals(this.event, jiuwenEvent.event) && Objects.equals(this.executionId,
            jiuwenEvent.executionId) && Objects.equals(this.conversationId, jiuwenEvent.conversationId)
            && Objects.equals(this.createdTime, jiuwenEvent.createdTime) && Objects.equals(this.index,
            jiuwenEvent.index) && Objects.equals(this.isStructMessage, jiuwenEvent.isStructMessage) && Objects.equals(
            this.data, jiuwenEvent.data) && Objects.equals(this.dataException, jiuwenEvent.dataException);
    }

    @Override
    public int hashCode() {
        return Objects.hash(event, executionId, conversationId, createdTime, index, isStructMessage, data,
            dataException);
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class JiuwenEvent {\n");
        sb.append("    event: ").append(event).append("\n");
        sb.append("    executionId: ").append(executionId).append("\n");
        sb.append("    conversationId: ").append(conversationId).append("\n");
        sb.append("    createdTime: ").append(createdTime).append("\n");
        sb.append("    index: ").append(index).append("\n");
        sb.append("    isStructMessage: ").append(isStructMessage).append("\n");
        sb.append("    data: ").append(data).append("\n");
        sb.append("    dataException: ").append(dataException).append("\n");
        sb.append("}");
        return sb.toString();
    }
}
