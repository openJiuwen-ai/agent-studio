/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 会话管理参数集，workflow和agent通用
 */
@Getter
@Setter
@NoArgsConstructor
@Accessors(chain = true)
public class ConversationParams {
    /**
     * 工作流或agent id
     */
    @Schema(description = "工作流或Agent ID", example = "agent-001")
    private String id;

    @Schema(description = "用户ID", example = "user-001")
    private String userId;

    /**
     * project id
     */
    @Schema(description = "项目ID", example = "project-001")
    private String projectId;

    /**
     * 会话id
     */
    @Schema(description = "会话ID", example = "conversation-001")
    private String conversationId;

    /**
     * 版本id
     */
    @Schema(description = "版本ID", example = "v1")
    private String versionId;

    /**
     * 执行类型
     */
    @Schema(description = "执行类型", example = "stream")
    private String executeType;
}
