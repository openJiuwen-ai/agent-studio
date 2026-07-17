/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;
import jakarta.validation.Valid;

import org.hibernate.validator.constraints.Length;
import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.Objects;

/**
 * 工作流执行接口流式响应体
 */
@ApiModel(description = "工作流执行接口流式响应体")

@Validated

public class WorkflowRunStreamRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("event")
    private String event = null;

    @JsonProperty("conversation_id")
    @Length(max = 32)
    private String conversationId = null;

    @JsonProperty("data")
    @Valid
    private Object data = null;

    @JsonProperty("createdTime")
    private Long createdTime = null;

    public String getEvent() {
        return event;
    }

    public WorkflowRunStreamRsp setEvent(String event) {
        this.event = event;
        return this;
    }

    public String getConversationId() {
        return conversationId;
    }

    public WorkflowRunStreamRsp setConversationId(String conversationId) {
        this.conversationId = conversationId;
        return this;
    }

    public Object getData() {
        return data;
    }

    public WorkflowRunStreamRsp setData(Object data) {
        this.data = data;
        return this;
    }

    public Long getCreatedTime() {
        return createdTime;
    }

    public WorkflowRunStreamRsp setCreatedTime(Long createdTime) {
        this.createdTime = createdTime;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class WorkflowRunStreamRsp {\n");

        sb.append("    event: ").append(toIndentedString(event)).append("\n");
        sb.append("    conversationId: ").append(toIndentedString(conversationId)).append("\n");
        sb.append("    data: ").append(toIndentedString(data)).append("\n");
        sb.append("    createdTime: ").append(toIndentedString(createdTime)).append("\n");
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
        WorkflowRunStreamRsp workflowRunStreamRsp = (WorkflowRunStreamRsp) o;
        return Objects.equals(this.event, workflowRunStreamRsp.event) && Objects.equals(this.conversationId,
            workflowRunStreamRsp.conversationId) && Objects.equals(this.data, workflowRunStreamRsp.data)
            && Objects.equals(this.createdTime, workflowRunStreamRsp.createdTime);
    }

    @Override
    public int hashCode() {
        return Objects.hash(event, conversationId, data, createdTime);
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
