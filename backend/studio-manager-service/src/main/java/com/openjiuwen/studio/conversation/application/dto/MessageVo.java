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
 * 会话消息视图
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MessageVo {
    /**
     * 消息角色：user/assistant/tool
     */
    @JsonProperty("role")
    private String role;

    /**
     * 消息正文
     */
    @JsonProperty("content")
    private String content;

    /**
     * 工具标识（仅role=tool）
     */
    @JsonProperty("tool_id")
    private String toolId;

    /**
     * 工具调用请求参数json（仅role=tool）
     */
    @JsonProperty("tool_args")
    private String toolArgs;

    /**
     * 文件引用json数组
     */
    @JsonProperty("file_ids")
    private String fileIds;

    /**
     * 主轮次execution_id
     */
    @JsonProperty("execution_id")
    private String executionId;

    /**
     * 子任务分组键（子agent消息）
     */
    @JsonProperty("sub_execution_id")
    private String subExecutionId;

    /**
     * agent溯源
     */
    @JsonProperty("agent_id")
    private String agentId;

    /**
     * 终止事件
     */
    @JsonProperty("event")
    private String event;

    /**
     * 创建时间
     */
    @JsonProperty("created_at")
    private Date createdAt;
}
