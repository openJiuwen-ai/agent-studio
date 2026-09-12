/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.application.dto;

import lombok.Data;

/**
 * 创建会话命令
 */
@Data
public class ConversationCreateCmd {
    /**
     * 会话标题（为空时默认"新会话"）
     */
    private String title;

    /**
     * 来源
     */
    private String source;
}
