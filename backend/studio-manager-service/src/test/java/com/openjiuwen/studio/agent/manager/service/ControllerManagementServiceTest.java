/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ControllerAgentIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOAgents;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOWorkflows;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.ModelConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVOErrors;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
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

import com.alibaba.fastjson2.JSON;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

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
    private I18nUtil i18nUtil;
    private ShareResourceManagerService shareResourceManagerService;

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
        i18nUtil = mock(I18nUtil.class);
        shareResourceManagerService = mock(ShareResourceManagerService.class);

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
        ReflectionTestUtils.setField(controllerManagementService, "i18nUtil", i18nUtil);
        ReflectionTestUtils.setField(controllerManagementService, "shareResourceManagerService", shareResourceManagerService);
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
        ReflectionTestUtils.setField(controllerManagementService, "controllerSingleAgentLimit", 10);
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

    // ==================== validateSubWorkflowVersions tests ====================

    @Test
    void testValidateSubWorkflowVersions_DistinguishesReasonByNodeType() {
        // Controller 节点：同时引用一个工作流节点、一个子多智能体节点和一个单智能体节点
        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOWorkflows wfConfig = new ControllerNodeConfigVOWorkflows();
        wfConfig.setNodeId("wf-node-1");
        wfConfig.setType("business");
        ControllerNodeConfigVOAgents subControllerConfig = new ControllerNodeConfigVOAgents();
        subControllerConfig.setNodeId("sub-controller-node-1");
        subControllerConfig.setMode(AgentMode.CONTROLLER.getMode());
        ControllerNodeConfigVOAgents agentConfig = new ControllerNodeConfigVOAgents();
        agentConfig.setNodeId("agent-node-1");
        agentConfig.setMode(AgentMode.PLANEXECUTE.getMode());
        configVo.setWorkflows(List.of(wfConfig));
        configVo.setAgents(List.of(subControllerConfig, agentConfig));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setId("controller-node-1");
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        // 工作流节点：引用已删除的版本
        ControllerNodeVO wfNode = new ControllerNodeVO();
        wfNode.setId("wf-node-1");
        wfNode.setType(AgentNodeType.WORKFLOW.getType());
        wfNode.setConfigs(Map.of("id", "wf-id-1", "version_id", "v-missing"));

        // 子多智能体节点：引用已删除的版本（导入历史包场景）
        ControllerNodeVO subControllerNode = new ControllerNodeVO();
        subControllerNode.setId("sub-controller-node-1");
        subControllerNode.setType(AgentNodeType.SUB_CONTROLLER.getType());
        subControllerNode.setConfigs(Map.of("id", "sub-agent-id-1", "version_id", "v-missing"));

        // 单智能体节点：引用已删除的版本
        ControllerNodeVO agentNode = new ControllerNodeVO();
        agentNode.setId("agent-node-1");
        agentNode.setType(AgentNodeType.AGENT.getType());
        agentNode.setConfigs(Map.of("id", "agent-resource-id-1", "version_id", "v-missing"));

        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setNodes(List.of(controllerNode, wfNode, subControllerNode, agentNode));

        Agent agent = new Agent();
        agent.setAgentId("agent-id");
        agent.setDslPath("dsl-path");

        when(mgObsService.downloadObsFile("dsl-path")).thenReturn(JSON.toJSONString(controllerVo));
        // 工作流版本、子多智能体版本与单智能体版本均不存在
        when(releaseVersionMapper.selectByAppIdAndVersionId(any(), any())).thenReturn(null);
        when(i18nUtil.getMessage("workflow.validate.workflow.node")).thenReturn("子工作流节点版本不存在");
        when(i18nUtil.getMessage("workflow.validate.sub.agent.node")).thenReturn("子智能体节点版本不存在");

        WorkflowValidationVO result = controllerManagementService.validateSubWorkflowVersions(agent);

        assertFalse(result.isSuccess());
        assertNotNull(result.getErrors());
        assertEquals(3, result.getErrors().size());
        Map<String, String> reasonByType = result.getErrors().stream()
            .collect(Collectors.toMap(WorkflowValidationVOErrors::getType, WorkflowValidationVOErrors::getReason));
        assertEquals("子工作流节点版本不存在", reasonByType.get(AgentNodeType.WORKFLOW.getType()));
        // 子多智能体与单智能体版本缺失时统一报"子智能体"文案，不得报子工作流文案误导定位方向
        assertEquals("子智能体节点版本不存在",
            reasonByType.get(AgentNodeType.SUB_CONTROLLER.getType()));
        assertEquals("子智能体节点版本不存在",
            reasonByType.get(AgentNodeType.AGENT.getType()));
    }

    // ==================== sub agent version usability tests ====================

    /**
     * 构造含一个子多智能体节点（SUB_CONTROLLER）的 DSL：controller 节点 agents 列表引用子节点，
     * 版本信息记录在子节点自身 configs（与前端保存结构一致）。
     */
    private ControllerVO buildControllerVoWithSubAgent(String subAgentId, String versionId) {
        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOAgents agentConfig = new ControllerNodeConfigVOAgents();
        agentConfig.setNodeId("sub-controller-node-1");
        agentConfig.setId(subAgentId);
        agentConfig.setMode(AgentMode.CONTROLLER.getMode());
        configVo.setAgents(List.of(agentConfig));
        // dslToIr 校验链路的前置条件：workflows 非空对象（valid 中直接取 size）、model 与 intent 至少其一
        configVo.setWorkflows(List.of());
        configVo.setModel(new ModelConfigVO().setModelDeploymentId("md-1"));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setId("controller-node-1");
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        ControllerNodeVO subControllerNode = new ControllerNodeVO();
        subControllerNode.setId("sub-controller-node-1");
        subControllerNode.setType(AgentNodeType.SUB_CONTROLLER.getType());
        subControllerNode.setConfigs(Map.of("id", subAgentId, "version_id", versionId));

        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setNodes(List.of(controllerNode, subControllerNode));
        return controllerVo;
    }

    /**
     * 跨空间且未共享授权的子智能体引用应被试运行/发布预校验拦截：
     * 版本全局存在但子智能体归属其他空间、又未共享给当前空间时，若无可见性判定会放行，
     * 运行时按 OBS 路径直接加载原空间 IR 越权执行。
     */
    @Test
    void testValidateSubWorkflowVersions_SubAgentCrossWorkspaceNotShared_Blocked() {
        ControllerVO controllerVo = buildControllerVoWithSubAgent("sub-agent-id-1", "v-1");
        Agent agent = new Agent();
        agent.setAgentId("agent-id");
        agent.setDslPath("dsl-path");
        agent.setProjectId("proj-1");
        agent.setWorkspaceId("ws-1");

        when(mgObsService.downloadObsFile("dsl-path")).thenReturn(JSON.toJSONString(controllerVo));
        when(releaseVersionMapper.selectByAppIdAndVersionId("sub-agent-id-1", "v-1")).thenReturn(new ReleaseVersion());
        // 子智能体归属其他空间，且未共享授权给当前空间
        Agent subAgent = new Agent();
        subAgent.setProjectId("proj-2");
        subAgent.setWorkspaceId("ws-2");
        when(agentMapper.selectById("sub-agent-id-1")).thenReturn(subAgent);
        when(shareResourceManagerService.queryShareResourceEntityByResourceIdAndVersionId("sub-agent-id-1", "ws-1",
            "v-1")).thenReturn(null);
        when(i18nUtil.getMessage("workflow.validate.sub.agent.node")).thenReturn("子智能体节点版本不存在");

        WorkflowValidationVO result = controllerManagementService.validateSubWorkflowVersions(agent);

        assertFalse(result.isSuccess());
        assertNotNull(result.getErrors());
        assertEquals(1, result.getErrors().size());
        assertEquals(AgentNodeType.SUB_CONTROLLER.getType(), result.getErrors().get(0).getType());
        assertEquals("子智能体节点版本不存在", result.getErrors().get(0).getReason());
    }

    /**
     * 子智能体归属当前空间时校验通过（版本存在 + 本空间资源）。
     */
    @Test
    void testValidateSubWorkflowVersions_SubAgentSameWorkspace_Passes() {
        ControllerVO controllerVo = buildControllerVoWithSubAgent("sub-agent-id-1", "v-1");
        Agent agent = new Agent();
        agent.setAgentId("agent-id");
        agent.setDslPath("dsl-path");
        agent.setProjectId("proj-1");
        agent.setWorkspaceId("ws-1");

        when(mgObsService.downloadObsFile("dsl-path")).thenReturn(JSON.toJSONString(controllerVo));
        when(releaseVersionMapper.selectByAppIdAndVersionId("sub-agent-id-1", "v-1")).thenReturn(new ReleaseVersion());
        Agent subAgent = new Agent();
        subAgent.setProjectId("proj-1");
        subAgent.setWorkspaceId("ws-1");
        when(agentMapper.selectById("sub-agent-id-1")).thenReturn(subAgent);

        WorkflowValidationVO result = controllerManagementService.validateSubWorkflowVersions(agent);

        assertTrue(result.isSuccess());
    }

    /**
     * 跨空间子智能体已共享授权（scope 授权 + 版本在共享版本列表内）时校验通过。
     */
    @Test
    void testValidateSubWorkflowVersions_SubAgentSharedVersion_Passes() {
        ControllerVO controllerVo = buildControllerVoWithSubAgent("sub-agent-id-1", "v-1");
        Agent agent = new Agent();
        agent.setAgentId("agent-id");
        agent.setDslPath("dsl-path");
        agent.setProjectId("proj-1");
        agent.setWorkspaceId("ws-1");

        when(mgObsService.downloadObsFile("dsl-path")).thenReturn(JSON.toJSONString(controllerVo));
        when(releaseVersionMapper.selectByAppIdAndVersionId("sub-agent-id-1", "v-1")).thenReturn(new ReleaseVersion());
        Agent subAgent = new Agent();
        subAgent.setProjectId("proj-2");
        subAgent.setWorkspaceId("ws-2");
        when(agentMapper.selectById("sub-agent-id-1")).thenReturn(subAgent);
        when(shareResourceManagerService.queryShareResourceEntityByResourceIdAndVersionId("sub-agent-id-1", "ws-1",
            "v-1")).thenReturn(new ShareResourceEntity());

        WorkflowValidationVO result = controllerManagementService.validateSubWorkflowVersions(agent);

        assertTrue(result.isSuccess());
    }

    /**
     * 保存链路（dslToIr flag=true）：子智能体引用的版本不存在时抛出明确错误阻断保存；
     * 导入链路（flag=false）：跳过该校验，保持导入行为与校验引入前一致。
     */
    @Test
    void testDslToIr_SubAgentVersionMissing_SaveBlocked_ImportSkipped() {
        ControllerVO controllerVo = buildControllerVoWithSubAgent("sub-agent-id-1", "v-missing");
        controllerVo.setId("controller-agent-id");
        controllerVo.setName("controller-agent");
        controllerVo.setProjectId("proj-1");
        controllerVo.setWorkspaceId("ws-1");
        controllerVo.setInputs(List.of());
        controllerVo.setGlobalVariables(List.of());
        when(releaseVersionMapper.selectByAppIdAndVersionId("sub-agent-id-1", "v-missing")).thenReturn(null);

        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId =
            controllerManagementService.groupDslNodes(controllerVo);

        // 导入链路：不校验子智能体版本；IR 构建阶段可能因最小化 DSL 报其他错误（兜底捕获），
        // 但不能是子智能体版本错误，且不触发版本查询
        try {
            controllerManagementService.dslToIr(controllerVo, nodesGroupByTypeId, false);
        } catch (AgentStudioException e) {
            assertNotEquals(StudioError.MULTI_AGENT_SUB_WORKFLOW_VERSION_NOT_FOUND, e.getErrorCode());
        }
        verify(releaseVersionMapper, never()).selectByAppIdAndVersionId("sub-agent-id-1", "v-missing");

        // 保存链路：版本不存在时抛出明确错误
        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> controllerManagementService.dslToIr(controllerVo, nodesGroupByTypeId, true));
        assertEquals(StudioError.MULTI_AGENT_SUB_WORKFLOW_VERSION_NOT_FOUND, exception.getErrorCode());
        verify(releaseVersionMapper, times(1)).selectByAppIdAndVersionId("sub-agent-id-1", "v-missing");
    }

    // ==================== 多单智能体挂载（#1523）tests ====================

    /**
     * 构造顶层控制器挂载多个单智能体（PlanExecute/ReAct 混合）的 DSL：
     * controller 节点 agents 列表引用 N 个 Agent 节点，与前端放开多选后的保存结构一致。
     */
    private ControllerVO buildControllerVoWithSingleAgents(List<String> modes) {
        List<ControllerNodeConfigVOAgents> agentConfigs = new ArrayList<>();
        List<ControllerNodeVO> nodes = new ArrayList<>();

        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        for (int i = 0; i < modes.size(); i++) {
            ControllerNodeConfigVOAgents agentConfig = new ControllerNodeConfigVOAgents();
            agentConfig.setNodeId("agent-node-" + i);
            agentConfig.setId("single-agent-" + i);
            agentConfig.setName("single-agent-" + i);
            agentConfig.setMode(modes.get(i));
            agentConfigs.add(agentConfig);

            ControllerNodeVO agentNode = new ControllerNodeVO();
            agentNode.setId("agent-node-" + i);
            agentNode.setType(AgentNodeType.AGENT.getType());
            agentNode.setConfigs(Map.of("id", "single-agent-" + i, "version_id", "v-1",
                "name", "single-agent-" + i));
            nodes.add(agentNode);
        }
        configVo.setAgents(agentConfigs);
        // dslToIr 校验链路的前置条件：workflows 非空对象、model 与 intent 至少其一
        configVo.setWorkflows(List.of());
        configVo.setModel(new ModelConfigVO().setModelDeploymentId("md-1"));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setId("controller-node-1");
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);
        nodes.add(controllerNode);

        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("controller-agent-id");
        controllerVo.setName("controller-agent");
        controllerVo.setProjectId("proj-1");
        controllerVo.setWorkspaceId("ws-1");
        controllerVo.setUpdateTime(String.valueOf(System.currentTimeMillis()));
        controllerVo.setInputs(List.of());
        controllerVo.setGlobalVariables(List.of());
        controllerVo.setNodes(nodes);
        return controllerVo;
    }

    /**
     * 顶层控制器挂载多个单智能体（2 个 PlanExecute + 1 个 ReAct）时校验通过，
     * 且成员按声明顺序完整进入 IR agents 列表、mode 原样透传给运行时。
     */
    @Test
    void testDslToIr_MultipleSingleAgents_PassAndBuiltIntoIr() {
        ReflectionTestUtils.setField(controllerManagementService, "controllerInitIr",
            "{\"schemaVersion\":\"0.6.0\",\"agentVersion\":\"0.6.0\",\"configs\":{\"mode\":\"Controller\","
                + "\"specify_workflow_order\":false,\"agents\":[],\"workflows\":[],\"global_intents\":[],"
                + "\"global_variables\":[]}}");
        ControllerVO controllerVo = buildControllerVoWithSingleAgents(
            List.of(AgentMode.PLANEXECUTE.getMode(), AgentMode.PLANEXECUTE.getMode(), AgentMode.REACT.getMode()));
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId =
            controllerManagementService.groupDslNodes(controllerVo);

        // 版本存在 + 子智能体实体缺失时保守放行（与 isSubAgentVersionUsable 语义一致）
        when(releaseVersionMapper.selectByAppIdAndVersionId(any(), any())).thenReturn(new ReleaseVersion());
        when(agentMapper.selectById(any())).thenReturn(null);
        when(agentCommonService.getAgentObsPath(any(), any(), any())).thenReturn("obs-path");
        // buildIrModelConfig 内取请求上下文，单测线程无请求，直接注入
        RequestContextUtils.setRequestAuthTokenAndProjectId("token", "proj-1");
        try {
            ControllerIR ir = controllerManagementService.dslToIr(controllerVo, nodesGroupByTypeId, true);

            assertNotNull(ir);
            assertNotNull(ir.getConfigs());
            assertEquals(3, ir.getConfigs().getAgents().size());
            List<String> irModes = ir.getConfigs().getAgents().stream()
                .map(ControllerAgentIR::getMode)
                .collect(Collectors.toList());
            assertEquals(List.of("PlanExecute", "PlanExecute", "ReAct"), irModes);
        } finally {
            RequestContextUtils.remove();
        }
    }

    /**
     * 单智能体数量超过 controller.single-agent-limit 上限时阻断保存，
     * 报明确的数量超限错误（取代原"仅允许一个 Plan&Execute 子 Agent"限制）。
     */
    @Test
    void testDslToIr_SingleAgentCountExceedsLimit_Blocked() {
        List<String> modes = new ArrayList<>();
        for (int i = 0; i < 11; i++) {
            modes.add(i % 2 == 0 ? AgentMode.PLANEXECUTE.getMode() : AgentMode.REACT.getMode());
        }
        ControllerVO controllerVo = buildControllerVoWithSingleAgents(modes);
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId =
            controllerManagementService.groupDslNodes(controllerVo);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> controllerManagementService.dslToIr(controllerVo, nodesGroupByTypeId, true));
        assertEquals(StudioError.MULTI_AGENT_SINGLE_AGENT_NUMBER_EXCEED_LIMIT, exception.getErrorCode());
    }

    /**
     * 单智能体（含 ReAct 模式）仍不允许挂在子控制器下：
     * 放开顶层多单智能体后，嵌套层限制语义保持不变并覆盖全部单智能体模式。
     */
    @Test
    void testDslToIr_ReActAgentInSubController_Blocked() {
        // 子控制器节点自身 configs 挂载了 ReAct 模式单智能体
        ControllerNodeConfigVO subControllerConfig = new ControllerNodeConfigVO();
        ControllerNodeConfigVOAgents reactAgent = new ControllerNodeConfigVOAgents();
        reactAgent.setNodeId("agent-node-0");
        reactAgent.setId("single-agent-0");
        reactAgent.setMode(AgentMode.REACT.getMode());
        subControllerConfig.setAgents(List.of(reactAgent));

        ControllerNodeVO subControllerNode = new ControllerNodeVO();
        subControllerNode.setId("sub-controller-node-1");
        subControllerNode.setType(AgentNodeType.SUB_CONTROLLER.getType());
        subControllerNode.setConfigs(subControllerConfig);

        // 顶层 controller 引用该子控制器
        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOAgents subControllerRef = new ControllerNodeConfigVOAgents();
        subControllerRef.setNodeId("sub-controller-node-1");
        subControllerRef.setId("sub-controller-id-1");
        subControllerRef.setMode(AgentMode.CONTROLLER.getMode());
        configVo.setAgents(List.of(subControllerRef));
        configVo.setWorkflows(List.of());
        configVo.setModel(new ModelConfigVO().setModelDeploymentId("md-1"));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setId("controller-node-1");
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("controller-agent-id");
        controllerVo.setName("controller-agent");
        controllerVo.setProjectId("proj-1");
        controllerVo.setWorkspaceId("ws-1");
        controllerVo.setUpdateTime(String.valueOf(System.currentTimeMillis()));
        controllerVo.setInputs(List.of());
        controllerVo.setGlobalVariables(List.of());
        controllerVo.setNodes(List.of(controllerNode, subControllerNode));
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId =
            controllerManagementService.groupDslNodes(controllerVo);

        AgentStudioException exception = assertThrows(AgentStudioException.class,
            () -> controllerManagementService.dslToIr(controllerVo, nodesGroupByTypeId, true));
        assertEquals(StudioError.MULTI_AGENT_PLAN_EXECUTE_ONLY_IN_TOP_CONTROLLER, exception.getErrorCode());
    }

    /**
     * recordRefAgent 记录所有单智能体模式成员（含 ReAct），
     * 与放开后的保存链路一致（此前仅记录 PlanExecute 模式）。
     */
    @Test
    void testRecordRefAgent_RecordsReactModeAgent() {
        ControllerVO controllerVo = new ControllerVO();
        controllerVo.setId("test-id");
        controllerVo.setName("test-name");

        ControllerNodeConfigVO configVo = new ControllerNodeConfigVO();
        ControllerNodeConfigVOAgents agentConfig = new ControllerNodeConfigVOAgents();
        agentConfig.setNodeId("agent-node-1");
        agentConfig.setId("agent-id-1");
        agentConfig.setMode(AgentMode.REACT.getMode());
        configVo.setAgents(List.of(agentConfig));

        ControllerNodeVO controllerNode = new ControllerNodeVO();
        controllerNode.setType(AgentNodeType.CONTROLLER.getType());
        controllerNode.setConfigs(configVo);

        WorkflowNodeConfigVO agentNodeConfig = new WorkflowNodeConfigVO();
        agentNodeConfig.setId("agent-resource-id-1");
        agentNodeConfig.setVersionId("v1");
        agentNodeConfig.setName("react-agent");
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
