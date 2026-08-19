/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.AgentInvokeInfo;
import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * AgentRuntimeService 单元测试：覆盖 G.MET.06 修改的
 * convertAgentInvokeInfo（Optional 转换）及调用方 convertAgentExecutionInfo（ifPresent 改造）
 */
class AgentRuntimeServiceTest {

    private static final String START_TIME = "2026-08-19T10:00:00";
    private static final String END_TIME = "2026-08-19T10:00:05";

    private AgentRuntimeService agentRuntimeService;

    @BeforeEach
    void setUp() {
        agentRuntimeService = new AgentRuntimeService();
    }

    private AgentExecuteParams buildParams() {
        return AgentExecuteParams.builder()
            .conversationId("conv-1")
            .executionId("exec-1")
            .modelDeploymentId("md-1")
            .build();
    }

    // ============ convertAgentInvokeInfo ============

    @Test
    void convertInvokeInfo_emptyEndTime_shouldReturnEmpty() {
        JiuwenAgentEventData eventData = new JiuwenAgentEventData().setInvokeType("llm");

        Optional<AgentInvokeInfo> result = agentRuntimeService.convertAgentInvokeInfo(
            new AgentExecutionInfo(), eventData, buildParams());

        assertTrue(result.isEmpty());
    }

    @Test
    void convertInvokeInfo_chainInvoke_shouldReturnEmptyAndFillExecutionInfo() {
        JiuwenAgentEventData eventData = new JiuwenAgentEventData()
            .setInvokeType("chain")
            .setStartTime(START_TIME)
            .setEndTime(END_TIME)
            .setOutputs("九问回答内容");
        AgentExecutionInfo executionInfo = new AgentExecutionInfo();

        Optional<AgentInvokeInfo> result = agentRuntimeService.convertAgentInvokeInfo(executionInfo, eventData,
            buildParams());

        assertTrue(result.isEmpty());
        // 敏感词替换：九问 -> Runtime
        assertEquals("Runtime回答内容", executionInfo.getOutputs());
        assertEquals("succeeded", executionInfo.getStatus());
        assertNotNull(executionInfo.getStartTime());
        assertNotNull(executionInfo.getEndTime());
    }

    @Test
    void convertInvokeInfo_llmInvokeWithError_shouldReturnFailedInfo() {
        JiuwenAgentEventData eventData = new JiuwenAgentEventData()
            .setInvokeType("llm")
            .setInvokeId("node-1")
            .setStartTime(START_TIME)
            .setEndTime(END_TIME)
            .setError("jiuwen service error");
        AgentExecutionInfo executionInfo = new AgentExecutionInfo();

        Optional<AgentInvokeInfo> result = agentRuntimeService.convertAgentInvokeInfo(executionInfo, eventData,
            buildParams());

        assertTrue(result.isPresent());
        AgentInvokeInfo invokeInfo = result.get();
        assertEquals("node-1", invokeInfo.getNodeId());
        assertEquals("llm", invokeInfo.getNodeType());
        assertEquals("failed", invokeInfo.getNodeStatus());
        // errorMessage 原样透传，不做敏感词替换
        assertEquals("jiuwen service error", invokeInfo.getErrorMessage());
        assertEquals("md-1", invokeInfo.getModelDeploymentId());
        // 执行整体状态置为 failed
        assertEquals("failed", executionInfo.getStatus());
    }

    @Test
    void convertInvokeInfo_pluginRetrieval_shouldMapToKnowledgeType() {
        JSONObject instanceAttributes = new JSONObject().fluentPut("plugin_name", "retrieval");
        JiuwenAgentEventData eventData = new JiuwenAgentEventData()
            .setInvokeType("plugin")
            .setInvokeId("node-2")
            .setStartTime(START_TIME)
            .setEndTime(END_TIME)
            .setMetaData(Map.of("instance_attributes", instanceAttributes));

        Optional<AgentInvokeInfo> result = agentRuntimeService.convertAgentInvokeInfo(new AgentExecutionInfo(),
            eventData, buildParams());

        assertTrue(result.isPresent());
        assertEquals("knowledge", result.get().getNodeType());
        assertEquals("知识库", result.get().getNodeName());
    }

    @Test
    void convertInvokeInfo_pluginMcp_shouldMapToMcpType() {
        JSONObject instanceAttributes = new JSONObject()
            .fluentPut("is_mcp", true)
            .fluentPut("server_name", "mcp-server-1");
        JiuwenAgentEventData eventData = new JiuwenAgentEventData()
            .setInvokeType("plugin")
            .setInvokeId("node-3")
            .setStartTime(START_TIME)
            .setEndTime(END_TIME)
            .setMetaData(Map.of("instance_attributes", instanceAttributes));

        Optional<AgentInvokeInfo> result = agentRuntimeService.convertAgentInvokeInfo(new AgentExecutionInfo(),
            eventData, buildParams());

        assertTrue(result.isPresent());
        assertEquals("mcp", result.get().getNodeType());
        assertEquals("mcp-server-1", result.get().getNodeName());
    }

    // ============ convertAgentExecutionInfo（Optional 调用方 ifPresent 改造） ============

    @Test
    void convertExecutionInfo_llmInvoke_shouldAddInvokeToList() {
        JiuwenAgentEventData eventData = new JiuwenAgentEventData()
            .setInvokeType("llm")
            .setInvokeId("node-1")
            .setStartTime(START_TIME)
            .setEndTime(END_TIME)
            .setConversationId("conv-1")
            .setMetaData(Map.of("k", "v"));
        AgentExecutionInfo executionInfo = new AgentExecutionInfo();

        AgentExecutionInfo result = agentRuntimeService.convertAgentExecutionInfo(executionInfo, eventData,
            buildParams());

        assertEquals("conv-1", result.getConversationId());
        assertEquals("exec-1", result.getExecutionId());
        assertNull(result.getInputs());
        assertEquals(1, result.getInvokeList().size());
        assertEquals("llm", result.getInvokeList().get(0).getNodeType());
    }
}
