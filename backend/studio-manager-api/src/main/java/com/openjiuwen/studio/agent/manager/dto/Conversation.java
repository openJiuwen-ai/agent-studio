/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

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
 * 会话记录。
 */
@ApiModel(description = "会话记录。")

@Validated

public class Conversation implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("lastUpdateTime")
    @Schema(description = "last更新时间", example = "1")
    private Long lastUpdateTime = null;

    @JsonProperty("messageList")
    @Schema(description = "消息列表", example = "[]")
    @Valid
    @Size()
    private List<WorkflowMessage> messageList = null;

    public Long getLastUpdateTime() {
        return lastUpdateTime;
    }

    public Conversation setLastUpdateTime(Long lastUpdateTime) {
        this.lastUpdateTime = lastUpdateTime;
        return this;
    }

    public List<WorkflowMessage> getMessageList() {
        return messageList;
    }

    public Conversation setMessageList(List<WorkflowMessage> messageList) {
        this.messageList = messageList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class Conversation {\n");

        sb.append("    lastUpdateTime: ").append(toIndentedString(lastUpdateTime)).append("\n");
        sb.append("    messageList: ").append(toIndentedString(messageList)).append("\n");
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
        Conversation conversation = (Conversation) o;
        return Objects.equals(this.lastUpdateTime, conversation.lastUpdateTime) && Objects.equals(this.messageList,
            conversation.messageList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(lastUpdateTime, messageList);
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
