/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 * 对话工作台聚合根：会话（id = conversation_id = 引擎 conversationId），聚合内包含全部消息
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Conversation {
    /**
     * 会话唯一标识（uuid，=引擎conversationId）
     */
    private String conversationId;

    /**
     * 会话标题（历史栏展示）
     */
    private String title;

    /**
     * 租户
     */
    private String projectId;

    /**
     * 工作空间
     */
    private String workspaceId;

    /**
     * 租户ID
     */
    private String domainId;

    /**
     * 拥有者用户域
     */
    private String ownerDomainId;

    /**
     * 拥有者用户
     */
    private String ownerUserId;

    /**
     * 来源
     */
    private String source;

    /**
     * 会话状态：ACTIVE/CLOSED
     */
    private String status;

    /**
     * 聚合内消息（created_on 序）
     */
    @Builder.Default
    private List<ConversationMessage> messages = new ArrayList<>();

    private Date createdAt;

    private Date updatedAt;
}
