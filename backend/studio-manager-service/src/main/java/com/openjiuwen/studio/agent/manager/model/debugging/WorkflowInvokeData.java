/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.experimental.Accessors;

import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.List;

/**
 * WorkflowInvokeData
 *
 */
@Getter
@Setter
@NoArgsConstructor
@Accessors(chain = true)
public class WorkflowInvokeData {
    public WorkflowInvokeData(String workflowId) {
        this.workflowId = workflowId;
    }

    private String id;

    private String executionId;

    private String workflowId;

    private Object inputs;

    private Object outputs;

    private String errorMsg;

    private String runInfo;

    private Long startTime;

    private Long endTime;

    private List<ControllerExecutionInvokeModel> eventList = new ArrayList<>();

    public void updateProperties(NodeRunInfo nodeInfo, JiuwenEventData eventData) {
        if ("Start".equals(nodeInfo.getNodeType())) {
            this.inputs = nodeInfo.getInputs();
            this.startTime = nodeInfo.getStartTime();
            this.executionId = nodeInfo.getExecutionId();
        } else if ("End".equals(nodeInfo.getNodeType())) {
            this.outputs = nodeInfo.getOutputs();
            this.endTime = nodeInfo.getEndTime();
        }

        if (StringUtils.isNotBlank(nodeInfo.getErrorMessage())) {
            this.errorMsg = nodeInfo.getErrorMessage();
            this.endTime = nodeInfo.getEndTime();
        }

        this.eventList.add(new ControllerExecutionInvokeModel(nodeInfo, eventData));
    }
}
