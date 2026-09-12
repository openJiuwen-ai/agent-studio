/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.infrastructure.entity;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;

/**
 * 对话式工作台子agent消息表实体（一行 = 一条消息）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "t_conversation_sub_run")
public class ConversationSubRunEntity {
    /**
     * 代理主键
     */
    @JsonProperty("id")
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * 业务分组键（一次任务指派）
     */
    @JsonProperty("sub_execution_id")
    private String subExecutionId;

    /**
     * 所属主轮次execution_id
     */
    @JsonProperty("execution_id")
    private String executionId;

    /**
     * 会话ID
     */
    @JsonProperty("conversation_id")
    private String conversationId;

    /**
     * 被调用的子agent
     */
    @JsonProperty("agent_id")
    private String agentId;

    /**
     * 消息角色：assistant/tool
     */
    @JsonProperty("role")
    private String role;

    @JsonProperty("content")
    private String content;

    /**
     * 仅role=tool
     */
    @JsonProperty("tool_id")
    private String toolId;

    /**
     * 仅role=tool
     */
    @JsonProperty("tool_args")
    private String toolArgs;

    @JsonProperty("file_ids")
    private String fileIds;

    /**
     * 事件类型：sub_done/reasoning/message/tool_call（按轮持久化，role 区分内容）
     */
    @JsonProperty("event")
    private String event;

    @JsonProperty("total_tokens")
    private String totalTokens;

    @JsonProperty("prompt_tokens")
    private String promptTokens;

    @JsonProperty("completion_tokens")
    private String completionTokens;

    @JsonProperty("project_id")
    private String projectId;

    @JsonProperty("workspace_id")
    private String workspaceId;

    @JsonProperty("domain_id")
    private String domainId;

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
