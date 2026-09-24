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
            // 子工作流节点自身的 finished 帧与 started 帧含相同关键字，
            // 仅 started 帧触发收集，避免 finished 帧再次触发产生重复空条目
            boolean subWorkflowStarted = NodeRunInfo.NodeStatusEnum.STARTED.equals(nowNode.getNodeStatus());
            // domain_objects子工作流
            if (subWorkflowStarted && isDomainObjectsNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode, ParamExtractionType.DOMAIN_OBJECTS);
                continue;
            }
            // extension_after_extraction子工作流
            if (subWorkflowStarted && isExtensionAfterExtractionNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode, ParamExtractionType.EXTENSION_AFTER_EXTRACTION);
                continue;
            }
            // extension_before_judge_quit子工作流
            if (subWorkflowStarted && isExtensionBeforeJudgeQuitNode(nowNode)) {
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
        // 从子工作流节点自身 started 帧的下一帧起，由 instructWorkFlow 扫描内部首帧
        // （原 +2 固定偏移假设子工作流 started/finished 相邻，与实际帧序不符，会跳过首帧
        // 甚至落在非内部帧上导致整段收集为空）
        int newIndex = currentIndex + 1;
        WorkFlowDTO workflow = instructWorkFlow(nodeRunInfos, newIndex, currentNode.getNodeId(),
            workflowType.name().toLowerCase(Locale.ROOT));

        if (ParamExtractionType.DOMAIN_OBJECTS.equals(workflowType)) {
            workflow.setDomainObjectName(getTrueObjectNames(currentNode.getNodeName()));
        }
        // 区间终点：instructWorkFlow 返回的终止帧前一帧 +1，即子工作流 finished 帧
        // （或无内部帧时的下一帧）
        setContextList(nodeRunInfos, currentIndex, workflow.getIndex() + 1, workflow);

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
            // 子工作流节点自身的 finished 帧与 started 帧含相同 extension_before_entry 关键字，
            // 仅 started 帧触发收集，避免 finished 帧再次触发产生重复空条目
            if (!NodeRunInfo.NodeStatusEnum.STARTED.equals(currentNode.getNodeStatus())) {
                continue;
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
        // 轮间累积的上下文变量状态：首轮由 before-entry 工作流快照初始化，
        // 之后每轮以上一轮结束时的状态为基线（下一轮"对话前"=上一轮"对话后"），
        // 避免后续轮次直接沿用 before-entry 快照导致前几轮修改变量后仍显示陈旧值
        Map<String, ContextDTO> accumulatedContext = null;
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
            accumulatedContext = processRoundContextList(round, beforeWorkflowList, accumulatedContext);
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

    /**
     * 组装单轮的上下文变量对比列表，并返回本轮结束时的变量状态（供下一轮作基线）。
     *
     * 首轮以执行前（首次进入）工作流的快照为基线；后续轮次以上一轮返回的累积状态
     * 为基线（本轮"对话前"=上一轮"对话后"），轮内工作流的修改值照常覆盖——否则某轮
     * 未修改某变量时会回退到 before-entry 快照，丢失前几轮的修改、显示陈旧值。
     *
     * @param round 待填充上下文的轮次对象
     * @param beforeWorkflowList 执行前（首次进入）工作流列表（仅首轮使用）
     * @param previousRoundContext 上一轮结束时的变量状态，首轮传 null
     * @return 本轮结束时的变量状态
     */
    private Map<String, ContextDTO> processRoundContextList(RoundDTO round, List<WorkFlowDTO> beforeWorkflowList,
        Map<String, ContextDTO> previousRoundContext) {
        Map<String, ContextDTO> contextDTOMap = new HashMap<>();
        if (previousRoundContext == null) {
            // 首轮：以执行前（首次进入）工作流的快照为基线
            mergeWorkflowContextList(beforeWorkflowList, contextDTOMap);
        } else {
            // 后续轮次：以上一轮结束状态为基线，本轮"对话前"=上一轮"对话后"
            previousRoundContext.forEach((key, previous) -> {
                ContextDTO current = copyOfContext(previous);
                current.setValueBefor(previous.getValueAfter());
                contextDTOMap.put(key, current);
            });
        }
        mergeWorkflowContextList(round.getWorkflowList(), contextDTOMap);
        round.setContextList(new ArrayList<>(contextDTOMap.values()));
        return contextDTOMap;
    }

    private void mergeWorkflowContextList(List<WorkFlowDTO> workflows, Map<String, ContextDTO> contextDTOMap) {
        if (workflows == null) {
            return;
        }
        for (WorkFlowDTO workflow : workflows) {
            if (workflow.getContextList() == null) {
                continue;
            }
            // 放入拷贝而非源对象：Map.merge 对不存在的 key 直接存入 value 引用，
            // 若直接放入源 ContextDTO，后续轮次/同轮后续工作流 merge 时的
            // setValueAfter 会原地修改该共享对象，污染 before-entry 工作流条目
            // 及已加入 roundList 的前几轮上下文（多轮场景下被最后一轮覆盖）
            workflow.getContextList().forEach((key, value) -> contextDTOMap.merge(key, copyOfContext(value),
                (existing, newValue) -> {
                    existing.setValueAfter(newValue.getValueAfter());
                    return existing;
                }));
        }
    }

    /**
     * ContextDTO 防御性拷贝（name/value_before/value_after 三字段）。
     */
    private ContextDTO copyOfContext(ContextDTO source) {
        ContextDTO copy = new ContextDTO();
        copy.setName(source.getName());
        copy.setValueBefor(source.getValueBefor());
        copy.setValueAfter(source.getValueAfter());
        return copy;
    }

    private WorkFlowDTO instructWorkFlow(List<NodeRunInfo> nodeRunInfos, int startIndex, String nodeIdFlag,
        String paramEventType) {
        WorkFlowDTO work = new WorkFlowDTO();
        work.setTiming(paramEventType);
        work.setEventList(new ArrayList<>());
        work.setContextList(new HashMap<>());
        work.setIndex(-1);
        int returnIndex;
        // 定位子工作流内部首帧：startIndex 起可能夹杂少量非内部帧，按 parent 精确匹配
        // 向后扫描，不再依赖固定帧数偏移。跳过的非内部帧不属于该子工作流的调用详情；
        // 参数提取复合图拆分产物为顺序结构（无并发兄弟节点），故此区间内不会出现
        // 需由外层单独聚合的合法交错事件——若未来复合图引入并行结构需重新审视此处
        int collectStart = findSubWorkflowFirstFrame(nodeRunInfos, startIndex, nodeIdFlag);
        if (collectStart < 0) {
            // 区间内无内部帧：保持原终止语义，外层 +1 后从 startIndex 继续处理后续事件
            work.setIndex(startIndex - 1);
            return work;
        }
        for (int index = collectStart; index < nodeRunInfos.size(); index++) {
            NodeRunInfo nowNode = nodeRunInfos.get(index);

            // 如果遇到异常，立刻终止循环，返回异常信息
            if (nowNode.getErrorMessage() != null) {
                work.getEventList().add(nowNode);
                work.setErrorMessage(nowNode.getErrorMessage());
                work.setStatus(nowNode.getStatus());
                // 错误帧位置作为区间终点，供 setContextList 读取报错前的最后快照；
                // 错误路径外层由 isErrorEventWorkflow 提前终止，不消费该 index
                work.setIndex(index);
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

    /**
     * 定位子工作流内部首帧：从 startIndex 起向后扫描，返回首个 parent_node_id 等于
     * nodeIdFlag 的帧下标；未找到返回 -1。
     *
     * 扫描区间以"下一个 nodeId 等于 nodeIdFlag 的帧"为边界，两者均标志本轮内部帧区间
     * 结束，因此区间内 parent 匹配的帧必属于本轮，不会跨轮误收；该边界不依赖固定窗口
     * 与帧数假设，边界帧序变化时仍能正确定位，避免内部帧泄漏到外层循环被误判
     * （如被 isLlmNode 识别覆盖 round 的 moduleInput/Output）。
     *
     * 边界前提的依据（区别于 ParamOutput 等原子节点 started/finished 相邻的帧序）：
     * extension_before_entry/after_extraction/domain_objects 等子工作流节点均为
     * jiuwen.workflowComposite 容器组件，引擎先执行其内部图（内部帧经同一 trace 流
     * 持续写入）再发送自身的 finished 帧，SSE 单流有序保证 finished 必晚于内部帧；
     * 三类实测帧序（对象提取/循环内子工作流/多轮恢复）均验证一致。
     */
    private int findSubWorkflowFirstFrame(List<NodeRunInfo> nodeRunInfos, int startIndex, String nodeIdFlag) {
        for (int index = startIndex; index < nodeRunInfos.size(); index++) {
            NodeRunInfo node = nodeRunInfos.get(index);
            if (nodeIdFlag.equals(node.getParentNodeId())) {
                return index;
            }
            if (nodeIdFlag.equals(node.getNodeId())) {
                // 子工作流自身的 finished 帧或下一轮同名节点的 started 帧：本轮区间结束
                return -1;
            }
        }
        return -1;
    }

    private WorkFlowDTO paramExtractionBeforeEvent(List<NodeRunInfo> nodeRunInfos, int beforeBeginIndex) {
        // 处理before事件，直到非before事件结束
        NodeRunInfo nowNode = nodeRunInfos.get(beforeBeginIndex);
        int instructIndex = beforeBeginIndex + 1;
        WorkFlowDTO workFlowDetail = instructWorkFlow(nodeRunInfos, instructIndex, nowNode.getNodeId(),
            ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT));

        // 区间终点：instructWorkFlow 返回的终止帧前一帧 +1，即子工作流 finished 帧
        setContextList(nodeRunInfos, beforeBeginIndex, workFlowDetail.getIndex() + 1, workFlowDetail);
        return workFlowDetail;
    }

    /**
     * 组装子工作流的上下文变量对比列表。
     *
     * 值（对话前）：子工作流 started 帧（startIndex）之前最近一次的记忆变量快照——
     * 全量快照由工作流开始节点等上游帧携带，子工作流自身帧仅在内部修改过记忆时才有；
     * 值（对话后）：[startIndex, endIndex] 区间内最后一次的记忆变量快照（子工作流修改
     * 记忆时会在区间内留下新快照）；区间内无快照说明子工作流未修改任何记忆变量，
     * 此时与对话前一致。原实现取 startIndex 与 startIndex+1 相邻两帧的 memory，
     * 依赖"子工作流 started/finished 相邻"的旧帧序假设，实际帧序（started→内部帧→
     * finished）下两处均取不到快照，导致上下文变量恒为空。
     *
     * @param nodeRunInfos 全部事件帧（按到达顺序）
     * @param startIndex 子工作流自身 started 帧下标
     * @param endIndex 子工作流区间终止帧下标（其 finished 帧，或无内部帧时的下一帧）
     * @param workflow 待填充上下文对比的子工作流对象
     */
    private void setContextList(List<NodeRunInfo> nodeRunInfos, int startIndex, int endIndex, WorkFlowDTO workflow) {
        workflow.setContextList(new HashMap<>());

        Map<String, Object> inputMemory = latestMemoryBefore(nodeRunInfos, startIndex - 1);
        Map<String, Object> outputMemory = latestMemoryBetween(nodeRunInfos, startIndex, endIndex);
        if (outputMemory == null) {
            // 区间内无快照：子工作流未修改记忆变量，前后一致
            outputMemory = inputMemory;
        }

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
            ContextDTO contextDTO = workflow.getContextList().get(valueKey);
            if (contextDTO == null) {
                // 子工作流新建的记忆变量：对话前无值，仅记录对话后值
                contextDTO = new ContextDTO();
                contextDTO.setName(valueKey);
                workflow.getContextList().put(valueKey, contextDTO);
            }
            contextDTO.setValueAfter(JSON.toJSONString(valueAfter, SerializerFeature.WriteMapNullValue));
        }
    }

    /**
     * 从 fromIndex（含）向下标减小方向查找最近一个携带非空 memory 快照的帧，
     * 返回其快照；找不到返回空 Map。用于确定子工作流执行前各上下文变量的最近已知值。
     */
    private Map<String, Object> latestMemoryBefore(List<NodeRunInfo> nodeRunInfos, int fromIndex) {
        for (int i = Math.min(fromIndex, nodeRunInfos.size() - 1); i >= 0; i--) {
            Map<String, Object> memory = nodeRunInfos.get(i).getMemory();
            if (memory != null && !memory.isEmpty()) {
                return memory;
            }
        }
        return new HashMap<>();
    }

    /**
     * 在 [fromIndex, toIndex] 区间内查找最后一个携带非空 memory 快照的帧，返回其快照；
     * 区间内无快照返回 null（调用方以此区分"子工作流未修改记忆变量"）。
     */
    private Map<String, Object> latestMemoryBetween(List<NodeRunInfo> nodeRunInfos, int fromIndex, int toIndex) {
        for (int i = Math.min(toIndex, nodeRunInfos.size() - 1); i >= fromIndex; i--) {
            Map<String, Object> memory = nodeRunInfos.get(i).getMemory();
            if (memory != null && !memory.isEmpty()) {
                return memory;
            }
        }
        return null;
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
        // 保留事件原始到达顺序，不按 startTime 排序。
        // 对话型工作流中结束节点的 stream 路径会提前触发，导致其 node_started 事件可能在大模型_1 之前到达，
        // 按 startTime 排序或仅保留到达顺序都无法保证结束节点在最后。
        // 将结束节点事件移到列表末尾，确保调用链中结束节点始终排在最后。
        nodeRunInfos = reorderEndNodeToEnd(nodeRunInfos);
        processOriginLoopInputs(nodeRunInfos);
        return nodeRunInfos;
    }

    /**
     * 将结束节点（End）的事件移到列表末尾，确保调用链中结束节点始终排在最后。
     * 对话型工作流中结束节点的 stream 路径会提前触发，导致其事件可能先于后续节点到达，
     * 仅保留到达顺序无法保证结束节点在最后，因此需要显式重排。
     * 重排后非结束节点保持原始相对顺序，结束节点事件也保持原始相对顺序并统一移到末尾。
     */
    private List<NodeRunInfo> reorderEndNodeToEnd(List<NodeRunInfo> nodeRunInfos) {
        List<NodeRunInfo> endNodeEvents = new ArrayList<>();
        List<NodeRunInfo> otherEvents = new ArrayList<>();
        for (NodeRunInfo node : nodeRunInfos) {
            // 仅顶层 End（parent_node_id 为空）参与沉底：子工作流、循环等嵌套段内部的
            // End 事件属于对应嵌套调用段（如参数提取折叠按 parent 收集子工作流 eventList），
            // 移到全局末尾会导致嵌套段 eventList 缺尾、调用链顺序错乱
            if (NodeType.END.getEiType().equals(node.getNodeType()) && StringUtils.isEmpty(node.getParentNodeId())) {
                endNodeEvents.add(node);
            } else {
                otherEvents.add(node);
            }
        }
        if (endNodeEvents.isEmpty()) {
            return nodeRunInfos;
        }
        otherEvents.addAll(endNodeEvents);
        return otherEvents;
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
