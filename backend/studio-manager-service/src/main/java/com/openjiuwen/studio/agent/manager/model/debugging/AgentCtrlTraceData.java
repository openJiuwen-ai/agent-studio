/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.model.debugging.WorkflowInvokeData;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

import java.util.HashMap;
import java.util.Map;

/**
 * 多控制器调用链数据
 */
@Getter
@Setter
@NoArgsConstructor
@Accessors(chain = true)
public class AgentCtrlTraceData {
    private String conversationId;

    private String agentId;

    private String executionId;

    private Map<String, WorkflowInvokeData> workflows = new HashMap<>();

    private Map<String, ControllerExecutionInvokeModel> llmInvokeDataMap = new HashMap<>();

    private Object inputs;

    private Object outputs;

    private boolean resume;

    private boolean block;

    private Long startTime;

    private Long endTime;

    private String status;

    private JiuwenEventType preEventType;

    public void appendAgentNode(JiuwenAgentEvent event) {
        JiuwenAgentEventData eventData = event.getData();
        if (!"llm".equals(eventData.getInvokeType())) {
            return;
        }
        ControllerExecutionInvokeModel node = llmInvokeDataMap.computeIfAbsent(eventData.getInvokeId(),
            (key) -> new ControllerExecutionInvokeModel());
        node.update(eventData);
    }
}
