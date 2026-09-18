/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 会话详情视图（含全部消息）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConversationDetailVo {
    /**
     * 会话唯一标识
     */
    @JsonProperty("conversation_id")
    private String conversationId;

    /**
     * 会话标题
     */
    @JsonProperty("title")
    private String title;

    /**
     * 会话状态：ACTIVE/CLOSED
     */
    @JsonProperty("status")
    private String status;

    /**
     * 全部消息（created_on 序）
     */
    @JsonProperty("messages")
    private List<MessageVo> messages;
}
