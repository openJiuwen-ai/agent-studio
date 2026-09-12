/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.conversation.domain.model.valueobject;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 执行上下文值对象（消息归属）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExecutionRef {
    /**
     * 主轮次 execution_id（=引擎execution_id）
     */
    private String executionId;

    /**
     * 子任务分组键（子 agent 消息必填，主 agent 消息为空）
     */
    private String subExecutionId;

    /**
     * agent 溯源（主 agent 或子 agent）
     */
    private String agentId;
}
