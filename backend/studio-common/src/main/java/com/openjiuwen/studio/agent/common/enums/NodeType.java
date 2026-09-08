/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.enums;

import lombok.Getter;

import java.util.Arrays;

/**
 * 节点类型枚举类，区分workflow组件和内置组件
 *
 */
@Getter
public enum NodeType {
    /**
     * 开始节点，workflow节点
     */
    START("Start", false, "jiuwen.start", "Start", "start"),

    /**
     * 结束节点，workflow节点
     */
    END("End", false, "jiuwen.end", "End", "end"),

    /**
     * 大模型节点，workflow节点
     */
    LLM("LLM", false, "jiuwen.LLMComponent", "LLM", "llm"),

    /**
     * 智能体节点，workflow节点
     */
    AGENT("Agent", false, "jiuwen.LLMReAct", "jiuwen.LLMReAct", "Agent"),

    /**
     * 知识检索节点，workflow节点
     */
    KNOWLEDGE_REPO("KnowledgeRepo", false, "jiuwen.knowledgeRetrieval", "FlowKnowledgeRetrieval", "knowledge-retrieval"),

    /**
     * 知识库节点，workflow节点（旧）
     */
    KNOWLEDGE("Knowledge", false, null, null),

    /**
     * API节点，workflow节点
     */
    API("Api", false, null, null),

    /**
     * 插件节点，workflow节点
     */
    PLUGIN("Plugin", false, "jiuwen.plugin", "Api"),

    /**
     * 消息节点，workflow节点
     */
    MESSAGE("Message", false, "jiuwen.message", "Message"),

    /**
     * 规划节点，workflow节点
     */
    TASK_FLOW("TaskFlow", false, "jiuwen.taskFlow", "Task"),

    /**
     * 分支节点，workflow节点
     */
    BRANCH("Branch", false, "jiuwen.branch", "Branch", "if-else"),

    /**
     * 代码节点，workflow节点
     */
    CODE("Code", false, "jiuwen.code", "Code", "code"),

    /**
     * 文本处理节点，workflow节点
     */
    TEMPLATE_TRANSFORM("Prompt", false, null, null),

    /**
     * 意图识别节点，workflow节点
     */
    INTENT_DETECTION("IntentDetection", false, "jiuwen.intentDetection", "IntentDetection", "question-classifier"),

    /**
     * 意图识别容器节点，仅DSL
     */
    INTENT_DETECTION_CONTAINER("IntentDetectionContainer", false, "EI.IntentDetectionContainer",
        "EI.IntentDetectionContainer"),

    /**
     * 意图识别容器节点，仅IR
     */
    INTENT_COMPLEX_INTENT("ComplexIntentDetection", false, "EI.ComplexIntentDetection", "EI.ComplexIntentDetection"),

    /**
     * workflow节点（嵌套），workflow节点
     */
    WORKFLOW("Workflow", false, "jiuwen.workflowComposite", "jiuwen.workflowComposite"),

    /**
     * 参数提取节点
     */
    PARAM_EXTRACTION("ParamExtraction", false, "jiuwen.paramExtraction", "jiuwen.paramExtraction"),

    /**
     * web搜索节点，内置节点
     */
    WEB_SEARCH("WebSearch", true, null, null),

    /**
     * 代码解释器节点，内置节点
     */
    CODE_INTERPRETER("CodeInterpreter", true, null, null),

    /**
     * 提问器节点
     */
    QUESTIONER("Questioner", false, "jiuwen.questioner", "Questioner"),

    /**
     * 规划节点
     */
    PLANNER("Planner", false, "jiuwen.planner", "jiuwen.planner"),

    /**
     * 输入节点
     */
    INPUT("Input", false, "jiuwen.input", "jiuwen.input"),

    /**
     * Aggregation，聚合节点
     */
    AGGREGATION("Aggregation", false, "jiuwen.aggregation", "jiuwen.aggregation", "variable-aggregator"),

    /**
     * Loop，循环节点
     */
    LOOP("Loop", false, "jiuwen.loop", "jiuwen.loop", "loop"),

    /**
     * LoopInput，循环输入节点
     */
    LOOP_INPUT("LoopInput", true, "jiuwen.loopInput", "jiuwen.loopInput", "loop-start"),

    /**
     * LoopOutput，循环输出节点
     */
    LOOP_OUTPUT("LoopOutput", true, "jiuwen.loopOutput", "jiuwen.loopOutput"),

    /**
     * 退出循环节点
     */
    LOOP_END("Empty", false, null, null, "loop-end"),

    /**
     * 设置变量节点
     */
    SET_VARIABLE("SetVariable", false, "jiuwen.setVariable", "jiuwen.setVariable", "assigner"),

    /**
     * 参数传递节点
     */
    PARAM_OUT("ParamOutput", false, "EI.ParamOutput", "EI.ParamOutput"),

    /**
     * http节点
     */
    HTTP("Http", false, "EI.http", "EI.http", "http-request"),

    /**
     * MCP 节点
     */
    MCP("Mcp", false, "jiuwen.mcp", "jiuwen.mcp"),

    /**
     * LTM节点
     */
    LTM("LTM", false, "EI.LTM", "EI.LTM"),

    /**
     * 问答节点
     */
    QA("QA", false, "EI.qa", "EI.qa"),

    /**
     * 未知节点
     */
    UN_KNOWN("Unknown", false, "unknown", "unknown"),

    /**
     * 数据获取节点
     */
    DATA_ACQUISITION("DataAcquisition", false, "jiuwen.mcp", "jiuwen.mcp"),

    /**
     * 数据加工节点
     */
    DATA_PROCESS("DataProcess", false, "jiuwen.mcp", "jiuwen.mcp"),

    /**
     * 数据合成节点
     */
    DATA_SYNTHESIS("DataSynthesis", false, "jiuwen.mcp", "jiuwen.mcp"),

    /**
     * 空白节点 用于Dify导入替换不兼容节点
     */
    EMPTY("Empty", false, null, null, "empty"),

    /**
     * 异常 节点
     */
    STRUCTURED_MESSAGES_EXCEPTION("StructuredMessagesException", false, "jiuwen.exception", "jiuwen.exception"),

    /**
     * 流式处理节点
     */
    STREAM_TRANSFORM("StreamTransform", false, "jiuwen.streamTransform", "jiuwen.streamTransform"),

    /**
     *  dify 模板转换节点
     */
    TEMPLATE_TRANSFORM_DIFY("Empty", false, null, null, "template-transform"),

    /**
     * dify 列表操作节点
     */
    LIST_OPERATOR("Empty", false, null, null, "list-operator"),

    /**
     *  dify 文档提取节点
     */
    DOCUMENT_EXTRACTOR("Empty", false, null, null, "document-extractor"),

    /**
     * dify 参数提取器节点
     */
    PARAMETER_EXTRACTOR("LLM", false, null, null, "parameter-extractor"),

    /**
     * dify 工具节点
     */
    TOOL("Empty", false, null, null, "tool"),

    /**
     * dify 回复节点
     */
    ANSWER("Message", false, null, null, "answer"),

    /**
     * env 节点
     */
    ENV("EnvVariables", true, null, null, "env"),

    /**
     * dify 触发器节点
     */
    TRIGGER_SCHEDULE("Start", false, null, null, "trigger-schedule"),

    TRIGGER_WEBHOOK("Start", false, null, null, "trigger-webhook"),

    /**
     * dify 迭代节点
     */
    ITERATION("Loop", false, null, null, "iteration"),

    /**
     * 迭代开始节点
     */
    ITERATION_START("LoopInput", false, null, null, "iteration-start"),

    /**
     * SQL节点，直接编写SQL语句
     */
    SQL("Sql", false, "jiuwen.sql", "jiuwen.sql", "sql"),

    /**
     * 数据查询节点，可视化查询条件构建SQL
     */
    DATA_QUERY("DataQuery", false, "jiuwen.sql", "jiuwen.sql", "data-query");


    /**
     * 是否为ir类型
     */
    private final String type;

    /**
     * 是否为内置节点
     */
    private final boolean isInnerNode;

    /**
     * 九问定义类型
     */
    private final String irType;

    /**
     * 调试事件类型
     */
    private final String insightType;

    /**
     *  dify DSL节点类型
     */
    private String difyType;

    NodeType(String type, boolean isInnerNode, String irType, String insightType) {
        this.type = type;
        this.isInnerNode = isInnerNode;
        this.irType = irType;
        this.insightType = insightType;
        this.difyType = null;
    }

    NodeType(String type, boolean isInnerNode, String irType, String insightType, String difyType) {
        this.type = type;
        this.isInnerNode = isInnerNode;
        this.irType = irType;
        this.insightType = insightType;
        this.difyType = difyType;
    }

    /**
     * 根据DSL中节点Type，获取NodeType对象
     *
     * @param type DSL中节点Type
     * @return NodeType
     */
    public static NodeType fromType(String type) {
        for (NodeType nodeType : NodeType.values()) {
            if (nodeType.getType().equalsIgnoreCase(type)) {
                return nodeType;
            }
        }
        return null;
    }

    /**
     * 根据九问name获取nodeType枚举
     *
     * @param jiuwenType 九问测节点类型
     * @return 节点类型对象
     */
    public static NodeType fromJiuwen(String jiuwenType) {
        for (NodeType nodeType : NodeType.values()) {
            if (nodeType.getJiuwenType() != null && nodeType.getJiuwenType().equalsIgnoreCase(jiuwenType)) {
                return nodeType;
            }
        }
        return UN_KNOWN;
    }

    /**
     * 根据九问insight type获取nodeType枚举
     *
     * @param insightType 九问debug节点类型
     * @return 节点类型对象
     */
    public static NodeType fromInsight(String insightType) {
        for (NodeType nodeType : NodeType.values()) {
            if (nodeType.getInsightType() != null && nodeType.getInsightType().equalsIgnoreCase(insightType)) {
                return nodeType;
            }
        }
        return UN_KNOWN;
    }

    /**
     * 根据dify类型获取nodeType
     * @param difyType dify节点类型
     * @return 节点类型流
     */
    public static NodeType fromDifyValue(String difyType) {
        return Arrays.stream(NodeType.values())
                .filter(nodeType -> nodeType.difyType != null && nodeType.difyType.equalsIgnoreCase(difyType))
                .findFirst()
                .orElse(NodeType.EMPTY);
    }

    /**
     * 根据 EI Type 获取 Insight type
     *
     * @param nodeType EI type
     * @return Insight type
     */
    public static String toInsight(String nodeType) {
        for (NodeType type : NodeType.values()) {
            if (type.getEiType().equals(nodeType)) {
                return type.getInsightType();
            }
        }
        return null;
    }

    /**
     * 兼容runtime接口，返回ei节点类型
     *
     * @return ei节点类型
     */
    public String getEiType() {
        return type;
    }

    /**
     * 兼容runtime接口，返回ir类型
     *
     * @return ir类型
     */
    public String getJiuwenType() {
        return irType;
    }
}
