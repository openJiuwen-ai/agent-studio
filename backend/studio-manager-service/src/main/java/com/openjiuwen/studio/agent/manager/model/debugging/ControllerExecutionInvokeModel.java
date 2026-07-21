/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.model.debugging;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;

import lombok.Data;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

/**
 * ControllerExecutionInvokeModel
 *
 */
@Data
public class ControllerExecutionInvokeModel {
    private String invokeId;

    private String parentInvokeId;

    private String invokeType;

    private String nodeId;

    private String nodeName;

    private String nodeType;

    private Status status;

    private String nodeStatus;

    private String modelDeploymentId;

    private String parentNodeId;

    private String loopNodeId;

    private Integer loopIndex;

    private Map<String, Object> memory;

    private String errorMsg;

    private Object innerError;

    private Object input;

    private Object output;

    private Map<String, Object> metadata;

    private Long prefillTime;

    private Long startupTime;

    private Long startTime;

    private Long endTime;

    private String applicationId;

    private String applicationType;

    private String parentApplicationId;

    private String parentApplicationType;

    private String executionId;

    private String elapsedTime;

    private List<Message> messages;

    public ControllerExecutionInvokeModel() {
    }

    public ControllerExecutionInvokeModel(NodeRunInfo nodeRunInfo, JiuwenEventData eventData) {
        this.applicationId = nodeRunInfo.getAgentId();
        this.applicationType = "WORKFLOW";
        this.nodeId = nodeRunInfo.getNodeId();
        this.nodeName = nodeRunInfo.getNodeName();
        this.nodeStatus = nodeRunInfo.getNodeStatus().toString();
        this.nodeType = nodeRunInfo.getNodeType();
        this.input = nodeRunInfo.getInputs();
        this.output = nodeRunInfo.getOutputs();
        this.startTime = nodeRunInfo.getStartTime();
        this.endTime = nodeRunInfo.getEndTime();
        this.status = nodeRunInfo.getStatus();
        this.executionId = nodeRunInfo.getExecutionId();
        this.messages = nodeRunInfo.getMessages();
        this.parentNodeId = nodeRunInfo.getParentNodeId();

        this.memory = nodeRunInfo.getMemory();

        this.invokeId = eventData.getInvokeId();
        this.parentInvokeId = eventData.getParentInvokeId();
        this.metadata = nodeRunInfo.getMetadata();

        this.errorMsg = nodeRunInfo.getErrorMessage();
    }

    public void update(JiuwenAgentEventData data) {
        this.applicationId = data.getInvokeId();
        this.applicationType = "LLM";
        this.nodeId = "";
        this.nodeType = "llm";
        this.input = data.getInputs();
        this.output = data.getOutputs();
        this.elapsedTime = data.getElapsedTime();
        this.metadata = data.getMetaData();

        if (data.getStartTime() != null) {
            LocalDateTime localDateTime = LocalDateTime.parse(data.getStartTime());
            startTime = localDateTime.atZone(ZoneOffset.systemDefault()).toInstant().toEpochMilli();
        }
        if (data.getEndTime() != null) {
            LocalDateTime localDateTime = LocalDateTime.parse(data.getEndTime());
            endTime = localDateTime.atZone(ZoneOffset.systemDefault()).toInstant().toEpochMilli();
        }
    }
}
