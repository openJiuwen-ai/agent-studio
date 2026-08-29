/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.WfImportDataWrapper;
import com.openjiuwen.studio.agent.manager.dto.QueryShareResourceListQo;
import com.openjiuwen.studio.agent.manager.dto.QuerySharedResourceListQo;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceRequestInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceInfo;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareInfo;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.prompt.engineering.mapper.PePromptTemplateMapper;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.ArrayList;
import java.util.List;

@ExtendWith(MockitoExtension.class)
class ShareResourceManagerServiceTest {

    @Mock
    private ShareResourceMapper shareResourceMapper;

    @Mock
    private ShareScopeMapper shareScopeMapper;

    @Mock
    private AgentMapper agentMapper;

    @Mock
    private WorkflowMapper workflowMapper;

    @Mock
    private PluginMapper pluginMapper;

    @Mock
    private ReleaseVersionMapper releaseVersionMapper;

    @Mock
    private WorkspaceMapper workspaceMapper;

    @Mock
    private MappingMapper mappingMapper;

    @Mock
    private MgObsService obsService;

    @Mock
    private IPluginBase pluginBase;

    @Mock
    private IPlugin pluginAdapter;

    @Mock
    private McpServiceDao mcpServiceDao;

    @Mock
    private PePromptTemplateMapper pePromptTemplateMapper;

    @InjectMocks
    private ShareResourceManagerService shareResourceManagerService;

    private static final String PROJECT_ID = "project-1";
    private static final String WORKSPACE_ID = "workspace-1";
    private static final String RESOURCE_ID = "resource-1";

    @Test
    void testCancelShareResource_ResourceNotFound() {
        when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
            .thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            shareResourceManagerService.cancelShareResource(PROJECT_ID, RESOURCE_ID, WORKSPACE_ID, "controller"));
    }

    @Test
    void testCancelShareResource_Success() {
        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setResourceType("controller");
        when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
            .thenReturn(entity);

        Boolean result = shareResourceManagerService.cancelShareResource(PROJECT_ID, RESOURCE_ID, WORKSPACE_ID, "controller");

        assertTrue(result);
        verify(shareResourceMapper).deleteByPrimaryKey(RESOURCE_ID);
        verify(shareScopeMapper).deleteByResourceId(RESOURCE_ID);
        verify(agentMapper).updateAgentShareStatus(RESOURCE_ID, 0);
        verify(mappingMapper).updateShareRelationValidStatusByShareResourceId(RESOURCE_ID, false);
    }

    @Test
    void testCancelShareResource_WorkflowType() {
        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setResourceType("workflow");
        when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
            .thenReturn(entity);

        Boolean result = shareResourceManagerService.cancelShareResource(PROJECT_ID, RESOURCE_ID, WORKSPACE_ID, "workflow");

        assertTrue(result);
        verify(workflowMapper).updateWorkflowShareStatus(RESOURCE_ID, 0);
    }

    @Test
    void testQueryShareResourceList_EmptyList() {
        QueryShareResourceListQo qo = new QueryShareResourceListQo();
        qo.setWorkspaceId(WORKSPACE_ID);
        qo.setResourceType("controller");
        qo.setOffset(0);
        qo.setLimit(10);

        when(shareResourceMapper.selectSharResourceEntityByWorkspaceId(
            eq(PROJECT_ID), eq(WORKSPACE_ID), eq("controller"), any()))
            .thenReturn(new ArrayList<>());

        ShareResourceListRsp result = shareResourceManagerService.queryShareResourceList(PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(0, result.getCount());
        assertNotNull(result.getResourceList());
        assertTrue(result.getResourceList().isEmpty());
    }

    @Test
    void testQueryShareResourceList_WithControllerResources() {
        QueryShareResourceListQo qo = new QueryShareResourceListQo();
        qo.setWorkspaceId(WORKSPACE_ID);
        qo.setResourceType("controller");
        qo.setOffset(0);
        qo.setLimit(10);

        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setResourceName("TestResource")
            .setResourceType("controller")
            .setWorkspaceId(WORKSPACE_ID)
            .setWorkspaceName("ws-name")
            .setVersionList("[{\"versionId\":\"v1\",\"versionName\":\"1.0\"}]")
            .setCreator("creator1");

        when(shareResourceMapper.selectSharResourceEntityByWorkspaceId(
            eq(PROJECT_ID), eq(WORKSPACE_ID), eq("controller"), any()))
            .thenReturn(List.of(entity));

        Agent agent = new Agent();
        agent.setAgentId(RESOURCE_ID);
        agent.setName("AgentName");
        agent.setDescription("desc");
        agent.setIcon("icon");
        agent.setType("chat");

        when(agentMapper.selectByAgentIds(eq(PROJECT_ID), eq("controller"), anyList()))
            .thenReturn(List.of(agent));

        ShareResourceListRsp result = shareResourceManagerService.queryShareResourceList(PROJECT_ID, qo);

        assertNotNull(result);
        assertNotNull(result.getResourceList());
    }

    @Test
    void testQuerySharedResourceList_EmptyList() {
        QuerySharedResourceListQo qo = new QuerySharedResourceListQo();
        qo.setWorkspaceId(WORKSPACE_ID);
        qo.setResourceType("controller");
        qo.setOffset(0);
        qo.setLimit(10);

        when(shareResourceMapper.selectSharedResourceByAuthWorkspaceIdAndType(
            eq(PROJECT_ID), eq(WORKSPACE_ID), eq("controller"), any()))
            .thenReturn(new ArrayList<>());

        ShareResourceListRsp result = shareResourceManagerService.querySharedResourceList(PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(0, result.getCount());
        assertTrue(result.getResourceList().isEmpty());
    }

    @Test
    void testQuerySharedResourceList_WithResources() {
        QuerySharedResourceListQo qo = new QuerySharedResourceListQo();
        qo.setWorkspaceId(WORKSPACE_ID);
        qo.setResourceType("controller");
        qo.setOffset(0);
        qo.setLimit(10);

        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setResourceType("controller")
            .setWorkspaceId("ws-other")
            .setWorkspaceName("other-ws")
            .setVersionList("[{\"versionId\":\"v1\",\"versionName\":\"1.0\"}]")
            .setCreator("creator1");

        when(shareResourceMapper.selectSharedResourceByAuthWorkspaceIdAndType(
            eq(PROJECT_ID), eq(WORKSPACE_ID), eq("controller"), any()))
            .thenReturn(List.of(entity));

        Agent agent = new Agent();
        agent.setAgentId(RESOURCE_ID);
        agent.setName("AgentName");
        agent.setDescription("desc");
        agent.setIcon("icon");
        agent.setType("chat");

        when(agentMapper.selectByAgentIds(eq(PROJECT_ID), eq("controller"), anyList()))
            .thenReturn(List.of(agent));

        ShareResourceListRsp result = shareResourceManagerService.querySharedResourceList(PROJECT_ID, qo);

        assertNotNull(result);
        assertNotNull(result.getResourceList());
    }

    @Test
    void testCheckWorkspaceAuthByResourceOrNot_ResourceNotFound() {
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(null);

        boolean result = shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(WORKSPACE_ID, RESOURCE_ID);

        assertFalse(result);
    }

    @Test
    void testCheckWorkspaceAuthByResourceOrNot_AllWorkspaceAuth() {
        ShareResourceEntity entity = new ShareResourceEntity().setResourceId(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(entity);

        ShareScopeEntity scopeEntity = new ShareScopeEntity().setWorkspaceId("all");
        when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID))
            .thenReturn(List.of(scopeEntity));

        boolean result = shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(WORKSPACE_ID, RESOURCE_ID);

        assertTrue(result);
    }

    @Test
    void testCheckWorkspaceAuthByResourceOrNot_SpecificWorkspaceAuth() {
        ShareResourceEntity entity = new ShareResourceEntity().setResourceId(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(entity);

        ShareScopeEntity scopeEntity = new ShareScopeEntity().setWorkspaceId(WORKSPACE_ID);
        when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID))
            .thenReturn(List.of(scopeEntity));

        boolean result = shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(WORKSPACE_ID, RESOURCE_ID);

        assertTrue(result);
    }

    @Test
    void testCheckWorkspaceAuthByResourceOrNot_WorkspaceNotAuthorized() {
        ShareResourceEntity entity = new ShareResourceEntity().setResourceId(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(entity);

        ShareScopeEntity scopeEntity = new ShareScopeEntity().setWorkspaceId("other-workspace");
        when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID))
            .thenReturn(List.of(scopeEntity));

        boolean result = shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(WORKSPACE_ID, RESOURCE_ID);

        assertFalse(result);
    }

    @Test
    void testCheckResourceSharedOrNot_Shared() {
        when(shareResourceMapper.countResourceByResourceId(PROJECT_ID, RESOURCE_ID)).thenReturn(1);

        assertThrows(AgentStudioException.class, () ->
            shareResourceManagerService.checkResourceSharedOrNot(PROJECT_ID, RESOURCE_ID));
    }

    @Test
    void testCheckResourceSharedOrNot_NotShared() {
        when(shareResourceMapper.countResourceByResourceId(PROJECT_ID, RESOURCE_ID)).thenReturn(0);

        shareResourceManagerService.checkResourceSharedOrNot(PROJECT_ID, RESOURCE_ID);

        verify(shareResourceMapper).countResourceByResourceId(PROJECT_ID, RESOURCE_ID);
    }

    @Test
    void testIsListIncluded_BothNull() {
        boolean result = shareResourceManagerService.isListIncluded(null, null);
        assertFalse(result);
    }

    @Test
    void testIsListIncluded_SourceEmpty() {
        boolean result = shareResourceManagerService.isListIncluded(new ArrayList<>(), List.of("a"));
        assertFalse(result);
    }

    @Test
    void testIsListIncluded_TargetEmpty() {
        boolean result = shareResourceManagerService.isListIncluded(List.of("a"), new ArrayList<>());
        assertFalse(result);
    }

    @Test
    void testIsListIncluded_AllIncluded() {
        boolean result = shareResourceManagerService.isListIncluded(List.of("a", "b"), List.of("a", "b", "c"));
        assertTrue(result);
    }

    @Test
    void testIsListIncluded_NotAllIncluded() {
        boolean result = shareResourceManagerService.isListIncluded(List.of("a", "d"), List.of("a", "b", "c"));
        assertFalse(result);
    }

    @Test
    void testIsListIncluded_ExactMatch() {
        boolean result = shareResourceManagerService.isListIncluded(List.of("a", "b"), List.of("a", "b"));
        assertTrue(result);
    }

    @Test
    void testQueryShareResourceEntityByResourceIdAndVersionId_BlankVersionId() {
        ShareResourceEntity result = shareResourceManagerService
            .queryShareResourceEntityByResourceIdAndVersionId(RESOURCE_ID, WORKSPACE_ID, "");

        assertNull(result);
    }

    @Test
    void testQueryShareResourceEntityByResourceIdAndVersionId_NullVersionId() {
        ShareResourceEntity result = shareResourceManagerService
            .queryShareResourceEntityByResourceIdAndVersionId(RESOURCE_ID, WORKSPACE_ID, null);

        assertNull(result);
    }

    @Test
    void testQueryShareResourceEntityByResourceIdAndVersionId_NoScope() {
        when(shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(RESOURCE_ID, WORKSPACE_ID))
            .thenReturn(null);

        ShareResourceEntity result = shareResourceManagerService
            .queryShareResourceEntityByResourceIdAndVersionId(RESOURCE_ID, WORKSPACE_ID, "v1");

        assertNull(result);
    }

    @Test
    void testQueryShareResourceEntityByResourceIdAndVersionId_VersionNotMatch() {
        ShareScopeEntity scopeEntity = new ShareScopeEntity().setWorkspaceId(WORKSPACE_ID);
        when(shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(RESOURCE_ID, WORKSPACE_ID))
            .thenReturn(scopeEntity);

        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setVersionList("[{\"versionId\":\"v2\",\"versionName\":\"2.0\"}]");
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(entity);

        ShareResourceEntity result = shareResourceManagerService
            .queryShareResourceEntityByResourceIdAndVersionId(RESOURCE_ID, WORKSPACE_ID, "v1");

        assertNull(result);
    }

    @Test
    void testQueryShareResourceEntityByResourceIdAndVersionId_Success() {
        ShareScopeEntity scopeEntity = new ShareScopeEntity().setWorkspaceId(WORKSPACE_ID);
        when(shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(RESOURCE_ID, WORKSPACE_ID))
            .thenReturn(scopeEntity);

        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setVersionList("[{\"versionId\":\"v1\",\"versionName\":\"1.0\"}]");
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(entity);

        ShareResourceEntity result = shareResourceManagerService
            .queryShareResourceEntityByResourceIdAndVersionId(RESOURCE_ID, WORKSPACE_ID, "v1");

        assertNotNull(result);
        assertEquals(RESOURCE_ID, result.getResourceId());
    }

    @Test
    void testExportShareInfo_ResourceNotFound() {
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(null);

        ShareInfo result = shareResourceManagerService.exportShareInfo(RESOURCE_ID);

        assertNull(result);
    }

    @Test
    void testExportShareInfo_Success() {
        ShareResourceEntity entity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setResourceName("TestResource")
            .setResourceType("controller")
            .setWorkspaceId(WORKSPACE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID))
            .thenReturn(entity);

        ShareScopeEntity scopeEntity = new ShareScopeEntity()
            .setResourceId(RESOURCE_ID)
            .setWorkspaceId("ws-2");
        when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID))
            .thenReturn(List.of(scopeEntity));

        ShareInfo result = shareResourceManagerService.exportShareInfo(RESOURCE_ID);

        assertNotNull(result);
        assertEquals(RESOURCE_ID, result.getResourceId());
        assertNotNull(result.getShareScopeEntityList());
        assertEquals(1, result.getShareScopeEntityList().size());
    }

    @Test
    void testImportShareInfo_NullShareInfo() {
        shareResourceManagerService.importShareInfo(PROJECT_ID, null, new WfImportDataWrapper());

        verify(shareResourceMapper, never()).insert(any());
    }

    @Test
    void testImportShareInfo_WorkspaceNotFound() {
        ShareInfo shareInfo = new ShareInfo();
        shareInfo.setWorkspaceId("ws-nonexist");
        shareInfo.setResourceId(RESOURCE_ID);

        when(workspaceMapper.selectById(PROJECT_ID, "ws-nonexist")).thenReturn(null);

        shareResourceManagerService.importShareInfo(PROJECT_ID, shareInfo, new WfImportDataWrapper());

        verify(shareResourceMapper, never()).insert(any());
    }

    @Test
    void testImportShareInfo_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            reqCtx.when(RequestContextUtils::getRequestWorkspaceName).thenReturn("ws-name");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-id-1");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ShareInfo shareInfo = new ShareInfo();
            shareInfo.setWorkspaceId("ws-source");
            shareInfo.setResourceId(RESOURCE_ID);
            shareInfo.setResourceName("TestResource");
            shareInfo.setResourceType("controller");

            WorkspaceInfo workspaceInfo = new WorkspaceInfo();
            when(workspaceMapper.selectById(PROJECT_ID, "ws-source")).thenReturn(workspaceInfo);

            WfImportDataWrapper wrapper = new WfImportDataWrapper();

            when(shareResourceMapper.selectShareResourceEntityById(eq(PROJECT_ID), eq(WORKSPACE_ID), eq(RESOURCE_ID)))
                .thenReturn(null);

            shareResourceManagerService.importShareInfo(PROJECT_ID, shareInfo, wrapper);

            verify(shareResourceMapper).insert(any(ShareResourceEntity.class));
        }
    }

    @Test
    void testImportShareResourceInfo_ExistingEntity_Update() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);

            ShareResourceEntity existingEntity = new ShareResourceEntity()
                .setResourceId(RESOURCE_ID)
                .setResourceName("OldName");
            when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(existingEntity);

            ShareInfo shareInfo = new ShareInfo();
            shareInfo.setResourceName("NewName");
            shareInfo.setVersionList("[{\"versionId\":\"v1\"}]");

            shareResourceManagerService.importShareResourceInfo(PROJECT_ID, RESOURCE_ID, shareInfo);

            verify(shareResourceMapper).updateShareResourceEntity(any(ShareResourceEntity.class));
            verify(shareResourceMapper, never()).insert(any());
        }
    }

    @Test
    void testImportShareResourceInfo_NewEntity_Insert() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            reqCtx.when(RequestContextUtils::getRequestWorkspaceName).thenReturn("ws-name");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-id-1");

            when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(null);

            ShareInfo shareInfo = new ShareInfo();
            shareInfo.setResourceName("NewResource");
            shareInfo.setResourceType("controller");

            shareResourceManagerService.importShareResourceInfo(PROJECT_ID, RESOURCE_ID, shareInfo);

            verify(shareResourceMapper).insert(any(ShareResourceEntity.class));
        }
    }

    @Test
    void testImportShareResourceScope_EmptyList() {
        shareResourceManagerService.importShareResourceScope(PROJECT_ID, RESOURCE_ID, null);

        verify(shareScopeMapper, never()).insert(any());
    }

    @Test
    void testImportShareResourceScope_EmptyCollection() {
        shareResourceManagerService.importShareResourceScope(PROJECT_ID, RESOURCE_ID, new ArrayList<>());

        verify(shareScopeMapper, never()).insert(any());
    }

    @Test
    void testImportShareResourceScope_AllWorkspace() {
        ShareScopeEntity allScope = new ShareScopeEntity().setWorkspaceId("all");

        shareResourceManagerService.importShareResourceScope(PROJECT_ID, RESOURCE_ID, List.of(allScope));

        verify(shareScopeMapper).deleteByResourceId(RESOURCE_ID);
        verify(shareScopeMapper).insert(any(ShareScopeEntity.class));
    }

    @Test
    void testImportShareResourceScope_SpecificWorkspaces() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ShareScopeEntity scope1 = new ShareScopeEntity().setWorkspaceId("ws-2");
            ShareScopeEntity scope2 = new ShareScopeEntity().setWorkspaceId(WORKSPACE_ID);

            WorkspaceEntity wsEntity = new WorkspaceEntity();
            wsEntity.setId("ws-2");
            when(workspaceMapper.selectWorkspaceListByDomainId(PROJECT_ID, "domain-1"))
                .thenReturn(List.of(wsEntity));

            when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID))
                .thenReturn(new ArrayList<>());

            shareResourceManagerService.importShareResourceScope(PROJECT_ID, RESOURCE_ID, List.of(scope1, scope2));

            verify(shareScopeMapper).insert(any(ShareScopeEntity.class));
        }
    }

    @Test
    void testValidateShareReferences_EmptyList() {
        shareResourceManagerService.validateShareReferences(null, WORKSPACE_ID);

        verify(shareResourceMapper, never()).selectShareResourceEntityByResourceId(anyString());
    }

    @Test
    void testValidateShareReferences_EmptyCollection() {
        shareResourceManagerService.validateShareReferences(new ArrayList<>(), WORKSPACE_ID);

        verify(shareResourceMapper, never()).selectShareResourceEntityByResourceId(anyString());
    }

    @Test
    void testValidateShareReferences_ShareResourceNotFound() {
        MappingEntity mapping = new MappingEntity();
        mapping.setResourceId(RESOURCE_ID);

        when(pluginAdapter.getPluginId(RESOURCE_ID)).thenReturn(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            shareResourceManagerService.validateShareReferences(List.of(mapping), WORKSPACE_ID));
    }

    @Test
    void testValidateShareReferences_ScopeEmpty() {
        MappingEntity mapping = new MappingEntity();
        mapping.setResourceId(RESOURCE_ID);

        ShareResourceEntity shareEntity = new ShareResourceEntity()
            .setResourceId(RESOURCE_ID)
            .setWorkspaceId("ws-owner");

        when(pluginAdapter.getPluginId(RESOURCE_ID)).thenReturn(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(shareEntity);
        when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID)).thenReturn(new ArrayList<>());

        assertThrows(AgentStudioException.class, () ->
            shareResourceManagerService.validateShareReferences(List.of(mapping), WORKSPACE_ID));
    }

    @Test
    void testValidateShareReferences_AllWorkspaceScope() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            MappingEntity mapping = new MappingEntity();
            mapping.setResourceId(RESOURCE_ID);

            ShareResourceEntity shareEntity = new ShareResourceEntity()
                .setResourceId(RESOURCE_ID)
                .setWorkspaceId("ws-owner");

            ShareScopeEntity allScope = new ShareScopeEntity().setWorkspaceId("all");

            when(pluginAdapter.getPluginId(RESOURCE_ID)).thenReturn(RESOURCE_ID);
            when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(shareEntity);
            when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID)).thenReturn(List.of(allScope));

            shareResourceManagerService.validateShareReferences(List.of(mapping), WORKSPACE_ID);

            verify(pluginAdapter, times(2)).getPluginId(RESOURCE_ID);
        }
    }

    @Test
    void testValidateShareReferences_WorkspaceInScope() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("other-ws");

            MappingEntity mapping = new MappingEntity();
            mapping.setResourceId(RESOURCE_ID);

            ShareResourceEntity shareEntity = new ShareResourceEntity()
                .setResourceId(RESOURCE_ID)
                .setWorkspaceId("ws-owner");

            ShareScopeEntity scope = new ShareScopeEntity().setWorkspaceId(WORKSPACE_ID);

            when(pluginAdapter.getPluginId(RESOURCE_ID)).thenReturn(RESOURCE_ID);
            when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(shareEntity);
            when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID)).thenReturn(List.of(scope));

            shareResourceManagerService.validateShareReferences(List.of(mapping), WORKSPACE_ID);
        }
    }

    @Test
    void testValidateShareReferences_WorkspaceNotInScope() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("other-ws");

            MappingEntity mapping = new MappingEntity();
            mapping.setResourceId(RESOURCE_ID);

            ShareResourceEntity shareEntity = new ShareResourceEntity()
                .setResourceId(RESOURCE_ID)
                .setWorkspaceId("ws-owner");

            ShareScopeEntity scope = new ShareScopeEntity().setWorkspaceId("some-other-ws");

            when(pluginAdapter.getPluginId(RESOURCE_ID)).thenReturn(RESOURCE_ID);
            when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(shareEntity);
            when(shareScopeMapper.selectShareScopesByResourceId(RESOURCE_ID)).thenReturn(List.of(scope));

            assertThrows(AgentStudioException.class, () ->
                shareResourceManagerService.validateShareReferences(List.of(mapping), WORKSPACE_ID));
        }
    }

    @Test
    void testQueryShareResourceEntityByResourceIdList() {
        List<String> ids = List.of("id1", "id2");
        ShareResourceEntity e1 = new ShareResourceEntity().setResourceId("id1");
        ShareResourceEntity e2 = new ShareResourceEntity().setResourceId("id2");

        when(shareResourceMapper.selectShareResourceByResourceIds(ids)).thenReturn(List.of(e1, e2));

        List<ShareResourceEntity> result = shareResourceManagerService.queryShareResourceEntityByResourceIdList(ids);

        assertEquals(2, result.size());
    }

    @Test
    void testQueryShareResourceEntityByResourceId() {
        ShareResourceEntity entity = new ShareResourceEntity().setResourceId(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(entity);

        ShareResourceEntity result = shareResourceManagerService.queryShareResourceEntityByResourceId(RESOURCE_ID);

        assertNotNull(result);
        assertEquals(RESOURCE_ID, result.getResourceId());
    }

    @Test
    void testQueryShareResourceEntityByResourceIdAndWorkspaceId() {
        ShareResourceEntity entity = new ShareResourceEntity().setResourceId(RESOURCE_ID);
        when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
            .thenReturn(entity);

        ShareResourceEntity result = shareResourceManagerService
            .queryShareResourceEntityByResourceIdAndWorkspaceId(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID);

        assertNotNull(result);
        assertEquals(RESOURCE_ID, result.getResourceId());
    }

    @Test
    void testCreateOrUpdateShareResource_ControllerNew() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceName).thenReturn("ws-name");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("userName");
            reqCtx.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);

            ShareResourceRequestInfo body = new ShareResourceRequestInfo();
            body.setResourceId(RESOURCE_ID);
            body.setResourceName("TestAgent");
            body.setResourceType(ShareResourceRequestInfo.ResourceTypeEnum.CONTROLLER);
            body.setVersionList(List.of("v1"));
            body.setAuthWorkspaceIdList(List.of("all"));

            when(mappingMapper.selectByAppIdAndAppVersion(eq(RESOURCE_ID), any(), any(), any()))
                .thenReturn(new ArrayList<>());

            Agent agent = new Agent();
            agent.setAgentId(RESOURCE_ID);
            agent.setTraceId("trace-1");
            when(agentMapper.selectByProjectIdAndWorkspaceId(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(agent);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setVersionId("v1");
            releaseVersion.setVersionName("1.0");
            when(releaseVersionMapper.selectByAppId(RESOURCE_ID))
                .thenReturn(List.of(releaseVersion));

            when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(null);

            Boolean result = shareResourceManagerService.createOrUpdateShareResource(PROJECT_ID, WORKSPACE_ID, body);

            assertTrue(result);
            verify(shareResourceMapper).insert(any(ShareResourceEntity.class));
            verify(agentMapper).updateAgentShareStatus(RESOURCE_ID, 1);
        }
    }

    @Test
    void testCreateOrUpdateShareResource_ControllerExisting() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceName).thenReturn("ws-name");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("userName");
            reqCtx.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);

            ShareResourceRequestInfo body = new ShareResourceRequestInfo();
            body.setResourceId(RESOURCE_ID);
            body.setResourceName("TestAgent");
            body.setResourceType(ShareResourceRequestInfo.ResourceTypeEnum.CONTROLLER);
            body.setVersionList(List.of("v1"));
            body.setAuthWorkspaceIdList(List.of("all"));

            when(mappingMapper.selectByAppIdAndAppVersion(eq(RESOURCE_ID), any(), any(), any()))
                .thenReturn(new ArrayList<>());

            Agent agent = new Agent();
            agent.setAgentId(RESOURCE_ID);
            agent.setTraceId("trace-1");
            when(agentMapper.selectByProjectIdAndWorkspaceId(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(agent);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setVersionId("v1");
            releaseVersion.setVersionName("1.0");
            when(releaseVersionMapper.selectByAppId(RESOURCE_ID))
                .thenReturn(List.of(releaseVersion));

            ShareResourceEntity existingEntity = new ShareResourceEntity().setResourceId(RESOURCE_ID);
            when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(existingEntity);

            Boolean result = shareResourceManagerService.createOrUpdateShareResource(PROJECT_ID, WORKSPACE_ID, body);

            assertTrue(result);
            verify(shareResourceMapper).updateShareResourceEntity(any(ShareResourceEntity.class));
        }
    }

    @Test
    void testCreateOrUpdateShareResource_AgentNotExist() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ShareResourceRequestInfo body = new ShareResourceRequestInfo();
            body.setResourceId(RESOURCE_ID);
            body.setResourceName("TestAgent");
            body.setResourceType(ShareResourceRequestInfo.ResourceTypeEnum.CONTROLLER);
            body.setVersionList(List.of("v1"));
            body.setAuthWorkspaceIdList(List.of("all"));

            when(mappingMapper.selectByAppIdAndAppVersion(eq(RESOURCE_ID), any(), any(), any()))
                .thenReturn(new ArrayList<>());

            when(agentMapper.selectByProjectIdAndWorkspaceId(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(null);

            assertThrows(AgentStudioException.class, () ->
                shareResourceManagerService.createOrUpdateShareResource(PROJECT_ID, WORKSPACE_ID, body));
        }
    }

    @Test
    void testCreateOrUpdateShareResource_ShareReferenceExists() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            ShareResourceRequestInfo body = new ShareResourceRequestInfo();
            body.setResourceId(RESOURCE_ID);
            body.setResourceName("TestAgent");
            body.setResourceType(ShareResourceRequestInfo.ResourceTypeEnum.CONTROLLER);
            body.setVersionList(List.of("v1"));
            body.setAuthWorkspaceIdList(List.of("all"));

            MappingEntity shareMapping = new MappingEntity();
            shareMapping.setAppVersion("v1");
            shareMapping.setReferenceType(ReferenceTypeEnum.SHARE.getValue());

            when(mappingMapper.selectByAppIdAndAppVersion(eq(RESOURCE_ID), any(), any(), any()))
                .thenReturn(List.of(shareMapping));

            assertThrows(AgentStudioException.class, () ->
                shareResourceManagerService.createOrUpdateShareResource(PROJECT_ID, WORKSPACE_ID, body));
        }
    }

    @Test
    void testCreateOrUpdateShareResource_WorkflowType() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestWorkspaceName).thenReturn("ws-name");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("userName");
            reqCtx.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);

            ShareResourceRequestInfo body = new ShareResourceRequestInfo();
            body.setResourceId(RESOURCE_ID);
            body.setResourceName("TestWorkflow");
            body.setResourceType(ShareResourceRequestInfo.ResourceTypeEnum.WORKFLOW);
            body.setVersionList(List.of("v1"));
            body.setAuthWorkspaceIdList(List.of("all"));

            when(mappingMapper.selectByAppIdAndAppVersion(eq(RESOURCE_ID), any(), any(), any()))
                .thenReturn(new ArrayList<>());

            WorkflowEntity workflowEntity = new WorkflowEntity();
            workflowEntity.setId(RESOURCE_ID);
            workflowEntity.setTraceId("trace-wf");
            when(workflowMapper.getWorkflowEntityByWorkspaceId(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(workflowEntity);

            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setVersionId("v1");
            releaseVersion.setVersionName("1.0");
            when(releaseVersionMapper.selectByAppId(RESOURCE_ID))
                .thenReturn(List.of(releaseVersion));

            when(shareResourceMapper.selectShareResourceEntityById(PROJECT_ID, WORKSPACE_ID, RESOURCE_ID))
                .thenReturn(null);

            Boolean result = shareResourceManagerService.createOrUpdateShareResource(PROJECT_ID, WORKSPACE_ID, body);

            assertTrue(result);
            verify(workflowMapper).updateWorkflowShareStatus(RESOURCE_ID, 1);
        }
    }

    // ==================== checkVersionSharedOrNot ====================

    @Test
    void testCheckVersionSharedOrNot_nullOrBlankArgs_noop() {
        // 空参数不应查库、不应抛异常
        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(null, "v1"));
        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot("", "v1"));
        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, null));
        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, "  "));
        verify(shareResourceMapper, never()).selectShareResourceEntityByResourceId(anyString());
    }

    @Test
    void testCheckVersionSharedOrNot_noShareRecord_noop() {
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(null);

        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, "v1"));
    }

    @Test
    void testCheckVersionSharedOrNot_shareRecordVersionListEmpty_noop() {
        ShareResourceEntity share = new ShareResourceEntity();
        share.setVersionList(null);
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(share);

        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, "v1"));

        share.setVersionList("");
        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, "v1"));
    }

    @Test
    void testCheckVersionSharedOrNot_versionNotInList_noop() {
        ShareResourceEntity share = new ShareResourceEntity();
        share.setVersionList("[{\"version_id\":\"v0\",\"version_name\":\"0.9\"}]");
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(share);

        // v1 不在已共享版本列表中，应放行
        assertDoesNotThrow(() -> shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, "v1"));
    }

    @Test
    void testCheckVersionSharedOrNot_versionIsShared_throwsCannotDelete() {
        // versionList 序列化中以字串包含目标 versionId 时（与 AgentManagementService/PluginService 校验语义一致）应抛错
        ShareResourceEntity share = new ShareResourceEntity();
        share.setVersionList("[{\"version_id\":\"v1\",\"version_name\":\"1.0\"},{\"version_id\":\"v2\",\"version_name\":\"2.0\"}]");
        when(shareResourceMapper.selectShareResourceEntityByResourceId(RESOURCE_ID)).thenReturn(share);

        AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
            shareResourceManagerService.checkVersionSharedOrNot(RESOURCE_ID, "v1"));
        assertEquals(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY, ex.getErrorCode());
    }
}
