/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.infrastructure.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;

/**
 * 对话式工作台会话表实体
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "t_conversation")
public class ConversationEntity {
    /**
     * 会话唯一标识（uuid，=引擎conversationId）
     */
    @JsonProperty("conversation_id")
    @Id
    private String conversationId;

    /**
     * 会话标题（历史栏展示）
     */
    @JsonProperty("title")
    private String title;

    /**
     * 租户
     */
    @JsonProperty("project_id")
    private String projectId;

    /**
     * 工作空间
     */
    @JsonProperty("workspace_id")
    private String workspaceId;

    /**
     * 租户ID
     */
    @JsonProperty("domain_id")
    private String domainId;

    /**
     * 拥有者用户域
     */
    @JsonProperty("owner_domain_id")
    private String ownerDomainId;

    /**
     * 拥有者用户
     */
    @JsonProperty("owner_user_id")
    private String ownerUserId;

    /**
     * 来源
     */
    @JsonProperty("source")
    private String source;

    /**
     * 会话状态：ACTIVE/CLOSED
     */
    @JsonProperty("status")
    private String status;

    @JsonProperty("creator")
    private String creator;

    @JsonProperty("creator_id")
    private String creatorId;

    @JsonProperty("updater")
    private String updater;

    @JsonProperty("updater_id")
    private String updaterId;

    @JsonProperty("created_on")
    private Date createdOn;

    @JsonProperty("updated_on")
    private Date updatedOn;

    @JsonProperty("deleted")
    private Integer deleted;
}
