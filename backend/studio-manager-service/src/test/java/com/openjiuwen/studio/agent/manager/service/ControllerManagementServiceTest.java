/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOAgents;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOWorkflows;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.ModelConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeConfigVO;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentMode;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentNodeType;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ControllerManagementServiceTest {

    private AgentMapper agentMapper;
    private WorkflowManagementService workflowManagementService;
    private AgentCommonService agentCommonService;
    private MappingMapper mappingMapper;
    private ReleaseVersionMapper releaseVersionMapper;
    private WorkflowMapper workflowMapper;
    private MgObsService mgObsService;
    private ModelServiceManager modelServiceManager;
    private ShareResourceMapper shareResourceMapper;
    private RelationManagementService relationManagementService;
    private AgentMemoryConfigService agentMemoryConfigService;
    private IrAdapterService irAdapterService;

    private ControllerManagementService controllerManagementService;

    @BeforeEach
    void setUp() {
        agentMapper = mock(AgentMapper.class);
        workflowManagementService = mock(WorkflowManagementService.class);
        agentCommonService = mock(AgentCommonService.class);
        mappingMapper = mock(MappingMapper.class);
        releaseVersionMapper = mock(ReleaseVersionMapper.class);
        workflowMapper = mock(WorkflowMapper.class);
        mgObsService = mock(MgObsService.class);
        modelServiceManager = mock(ModelServiceManager.class);
        shareResourceMapper = mock(ShareResourceMapper.class);
        relationManagementService = mock(RelationManagementService.class);
        agentMemoryConfigService = mock(AgentMemoryConfigService.class);
        irAdapterService = mock(IrAdapterService.class);

        MockitoAnnotations.openMocks(this);
        controllerManagementService = new ControllerManagementService();
        ReflectionTestUtils.setField(controllerManagementService, "agentMapper", agentMapper);
        ReflectionTestUtils.setField(controllerManagementService, "workflowManagementService", workflowManagementService);
        ReflectionTestUtils.setField(controllerManagementService, "agentCommonService", agentCommonService);
        ReflectionTestUtils.setField(controllerManagementService, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(controllerManagementService, "releaseVersionMapper", releaseVersionMapper);
        ReflectionTestUtils.setField(controllerManagementService, "workflowMapper", workflowMapper);
        ReflectionTestUtils.setField(controllerManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(controllerManagementService, "modelServiceManager", modelServiceManager);
        ReflectionTestUtils.setField(controllerManagementService, "shareResourceMapper", shareResourceMapper);
        ReflectionTestUtils.setField(controllerManagementService, "relationManagementService", relationManagementService);
        ReflectionTestUtils.setField(controllerManagementService, "agentMemoryConfigService", agentMemoryConfigService);
        ReflectionTestUtils.setField(controllerManagementService, "irAdapterService", irAdapterService);
        ReflectionTestUtils.setField(controllerManagementService, "showIntentParamEnable", false);
        ReflectionTestUtils.setField(controllerManagementService, "controllerInitIntentDsl", "{}");
        ReflectionTestUtils.setField(controllerManagementService, "controllerInitIntentDslEn", "{}");
        ReflectionTestUtils.setField(controllerManagementService, "controllerInitDsl", "{}");
        ReflectionTestUtils.setField(controllerManagementService, "controllerInitDslEn", "{}");
        ReflectionTestUtils.setField(controllerManagementService, "controllerInitIr", "{}");
        ReflectionTestUtils.setField(controllerManagementService, "uniqueWorkflowTypes", "type1,type2");
        ReflectionTestUtils.setField(controllerManagementService, "maxIterationConf", 10);
        ReflectionTestUtils.setField(controllerManagementService, "chatHistoryMaxTurnConf", 5);
        ReflectionTestUtils.setField(controllerManagementService, "globalIntendDefaultAction", "default");
        ReflectionTestUtils.setField(controllerManagementService, "controllerWorkflowLimit", 5);
        ReflectionTestUtils.setField(controllerManagementService, "controllerSubAgentLimit", 3);
        ReflectionTestUtils.setField(controllerManagementService, "controllerSubAgentMaxDepth", 2);
        ReflectionTestUtils.setField(controllerManagementService, "workflowInteractiveTypes", "type1,type2");
    }

    @Test
    void testGetControllerNode_Success() {
        ControllerNodeVO nodeVo = new ControllerNodeVO();
        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("node-1", nodeVo);

        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);

        ControllerNodeVO result = controllerManagementService.getControllerNode(nodesGroupByTypeId);

        assertNotNull(result);
        assertEquals(nodeVo, result);
    }

    @Test
    void testGetControllerNode_EmptyControllerMap() {
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), Collections.emptyMap());

        assertThrows(AgentStudioException.class, () ->
            controllerManagementService.getControllerNode(nodesGroupByTypeId));
    }

    @Test
    void testGetControllerNode_NullControllerMap() {
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();

        assertThrows(AgentStudioException.class, () ->
            controllerManagementService.getControllerNode(nodesGroupByTypeId));
    }

    @Test
    void testGetControllerNode_MissingControllerType() {
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put("other_type", new HashMap<>());

        assertThrows(AgentStudioException.class, () ->
            controllerManagementService.getControllerNode(nodesGroupByTypeId));
    }

    // ==================== recordRefModel tests ====================

    @Test
    void testRecordRefModel_ModelNull_DeletesMapping() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        // model is null

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("node-1", controllerNode);
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);

        controllerManagementService.recordRefModel(controllerVo, nodesGroupByTypeId);

        verify(mappingMapper).deleteBatchByAppIdAndResourceType("test-id", ResourceTypeEnum.MODEL.toString());
        verify(mappingMapper, never()).insert(any());
        verify(mappingMapper, never()).updateById(any());
    }

    @Test
    void testRecordRefModel_ModelDeploymentIdNull_DeletesMapping() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        configVo.setModel(new ModelConfigVO()); // modelDeploymentId is null

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("node-1", controllerNode);
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);

        controllerManagementService.recordRefModel(controllerVo, nodesGroupByTypeId);

        verify(mappingMapper).deleteBatchByAppIdAndResourceType("test-id", ResourceTypeEnum.MODEL.toString());
        verify(mappingMapper, never()).insert(any());
        verify(mappingMapper, never()).updateById(any());
    }

    @Test
    void testRecordRefModel_ConfigsNull_ReturnsEarly() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        // configs is null

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("node-1", controllerNode);
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);

        controllerManagementService.recordRefModel(controllerVo, nodesGroupByTypeId);

        verify(mappingMapper, never()).deleteBatchByAppIdAndResourceType(any(), any());
        verify(mappingMapper, never()).insert(any());
        verify(mappingMapper, never()).updateById(any());
    }

    @Test
    void testRecordRefModel_ValidModel_NoOldMapping_Inserts() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        configVo.setModel(new ModelConfigVO()
            .setModelDeploymentId("model-deploy-id")
            .setModelName("test-model")
            .setModelType("llm"));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("node-1", controllerNode);
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);

        when(mappingMapper.selectAllByAppId("test-id")).thenReturn(Collections.emptyList());

        controllerManagementService.recordRefModel(controllerVo, nodesGroupByTypeId);

        verify(mappingMapper).insert(any(MappingEntity.class));
        verify(mappingMapper, never()).updateById(any());
        verify(mappingMapper, never()).deleteBatchByAppIdAndResourceType(any(), any());
    }

    @Test
    void testRecordRefModel_ValidModel_OldMappingExists_Updates() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        configVo.setModel(new ModelConfigVO()
            .setModelDeploymentId("model-deploy-id")
            .setModelName("test-model")
            .setModelType("llm"));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("node-1", controllerNode);
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);

        MappingEntity oldMapping = new MappingEntity();
        oldMapping.setMappingId("old-mapping-id");
        oldMapping.setResourceType(ResourceTypeEnum.MODEL.toString());
        when(mappingMapper.selectAllByAppId("test-id")).thenReturn(List.of(oldMapping));

        controllerManagementService.recordRefModel(controllerVo, nodesGroupByTypeId);

        verify(mappingMapper).updateById(any(MappingEntity.class));
        verify(mappingMapper, never()).insert(any());
        verify(mappingMapper, never()).deleteBatchByAppIdAndResourceType(any(), any());
    }

    // ==================== recordRefWorkflow tests ====================

    @Test
    void testRecordRefWorkflow_SetsAppTypeToController() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        // Controller node with workflows config
        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOWorkflows wfConfig = new ControllerNodeConfigVOWorkflows();
        wfConfig.setNodeId("wf-node-1");
        configVo.setWorkflows(List.of(wfConfig));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        // Workflow node
        WorkflowNodeConfigVO wfNodeConfig = new WorkflowNodeConfigVO();
        wfNodeConfig.setId("wf-id-1");
        wfNodeConfig.setVersionId("v1");
        wfNodeConfig.setName("test-workflow");
        ControllerNodeVO wfNode = new ControllerNodeVO();
        wfNode.setType(AgentNodeType.WORKFLOW.getType());
        wfNode.setConfigs(wfNodeConfig);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("controller-node-1", controllerNode);
        Map<String, ControllerNodeVO> workflowMap = new HashMap<>();
        workflowMap.put("wf-node-1", wfNode);

        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);
        nodesGroupByTypeId.put(AgentNodeType.WORKFLOW.getType(), workflowMap);

        when(mappingMapper.selectByAppIdAndAppVersion(any(), any(), any(), any()))
            .thenReturn(Collections.emptyList());

        ReflectionTestUtils.invokeMethod(controllerManagementService, "recordRefWorkflow",
            controllerVo, nodesGroupByTypeId);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
        verify(mappingMapper).insertBatch(captor.capture());

        List<MappingEntity> captured = captor.getValue();
        assertNotNull(captured);
        assertFalse(captured.isEmpty());
        assertEquals(CommonConstant.CONTROLLER, captured.get(0).getAppType());
    }

    // ==================== recordRefSubController tests ====================

    @Test
    void testRecordRefSubController_SetsAppTypeToController() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        // Controller node with agents config
        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOAgents agentConfig = new ControllerNodeConfigVOAgents();
        agentConfig.setNodeId("sub-controller-node-1");
        agentConfig.setId("agent-id-1");
        agentConfig.setMode(AgentMode.CONTROLLER.getMode());
        configVo.setAgents(List.of(agentConfig));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        // Sub-controller node
        WorkflowNodeConfigVO subControllerConfig = new WorkflowNodeConfigVO();
        subControllerConfig.setId("sub-controller-id-1");
        subControllerConfig.setVersionId("v1");
        subControllerConfig.setName("test-sub-controller");
        ControllerNodeVO subControllerNode = new ControllerNodeVO();
        subControllerNode.setType(AgentNodeType.SUB_CONTROLLER.getType());
        subControllerNode.setConfigs(subControllerConfig);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("controller-node-1", controllerNode);
        Map<String, ControllerNodeVO> subControllerMap = new HashMap<>();
        subControllerMap.put("sub-controller-node-1", subControllerNode);

        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);
        nodesGroupByTypeId.put(AgentNodeType.SUB_CONTROLLER.getType(), subControllerMap);

        when(mappingMapper.selectByAppIdAndAppVersion(any(), any(), any(), any()))
            .thenReturn(Collections.emptyList());

        ReflectionTestUtils.invokeMethod(controllerManagementService, "recordRefSubController",
            controllerVo, nodesGroupByTypeId);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
        verify(mappingMapper).insertBatch(captor.capture());

        List<MappingEntity> captured = captor.getValue();
        assertNotNull(captured);
        assertFalse(captured.isEmpty());
        assertEquals(CommonConstant.CONTROLLER, captured.get(0).getAppType());
    }

    // ==================== recordRefAgent tests ====================

    @Test
    void testRecordRefAgent_SetsAppTypeToController() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        // Controller node with agents config
        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOAgents agentConfig = new ControllerNodeConfigVOAgents();
        agentConfig.setNodeId("agent-node-1");
        agentConfig.setId("agent-id-1");
        agentConfig.setMode(AgentMode.PLANEXECUTE.getMode());
        configVo.setAgents(List.of(agentConfig));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        // Agent node
        WorkflowNodeConfigVO agentNodeConfig = new WorkflowNodeConfigVO();
        agentNodeConfig.setId("agent-resource-id-1");
        agentNodeConfig.setVersionId("v1");
        agentNodeConfig.setName("test-agent");
        ControllerNodeVO agentNode = new ControllerNodeVO();
        agentNode.setType(AgentNodeType.AGENT.getType());
        agentNode.setConfigs(agentNodeConfig);

        Map<String, ControllerNodeVO> controllerMap = new HashMap<>();
        controllerMap.put("controller-node-1", controllerNode);
        Map<String, ControllerNodeVO> agentNodeMap = new HashMap<>();
        agentNodeMap.put("agent-node-1", agentNode);

        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = new HashMap<>();
        nodesGroupByTypeId.put(AgentNodeType.CONTROLLER.getType(), controllerMap);
        nodesGroupByTypeId.put(AgentNodeType.AGENT.getType(), agentNodeMap);

        when(mappingMapper.selectByAppIdAndAppVersion(any(), any(), any(), any()))
            .thenReturn(Collections.emptyList());

        ReflectionTestUtils.invokeMethod(controllerManagementService, "recordRefAgent",
            controllerVo, nodesGroupByTypeId);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
        verify(mappingMapper).insertBatch(captor.capture());

        List<MappingEntity> captured = captor.getValue();
        assertNotNull(captured);
        assertFalse(captured.isEmpty());
        assertEquals(CommonConstant.CONTROLLER, captured.get(0).getAppType());
    }
}
