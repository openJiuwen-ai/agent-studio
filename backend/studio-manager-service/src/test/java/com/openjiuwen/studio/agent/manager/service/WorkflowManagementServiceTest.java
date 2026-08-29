/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.*;
import com.openjiuwen.studio.agent.manager.entity.*;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.enums.VisibilityEnum;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.TagMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.client.JiuWenClient;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.service.serializer.YamlSerializer;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMemberService;
import com.openjiuwen.studio.agent.manager.workflow.convert.adapt.ThirdpartyWorkflowAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.quartz.Scheduler;
import org.quartz.SchedulerException;
import org.quartz.Trigger;
import org.quartz.TriggerKey;
import org.springframework.context.MessageSource;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class WorkflowManagementServiceTest {

    @Mock private WorkflowMapper workflowMapper;
    @Mock private MgObsService obsService;
    @Mock private Scheduler scheduler;
    @Mock private AppMapper appMapper;
    @Mock private MappingMapper mappingMapper;
    @Mock private TagMapper tagMapper;
    @Mock private ReleaseVersionMapper releaseVersionMapper;
    @Mock private ReleaseChannelMapper releaseChannelMapper;
    @Mock private JiuWenClient jiuWenClient;
    @Mock private PublishUtils publishUtils;
    @Mock private AgentCommonService agentCommonService;
    @Mock private IrAdapterService irAdapterService;
    @Mock private WorkflowValidationService workflowValidationService;
    @Mock private MessageSource messageSource;
    @Mock private SkuManageService skuManageService;
    @Mock private ModelServiceManager modelServiceManager;
    @Mock private MemoryRepoMapper memoryRepoMapper;
    @Mock private AssetFreeTrialMgmtService assetFreeTrialMgmtService;
    @Mock private AgentMemoryConfigService agentMemoryConfigService;
    @Mock private WorkspaceMemberService workspaceMemberService;
    @Mock private PluginBaseImpl pluginBase;
    @Mock private EnvironmentServiceManagerService environmentServiceManagerService;
    @Mock private ShareResourceManagerService shareResourceManagerService;
    @Mock private WorkflowCommonService workflowCommonService;
    @Mock private AgentSpaceService agentSpaceService;
    @Mock private AgentRuntimeClient agentRuntimeClient;
    @Mock private ObjectMapper mapper;
    @Mock private RouterStrategyMapper routerStrategyMapper;
    @Mock private ThirdpartyWorkflowAdapter thirdpartyWorkflowAdapter;
    @Mock private AgentImportExportService agentImportExportService;
    @Mock private AgentImportService agentImportService;
    @Mock private AgentManagementService agentManagementService;
    @Mock private AiGenService aiGenerateService;
    @Mock private YamlSerializer yamlSerializer;
    @Mock private KnowledgeBaseServiceImpl knowledgeBaseService;

    @InjectMocks private WorkflowManagementService workflowManagementService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(workflowManagementService, "opSvcProjectId", "op-project-id");
        ReflectionTestUtils.setField(workflowManagementService, "defaultIcon", "default-icon");
        ReflectionTestUtils.setField(workflowManagementService, "releaseMaxSize", 10);
        ReflectionTestUtils.setField(workflowManagementService, "nestedLevel", 10);
        ReflectionTestUtils.setField(workflowManagementService, "knowledgeRepoLimit", 3);
        ReflectionTestUtils.setField(workflowManagementService, "isSoftDelete", true);
        ReflectionTestUtils.setField(workflowManagementService, "publishAgentBuilderEnable", false);
        ReflectionTestUtils.setField(workflowManagementService, "publishCrossWorkspace", false);
        ReflectionTestUtils.setField(workflowManagementService, "publishAppEnable", false);
        ReflectionTestUtils.setField(workflowManagementService, "envType", "poc");
        ReflectionTestUtils.setField(workflowManagementService, "endpointTemplate", "http://endpoint/%s/%s");
        ReflectionTestUtils.setField(workflowManagementService, "webpageEndpoint", "http://webpage/");
        ReflectionTestUtils.setField(workflowManagementService, "agentRuntimeEndpoint", "http://runtime");
        ReflectionTestUtils.setField(workflowManagementService, "runWorkflowStreamUrl", "/stream");
        ReflectionTestUtils.setField(workflowManagementService, "knowledgeSource", "custom");
        ReflectionTestUtils.setField(workflowManagementService, "contentReviewConfigs", "{}");
        ReflectionTestUtils.setField(workflowManagementService, "fileMaxSize", 10240L);
        ReflectionTestUtils.setField(workflowManagementService, "assetAppFreeTrialQuotaLimit", 10);
    }

    // ==================== getWorkflow ====================

    @Test
    void testGetWorkflow_Success() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        entity.setName("Test Workflow");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
        when(obsService.downloadObsFile(any())).thenReturn("{\"nodes\":[]}");

        var result = workflowManagementService.getWorkflow("p1", "wf-1", "w1");

        assertNotNull(result);
    }

    @Test
    void testGetWorkflow_NotFound() {
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.getWorkflow("p1", "wf-1", "w1"));
    }

    // ==================== getWorkflowInfo ====================

    @Test
    void testGetWorkflowInfo_UserVisibilityPrivilegeError() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("other-user");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setName("Test Workflow");
            entity.setVisibility(VisibilityEnum.USER.getValue());
            entity.setCreatorId("creator-user");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.getWorkflowInfo("p1", "wf-1", "w1"));
        }
    }

    @Test
    void testGetWorkflowInfo_UserVisibilitySameCreator() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("creator-user");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setName("Test Workflow");
            entity.setVisibility(VisibilityEnum.USER.getValue());
            entity.setCreatorId("creator-user");
            entity.setDslPath("workflow/flow/wf-1.json");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
            when(obsService.downloadObsFile(anyString())).thenReturn("{\"nodes\":[],\"configs\":{}}");
            when(obsService.getAbsolutePath(anyString())).thenReturn("/abs/path");

            var result = workflowManagementService.getWorkflowInfo("p1", "wf-1", "w1");

            assertNotNull(result);
            assertEquals("wf-1", result.getWorkflowId());
        }
    }

    @Test
    void testGetWorkflowInfo_ProjectVisibility() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        entity.setName("Test Workflow");
        entity.setVisibility(VisibilityEnum.PROJECT.getValue());
        entity.setDslPath("workflow/flow/wf-1.json");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
        when(obsService.downloadObsFile(anyString())).thenReturn("{\"nodes\":[],\"configs\":{}}");
        when(obsService.getAbsolutePath(anyString())).thenReturn("/abs/path");

        var result = workflowManagementService.getWorkflowInfo("p1", "wf-1", "w1");

        assertNotNull(result);
        assertEquals("wf-1", result.getWorkflowId());
    }

    // ==================== deleteWorkflow ====================

    @Test
    void testDeleteWorkflow_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("test-token");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setProjectId("p1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            var result = workflowManagementService.deleteWorkflow("p1", "wf-1", "w1");

            assertNotNull(result);
        }
    }

    @Test
    void testDeleteWorkflow_NotFound() {
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.deleteWorkflow("p1", "wf-1", "w1"));
    }

    @Test
    void testDeleteWorkflow_WrongProject() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        entity.setProjectId("other-project");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
        doThrow(new AgentStudioException(StudioError.PRIVILEGE_ERROR))
            .when(workflowValidationService).validateModifyPrivilege(any(), anyString(), anyString());

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.deleteWorkflow("p1", "wf-1", "w1"));
    }

    @Test
    void testDeleteWorkflow_WithTimerTriggers() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("test-token");

            TriggerConfig timerTrigger = new TriggerConfig();
            timerTrigger.setTriggerId("trigger-1");
            timerTrigger.setName("timer-trigger");
            timerTrigger.setType("TIMER");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setProjectId("p1");
            entity.setWorkspaceId("w1");
            entity.setTriggerList(new ArrayList<>(List.of(timerTrigger)));
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            var result = workflowManagementService.deleteWorkflow("p1", "wf-1", "w1");

            assertNotNull(result);
        }
    }

    @Test
    void testDeleteWorkflow_SchedulerException() throws Exception {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("test-token");

            TriggerConfig timerTrigger = new TriggerConfig();
            timerTrigger.setTriggerId("trigger-1");
            timerTrigger.setName("timer-trigger");
            timerTrigger.setType("TIMER");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setProjectId("p1");
            entity.setWorkspaceId("w1");
            entity.setTriggerList(new ArrayList<>(List.of(timerTrigger)));
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
            doThrow(new SchedulerException("test")).when(scheduler).pauseTrigger(any(TriggerKey.class));

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.deleteWorkflow("p1", "wf-1", "w1"));
        }
    }

    @Test
    void testDeleteWorkflow_HardDelete() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("test-token");
            ReflectionTestUtils.setField(workflowManagementService, "isSoftDelete", false);

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setProjectId("p1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            var result = workflowManagementService.deleteWorkflow("p1", "wf-1", "w1");

            assertNotNull(result);
            verify(mappingMapper).deleteBatchByAppId(eq("wf-1"), isNull(), eq(true));
            verify(releaseVersionMapper).deleteByAppId(eq("wf-1"));
        }
    }

    @Test
    void testDeleteWorkflow_WithAgentBuilderEnabled() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("test-token");
            ReflectionTestUtils.setField(workflowManagementService, "publishAgentBuilderEnable", true);

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setProjectId("p1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            var result = workflowManagementService.deleteWorkflow("p1", "wf-1", "w1");

            assertNotNull(result);
            verify(agentSpaceService).delete(eq("w1"), eq("wf-1"));
        }
    }

    // ==================== getWorkflowScene ====================

    @Test
    void testGetWorkflowScene_NotPublished() {
        when(releaseChannelMapper.selectByAppIdAndChannel(anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.getWorkflowScene("p1", "wf-1", "w1"));
    }

    @Test
    void testGetWorkflowScene_VersionNotFound() {
        ReleaseChannel channel = new ReleaseChannel();
        channel.setVersionId("v1");
        when(releaseChannelMapper.selectByAppIdAndChannel(anyString(), anyString())).thenReturn(channel);
        when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.getWorkflowScene("p1", "wf-1", "w1"));
    }

    // ==================== setWorkflowTestStatus ====================

    @Test
    void testSetWorkflowTestStatus_Success_True() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(entity);

            var result = workflowManagementService.setWorkflowTestStatus("p1", "wf-1", "w1", true);

            assertNotNull(result);
            assertEquals("wf-1", result.getWorkflowId());
            assertEquals(1, result.getTestStatus());
            verify(workflowMapper).updateWorkflowEntity(eq("p1"), eq("wf-1"), any());
        }
    }

    @Test
    void testSetWorkflowTestStatus_Success_False() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(entity);

            var result = workflowManagementService.setWorkflowTestStatus("p1", "wf-1", "w1", false);

            assertNotNull(result);
            assertEquals(0, result.getTestStatus());
        }
    }

    @Test
    void testSetWorkflowTestStatus_NotFound() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(null);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.setWorkflowTestStatus("p1", "wf-1", "w1", true));
        }
    }

    // ==================== addTrigger ====================

    @Test
    void testAddTrigger_InvalidType() {
        TriggerConfig body = new TriggerConfig();
        body.setType("INVALID");

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.addTrigger("p1", "wf-1", "w1", body));
    }

    @Test
    void testAddTrigger_TimerSuccess() throws Exception {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(null);
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
            when(scheduler.getTrigger(any(TriggerKey.class))).thenReturn(null);
            when(scheduler.isShutdown()).thenReturn(false);

            TriggerConfig body = new TriggerConfig();
            body.setType("TIMER");
            body.setName("test-trigger");
            body.setCron("0 0 * * * ?");
            body.setPrompt("test prompt");

            var result = workflowManagementService.addTrigger("p1", "wf-1", "w1", body);

            assertNotNull(result);
            assertNotNull(result.getTriggerId());
            verify(scheduler).scheduleJob(any(), any());
            verify(scheduler).start();
            verify(workflowMapper).updateWorkflowEntity(eq("p1"), eq("wf-1"), any());
        }
    }

    @Test
    void testAddTrigger_TriggerLimitReached() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        List<TriggerConfig> triggers = new ArrayList<>();
        for (int i = 0; i < CommonConstant.MAX_TRIGGER_WORKFLOW_NUMS; i++) {
            TriggerConfig tc = new TriggerConfig();
            tc.setTriggerId("trigger-" + i);
            tc.setType("TIMER");
            triggers.add(tc);
        }
        entity.setTriggerList(triggers);
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

        TriggerConfig body = new TriggerConfig();
        body.setType("TIMER");
        body.setName("new-trigger");

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.addTrigger("p1", "wf-1", "w1", body));
    }

    @Test
    void testAddTrigger_EventType() throws Exception {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(new ArrayList<>());
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
            when(scheduler.getTrigger(any(TriggerKey.class))).thenReturn(null);
            when(scheduler.isShutdown()).thenReturn(false);

            TriggerConfig body = new TriggerConfig();
            body.setType("EVENT");
            body.setName("event-trigger");
            body.setTriggerId("evt-1");
            body.setCron("0 0 * * * ?");
            body.setPrompt("test prompt");

            var result = workflowManagementService.addTrigger("p1", "wf-1", "w1", body);

            assertNotNull(result);
            assertEquals("evt-1", result.getTriggerId());
        }
    }

    @Test
    void testAddTrigger_WithExistingTriggerId() throws Exception {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(new ArrayList<>());
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
            when(scheduler.getTrigger(any(TriggerKey.class))).thenReturn(null);
            when(scheduler.isShutdown()).thenReturn(true);

            TriggerConfig body = new TriggerConfig();
            body.setType("TIMER");
            body.setName("test-trigger");
            body.setCron("0 0 * * * ?");
            body.setTriggerId("existing-id");

            var result = workflowManagementService.addTrigger("p1", "wf-1", "w1", body);

            assertEquals("existing-id", result.getTriggerId());
            verify(scheduler, never()).start();
        }
    }

    // ==================== deleteTrigger ====================

    @Test
    void testDeleteTrigger_Success() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            TriggerConfig tc = new TriggerConfig();
            tc.setTriggerId("trigger-1");
            tc.setName("my-trigger");
            tc.setType("EVENT");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(new ArrayList<>(List.of(tc)));
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            var result = workflowManagementService.deleteTrigger("p1", "wf-1", "trigger-1", "w1");

            assertNull(result);
            verify(workflowMapper).updateWorkflowEntity(eq("p1"), eq("wf-1"), any());
        }
    }

    @Test
    void testDeleteTrigger_TimerType() throws Exception {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            TriggerConfig tc = new TriggerConfig();
            tc.setTriggerId("trigger-1");
            tc.setName("my-trigger");
            tc.setType("TIMER");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(new ArrayList<>(List.of(tc)));
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            workflowManagementService.deleteTrigger("p1", "wf-1", "trigger-1", "w1");

            verify(scheduler).pauseTrigger(any(TriggerKey.class));
            verify(scheduler).unscheduleJob(any(TriggerKey.class));
        }
    }

    @Test
    void testDeleteTrigger_EmptyTriggerList() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(null);
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.deleteTrigger("p1", "wf-1", "trigger-1", "w1"));
        }
    }

    @Test
    void testDeleteTrigger_TriggerNotFoundInList() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            TriggerConfig tc = new TriggerConfig();
            tc.setTriggerId("trigger-other");
            tc.setName("other-trigger");
            tc.setType("EVENT");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setTriggerList(new ArrayList<>(List.of(tc)));
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.deleteTrigger("p1", "wf-1", "trigger-1", "w1"));
        }
    }

    // ==================== getTriggerConfigList ====================

    @Test
    void testGetTriggerConfigList_NullWorkflow() {
        var result = workflowManagementService.getTriggerConfigList(null);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetTriggerConfigList_NullConfigs() {
        WorkflowVO workflow = new WorkflowVO();
        workflow.setConfigs(null);

        var result = workflowManagementService.getTriggerConfigList(workflow);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetTriggerConfigList_NoTriggerList() {
        WorkflowVO workflow = new WorkflowVO();
        workflow.setConfigs(new HashMap<>());

        var result = workflowManagementService.getTriggerConfigList(workflow);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetTriggerConfigList_TriggerListNotListType() {
        WorkflowVO workflow = new WorkflowVO();
        Map<String, Object> configs = new HashMap<>();
        configs.put("trigger_list", "not-a-list");
        workflow.setConfigs(configs);

        var result = workflowManagementService.getTriggerConfigList(workflow);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetTriggerConfigList_ValidTriggerList() {
        Map<String, Object> triggerMap = new HashMap<>();
        triggerMap.put("triggerId", "t-1");
        triggerMap.put("name", "trigger-1");
        triggerMap.put("type", "TIMER");

        WorkflowVO workflow = new WorkflowVO();
        Map<String, Object> configs = new HashMap<>();
        configs.put("trigger_list", List.of(triggerMap));
        workflow.setConfigs(configs);

        TriggerConfig convertedTrigger = new TriggerConfig();
        convertedTrigger.setTriggerId("t-1");
        convertedTrigger.setName("trigger-1");
        convertedTrigger.setType("TIMER");
        when(mapper.convertValue(any(), eq(TriggerConfig.class))).thenReturn(convertedTrigger);

        var result = workflowManagementService.getTriggerConfigList(workflow);

        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("t-1", result.get(0).getTriggerId());
    }

    @Test
    void testGetTriggerConfigList_TriggerWithEmptyId() {
        Map<String, Object> triggerMap = new HashMap<>();
        triggerMap.put("triggerId", "");
        triggerMap.put("name", "trigger-1");

        WorkflowVO workflow = new WorkflowVO();
        Map<String, Object> configs = new HashMap<>();
        configs.put("trigger_list", List.of(triggerMap));
        workflow.setConfigs(configs);

        TriggerConfig convertedTrigger = new TriggerConfig();
        convertedTrigger.setTriggerId("");
        convertedTrigger.setName("trigger-1");
        when(mapper.convertValue(any(), eq(TriggerConfig.class))).thenReturn(convertedTrigger);

        var result = workflowManagementService.getTriggerConfigList(workflow);

        assertNotNull(result);
        assertEquals(1, result.size());
        assertFalse(result.get(0).getTriggerId().isEmpty());
    }

    // ==================== buildGlobalModelReference ====================

    @Test
    void testBuildGlobalModelReference_NullWorkflow() {
        List<MappingEntity> relateComponents = new ArrayList<>();

        workflowManagementService.buildGlobalModelReference("p1", "w1", null, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    @Test
    void testBuildGlobalModelReference_NullConfigs() {
        WorkflowVO workflow = new WorkflowVO();
        workflow.setConfigs(null);
        List<MappingEntity> relateComponents = new ArrayList<>();

        workflowManagementService.buildGlobalModelReference("p1", "w1", workflow, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    @Test
    void testBuildGlobalModelReference_NoDefaultModel() {
        WorkflowVO workflow = new WorkflowVO();
        Map<String, Object> configs = new HashMap<>();
        workflow.setConfigs(configs);
        List<MappingEntity> relateComponents = new ArrayList<>();

        workflowManagementService.buildGlobalModelReference("p1", "w1", workflow, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    @Test
    void testBuildGlobalModelReference_NoModelDeploymentId() {
        WorkflowVO workflow = new WorkflowVO();
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> defaultModel = new HashMap<>();
        defaultModel.put("model_type", "llm");
        configs.put("default_model", defaultModel);
        workflow.setConfigs(configs);
        List<MappingEntity> relateComponents = new ArrayList<>();

        workflowManagementService.buildGlobalModelReference("p1", "w1", workflow, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    // ==================== buildGlobalMemoryRepo ====================

    @Test
    void testBuildGlobalMemoryRepo_NullWorkflow() {
        List<MappingEntity> relateComponents = new ArrayList<>();

        workflowManagementService.buildGlobalMemoryRepo(null, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    @Test
    void testBuildGlobalMemoryRepo_NoMemoryConfig() {
        WorkflowVO workflow = new WorkflowVO();
        workflow.setId("wf-1");
        workflow.setName("Test");
        workflow.setConfigs(new HashMap<>());
        List<MappingEntity> relateComponents = new ArrayList<>();

        workflowManagementService.buildGlobalMemoryRepo(workflow, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    @Test
    void testBuildGlobalMemoryRepo_MemoryRepoExists() {
        WorkflowVO workflow = new WorkflowVO();
        workflow.setId("wf-1");
        workflow.setName("Test");
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> memoryConfig = new HashMap<>();
        memoryConfig.put("memory_repo_id", "repo-1");
        configs.put("memory_config", memoryConfig);
        workflow.setConfigs(configs);

        MemoryRepoEntity memoryRepoEntity = MemoryRepoEntity.builder()
            .name("Test Repo")
            .description("Test Description")
            .build();
        when(memoryRepoMapper.selectById("repo-1")).thenReturn(memoryRepoEntity);

        List<MappingEntity> relateComponents = new ArrayList<>();
        workflowManagementService.buildGlobalMemoryRepo(workflow, relateComponents, "v1");

        assertEquals(1, relateComponents.size());
        assertEquals("repo-1", relateComponents.get(0).getResourceId());
        assertEquals("memory", relateComponents.get(0).getResourceType());
    }

    @Test
    void testBuildGlobalMemoryRepo_MemoryRepoNotExist() {
        WorkflowVO workflow = new WorkflowVO();
        workflow.setId("wf-1");
        workflow.setName("Test");
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> memoryConfig = new HashMap<>();
        memoryConfig.put("memory_repo_id", "repo-1");
        configs.put("memory_config", memoryConfig);
        workflow.setConfigs(configs);

        when(memoryRepoMapper.selectById("repo-1")).thenReturn(null);

        List<MappingEntity> relateComponents = new ArrayList<>();
        workflowManagementService.buildGlobalMemoryRepo(workflow, relateComponents, "v1");

        assertTrue(relateComponents.isEmpty());
    }

    // ==================== getWorkflowObsPath ====================

    @Test
    void testGetWorkflowObsPath() {
        String result = workflowManagementService.getWorkflowObsPath("wf-1", "ir", "v1");

        assertEquals("workflow/ir/wf-1/wf-1_v1.json", result);
    }

    @Test
    void testGetWorkflowObsPath_FlowType() {
        String result = workflowManagementService.getWorkflowObsPath("wf-2", "flow", "v2");

        assertEquals("workflow/flow/wf-2/wf-2_v2.json", result);
    }

    // ==================== queryWorkflowList ====================

    @Test
    void testQueryWorkflowList() {
        List<WorkflowEntity> expected = List.of(new WorkflowEntity());
        when(workflowMapper.queryWorkflowList(10, 0)).thenReturn(expected);

        var result = workflowManagementService.queryWorkflowList(10, 0);

        assertEquals(1, result.size());
        verify(workflowMapper).queryWorkflowList(10, 0);
    }

    // ==================== workflowDslToIr ====================

    @Test
    void testWorkflowDslToIr_Delegation() {
        WorkflowEntity entity = new WorkflowEntity();
        WorkflowVO workflowVo = new WorkflowVO();
        when(workflowCommonService.workflowDslToIr(anyString(), any(), any(), isNull())).thenReturn("ir/path");

        String result = workflowManagementService.workflowDslToIr("wf-1", entity, workflowVo);

        assertEquals("ir/path", result);
        verify(workflowCommonService).workflowDslToIr(eq("wf-1"), eq(entity), eq(workflowVo), isNull());
    }

    @Test
    void testWorkflowDslToIr_WithVersionId() {
        WorkflowEntity entity = new WorkflowEntity();
        WorkflowVO workflowVo = new WorkflowVO();
        workflowVo.setId("wf-1");
        workflowVo.setName("Test");

        Map<String, Object> metadata = new HashMap<>();
        when(workflowCommonService.parseMetadata(any())).thenReturn(metadata);
        when(irAdapterService.adaptWorkflow(any(), any())).thenReturn(new HashMap<>());
        when(obsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("ir/path");

        String result = workflowManagementService.workflowDslToIr("wf-1", entity, workflowVo, "v1");

        assertEquals("ir/path", result);
        verify(obsService).uploadObsFile(eq("wf-1"), eq("wf-1_v1"), anyString(), anyString(), anyString());
    }

    @Test
    void testWorkflowDslToIr_WithoutVersionId() {
        WorkflowEntity entity = new WorkflowEntity();
        WorkflowVO workflowVo = new WorkflowVO();
        workflowVo.setId("wf-1");
        workflowVo.setName("Test");

        Map<String, Object> metadata = new HashMap<>();
        when(workflowCommonService.parseMetadata(any())).thenReturn(metadata);
        when(irAdapterService.adaptWorkflow(any(), any())).thenReturn(new HashMap<>());
        when(obsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("ir/path");

        String result = workflowManagementService.workflowDslToIr("wf-1", entity, workflowVo, null);

        assertEquals("ir/path", result);
        verify(obsService).uploadObsFile(eq("wf-1"), eq("wf-1"), anyString(), anyString(), anyString());
    }

    // ==================== listWorkflowVersions ====================

    @Test
    void testListWorkflowVersions_Success() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

        VersionListRsp expectedRsp = new VersionListRsp();
        when(agentCommonService.listVersions(eq("wf-1"), eq(10))).thenReturn(expectedRsp);

        ListWorkflowVersionsQo qo = new ListWorkflowVersionsQo();
        qo.setWorkspaceId("w1");

        var result = workflowManagementService.listWorkflowVersions("p1", "wf-1", qo);

        assertNotNull(result);
        verify(agentCommonService).listVersions("wf-1", 10);
    }

    @Test
    void testListWorkflowVersions_WorkflowNotFound() {
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(null);

        ListWorkflowVersionsQo qo = new ListWorkflowVersionsQo();
        qo.setWorkspaceId("w1");

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.listWorkflowVersions("p1", "wf-1", qo));
    }

    @Test
    void testListWorkflowVersions_CrossWorkspace() {
        ReflectionTestUtils.setField(workflowManagementService, "publishCrossWorkspace", true);

        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), any(), anyString())).thenReturn(entity);

        VersionListRsp expectedRsp = new VersionListRsp();
        when(agentCommonService.listVersions(eq("wf-1"), eq(10))).thenReturn(expectedRsp);

        ListWorkflowVersionsQo qo = new ListWorkflowVersionsQo();
        qo.setWorkspaceId("w1");

        var result = workflowManagementService.listWorkflowVersions("p1", "wf-1", qo);

        assertNotNull(result);
        assertNull(qo.getWorkspaceId());
    }

    // ==================== deleteWorkflowVersion ====================

    @Test
    void testDeleteWorkflowVersion_NoPermission() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("other-workspace");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setId("rv-1");
            when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(releaseVersion);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.deleteWorkflowVersion("p1", "wf-1", "v1", "w1"));
        }
    }

    @Test
    void testDeleteWorkflowVersion_SharedVersion_throwsCannotDelete() {
        // 已共享到资产广场的版本不允许删除——应抛 SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setId("rv-1");
            when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(releaseVersion);

            doThrow(new AgentStudioException(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY))
                .when(shareResourceManagerService).checkVersionSharedOrNot(eq("wf-1"), eq("v1"));

            AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
                workflowManagementService.deleteWorkflowVersion("p1", "wf-1", "v1", "w1"));
            assertEquals(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY, ex.getErrorCode());
            // 共享校验抛错后不应走到删除逻辑
            verify(releaseVersionMapper, never()).deleteByPrimaryKey(any());
            verify(agentCommonService, never()).softDeleteReleaseVersionById(any());
        }
    }

    @Test
    void testDeleteWorkflowVersion_callsVersionSharedCheck() {
        // 未共享版本应顺利调用删除流程，且校验方法以正确参数被调用
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setId("rv-1");
            releaseVersion.setDslPath("dsl/path");
            releaseVersion.setIrPath("ir/path");
            releaseVersion.setAppId("wf-1");
            when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(releaseVersion);
            when(releaseVersionMapper.selectByAppId(anyString())).thenReturn(Collections.emptyList());

            workflowManagementService.deleteWorkflowVersion("p1", "wf-1", "v1", "w1");

            verify(shareResourceManagerService).checkVersionSharedOrNot("wf-1", "v1");
        }
    }

    @Test
    void testDeleteWorkflowVersion_SoftDelete_AllVersionsDeleted() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setWorkspaceId("w1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setId("rv-1");
            releaseVersion.setDslPath("dsl/path");
            releaseVersion.setIrPath("ir/path");
            releaseVersion.setAppId("wf-1");
            when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(releaseVersion);
            when(releaseVersionMapper.selectByAppId(anyString())).thenReturn(Collections.emptyList());

            var result = workflowManagementService.deleteWorkflowVersion("p1", "wf-1", "v1", "w1");

            assertNotNull(result);
            assertEquals("v1", result.getId());
            verify(workflowMapper).updateWorkflowEntity(eq("p1"), eq("wf-1"), any());
        }
    }

    // ==================== getWorkflowVersion ====================

    @Test
    void testGetWorkflowVersion_Success() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            when(shareResourceManagerService.queryShareResourceEntityByResourceIdAndVersionId(anyString(), anyString(), anyString()))
                .thenReturn(null);

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setName("Test");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setDslPath("dsl/path");
            when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(releaseVersion);

            WorkflowEntity wfEntity = new WorkflowEntity();
            wfEntity.setId("wf-1");
            wfEntity.setName("Test");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(wfEntity);
            when(obsService.downloadObsFile(anyString())).thenReturn("{\"nodes\":[],\"configs\":{}}");
            when(obsService.getAbsolutePath(any())).thenReturn("/abs/path");

            GetWorkflowVersionQo qo = new GetWorkflowVersionQo();
            var result = workflowManagementService.getWorkflowVersion("p1", "wf-1", "v1", null, qo);

            assertNotNull(result);
        }
    }

    @Test
    void testGetWorkflowVersion_VersionNotFound() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            when(shareResourceManagerService.queryShareResourceEntityByResourceIdAndVersionId(anyString(), anyString(), anyString()))
                .thenReturn(null);

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
            when(releaseVersionMapper.selectByAppIdAndVersionId(anyString(), anyString())).thenReturn(null);

            GetWorkflowVersionQo qo = new GetWorkflowVersionQo();
            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.getWorkflowVersion("p1", "wf-1", "v1", null, qo));
        }
    }

    // ==================== deleteWorkflowChannel ====================

    @Test
    void testDeleteWorkflowChannel_AgentBuilderChannel() {
        ReflectionTestUtils.setField(workflowManagementService, "publishAgentBuilderEnable", true);

        var result = workflowManagementService.deleteWorkflowChannel("p1", "wf-1", "wf-1", "w1");

        assertNull(result);
        verify(agentSpaceService).unpublish("w1", "wf-1");
    }

    @Test
    void testDeleteWorkflowChannel_ChannelNotExist() {
        when(releaseChannelMapper.selectByIdAppIdWorkspaceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.deleteWorkflowChannel("p1", "wf-1", "ch-1", "w1"));
    }

    @Test
    void testDeleteWorkflowChannel_UnsupportedChannelType() {
        ReleaseChannel channel = new ReleaseChannel();
        channel.setId("ch-1");
        channel.setWorkspaceId("w1");
        channel.setChannelType(CommonConstant.WEB_PAGE_CHANNEL);
        when(releaseChannelMapper.selectByIdAppIdWorkspaceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(channel);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.deleteWorkflowChannel("p1", "wf-1", "ch-1", "w1"));
    }

    @Test
    void testDeleteWorkflowChannel_AppStoreChannel() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            ReleaseChannel channel = new ReleaseChannel();
            channel.setId("ch-1");
            channel.setWorkspaceId("w1");
            channel.setChannelType(CommonConstant.APP_STORE_CHANNEL);
            channel.setAppId("wf-1");
            when(releaseChannelMapper.selectByIdAppIdWorkspaceId(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(channel);

            var result = workflowManagementService.deleteWorkflowChannel("p1", "wf-1", "ch-1", "w1");

            assertNotNull(result);
            assertEquals("ch-1", result.getId());
            verify(appMapper).deleteByResourceId("wf-1", "p1", "w1");
            verify(publishUtils).deletePublish(eq("wf-1"), anyString(), any());
        }
    }

    // ==================== modifyWorkflowChannel ====================

    @Test
    void testModifyWorkflowChannel_ChannelNotExist() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);
        when(releaseChannelMapper.selectByIdAppIdWorkspaceId(anyString(), anyString(), anyString(), anyString()))
            .thenReturn(null);

        ModifyChannelReq body = new ModifyChannelReq();
        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.modifyWorkflowChannel("p1", "wf-1", "ch-1", "w1", body));
    }

    // ==================== exportWorkflows ====================

    @Test
    void testExportWorkflows() {
        ExportParams body = new ExportParams();
        org.springframework.core.io.Resource mockResource = mock(org.springframework.core.io.Resource.class);
        when(agentImportExportService.exportWorkflows(anyString(), anyString(), any())).thenReturn(mockResource);

        var result = workflowManagementService.exportWorkflows("p1", "w1", body);

        assertNotNull(result);
        verify(agentImportExportService).exportWorkflows("p1", "w1", body);
    }

    // ==================== getReferenceType ====================

    @Test
    void testGetReferenceType_SameWorkspace() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ShareResourceEntity shareResource = new ShareResourceEntity();
            shareResource.setWorkspaceId("w1");

            String result = workflowManagementService.getReferenceType(shareResource);

            assertEquals("direct", result);
        }
    }

    @Test
    void testGetReferenceType_DifferentWorkspace() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ShareResourceEntity shareResource = new ShareResourceEntity();
            shareResource.setWorkspaceId("w2");

            String result = workflowManagementService.getReferenceType(shareResource);

            assertEquals("share", result);
        }
    }

    // ==================== listWorkflowLastVersions ====================

    @Test
    void testListWorkflowLastVersions_Success() {
        ListWorkflowLastVersionsQo qo = new ListWorkflowLastVersionsQo();
        qo.setOffset(0);
        qo.setLimit(10);

        WorkflowVersionEntity versionEntity = new WorkflowVersionEntity();
        versionEntity.setId("wf-1");
        versionEntity.setName("Test");
        versionEntity.setVersionId("v1");
        versionEntity.setVersionName("Version 1");
        List<WorkflowVersionEntity> versionList = List.of(versionEntity);

        when(workflowMapper.selectLastVersionByWorkflowSearchCriteria(anyString(), any())).thenReturn(versionList);

        var result = workflowManagementService.listWorkflowLastVersions("p1", qo);

        assertNotNull(result);
        assertEquals(1, result.getWorkflowVersionList().size());
    }

    @Test
    void testListWorkflowLastVersions_EmptyList() {
        ListWorkflowLastVersionsQo qo = new ListWorkflowLastVersionsQo();
        qo.setOffset(0);
        qo.setLimit(10);

        when(workflowMapper.selectLastVersionByWorkflowSearchCriteria(anyString(), any()))
            .thenReturn(Collections.emptyList());

        var result = workflowManagementService.listWorkflowLastVersions("p1", qo);

        assertNotNull(result);
        assertTrue(result.getWorkflowVersionList().isEmpty());
    }

    @Test
    void testListWorkflowLastVersions_CrossWorkspace() {
        ReflectionTestUtils.setField(workflowManagementService, "publishCrossWorkspace", true);

        ListWorkflowLastVersionsQo qo = new ListWorkflowLastVersionsQo();
        qo.setOffset(0);
        qo.setLimit(10);
        qo.setWorkspaceId("w1");

        when(workflowMapper.selectLastVersionByWorkflowSearchCriteria(anyString(), any()))
            .thenReturn(Collections.emptyList());

        var result = workflowManagementService.listWorkflowLastVersions("p1", qo);

        assertNotNull(result);
        assertNull(qo.getWorkspaceId());
    }

    // ==================== listWorkflowChannels ====================

    @Test
    void testListWorkflowChannels_Success() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

        ReleaseChannel channel = new ReleaseChannel();
        channel.setId("ch-1");
        channel.setChannelType("web_page");
        List<ReleaseChannel> channels = new ArrayList<>(List.of(channel));
        when(releaseChannelMapper.selectByAppId(anyString(), anyString())).thenReturn(channels);

        VersionListRsp versionListRsp = new VersionListRsp();
        versionListRsp.setVersionList(Collections.emptyList());
        when(agentCommonService.listVersions(anyString(), anyInt())).thenReturn(versionListRsp);

        ListWorkflowChannelsQo qo = new ListWorkflowChannelsQo();
        qo.setWorkspaceId("w1");

        var result = workflowManagementService.listWorkflowChannels("p1", "wf-1", qo);

        assertNotNull(result);
        assertEquals(1, result.getCount());
    }

    @Test
    void testListWorkflowChannels_WithAgentBuilder() {
        ReflectionTestUtils.setField(workflowManagementService, "publishAgentBuilderEnable", true);

        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(entity);

        when(releaseChannelMapper.selectByAppId(anyString(), anyString())).thenReturn(new ArrayList<>());

        ReleaseChannel agentBuilderChannel = new ReleaseChannel();
        agentBuilderChannel.setId("ab-1");
        when(agentSpaceService.publishQuery(anyString(), anyString())).thenReturn(agentBuilderChannel);

        VersionListRsp versionListRsp = new VersionListRsp();
        versionListRsp.setVersionList(Collections.emptyList());
        when(agentCommonService.listVersions(anyString(), anyInt())).thenReturn(versionListRsp);

        ListWorkflowChannelsQo qo = new ListWorkflowChannelsQo();
        qo.setWorkspaceId("w1");

        var result = workflowManagementService.listWorkflowChannels("p1", "wf-1", qo);

        assertNotNull(result);
        assertEquals(1, result.getCount());
    }

    // ==================== publishWorkflow ====================

    @Test
    void testPublishWorkflow_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class);
             MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user");
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setProjectId("op-project-id");
            entity.setDslPath("dsl/path");
            entity.setWorkflowType("chat");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(entity);
            when(obsService.downloadObsFile(anyString())).thenReturn("{\"configs\":{}}");

            var result = workflowManagementService.publishWorkflow("op-project-id", "wf-1", List.of("tag1"));

            assertNull(result);
            verify(appMapper).deleteByResourceId(eq("wf-1"), eq("op-project-id"), anyString());
            verify(appMapper).insert(any());
            verify(workflowMapper).updateWorkflowEntity(eq("op-project-id"), eq("wf-1"), any());
        }
    }

    // ==================== releaseWorkflowVersion ====================

    @Test
    void testReleaseWorkflowVersion_WorkflowNotFound() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(null);

            CreateVersionReq req = new CreateVersionReq();
            req.setVersionName("v1");

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.releaseWorkflowVersion("p1", "wf-1", "w1", req));
        }
    }

    @Test
    void testReleaseWorkflowVersion_VersionNameAlreadyExists() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(entity);

            ReleaseVersion existingVersion = new ReleaseVersion();
            existingVersion.setVersionName("v1");
            when(releaseVersionMapper.selectByAppId("wf-1")).thenReturn(List.of(existingVersion));

            CreateVersionReq req = new CreateVersionReq();
            req.setVersionName("v1");

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.releaseWorkflowVersion("p1", "wf-1", "w1", req));
        }
    }

    @Test
    void testReleaseWorkflowVersion_ExceedsMaxSize() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(entity);

            List<ReleaseVersion> versions = new ArrayList<>();
            for (int i = 0; i <= 10; i++) {
                ReleaseVersion rv = new ReleaseVersion();
                rv.setVersionName("v" + i);
                versions.add(rv);
            }
            when(releaseVersionMapper.selectByAppId("wf-1")).thenReturn(versions);

            CreateVersionReq req = new CreateVersionReq();
            req.setVersionName("new-version");

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.releaseWorkflowVersion("p1", "wf-1", "w1", req));
        }
    }

    // ==================== updateWorkflow ====================

    @Test
    void testUpdateWorkflow_NotFound() {
        WorkflowInfo body = new WorkflowInfo();
        body.setUpdateTime(System.currentTimeMillis());
        when(workflowMapper.getWorkflowEntityByWorkspaceId(anyString(), anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.updateWorkflow("p1", "wf-1", "w1", body));
    }

    // ==================== getWorkflowEnvs ====================

    @Test
    void testGetWorkflowEnvs_WorkflowNotFound() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(null);

            GetWorkflowEnvsQo qo = new GetWorkflowEnvsQo();
            qo.setVersionId("");
            qo.setNestedCheck(false);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.getWorkflowEnvs("p1", "wf-1", qo));
        }
    }

    @Test
    void testGetWorkflowEnvs_NoEnvironment() {
        try (MockedStatic<ThreadLocalUtils> tl = mockStatic(ThreadLocalUtils.class)) {
            tl.when(ThreadLocalUtils::getWorkspaceId).thenReturn("w1");

            WorkflowEntity entity = new WorkflowEntity();
            entity.setId("wf-1");
            entity.setDslPath("dsl/path");
            when(workflowCommonService.getWorkflowByWorkspaceAndOpProject(anyString(), anyString(), anyString()))
                .thenReturn(entity);
            when(obsService.downloadObsFile(anyString())).thenReturn("{\"nodes\":[],\"configs\":{}}");

            GetWorkflowEnvsQo qo = new GetWorkflowEnvsQo();
            qo.setVersionId("");
            qo.setNestedCheck(false);

            var result = workflowManagementService.getWorkflowEnvs("p1", "wf-1", qo);

            assertNotNull(result);
            assertTrue(result.getVariables().isEmpty());
        }
    }

    // ==================== generateWorkflowPrologue ====================

    @Test
    void testGenerateWorkflowPrologue_WorkflowNotFound() {
        when(workflowMapper.selectByWorkflowId(anyString(), anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.generateWorkflowPrologue("p1", "wf-1", "w1"));
    }

    @Test
    void testGenerateWorkflowPrologue_NoDefaultModel() {
        WorkflowEntity entity = new WorkflowEntity();
        entity.setId("wf-1");
        entity.setDslPath("dsl/path");
        when(workflowMapper.selectByWorkflowId(anyString(), anyString(), anyString())).thenReturn(entity);
        when(obsService.downloadObsFile(anyString())).thenReturn("{\"configs\":{}}");

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.generateWorkflowPrologue("p1", "wf-1", "w1"));
    }

    // ==================== recommendedWorkflowQuestions ====================

    @Test
    void testRecommendedWorkflowQuestions_WorkflowNotFound() {
        when(workflowMapper.selectByWorkflowId(anyString(), anyString(), anyString())).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            workflowManagementService.recommendedWorkflowQuestions("p1", "wf-1", "w1"));
    }

    // ==================== parseThirdpartyWorkflowFile ====================

    @Test
    void testParseThirdpartyWorkflowFile_Exception() {
        try (MockedStatic<com.openjiuwen.studio.agent.common.utils.FileCommonUtils> fu =
                 mockStatic(com.openjiuwen.studio.agent.common.utils.FileCommonUtils.class)) {
            fu.when(() -> com.openjiuwen.studio.agent.common.utils.FileCommonUtils.validatedFile(any(), anyLong(), anyString()))
                .thenThrow(new RuntimeException("file error"));

            org.springframework.web.multipart.MultipartFile file = mock(org.springframework.web.multipart.MultipartFile.class);

            assertThrows(AgentStudioException.class, () ->
                workflowManagementService.parseThirdpartyWorkflowFile("dify", "w1", "p1", file));
        }
    }
}
