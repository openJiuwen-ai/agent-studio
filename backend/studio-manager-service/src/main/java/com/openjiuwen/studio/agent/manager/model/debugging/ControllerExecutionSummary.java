/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import com.openjiuwen.studio.agent.common.dto.agent.Message;

import lombok.Getter;
import lombok.Setter;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Getter
@Setter
public class ControllerExecutionSummary {
    private String conversationId;

    private String agentId;

    private Object inputs;

    private Object outputs;

    private String executionId;

    private String query;

    private Set<String> agentNodeIds;

    private Set<String> workflowIds;

    private Long startTime;

    private Long endTime;

    private String status;

    private List<Message> messages;

    public ControllerExecutionSummary() {
        this.agentNodeIds = new HashSet<>();
        this.workflowIds = new HashSet<>();
    }

    public ControllerExecutionSummary(AgentCtrlTraceData traceData) {
        this.agentNodeIds = new HashSet<>(traceData.getLlmInvokeDataMap().keySet());
        this.workflowIds = new HashSet<>(traceData.getWorkflows().keySet());
        this.conversationId = traceData.getConversationId();
        this.agentId = traceData.getAgentId();
        this.inputs = traceData.getInputs();
        this.outputs = traceData.getOutputs();
        this.executionId = traceData.getExecutionId();
        this.startTime = traceData.getStartTime();
        this.endTime = traceData.getEndTime();
        this.status = traceData.getStatus();
    }
}
