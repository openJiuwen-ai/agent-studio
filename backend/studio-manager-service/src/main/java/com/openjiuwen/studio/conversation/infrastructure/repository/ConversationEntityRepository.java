/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.infrastructure.repository;

import com.openjiuwen.studio.conversation.infrastructure.entity.ConversationEntity;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

/**
 * 会话表 JPA 仓库
 */
public interface ConversationEntityRepository extends JpaRepository<ConversationEntity, String> {

    /**
     * 按工作空间维度查询未删除会话，updated_on 倒序分页
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param ownerUserId 拥有者用户
     * @param deleted     逻辑删除标记
     * @param pageable    分页
     * @return 会话列表
     */
    List<ConversationEntity> findByProjectIdAndWorkspaceIdAndOwnerUserIdAndDeletedOrderByUpdatedOnDesc(
        String projectId, String workspaceId, String ownerUserId, Integer deleted, Pageable pageable);

    /**
     * 按工作空间维度统计会话数
     *
     * @param projectId   租户
     * @param workspaceId 工作空间
     * @param ownerUserId 拥有者用户
     * @param deleted     逻辑删除标记
     * @return 会话数
     */
    long countByProjectIdAndWorkspaceIdAndOwnerUserIdAndDeleted(
        String projectId, String workspaceId, String ownerUserId, Integer deleted);
}
