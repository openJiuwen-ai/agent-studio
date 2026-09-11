/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.Message;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.WorkflowMessageEntity;

import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@MockitoSettings(strictness = Strictness.LENIENT)
class WorkflowUtilsTest {

    @Test
    void testGetWorkflowNodeID_Found() {
        WorkflowNodeVO node = new WorkflowNodeVO();
        node.setId("node1");
        List<WorkflowNodeVO> nodes = List.of(node);
        WorkflowNodeVO result = WorkflowUtils.getWorkflowNodeID("node1", nodes);
        assertEquals("node1", result.getId());
    }

    @Test
    void testGetWorkflowNodeID_NotFound() {
        WorkflowNodeVO node = new WorkflowNodeVO();
        node.setId("node1");
        assertThrows(AgentStudioException.class, () -> WorkflowUtils.getWorkflowNodeID("node2", List.of(node)));
    }

    @Test
    void testGetWorkflowNodeID_EmptyNodeId() {
        assertNull(WorkflowUtils.getWorkflowNodeID("", List.of()));
    }

    @Test
    void testGetWorkflowNodeID_NullNodeId() {
        assertNull(WorkflowUtils.getWorkflowNodeID(null, List.of()));
    }

    @Test
    void testGetWorkflowNodeID_EmptyList() {
        assertThrows(AgentStudioException.class, () -> WorkflowUtils.getWorkflowNodeID("node1", List.of()));
    }

    @Test
    void testConvertMessageToMessageEntity() {
        Message msg = new Message();
        msg.setRole("user");
        msg.setContent("hello");
        List<WorkflowMessageEntity> result = WorkflowUtils.convertMessageToMessageEntity("session1", List.of(msg));
        assertEquals(1, result.size());
        assertEquals("user", result.get(0).getRole());
        assertEquals("hello", result.get(0).getContent());
        assertEquals("session1", result.get(0).getSessionId());
        assertNotNull(result.get(0).getMessageId());
    }

    @Test
    void testConvertMessageToMessageEntity_EmptyList() {
        List<WorkflowMessageEntity> result = WorkflowUtils.convertMessageToMessageEntity("session1", List.of());
        assertTrue(result.isEmpty());
    }

    @Test
    void testFormatWorkflowType_Empty() {
        assertEquals("string", WorkflowUtils.formatWorkflowType(""));
    }

    @Test
    void testFormatWorkflowType_Null() {
        assertEquals("string", WorkflowUtils.formatWorkflowType(null));
    }

    @Test
    void testFormatWorkflowType_File() {
        assertEquals("string", WorkflowUtils.formatWorkflowType("file"));
    }

    @Test
    void testFormatWorkflowType_Number() {
        assertEquals("number", WorkflowUtils.formatWorkflowType("NUMBER"));
    }

    @Test
    void testFormatWorkflowActualType_Empty() {
        assertEquals("string", WorkflowUtils.formatWorkflowActualType(""));
    }

    @Test
    void testFormatWorkflowActualType_Null() {
        assertEquals("string", WorkflowUtils.formatWorkflowActualType(null));
    }

    @Test
    void testFormatWorkflowActualType_Boolean() {
        assertEquals("boolean", WorkflowUtils.formatWorkflowActualType("BOOLEAN"));
    }

    @Test
    void testParseHttpEndpoint_Valid() {
        Map<String, Object> configs = new HashMap<>();
        configs.put(CommonConstant.Http.ENDPOINT, "http://example.com/api");
        String result = WorkflowUtils.parseHttpEndpoint(configs);
        assertEquals("http://example.com/api", result);
    }

    @Test
    void testParseHttpEndpoint_Null() {
        assertEquals("", WorkflowUtils.parseHttpEndpoint(null));
    }

    @Test
    void testParseHttpEndpoint_NoEndpoint() {
        Map<String, Object> configs = new HashMap<>();
        assertEquals("", WorkflowUtils.parseHttpEndpoint(configs));
    }

    @Test
    void testParseHttpEndpoint_InvalidUrl() {
        Map<String, Object> configs = new HashMap<>();
        configs.put(CommonConstant.Http.ENDPOINT, "://invalid");
        String result = WorkflowUtils.parseHttpEndpoint(configs);
        assertEquals("", result);
    }

    @Test
    void testRemoveQueryParamsFromUrl_Valid() {
        String result = WorkflowUtils.removeQueryParamsFromUrl("http://example.com/path?key=value");
        assertEquals("http://example.com/path", result);
    }

    @Test
    void testRemoveQueryParamsFromUrl_NoQuery() {
        String result = WorkflowUtils.removeQueryParamsFromUrl("http://example.com/path");
        assertEquals("http://example.com/path", result);
    }

    @Test
    void testRemoveQueryParamsFromUrl_Null() {
        assertNull(WorkflowUtils.removeQueryParamsFromUrl(null));
    }

    @Test
    void testRemoveQueryParamsFromUrl_Empty() {
        assertEquals("", WorkflowUtils.removeQueryParamsFromUrl(""));
    }

    @Test
    void testExtractQueryParamsFromUrl_Valid() {
        Map<String, String> result = WorkflowUtils.extractQueryParamsFromUrl("http://example.com?key=val&foo=bar");
        assertEquals("val", result.get("key"));
        assertEquals("bar", result.get("foo"));
    }

    @Test
    void testExtractQueryParamsFromUrl_NoQuery() {
        Map<String, String> result = WorkflowUtils.extractQueryParamsFromUrl("http://example.com");
        assertTrue(result.isEmpty());
    }

    @Test
    void testExtractQueryParamsFromUrl_Null() {
        Map<String, String> result = WorkflowUtils.extractQueryParamsFromUrl(null);
        assertTrue(result.isEmpty());
    }

    @Test
    void testExtractQueryParamsFromUrl_Empty() {
        Map<String, String> result = WorkflowUtils.extractQueryParamsFromUrl("");
        assertTrue(result.isEmpty());
    }

    @Test
    void testExtractQueryParamsFromUrl_KeyOnly() {
        Map<String, String> result = WorkflowUtils.extractQueryParamsFromUrl("http://example.com?key");
        assertEquals("", result.get("key"));
    }

    @Test
    void testParseAuthInfo_NullAuthInfo() {
        Object result = WorkflowUtils.parseAuthInfo(null);
        assertTrue(result instanceof Map);
        assertTrue(((Map<?, ?>) result).isEmpty());
    }

    @Test
    void testParseAuthInfo_NullScope() {
        AuthInfo authInfo = new AuthInfo();
        Object result = WorkflowUtils.parseAuthInfo(authInfo);
        assertTrue(result instanceof Map);
        assertTrue(((Map<?, ?>) result).isEmpty());
    }

    @Test
    void testParseAuthInfo_ThreeArgs_NullAuthInfo() {
        Object result = WorkflowUtils.parseAuthInfo("type", "config", null);
        assertTrue(result instanceof Map);
        assertTrue(((Map<?, ?>) result).isEmpty());
    }

    @Test
    void testGetNodesFromMap_SimpleGraph() {
        Map<String, List<String>> edgeMap = new HashMap<>();
        edgeMap.put(CommonConstant.Workflow.NODE_START, List.of("node1"));
        edgeMap.put("node1", List.of("node2"));
        Set<String> visit = new HashSet<>();
        visit.add(CommonConstant.Workflow.NODE_START);
        WorkflowUtils.getNodesFromMap(edgeMap, visit);
        assertTrue(visit.contains("node1"));
        assertTrue(visit.contains("node2"));
    }

    @Test
    void testGetNodesFromMap_EmptyGraph() {
        Map<String, List<String>> edgeMap = new HashMap<>();
        Set<String> visit = new HashSet<>();
        visit.add(CommonConstant.Workflow.NODE_START);
        WorkflowUtils.getNodesFromMap(edgeMap, visit);
        assertEquals(1, visit.size());
    }

    @Test
    void testGetFreeNodes_AllConnected() {
        WorkflowVO workflowVo = new WorkflowVO();
        WorkflowNodeVO startNode = new WorkflowNodeVO();
        startNode.setId(CommonConstant.Workflow.NODE_START);
        WorkflowNodeVO node1 = new WorkflowNodeVO();
        node1.setId("node1");
        WorkflowNodeVO endNode = new WorkflowNodeVO();
        endNode.setId(CommonConstant.Workflow.NODE_END);
        workflowVo.setNodes(List.of(startNode, node1, endNode));

        WorkflowEdgeVO edge1 = new WorkflowEdgeVO();
        edge1.setSource(CommonConstant.Workflow.NODE_START);
        edge1.setTarget("node1");
        WorkflowEdgeVO edge2 = new WorkflowEdgeVO();
        edge2.setSource("node1");
        edge2.setTarget(CommonConstant.Workflow.NODE_END);
        workflowVo.setEdges(List.of(edge1, edge2));

        Set<String> freeNodes = WorkflowUtils.getFreeNodes(workflowVo);
        assertTrue(freeNodes.isEmpty());
    }

    @Test
    void testGetFreeNodes_WithFreeNode() {
        WorkflowVO workflowVo = new WorkflowVO();
        WorkflowNodeVO startNode = new WorkflowNodeVO();
        startNode.setId(CommonConstant.Workflow.NODE_START);
        WorkflowNodeVO node1 = new WorkflowNodeVO();
        node1.setId("node1");
        WorkflowNodeVO freeNode = new WorkflowNodeVO();
        freeNode.setId("freeNode");
        WorkflowNodeVO endNode = new WorkflowNodeVO();
        endNode.setId(CommonConstant.Workflow.NODE_END);
        workflowVo.setNodes(List.of(startNode, node1, freeNode, endNode));

        WorkflowEdgeVO edge1 = new WorkflowEdgeVO();
        edge1.setSource(CommonConstant.Workflow.NODE_START);
        edge1.setTarget("node1");
        WorkflowEdgeVO edge2 = new WorkflowEdgeVO();
        edge2.setSource("node1");
        edge2.setTarget(CommonConstant.Workflow.NODE_END);
        workflowVo.setEdges(List.of(edge1, edge2));

        Set<String> freeNodes = WorkflowUtils.getFreeNodes(workflowVo);
        assertTrue(freeNodes.contains("freeNode"));
        assertEquals(1, freeNodes.size());
    }

    @Test
    void testParseHeadersOfServerConfig_Empty() {
        Object result = WorkflowUtils.parseHeadersOfServerConfig("type", "");
        assertTrue(result instanceof Map);
        assertTrue(((Map<?, ?>) result).isEmpty());
    }

    @Test
    void testParseHeadersOfServerConfig_Null() {
        Object result = WorkflowUtils.parseHeadersOfServerConfig("type", null);
        assertTrue(result instanceof Map);
        assertTrue(((Map<?, ?>) result).isEmpty());
    }

    @Test
    void testBuildOauthConfig_NullOauth() {
        AuthInfo authInfo = new AuthInfo();
        com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.OauthConfig config =
            new com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.OauthConfig();
        assertDoesNotThrow(() -> WorkflowUtils.buildOauthConfig(config, authInfo));
    }

    @Test
    void testBuildAuthIamConfig_NullCredentials() {
        AuthInfo authInfo = new AuthInfo();
        com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.CustomIAMConfig config =
            new com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.CustomIAMConfig();
        assertDoesNotThrow(() -> WorkflowUtils.buildAuthIamConfig(config, authInfo));
    }

    /**
     * 用例描述：验证URL含环境变量占位符时removeQueryParamsFromUrl原样返回URL
     * 预制条件：无特殊前置条件
     * 输入参数：URL含${_env.plugin_url_params.var}占位符
     * 预期结果：返回原始URL不做任何修改
     *
     * Given：前置条件 / 初始状态
     *  1. 构造含环境变量占位符的URL
     * When：执行动作（仅1行核心调用）
     *  执行：WorkflowUtils.removeQueryParamsFromUrl(url)
     * Then：结果校验
     *  1. 断言返回值等于原始URL
     */
    @Test
    void testRemoveQueryParamsFromUrl_EnvPlaceholder() {
        String url = "http://${_env.plugin_url_params.host}/sse?key=value";
        String result = WorkflowUtils.removeQueryParamsFromUrl(url);
        assertEquals(url, result);
    }

    /**
     * 用例描述：验证URL含环境变量占位符时extractQueryParamsFromUrl返回空Map
     * 预制条件：无特殊前置条件
     * 输入参数：URL含${_env.plugin_url_params.var}占位符
     * 预期结果：返回空Map
     */
    @Test
    void testExtractQueryParamsFromUrl_EnvPlaceholder() {
        String url = "http://${_env.plugin_url_params.host}/sse?key=value";
        Map<String, String> result = WorkflowUtils.extractQueryParamsFromUrl(url);
        assertTrue(result.isEmpty());
    }
}
