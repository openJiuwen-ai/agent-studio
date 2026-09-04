/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.application.dto;

import lombok.Data;

/**
 * 会话列表查询
 */
@Data
public class ConversationListQuery {
    /**
     * 页码（从0开始）
     */
    private Integer page = 0;

    /**
     * 页大小
     */
    private Integer size = 20;
}
