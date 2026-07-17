/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfoInnerError;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfoInnerErrorErrorBody;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.manager.dto.JiuwenEventDataInnerError;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import javax.annotation.PostConstruct;

/**
 * Jiuwen流式响应Event处理
 *
 */
@Component
@Slf4j
public class JiuwenEventProcessor {

    private static final String USER_FIELDS = "userFields";

    private static final String SYSTEM_FIELDS = "systemFields";

    private static final String ENVIRONMENT_FIELDS = "environmentFields";

    private static final List<JiuwenEventType> TO_RECORD_EVENTS = Arrays.asList(JiuwenEventType.START,
        JiuwenEventType.WORKFLOW_START, JiuwenEventType.DONE, JiuwenEventType.WORKFLOW_END,
        JiuwenEventType.WORKFLOW_NODE_MESSAGE, JiuwenEventType.EXCEPTION);

    private static final String JIUWEN_EXCEPTION_NODE_ID = "jiuwen_exception_node_id";

    private static final String DATA_EXCEPTION = "dataException";

    // 节点首次响应时间；如大模型节点，表示首token时间
    private static final String PREFILL_TIME = "firstTokenTime";

    // 节点首次运行时间；如大模型节点，表示真正请求的时间
    private static final String STARTUP_TIME = "requestStartTime";

    // 提问器历史输入key值
    private static final List<String> MESSAGE_ROLE = List.of("user", "assistant", "system");

    // 交互式节点（提问器，input）
    private static final List<String> INTERACTION_NODE = List.of(NodeType.QUESTIONER.getEiType(),
        NodeType.INPUT.getEiType(), NodeType.QA.getEiType());

    @Value("${redis.max_debug_msg_size:10000}")
    private int maxDebugMsgLength;

    private static int maxMsgLength = 10000;

    @PostConstruct
    public void postConstruct() {
        JiuwenEventProcessor.maxMsgLength = maxDebugMsgLength;
    }

    /**
     * 记录九问事件
     *
     * @param jiuwenEvent 九问事件
     * @param eventType 九问事件类型
     * @param instance 工作流实例
     */
    @SuppressWarnings("unchecked")
    public void recordEvent(JiuwenEvent jiuwenEvent, JiuwenEventType eventType, WorkflowInstanceEntity instance) {
        // 九问原始事件日志打印
        if (TO_RECORD_EVENTS.contains(eventType)) {
            List<JiuwenEvent> eventList = instance.getEventList();
            if (eventList == null) {
                eventList = new ArrayList<>();
                instance.setEventList(eventList);
            }
            try {
                if ("jiuwen.setVariable".equals(jiuwenEvent.getData().getComponentType())) {
                    Map<String, Object> userFields = (Map<String, Object>) jiuwenEvent.getData()
                        .getInputs()
                        .get("userFields");
                    for (Map.Entry<String, Object> entry : userFields.entrySet()) {
                        if (entry.getValue() == null) {
                            entry.setValue("<null>");
                        }
                    }
                }
            } catch (Exception e) {
                log.warn("Fix set variable input fail.");
            }
            eventList.add(jiuwenEvent);
        }
    }

    /**
     * 处理exception原始事件
     *
     * @param eventStr 原始事件信息
     */
    public String processOriginEvent(String eventStr) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode rootNode = mapper.readTree(eventStr);

            if (rootNode.has("data") && rootNode.get("data").has(JIUWEN_EXCEPTION_NODE_ID)) {
                ObjectNode objectNode = (ObjectNode) rootNode;
                JsonNode dataNode = objectNode.get("data");
                objectNode.remove("data");
                objectNode.set(DATA_EXCEPTION, dataNode);
                return mapper.writeValueAsString(rootNode);
            } else {
                return eventStr;
            }
        } catch (Exception e) {
            log.error("transfer exception event error!");
            throw new AgentStudioException(StudioError.WORKFLOW_EXCEPTION_CONFIG_INVALID);
        }
    }

    /**
     * 九问节点类型转换为EI节点类型
     *
     * @param eventData 九问事件
     * @return NodeRunInfo
     */
    public static NodeRunInfo convertNodeRunInfo(JiuwenEventData eventData) {
        NodeRunInfo nodeRun = new NodeRunInfo();
        nodeRun.setNodeId(eventData.getComponentId());
        nodeRun.setParentNodeId(eventData.getParentNodeId());
        nodeRun.setExecutionId(eventData.getTraceId());
        nodeRun.setNodeName(eventData.getComponentName());
        NodeType nodeType = NodeType.fromInsight(eventData.getComponentType());

        // 知识库类型后台插件逻辑实现，映射为插件类型
        nodeRun.setNodeType(nodeType == NodeType.KNOWLEDGE_REPO ? NodeType.PLUGIN.getEiType() : nodeType.getEiType());
        nodeRun.setParentWorkflowId(eventData.getAgentParentInvokeId());
        nodeRun.setInputs(parseParams(eventData.getInputs()));

        nodeRun.setOutputs(parseParams(eventData.getOutputs()));
        nodeRun.setMetadata(eventData.getMetaData());
        nodeRun.setAgentId(eventData.getAgentId());
        nodeRun.setMemory(eventData.getMemory());

        // 循环节点相关参数
        nodeRun.setLoopNodeId(eventData.getLoopNodeId());
        nodeRun.setLoopIndex(eventData.getLoopIndex());

        // onInvokeData字段处理
        if (!CollectionUtils.isEmpty(eventData.getOnInvokeData())) {
            convertJiuwenInvokeData(nodeRun, eventData.getOnInvokeData());
        }

        // 时间日期转换格式
        if (StringUtils.isNotEmpty(eventData.getStartTime())) {
            OffsetDateTime offsetStartTime = OffsetDateTime.parse(eventData.getStartTime());
            nodeRun.setStartTime(offsetStartTime.toInstant().toEpochMilli());
        }
        if (StringUtils.isNotEmpty(eventData.getEndTime())) {
            OffsetDateTime offsetEndTime = OffsetDateTime.parse(eventData.getEndTime());
            nodeRun.setEndTime(offsetEndTime.toInstant().toEpochMilli());
        }

        // 时间日期转换格式. 调测接口真正启动的时间
        if (!Objects.isNull(eventData.getOutputs()) && !Objects.isNull(eventData.getOutputs().get(STARTUP_TIME))
            && StringUtils.isNotEmpty(eventData.getOutputs().get(STARTUP_TIME).toString())) {
            nodeRun.setStartupTime(
                OffsetDateTime.parse(eventData.getOutputs().get(STARTUP_TIME).toString()).toInstant().toEpochMilli());
        }

        // 时间日期转换格式. 预热时间，如大模型节点表示首token时间
        if (!Objects.isNull(eventData.getOutputs()) && !Objects.isNull(eventData.getOutputs().get(PREFILL_TIME))
            && StringUtils.isNotEmpty(eventData.getOutputs().get(PREFILL_TIME).toString())) {
            nodeRun.setPrefillTime(
                OffsetDateTime.parse(eventData.getOutputs().get(PREFILL_TIME).toString()).toInstant().toEpochMilli());
        }

        // 节点状态从九问返回值解析转换
        switch (eventData.getStatus()) {
            case START: {
                nodeRun.setStatus(new Status().setCode(0).setDesc("succeeded"));
                nodeRun.setNodeStatus(NodeRunInfo.NodeStatusEnum.STARTED);
                break;
            }
            case ERROR: {
                nodeRun.setNodeStatus(NodeRunInfo.NodeStatusEnum.FINISHED);
                if (eventData.getInnerError() != null) {
                    handleInnerError(nodeRun, eventData.getInnerError());
                } else {
                    nodeRun.setStatus(new Status().setCode(eventData.getError().getErrorCode()).setDesc("failed"));
                    nodeRun.setErrorMessage(eventData.getError().getMessage());
                }
                break;
            }
            case RUNNING: {
                nodeRun.setStatus(new Status().setCode(1).setDesc("waiting"));
                nodeRun.setNodeStatus(NodeRunInfo.NodeStatusEnum.WAIT);
                break;
            }
            case FINISH: {
                nodeRun.setStatus(new Status().setCode(0).setDesc("succeeded"));
                nodeRun.setNodeStatus(NodeRunInfo.NodeStatusEnum.FINISHED);
                handleInnerError(nodeRun, eventData.getInnerError());
                break;
            }
            default: {
                log.error(String.format("unexpect status type received: %s", eventData.getStatus()));
                nodeRun.setStatus(new Status().setCode(-1).setDesc("unknown type received"));
                nodeRun.setNodeStatus(NodeRunInfo.NodeStatusEnum.FINISHED);
                nodeRun.setErrorMessage(eventData.getError().getMessage());
            }
        }
        return nodeRun;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> parseParams(Map<String, Object> params) {
        Map<String, Object> result = new HashMap<>();
        if (params == null) {
            return result;
        }
        // 解析userFields和systemFields，平铺于inputs和outputs下
        for (Map.Entry<String, Object> entry : params.entrySet()) {
            if ((Objects.equals(entry.getKey(), USER_FIELDS) || Objects.equals(entry.getKey(), SYSTEM_FIELDS)
                || Objects.equals(entry.getKey(), ENVIRONMENT_FIELDS)) && entry.getValue() instanceof Map) {
                Map<String, Object> obj = (Map<String, Object>) entry.getValue();
                result.putAll(obj);
            } else {
                result.put(entry.getKey(), entry.getValue());
            }
        }
        return result;
    }

    private static void convertJiuwenInvokeData(NodeRunInfo nodeRunInfo, List<Map<String, Object>> invokeData) {
        List<Message> messages = new ArrayList<>();
        Map<String, Object> metadata = nodeRunInfo.getMetadata() != null ? nodeRunInfo.getMetadata() : new HashMap<>();
        valueClipping(invokeData);
        for (Map<String, Object> invokeDatum : invokeData) {
            for (Map.Entry<String, Object> entry : invokeDatum.entrySet()) {
                if (MESSAGE_ROLE.contains(entry.getKey())) {
                    // message相关信息(提问器、消息节点)置于message字段下
                    messages.add(new Message().setRole(entry.getKey())
                        .setContent(entry.getValue() != null ? entry.getValue().toString() : StringUtils.EMPTY));
                } else {
                    // 非message相关信息包括大模型原始回复置于metadata中
                    metadata.put(entry.getKey(), entry.getValue());
                }
            }
        }
        nodeRunInfo.setMessages(messages);
        if (!metadata.isEmpty()) {
            nodeRunInfo.setMetadata(metadata);
        }
    }

    private static void handleInnerError(NodeRunInfo nodeRun, JiuwenEventDataInnerError innerError) {
        if (innerError == null) {
            return;
        }
        NodeRunInfoInnerError nodeRunInfoInnerError = new NodeRunInfoInnerError().setIsSuccess(
            innerError.isIsSuccess());
        if (Boolean.FALSE.equals(nodeRunInfoInnerError.isIsSuccess())) {
            nodeRun.setStatus(new Status().setCode(WorkflowRunStatus.FAILED.getStatus().getCode()).setDesc("failed"));
            nodeRun.setErrorMessage(innerError.getErrorBody().getErrorMessage());
            nodeRunInfoInnerError.setErrorBody(
                new NodeRunInfoInnerErrorErrorBody().setErrorCode(innerError.getErrorBody().getErrorCode())
                    .setErrorMessage(innerError.getErrorBody().getErrorMessage()));
        }
        nodeRun.setInnerError(nodeRunInfoInnerError);
    }

    @SuppressWarnings("unchecked")
    static void valueClipping(Object data) {
        if (!(data instanceof List)) {
            return;
        }
        listValueClipping((List<Object>) data);
    }

    @SuppressWarnings("unchecked")
    private static void listValueClipping(List<Object> invokeData) {
        int idx = 0;
        for (Object value : invokeData) {
            if (value instanceof List) {
                listValueClipping((List<Object>) value);
            } else if (value instanceof Map) {
                mapValueClipping((Map<String, Object>) value);
            } else if (value instanceof String) {
                invokeData.set(idx, StringUtils.abbreviate((String) value, maxMsgLength));
            }
            ++idx;
        }
    }

    @SuppressWarnings("unchecked")
    private static void mapValueClipping(Map<String, Object> data) {
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof List) {
                listValueClipping((List<Object>) value);
            } else if (value instanceof Map) {
                mapValueClipping((Map<String, Object>) value);
            } else if (value instanceof String) {
                entry.setValue(StringUtils.abbreviate((String) value, maxMsgLength));
            }
        }
    }
}
