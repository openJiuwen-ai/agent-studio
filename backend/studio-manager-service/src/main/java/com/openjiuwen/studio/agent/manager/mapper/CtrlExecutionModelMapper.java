/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.mapper;

import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.run.ControllerExecution;
import com.openjiuwen.studio.agent.manager.dto.ControllerExecutionDetail;
import com.openjiuwen.studio.agent.manager.dto.ControllerInvokeInfo;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBaseData;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionBriefModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionDetailModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionInvokeModel;

import org.apache.commons.lang3.Strings;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.Named;
import org.mapstruct.factory.Mappers;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * CtrlExecutionModelMapper
 *
 */
@Mapper
public interface CtrlExecutionModelMapper {
    /**
     * INSTANCE
     */
    CtrlExecutionModelMapper INSTANCE = Mappers.getMapper(CtrlExecutionModelMapper.class);

    /**
     * toCtrlExecInvokeModel
     *
     * @param node node
     * @param event event
     * @return ControllerExecutionInvokeModel
     */
    @Mapping(target = "invokeId", source = "event.invokeId")
    @Mapping(target = "parentInvokeId", source = "event.parentInvokeId")
    @Mapping(target = "invokeType", ignore = true)
    @Mapping(target = "nodeId", source = "node.nodeId")
    @Mapping(target = "nodeName", source = "node.nodeName")
    @Mapping(target = "nodeType", source = "node.nodeType")
    @Mapping(target = "status", source = "node.status")
    @Mapping(target = "nodeStatus", source = "node.nodeStatus")
    @Mapping(target = "modelDeploymentId", ignore = true)
    @Mapping(target = "parentNodeId", source = "node.parentNodeId")
    @Mapping(target = "loopNodeId", source = "node.loopNodeId")
    @Mapping(target = "loopIndex", source = "node.loopIndex")
    @Mapping(target = "memory", source = "node.memory")
    @Mapping(target = "errorMsg", source = "node.errorMessage")
    @Mapping(target = "innerError", source = "node.innerError")
    @Mapping(target = "input", source = "node.inputs")
    @Mapping(target = "output", source = "node.outputs")
    @Mapping(target = "metadata", source = "node.metadata")
    @Mapping(target = "prefillTime", source = "node.prefillTime")
    @Mapping(target = "startupTime", source = "node.startupTime")
    @Mapping(target = "startTime", source = "node.startTime")
    @Mapping(target = "endTime", source = "node.endTime")
    @Mapping(target = "applicationId", source = "node.agentId")
    @Mapping(target = "applicationType", constant = "WORKFLOW")
    @Mapping(target = "parentApplicationId", source = "node.parentWorkflowId")
    @Mapping(target = "parentApplicationType", ignore = true)
    ControllerExecutionInvokeModel toCtrlExecInvokeModel(NodeRunInfo node, JiuwenEventData event);

    /**
     * toNodeRunInfo
     *
     * @param ctrlExecInvocation ctrlExecInvocation
     * @return NodeRunInfo
     */
    @Mapping(target = "agentId", source = "applicationId")
    @Mapping(target = "nodeId", source = "nodeId")
    @Mapping(target = "parentNodeId", source = "parentNodeId")
    @Mapping(target = "nodeStatus", source = "nodeStatus")
    @Mapping(target = "parentWorkflowId", source = "parentApplicationId")
    @Mapping(target = "loopIndex", ignore = true)
    @Mapping(target = "loopNodeId", ignore = true)
    @Mapping(target = "status", source = "status")
    @Mapping(target = "nodeName", source = "nodeName")
    @Mapping(target = "nodeType", source = "nodeType")
    @Mapping(target = "errorMessage", source = "errorMsg")
    @Mapping(target = "inputs", source = "input", qualifiedByName = "toMap")
    @Mapping(target = "outputs", source = "output", qualifiedByName = "toMap")
    @Mapping(target = "messages", source = "messages")
    @Mapping(target = "metadata", source = "metadata")
    @Mapping(target = "startTime", source = "startTime")
    @Mapping(target = "endTime", source = "endTime")
    @Mapping(target = "executionId", source = "executionId")
    @Mapping(target = "startupTime", source = "startupTime")
    @Mapping(target = "prefillTime", source = "prefillTime")
    @Mapping(target = "innerError", ignore = true)
    @Mapping(target = "memory", source = "memory")
    NodeRunInfo toNodeRunInfo(ControllerExecutionInvokeModel ctrlExecInvocation);

    @Named("toMap")
    @SuppressWarnings("unchecked")
    default Map<String, Object> toMap(Object object) {
        if (object instanceof Map) {
            return (Map<String, Object>) object;
        }
        return Collections.emptyMap();
    }

    /**
     * toNodeStatus
     *
     * @param nodeStatus nodeStatus
     * @return NodeRunInfo.NodeStatusEnum
     */
    default NodeRunInfo.NodeStatusEnum toNodeStatus(String nodeStatus) {
        for (NodeRunInfo.NodeStatusEnum nodeStatusEnum : NodeRunInfo.NodeStatusEnum.values()) {
            if (Strings.CS.equals(nodeStatus, nodeStatusEnum.toString())) {
                return nodeStatusEnum;
            }
        }
        return NodeRunInfo.NodeStatusEnum.FINISHED;
    }

    /**
     * toCtrlExecBriefModel
     *
     * @param ctrlExecDetail ctrlExecDetail
     * @return ControllerExecutionBriefModel
     */
    @Mapping(target = "executionId", source = "executionId")
    @Mapping(target = "query", source = "query")
    @Mapping(target = "status", source = "status")
    @Mapping(target = "error", source = "error")
    @Mapping(target = "startTime", source = "startTime")
    ControllerExecutionBriefModel toCtrlExecBriefModel(ControllerExecutionDetailModel ctrlExecDetail);

    /**
     * toCtrlExecDetail
     *
     * @param controllerExecutionDetailModel controllerExecutionDetailModel
     * @return ControllerExecutionDetail
     */
    @Mapping(target = "conversationId", source = "conversationId")
    @Mapping(target = "executionId", source = "executionId")
    @Mapping(target = "inputs", source = "input")
    @Mapping(target = "outputs", source = "output")
    @Mapping(target = "errorInfo", source = "error")
    @Mapping(target = "status", source = "status")
    @Mapping(target = "startTime", source = "startTime")
    @Mapping(target = "endTime", source = "endTime")
    @Mapping(target = "invocations", source = "invocations")
    @Mapping(target = "nestedWorkflows", source = "nestedWorkflowIds")
    ControllerExecutionDetail toCtrlExecDetail(ControllerExecutionDetailModel controllerExecutionDetailModel);

    /**
     * toWorkflowBaseData
     *
     * @param workflowId workflowId
     * @return WorkflowBaseData
     */
    default WorkflowBaseData toWorkflowBaseData(String workflowId) {
        WorkflowBaseData workflowBaseData = new WorkflowBaseData();
        workflowBaseData.setFlowId(workflowId);
        return workflowBaseData;
    }

    /**
     * toCtrlInvokeInfo
     *
     * @param controllerExecutionInvokeModel controllerExecutionInvokeModel
     * @return ControllerInvokeInfo
     */
    @Mapping(target = "invokeId", source = "invokeId")
    @Mapping(target = "parentInvokeId", source = "parentInvokeId")
    @Mapping(target = "nodeId", source = "nodeId")
    @Mapping(target = "nodeName", source = "nodeName")
    @Mapping(target = "nodeType", source = "nodeType")
    @Mapping(target = "nodeStatus", source = "nodeStatus")
    @Mapping(target = "parentNodeId", source = "parentNodeId")
    @Mapping(target = "modelDeploymentId", source = "modelDeploymentId")
    @Mapping(target = "errorMessage", source = "errorMsg")
    @Mapping(target = "status", source = "status")
    @Mapping(target = "inputs", source = "input")
    @Mapping(target = "outputs", source = "output")
    @Mapping(target = "startTime", source = "startTime")
    @Mapping(target = "endTime", source = "endTime")
    @Mapping(target = "messages", source = "messages")
    @Mapping(target = "metadata", source = "metadata")
    @Mapping(target = "applicationId", source = "applicationId")
    @Mapping(target = "applicationType", source = "applicationType")
    @Mapping(target = "parentApplicationId", source = "parentApplicationId")
    ControllerInvokeInfo toCtrlInvokeInfo(ControllerExecutionInvokeModel controllerExecutionInvokeModel);

    /**
     * toCtrlExecs
     *
     * @param controllerExecutionBriefModels controllerExecutionBriefModels
     * @return List<ControllerExecution>
     */
    List<ControllerExecution> toCtrlExecs(List<ControllerExecutionBriefModel> controllerExecutionBriefModels);

    /**
     * toCtrlExec
     *
     * @param controllerExecutionBriefModel controllerExecutionBriefModel
     * @return ControllerExecution
     */
    @Mapping(target = "executionId", source = "executionId")
    @Mapping(target = "query", source = "query")
    @Mapping(target = "status", source = "status")
    @Mapping(target = "errorInfo", source = "error")
    @Mapping(target = "startTime", source = "startTime")
    ControllerExecution toCtrlExec(ControllerExecutionBriefModel controllerExecutionBriefModel);
}
