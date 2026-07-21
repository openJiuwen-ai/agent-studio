/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UuidUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfoRefWorkflows;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.HistoryAgentEntity;
import com.openjiuwen.studio.agent.manager.entity.HistoryMappingEntity;
import com.openjiuwen.studio.agent.manager.entity.HistoryReleaseVersionEntity;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.HistoryAgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.HistoryMappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.HistoryReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.models.AskModelReq;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;

@ExtendWith(MockitoExtension.class)
class AgentCommonServiceTest {

    @Mock
    private AgentMapper agentMapper;
    @Mock
    private MappingMapper mappingMapper;
    @Mock
    private ReleaseVersionMapper releaseVersionMapper;
    @Mock
    private HistoryAgentMapper historyAgentMapper;
    @Mock
    private HistoryReleaseVersionMapper historyReleaseVersionMapper;
    @Mock
    private HistoryMappingMapper historyMappingMapper;
    @Mock
    private ToolMapper toolMapper;
    @Mock
    private WorkflowMapper workflowMapper;
    @Mock
    private MgObsService mgObsService;
    @Mock
    private IPlugin pluginService;
    @Mock
    private ShareResourceManagerService shareResourceManagerService;
    @Mock
    private ModelServiceMapper modelServiceMapper;
    @Mock
    private FreeModelServiceMapper freeModelServiceMapper;
    @Mock
    private RelationManagementService relationManagementService;

    @InjectMocks
    private AgentCommonService agentCommonService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(agentCommonService, "agentDefaultIcon", "default-icon.png");
        ReflectionTestUtils.setField(agentCommonService, "controllerDefaultIcon", "controller-icon.png");
        ReflectionTestUtils.setField(agentCommonService, "iconMaxSize", "100");
        ReflectionTestUtils.setField(agentCommonService, "maxCustomizeNodeSize", 100);
        ReflectionTestUtils.setField(agentCommonService, "opSvcProjectId", "op-project-id");
        ReflectionTestUtils.setField(agentCommonService, "envType", "test");
        ReflectionTestUtils.setField(agentCommonService, "modelObsPrefix", "/test/prefix");
    }

    @Test
    void testUploadToObs_Success() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("/obs/path");

        String result = agentCommonService.uploadToObs(agent, "content", "ir");

        assertEquals("/obs/path", result);
        verify(mgObsService).uploadObsFile(eq("agent-1"), eq("agent-1"), eq(CommonConstant.AGENT), anyString(), eq("ir"));
    }

    @Test
    void testUploadToObsWithVersion_Success() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");

        agentCommonService.uploadToObsWithVersion(agent, "content", "ir", "v1");

        verify(mgObsService).uploadObsFile(eq("agent-1"), eq("agent-1_v1"), eq(CommonConstant.AGENT), anyString(), eq("ir"));
    }

    @Test
    void testUploadToObsNoNullWithVersion_Success() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");

        agentCommonService.uploadToObsNoNullWithVersion(agent, "content", "ir", "v1");

        verify(mgObsService).uploadObsFile(eq("agent-1"), eq("agent-1_v1"), eq(CommonConstant.AGENT), anyString(), eq("ir"));
    }

    @Test
    void testUploadToObsNoNull_Success() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), anyString()))
            .thenReturn("/obs/path2");

        String result = agentCommonService.uploadToObsNoNull(agent, "content", "dsl");

        assertEquals("/obs/path2", result);
        verify(mgObsService).uploadObsFile(eq("agent-1"), eq("agent-1"), eq(CommonConstant.AGENT), anyString(), eq("dsl"));
    }

    @Test
    void testGetAgentObsPath_WithoutVersion() {
        String result = agentCommonService.getAgentObsPath("id-1", "ir");
        assertEquals("agent/ir/id-1/id-1.json", result);
    }

    @Test
    void testGetAgentObsPath_WithVersion() {
        String result = agentCommonService.getAgentObsPath("id-1", "ir", "v2");
        assertEquals("agent/ir/id-1/id-1_v2.json", result);
    }

    @Test
    void testGetAgent_Found() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        when(agentMapper.selectByPrimaryKey("p1", "agent-1")).thenReturn(agent);

        Agent result = agentCommonService.getAgent("p1", "agent-1");

        assertNotNull(result);
        assertEquals("agent-1", result.getAgentId());
    }

    @Test
    void testGetAgent_NotFound_ThrowsException() {
        when(agentMapper.selectByPrimaryKey("p1", "agent-1")).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.getAgent("p1", "agent-1"));
        assertEquals(StudioError.AGENT_NOT_EXIST, ex.getErrorCode());
    }

    @Test
    void testGetAgent_WithWorkspaceId_FoundDirectly() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        when(agentMapper.selectByProjectIdAndWorkspaceId("p1", "w1", "agent-1")).thenReturn(agent);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            Agent result = agentCommonService.getAgent("p1", "w1", "agent-1");
            assertNotNull(result);
            assertEquals("agent-1", result.getAgentId());
        }
    }

    @Test
    void testGetAgent_WithWorkspaceId_FoundViaShare() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        when(agentMapper.selectByProjectIdAndWorkspaceId("p1", "w1", "agent-1")).thenReturn(null);
        when(shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(anyString(), anyString())).thenReturn(true);
        when(agentMapper.selectById("agent-1")).thenReturn(agent);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            Agent result = agentCommonService.getAgent("p1", "w1", "agent-1");
            assertNotNull(result);
            assertEquals("agent-1", result.getAgentId());
        }
    }

    @Test
    void testGetAgent_WithWorkspaceId_NotFound_ThrowsException() {
        when(agentMapper.selectByProjectIdAndWorkspaceId("p1", "w1", "agent-1")).thenReturn(null);
        when(shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(anyString(), anyString())).thenReturn(false);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentCommonService.getAgent("p1", "w1", "agent-1"));
            assertEquals(StudioError.AGENT_NOT_EXIST, ex.getErrorCode());
        }
    }

    @Test
    void testGetRefWfLastVersion_NullList() {
        Map<String, WorkflowInfoRefWorkflows> result = agentCommonService.getRefWfLastVersion(null);
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetRefWfLastVersion_EmptyList() {
        Map<String, WorkflowInfoRefWorkflows> result = agentCommonService.getRefWfLastVersion(Collections.emptyList());
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetRefWfLastVersion_WithWorkflows() {
        WorkflowEntity wf = new WorkflowEntity();
        wf.setId("wf-1");
        List<WorkflowEntity> workflows = List.of(wf);

        ReleaseVersion rv = new ReleaseVersion();
        rv.setAppId("wf-1");
        rv.setVersionId("v1");
        rv.setVersionName("Version 1");

        when(releaseVersionMapper.queryLastVersionByAppIds(any(Set.class))).thenReturn(List.of(rv));

        Map<String, WorkflowInfoRefWorkflows> result = agentCommonService.getRefWfLastVersion(workflows);

        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("v1", result.get("wf-1").getLastVersionId());
        assertEquals("Version 1", result.get("wf-1").getLastVersionName());
    }

    @Test
    void testGetRefWfLastVersion_NoReleaseVersions() {
        WorkflowEntity wf = new WorkflowEntity();
        wf.setId("wf-1");
        List<WorkflowEntity> workflows = List.of(wf);

        when(releaseVersionMapper.queryLastVersionByAppIds(any(Set.class))).thenReturn(Collections.emptyList());

        Map<String, WorkflowInfoRefWorkflows> result = agentCommonService.getRefWfLastVersion(workflows);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testCheckAgentIcon_NullIcon_ThrowsException() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.checkAgentIcon(null));
        assertEquals(StudioError.AGENT_ICON_EXIST, ex.getErrorCode());
    }

    @Test
    void testCheckAgentIcon_EmptyIcon_ThrowsException() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.checkAgentIcon(""));
        assertEquals(StudioError.AGENT_ICON_EXIST, ex.getErrorCode());
    }

    @Test
    void testCheckAgentIcon_SizeExceedsLimit_ThrowsException() {
        String largeBase64 = "data:image/png;base64," + "A".repeat(200 * 1024);
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.checkAgentIcon(largeBase64));
        assertEquals(StudioError.AGENT_ICON_SIZE_EXCEEDS_LIMIT, ex.getErrorCode());
    }

    @Test
    void testCheckAgentIcon_ValidIcon_NoException() {
        String validBase64 = "data:image/png;base64," + "A".repeat(50);
        assertDoesNotThrow(() -> agentCommonService.checkAgentIcon(validBase64));
    }

    @Test
    void testListVersions_EmptyResult() {
        when(releaseVersionMapper.selectByAppIdWithLimit("app-1", 10)).thenReturn(Collections.emptyList());

        VersionListRsp result = agentCommonService.listVersions("app-1", 10);

        assertNotNull(result);
        assertEquals(0, result.getCount());
        assertTrue(result.getVersionList().isEmpty());
    }

    @Test
    void testListVersions_WithVersions() {
        ReleaseVersion rv = new ReleaseVersion();
        rv.setVersionId("v1");
        rv.setVersionName("Version 1");
        rv.setVersionNote("note");
        rv.setStatus("published");

        when(releaseVersionMapper.selectByAppIdWithLimit("app-1", 10)).thenReturn(List.of(rv));

        VersionListRsp result = agentCommonService.listVersions("app-1", 10);

        assertNotNull(result);
        assertEquals(1, result.getCount());
        assertEquals(1, result.getVersionList().size());
        assertEquals("v1", result.getVersionList().get(0).getVersionId());
    }

    @Test
    void testIsExceedMaxCustomizeNodeNum_NotExceed() {
        when(toolMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(10);
        when(workflowMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(20);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            boolean result = agentCommonService.isExceedMaxCustomizeNodeNum();
            assertFalse(result);
        }
    }

    @Test
    void testIsExceedMaxCustomizeNodeNum_Exceed() {
        when(toolMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(60);
        when(workflowMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(50);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            boolean result = agentCommonService.isExceedMaxCustomizeNodeNum();
            assertTrue(result);
        }
    }

    @Test
    void testPublishCustomizeNodeCheck_NoPermission_ThrowsException() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.publishCustomizeNodeCheck("other-project", "id-1", "v1", 1));
        assertEquals(StudioError.NO_PERMISSION_PUBLISH_CUSTOMIZE_NODE, ex.getErrorCode());
    }

    @Test
    void testPublishCustomizeNodeCheck_NotPublished_ThrowsException() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.publishCustomizeNodeCheck("op-project-id", "id-1", null, 1));
        assertEquals(StudioError.PUBLISH_CUSTOMIZE_NODE_ERROR, ex.getErrorCode());
    }

    @Test
    void testPublishCustomizeNodeCheck_BlankVersion_ThrowsException() {
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> agentCommonService.publishCustomizeNodeCheck("op-project-id", "id-1", "", 1));
        assertEquals(StudioError.PUBLISH_CUSTOMIZE_NODE_ERROR, ex.getErrorCode());
    }

    @Test
    void testPublishCustomizeNodeCheck_ExceedLimit_ThrowsException() {
        when(toolMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(60);
        when(workflowMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(50);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> agentCommonService.publishCustomizeNodeCheck("op-project-id", "id-1", "v1", 1));
            assertEquals(StudioError.CUSTOMIZE_NODE_NUMBER_EXCEED_LIMIT, ex.getErrorCode());
        }
    }

    @Test
    void testPublishCustomizeNodeCheck_Success() {
        when(toolMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(10);
        when(workflowMapper.selectCustomizeNodeCountByProjectId(anyString(), anyString())).thenReturn(20);

        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");
            assertDoesNotThrow(() ->
                agentCommonService.publishCustomizeNodeCheck("op-project-id", "id-1", "v1", 1));
        }
    }

    @Test
    void testPublishCustomizeNodeCheck_Unpublish_Success() {
        assertDoesNotThrow(() ->
            agentCommonService.publishCustomizeNodeCheck("op-project-id", "id-1", "v1", 0));
    }

    @Test
    void testBuildAskModelReq_WithConfig() {
        ModelConfig config = new ModelConfig();
        config.setTopP(0.8);
        config.setTemperature(0.7);

        AskModelReq result = agentCommonService.buildAskModelReq("deploy-1", "model-type", "model-name", config, "hello");

        assertNotNull(result);
        assertEquals("deploy-1|model-name", result.getModelName());
        assertFalse(result.getIsStream());
        assertEquals(0.8, result.getTopP());
        assertEquals(0.7, result.getTemperature());
        assertEquals(1, result.getMessages().size());
    }

    @Test
    void testBuildAskModelReq_NullConfig_Defaults() {
        AskModelReq result = agentCommonService.buildAskModelReq("deploy-1", null, null, null, "hello");

        assertNotNull(result);
        assertEquals("deploy-1", result.getModelName());
        assertFalse(result.getIsStream());
        assertEquals(0.5, result.getTopP());
        assertEquals(0.5, result.getTemperature());
        assertEquals(1, result.getMessages().size());
    }

    @Test
    void testBuildAskModelReq_SimpleEnv_SetsModelConfigPath() {
        ReflectionTestUtils.setField(agentCommonService, "envType", "simple");
        ModelConfig config = new ModelConfig();
        config.setTopP(0.5);
        config.setTemperature(0.5);

        AskModelReq result = agentCommonService.buildAskModelReq("deploy-1", "type-1", "model-1", config, "query");

        assertNotNull(result);
        assertEquals("deploy-1|model-1", result.getModelName());
    }

    @Test
    void testValidTools_EmptyList_NoCall() {
        agentCommonService.validTools("p1", "w1", Collections.emptyList());
        verify(pluginService, never()).validTools(anyString(), anyString(), anyList());
    }

    @Test
    void testValidTools_NullList_NoCall() {
        agentCommonService.validTools("p1", "w1", null);
        verify(pluginService, never()).validTools(anyString(), anyString(), anyList());
    }

    @Test
    void testValidTools_WithToolIds_Delegates() {
        agentCommonService.validTools("p1", "w1", List.of("tool-1", "tool-2"));
        verify(pluginService, times(1)).validTools("p1", "w1", List.of("tool-1", "tool-2"));
    }

    @Test
    void testSoftDeleteMapping_WithMappings() {
        MappingEntity m1 = new MappingEntity();
        m1.setMappingId("m1");
        m1.setAppId("app-1");
        m1.setResourceId("r1");

        when(mappingMapper.selectAllByAppId("app-1")).thenReturn(List.of(m1));
        when(historyMappingMapper.insertBatch(anyList())).thenReturn(1);

        try (MockedStatic<UuidUtils> uuidMock = mockStatic(UuidUtils.class)) {
            uuidMock.when(UuidUtils::getUUID).thenReturn("uuid-1");
            agentCommonService.softDeleteMapping("app-1");
        }

        verify(mappingMapper).selectAllByAppId("app-1");
        verify(historyMappingMapper).insertBatch(anyList());
        verify(mappingMapper).deleteBatchByAppId("app-1", null, true);
    }

    @Test
    void testSoftDeleteMapping_EmptyMappings() {
        when(mappingMapper.selectAllByAppId("app-1")).thenReturn(Collections.emptyList());

        agentCommonService.softDeleteMapping("app-1");

        verify(mappingMapper).selectAllByAppId("app-1");
        verify(historyMappingMapper, never()).insertBatch(anyList());
        verify(mappingMapper).deleteBatchByAppId("app-1", null, true);
    }

    @Test
    void testSoftDeleteAgent_AgentExists() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setProjectId("p1");

        when(agentMapper.selectByPrimaryKey("p1", "agent-1")).thenReturn(agent);
        when(historyAgentMapper.insert(any(HistoryAgentEntity.class))).thenReturn(1);

        try (MockedStatic<UuidUtils> uuidMock = mockStatic(UuidUtils.class)) {
            uuidMock.when(UuidUtils::getUUID).thenReturn("uuid-1");
            agentCommonService.softDeleteAgent("p1", "agent-1");
        }

        verify(agentMapper).selectByPrimaryKey("p1", "agent-1");
        verify(historyAgentMapper).insert(any(HistoryAgentEntity.class));
        verify(agentMapper).deleteByPrimaryKey("agent-1", "p1");
    }

    @Test
    void testSoftDeleteAgent_AgentNotFound_Skip() {
        when(agentMapper.selectByPrimaryKey("p1", "agent-1")).thenReturn(null);

        agentCommonService.softDeleteAgent("p1", "agent-1");

        verify(agentMapper).selectByPrimaryKey("p1", "agent-1");
        verify(historyAgentMapper, never()).insert(any());
        verify(agentMapper, never()).deleteByPrimaryKey(anyString(), anyString());
    }

    @Test
    void testParseMetadata() {
        Agent agent = new Agent();
        agent.setProjectId("p1");
        agent.setWorkspaceId("w1");
        agent.setUpdatedOn(new java.util.Date());
        agent.setMemoryVariables(null);
        agent.setTriggerList(null);

        Map<String, Object> result = agentCommonService.parseMetadata(agent);

        assertNotNull(result);
        assertEquals("p1", result.get("projectId"));
        assertEquals("w1", result.get("workspaceId"));
        assertNotNull(result.get("updatedAt"));
        assertNull(result.get("memoryVariables"));
        assertNull(result.get("triggerConfigs"));
    }

    @Test
    void testParseMetadata_WithMemoryAndTrigger() {
        Agent agent = new Agent();
        agent.setProjectId("p1");
        agent.setWorkspaceId("w1");
        agent.setUpdatedOn(new java.util.Date());
        agent.setMemoryVariables(List.of());
        agent.setTriggerList(List.of());

        Map<String, Object> result = agentCommonService.parseMetadata(agent);

        assertNotNull(result);
        assertEquals("p1", result.get("projectId"));
        assertNotNull(result.get("memoryVariables"));
        assertNotNull(result.get("triggerConfigs"));
    }

    @Test
    void testSoftDeleteReleaseVersionByAppId_not_exist() {
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");

        when(releaseVersionMapper.selectByAppId("testAppId")).thenReturn(List.of(releaseVersion));
        when(releaseVersionMapper.deleteByAppId("testAppId")).thenReturn(0);
        when(historyReleaseVersionMapper.findByAppIdAndVersionId("testAppId", "v1.0")).thenReturn(null);

        agentCommonService.softDeleteReleaseVersionByAppId("testAppId");

        verify(releaseVersionMapper, times(1)).selectByAppId("testAppId");
        verify(historyReleaseVersionMapper, times(1)).findByAppIdAndVersionId("testAppId", "v1.0");
        verify(historyReleaseVersionMapper, times(1)).insertBatch(anyList());
        verify(releaseVersionMapper, times(1)).deleteByAppId("testAppId");
    }

    @Test
    void testSoftDeleteReleaseVersionByAppId_exist() {
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");

        HistoryReleaseVersionEntity existingHistory = mock(HistoryReleaseVersionEntity.class);

        when(releaseVersionMapper.selectByAppId(anyString())).thenReturn(List.of(releaseVersion));
        when(releaseVersionMapper.deleteByAppId(anyString())).thenReturn(0);
        when(historyReleaseVersionMapper.findByAppIdAndVersionId("testAppId", "v1.0")).thenReturn(existingHistory);

        agentCommonService.softDeleteReleaseVersionByAppId("testAppId");

        verify(releaseVersionMapper, times(1)).selectByAppId("testAppId");
        verify(historyReleaseVersionMapper, times(1)).findByAppIdAndVersionId("testAppId", "v1.0");
        verify(historyReleaseVersionMapper, times(0)).insertBatch(anyList());
        verify(releaseVersionMapper, times(1)).deleteByAppId("testAppId");
    }

    @Test
    void testSoftDeleteReleaseVersionByAppId_EmptyList() {
        when(releaseVersionMapper.selectByAppId("testAppId")).thenReturn(Collections.emptyList());

        agentCommonService.softDeleteReleaseVersionByAppId("testAppId");

        verify(releaseVersionMapper, times(1)).selectByAppId("testAppId");
        verify(historyReleaseVersionMapper, never()).insertBatch(anyList());
        verify(releaseVersionMapper, times(1)).deleteByAppId("testAppId");
    }

    @Test
    void testSoftDeleteReleaseVersionById() {
        ReleaseVersion releaseVersion = mock(ReleaseVersion.class);
        when(releaseVersion.getId()).thenReturn("id-123");
        when(releaseVersion.getVersionId()).thenReturn("v1.0");
        when(releaseVersion.getVersionName()).thenReturn("Version v1.0");
        when(releaseVersion.getAppId()).thenReturn("testAppId");
        when(releaseVersion.getAppType()).thenReturn("agent");
        when(releaseVersion.getStatus()).thenReturn("published");

        when(historyReleaseVersionMapper.insert(any(HistoryReleaseVersionEntity.class))).thenReturn(1);
        when(releaseVersionMapper.deleteByPrimaryKey(anyString())).thenReturn(1);

        agentCommonService.softDeleteReleaseVersionById(releaseVersion);

        verify(historyReleaseVersionMapper, times(1)).insert(any(HistoryReleaseVersionEntity.class));
        verify(releaseVersionMapper, times(1)).deleteByPrimaryKey("id-123");
    }

    @Test
    void testBuildComplexAgentInfo_PlanExecute_PublishTimeFromDatabase() {
        // 准备测试数据
        Date dbPublishTime = new Date(System.currentTimeMillis() - 86400000); // 1天前
        Date dslPublishTime = new Date(System.currentTimeMillis() - 172800000); // 2天前（过期的）
        Date updateTime = new Date();

        Agent agent = new Agent();
        agent.setAgentId("agent-123");
        agent.setProjectId("project-1");
        agent.setWorkspaceId("workspace-1");
        agent.setSubType(CommonConstant.PLANEXECUTE_TYPE);
        agent.setDslPath("/obs/dsl/path");
        agent.setPublishedOn(dbPublishTime);
        agent.setUpdatedOn(updateTime);

        // DSL中返回过期的publish_time
        String dslJson = String.format("{\"agentId\":\"agent-123\",\"publishTime\":%d,\"updateTime\":%d}",
            dslPublishTime.getTime(), updateTime.getTime());
        when(mgObsService.downloadObsFile("/obs/dsl/path")).thenReturn(dslJson);

        // Mock依赖服务
        when(relationManagementService.listAgentTools(anyString(), anyString(), anyString(), anyInt(), anyInt()))
            .thenReturn(Collections.emptyList());
        when(relationManagementService.listAgentMcpServers(anyString()))
            .thenReturn(Collections.emptyList());
        when(relationManagementService.listAgentSkills(anyString()))
            .thenReturn(Collections.emptyList());

        // 执行
        var result = agentCommonService.buildComplexAgentInfo(agent);

        // 验证publishTime应该来自数据库，而不是DSL
        assertNotNull(result);
        assertEquals(dbPublishTime, result.getPublishTime(),
            "publishTime should be from database, not from DSL");
    }

    @Test
    void testBuildComplexAgentInfo_DeepResearch_PublishTimeFromDatabase() {
        // 准备测试数据
        Date dbPublishTime = new Date(System.currentTimeMillis() - 86400000); // 1天前
        Date dslPublishTime = new Date(System.currentTimeMillis() - 172800000); // 2天前（过期的）
        Date updateTime = new Date();

        Agent agent = new Agent();
        agent.setAgentId("agent-456");
        agent.setProjectId("project-1");
        agent.setWorkspaceId("workspace-1");
        agent.setSubType(CommonConstant.DEEPRESEARCH_TYPE);
        agent.setDslPath("/obs/dsl/path");
        agent.setPublishedOn(dbPublishTime);
        agent.setUpdatedOn(updateTime);

        // DSL中返回过期的publish_time
        String dslJson = String.format("{\"agentId\":\"agent-456\",\"publishTime\":%d,\"updateTime\":%d}",
            dslPublishTime.getTime(), updateTime.getTime());
        when(mgObsService.downloadObsFile("/obs/dsl/path")).thenReturn(dslJson);

        // 执行
        var result = agentCommonService.buildComplexAgentInfo(agent);

        // 验证publishTime应该来自数据库，而不是DSL
        assertNotNull(result);
        assertEquals(dbPublishTime, result.getPublishTime(),
            "publishTime should be from database, not from DSL for DeepResearch");
    }
}
