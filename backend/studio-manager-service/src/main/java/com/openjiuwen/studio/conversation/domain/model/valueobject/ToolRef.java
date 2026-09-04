/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.model.valueobject;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 工具引用值对象（一行工具调用 = 一次引用）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ToolRef {
    /**
     * 工具标识，=t_tool.tool_id
     */
    private String toolId;

    /**
     * 工具调用请求参数json
     */
    private String args;
}
