/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.infrastructure.repository;

import com.openjiuwen.studio.conversation.infrastructure.entity.ConversationRunEntity;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

/**
 * 主agent消息表 JPA 仓库
 */
public interface ConversationRunEntityRepository extends JpaRepository<ConversationRunEntity, Long> {

    /**
     * 按会话查询未删除消息，created_on 升序（同时间按 id 升序保证稳定）
     *
     * @param conversationId 会话ID
     * @param deleted        逻辑删除标记
     * @return 消息列表
     */
    List<ConversationRunEntity> findByConversationIdAndDeletedOrderByCreatedOnAscIdAsc(
        String conversationId, Integer deleted);
}
