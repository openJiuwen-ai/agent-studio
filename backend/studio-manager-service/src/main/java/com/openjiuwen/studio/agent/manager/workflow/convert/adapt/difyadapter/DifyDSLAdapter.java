/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import static com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter.EnvVariablesConverter.parseEnvVariables;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.VariableEnum;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.service.WorkflowValidationService;
import com.openjiuwen.studio.agent.manager.utils.MapReadUtil;
import com.openjiuwen.studio.agent.manager.workflow.convert.adapt.AdapterService;
import com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter.models.DifyEnvironmentVariableVO;
import com.openjiuwen.studio.agent.manager.workflow.models.WorkflowConfigMemoryVariable;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ArrayUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Queue;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service("DifyAdapterService")
public class DifyDSLAdapter implements AdapterService {

    private static final Pattern TYPE_PATTERN = Pattern.compile("^array\\[(.*)\\]");

    private static final String DEFAULT_CODE_NAME = "Dify_To_AgentBuilder";

    protected final List<NodeConverter> nodeConverters;

    private static final int MAX_RECURSION_DEPTH = 1000;

    private static final String LINE_SEPARATOR = "\n";

    @Value("${front-page.block-nodes:}")
    private String blockNodes;

    @Autowired
    private WorkflowValidationService workflowValidationService;

    public DifyDSLAdapter(List<NodeConverter> nodeConverters) {
        this.nodeConverters = nodeConverters;
    }

    protected NodeConverter getNodeDataConverter(NodeType nodeType) {
        Set<String> blockNodeSet = Arrays.stream(StringUtils.split(blockNodes, ",")).collect(Collectors.toSet());
        if (!blockNodeSet.isEmpty() && nodeType != null && blockNodeSet.contains(nodeType.getType())) {
            return nodeConverters.stream()
                    .filter(converter -> converter.supportNodeType(NodeType.EMPTY))
                    .findFirst()
                    .orElseThrow(() -> new IllegalArgumentException("invalid node type: " + NodeType.EMPTY));
        }
        return nodeConverters.stream()
                .filter(converter -> converter.supportNodeType(nodeType))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("invalid node type: " + nodeType));
    }

    @Override
    public WorkflowInfo convert(Map<String, Object> thirdpartyWorkflowInfo) {
        log.info("dsl importing...");
        Map<String, Object> immutableData = Map.copyOf(thirdpartyWorkflowInfo);
        WorkflowInfo metadata = mapToMetadata(immutableData);
        WorkflowVO workflowVo = new WorkflowVO();
        workflowVo.setDescription(metadata.getDescription()).setName(metadata.getName());
        workflowVo = mapToWorkflow(immutableData, workflowVo);
        metadata.setWorkflowDetails(JSONObject.from(workflowVo));
        log.info("DSL imported successfully.");
        return metadata;
    }

    @Override
    public void validateFormat(Map<String, Object> thirdpartyWorkflowInfo) {
        if (thirdpartyWorkflowInfo == null || !thirdpartyWorkflowInfo.containsKey("app") || !thirdpartyWorkflowInfo.containsKey("workflow")) {
            log.error("Invalid file format!");
            throw new AgentStudioException(StudioError.PARSE_THIRD_PARTY_WORKFLOW_FILE_FAILED);
        }
    }

    @SuppressWarnings("unchecked")
    public WorkflowVO mapToWorkflow(Map<String, Object> data, WorkflowVO workflowVo) {
        Map<String, Object> workflowData = MapReadUtil.safeCastToMapWithStringKey(data.get("workflow"));
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        objectMapper.setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

        Map<String, Object> graphData = MapReadUtil.safeCastToMapWithStringKey(workflowData.get("graph"));
        List<String> sortNodeIds = new ArrayList<>();
        List<WorkflowEdgeVO> workflowEdges = constructEdgesAndSort(graphData, sortNodeIds);

        Map<String, WorkflowNodeVO> nodeMap = new HashMap<>();
        // 构造环境变量，会话变量的节点
        List<Map<String, Object>> environmentVariables = (List<Map<String, Object>>) workflowData.get("environment_variables");
        nodeMap.put(CommonConstant.DIFY.ENV_VARIABLE, constructEnvNode(environmentVariables));
        nodeMap.put(CommonConstant.DIFY.CONVERSATION_VARIABLE, constructConversationNode(data, workflowVo));
        // 构造其他节点
        List<WorkflowNodeVO> workflowNodes = constructNodes(graphData, nodeMap, sortNodeIds, workflowVo);
        // 构造循环的结束节点
        constructLoopEndNode(workflowEdges, workflowNodes);
        // 构造end节点，将所有的消息节点连接到end节点
        constructEndNode(workflowEdges, workflowNodes);
        // 后置处理edge
        edgesAfterProcess(workflowEdges, workflowNodes);
        Map<String, Object> workflowNodeLayouts = constructLayouts(graphData);

        workflowVo.setEdges(workflowEdges);
        workflowVo.setLayouts(workflowNodeLayouts);
        workflowVo.setNodes(workflowNodes);

        // 处理处理对话型-功能相关配置
        if (ObjectUtils.isNotEmpty(workflowData.get("features"))) {
            handlerWorkflowConfig(workflowVo.getConfigs(), workflowData.get("features"));
        }

        WorkflowNodeVO startNode = workflowNodes.stream().filter(node -> node.getType().equals(NodeType.START.getType())).findFirst().orElse(null);
        if (startNode != null) {
            Map<String, Object> configs = startNode.getConfigs();
            if (!configs.containsKey(CommonConstant.DIFY.TRIGGER)) {
                return workflowVo;
            }
            Map<String, Object> configsMap = workflowVo.getConfigs();
            configsMap.put(CommonConstant.DIFY.TRIGGER, configs.get(CommonConstant.DIFY.TRIGGER));
            workflowVo.setConfigs(configsMap);
        }

        return workflowVo;
    }

    public void edgesAfterProcess(List<WorkflowEdgeVO> workflowEdges, List<WorkflowNodeVO> workflowNodes) {
        if (workflowEdges == null || workflowNodes == null) {
            return;
        }
        Map<String, WorkflowNodeVO> nodeMap = workflowNodes.stream()
                .collect(Collectors.toMap(WorkflowNodeVO::getId, node -> node, (v1, v2) -> v1));
        workflowEdges.removeIf(edge -> {
            String sourceId = edge.getSource();
            if (StringUtils.isEmpty(sourceId)) {
                return true;
            }

            WorkflowNodeVO node = nodeMap.get(sourceId);

            // 如果找不到对应节点，移除该边
            if (node == null) {
                return true;
            }

            // 判断节点的边branch字段作映射
            if (NodeType.BRANCH.getType().equalsIgnoreCase(node.getType())) {
                Map<String, Object> configs = node.getConfigs();
                if (configs != null) {
                    // 从 configs 中获取 branchMap
                    Map<String, Object> branchMap = MapReadUtil.safeCastToMapWithStringKey(configs.get("branchMap"));

                    // 如果 branchMap 存在且 edge 有 branch 字段
                    if (branchMap != null && StringUtils.isNotEmpty(edge.getBranch())) {
                        String mappedBranch = branchMap.get(edge.getBranch()).toString();
                        // 如果映射到了新值，则修改 edge 的 branch 字段
                        if (StringUtils.isNotEmpty(mappedBranch)) {
                            edge.setBranch(mappedBranch);
                        }
                    }
                }
                return false;
            }

            // 处理异常分支
            if (!edge.isExceptionBranch()) {
                return false;
            }

            // 判断节点类型是否为 LLM
            if (NodeType.LLM.getType().equalsIgnoreCase(node.getType())) {
                Map<String, Object> configs = node.getConfigs();
                Map<String, Object> exceptionConfig = MapReadUtil.safeCastToMapWithStringKey(configs.get(CommonConstant.DIFY.EXCEPTION_PROCESS));
                if (exceptionConfig == null) {
                    return true;
                }
                return !CommonConstant.DIFY.ERROR_BRANCH.equalsIgnoreCase(exceptionConfig.getOrDefault(CommonConstant.DIFY.HANDLE_TYPE, CommonConstant.DIFY.INTERRUPT).toString());
            }

            // 判断节点类型是否为 HTTP
            if ((NodeType.HTTP.getType().equalsIgnoreCase(node.getType())|| NodeType.EMPTY.getType().equalsIgnoreCase(node.getType())) && edge.isExceptionBranch()) {
                return true;
            }
            return false;
        });
    }

    /**
     * 处理处理对话型-功能相关配置
     * @param configsMap 工作流配置
     * @param features Dify对话型-功能相关配置
     */
    @SuppressWarnings("unchecked")
    private void handlerWorkflowConfig(Map<String, Object> configsMap, Object features) {
        Map<String, Object> featuresMap = (Map<String, Object>) features;
        // 开场白
        if (ObjectUtils.isNotEmpty(featuresMap.get("opening_statement"))) {
            configsMap.put("prologue", featuresMap.get("opening_statement"));
        }
        // 推荐问题
        if (ObjectUtils.isNotEmpty(featuresMap.get("suggested_questions"))) {
            configsMap.put("suggest_queries", featuresMap.get("suggested_questions"));
        }
        // 下一步问题推荐
        if (ObjectUtils.isNotEmpty(featuresMap.get("suggested_questions_after_answer"))) {

            Map<String, Object> suggestedQuestionsAfterAnswer = (Map<String, Object>) featuresMap.get("suggested_questions_after_answer");
            suggestedQuestionsAfterAnswer.put("enable", suggestedQuestionsAfterAnswer.get("enabled"));
            suggestedQuestionsAfterAnswer.put("prompt", CommonConstant.ADDITIONAL_QUESTIONS_PROMPT_CUSTOM);
            suggestedQuestionsAfterAnswer.remove("enabled");
            configsMap.put("additional_questions_config", suggestedQuestionsAfterAnswer);
        }
        // 内容审核
        if (ObjectUtils.isNotEmpty(featuresMap.get("sensitive_word_avoidance"))) {
            Map<String, Object> sensitiveWordAvoidance = (Map<String, Object>) featuresMap.get("sensitive_word_avoidance");
            // OpenAI Moderation
            if ("openai_moderation".equals(sensitiveWordAvoidance.get("type"))) {
                configsMap.put("safety_barrier", sensitiveWordAvoidance.get("enabled"));
            }
            // 关键词模式
            if ("keywords".equals(sensitiveWordAvoidance.get("type"))) {
                Map<String, Object> contentReview = new HashMap<>();
                contentReview.put("replace", new ArrayList<>());
                contentReview.put("filter", Map.ofEntries(Map.entry("keywords", "")));
                contentReview.put("enabled", sensitiveWordAvoidance.get("enabled"));
                Map<String, Object> reply = new HashMap<>();
                Map<String, Object> configMap = (Map<String, Object>) sensitiveWordAvoidance.get("config");
                Map<String, Object> inputsConfig = (Map<String, Object>) configMap.get("inputs_config");
                String keywords = (String) configMap.get("keywords");
                Map<String, Object> outputsConfig = (Map<String, Object>) configMap.get("outputs_config");
                if (ObjectUtils.isNotEmpty(inputsConfig)) {
                    reply.put("input_enable", inputsConfig.get("enabled"));
                    reply.put("input_text", inputsConfig.get("preset_response"));
                }
                if (ObjectUtils.isNotEmpty(outputsConfig)) {
                    reply.put("output_enable", outputsConfig.get("enabled"));
                    reply.put("output_text", outputsConfig.get("preset_response"));
                }
                if (ObjectUtils.isNotEmpty(keywords)) {
                    reply.put("keywords", keywords.replace("\n", ","));
                }
                contentReview.put("reply", ArrayUtils.toArray(reply));

                configsMap.put("content_review", contentReview);
            }
        }
    }

    /**
     * 处理循环节点的循环输出节点
     * @param workflowEdges 边
     * @param workflowNodes 节点
     */
    private void constructLoopEndNode(List<WorkflowEdgeVO> workflowEdges, List<WorkflowNodeVO> workflowNodes) {
        // 前置校验：避免空指针异常
        if (workflowEdges == null || workflowNodes == null || workflowNodes.isEmpty()) {
            return;
        }

        // 预处理：构建「源节点ID→目标节点ID」的映射
        Map<String, String> sourceToTargetMap = buildSourceToTargetMap(workflowEdges);

        // 临时集合：收集待添加的循环结束节点和边（避免迭代中修改原集合）
        List<WorkflowNodeVO> toAddLoopEndNodes = new ArrayList<>();
        List<WorkflowEdgeVO> toAddLoopEndEdges = new ArrayList<>();

        // 遍历所有节点，处理循环开始节点（仅读取，不修改原集合）
        for (WorkflowNodeVO node : workflowNodes) {
            // 跳过空节点/非循环/迭代开始节点
            if (node == null || (!NodeType.LOOP_INPUT.getType().equals(node.getType()) && !NodeType.ITERATION_START.getType().equals(node.getType()))) {
                continue;
            }

            // 1. 创建循环结束节点（先存入临时集合）
            WorkflowNodeVO loopEndNode = createLoopEndNode(node);
            toAddLoopEndNodes.add(loopEndNode);

            // 2. 找到循环链的最后一个节点ID
            String lastLoopNodeId = findLastLoopNodeId(node.getId(), sourceToTargetMap);
            if (lastLoopNodeId == null) {
                continue; // 无后续节点，跳过建边
            }

            // 3. 创建循环结束边（先存入临时集合）
            WorkflowEdgeVO loopEndEdge = createLoopEndEdge(lastLoopNodeId, loopEndNode.getId());
            toAddLoopEndEdges.add(loopEndEdge);
        }

        // 循环结束后，批量添加到原集合（核心修复：避免迭代中修改）
        workflowNodes.addAll(toAddLoopEndNodes);
        workflowEdges.addAll(toAddLoopEndEdges);
    }

    /**
     * 预处理边关系：构建源节点ID到目标节点ID的映射（一对一场景）
     */
    private Map<String, String> buildSourceToTargetMap(List<WorkflowEdgeVO> workflowEdges) {
        Map<String, String> sourceToTargetMap = new HashMap<>(workflowEdges.size());
        for (WorkflowEdgeVO edge : workflowEdges) {
            if (edge != null && edge.getSource() != null && edge.getTarget() != null) {
                sourceToTargetMap.put(edge.getSource(), edge.getTarget());
            }
        }
        return sourceToTargetMap;
    }

    /**
     * 创建循环结束节点
     */
    private WorkflowNodeVO createLoopEndNode(WorkflowNodeVO loopInputNode) {
        WorkflowNodeVO loopEndNode = new WorkflowNodeVO();
        // 替换后缀生成结束节点ID，兼容空ID场景
        String endNodeId = Optional.ofNullable(loopInputNode.getId())
            .map(id -> id.replaceAll("_input", "_output"))
            .orElse("default_loop_output");
        loopEndNode.setId(endNodeId);
        loopEndNode.setType(NodeType.LOOP_OUTPUT.getType());
        loopEndNode.setName("循环输出");
        return loopEndNode;
    }

    /**
     * 查找循环链的最后一个节点ID（避免死循环：限制最大遍历次数）
     */
    private String findLastLoopNodeId(String startNodeId, Map<String, String> sourceToTargetMap) {
        if (startNodeId == null || sourceToTargetMap.isEmpty()) {
            return null;
        }

        String currentNodeId = startNodeId;
        int maxTraverseTimes = 1000; // 防死循环：限制最大遍历次数（可根据业务调整）
        int traverseCount = 0;

        // 循环查找下一个节点，直到无后续节点或达到最大次数
        while (sourceToTargetMap.containsKey(currentNodeId) && traverseCount < maxTraverseTimes) {
            currentNodeId = sourceToTargetMap.get(currentNodeId);
            traverseCount++;
        }

        // 达到最大次数，说明可能存在循环依赖，返回null避免死循环
        return traverseCount >= maxTraverseTimes ? null : currentNodeId;
    }

    /**
     * 创建循环结束边
     */
    private WorkflowEdgeVO createLoopEndEdge(String sourceId, String targetId) {
        WorkflowEdgeVO edge = new WorkflowEdgeVO();
        edge.setSource(sourceId);
        edge.setTarget(targetId);
        edge.setExceptionBranch(false); // 正常分支
        return edge;
    }

    private void constructEndNode(List<WorkflowEdgeVO> workflowEdges, List<WorkflowNodeVO> workflowNodes) {
        WorkflowNodeVO endNode = workflowNodes.stream().filter(node -> node.getType().equals(NodeType.END.getType())).findFirst().orElse(null);
        if (endNode != null) {
            return;
        }

        Map<String, WorkflowEdgeVO> sourceEdgeMap = workflowEdges.stream()
                .collect(Collectors.toMap(WorkflowEdgeVO::getSource, edgeVO -> edgeVO, (v1, v2) -> v1));
        for (WorkflowNodeVO node : workflowNodes) {
            // 消息节点 且 非循环体内 且 无出度分支
            if (NodeType.MESSAGE.getType().equalsIgnoreCase(node.getType())
                    && !(boolean) node.getConfigs().getOrDefault(CommonConstant.DIFY.IS_IN_LOOP, false)
                    && !sourceEdgeMap.containsKey(node.getId())) {
                WorkflowEdgeVO edge = new WorkflowEdgeVO();
                edge.setSource(node.getId());
                edge.setTarget("node_end");
                edge.setExceptionBranch(false);
                workflowEdges.add(edge);
            }
        }
        Map<String, Object> config = new HashMap<>();
        config.put("is_stream_out", true);
        config.put("response_mode", "directResponse");
        config.put("response_template", "");
        endNode = new WorkflowNodeVO();
        endNode.setId("node_end")
                .setType(NodeType.END.getType())
                .setName("结束")
                .setConfigs(config)
                .setOutputs(List.of(new WorkflowFieldVO()
                        .setName("response_content")
                        .setSource(WorkflowFieldVO.SourceEnum.SYSTEM)
                        .setDescription("最终输出")
                        .setType("string")
                        .setValue(new WorkflowFieldVOValue()
                                .setType(WorkflowFieldVOValue.TypeEnum.GENERATED))));
        workflowNodes.add(endNode);
    }

    public WorkflowInfo mapToMetadata(Map<String, Object> data) {
        @SuppressWarnings("unchecked")
        Map<String, Object> map = (Map<String, Object>) data.get("app");
        WorkflowInfo metadata = new WorkflowInfo();
        if (CommonConstant.DIFY.CHAT_WORKFLOW.equalsIgnoreCase((String) map.get("mode"))) {
            metadata.setType(CommonConstant.CHAT);
        } else if (CommonConstant.DIFY.TASK_WORKFLOW.equalsIgnoreCase((String) map.get("mode"))) {
            metadata.setType(CommonConstant.Workflow.TASK);
        } else {
            throw new AgentStudioException(StudioError.UNSUPPORTED_WORKFLOW_TYPE);
        }
        metadata.setName(workflowValidationService.sanitizeName((String) map.getOrDefault("name", metadata.getType() + "-" + UUID.randomUUID())));
        String description = StringUtils.isEmpty((String) map.getOrDefault("description", DEFAULT_CODE_NAME)) ? DEFAULT_CODE_NAME : (String) map.get("description");
        metadata.setDescription(description)
                .setCode(DEFAULT_CODE_NAME);
        return metadata;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> constructLayouts(Map<String, Object> data) {
        Map<String, Object> layouts = new HashMap<>();
        int maxX = 0;
        int maxY = 0;
        if (data.containsKey("nodes")) {
            List<Map<String, Object>> nodeMaps = (List<Map<String, Object>>) data.get("nodes");
            for (Map<String, Object> nodeMap : nodeMaps) {
                Map<String, Object> nodeConfig = (Map<String, Object>) nodeMap.get("data");
                String difyNodeType = (String) nodeConfig.get("type");
                if (difyNodeType == null || difyNodeType.isBlank()) {
                    // 注释节点不参与转换
                    continue;
                }
                Map<String, Object> pos = (Map<String, Object>) nodeMap.get("positionAbsolute");
                Number x = (Number) pos.get("x");
                Number y = (Number) pos.get("y");
                if (x != null) {
                    maxX = Math.max(maxX, x.intValue());
                }
                if (y != null) {
                    maxY = Math.max(maxY, y.intValue());
                }
                switch (NodeType.fromDifyValue(nodeConfig.get("type").toString())) {
                    case START, TRIGGER_SCHEDULE, TRIGGER_WEBHOOK ->
                            layouts.put("node_start", nodeMap.get("positionAbsolute"));
                    case LOOP_INPUT, ITERATION_START ->
                            layouts.put("node_" + nodeMap.get("id").toString().replaceAll("start", "_input"), nodeMap.get("positionAbsolute"));
                    case END ->
                            // END节点可能有多个，只需要一个即可
                            layouts.putIfAbsent("node_end", nodeMap.get("positionAbsolute"));
                    default ->
                            layouts.put("node_" + nodeMap.get("id"), nodeMap.get("positionAbsolute"));
                }
            }
        }
        Map<String, Object> endPos = new HashMap<>();
        int endX = maxX + 300;
        int endY = maxY + 50;
        endPos.put("x", endX);
        endPos.put("y", endY);
        // 适配对话型工作流无end节点的情况
        layouts.putIfAbsent("node_end", endPos);
        return layouts;
    }

    private WorkflowNodeVO convertNode(Map<String, Object> nodeMap, String difyNodeType, Map<String, WorkflowNodeVO> workflowNodeMap) {
        NodeType nodeType = (NodeType.TRIGGER_SCHEDULE.getDifyType().equalsIgnoreCase(difyNodeType) || NodeType.TRIGGER_WEBHOOK.getDifyType().equalsIgnoreCase(difyNodeType)) ? NodeType.START : NodeType.fromDifyValue(difyNodeType);
        WorkflowNodeVO workflowNodeVO;
        try {
            workflowNodeVO = getNodeDataConverter(nodeType).parseMapData(nodeMap, workflowNodeMap);
        }catch (Exception e) {
            log.error("An exception occurred during node type conversion. Node id: {}, Exception: {}", nodeMap.get("id"), e);
            workflowNodeVO = getNodeDataConverter(NodeType.EMPTY).parseMapData(nodeMap, workflowNodeMap);
        }
        return workflowNodeVO;
    }

    /**
     * 构造边列表并计算节点拓扑顺序
     *
     * @param data      原始数据 Map
     * @param nodeOrder [输出参数] 用于保存节点的拓扑排序顺序（原始 ID）
     * @return List<WorkflowEdgeVO> 格式化后的边列表
     */
    @SuppressWarnings("unchecked")
    public List<WorkflowEdgeVO> constructEdgesAndSort(Map<String, Object> data, List<String> nodeOrder) {
        List<WorkflowEdgeVO> edges = new ArrayList<>();
        Map<String, List<String>> graph = new HashMap<>();
        Map<String, Integer> inDegree = new HashMap<>();
        Set<String> startTypeNodes = new HashSet<>();
        if (data.containsKey("edges")) {
            List<Map<String, Object>> edgeMaps = (List<Map<String, Object>>) data.get("edges");
            for (Map<String, Object> edgeMap : edgeMaps) {
                String sourceIdRaw = edgeMap.get("source").toString();
                // 针对循环节点的拓扑顺序需要做特殊处理
                if (sourceIdRaw.endsWith("start")) {
                    graph.computeIfAbsent(sourceIdRaw.replaceAll("start$", ""), k -> new ArrayList<>()).add(sourceIdRaw);
                    inDegree.put(sourceIdRaw, inDegree.getOrDefault(sourceIdRaw, 0) + 1);
                    inDegree.putIfAbsent(sourceIdRaw.replaceAll("start$", ""), 0); // 确保起点也有记录
                }
                String targetIdRaw = edgeMap.get("target").toString();
                graph.computeIfAbsent(sourceIdRaw, k -> new ArrayList<>()).add(targetIdRaw);
                inDegree.put(targetIdRaw, inDegree.getOrDefault(targetIdRaw, 0) + 1);
                inDegree.putIfAbsent(sourceIdRaw, 0); // 确保起点也有记录
                WorkflowEdgeVO workflowEdgeVO = new WorkflowEdgeVO();
                Map<String, String> edgeConfig = (Map<String, String>) edgeMap.get("data");

                // 处理branch的source
                String voSourceId = "node_" + sourceIdRaw;
                if (edgeConfig != null && (NodeType.START.getDifyType().equalsIgnoreCase(edgeConfig.get("sourceType"))
                        || NodeType.TRIGGER_SCHEDULE.getDifyType().equalsIgnoreCase(edgeConfig.get("sourceType"))
                        || NodeType.TRIGGER_WEBHOOK.getDifyType().equalsIgnoreCase(edgeConfig.get("sourceType")))) {
                    voSourceId = "node_start";
                    startTypeNodes.add(sourceIdRaw);
                } else if (edgeConfig != null && NodeType.INTENT_DETECTION.getDifyType()
                    .equalsIgnoreCase(edgeConfig.get("sourceType"))) {
                    workflowEdgeVO.setBranch("branch_" + edgeMap.get("sourceHandle").toString());
                } else if (edgeConfig != null && (
                    CommonConstant.DIFY.LOOP_START.equalsIgnoreCase(edgeConfig.get("sourceType"))
                        || CommonConstant.DIFY.ITERATION_START.equalsIgnoreCase(edgeConfig.get("sourceType")))) {
                    voSourceId = "node_" + sourceIdRaw.replaceAll("start", "_input");
                } else if (edgeConfig != null && (NodeType.END.getDifyType().equalsIgnoreCase(edgeConfig.get("sourceType")))) {
                    // 起始类型为end的branch跳过
                    continue;
                }
                workflowEdgeVO.setSource(voSourceId);

                // 处理branch的target
                String voTargetId = "node_" + targetIdRaw;
                if (edgeConfig != null && NodeType.END.getDifyType().equalsIgnoreCase(edgeConfig.get("targetType"))) {
                    voTargetId = "node_end";
                }
                workflowEdgeVO.setTarget(voTargetId);

                // 处理判断节点的branch
                if (edgeConfig != null && NodeType.BRANCH.getDifyType().equalsIgnoreCase(edgeConfig.get("sourceType"))) {
                    workflowEdgeVO.setBranch(edgeMap.get("sourceHandle").toString());
                }

                // 处理异常分支
                if ("fail-branch".equalsIgnoreCase(edgeMap.get("sourceHandle").toString())) {
                    workflowEdgeVO.setExceptionBranch(true);
                }
                edges.add(workflowEdgeVO);
            }
            Map<String, WorkflowEdgeVO> uniqueEdgesMap = new LinkedHashMap<>();
            for (WorkflowEdgeVO edge : edges) {
                String key = edge.getSource() + "->" + edge.getTarget() + "|" + edge.isExceptionBranch();
                uniqueEdgesMap.putIfAbsent(key, edge);
            }
            edges = new ArrayList<>(uniqueEdgesMap.values());
            Queue<String> queue = new ArrayDeque<>();
            if (!startTypeNodes.isEmpty()) {
                queue.addAll(startTypeNodes);
            } else {
                for (Map.Entry<String, Integer> entry : inDegree.entrySet()) {
                    if (entry.getValue() == 0) {
                        queue.add(entry.getKey());
                    }
                }
            }
            while (!queue.isEmpty()) {
                String currentNode = queue.poll();
                nodeOrder.add(currentNode);
                List<String> neighbors = graph.get(currentNode);
                if (neighbors != null) {
                    for (String neighbor : neighbors) {
                        int newDegree = inDegree.get(neighbor) - 1;
                        inDegree.put(neighbor, newDegree);
                        if (newDegree == 0) {
                            queue.add(neighbor);
                        }
                    }
                }
            }
        }
        return edges;
    }

    @SuppressWarnings("unchecked")
    private List<WorkflowNodeVO> constructNodes(Map<String, Object> data, Map<String, WorkflowNodeVO> workflowNodeMap, List<String> nodeOrder, WorkflowVO workflowVo) {
        if (data.containsKey("nodes")) {
            List<Map<String, Object>> nodeMaps = (List<Map<String, Object>>) data.get("nodes");
            Map<String, Map<String, Object>> tempNodeMap = new HashMap<>();
            for (Map<String, Object> nodeMap : nodeMaps) {
                if ("custom-note".equals(nodeMap.get("type"))) {
                    // 处理注释节点
                    List<Object> comments = workflowVo.getComments();
                    if (ObjectUtils.isEmpty(comments)) {
                        comments = new ArrayList<>();
                    }
                    Map<String, Object> comment = new HashMap<>();
                    comment.put("id", "node_" + nodeMap.get("id"));
                    Map<String, Object> nodeData = (Map<String, Object>) nodeMap.get("data");
                    comment.put("height", nodeData.get("height"));
                    comment.put("width", nodeData.get("width"));
                    comment.put("name", "注释");
                    comment.put("type", "Comment");
                    comment.put("content", extractAndJoinText(ObjectUtils.isNotEmpty(nodeData.get("text")) ? (String) nodeData.get("text") : ""));
                    Map<String, Object> nodePosition = (Map<String, Object>) nodeMap.get("position");
                    comment.put("x", nodePosition.get("x"));
                    comment.put("y", nodePosition.get("y"));
                    comments.add(comment);
                    workflowVo.setComments(comments);
                    continue;
                }
                String id = nodeMap.get("id").toString();
                tempNodeMap.put(id, nodeMap);
            }

            if (nodeOrder != null && !nodeOrder.isEmpty()) {
                for (String id : nodeOrder) {
                    Map<String, Object> nodeMap = tempNodeMap.get(id);
                    if (nodeMap != null) {
                        processSingleNode(nodeMap, workflowNodeMap);
                        tempNodeMap.remove(id);
                    }
                }
            }

            for (Map<String, Object> nodeMap : tempNodeMap.values()) {
                processSingleNode(nodeMap, workflowNodeMap);
            }
        }
        // 系统变量、环境变量、会话变量在转换前删除，只用作获取信息
        workflowNodeMap.remove(CommonConstant.DIFY.SYS_VARIABLE);
        workflowNodeMap.remove(CommonConstant.DIFY.ENV_VARIABLE);
        workflowNodeMap.remove(CommonConstant.DIFY.CONVERSATION_VARIABLE);
        // 对转换后的节点根据node_id去重，防止存在多个结束节点
        return workflowNodeMap.values().stream()
                .collect(Collectors.collectingAndThen(
                        Collectors.toMap(
                                WorkflowNodeVO::getId,
                                Function.identity(),
                                (existing, replacement) -> existing),
                        map -> new ArrayList<>(map.values())
                ));
    }

    /**
     * 核心方法：提取所有层级的text，按语义行拼接（listitem/paragraph为独立行）
     * @param jsonStr 原始JSON字符串（支持list/listitem/paragraph嵌套）
     * @return 拼接后的text字符串（异常场景返回空字符串）
     */
    public String extractAndJoinText(String jsonStr) {
        // 前置校验：空/空白输入直接返回空字符串
        if (jsonStr == null || jsonStr.trim().isEmpty()) {
            return "";
        }

        StringBuilder textSb = new StringBuilder();

        try {
            // 解析JSON根对象
            JSONObject rootObj = JSONObject.parseObject(jsonStr);
            if (rootObj == null) {
                return "";
            }

            // 获取root节点
            JSONObject rootNode = rootObj.getJSONObject("root");
            if (rootNode == null) {
                return "";
            }

            // 递归遍历root下的所有节点，提取text（核心修复：不限节点类型）
            extractTextRecursive(rootNode, textSb, 0, false);

            // 去除末尾多余的换行符，返回结果
            return textSb.toString().replaceAll(LINE_SEPARATOR + "$", "");
        } catch (Exception e) {
            log.error("Unknown exception occurred during text extraction", e);
            return "";
        }
    }

    /**
     * 递归遍历所有节点提取text（核心修复：支持list/listitem/paragraph所有类型）
     * @param node 当前节点（JSONObject/JSONArray）
     * @param textSb 结果拼接容器
     * @param currentDepth 当前递归深度（防止栈溢出）
     * @param isInListItem 是否在listitem节点内（控制换行逻辑）
     */
    private void extractTextRecursive(Object node, StringBuilder textSb, int currentDepth, boolean isInListItem) {
        // 递归深度限制：防止恶意嵌套导致栈溢出
        if (currentDepth > MAX_RECURSION_DEPTH || node == null) {
            return;
        }

        try {
            // 处理JSONArray（节点数组，如children）
            if (node instanceof JSONArray jsonArray) {
                for (Object item : jsonArray) {
                    // 递归遍历数组项，继承isInListItem状态
                    extractTextRecursive(item, textSb, currentDepth + 1, isInListItem);
                }
            }

            // 处理JSONObject（核心节点：list/paragraph/text）
            else if (node instanceof JSONObject jsonObj) {
                String nodeType = jsonObj.getString("type");
                boolean isListItem = "listitem".equals(nodeType);
                boolean isParagraph = "paragraph".equals(nodeType);

                // 1. 提取当前节点的text字段（仅非空字符串有效）
                if (jsonObj.containsKey("text")) {
                    Object textObj = jsonObj.get("text");
                    if (textObj instanceof String text && !text.trim().isEmpty()) {
                        // listitem/paragraph开头添加换行（避免文本粘连）
                        if ((isListItem || isParagraph) && !textSb.isEmpty()) {
                            textSb.append(LINE_SEPARATOR);
                        }
                        textSb.append(text);
                    }
                }

                // 2. 递归遍历子节点（children）
                JSONArray children = jsonObj.getJSONArray("children");
                if (children != null && !children.isEmpty()) {
                    // 传递isListItem状态（listitem内的文本属于同一行）
                    extractTextRecursive(children, textSb, currentDepth + 1, isListItem);
                }

                // 3. listitem/paragraph结束后添加换行（独立行）
                if ((isListItem || isParagraph) && !textSb.isEmpty()) {
                    textSb.append(LINE_SEPARATOR);
                }
            }
        } catch (Exception e) {
            // 单个节点遍历异常：记录日志，继续处理其他节点
            log.error("Exception occurred while extracting text. Depth: {}, Error: {}", currentDepth, e.getMessage(), e);
        }
    }

    @SuppressWarnings("unchecked")
    private void processSingleNode(Map<String, Object> nodeMap, Map<String, WorkflowNodeVO> workflowNodeMap) {
        Map<String, Object> nodeConfig = (Map<String, Object>) nodeMap.get("data");
        String difyNodeType = (String) nodeConfig.get("type");
        if (difyNodeType == null || difyNodeType.isBlank()) {
            return;
        }

        WorkflowNodeVO node = convertNode(nodeMap, difyNodeType, workflowNodeMap);
        workflowNodeMap.put(nodeMap.get("id").toString(), node);
        if (node.getType().equals(NodeType.START.getType())) {
            workflowNodeMap.put(CommonConstant.DIFY.SYS_VARIABLE, node);
        }
    }

    private WorkflowNodeVO constructEnvNode(List<Map<String, Object>> environmentVariables) {
        Map<String, DifyEnvironmentVariableVO> envVariablesMap = parseEnvVariables(environmentVariables);
        WorkflowNodeVO envVariablesNode = new WorkflowNodeVO().setType(NodeType.ENV.getType())
            .setName("环境变量")
            .setId("node_env");

        List<WorkflowFieldVO> outputs = new ArrayList<>();
        for (Map.Entry<String, DifyEnvironmentVariableVO> entry : envVariablesMap.entrySet()) {
            DifyEnvironmentVariableVO tempRawEnvVariable = entry.getValue();
            WorkflowFieldVOValue tempEnvValue = new WorkflowFieldVOValue().setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                .setDefault(tempRawEnvVariable.getValue())
                .setHint("");

            WorkflowFieldVO tempEnvVariable = new WorkflowFieldVO().setName(tempRawEnvVariable.getName())
                .setType(String.valueOf(tempRawEnvVariable.getValueType()))
                .setDescription(tempRawEnvVariable.getDescription())
                .setRequired(true)
                .setSource(WorkflowFieldVO.SourceEnum.ENVIRONMENT)
                .setValue(tempEnvValue);
            tempEnvVariable.setName(tempRawEnvVariable.getName());


            outputs.add(tempEnvVariable);
        }
        envVariablesNode.setOutputs(outputs);
        return envVariablesNode;
    }

    /**
     * 输出会话变量节点的同时，配置好configs里的记忆变量
     *
     * @param data dify的数据
     * @param workflowVo 工作流信息
     * @return 会话变量节点
     */
    @SuppressWarnings("unchecked")
    private WorkflowNodeVO constructConversationNode(Map<String, Object> data, WorkflowVO workflowVo) {

        // 构造会话变量节点的输出
        List<WorkflowFieldVO> outputs = new ArrayList<>();

        // 遍历会话变量，并转换为记忆变量配置和会话变量节点
        List<WorkflowConfigMemoryVariable> memoryVariables = Optional.ofNullable((Map<String, Object>) data.get("workflow"))
                .map(workflow -> (List<Map<String, Object>>) workflow.get("conversation_variables"))
                .orElse(Collections.emptyList())
                .stream().map(conversationVariable -> {
                    // 设置会话变量节点的输出
                    WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO()
                            .setDescription((String) conversationVariable.get("description"))
                            .setName((String) conversationVariable.get("name"))
                            .setValue(new WorkflowFieldVOValue()
                                    .setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                                    .setDefault(conversationVariable.get("value"))
                                    .setHint(""));
                    setTypeAndSchemaByType(workflowFieldVO, (String) conversationVariable.get("value_type"));
                    outputs.add(workflowFieldVO);
                    // 设置configs里的记忆变量
                    WorkflowConfigMemoryVariable workflowConfigMemoryVariable = new WorkflowConfigMemoryVariable();
                    workflowConfigMemoryVariable.setName(workflowFieldVO.getName());
                    workflowConfigMemoryVariable.setDescription(workflowFieldVO.getDescription());
                    workflowConfigMemoryVariable.setValue(workflowFieldVO.getValue());
                    workflowConfigMemoryVariable.setType(workflowFieldVO.getType());
                    workflowConfigMemoryVariable.setSchema(workflowFieldVO.getSchema());
                    return workflowConfigMemoryVariable;
                })
                .toList();

        // 设置configs
        workflowVo.setConfigs(new HashMap<>(Map.of("memory", memoryVariables)));

        // 返回
        return new WorkflowNodeVO().setType(CommonConstant.DIFY.CONVERSATION_VARIABLE).setOutputs(outputs);
    }

    /**
     * 解析dify的type字段
     * type ->  type + schema
     *
     * @param memoryVariable 要设置的记忆变量
     * @param type dify的type
     */
    private void setTypeAndSchemaByType(WorkflowConfigMemoryVariable memoryVariable, String type) {
        Matcher matcher = TYPE_PATTERN.matcher(type);
        if (matcher.matches()) {
            memoryVariable.setType(VariableEnum.ARRAY.getDslType());
            memoryVariable.setSchema(new WorkflowFieldVO().setType(matcher.group(1)).setName(""));
        } else {
            memoryVariable.setType(type);
        }
    }

    private void setTypeAndSchemaByType(WorkflowFieldVO workflowFieldVO, String type) {
        Matcher matcher = TYPE_PATTERN.matcher(type);
        if (matcher.matches()) {
            workflowFieldVO.setType(VariableEnum.ARRAY.getDslType());
            workflowFieldVO.setSchema(new WorkflowFieldVO().setType(matcher.group(1)).setName(""));
        } else {
            workflowFieldVO.setType(type);
        }
    }

}
