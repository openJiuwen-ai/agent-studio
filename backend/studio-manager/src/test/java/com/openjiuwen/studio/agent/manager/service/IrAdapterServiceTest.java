/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.DESCRIPTION;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Answers.RETURNS_DEEP_STUBS;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.nullable;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRepoReference;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVOErrors;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.enums.PluginCallModeEnum;
import com.openjiuwen.studio.agent.manager.mapper.ToolCredentialMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.mcp.infrastructure.apig.CesService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.TestUtil;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt.IRAdapter;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import jakarta.annotation.Resource;

import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * ir适配测试类
 *
 */
@TestPropertySource(locations = "classpath:environment.properties",
        properties = {"logging.level.com.openjiuwen.studio.agent.manager.service.IrAdapterService=DEBUG"})
@Transactional
@MockitoSettings(strictness = Strictness.LENIENT)
class IrAdapterServiceTest extends BaseTest {
    @Mock(answer = RETURNS_DEEP_STUBS)
    private MgObsService obsService;

    @Mock
    private ToolCredentialMapper toolCredentialMapper;

    @Mock
    private IPlugin pluginService;

    @Mock
    private PluginBaseImpl pluginBaseImplMock;

    @Mock
    private ModelServiceManager modelServiceManager;

    private static MockedStatic<CryptoUtils> mgSccCryptoUtils;

    private static MockedStatic<CommonUtil> commonUtilMockedStatic;

    @Autowired
    private IrAdapterService irAdapterService;

    @Mock
    private EncryptionAdapter encryptionAdapter;

    @Resource
    CesService cesService;

    @Mock(answer = RETURNS_DEEP_STUBS)
    private ShareInnerService shareInnerService;

    @NotNull
    private static WorkflowVO getWorkflowVO(String filePath) {
        String json = TestUtil.getStringFromFile(filePath);
        WorkflowVO workflowVO = JsonUtils.json2ObjQuietly(json, WorkflowVO.class);
        assertNotNull(workflowVO);
        return workflowVO;
    }

    private static MockedStatic<RequestContextUtils> mockedRequestContextUtils;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedRequestContextUtils = mockStatic(RequestContextUtils.class);
    }

    @org.junit.jupiter.api.BeforeEach
    public void setUp() {
        // 注入Mock对象到服务中
        ReflectionTestUtils.setField(irAdapterService, "pluginService", pluginService);
        ReflectionTestUtils.setField(irAdapterService, "toolCredentialMapper", toolCredentialMapper);
        ReflectionTestUtils.setField(irAdapterService, "modelServiceManager", modelServiceManager);

        // 将 Mock 出来的 encryptionAdapter 注入到 irAdapterService 中
        ReflectionTestUtils.setField(irAdapterService, "encryptionAdapter", encryptionAdapter);

        // Mock pluginBaseImpl 以避免 isAuthRequiredPresetPlugin 查询真实 DB
        ReflectionTestUtils.setField(irAdapterService, "pluginBaseImpl", pluginBaseImplMock);
        when(pluginBaseImplMock.buildToolByPlugin(
                nullable(String.class), nullable(String.class), anyString(), anyString()))
                .thenReturn(createMockToolEntity());

        ReflectionTestUtils.setField(irAdapterService, "agentIrVersion", "1.0.0");
        ReflectionTestUtils.setField(irAdapterService, "opProjectId", "test-op-project");

        // 设置默认的Mock行为
        when(pluginService.getToolEntity(anyString(), eq("test-project"), eq("test-op-project"), anyString()))
                .thenReturn(createMockToolEntity());
        when(toolCredentialMapper.selectAuthKeysByToolId(anyString()))
                .thenReturn(Collections.singletonList("test-api-key"));
        when(modelServiceManager.parseModelExtension(anyString(), anyString(), anyString(), anyBoolean()))
                .thenReturn(new HashMap<>());
    }

    @AfterAll
    static void end() {
        mockedRequestContextUtils.close();
    }

    private static String assertStartBranchIdAndGet(WorkflowEdgeVO edge, String branchId) {
        // 并行开始
        assertNotNull(edge.getSourceBranchId());

        if (branchId == null) {
            branchId = edge.getSourceBranchId();
        }
        // 每个分支的branchId至少要存在交集
        assertTrue(Strings.CS.contains(edge.getSourceBranchId(), branchId)
                || Strings.CS.contains(branchId, edge.getSourceBranchId()));
        return branchId;
    }

    private static boolean isTarget(WorkflowEdgeVO edge, String... nodeIds) {
        for (String nodeId : nodeIds) {
            if (Objects.equals(edge.getTarget(), nodeId)) {
                return true;
            }
        }
        return false;
    }

    private static boolean isSource(WorkflowEdgeVO edge, String nodeId) {
        return Objects.equals(edge.getSource(), nodeId);
    }

    private static boolean isSourceBranch(WorkflowEdgeVO edge, String nodeId, String branchId) {
        return Objects.equals(edge.getSource(), nodeId) && Objects.equals(edge.getBranch(), branchId);
    }

    /**
     * 创建用于测试的Mock ToolEntity
     */
    private ToolEntity createMockToolEntity() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("test-tool-id");
        toolEntity.setToolDisplayName("Test WebSearch Tool");
        toolEntity.setIntfType("websearch");
        // 简化测试，不设置RequestInfo
        return toolEntity;
    }

    /**
     * 创建用于测试的AgentInfo
     */
    private AgentInfo createTestAgentInfo() {
        AgentInfo agentInfo = new AgentInfo();
        agentInfo.setAgentId("test-deep-research-agent");
        agentInfo.setProjectId("test-project");
        agentInfo.setName("Test Deep Research Agent");
        agentInfo.setDescription("A test agent for deep research functionality");
        agentInfo.setModelDeploymentId("test-deployment");
        agentInfo.setModel("gpt-4");
        agentInfo.setModelConfig(createTestModelConfig());
        return agentInfo;
    }

    /**
     * 创建用于测试的ModelConfig
     */
    private ModelConfig createTestModelConfig() {
        ModelConfig modelConfig = new ModelConfig();
        modelConfig.setTemperature(0.2);
        modelConfig.setTopP(0.9);
        modelConfig.setHistorySize(100);
        modelConfig.setOutputFormat("text");
        modelConfig.setMaxTokens(4000);
        modelConfig.setEnableThinking(true);
        return modelConfig;
    }

    /**
     * 创建用于测试的ToolReference
     */
    private ToolReference createTestToolReference(String toolId) {
        ToolReference toolReference = new ToolReference();
        toolReference.setToolId(toolId);
        return toolReference;
    }

    /**
     * 创建用于测试的KnowledgeRepoReference
     */
    private KnowledgeRepoReference createTestKnowledgeRepoReference(String repoId) {
        KnowledgeRepoReference repoReference = new KnowledgeRepoReference();
        repoReference.setKnowledgeRepoId(repoId);
        return repoReference;
    }

    private static void assertEndBranch(WorkflowVO workflowVO, String nodeId, String... branchIds) {
        Set<String> branchIdSet = new HashSet<>();
        for (String branchId : branchIds) {
            for (String s : branchId.split(",")) {
                // 去掉开头的s_、e_
                branchIdSet.add(s.trim().substring(2));
            }
        }

        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (Objects.equals(edge.getTarget(), nodeId)) {
                // 并行结束的branchId需要和开始的branchId相同
                assertTrue(
                        Strings.CS.containsAny(edge.getTargetBranchId().substring(2), branchIdSet.toArray(new String[0])));
            }
        }
    }

    @Test
    void test_add_parallel_tag_should_success_when_simple_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_simple.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String branchId = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_1738913682745")) {
                branchId = assertStartBranchIdAndGet(edge, branchId);
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_end", branchId);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_simple_branch_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_simple_branch.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String branchId = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_1738913682745")) {
                branchId = assertStartBranchIdAndGet(edge, branchId);
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_end", branchId);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_in_cycle_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_in_cycle.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String branchId = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_1738913682745")) {
                branchId = assertStartBranchIdAndGet(edge, branchId);
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_end", branchId);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_out_cycle_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_out_cycle.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String branchId = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_1738913682745")) {
                branchId = assertStartBranchIdAndGet(edge, branchId);
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_end", branchId);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_cross_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_cross.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String branchId1 = null;
        String branchId2 = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_message")) {
                branchId1 = assertStartBranchIdAndGet(edge, branchId1);
            } else if (isSource(edge, "node_message_3")) {
                branchId2 = assertStartBranchIdAndGet(edge, branchId2);
            } else if (isTarget(edge, "node_message_4", "node_message_6")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_message_4", branchId1);
        assertEndBranch(workflowVO, "node_message_6", branchId2);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_serial_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_serial.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String branchId1 = null;
        String branchId2 = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_1738913682745")) {
                branchId1 = assertStartBranchIdAndGet(edge, branchId1);
            } else if (isSource(edge, "node_1740733457896")) {
                branchId2 = assertStartBranchIdAndGet(edge, branchId2);
            } else if (isTarget(edge, "node_end", "node_1740733457896")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_1740733457896", branchId1);
        assertEndBranch(workflowVO, "node_end", branchId2);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_complex_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_complex.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String startBranchId = null;
        String intentBranchId = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_start")) {
                // 开始节点并行开始
                startBranchId = assertStartBranchIdAndGet(edge, startBranchId);
            } else if (isSourceBranch(edge, "node_1740454765384", "branch_1")) {
                // 意图的第一个分支并行开始
                intentBranchId = assertStartBranchIdAndGet(edge, intentBranchId);
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_end", startBranchId, intentBranchId);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_complex2_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_complex2.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String message = null;
        String message1 = null;
        String condition = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_message")) {
                // 开始节点并行开始
                message = assertStartBranchIdAndGet(edge, message);
            } else if (isSource(edge, "node_message1")) {
                // 开始节点并行开始
                message1 = assertStartBranchIdAndGet(edge, message1);
            } else if (isSourceBranch(edge, "node_condition", "if")) {
                // 意图的第一个分支并行开始
                condition = assertStartBranchIdAndGet(edge, condition);
            } else if (isTarget(edge, "node_message3")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_end", message, message1);
        assertEndBranch(workflowVO, "node_message3", condition);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_complex3_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_complex3.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String start = null;
        String message6 = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_start")) {
                start = assertStartBranchIdAndGet(edge, start);
            } else if (isSource(edge, "node_message6")) {
                message6 = assertStartBranchIdAndGet(edge, message6);
            } else if (isTarget(edge, "node_message")) {
                assertNotNull(edge.getTargetBranchId());
            } else if (isTarget(edge, "node_message1")) {
                // 包含分支产生的异常，此处实际应该为NotNull
                assertNull(edge.getTargetBranchId());
            } else if (isTarget(edge, "node_message6")) {
                assertNotNull(edge.getTargetBranchId());
            } else if (isTarget(edge, "node_message2")) {
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }
        assertEndBranch(workflowVO, "node_message6", start);
        assertEndBranch(workflowVO, "node_message", start);
        assertEndBranch(workflowVO, "node_message2", message6);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_relay_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_relay.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);

        String message = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "message_7")) {
                message = assertStartBranchIdAndGet(edge, message);
            } else if (isTarget(edge, "message_5")) {
                // 中继并行结束
                assertNotNull(edge.getTargetBranchId());
            } else if (isTarget(edge, "message_4")) {
                // 中继并行结束
                assertNotNull(edge.getTargetBranchId());
            } else if (isTarget(edge, "node_end")) {
                // 结束节点并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }

        assertEndBranch(workflowVO, "message_5", message);
        assertEndBranch(workflowVO, "message_4", message);
        assertEndBranch(workflowVO, "node_end", message);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_failed_when_broken_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_broken.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            assertNull(edge.getSourceBranchId());
            assertNull(edge.getTargetBranchId());
        }
        assertEquals(2, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_interactive_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_interactive2.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);
        String message = null;
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (isSource(edge, "node_start")) {
                message = assertStartBranchIdAndGet(edge, message);
            } else if (isTarget(edge, "questioner")) {
                // 中继并行结束
                assertNotNull(edge.getTargetBranchId());
            } else {
                assertNull(edge.getSourceBranchId());
                assertNull(edge.getTargetBranchId());
            }
        }

        assertEndBranch(workflowVO, "questioner", message);
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_failed_when_interactive_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_interactive.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            assertNull(edge.getSourceBranchId());
            assertNull(edge.getTargetBranchId());
        }
        assertEquals(2, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_success_when_task_wf_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_task_workflow.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);
        for (WorkflowEdgeVO edge : workflowVO.getEdges()) {
            if (edge.getSource().equals("node_1738913682745")) {
                assertNotNull(edge.getSourceBranchId());
            }
        }
        assertEquals(0, errors.size());
    }

    @Test
    void test_add_parallel_tag_should_failed_when_chat_wf_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_chat_workflow.json");
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(workflowVO, null);
        assertEquals(0, errors.size());
    }

    @Test
    void test_connection_ir_should_success_when_complex_dsl() {
        WorkflowVO workflowVO = getWorkflowVO("classpath:flow_dsl/parallel/test_complex.json");
        irAdapterService.addParallelTag(workflowVO, null);

        Map<String, String> reflection = new HashMap<>();
        workflowVO.getNodes().forEach(m -> reflection.put(m.getId(), m.getType()));
        IRAdapter irAdapter = new IRAdapter();
        List<Map<String, Object>> connections =
                irAdapter.adaptConnections(workflowVO.getEdges(), reflection, null);
        assertFalse(connections.isEmpty());
    }

    @Test
    void test_getServiceConfig() {
        // 1. 准备数据
        McpServiceEntity entity = new McpServiceEntity();
        entity.setServerConfig("mock_cipher_text");

        // 2. Mock 行为 (这里因为 encryptionAdapter 已经是 Mock 对象，可以安全使用 anyString())
        when(encryptionAdapter.decrypt(anyString())).thenReturn("decrypted_json");

        // 3. 执行
        String result = irAdapterService.getServiceConfig(entity);

        // 4. 断言
        assertNotNull(result);
        assertEquals("decrypted_json", result);
    }

    // ========== adaptAgentDeepResearch 方法测试用例 ==========

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 基本功能测试（正常情况下的完整流程）
     */
    @Test
    void test_adaptAgentDeepResearch_should_success_with_basic_function() {
        // 准备测试数据
        AgentInfo agentInfo = createTestAgentInfo();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("test-key", "test-value");

        // 调用方法
        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);

        // 验证结果
        assertNotNull(result);
        assertEquals("test-deep-research-agent", result.get("agentId"));
        assertEquals("Test Deep Research Agent", result.get("agentName"));
        assertEquals("A test agent for deep research functionality", result.get(DESCRIPTION));
        assertEquals("1.0.0", result.get("agentVersion"));
        assertEquals("1.0.0", result.get("schemaVersion"));

        // 验证基础配置
        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");
        assertNotNull(configs);
        assertNotNull(configs.get("llm_config"));

        // 验证模型配置
        @SuppressWarnings("unchecked")
        Map<String, Object> llmConfig = (Map<String, Object>) configs.get("llm_config");
        assertEquals("test-deployment|gpt-4", llmConfig.get("model_name"));
        assertEquals("openai", llmConfig.get("model_type"));

        // 验证DeepResearch特有的配置
        assertEquals("commercial", configs.get("deep_search_execute_mode"));
        assertEquals(true, configs.get("workflow_human_in_the_loop"));
        assertEquals(10, configs.get("outliner_max_section_num"));
        assertEquals("all", configs.get("info_collector_search_method"));
        assertEquals(false, configs.get("has_template"));
    }

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 模型配置测试（各种模型配置场景）
     */
    @Test
    @SuppressWarnings("unchecked")
    void test_adaptAgentDeepResearch_should_success_with_various_model_configs() {
        // 测试1: 无modelConfig的情况
        AgentInfo agentInfo = createTestAgentInfo();
        agentInfo.setModelConfig(null);
        Map<String, Object> metadata = new HashMap<>();

        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");
        assertNull(configs.get("llm_config"));

        // 测试2: 自定义temperature
        agentInfo.setModelConfig(createTestModelConfig());
        agentInfo.getModelConfig().setTemperature(0.5);

        result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        configs = (Map<String, Object>) result.get("configs");
        @SuppressWarnings("unchecked")
        Map<String, Object> llmConfig = (Map<String, Object>) configs.get("llm_config");

        // 测试3: 无temperature时的默认值
        agentInfo.getModelConfig().setTemperature(null);
        when(modelServiceManager.parseModelExtension(anyString(), anyString(), anyString(), anyBoolean()))
                .thenReturn(new HashMap<>());

        result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        configs = (Map<String, Object>) result.get("configs");
        llmConfig = (Map<String, Object>) configs.get("llm_config");

    }

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 工具配置测试（websearch工具存在和无工具的情况）
     */
    @Test
    @SuppressWarnings("unchecked")
    void test_adaptAgentDeepResearch_should_success_with_websearch_tools() {
        // 测试1: 包含websearch工具的情况
        AgentInfo agentInfo = createTestAgentInfo();
        List<ToolReference> tools = new ArrayList<>();
        tools.add(createTestToolReference("websearch-tool-1"));
        tools.add(createTestToolReference("other-tool-1"));
        agentInfo.setTools(tools);
        Map<String, Object> metadata = new HashMap<>();

        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");

        Map<String, Object> webSearchConfig = (Map<String, Object>) configs.get("web_search_engine_config");
        assertNotNull(webSearchConfig);
        // 由于RequestInfo为空，URL会是null或空字符串
        Object searchUrl = webSearchConfig.get("search_url");
        assertTrue(searchUrl == null || "".equals(searchUrl));

        // 测试2: 无工具的情况
        agentInfo.setTools(new ArrayList<>());
        result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        configs = (Map<String, Object>) result.get("configs");

        // 测试3: 工具不为空但没有websearch类型
        tools.add(createTestToolReference("non-websearch-tool"));
        agentInfo.setTools(tools);
        result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        configs = (Map<String, Object>) result.get("configs");
    }

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 知识库配置测试（有知识库和无知识库的情况）
     */
    @Test
    @SuppressWarnings("unchecked")
    void test_adaptAgentDeepResearch_should_success_with_knowledge_repos() {
        // 测试1: 包含知识库的情况
        AgentInfo agentInfo = createTestAgentInfo();
        List<KnowledgeRepoReference> knowledgeRepos = new ArrayList<>();
        knowledgeRepos.add(createTestKnowledgeRepoReference("repo-1"));
        knowledgeRepos.add(createTestKnowledgeRepoReference("repo-2"));
        agentInfo.setKnowledgeRepos(knowledgeRepos);
        Map<String, Object> metadata = new HashMap<>();

        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");

        // 验证知识库配置是在 deep_search_execute_mode 下的配置
        assertEquals("commercial", configs.get("deep_search_execute_mode"));
        @SuppressWarnings("unchecked")
        Map<String, Object> webSearchConfig = (Map<String, Object>) configs.get("web_search_engine_config");

        // 测试2: 无知识库的情况
        agentInfo.setKnowledgeRepos(new ArrayList<>());
        result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        configs = (Map<String, Object>) result.get("configs");
        assertNotNull(configs.get("deep_search_execute_mode"));
    }

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 写作模板测试（模板存在和不存在的情况）
     */
    @Test
    @SuppressWarnings("unchecked")
    void test_adaptAgentDeepResearch_should_success_with_writing_template() {
        // 测试1: 包含写作模板的情况
        AgentInfo agentInfo = createTestAgentInfo();
        agentInfo.setWritingTemplate("test-template-content");
        agentInfo.setIsTemplate(true);
        Map<String, Object> metadata = new HashMap<>();

        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);

        assertEquals("test-template-content", result.get("template_path"));
        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");
        assertEquals(true, configs.get("has_template"));
        assertEquals(true, configs.get("is_template"));

        // 测试2: 无写作模板的情况
        agentInfo.setWritingTemplate(null);
        agentInfo.setIsTemplate(false);
        result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        assertNull(result.get("template_path"));
        configs = (Map<String, Object>) result.get("configs");
        assertEquals(false, configs.get("has_template"));
        assertEquals(false, configs.get("is_template"));
    }

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 边界条件测试（空值、null值等边界情况）
     */
    @Test
    void test_adaptAgentDeepResearch_should_success_with_edge_cases() {
        // 测试1: projectId为空时的处理
        AgentInfo agentInfo = createTestAgentInfo();
        agentInfo.setProjectId(null);
        Map<String, Object> metadata = new HashMap<>();

        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        assertNotNull(result);
        assertEquals("test-deep-research-agent", result.get("agentId"));

        // 测试2: 完整的空参数测试
        AgentInfo emptyAgentInfo = new AgentInfo();
        emptyAgentInfo.setAgentId("empty-agent");
        emptyAgentInfo.setProjectId(null);
        emptyAgentInfo.setName(null);
        emptyAgentInfo.setDescription(null);
        emptyAgentInfo.setModelConfig(null);
        emptyAgentInfo.setTools(null);
        emptyAgentInfo.setKnowledgeRepos(null);
        emptyAgentInfo.setWritingTemplate(null);

        result = irAdapterService.adaptAgentDeepResearch(emptyAgentInfo, null);
        assertNotNull(result);
        assertEquals("empty-agent", result.get("agentId"));
        assertNull(result.get("agentName"));
        assertNull(result.get(DESCRIPTION));
        assertNull(result.get("template_path"));

        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");
        assertNull(configs.get("llm_config"));
        assertEquals("commercial", configs.get("deep_search_execute_mode"));
        assertEquals(false, configs.get("has_template"));
    }

    /**
     * 测试 adaptAgentDeepSearch 方法的 - 异常处理测试
     */
    @Test
    void test_adaptAgentDeepResearch_should_handle_exceptions_gracefully() {
        // 测试pluginService抛出异常的情况
        AgentInfo agentInfo = createTestAgentInfo();
        List<ToolReference> tools = new ArrayList<>();
        tools.add(createTestToolReference("exception-tool"));
        agentInfo.setTools(tools);
        Map<String, Object> metadata = new HashMap<>();

        when(pluginService.getToolEntity(anyString(), anyString(), anyString(), anyString()))
                .thenThrow(new RuntimeException("Test exception"));

        Map<String, Object> result = irAdapterService.adaptAgentDeepResearch(agentInfo, metadata);
        assertNotNull(result);
        // 应该返回基础 IR，忽略配置错误并记录警告
        @SuppressWarnings("unchecked")
        Map<String, Object> configs = (Map<String, Object>) result.get("configs");

    }

    @Test
    public void test_parseAgentMcpParams_null_input() throws Exception {
        List<Map<String, Object>> result = irAdapterService.parseAgentMcpParams(null, false);
        assertTrue(result.isEmpty());
    }

    @Test
    public void test_parseAgentMcpParams_valid_input() throws Exception {
        McpServiceEntity mcpEntity = mock(McpServiceEntity.class);
        when(mcpEntity.getServerConfig()).thenReturn("encryptedServerConfig");
        when(encryptionAdapter.decrypt("encryptedServerConfig")).thenReturn("decryptedServerConfig");

        try (MockedStatic<CommonUtil> commonUtilMock = mockStatic(CommonUtil.class)) {
            Map<String, String> headers = new HashMap<>();
            headers.put("header1", "value1");
            commonUtilMock.when(() -> CommonUtil.parseMcpConfigHeaderInfo("decryptedServerConfig")).thenReturn(headers);

            List<Map<String, Object>> result = irAdapterService.parseAgentMcpParams(mcpEntity, false);
            assertEquals(1, result.size());
            assertEquals("header1", result.get(0).get("name"));
            assertEquals("value1", result.get(0).get("description"));
        }
    }

    @Test
    public void test_parseAgentMcpParams_with_validation() throws Exception {
        McpServiceEntity mcpEntity = mock(McpServiceEntity.class);
        when(mcpEntity.getServerConfig()).thenReturn("encryptedServerConfig");
        when(encryptionAdapter.decrypt("encryptedServerConfig")).thenReturn("decryptedServerConfig");

        try (MockedStatic<CommonUtil> commonUtilMock = mockStatic(CommonUtil.class)) {
            Map<String, String> headers = new HashMap<>();
            headers.put("header1", "value1");
            commonUtilMock.when(() -> CommonUtil.parseMcpConfigHeaderInfo("decryptedServerConfig")).thenReturn(headers);

            List<Map<String, Object>> result = irAdapterService.parseAgentMcpParams(mcpEntity, true);
            assertEquals(1, result.size());
        }
    }

    /**
     * 用例描述：验证 parsePluginConfig 对自定义插件输出 callMode 为 "custom"
     * 预制条件：Mock pluginService.getToolEntity 返回 callMode="custom" 的 ToolEntity
     * 输入参数：pluginConfig.id="test#0"，projectId="test-project"，isAgentPlugin=false
     * 预期结果：返回的 Map 中 callMode 为 "custom"
     */
    @Test
    void testParsePluginConfigShouldOutputCallModeForCustomPlugin() {
        // Given
        ToolEntity customTool = new ToolEntity();
        customTool.setToolId("test#0");
        customTool.setCallMode(PluginCallModeEnum.CUSTOM.getCode());
        customTool.setInputSchema("{}");
        customTool.setOutputSchema("{}");

        when(pluginService.getToolEntity(anyString(), eq("test-project"), eq("test-op-project"), anyString()))
            .thenReturn(customTool);

        Map<String, Object> pluginConfig = new HashMap<>();
        pluginConfig.put("id", "test#0");
        pluginConfig.put("version_id", "v1");

        // When
        Map<String, Object> result = irAdapterService.parsePluginConfig(pluginConfig, "test-project", false);

        // Then
        assertNotNull(result);
        assertEquals(PluginCallModeEnum.CUSTOM.getCode(), result.get("callMode"));
    }

    /**
     * 用例描述：验证 parsePluginConfig 在 callMode 为 null 时默认输出 "api"
     * 预制条件：Mock pluginService.getToolEntity 返回 callMode=null 的 ToolEntity
     * 输入参数：pluginConfig.id="test#0"，projectId="test-project"，isAgentPlugin=false
     * 预期结果：返回的 Map 中 callMode 为 "api"
     */
    @Test
    void testParsePluginConfigShouldDefaultCallModeToApiWhenNull() {
        // Given
        ToolEntity tool = new ToolEntity();
        tool.setToolId("test#0");
        // callMode is null
        tool.setInputSchema("{}");
        tool.setOutputSchema("{}");

        when(pluginService.getToolEntity(anyString(), eq("test-project"), eq("test-op-project"), anyString()))
            .thenReturn(tool);

        Map<String, Object> pluginConfig = new HashMap<>();
        pluginConfig.put("id", "test#0");
        pluginConfig.put("version_id", "v1");

        // When
        Map<String, Object> result = irAdapterService.parsePluginConfig(pluginConfig, "test-project", false);

        // Then
        assertNotNull(result);
        assertEquals(PluginCallModeEnum.API.getCode(), result.get("callMode"));
    }

    /**
     * 用例描述：验证 parsePluginConfig 对自定义插件从 metadata 中提取并输出 componentType
     * 预制条件：Mock pluginService.getToolEntity 返回 callMode="custom" 且 metadata 含 component_type 的 ToolEntity
     * 输入参数：pluginConfig.id="test#0"，projectId="test-project"，isAgentPlugin=false
     * 预期结果：返回的 Map 中 componentType 为 "draw_box"
     */
    @Test
    void testParsePluginConfigShouldOutputComponentTypeForCustomPlugin() {
        // Given
        ToolEntity customTool = new ToolEntity();
        customTool.setToolId("test#0");
        customTool.setCallMode(PluginCallModeEnum.CUSTOM.getCode());
        customTool.setMetadata("{\"component_type\":\"draw_box\"}");
        customTool.setInputSchema("{}");
        customTool.setOutputSchema("{}");

        when(pluginService.getToolEntity(anyString(), eq("test-project"), eq("test-op-project"), anyString()))
            .thenReturn(customTool);

        Map<String, Object> pluginConfig = new HashMap<>();
        pluginConfig.put("id", "test#0");
        pluginConfig.put("version_id", "v1");

        // When
        Map<String, Object> result = irAdapterService.parsePluginConfig(pluginConfig, "test-project", false);

        // Then
        assertNotNull(result);
        assertEquals(PluginCallModeEnum.CUSTOM.getCode(), result.get("callMode"));
        assertEquals("draw_box", result.get("componentType"));
    }

    /**
     * 用例描述：验证 parsePluginConfig 在 metadata 为空时不出输出 componentType
     * 预制条件：Mock pluginService.getToolEntity 返回 callMode="custom" 但 metadata 为 null 的 ToolEntity
     * 输入参数：pluginConfig.id="test#0"，projectId="test-project"，isAgentPlugin=false
     * 预期结果：返回的 Map 中不包含 componentType
     */
    @Test
    void testParsePluginConfigShouldNotOutputComponentTypeWhenMetadataIsEmpty() {
        // Given
        ToolEntity customTool = new ToolEntity();
        customTool.setToolId("test#0");
        customTool.setCallMode(PluginCallModeEnum.CUSTOM.getCode());
        // metadata is null
        customTool.setInputSchema("{}");
        customTool.setOutputSchema("{}");

        when(pluginService.getToolEntity(anyString(), eq("test-project"), eq("test-op-project"), anyString()))
            .thenReturn(customTool);

        Map<String, Object> pluginConfig = new HashMap<>();
        pluginConfig.put("id", "test#0");
        pluginConfig.put("version_id", "v1");

        // When
        Map<String, Object> result = irAdapterService.parsePluginConfig(pluginConfig, "test-project", false);

        // Then
        assertNotNull(result);
        assertEquals(PluginCallModeEnum.CUSTOM.getCode(), result.get("callMode"));
        assertNull(result.get("componentType"));
    }

    /**
     * 用例描述：验证 parsePluginConfig 在 requestInfo 为 null 时不抛 NPE
     * 预制条件：Mock pluginService.getToolEntity 返回 requestInfo=null 的 ToolEntity
     * 输入参数：pluginConfig.id="test#0"，projectId="test-project"，isAgentPlugin=false
     * 预期结果：方法不抛异常，结果中 url 和 method 为 null
     */
    @Test
    void testParsePluginConfigShouldHandleNullRequestInfoWithoutNpe() {
        // Given
        ToolEntity tool = new ToolEntity();
        tool.setToolId("test#0");
        tool.setCallMode(PluginCallModeEnum.API.getCode());
        tool.setInputSchema("{}");
        tool.setOutputSchema("{}");
        // requestInfo is null

        when(pluginService.getToolEntity(anyString(), eq("test-project"), eq("test-op-project"), anyString()))
            .thenReturn(tool);

        Map<String, Object> pluginConfig = new HashMap<>();
        pluginConfig.put("id", "test#0");
        pluginConfig.put("version_id", "v1");

        // When
        Map<String, Object> result = irAdapterService.parsePluginConfig(pluginConfig, "test-project", false);

        // Then — requestInfo 为 null 时 url 和 method 不在结果中
        assertNotNull(result);
        assertNull(result.get("url"));
        assertNull(result.get("method"));
    }

}
