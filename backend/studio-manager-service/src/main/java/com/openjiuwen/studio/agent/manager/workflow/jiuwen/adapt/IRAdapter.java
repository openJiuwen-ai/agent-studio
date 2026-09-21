/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.BranchConfig;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * IR转换适配器
 *
 */
@Slf4j
public class IRAdapter {
    private static final Map<String, AbstractIRNodeAdapter> IR_NODE_ADAPTER_MAP = new HashMap<>();

    private static final IREdgeAdapter IR_EDGE_ADAPTER = new IREdgeAdapter();

    static {
        IR_NODE_ADAPTER_MAP.put(NodeType.START.getType(), new StartNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.LLM.getType(), new LLMNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.CODE.getType(), new CodeNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.BRANCH.getType(), new BranchNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.END.getType(), new EndNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.MESSAGE.getType(), new MessageNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.INTENT_DETECTION.getType(), new IntentDetectionNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.QUESTIONER.getType(), new QuestionerNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.PLUGIN.getType(), new PluginNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.KNOWLEDGE_REPO.getType(), new KnowledgeRepoNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.TASK_FLOW.getType(), new TaskFlowNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.INPUT.getType(), new InputNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.AGGREGATION.getType(), new AggregationNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.WORKFLOW.getType(), new WorkflowNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.LOOP.getType(), new LoopNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.SET_VARIABLE.getType(), new SetVariableNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.HTTP.getType(), new HttpNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.AGENT.getType(), new AgentNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.MCP.getType(), new McpNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.LTM.getType(), new LTMNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.QA.getType(), new QaNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.DATA_ACQUISITION.getType(), new McpNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.DATA_PROCESS.getType(), new McpNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.DATA_SYNTHESIS.getType(), new McpNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.EMPTY.getType(), new EmptyNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.STRUCTURED_MESSAGES_EXCEPTION.getType(), new StructuredMessagesNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.PARAM_EXTRACTION.getType(), new ParamExtractionAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.PARAM_OUT.getType(), new ParamOutputAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.STREAM_TRANSFORM.getType(), new StreamTransformNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.SQL.getType(), new SqlNodeAdapter());
        IR_NODE_ADAPTER_MAP.put(NodeType.DATA_QUERY.getType(), new SqlNodeAdapter());
    }

    // 对于引用意图容器节点的参数，映射为意图节点
    private static void replaceFieldRefNode(WorkflowNodeVO node, Map<String, String> nodePairReverses) {
        if (nodePairReverses == null || nodePairReverses.isEmpty() || CollectionUtils.isEmpty(node.getInputs())) {
            return;
        }

        // 字段名
        String fieldRefNode = CommonConstant.Workflow.REF_NODE_ID;

        for (WorkflowFieldVO field : node.getInputs()) {
            if (Objects.isNull(field) || Objects.isNull(field.getValue())
                || Objects.isNull(field.getValue().getType())) {
                continue;
            }

            if (WorkflowFieldVOValue.TypeEnum.REF.equals(field.getValue().getType())) {
                Map<String, String> content = JsonUtils.objectToClass(field.getValue().getContent());
                if (StringUtils.isNotEmpty(content.get(fieldRefNode))
                    && nodePairReverses.containsKey(content.get(fieldRefNode))) {
                    content.put(fieldRefNode, nodePairReverses.get(content.get(fieldRefNode)));
                    field.getValue().setContent(content);
                }
            }
        }
    }

    /**
     * 适配组件
     *
     * @param nodes 工作流节点列表
     * @return 适配后的组件结果列表
     */
    public List<Map<String, Object>> adaptComponents(List<WorkflowNodeVO> nodes, Map<String, String> nodePair) {
        log.info("begin adapt nodes.");
        try {
            // 提取节点id，和节点的映射
            Map<String, WorkflowNodeVO> nodeMap = Objects.isNull(nodePair) ? null : nodes.stream()
                .collect(Collectors.toMap(WorkflowNodeVO::getId, node -> node, (existing, replacement) -> replacement));

            // 翻转高级意图和意图转换的id，便于后续的映射
            Map<String, String> nodePairReverses = Objects.isNull(nodePair) ? null
                : nodePair.entrySet().stream().collect(Collectors.toMap(Map.Entry::getValue, Map.Entry::getKey));
            List<Map<String, Object>> results = new ArrayList<>();
            for (WorkflowNodeVO node : nodes) {
                log.info("begin adapt node id:{}, node type:{}.", node.getId(), node.getType());

                replaceFieldRefNode(node, nodePairReverses);

                // 判断节点引用意图节点转换id
                if (node.getType().equals(NodeType.BRANCH.getType())) {
                    replaceFieldBranchRefNode(node, nodePairReverses);
                }

                // 意图容器节点合并，不单独展示
                if (node.getType().equals(NodeType.INTENT_DETECTION_CONTAINER.getType())) {
                    continue;
                }

                // 高级意图节点转换
                if (node.getType().equals(NodeType.INTENT_COMPLEX_INTENT.getType())) {
                    WorkflowNodeVO workflowNodeVO = new WorkflowNodeVO();
                    if (!Objects.isNull(nodePair) && nodePair.containsKey(node.getId())) {
                        workflowNodeVO = nodeMap.getOrDefault(nodePair.get(node.getId()), new WorkflowNodeVO());
                    }
                    results.add(new EIComplexIntentNodeAdapter().adapt(node, workflowNodeVO));
                    continue;
                }

                results.add(IR_NODE_ADAPTER_MAP.get(node.getType()).adapt(node));

                log.info("adapt node id:{}, node type:{} succeed.", node.getId(), node.getType());
            }
            return results;
        } catch (AgentStudioException e) {
            log.error("parse components failed!", e);
            throw e;
        } catch (Exception e) {
            log.error("parse components failed!", e);
            throw new AgentStudioException(StudioError.CONVERT_NODE_FAILED);
        }
    }

    private void replaceFieldBranchRefNode(WorkflowNodeVO node, Map<String, String> nodePairReverses) {
        for (WorkflowBranchVO branch : node.getBranches()) {
            if (branch.getConfigs() == null) {
                continue;
            }
            BranchConfig config = JsonUtils.objectToClassType(branch.getConfigs(), BranchConfig.class);
            if (config == null) {
                continue;
            }

            // 字段名
            String fieldRefNode = CommonConstant.Workflow.REF_NODE_ID;

            for (BranchConfig.Condition condition : config.getConditions()) {
                // 处理left
                WorkflowFieldVOValue leftValue = condition.getLeft() != null ? condition.getLeft().getValue() : null;
                replaceRefNodeIdInConditionField(leftValue, nodePairReverses, fieldRefNode);

                // 处理right
                WorkflowFieldVOValue rightValue = condition.getRight() != null ? condition.getRight().getValue() : null;
                replaceRefNodeIdInConditionField(rightValue, nodePairReverses, fieldRefNode);
            }
            branch.setConfigs(JsonUtils.objectToClass(config));
        }
    }

    private void replaceRefNodeIdInConditionField(WorkflowFieldVOValue value, Map<String, String> nodePairReverses,
        String fieldRefNode) {
        if (value == null || !value.getType().equals(WorkflowFieldVOValue.TypeEnum.REF)) {
            return;
        }

        Map<String, String> contentMap = JsonUtils.objectToClass(value.getContent());
        if (StringUtils.isNotEmpty(contentMap.get(fieldRefNode))
            && nodePairReverses.containsKey(contentMap.get(fieldRefNode))) {
            // 执行ref_node_id替换
            contentMap.put(fieldRefNode, nodePairReverses.get(contentMap.get(fieldRefNode)));
            value.setContent(contentMap);
        }
    }

    /**
     * 适配连接关系
     *
     * @param edges 工作流边连接关系
     * @param reflection 节点和类型映射关系
     * @param nodePair 节点对； 如高级意图和意图容器，成对出现
     * @return 适配后的连接结果列表
     */
    public List<Map<String, Object>> adaptConnections(List<WorkflowEdgeVO> edges, Map<String, String> reflection,
        Map<String, String> nodePair) {
        try {
            log.info("adapt connection.");
            Map<String, String> nodePairReverses = Objects.isNull(nodePair) ? null
                : nodePair.entrySet().stream().collect(Collectors.toMap(Map.Entry::getValue, Map.Entry::getKey));
            return edges.stream()
                .map(m -> IR_EDGE_ADAPTER.adaptEdge(m, reflection, nodePairReverses))
                .filter(m -> !m.isEmpty())
                .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("parse connections failed!", e);
            throw new AgentStudioException(StudioError.CONVERT_NODE_FAILED);
        }
    }
}
