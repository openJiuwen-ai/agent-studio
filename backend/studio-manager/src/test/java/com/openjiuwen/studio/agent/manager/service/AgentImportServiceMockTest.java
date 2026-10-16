/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2018-2020. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson.JSON;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.ControllerIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportInfo;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;

import java.util.HashMap;
import java.util.Map;

/**
 * Test class for AgentImportService.uploadControllerDsl method
 */
public class AgentImportServiceMockTest {

    @Mock
    private AgentMapper agentMapper;

    @Mock
    private AgentCommonService agentCommonService;

    @Mock
    private ControllerManagementService controllerManagementService;

    @Mock
    private IrAdapterService irAdapterService;

    @Mock
    private MgObsService obsService;

    @InjectMocks
    private AgentImportService agentImportService;

    private AutoCloseable closeable;

    @BeforeEach
    void setUp() {
        closeable = MockitoAnnotations.openMocks(this);
    }

    @Test
    void testUploadControllerDsl_WithVersion() {
        // Given
        Agent agent = new Agent();
        agent.setAgentId("test-agent-id");
        agent.setName("test-agent");
        
        when(agentMapper.selectById("test-id")).thenReturn(agent);
        
        // Mock controllerManagementService.groupDslNodes
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        when(controllerManagementService.groupDslNodes(any(ControllerVO.class))).thenReturn(nodesGroupByTypeId);
        
        // Mock controllerManagementService.dslToIr
        ControllerIR ir = mock(ControllerIR.class);
        when(controllerManagementService.dslToIr(any(ControllerVO.class), any(), anyBoolean())).thenReturn(ir);
        
        // Mock agentCommonService methods - void methods, use doNothing()
        doNothing().when(agentCommonService).uploadToObsWithVersion(any(Agent.class), any(Object.class), anyString(), anyString());
        doNothing().when(agentCommonService).uploadToObsNoNullWithVersion(any(Agent.class), any(Object.class), anyString(), anyString());
        // Mock String return methods
        when(agentCommonService.uploadToObs(any(Agent.class), any(Object.class), anyString())).thenReturn("success");
        when(agentCommonService.uploadToObsNoNull(any(Agent.class), any(Object.class), anyString())).thenReturn("success");
        
        // Mock ImportInfo
        ImportInfo importInfo = mock(ImportInfo.class);
        when(importInfo.getDsl()).thenReturn("{}");
        
        // When & Then - should not throw exception
        assertDoesNotThrow(() -> {
            agentImportService.uploadControllerDsl(importInfo, "test-id", "v1.0.0");
        });
    }

    @Test
    void testUploadControllerDsl_WithoutVersion() {
        // Given
        Agent agent = new Agent();
        agent.setAgentId("test-agent-id");
        agent.setName("test-agent");
        
        when(agentMapper.selectById("test-id")).thenReturn(agent);
        
        // Mock controllerManagementService.groupDslNodes
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        when(controllerManagementService.groupDslNodes(any(ControllerVO.class))).thenReturn(nodesGroupByTypeId);
        
        // Mock controllerManagementService.dslToIr
        ControllerIR ir = mock(ControllerIR.class);
        when(controllerManagementService.dslToIr(any(ControllerVO.class), any(), anyBoolean())).thenReturn(ir);
        
        // Mock agentCommonService methods - void methods, use doNothing()
        doNothing().when(agentCommonService).uploadToObsWithVersion(any(Agent.class), any(Object.class), anyString(), anyString());
        doNothing().when(agentCommonService).uploadToObsNoNullWithVersion(any(Agent.class), any(Object.class), anyString(), anyString());
        // Mock String return methods
        when(agentCommonService.uploadToObs(any(Agent.class), any(Object.class), anyString())).thenReturn("success");
        when(agentCommonService.uploadToObsNoNull(any(Agent.class), any(Object.class), anyString())).thenReturn("success");
        
        // Mock ImportInfo
        ImportInfo importInfo = mock(ImportInfo.class);
        when(importInfo.getDsl()).thenReturn("{}");
        
        // When & Then - should not throw exception
        assertDoesNotThrow(() -> {
            agentImportService.uploadControllerDsl(importInfo, "test-id", null);
        });
    }

    @Test
    void testUploadAgentDsl_CommonAgentType() {
        try (MockedStatic<JSON> jsonMockedStatic = Mockito.mockStatic(JSON.class)) {
            Agent agent = new Agent();
            agent.setSubType(CommonConstant.COMMON_AGENT_TYPE);
            agent.setAgentId("commonId");
            AgentInfo agentInfo = mock(AgentInfo.class);
            when(agentCommonService.buildComplexAgentInfo(any(Agent.class))).thenReturn(agentInfo);
            Map<String, Object> metadata = new HashMap<>();
            when(agentCommonService.parseMetadata(any(Agent.class))).thenReturn(metadata);

            Map<String, Object> irInfo = new HashMap<>();
            when(irAdapterService.adaptAgent(any(Agent.class), any())).thenReturn(irInfo);
            jsonMockedStatic.when(() -> JSON.toJSONString(irInfo)).thenReturn("serializedIrInfo");

            ImportInfo importInfo = mock(ImportInfo.class);
            String id = "commonId";
            String objectKey = "commonObjectKey";
            agentImportService.uploadAgentDsl(importInfo, id, objectKey);
        }
    }

    @Test
    void testUploadAgentDsl_DEEPRESEARCH_TYPE() {
        try (MockedStatic<JSON> jsonMockedStatic = Mockito.mockStatic(JSON.class)) {
            Agent agent = new Agent();
            agent.setSubType(CommonConstant.DEEPRESEARCH_TYPE);
            agent.setAgentId("deepresearchId");

            AgentInfo agentInfo = mock(AgentInfo.class);
            when(agentCommonService.buildComplexAgentInfo(any(Agent.class))).thenReturn(agentInfo);

            Map<String, Object> metadata = new HashMap<>();
            when(agentCommonService.parseMetadata(any(Agent.class))).thenReturn(metadata);

            Map<String, Object> irInfo = new HashMap<>();
            when(irAdapterService.adaptAgent(any(Agent.class), any())).thenReturn(irInfo);
            jsonMockedStatic.when(() -> JSON.toJSONString(irInfo)).thenReturn("serializedIrInfo");

            ImportInfo importInfo = mock(ImportInfo.class);
            String id = "commonId";
            String objectKey = "commonObjectKey";
            agentImportService.uploadAgentDsl(importInfo, id, objectKey);
        }
    }

    @Test
    void testUploadAgentDsl_UnsupportedSubType() throws Exception {
        Agent agent = mock(Agent.class);
        when(agent.getSubType()).thenReturn("unsupportedType");

        ImportInfo importInfo = mock(ImportInfo.class);
        String id = "unsupportedId";
        String objectKey = "unsupportedObjectKey";

        agentImportService.uploadAgentDsl(importInfo, id, objectKey);
        // 由于方法捕获异常并记录日志，不会抛出异常
    }

    @Test
    void testUploadAgentDsl_ExceptionInCommonAgentType() throws Exception {
        Agent agent = mock(Agent.class);
        when(agent.getSubType()).thenReturn(CommonConstant.COMMON_AGENT_TYPE);
        when(agent.getAgentId()).thenReturn("commonAgentId");

        when(agentCommonService.buildComplexAgentInfo(any(Agent.class)))
            .thenThrow(new RuntimeException("Test exception"));

        ImportInfo importInfo = mock(ImportInfo.class);
        String id = "commonId";
        String objectKey = "commonObjectKey";

        agentImportService.uploadAgentDsl(importInfo, id, objectKey);
        // 由于方法捕获异常并记录日志，不会抛出异常
    }
}
