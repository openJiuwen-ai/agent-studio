/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.debugging;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.serializer.SerializerFeature;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.manager.dto.ContextDTO;
import com.openjiuwen.studio.agent.manager.dto.RoundDTO;
import com.openjiuwen.studio.agent.manager.dto.WorkFlowDTO;
import com.openjiuwen.studio.agent.manager.enums.ParamExtractionType;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionDetailModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionInvokeModel;
import com.openjiuwen.studio.agent.manager.mapper.CtrlExecutionModelMapper;

import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * CtrlDebuggingModelProcessService
 *
 */
@Slf4j
@Service
@RequiredArgsConstructor(onConstructor_ = {@Autowired})
public class CtrlDebuggingModelProcessService {
    private static final String PARAM_EXTRACT_NODE_ID_MARK = "composite";

    private static final String PARAM_EXTRACTION = "ParamExtraction";

    private static final Predicate<ControllerExecutionInvokeModel> USEFUL_PARAM_EXTRACT_NODE_FILTER = ctrlExecNode -> {
        String nodeId = ctrlExecNode.getNodeId();
        if (nodeId.contains(PARAM_EXTRACT_NODE_ID_MARK)) {
            return ParamExtractionType.obtainParamExtractTypes().stream().anyMatch(nodeId::contains);
        }
        return true;
    };

    /**
     * filterUsefulNodes
     *
     * @param oriCtrlExecNodes oriCtrlExecNodes
     * @return List<ControllerExecutionInvokeModel>
     */
    public List<ControllerExecutionInvokeModel> filterUsefulNodes(
        List<ControllerExecutionInvokeModel> oriCtrlExecNodes) {
        if (CollectionUtils.isEmpty(oriCtrlExecNodes)) {
            return oriCtrlExecNodes;
        }
        return oriCtrlExecNodes.stream().filter(USEFUL_PARAM_EXTRACT_NODE_FILTER).collect(Collectors.toList());
    }

    /**
     * constructParamExtractNodes
     *
     * @param oriCtrlExecNodes oriCtrlExecNodes
     * @param ctrlExecModel ctrlExecModel
     * @return List<ControllerExecutionInvokeModel>
     */
    public List<ControllerExecutionInvokeModel> normalizeCtrlExecNodes(
        List<ControllerExecutionInvokeModel> oriCtrlExecNodes, ControllerExecutionDetailModel ctrlExecModel) {
        if (CollectionUtils.isEmpty(oriCtrlExecNodes)) {
            return oriCtrlExecNodes;
        }

        List<ControllerExecutionInvokeModel> normalizedCtrlExecNodes = new ArrayList<>();
        List<ControllerExecutionInvokeModel> paramExtractNodes = new ArrayList<>();

        for (ControllerExecutionInvokeModel currInvocation : oriCtrlExecNodes) {
            if (isParamExtractNode(currInvocation)) {
                paramExtractNodes.add(currInvocation);
            } else {
                normalizedCtrlExecNodes.add(currInvocation);
            }
        }

        List<ControllerExecutionInvokeModel> normalizedParamExtractNodes = normalizeParamExtractNodes(
            paramExtractNodes, ctrlExecModel);
        normalizedCtrlExecNodes.addAll(normalizedParamExtractNodes);

        return normalizedCtrlExecNodes;
    }

    private boolean isParamExtractStartNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
        if (ctrlExecInvocation == null) {
            return false;
        }
        String nodeId = ctrlExecInvocation.getNodeId();
        return nodeId.contains(ParamExtractionType.START.name().toLowerCase(Locale.ROOT)) && nodeId.contains(
            PARAM_EXTRACT_NODE_ID_MARK);
    }

    private boolean isParamExtractNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
        if (ctrlExecInvocation == null) {
            return false;
        }

        return Strings.CS.contains(ctrlExecInvocation.getNodeId(), PARAM_EXTRACT_NODE_ID_MARK) || Strings.CS.contains(
            ctrlExecInvocation.getParentNodeId(), PARAM_EXTRACT_NODE_ID_MARK);
    }

    private List<ControllerExecutionInvokeModel> normalizeParamExtractNodes(
        List<ControllerExecutionInvokeModel> oriParamExtractNodes, ControllerExecutionDetailModel ctrlExecModel) {
        Map<String, ParamExtractNode> paramExtractNodeIdMap = new HashMap<>();

        for (ControllerExecutionInvokeModel currInvocation : oriParamExtractNodes) {
            String paramExtractNodeId = obtainParamExtractNodeId(currInvocation);
            ParamExtractNode paramExtractNode = paramExtractNodeIdMap.getOrDefault(paramExtractNodeId,
                new ParamExtractNode(paramExtractNodeId));

            if (isParamExtractStartNode(currInvocation)) {
                paramExtractNode.updateStartNode(currInvocation);
                paramExtractNode.setInput(currInvocation.getInput());
            } else {
                paramExtractNode.updateFinishedNode(currInvocation);
                paramExtractNode.updateContext(currInvocation);
                paramExtractNode.updateNestedWorkflow(currInvocation);
            }

            paramExtractNodeIdMap.put(paramExtractNodeId, paramExtractNode);
        }

        List<ControllerExecutionInvokeModel> normalizedParamExtractNodes = new ArrayList<>();
        for (ParamExtractNode paramExtractNode : paramExtractNodeIdMap.values()) {
            normalizedParamExtractNodes.addAll(paramExtractNode.toNodes());
            ctrlExecModel.setNestedWorkflowIds(paramExtractNode.obtainNestedWorkflowIds());
        }
        return normalizedParamExtractNodes;
    }

    private static String obtainParamExtractNodeId(ControllerExecutionInvokeModel ctrlExecInvocation) {
        String nodeId = ctrlExecInvocation.getNodeId();
        if (Strings.CS.contains(nodeId, PARAM_EXTRACT_NODE_ID_MARK)) {
            String[] nameParts = nodeId.split("_");
            return nameParts[1] + '_' + nameParts[2];
        }

        String parentNodeId = ctrlExecInvocation.getParentNodeId();
        if (Strings.CS.contains(parentNodeId, PARAM_EXTRACT_NODE_ID_MARK)) {
            String[] nameParts = parentNodeId.split("_");
            return nameParts[1] + '_' + nameParts[2];
        }

        return nodeId;
    }

    @Data
    private static final class ParamExtractNode {
        private String nodeId;

        private String applicationId;

        private ControllerExecutionInvokeModel startNode;

        private ControllerExecutionInvokeModel finishedNode;

        private Object input;

        private Set<String> beforeEntryNodeIds = new HashSet<>();

        /**
         * key: nodeId; EXTENSION_BEFORE_ENTRY, EXTENSION_BEFORE_JUDGE_QUIT, EXTENSION_AFTER_EXTRACTION, DOMAIN_OBJECTS
         * value: matched workflow
         * */
        private Map<String, WorkFlowDTO> nestedWorkflowIdMap = new HashMap<>();

        private int roundIndex = 1;

        /**
         * key: nodeId; cycle_begin
         * value: childNodeIds; EXTENSION_BEFORE_JUDGE_QUIT, EXTENSION_AFTER_EXTRACTION, DOMAIN_OBJECTS
         */
        private Map<String, Set<String>> cycleChildNodeIdsMap = new HashMap<>();

        /**
         * key: cycle_begin nodeId
         * value: matched round
         */
        private Map<String, RoundDTO> nodeIdRoundMap = new HashMap<>();

        /**
         * key: matched invokeId
         * value: cycle_begin nodeId
         */
        private Map<String, String> cycleNodeInvokeIdMap = new HashMap<>();

        /**
         * key: cycle node invokeId
         * value: child invoke ids
         */
        private Map<String, Set<String>> cycleNodeChildInvokeIdsMap = new HashMap<>();

        private Map<String, Map<String, ContextDTO>> workflowContextMap = new HashMap<>();

        public ParamExtractNode(String nodeId) {
            this.nodeId = nodeId;
        }

        /**
         * updateStartNode
         *
         * @param ctrlExecInvocation ctrlExecInvocation
         */
        public void updateStartNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (this.startNode == null) {
                this.startNode = new ControllerExecutionInvokeModel();
            }

            this.applicationId = ctrlExecInvocation.getApplicationId();
            this.startNode.setApplicationId(ctrlExecInvocation.getApplicationId());
            this.startNode.setApplicationType("WORKFLOW");

            this.startNode.setNodeType(PARAM_EXTRACTION);
            this.startNode.setNodeStatus(NodeRunInfo.NodeStatusEnum.STARTED.toString());
            this.startNode.setMetadata(new HashMap<>());

            if (StringUtils.isBlank(this.startNode.getNodeId())) {
                this.startNode.setNodeId(obtainParamExtractNodeId(ctrlExecInvocation));
            }

            this.startNode.setNodeName(ctrlExecInvocation.getNodeName());
            this.startNode.setStartTime(ctrlExecInvocation.getStartTime());
        }

        /**
         * updateFinishedNode
         *
         * @param ctrlExecInvocation ctrlExecInvocation
         */
        public void updateFinishedNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (this.finishedNode == null) {
                this.finishedNode = new ControllerExecutionInvokeModel();
            }
            this.finishedNode.setApplicationId(this.applicationId);
            this.finishedNode.setApplicationType("WORKFLOW");

            this.finishedNode.setNodeType(PARAM_EXTRACTION);
            this.finishedNode.setNodeStatus(NodeRunInfo.NodeStatusEnum.FINISHED.toString());

            if (this.startNode != null) {
                this.finishedNode.setStartTime(this.startNode.getStartTime());
            }
            this.finishedNode.setEndTime(ctrlExecInvocation.getEndTime());

            if (StringUtils.isBlank(this.finishedNode.getNodeId())) {
                this.finishedNode.setNodeId(obtainParamExtractNodeId(ctrlExecInvocation));
            }

            this.finishedNode.setNodeStatus(NodeRunInfo.NodeStatusEnum.FINISHED.toString());
            if (this.startNode != null) {
                this.finishedNode.setNodeName(this.startNode.getNodeName());
            }

            if (StringUtils.isNotBlank(ctrlExecInvocation.getErrorMsg())) {
                this.finishedNode.setErrorMsg(ctrlExecInvocation.getErrorMsg());
                this.finishedNode.setEndTime(ctrlExecInvocation.getEndTime());
            }
        }

        /**
         * updateBeforeWorkflow
         *
         * @param ctrlExecInvocation ctrlExecInvocation
         */
        @SuppressWarnings("unchecked")
        public void updateNestedWorkflow(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (StringUtils.isNotBlank(ctrlExecInvocation.getErrorMsg())) {
                this.finishedNode.setErrorMsg(ctrlExecInvocation.getErrorMsg());
                this.finishedNode.setStatus(ctrlExecInvocation.getStatus());
                this.finishedNode.setEndTime(ctrlExecInvocation.getEndTime());

                return;
            }

            if (isRoundStartNode(ctrlExecInvocation)) {
                String initNodeId = ctrlExecInvocation.getNodeId();
                RoundDTO round = nodeIdRoundMap.get(initNodeId);
                if (round == null) {
                    round = new RoundDTO();
                    round.setIndex(roundIndex);
                    round.setWorkflowList(new ArrayList<>());
                    round.setContextList(new ArrayList<>());

                    nodeIdRoundMap.put(initNodeId, round);
                    roundIndex++;

                    cycleNodeChildInvokeIdsMap.put(ctrlExecInvocation.getInvokeId(), new HashSet<>());
                }

                cycleNodeInvokeIdMap.put(ctrlExecInvocation.getInvokeId(), initNodeId);
            }

            if (isWorkflowInitNode(ctrlExecInvocation)) {
                String initNodeId = ctrlExecInvocation.getNodeId();
                WorkFlowDTO workFlowDTO = nestedWorkflowIdMap.getOrDefault(initNodeId, new WorkFlowDTO());
                workFlowDTO.setTiming(obtainWorkflowTiming(initNodeId));

                nestedWorkflowIdMap.put(initNodeId, workFlowDTO);

                if (isParamExtractBeforeEntryNode(ctrlExecInvocation)) {
                    this.beforeEntryNodeIds.add(initNodeId);
                } else {
                    for (Map.Entry<String, Set<String>> cycleNodeChildInvokeEntry : this.cycleNodeChildInvokeIdsMap.entrySet()) {
                        String cycleBeginNodeInvokeId = cycleNodeChildInvokeEntry.getKey();

                        String cycleBeginNodeId = this.cycleNodeInvokeIdMap.get(cycleBeginNodeInvokeId);
                        if (StringUtils.isBlank(cycleBeginNodeId)) {
                            continue;
                        }

                        if (cycleNodeChildInvokeEntry.getValue().contains(ctrlExecInvocation.getParentInvokeId())) {
                            cycleNodeChildInvokeEntry.getValue().add(ctrlExecInvocation.getInvokeId());

                            Set<String> cycleChildNodeIds = this.cycleChildNodeIdsMap.get(cycleBeginNodeId);
                            if (cycleChildNodeIds == null) {
                                cycleChildNodeIds = new HashSet<>();
                            }

                            cycleChildNodeIds.add(ctrlExecInvocation.getNodeId());
                            this.cycleChildNodeIdsMap.put(cycleBeginNodeId, cycleChildNodeIds);
                        }
                    }
                }

                return;
            }

            if (isCycleLLMNode(ctrlExecInvocation)) {
                String parentInvokeId = ctrlExecInvocation.getParentInvokeId();

                Set<String> parentChildInvokeIds = this.cycleNodeChildInvokeIdsMap.getOrDefault(parentInvokeId,
                    new HashSet<>());
                parentChildInvokeIds.add(ctrlExecInvocation.getInvokeId());
                this.cycleNodeChildInvokeIdsMap.put(parentInvokeId, parentChildInvokeIds);

                String matchedCycleBeginNode = cycleNodeInvokeIdMap.get(parentInvokeId);
                if (StringUtils.isNotBlank(matchedCycleBeginNode)) {
                    RoundDTO roundDTO = nodeIdRoundMap.get(matchedCycleBeginNode);
                    if (roundDTO != null) {
                        roundDTO.setModuleInput((Map<String, Object>) ctrlExecInvocation.getInput());
                        roundDTO.setModuleOutput((Map<String, Object>) ctrlExecInvocation.getOutput());
                    }
                }

                if (ctrlExecInvocation.getOutput() != null) {
                    this.finishedNode.setOutput(ctrlExecInvocation.getOutput());
                }
            }

            if (!Strings.CS.contains(ctrlExecInvocation.getParentNodeId(), this.nodeId)) {
                return;
            }

            // EXTENSION_BEFORE_ENTRY, EXTENSION_BEFORE_JUDGE_QUIT, EXTENSION_AFTER_EXTRACTION, DOMAIN_OBJECTS等节点的子节点, 刷新对应的workflow信息
            String parentNodeId = ctrlExecInvocation.getParentNodeId();
            String workflowId = ctrlExecInvocation.getApplicationId();
            WorkFlowDTO workFlowDTO = nestedWorkflowIdMap.getOrDefault(parentNodeId, new WorkFlowDTO());

            workFlowDTO.setId(workflowId);

            if (workFlowDTO.getEventList() == null) {
                workFlowDTO.setEventList(new ArrayList<>());
            }

            workFlowDTO.getEventList().add(CtrlExecutionModelMapper.INSTANCE.toNodeRunInfo(ctrlExecInvocation));
            if (ctrlExecInvocation.getErrorMsg() != null) {
                workFlowDTO.setErrorMessage(ctrlExecInvocation.getErrorMsg());
                workFlowDTO.setStatus(ctrlExecInvocation.getStatus());
            }

            nestedWorkflowIdMap.put(parentNodeId, workFlowDTO);
        }

        private void updateContext(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (!Strings.CS.contains(ctrlExecInvocation.getNodeId(), this.nodeId)) {
                return;
            }

            if (!isWorkflowInitNode(ctrlExecInvocation)) {
                return;
            }

            String ctrlExecNodeId = ctrlExecInvocation.getNodeId();

            Map<String, ContextDTO> context = this.workflowContextMap.getOrDefault(ctrlExecNodeId, new HashMap<>());

            Map<String, Object> memories = Optional.ofNullable(ctrlExecInvocation.getMemory()).orElse(new HashMap<>());
            for (Map.Entry<String, Object> memory : memories.entrySet()) {
                String memoryKey = memory.getKey();
                Object memoryVal = replaceNoneWithEmpty(memory.getValue());

                ContextDTO contextDTO = context.get(memoryKey);
                if (contextDTO != null) {
                    contextDTO.setValueAfter(JSON.toJSONString(memoryVal, SerializerFeature.WriteMapNullValue));
                } else {
                    contextDTO = new ContextDTO();
                    contextDTO.setName(memoryKey);
                    contextDTO.setValueBefor(JSON.toJSONString(memoryVal, SerializerFeature.WriteMapNullValue));
                }
                context.put(memoryKey, contextDTO);
            }

            this.workflowContextMap.put(ctrlExecNodeId, context);
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

        /**
         * toNodes
         *
         * @return List<ControllerExecutionInvokeModel>
         */
        public List<ControllerExecutionInvokeModel> toNodes() {
            List<ControllerExecutionInvokeModel> chainNodes = new ArrayList<>();
            if (this.startNode != null) {
                chainNodes.add(this.startNode);
            }
            if (this.finishedNode != null) {
                this.finishedNode.setInput(this.input);

                List<WorkFlowDTO> workFlows = new ArrayList<>();
                for (String beforeEntryNodeId : this.beforeEntryNodeIds) {
                    if (this.nestedWorkflowIdMap.containsKey(beforeEntryNodeId)) {
                        WorkFlowDTO workFlowDTO = this.nestedWorkflowIdMap.get(beforeEntryNodeId);
                        if (this.workflowContextMap.get(beforeEntryNodeId) != null) {
                            workFlowDTO.setContextList(this.workflowContextMap.get(beforeEntryNodeId));
                        }

                        workFlows.add(workFlowDTO);
                    }
                }

                List<RoundDTO> rounds = new ArrayList<>();
                for (Map.Entry<String, RoundDTO> nodeIdRoundEntry : this.nodeIdRoundMap.entrySet()) {
                    String cycleBeginNodeId = nodeIdRoundEntry.getKey();
                    RoundDTO roundDTO = nodeIdRoundEntry.getValue();

                    Set<String> childNodeIds = cycleChildNodeIdsMap.getOrDefault(cycleBeginNodeId, new HashSet<>());
                    for (String childNodeId : childNodeIds) {
                        WorkFlowDTO childWorkflow = nestedWorkflowIdMap.get(childNodeId);
                        if (childWorkflow != null) {
                            Map<String, ContextDTO> workflowContext = this.workflowContextMap.get(childNodeId);
                            if (workflowContext != null) {
                                childWorkflow.setContextList(workflowContext);
                            }

                            roundDTO.getWorkflowList().add(childWorkflow);
                        }
                    }

                    Map<String, ContextDTO> contextDTOMap = new HashMap<>();
                    for (WorkFlowDTO workflow : roundDTO.getWorkflowList()) {
                        if (workflow.getContextList() == null) {
                            continue;
                        }
                        for (Map.Entry<String, ContextDTO> entry : workflow.getContextList().entrySet()) {
                            String key = entry.getKey();
                            ContextDTO value = entry.getValue();
                            contextDTOMap.merge(key, value, (existing, newValue) -> {
                                existing.setValueAfter(newValue.getValueAfter());
                                return existing;
                            });
                        }
                    }
                    List<ContextDTO> contextList = new ArrayList<>(contextDTOMap.values());
                    roundDTO.setContextList(contextList);

                    rounds.add(roundDTO);
                }

                Map<String, Object> metadata = new HashMap<>();
                metadata.put("workflow_list", workFlows);
                metadata.put("round_list", rounds);
                this.finishedNode.setMetadata(metadata);

                chainNodes.add(this.finishedNode);
            }
            return chainNodes;
        }

        /**
         * obtainNestWorkflowIds
         *
         * @return List<String>
         */
        public List<String> obtainNestedWorkflowIds() {
            return this.nestedWorkflowIdMap.values().stream().map(WorkFlowDTO::getId).distinct().toList();
        }

        private boolean isRoundStartNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (ctrlExecInvocation == null || StringUtils.isBlank(ctrlExecInvocation.getNodeId())) {
                return false;
            }

            return Strings.CS.contains(ctrlExecInvocation.getNodeId(),
                ParamExtractionType.CYCLE_BEGIN.name().toLowerCase(Locale.ROOT));
        }

        private boolean isWorkflowInitNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (ctrlExecInvocation == null || StringUtils.isBlank(ctrlExecInvocation.getNodeId())) {
                return false;
            }
            return Strings.CS.containsAny(ctrlExecInvocation.getNodeId(),
                ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT),
                ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT.name().toLowerCase(Locale.ROOT),
                ParamExtractionType.EXTENSION_AFTER_EXTRACTION.name().toLowerCase(Locale.ROOT),
                ParamExtractionType.DOMAIN_OBJECTS.name().toLowerCase(Locale.ROOT));
        }

        private String obtainWorkflowTiming(String nodeId) {
            if (Strings.CS.contains(nodeId,
                ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT.name().toLowerCase(Locale.ROOT))) {
                return ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT.name().toLowerCase(Locale.ROOT);
            } else if (Strings.CS.contains(nodeId,
                ParamExtractionType.EXTENSION_AFTER_EXTRACTION.name().toLowerCase(Locale.ROOT))) {
                return ParamExtractionType.EXTENSION_AFTER_EXTRACTION.name().toLowerCase(Locale.ROOT);
            } else if (Strings.CS.contains(nodeId,
                ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT))) {
                return ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT);
            } else if (Strings.CS.contains(nodeId,
                ParamExtractionType.DOMAIN_OBJECTS.name().toLowerCase(Locale.ROOT))) {
                return ParamExtractionType.DOMAIN_OBJECTS.name().toLowerCase(Locale.ROOT);
            } else {
                return StringUtils.EMPTY;
            }
        }

        private boolean isCycleLLMNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (ctrlExecInvocation == null || StringUtils.isBlank(ctrlExecInvocation.getNodeId())) {
                return false;
            }

            String ctrlExecNodeId = ctrlExecInvocation.getNodeId();
            return Strings.CS.contains(ctrlExecNodeId, PARAM_EXTRACT_NODE_ID_MARK) && Strings.CS.contains(
                ctrlExecNodeId, ParamExtractionType.LLM.name().toLowerCase(Locale.ROOT));
        }

        private boolean isParamExtractBeforeEntryNode(ControllerExecutionInvokeModel ctrlExecInvocation) {
            if (StringUtils.isBlank(ctrlExecInvocation.getNodeId())) {
                return false;
            }
            return ctrlExecInvocation.getNodeId()
                .contains(ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT));
        }
    }
}
