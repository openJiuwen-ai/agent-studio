/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.repository;

import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.model.ConversationMessage;

import java.util.List;
import java.util.Optional;

/**
 * 会话聚合仓库（领域接口，基础设施层提供 JPA 实现）
 */
public interface ConversationRepository {

    /**
     * 按会话ID查询（含全部消息）
     *
     * @param conversationId 会话ID
     * @return 会话
     */
    Optional<Conversation> findById(String conversationId);

    /**
     * 按工作空间维度查询会话列表（updated_on 倒序，分页）
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param ownerUserId 拥有者用户
     * @param page        页码（从0开始）
     * @param size        页大小
     * @return 会话列表
     */
    List<Conversation> listByOwner(String projectId, String workspaceId, String ownerUserId, int page, int size);

    /**
     * 按工作空间维度统计会话数
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param ownerUserId 拥有者用户
     * @return 会话数
     */
    long countByOwner(String projectId, String workspaceId, String ownerUserId);

    /**
     * 保存会话（创建/更新元信息）
     *
     * @param conversation 会话
     * @return 保存后的会话
     */
    Conversation save(Conversation conversation);

    /**
     * 追加消息（run/sub_run 按 ExecutionRef 拆分落库）
     *
     * @param conversationId 会话ID
     * @param messages       消息列表
     */
    void appendMessages(String conversationId, List<ConversationMessage> messages);

    /**
     * 软删除会话
     *
     * @param conversationId 会话ID
     */
    void softDelete(String conversationId);
}
