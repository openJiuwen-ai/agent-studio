/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.enums;

/**
 * 工作流接口事件
 *
 */
public enum WorkflowStreamEventEnum {
    WORKFLOW_STARTED,
    NODE_STARTED,
    NODE_WAIT,
    NODE_FINISHED,
    WORKFLOW_FINISHED,
    MESSAGE,
    SENSITIVE,
    ERROR,
    EXCEPTION,
    END,
    HEARTBEAT,
    KNOWLEDGE_BASE_FILES_INFO
}
