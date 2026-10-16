/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentListRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.ListAgentsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRetrievePolicy;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AgentVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.TagMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.quartz.Scheduler;
import org.springframework.context.MessageSource;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;

class AgentManagementServiceTest {

    @Mock
    private AgentMapper agentMapper;

    @Mock
    private AgentVersionMapper agentVersionMapper;

    @Mock
    private ReleaseVersionMapper releaseVersionMapper;

    @Mock
    private ReleaseChannelMapper releaseChannelMapper;

    @Mock
    private AppMapper appMapper;

    @Mock
    private WorkflowMapper workflowMapper;

    @Mock
    private TagMapper tagMapper;

    @Mock
    private MgObsService mgObsService;

    @Mock
    private ObjectMapper jacksonObjectMapper;

    @Mock
    private MappingMapper mappingMapper;

    @Mock
    private RelationManagementService relationManagementService;

    @Mock
    private IrAdapterService irAdapterService;

    @Mock
    private Scheduler scheduler;

    @Mock
    private org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor fixedThreadPool;

    @Mock
    private AgentImportExportService agentImportExportService;

    @Mock
    private AgentCommonService agentCommonService;

    @Mock
    private ControllerManagementService controllerManagementService;

    @Mock
    private PublishUtils publishUtils;

    @Mock
    private MessageSource messageSource;

    @Mock
    private JiuWenService jiuWenService;

    @Mock
    private WorkspaceMapper workspaceMapper;

    @Mock
    private PermissionService permissionService;

    @Mock
    private AgentMemoryConfigService agentMemoryConfigService;

    @Mock
    private AssetFreeTrialMgmtService assetFreeTrialMgmtService;

    @Mock
    private ShareResourceMapper shareResourceMapper;

    @Mock
    private ShareResourceManagerService shareResourceManagerService;

    @Mock
    private AgentRuntimeClient agentRuntimeClient;

    @Mock
    private AgentSpaceService agentSpaceService;

    @Mock
    private WorkflowValidationService workflowValidationService;

    private AgentManagementService agentManagementService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        agentManagementService = new AgentManagementService(
            agentMapper, agentVersionMapper, releaseVersionMapper, releaseChannelMapper,
            appMapper, workflowMapper, tagMapper, mgObsService, jacksonObjectMapper,
            mappingMapper, relationManagementService, irAdapterService, scheduler,
            agentImportExportService, agentCommonService, controllerManagementService,
            publishUtils, messageSource, jiuWenService, workspaceMapper, permissionService,
            agentMemoryConfigService, assetFreeTrialMgmtService
        );
        ReflectionTestUtils.setField(agentManagementService, "shareResourceMapper", shareResourceMapper);
        ReflectionTestUtils.setField(agentManagementService, "shareResourceManagerService", shareResourceManagerService);
        ReflectionTestUtils.setField(agentManagementService, "agentRuntimeClient", agentRuntimeClient);
        ReflectionTestUtils.setField(agentManagementService, "agentSpaceService", agentSpaceService);
        ReflectionTestUtils.setField(agentManagementService, "workflowValidationService", workflowValidationService);
        // COM-02: fixedThreadPool 迁移为 @Autowired agentMgmtCleanupExecutor bean，手工 new 不注入→setField
        ReflectionTestUtils.setField(agentManagementService, "fixedThreadPool", fixedThreadPool);
        ReflectionTestUtils.setField(agentManagementService, "opSvcProjectId", "op-project-id");
        ReflectionTestUtils.setField(agentManagementService, "agentRuntimeEndpoint", "http://runtime");
        ReflectionTestUtils.setField(agentManagementService, "runAgentStreamUrl", "http://stream");
        ReflectionTestUtils.setField(agentManagementService, "endpointTemplate", "http://endpoint/%s/%s");
        ReflectionTestUtils.setField(agentManagementService, "releaseMaxSize", 10);
        ReflectionTestUtils.setField(agentManagementService, "fileMaxSize", 1024L);
        ReflectionTestUtils.setField(agentManagementService, "webpageEndpoint", 8080);
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMin", 0.0);
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMax", 1.0);
        ReflectionTestUtils.setField(agentManagementService, "longTermMemoryEnable", false);
        ReflectionTestUtils.setField(agentManagementService, "isSoftDelete", true);
        ReflectionTestUtils.setField(agentManagementService, "authorization", "Bearer token");
        ReflectionTestUtils.setField(agentManagementService, "knowledgeSource", "custom");
        ReflectionTestUtils.setField(agentManagementService, "publishAgentBuilderEnable", false);
        ReflectionTestUtils.setField(agentManagementService, "importMaxLen", 100);
        ReflectionTestUtils.setField(agentManagementService, "publishAppEnable", false);
        ReflectionTestUtils.setField(agentManagementService, "contentReviewConfigs", "");
        ReflectionTestUtils.setField(agentManagementService, "assetAppFreeTrialQuotaLimit", 10);
        ReflectionTestUtils.setField(agentManagementService, "controllerEndPointTemplate", "http://controller/%s/%s");
    }

    @Test
    void testDeleteAgent_Success() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);
        agent.setTriggerList(null);

        when(agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId)).thenReturn(agent);
        when(shareResourceMapper.countResourceByResourceId(projectId, agentId)).thenReturn(0);

        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class);
             MockedStatic<LanguageUtils> langCtx = mockStatic(LanguageUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            langCtx.when(LanguageUtils::getLanguage).thenReturn("zh-cn");

            CommonDeleteRsp result = agentManagementService.deleteAgent(projectId, agentId, workspaceId);

            assertNotNull(result);
            assertEquals(agentId, result.getId());
            // COM-02 回归断言：异步清理任务提交到受管 executor（防误删 fixedThreadPool.execute 调度）
            verify(fixedThreadPool).execute(any(Runnable.class));
        }
    }

    @Test
    void testDeleteAgent_AgentNotExist() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        when(agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId)).thenReturn(null);

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.deleteAgent(projectId, agentId, workspaceId));
    }

    @Test
    void testDeleteAgent_SharedResourceCannotDelete() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setTriggerList(null);

        when(agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId)).thenReturn(agent);
        when(shareResourceMapper.countResourceByResourceId(projectId, agentId)).thenReturn(1);

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.deleteAgent(projectId, agentId, workspaceId));
    }

    @Test
    void testDeleteAgent_HardDelete() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        ReflectionTestUtils.setField(agentManagementService, "isSoftDelete", false);

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setTriggerList(null);

        when(agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId)).thenReturn(agent);
        when(shareResourceMapper.countResourceByResourceId(projectId, agentId)).thenReturn(0);

        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class);
             MockedStatic<LanguageUtils> langCtx = mockStatic(LanguageUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            langCtx.when(LanguageUtils::getLanguage).thenReturn("zh-cn");

            CommonDeleteRsp result = agentManagementService.deleteAgent(projectId, agentId, workspaceId);

            assertNotNull(result);
            assertEquals(agentId, result.getId());
            verify(mappingMapper).deleteBatchByAppId(agentId, null, true);
            verify(releaseVersionMapper).deleteByAppId(agentId);
            verify(agentMapper).deleteByPrimaryKey(agentId, projectId);
            // COM-02 回归断言：异步清理任务提交到受管 executor（防误删 fixedThreadPool.execute 调度）
            verify(fixedThreadPool).execute(any(Runnable.class));
        }
    }

    @Test
    void testRetrieveAgent_Success() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setName("Test Agent");

        AgentInfo expectedInfo = new AgentInfo();
        expectedInfo.setAgentId(agentId);
        expectedInfo.setName("Test Agent");

        when(agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId)).thenReturn(agent);
        when(agentCommonService.buildComplexAgentInfo(agent)).thenReturn(expectedInfo);

        AgentInfo result = agentManagementService.retrieveAgent(projectId, agentId, workspaceId);

        assertNotNull(result);
        assertEquals(agentId, result.getAgentId());
        assertEquals("Test Agent", result.getName());
    }

    @Test
    void testRetrieveAgent_NotExist() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        when(agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId)).thenReturn(null);
        when(shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(workspaceId, agentId)).thenReturn(false);

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.retrieveAgent(projectId, agentId, workspaceId));
    }

    @Test
    void testListAgents_Success() {
        String projectId = "project-1";
        ListAgentsQo query = new ListAgentsQo();
        query.setWorkspaceId("workspace-1");
        query.setOffset(0);
        query.setLimit(10);

        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("Test Agent");
        agent.setType("agent");
        agent.setStatus("draft");
        List<Agent> agentList = new ArrayList<>();
        agentList.add(agent);

        when(agentMapper.selectByProjectIdAndSearchCriteria(eq(projectId), any())).thenReturn(agentList);

        AgentListRsp result = agentManagementService.listAgents(projectId, query);

        assertNotNull(result);
        assertNotNull(result.getAgentList());
    }

    @Test
    void testListAgents_EmptyResult() {
        String projectId = "project-1";
        ListAgentsQo query = new ListAgentsQo();
        query.setWorkspaceId("workspace-1");
        query.setOffset(0);
        query.setLimit(10);

        when(agentMapper.selectByProjectIdAndSearchCriteria(eq(projectId), any())).thenReturn(Collections.emptyList());

        AgentListRsp result = agentManagementService.listAgents(projectId, query);

        assertNotNull(result);
        assertNotNull(result.getAgentList());
        assertEquals(0, result.getAgentList().size());
    }

    @Test
    void testListAgents_WithFilters() {
        String projectId = "project-1";
        ListAgentsQo query = new ListAgentsQo();
        query.setWorkspaceId("workspace-1");
        query.setName("test");
        query.setType("agent");
        query.setStatus("published");
        query.setOffset(0);
        query.setLimit(10);

        when(agentMapper.selectByProjectIdAndSearchCriteria(eq(projectId), any())).thenReturn(Collections.emptyList());

        AgentListRsp result = agentManagementService.listAgents(projectId, query);

        assertNotNull(result);
    }

    @Test
    void testModifyAgent_AgentNotExist() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        ModifyAgentReq body = new ModifyAgentReq();

        when(agentMapper.selectById(agentId)).thenReturn(null);

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.modifyAgent(projectId, agentId, workspaceId, body));
    }

    @Test
    void testModifyAgent_HasBeenUpdated() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        ModifyAgentReq body = new ModifyAgentReq();
        body.setUpdateTime(new Date());

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setUpdatedOn(new Date(0));

        when(agentMapper.selectById(agentId)).thenReturn(agent);

        assertThrows(AgentStudioException.class,
            () -> agentManagementService.modifyAgent(projectId, agentId, workspaceId, body));
    }

    @Test
    void testGetAgent_ById_Success() {
        String projectId = "project-1";
        String agentId = "agent-1";

        Agent expected = new Agent();
        expected.setAgentId(agentId);

        when(agentCommonService.getAgent(projectId, agentId)).thenReturn(expected);

        Agent result = agentManagementService.getAgent(projectId, agentId);

        assertNotNull(result);
        assertEquals(agentId, result.getAgentId());
    }

    @Test
    void testGetAgent_WithWorkspace_Success() {
        String projectId = "project-1";
        String workspaceId = "workspace-1";
        String agentId = "agent-1";

        Agent expected = new Agent();
        expected.setAgentId(agentId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(expected);

        Agent result = agentManagementService.getAgent(projectId, workspaceId, agentId);

        assertNotNull(result);
        assertEquals(agentId, result.getAgentId());
    }

    /**
     * 用例描述：创建发布渠道时版本不存在（version 为 null），应抛出 AGENT_VERSION_NOT_EXIST 异常
     * 预制条件：Agent 存在，通道类型为 WEB_PAGE，oldChannel 为 null（走新建分支），version 查询返回 null
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1, channelType=WEB_PAGE, versionId=v-not-exist
     * 预期结果：抛出 AgentStudioException，错误码为 AGENT_VERSION_NOT_EXIST
     */
    @Test
    void testCreateAgentChannel_VersionNotFound_ThrowsException() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("WEB_PAGE");
        req.setVersionId("v-not-exist");
        req.setVisibilityScope(CreateChannelReq.VisibilityScopeEnum.TENANT);
        req.setCallCount(100);

        when(releaseChannelMapper.selectByAppIdAndTypeAndWorkspaceId(agentId, "WEB_PAGE", projectId, workspaceId))
            .thenReturn(null);
        when(releaseVersionMapper.selectByAppIdAndVersionId(agentId, "v-not-exist")).thenReturn(null);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req));
            assertEquals(StudioError.AGENT_VERSION_NOT_EXIST, ex.getErrorCode());
        }
    }

    /**
     * 用例描述：创建发布渠道时版本存在，应正常返回 VersionChannelInfo
     * 预制条件：Agent 存在，通道类型为 WEB_PAGE，oldChannel 为 null（走新建分支），version 查询返回有效版本
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1, channelType=WEB_PAGE, versionId=v-1
     * 预期结果：返回非空 VersionChannelInfo，versionId 和 channelType 正确
     */
    @Test
    void testCreateAgentChannel_Success() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("WEB_PAGE");
        req.setVersionId("v-1");
        req.setVisibilityScope(CreateChannelReq.VisibilityScopeEnum.TENANT);
        req.setCallCount(100);

        ReleaseVersion version = new ReleaseVersion();
        version.setVersionId("v-1");
        version.setVersionName("Version 1.0");

        when(releaseChannelMapper.selectByAppIdAndTypeAndWorkspaceId(agentId, "WEB_PAGE", projectId, workspaceId))
            .thenReturn(null);
        when(releaseVersionMapper.selectByAppIdAndVersionId(agentId, "v-1")).thenReturn(version);

        ReleaseChannel channel = new ReleaseChannel();
        channel.setId("channel-1");
        channel.setAppId(agentId);
        channel.setAppType("AGENT");
        channel.setVersionId("v-1");
        channel.setVersionName("Version 1.0");
        channel.setChannelType("WEB_PAGE");
        channel.setStatus("released");
        when(releaseChannelMapper.selectByPrimaryKey(any())).thenReturn(channel);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            VersionChannelInfo result = agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req);

            assertNotNull(result);
            assertEquals("channel-1", result.getId());
            assertEquals("v-1", result.getVersionId());
            assertEquals("WEB_PAGE", result.getChannelType());
            verify(releaseChannelMapper).insert(any(ReleaseChannel.class));
            verify(agentRuntimeClient).createReleaseInfo(eq("token"), eq(projectId), any());
        }
    }

    /**
     * 用例描述：创建发布渠道时通道已存在（更新分支），版本不存在（version 为 null），应抛出 AGENT_VERSION_NOT_EXIST
     * 预制条件：Agent 存在，通道类型为 WEB_PAGE，oldChannel 非空（走更新分支），version 查询返回 null
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1, channelType=WEB_PAGE, versionId=v-not-exist
     * 预期结果：抛出 AgentStudioException，错误码为 AGENT_VERSION_NOT_EXIST，updateByPrimaryKeySelective 不被调用
     */
    @Test
    void testCreateAgentChannel_UpdateBranchVersionNotFound_ThrowsException() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        ReleaseChannel oldChannel = new ReleaseChannel();
        oldChannel.setId("ch-1");
        oldChannel.setChannelType("WEB_PAGE");
        oldChannel.setVersionId("v-old");

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("WEB_PAGE");
        req.setVersionId("v-not-exist");
        req.setVisibilityScope(CreateChannelReq.VisibilityScopeEnum.TENANT);
        req.setCallCount(100);

        when(releaseChannelMapper.selectByAppIdAndTypeAndWorkspaceId(agentId, "WEB_PAGE", projectId, workspaceId))
            .thenReturn(oldChannel);
        when(releaseVersionMapper.selectByAppIdAndVersionId(agentId, "v-not-exist")).thenReturn(null);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req));
            assertEquals(StudioError.AGENT_VERSION_NOT_EXIST, ex.getErrorCode());
            verify(releaseChannelMapper, never()).updateByPrimaryKeySelective(any());
        }
    }

    /**
     * 用例描述：创建发布渠道时通道已存在（更新分支），版本存在时正常更新通道记录并回填版本名
     * 预制条件：Agent 存在，通道类型为 WEB_PAGE，oldChannel 非空（走更新分支），version 查询返回有效版本
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1, channelType=WEB_PAGE, versionId=v-1
     * 预期结果：返回非空 VersionChannelInfo，updateByPrimaryKeySelective 被调用且携带新版本名
     */
    @Test
    void testCreateAgentChannel_UpdateBranchSuccess() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        ReleaseChannel oldChannel = new ReleaseChannel();
        oldChannel.setId("ch-1");
        oldChannel.setChannelType("WEB_PAGE");
        oldChannel.setVersionId("v-old");
        oldChannel.setShortCode("short-001");

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("WEB_PAGE");
        req.setVersionId("v-1");
        req.setVisibilityScope(CreateChannelReq.VisibilityScopeEnum.TENANT);
        req.setCallCount(100);

        ReleaseVersion version = new ReleaseVersion();
        version.setVersionId("v-1");
        version.setVersionName("Version 1.0");

        when(releaseChannelMapper.selectByAppIdAndTypeAndWorkspaceId(agentId, "WEB_PAGE", projectId, workspaceId))
            .thenReturn(oldChannel);
        when(releaseVersionMapper.selectByAppIdAndVersionId(agentId, "v-1")).thenReturn(version);

        ReleaseChannel channel = new ReleaseChannel();
        channel.setId("ch-1");
        channel.setAppId(agentId);
        channel.setAppType("AGENT");
        channel.setVersionId("v-1");
        channel.setVersionName("Version 1.0");
        channel.setChannelType("WEB_PAGE");
        channel.setShortCode("short-001");
        channel.setStatus("released");
        when(releaseChannelMapper.selectByPrimaryKey(any())).thenReturn(channel);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            VersionChannelInfo result = agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req);

            assertNotNull(result);
            assertEquals("ch-1", result.getId());
            assertEquals("v-1", result.getVersionId());
            // 更新分支回填版本名（MR 2380：更新分支补 version 判空 + setVersionName）
            ArgumentCaptor<ReleaseChannel> captor = ArgumentCaptor.forClass(ReleaseChannel.class);
            verify(releaseChannelMapper).updateByPrimaryKeySelective(captor.capture());
            assertEquals("Version 1.0", captor.getValue().getVersionName());
            verify(releaseChannelMapper, never()).insert(any(ReleaseChannel.class));
            verify(agentRuntimeClient).createReleaseInfo(eq("token"), eq(projectId), any());
        }
    }

    /**
     * 用例描述：创建发布渠道类型为 agentBuilder 时直接发布到 agentBuilder 空间
     * 预制条件：Agent 存在（type 非空），channelType=agentBuilder
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1
     * 预期结果：返回非空 VersionChannelInfo，agentSpaceService.publish 被调用
     */
    @Test
    void testCreateAgentChannel_AgentBuilderChannel() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);
        agent.setType("AGENT");

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("agentBuilder");

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            VersionChannelInfo result = agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req);

            assertNotNull(result);
            verify(agentSpaceService).publish(any(ReleaseChannel.class));
        }
    }

    /**
     * 用例描述：创建发布渠道类型为 APP_STORE 但百宝箱发布未启用时抛出 AGENT_CHANNEL_TYPE_INCORRECT
     * 预制条件：Agent 存在，publishAppEnable=false（默认），channelType=APP_STORE
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1
     * 预期结果：抛出 AgentStudioException，错误码为 AGENT_CHANNEL_TYPE_INCORRECT
     */
    @Test
    void testCreateAgentChannel_AppStoreNotSupported() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("APP_STORE");

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req));
            assertEquals(StudioError.AGENT_CHANNEL_TYPE_INCORRECT, ex.getErrorCode());
        }
    }

    /**
     * 用例描述：创建发布渠道类型非法时抛出 AGENT_CHANNEL_TYPE_INCORRECT
     * 预制条件：Agent 存在，channelType=INVALID
     * 输入参数：projectId=project-1, agentId=agent-1, workspaceId=workspace-1
     * 预期结果：抛出 AgentStudioException，错误码为 AGENT_CHANNEL_TYPE_INCORRECT
     */
    @Test
    void testCreateAgentChannel_InvalidChannelType() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String workspaceId = "workspace-1";

        Agent agent = new Agent();
        agent.setAgentId(agentId);
        agent.setProjectId(projectId);

        when(agentCommonService.getAgent(projectId, workspaceId, agentId)).thenReturn(agent);

        CreateChannelReq req = new CreateChannelReq();
        req.setChannelType("INVALID");

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentManagementService.createAgentChannel(projectId, agentId, workspaceId, req));
            assertEquals(StudioError.AGENT_CHANNEL_TYPE_INCORRECT, ex.getErrorCode());
        }
    }

    /**
     * 用例描述：修改发布渠道时版本不存在（version 为 null），应抛出 AGENT_VERSION_NOT_EXIST 异常
     * 预制条件：oldChannel 存在，version 查询返回 null
     * 输入参数：projectId=project-1, agentId=agent-1, channelId=ch-1, workspaceId=workspace-1, versionId=v-not-exist
     * 预期结果：抛出 AgentStudioException，错误码为 AGENT_VERSION_NOT_EXIST
     */
    @Test
    void testModifyAgentChannel_VersionNotFound_ThrowsException() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String channelId = "ch-1";
        String workspaceId = "workspace-1";

        ReleaseChannel oldChannel = new ReleaseChannel();
        oldChannel.setId(channelId);
        oldChannel.setChannelType("WEB_PAGE");
        oldChannel.setVersionId("v-old");

        when(releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, agentId, projectId, workspaceId))
            .thenReturn(oldChannel);
        when(releaseVersionMapper.selectByAppIdAndVersionId(agentId, "v-not-exist")).thenReturn(null);

        ModifyChannelReq body = new ModifyChannelReq();
        body.setVersionId("v-not-exist");
        body.setVisibilityScope(ModifyChannelReq.VisibilityScopeEnum.TENANT);
        body.setCallCount(100);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentManagementService.modifyAgentChannel(projectId, agentId, channelId, workspaceId, body));
            assertEquals(StudioError.AGENT_VERSION_NOT_EXIST, ex.getErrorCode());
        }
    }

    /**
     * 用例描述：修改发布渠道时版本存在，应正常返回 VersionChannelInfo
     * 预制条件：oldChannel 存在（channelType=WEB_PAGE），version 查询返回有效版本
     * 输入参数：projectId=project-1, agentId=agent-1, channelId=ch-1, workspaceId=workspace-1, versionId=v-2
     * 预期结果：返回非空 VersionChannelInfo，versionId 为新版本 v-2
     */
    @Test
    void testModifyAgentChannel_Success() {
        String projectId = "project-1";
        String agentId = "agent-1";
        String channelId = "ch-1";
        String workspaceId = "workspace-1";

        ReleaseChannel oldChannel = new ReleaseChannel();
        oldChannel.setId(channelId);
        oldChannel.setChannelType("WEB_PAGE");
        oldChannel.setVersionId("v-old");
        oldChannel.setShortCode("short-001");

        ReleaseVersion version = new ReleaseVersion();
        version.setVersionId("v-2");
        version.setVersionName("Version 2.0");

        when(releaseChannelMapper.selectByIdAppIdWorkspaceId(channelId, agentId, projectId, workspaceId))
            .thenReturn(oldChannel);
        when(releaseVersionMapper.selectByAppIdAndVersionId(agentId, "v-2")).thenReturn(version);

        ReleaseChannel updatedChannel = new ReleaseChannel();
        updatedChannel.setId(channelId);
        updatedChannel.setAppId(agentId);
        updatedChannel.setAppType("AGENT");
        updatedChannel.setVersionId("v-2");
        updatedChannel.setVersionName("Version 2.0");
        updatedChannel.setChannelType("WEB_PAGE");
        updatedChannel.setShortCode("short-001");
        updatedChannel.setVisibilityScope("TENANT");
        updatedChannel.setCallCount(100);
        when(releaseChannelMapper.selectByPrimaryKey(channelId)).thenReturn(updatedChannel);

        ModifyChannelReq body = new ModifyChannelReq();
        body.setVersionId("v-2");
        body.setVisibilityScope(ModifyChannelReq.VisibilityScopeEnum.TENANT);
        body.setCallCount(100);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");

            VersionChannelInfo result = agentManagementService.modifyAgentChannel(projectId, agentId, channelId,
                workspaceId, body);

            assertNotNull(result);
            assertEquals(channelId, result.getId());
            assertEquals("v-2", result.getVersionId());
            verify(releaseChannelMapper).updateByPrimaryKeySelective(any(ReleaseChannel.class));
            verify(agentRuntimeClient).createReleaseInfo(eq("token"), eq(projectId), any());
        }
    }

    // ======================================================================
    // checkKnowledgeRetrievePolicy clamp 校验验证
    // ======================================================================

    /**
     * 通过反射调用 private checkKnowledgeRetrievePolicy，验证阈值 clamp 逻辑。
     */
    private void invokeCheckKnowledgeRetrievePolicy(KnowledgeRetrievePolicy policy) throws Exception {
        Method method = AgentManagementService.class.getDeclaredMethod(
            "checkKnowledgeRetrievePolicy", KnowledgeRetrievePolicy.class);
        method.setAccessible(true);
        method.invoke(agentManagementService, policy);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_recallThresholdAboveMax_clampedToMax() throws Exception {
        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(20.0f);
        policy.setFaqThreshold(0.5f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(1.0f, policy.getRecallThreshold(), 0.0001f);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_recallThresholdBelowMin_clampedToMin() throws Exception {
        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(-5.0f);
        policy.setFaqThreshold(0.5f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(0.0f, policy.getRecallThreshold(), 0.0001f);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_recallThresholdWithinRange_unchanged() throws Exception {
        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(0.5f);
        policy.setFaqThreshold(0.9f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(0.5f, policy.getRecallThreshold(), 0.0001f);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_faqThresholdAboveMax_clampedToMax() throws Exception {
        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(0.5f);
        policy.setFaqThreshold(20.0f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(1.0f, policy.getFaqThreshold(), 0.0001f);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_faqThresholdBelowMin_clampedToMin() throws Exception {
        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(0.5f);
        policy.setFaqThreshold(-5.0f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(0.0f, policy.getFaqThreshold(), 0.0001f);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_faqThresholdWithinRange_unchanged() throws Exception {
        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(0.5f);
        policy.setFaqThreshold(0.9f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(0.9f, policy.getFaqThreshold(), 0.0001f);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_nullPolicy_noException() throws Exception {
        // policy 为 null 时直接返回，不抛异常
        invokeCheckKnowledgeRetrievePolicy(null);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_customRange_clampsCorrectly() throws Exception {
        // 模拟客户配置 -10~10
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMin", -10.0);
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMax", 10.0);

        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(15.0f);   // 超过 max=10，clamp 到 10
        policy.setFaqThreshold(-15.0f);     // 低于 min=-10，clamp 到 -10

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(10.0f, policy.getRecallThreshold(), 0.0001f);
        assertEquals(-10.0f, policy.getFaqThreshold(), 0.0001f);

        // 恢复默认值
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMin", 0.0);
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMax", 1.0);
    }

    @Test
    void testCheckKnowledgeRetrievePolicy_customRange_negativeValueWithinRange_unchanged() throws Exception {
        // 模拟客户配置 -10~10，负值在范围内不被 clamp
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMin", -10.0);
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMax", 10.0);

        KnowledgeRetrievePolicy policy = new KnowledgeRetrievePolicy();
        policy.setRecallThreshold(-5.0f);
        policy.setFaqThreshold(5.0f);

        invokeCheckKnowledgeRetrievePolicy(policy);

        assertEquals(-5.0f, policy.getRecallThreshold(), 0.0001f);
        assertEquals(5.0f, policy.getFaqThreshold(), 0.0001f);

        // 恢复默认值
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMin", 0.0);
        ReflectionTestUtils.setField(agentManagementService, "knowledgeRecallThresholdMax", 1.0);
    }
}
