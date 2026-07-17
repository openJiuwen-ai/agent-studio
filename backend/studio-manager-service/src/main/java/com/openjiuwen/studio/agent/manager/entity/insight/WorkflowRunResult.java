/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity.insight;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class WorkflowRunResult {
    private WorkflowInstanceEntity instance;

    private List<NodeRunInfo> nodeRunInfoList = new ArrayList<>();

    private Object workflowRunInfo;

    /**
     * 保存助手返回信息
     */
    private List<Object> messageList = new ArrayList<>();

    /**
     * 九问引擎事件（透传data）
     */
    private List<Object> eventList = new ArrayList<>();

    private boolean taskEnd;

    private boolean workflowEnd;
}
