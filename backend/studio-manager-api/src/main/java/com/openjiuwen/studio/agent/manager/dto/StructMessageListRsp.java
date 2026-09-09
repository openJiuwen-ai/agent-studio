/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.annotations.ApiModel;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import org.springframework.validation.annotation.Validated;

import java.io.Serializable;
import java.util.List;
import java.util.Objects;

/**
 * 查询结构化信息列表返回体
 */
@ApiModel(description = "查询结构化信息列表返回体")

@Validated

public class StructMessageListRsp implements Serializable {
    private static final long serialVersionUID = 1L;

    @JsonProperty("count")
    @Schema(description = "数量", example = "1", required = true)
    @NotNull
    private Long count = null;

    @JsonProperty("message_list")
    @Schema(description = "消息", example = "[]")
    @Valid
    @Size()
    private List<StructMessage> messageList = null;

    public Long getCount() {
        return count;
    }

    public StructMessageListRsp setCount(Long count) {
        this.count = count;
        return this;
    }

    public List<StructMessage> getMessageList() {
        return messageList;
    }

    public StructMessageListRsp setMessageList(List<StructMessage> messageList) {
        this.messageList = messageList;
        return this;
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("class StructMessageListRsp {\n");

        sb.append("    count: ").append(toIndentedString(count)).append("\n");
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
        StructMessageListRsp structMessageListRsp = (StructMessageListRsp) o;
        return Objects.equals(this.count, structMessageListRsp.count) && Objects.equals(this.messageList,
            structMessageListRsp.messageList);
    }

    @Override
    public int hashCode() {
        return Objects.hash(count, messageList);
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
