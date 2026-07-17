/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

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
    private String id;

    private String userId;

    /**
     * project id
     */
    private String projectId;

    /**
     * 会话id
     */
    private String conversationId;

    /**
     * 版本id
     */
    private String versionId;

    /**
     * 执行类型
     */
    private String executeType;
}
