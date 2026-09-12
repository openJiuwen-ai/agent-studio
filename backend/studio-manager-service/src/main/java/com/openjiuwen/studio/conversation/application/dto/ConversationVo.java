/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.application.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;

/**
 * 会话列表项
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConversationVo {
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
     * 来源
     */
    @JsonProperty("source")
    private String source;

    /**
     * 创建时间
     */
    @JsonProperty("created_at")
    private Date createdAt;

    /**
     * 更新时间（列表按此倒序）
     */
    @JsonProperty("updated_at")
    private Date updatedAt;
}
