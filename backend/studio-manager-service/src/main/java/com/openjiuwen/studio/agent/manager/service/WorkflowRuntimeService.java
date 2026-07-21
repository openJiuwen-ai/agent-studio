/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.serializer.SerializerFeature;
import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.run.GetExecutionInsightQo;
import com.openjiuwen.studio.agent.common.dto.run.ListConversationQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListExecutionQueriesQo;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.ContextDTO;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.manager.dto.ParamExtractionIndex;
import com.openjiuwen.studio.agent.manager.dto.RoundDTO;
import com.openjiuwen.studio.agent.manager.dto.WorkFlowDTO;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.enums.ParamExtractionType;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * workflow运行面service
 *
 */
@Slf4j
@Service
public class WorkflowRuntimeService implements IWorkflowRuntimeService {
    private static final String PARAM_EXTRACTION = "ParamExtraction";

    private static final String COMPOSITE = "composite";

    private static final String JIUWEN_EXCEPTION_NODE_ID = "jiuwen_exception_node_id";

    @Autowired
    private WorkflowInstanceService workflowInstanceService;

    @Value("${workflow.max-execution-size:}")
    private Integer maxExecutionSize;

    /**
     * 处理参数提取节点的内循环
     *
     * @param nodeRunInfos    所有事件
     * @param cycleBeginIndex 内循环开始的标志位
     */
    private RoundDTO paramExtractionInCirculation(List<NodeRunInfo> nodeRunInfos, int cycleBeginIndex) {
        RoundDTO round = new RoundDTO();
        round.setWorkflowList(new ArrayList<>());
        round.setContextList(new ArrayList<>());
        round.setIndex(-1);
        for (int i = cycleBeginIndex + 2; i < nodeRunInfos.size(); i++) {
            NodeRunInfo nowNode = nodeRunInfos.get(i);
            // 执行遇见错误
            if (nowNode.getErrorMessage() != null) {
                round.setErrorNode(nowNode);
                return round;
            }
            // finish事件错误
            if (i + 1 < nodeRunInfos.size() && nodeRunInfos.get(i + 1).getErrorMessage() != null) {
                round.setErrorNode(nodeRunInfos.get(i + 1));
                return round;
            }
            // 异常事件
            if (isEndExceptionNode(nowNode)) {
                NodeRunInfo endNode = nodeRunInfos.get(i + 1);
                round.setErrorNode(endNode);
                round.setIndex(i + 1);
                break;
            }
            // 结束事件
            if (isEndNode(nowNode)) {
                round.setIndex(i + 1);
                break;
            }
            // domain_objects子工作流
            if (isDomainObjectsNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode, ParamExtractionType.DOMAIN_OBJECTS);
                continue;
            }
            // extension_after_extraction子工作流
            if (isExtensionAfterExtractionNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode, ParamExtractionType.EXTENSION_AFTER_EXTRACTION);
                continue;
            }
            // extension_before_judge_quit子工作流
            if (isExtensionBeforeJudgeQuitNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode,
                    ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT);
                continue;
            }
            // 大模型节点
            if (isLlmNode(nowNode)) {
                round.setModuleInput(nowNode.getInputs());
                round.setModuleOutput(nowNode.getOutputs());
            }
        }

        // 交互节点是否中断判定
        if (round.getIndex() == -1) {
            round.setIndex(nodeRunInfos.size() - 1);
        }
        return round;
    }

    private int processSubWorkflow(RoundDTO round, List<NodeRunInfo> nodeRunInfos, int currentIndex,
        NodeRunInfo currentNode, ParamExtractionType workflowType) {
        int newIndex = currentIndex + 2;// 直接跳到扩展子工作流的开始节点
        WorkFlowDTO workflow = instructWorkFlow(nodeRunInfos, newIndex, currentNode.getNodeId(),
            workflowType.name().toLowerCase(Locale.ROOT));

        if (ParamExtractionType.DOMAIN_OBJECTS.equals(workflowType)) {
            workflow.setDomainObjectName(getTrueObjectNames(currentNode.getNodeName()));
        }
        setContextList(nodeRunInfos, newIndex - 2, workflow);

        round.getWorkflowList().add(workflow);

        if (isErrorEventWorkflow(workflow, round, currentNode)) {
            return nodeRunInfos.size(); // 遇到异常，直接终止最外层循环
        }

        return workflow.getIndex();
    }

    private String getTrueObjectNames(String oriObjectName) {
        if (oriObjectName == null || oriObjectName.isEmpty()) {
            return "";
        }
        int index = oriObjectName.indexOf("domain_objects_");
        if (index == -1) {
            return "";
        }
        int startIndex = index + "domain_objects_".length();
        if (startIndex < oriObjectName.length()) {
            return oriObjectName.substring(startIndex);
        }
        return "";
    }

    private Boolean isErrorEventWorkflow(WorkFlowDTO workflow, RoundDTO round, NodeRunInfo nowNode) {
        if (workflow.getErrorMessage() != null) {
            nowNode.setErrorMessage(workflow.getErrorMessage());
            nowNode.setStatus(workflow.getStatus());
            round.setErrorNode(nowNode);
            return true;
        }
        return false;
    }

    /**
     * 处理参数提取节点的外循环
     *
     * @param nodeRunInfos      所有事件
     * @param startProcessIndex 外循环开始的标志位
     * @param sumName           提取节点的名字
     * @param inputs            提取节点的原始输入
     */
    private ParamExtractionIndex paramExtractionOutCirculation(List<NodeRunInfo> nodeRunInfos, int startProcessIndex,
        String sumName, Map<String, Object> inputs) {
        ParamExtractionIndex paramExtractionIndex = new ParamExtractionIndex();
        paramExtractionIndex.setIndex(-1);
        NodeRunInfo sumNode = createSumNode(nodeRunInfos, startProcessIndex, sumName,
            NodeRunInfo.NodeStatusEnum.FINISHED);

        // 处理extension_before_entry类型
        List<WorkFlowDTO> beforeWorkflowList = new ArrayList<>();
        int cycleBegin = processBeforeEntryEvents(beforeWorkflowList, nodeRunInfos, startProcessIndex, inputs, sumNode,
            paramExtractionIndex);
        // before事件异常
        if (cycleBegin == -1) {
            return paramExtractionIndex;
        }
        // 验证循环开始事件
        if (!isCycleBeginEvent(nodeRunInfos.get(cycleBegin))) {
            log.warn("before event next event is not cycle begin event !");
            finalizeResult(sumNode, inputs, nodeRunInfos, new ArrayList<>(), beforeWorkflowList, paramExtractionIndex);
            return paramExtractionIndex;
        }
        // 内循环处理
        List<RoundDTO> roundList = new ArrayList<>();
        int cycleEnd = processCirculationEvents(roundList, nodeRunInfos, cycleBegin, inputs, beforeWorkflowList,
            sumNode, paramExtractionIndex);
        if (cycleEnd == -1) {
            return paramExtractionIndex;
        }
        // 处理最终结果
        finalizeResult(sumNode, inputs, nodeRunInfos, roundList, beforeWorkflowList, paramExtractionIndex);
        return paramExtractionIndex;
    }

    private NodeRunInfo createSumNode(List<NodeRunInfo> nodeRunInfos, int startProcessIndex, String sumName,
        NodeRunInfo.NodeStatusEnum type) {
        NodeRunInfo sumNode = new NodeRunInfo();
        NodeRunInfo nowNode = nodeRunInfos.get(startProcessIndex);
        // 总节点设置名字和id
        String[] nameParts = nowNode.getNodeId().split("_");
        String nodeId = "";
        if (nameParts.length < 2) {
            log.warn("event node is illegal, nodeName: {}, oriNodeId: {}", sumName, nowNode.getNodeId());
        }
        nodeId = nameParts[1] + '_' + nameParts[2];
        sumNode.setMetadata(new HashMap<>());
        sumNode.setNodeId(nodeId);
        sumNode.setNodeStatus(type);
        sumNode.setNodeType(PARAM_EXTRACTION);
        sumNode.setNodeName(sumName);

        Status status = new Status();
        status.setCode(0);
        status.setDesc("succeeded");
        sumNode.setStatus(status);

        return sumNode;
    }

    private int processBeforeEntryEvents(List<WorkFlowDTO> beforeWorkflowList, List<NodeRunInfo> nodeRunInfos,
        int startProcessIndex, Map<String, Object> inputs, NodeRunInfo sumNode,
        ParamExtractionIndex paramExtractionIndex) {
        log.info("process before entry events start.");
        for (int beforeIndex = startProcessIndex; beforeIndex < nodeRunInfos.size(); beforeIndex++) {
            NodeRunInfo currentNode = nodeRunInfos.get(beforeIndex);

            if (!isBeforeEntryEvent(currentNode)) {
                // before_entry事件结束，循环事件开始
                startProcessIndex = beforeIndex;
                break;
            }
            // before事件直接报错
            if (hasErrorInBeforeEvent(nodeRunInfos, beforeIndex)) {
                setErrorNodeInfo(sumNode, nodeRunInfos, beforeIndex + 1, inputs, beforeWorkflowList, new ArrayList<>());
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                log.info("process before entry events finish : before event error.");
                return -1;
            }

            WorkFlowDTO newWork = paramExtractionBeforeEvent(nodeRunInfos, beforeIndex);
            beforeWorkflowList.add(newWork);
            // 如果遇见异常，直接返回总结点的结束
            if (newWork.getErrorMessage() != null) {
                setErrorNodeInfo(sumNode, nodeRunInfos, startProcessIndex - 1, inputs, beforeWorkflowList,
                    new ArrayList<>());
                sumNode.setErrorMessage(newWork.getErrorMessage());
                sumNode.setStatus(newWork.getStatus());
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                log.info("process before entry events finish : other event error.");
                return -1;
            }

            beforeIndex = newWork.getIndex();
            startProcessIndex = beforeIndex;
        }
        log.info("process before entry events finish : success.");
        return startProcessIndex;
    }

    private boolean hasErrorInBeforeEvent(List<NodeRunInfo> nodeRunInfos, int beforeIndex) {
        return beforeIndex + 1 < nodeRunInfos.size() && nodeRunInfos.get(beforeIndex + 1).getErrorMessage() != null
            && beforeIndex + 2 >= nodeRunInfos.size();
    }

    private int processCirculationEvents(List<RoundDTO> roundList, List<NodeRunInfo> nodeRunInfos,
        int startProcessIndex, Map<String, Object> inputs, List<WorkFlowDTO> beforeWorkflowList, NodeRunInfo sumNode,
        ParamExtractionIndex paramExtractionIndex) {
        for (int circulationIndex = startProcessIndex; circulationIndex < nodeRunInfos.size(); circulationIndex++) {
            NodeRunInfo currentNode = nodeRunInfos.get(circulationIndex);
            log.info("param extraction in cycle begin, event index is {}", circulationIndex);
            if (!isCycleBeginEvent(currentNode)) {
                // 一轮循环事件结束，新事件开始
                paramExtractionIndex.setIndex(circulationIndex - 1);
                break;
            }
            // cycle事件直接报错
            if (hasErrorInCycleEvent(nodeRunInfos, circulationIndex)) {
                setErrorNodeInfo(sumNode, nodeRunInfos, circulationIndex + 1, inputs, beforeWorkflowList, roundList);
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                return -1;
            }
            // 一轮循环
            RoundDTO round = paramExtractionInCirculation(nodeRunInfos, circulationIndex);
            processRoundContextList(round);
            roundList.add(round);

            if (round.getErrorNode() != null) {
                setErrorNodeInfo(sumNode, nodeRunInfos, startProcessIndex - 1, inputs, beforeWorkflowList, roundList);
                sumNode.setErrorMessage(round.getErrorNode().getErrorMessage());
                sumNode.setStatus(round.getErrorNode().getStatus());
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                return -1;
            }
            circulationIndex = round.getIndex();
        }
        return nodeRunInfos.size();
    }

    private boolean hasErrorInCycleEvent(List<NodeRunInfo> nodeRunInfos, int circulationIndex) {
        return circulationIndex + 1 < nodeRunInfos.size()
            && nodeRunInfos.get(circulationIndex + 1).getErrorMessage() != null;
    }

    private void setErrorNodeInfo(NodeRunInfo sumNode, List<NodeRunInfo> nodeRunInfos, int errorIndex,
        Map<String, Object> inputs, List<WorkFlowDTO> beforeWorkflowList, List<RoundDTO> roundList) {
        sumNode.setInputs(inputs);
        sumNode.setErrorMessage(nodeRunInfos.get(errorIndex).getErrorMessage());
        sumNode.setStartTime(nodeRunInfos.get(errorIndex).getStartTime());
        sumNode.setEndTime(nodeRunInfos.get(errorIndex).getEndTime());
        sumNode.setStatus(nodeRunInfos.get(errorIndex).getStatus());
        sumNode.getMetadata().put("workflow_list", beforeWorkflowList);
        sumNode.getMetadata().put("round_list", roundList);
    }

    private void finalizeResult(NodeRunInfo sumNode, Map<String, Object> inputs, List<NodeRunInfo> nodeRunInfos,
        List<RoundDTO> roundList, List<WorkFlowDTO> beforeWorkflowList, ParamExtractionIndex paramExtractionIndex) {
        // 是否有返回带错误的error事件
        if (!roundList.isEmpty() && roundList.get(roundList.size() - 1).getErrorNode() != null) {
            RoundDTO errorRound = roundList.get(roundList.size() - 1);
            sumNode.setErrorMessage(errorRound.getErrorNode().getErrorMessage());
            sumNode.setStatus(errorRound.getErrorNode().getStatus());
        }
        // 交互节点中断情况
        if (paramExtractionIndex.getIndex() == -1) {
            paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
        }
        // 模型输出作为round的输出
        if (!roundList.isEmpty()) {
            sumNode.setInputs(inputs);
            sumNode.setOutputs(roundList.get(roundList.size() - 1).getModuleOutput());
            sumNode.setStartTime(nodeRunInfos.get(paramExtractionIndex.getIndex()).getStartTime());
            sumNode.setEndTime(nodeRunInfos.get(paramExtractionIndex.getIndex()).getEndTime());
        }
        // 拼装workflowList和roundList到sumNode里面的metadata
        sumNode.getMetadata().put("workflow_list", beforeWorkflowList);
        sumNode.getMetadata().put("round_list", roundList);
        paramExtractionIndex.setParamFinishNode(sumNode);
    }

    private void processRoundContextList(RoundDTO round) {
        Map<String, ContextDTO> contextDTOMap = new HashMap<>();
        for (WorkFlowDTO workflow : round.getWorkflowList()) {
            if (workflow.getContextList() == null) {
                continue;
            }
            workflow.getContextList().forEach((key, value) -> contextDTOMap.merge(key, value, (existing, newValue) -> {
                existing.setValueAfter(newValue.getValueAfter());
                return existing;
            }));
        }
        List<ContextDTO> contextList = new ArrayList<>(contextDTOMap.values());
        round.setContextList(contextList);
    }

    private WorkFlowDTO instructWorkFlow(List<NodeRunInfo> nodeRunInfos, int startIndex, String nodeIdFlag,
        String paramEventType) {
        WorkFlowDTO work = new WorkFlowDTO();
        work.setTiming(paramEventType);
        work.setEventList(new ArrayList<>());
        work.setContextList(new HashMap<>());
        work.setIndex(-1);
        int returnIndex;
        for (int index = startIndex; index < nodeRunInfos.size(); index++) {
            NodeRunInfo nowNode = nodeRunInfos.get(index);

            // 如果遇到异常，立刻终止循环，返回异常信息
            if (nowNode.getErrorMessage() != null) {
                work.getEventList().add(nowNode);
                work.setErrorMessage(nowNode.getErrorMessage());
                work.setStatus(nowNode.getStatus());
                return work;
            }

            // 结束循环
            if (nowNode.getParentNodeId() == null || !nowNode.getParentNodeId().equals(nodeIdFlag)) {
                // 工作流构建完毕，设定下一个世事件的开始index，外层循环会+1，这里设置为-1
                returnIndex = index - 1;
                work.setIndex(returnIndex);
                break;
            }
            work.setId(nowNode.getAgentId());
            work.getEventList().add(nowNode);

        }
        // 交互节点中断的情况
        if (work.getIndex() == -1) {
            work.setIndex(nodeRunInfos.size() - 1);
        }
        return work;
    }

    private WorkFlowDTO paramExtractionBeforeEvent(List<NodeRunInfo> nodeRunInfos, int beforeBeginIndex) {
        // 处理before事件，直到非before事件结束
        NodeRunInfo nowNode = nodeRunInfos.get(beforeBeginIndex);
        int instructIndex = beforeBeginIndex + 2;
        WorkFlowDTO workFlowDetail = instructWorkFlow(nodeRunInfos, instructIndex, nowNode.getNodeId(),
            ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT));

        setContextList(nodeRunInfos, beforeBeginIndex, workFlowDetail);
        return workFlowDetail;
    }

    private void setContextList(List<NodeRunInfo> nodeRunInfos, int startIndex, WorkFlowDTO workflow) {
        workflow.setContextList(new HashMap<>());

        Map<String, Object> inputMemory = Optional.ofNullable(nodeRunInfos.get(startIndex).getMemory())
            .orElse(new HashMap<>());
        Map<String, Object> outputMemory = Optional.ofNullable(
                startIndex + 1 < nodeRunInfos.size() ? nodeRunInfos.get(startIndex + 1).getMemory() : null)
            .orElse(new HashMap<>());

        for (Map.Entry<String, Object> input : inputMemory.entrySet()) {
            ContextDTO contextDTO = new ContextDTO();
            String valueKey = input.getKey();
            Object valueBefore = input.getValue();
            valueBefore = replaceNoneWithEmpty(valueBefore);
            contextDTO.setName(valueKey);
            contextDTO.setValueBefor(JSON.toJSONString(valueBefore, SerializerFeature.WriteMapNullValue));
            workflow.getContextList().put(valueKey, contextDTO);
        }

        for (Map.Entry<String, Object> output : outputMemory.entrySet()) {
            String valueKey = output.getKey();
            Object valueAfter = output.getValue();
            valueAfter = replaceNoneWithEmpty(valueAfter);
            if (workflow.getContextList().get(valueKey) != null) {
                workflow.getContextList()
                    .get(valueKey)
                    .setValueAfter(JSON.toJSONString(valueAfter, SerializerFeature.WriteMapNullValue));
            }
        }
    }

    private Object replaceNoneWithEmpty(Object input) {
        if (input instanceof String) {
            return ((String) input).equals("None") ? "" : input;
        } else if (input instanceof Map) {
            @SuppressWarnings("unchecked") Map<String, Object> map = (Map<String, Object>) input;
            Map<String, Object> newMap = new HashMap<>();
            for (Map.Entry<String, Object> entry : map.entrySet()) {
                Object val = entry.getValue();
                if (val instanceof String && ((String) val).equals("None")) {
                    newMap.put(entry.getKey(), "");
                } else {
                    newMap.put(entry.getKey(), replaceNoneWithEmpty(val));
                }
            }
            return newMap;
        } else if (input instanceof List) {
            List<Object> list = new ArrayList<>();
            for (Object item : (List<?>) input) {
                list.add(replaceNoneWithEmpty(item));
            }
            return list;
        }
        return input;
    }

    @Override
    public ExecutionInfo getExecutionInsight(String projectId, String workflowId, String executionId,
        GetExecutionInsightQo getExecutionInsightQo) {
        WorkflowInstanceEntity workflowInstances = workflowInstanceService.get(executionId,
            getExecutionInsightQo.getVersion());
        if (workflowInstances == null) {
            return new ExecutionInfo();
        }
        ExecutionInfo executionInfo = workflowInstanceService.convertExecutionInfo(workflowInstances);
        // 处理异常的事件, 对每条workflow_node_message debug事件进行转换并倒叙排序
        Map<String, String> nodeIdToErrorMessage = nodeIdToErrorMessage(workflowInstances);
        List<NodeRunInfo> nodeRunInfos = getSortedNodeRunInfos(workflowInstances, nodeIdToErrorMessage);
        try {
            // 参数提取事件的特殊处理
            List<NodeRunInfo> finalNodeRunInfos = processParamsExtractionEvent(nodeRunInfos);
            executionInfo.setEventList(finalNodeRunInfos);
            setJiuwenOriginEventTime(executionInfo, finalNodeRunInfos);
        } catch (Exception e) {
            log.error("Failed to obtain debugging event", e);
            throw new AgentStudioException(StudioError.OBTAIN_DEBUG_EVENT_FAILED);
        }
        return executionInfo;
    }

    private List<NodeRunInfo> getSortedNodeRunInfos(WorkflowInstanceEntity workflowInstances,
        Map<String, String> nodeIdToErrorMessage) {
        List<NodeRunInfo> nodeRunInfos = new ArrayList<>();
        for (JiuwenEvent jiuwenEvent : workflowInstances.getEventList()) {
            if (Strings.CS.equals(jiuwenEvent.getEvent(),
                JiuwenEventType.WORKFLOW_NODE_MESSAGE.name().toLowerCase(Locale.ROOT))) {
                // 异常节点errorMessage处理
                errorNodeMessage(jiuwenEvent, nodeIdToErrorMessage);
                nodeRunInfos.add(JiuwenEventProcessor.convertNodeRunInfo(jiuwenEvent.getData()));
            }
        }
        nodeRunInfos = nodeRunInfos.stream().sorted(Comparator.comparing(NodeRunInfo::getStartTime)).toList();
        processOriginLoopInputs(nodeRunInfos);
        return nodeRunInfos;
    }

    private void processOriginLoopInputs(List<NodeRunInfo> nodeRunInfos) {
        if (nodeRunInfos.size() <= 1) {
            return;
        }
        for (int i = 1; i < nodeRunInfos.size(); i++) {
            NodeRunInfo currentNode = nodeRunInfos.get(i);
            NodeRunInfo previousNode = nodeRunInfos.get(i - 1);
            if (NodeType.LOOP.getType().equals(currentNode.getNodeType()) &&
                NodeRunInfo.NodeStatusEnum.FINISHED.equals(currentNode.getNodeStatus())) {
                currentNode.setInputs(previousNode.getInputs());
            }
        }
    }

    private Map<String, String> nodeIdToErrorMessage(WorkflowInstanceEntity workflowInstances) {
        Map<String, String> nodeIdToErrorMessage = new HashMap<>();
        for (JiuwenEvent jiuwenEvent : workflowInstances.getEventList()) {
            if (Strings.CS.equals(jiuwenEvent.getEvent(), JiuwenEventType.EXCEPTION.name().toLowerCase(Locale.ROOT))) {
                Map<String, String> dataMap = JsonUtils.json2Obj(jiuwenEvent.getDataException(),
                    new com.fasterxml.jackson.core.type.TypeReference<Map<String, String>>() {
                    });

                if (dataMap == null || dataMap.isEmpty()) {
                    continue;
                }
                String nodeId = dataMap.get(JIUWEN_EXCEPTION_NODE_ID);
                dataMap.remove(JIUWEN_EXCEPTION_NODE_ID);
                String oriMessage = JSON.toJSONString(dataMap, SerializerFeature.WriteMapNullValue);
                nodeIdToErrorMessage.put(nodeId, oriMessage);
            }
        }
        return nodeIdToErrorMessage;
    }

    private void errorNodeMessage(JiuwenEvent jiuwenEvent, Map<String, String> nodeIdToErrorMessage) {
        if (nodeIdToErrorMessage.containsKey(jiuwenEvent.getData().getComponentId())
            && JiuwenEventData.StatusEnum.ERROR.equals(jiuwenEvent.getData().getStatus())) {
            jiuwenEvent.getData()
                .getError()
                .setMessage(nodeIdToErrorMessage.get(jiuwenEvent.getData().getComponentId()));
        }
    }

    private void setJiuwenOriginEventTime(ExecutionInfo executionInfo, List<NodeRunInfo> finalNodeRunInfos) {
        if (finalNodeRunInfos.isEmpty()) {
            return;
        }
        if (executionInfo.getStartTime() == null && finalNodeRunInfos.get(0).getStartTime() != null) {
            executionInfo.setStartTime(finalNodeRunInfos.get(0).getStartTime());
        }
        int endIndex = finalNodeRunInfos.size() - 1;
        if (executionInfo.getEndTime() == null) {
            if (finalNodeRunInfos.get(endIndex).getEndTime() != null) {
                executionInfo.setEndTime(finalNodeRunInfos.get(endIndex).getEndTime());
            } else {
                executionInfo.setEndTime(finalNodeRunInfos.get(endIndex).getStartTime());
            }
        }
    }

    private boolean otherNoUseParamsExtractionEvent(NodeRunInfo node) {
        String nodeId = node.getNodeId();
        if (nodeId.contains(COMPOSITE)) {
            boolean match = Arrays.stream(ParamExtractionType.values())
                .noneMatch(type -> nodeId.contains(type.name().toLowerCase(Locale.ROOT)));
            return Arrays.stream(ParamExtractionType.values())
                .noneMatch(type -> nodeId.contains(type.name().toLowerCase(Locale.ROOT)));
        }
        return false;
    }

    private List<NodeRunInfo> processParamsExtractionEvent(List<NodeRunInfo> nodeRunInfo) {
        // 过滤参数提取事件中的无用事件
        nodeRunInfo = nodeRunInfo.stream()
            .filter(node -> !otherNoUseParamsExtractionEvent(node))
            .collect(Collectors.toList());

        List<NodeRunInfo> finalNodeRunInfos = new ArrayList<>();
        for (int index = 0; index < nodeRunInfo.size(); index++) {
            // 如果是参数提取事件，就开始做处理
            NodeRunInfo nowNode = nodeRunInfo.get(index);
            if (isStartCompositeEvent(nowNode)) {
                log.info("param extraction out cycle begin, event index is {}", index);
                // 开始节点直接加入
                index = index + 1;// 跳到对应的finish事件
                nowNode = nodeRunInfo.get(index);
                String sumName = nowNode.getNodeName();

                NodeRunInfo sumStartNode = createSumNode(nodeRunInfo, index, sumName,
                    NodeRunInfo.NodeStatusEnum.STARTED);
                finalNodeRunInfos.add(sumStartNode);

                Map<String, Object> inputs = nowNode.getInputs();
                index = index + 1; // 跳转到start的下一个事件，可能是before或者cycle事件，直接做处理
                if (index >= nodeRunInfo.size()) {
                    break;
                }
                ParamExtractionIndex paramFinishNode = paramExtractionOutCirculation(nodeRunInfo, index, sumName,
                    inputs);
                paramFinishNode.getParamFinishNode().setStartTime(nowNode.getStartTime());
                index = paramFinishNode.getIndex();
                setParamFinishNodeEndTime(paramFinishNode, nodeRunInfo);
                finalNodeRunInfos.add(paramFinishNode.getParamFinishNode());
            } else {
                finalNodeRunInfos.add(nowNode);
            }
        }
        return finalNodeRunInfos;
    }

    private void setParamFinishNodeEndTime(ParamExtractionIndex paramFinishNode, List<NodeRunInfo> nodeRunInfo) {
        int endIndex = paramFinishNode.getIndex();
        if (endIndex >= nodeRunInfo.size()) {
            endIndex = nodeRunInfo.size() - 1;
        }

        if (nodeRunInfo.get(endIndex).getEndTime() != null) {
            paramFinishNode.getParamFinishNode().setEndTime(nodeRunInfo.get(endIndex).getEndTime());
        } else {
            paramFinishNode.getParamFinishNode().setEndTime(nodeRunInfo.get(endIndex).getStartTime());
        }
    }

    @Override
    public ConversionQueries listConversationQueries(String projectId, String workflowId,
        ListConversationQueriesQo listConversationQueriesQo) {
        ConversionQueries conversionQueries = new ConversionQueries();
        // 对每条debug事件进行转换
        List<ConversationInfo> conversationInfos = workflowInstanceService.getConversationInfos(workflowId,
            listConversationQueriesQo.getVersion());
        conversionQueries.setCount(conversationInfos.size());
        conversationInfos = conversationInfos.stream()
            .filter(conversationInfo -> filterTimeRange(conversationInfo.getStartTime(),
                listConversationQueriesQo.getStartTime(), listConversationQueriesQo.getEndTime()))
            .sorted(Comparator.comparing(ConversationInfo::getStartTime).reversed())
            .toList();
        conversationInfos =
            filterAndUpdateConversations(projectId, workflowId, listConversationQueriesQo, conversationInfos);
        conversionQueries.setConversationInfos(
            CommonUtil.subList(listConversationQueriesQo.getOffset(), listConversationQueriesQo.getLimit(),
                conversationInfos));

        return conversionQueries;
    }

    @Override
    public ExecutionQueries listExecutionQueries(String projectId, String workflowId, String conversationId,
        ListExecutionQueriesQo listExecutionQueriesQo) {
        ExecutionQueries executionQueries = new ExecutionQueries();
        // 对每条debug事件进行
        List<ExecutionInfo> executionInfos = workflowInstanceService.getExecutionInfos(workflowId, conversationId,
            listExecutionQueriesQo.getVersion());
        executionQueries.setCount(executionInfos.size());
        executionInfos = executionInfos.stream()
            .filter(
                executionInfo -> filterTimeRange(executionInfo.getStartTime(), listExecutionQueriesQo.getStartTime(),
                    listExecutionQueriesQo.getEndTime()))
            .sorted(Comparator.comparing(ExecutionInfo::getStartTime).reversed())
            .toList();

        executionQueries.setExecutionInfos(
            CommonUtil.subList(listExecutionQueriesQo.getOffset(), listExecutionQueriesQo.getLimit(), executionInfos));

        return executionQueries;
    }

    private boolean filterTimeRange(Long currentTime, Long startTime, Long endTime) {
        startTime = startTime != null ? startTime : Long.MIN_VALUE;
        endTime = endTime != null ? endTime : Long.MAX_VALUE;
        return currentTime != null && currentTime >= startTime && currentTime <= endTime;
    }

    private List<ConversationInfo> filterAndUpdateConversations(String projectId, String workflowId,
        ListConversationQueriesQo listConversationQueriesQo, List<ConversationInfo> conversationInfos) {
        ListExecutionQueriesQo queriesQo = new ListExecutionQueriesQo();
        queriesQo.setStartTime(listConversationQueriesQo.getStartTime())
            .setEndTime(listConversationQueriesQo.getEndTime())
            .setOffset(0)
            .setLimit(maxExecutionSize)
            .setVersion(listConversationQueriesQo.getVersion());
        List<ConversationInfo> result = new ArrayList<>();
        for (ConversationInfo info : conversationInfos) {
            ExecutionQueries executionQueries =
                listExecutionQueries(projectId, workflowId, info.getConversationId(), queriesQo);
            if (executionQueries.getCount() > 0) {
                result.add(info);
                info.setSuccessCount(0).setFailureCount(0);
                for (ExecutionInfo executionInfo : executionQueries.getExecutionInfos()) {
                    if (StringUtils.isEmpty(executionInfo.getStatus()) || Objects.equals(executionInfo.getStatus(),
                        WorkflowRunStatus.SUCCEEDED.getStatus().getDesc())) {
                        info.setSuccessCount(info.getSuccessCount() + 1);
                    } else {
                        info.setFailureCount(info.getFailureCount() + 1);
                    }
                }
            }
        }
        log.info("workflow conversations with id: {}, total: {}, valid: {}", workflowId, conversationInfos.size(),
            result.size());
        return result;
    }

    private boolean isEndExceptionNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.END_EXCEPTION.name().toLowerCase(Locale.ROOT));
    }

    private boolean isEndNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.END.name().toLowerCase(Locale.ROOT)) && node.getNodeId()
            .contains(COMPOSITE);
    }

    private boolean isDomainObjectsNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.DOMAIN_OBJECTS.name().toLowerCase(Locale.ROOT));
    }

    private boolean isExtensionAfterExtractionNode(NodeRunInfo node) {
        return node.getNodeId()
            .contains(ParamExtractionType.EXTENSION_AFTER_EXTRACTION.name().toLowerCase(Locale.ROOT));
    }

    private boolean isExtensionBeforeJudgeQuitNode(NodeRunInfo node) {
        return node.getNodeId()
            .contains(ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT.name().toLowerCase(Locale.ROOT));
    }

    private boolean isLlmNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.LLM.name().toLowerCase(Locale.ROOT));
    }

    private boolean isBeforeEntryEvent(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT));
    }

    private boolean isCycleBeginEvent(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.CYCLE_BEGIN.name().toLowerCase(Locale.ROOT));
    }

    private boolean isStartCompositeEvent(NodeRunInfo node) {
        return node.getNodeId() != null && node.getNodeId()
            .contains(ParamExtractionType.START.name().toLowerCase(Locale.ROOT)) && node.getNodeId()
            .contains(COMPOSITE);
    }
}
