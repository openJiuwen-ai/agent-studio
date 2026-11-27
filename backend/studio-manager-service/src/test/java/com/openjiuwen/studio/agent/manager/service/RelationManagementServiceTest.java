/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.HistoryWorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.mcp.auth.IMcpBase;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourceRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourcesRelationsQo;

import java.util.Collections;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class RelationManagementServiceTest {

    private ReleaseVersionMapper releaseVersionMapper;
    private AgentMapper agentMapper;
    private MappingMapper mappingMapper;
    private WorkflowMapper workflowMapper;
    private HistoryWorkflowMapper historyWorkflowMapper;
    private PluginMapper pluginMapper;
    private ToolMapper toolMapper;
    private WorkspaceMapper workspaceMapper;
    private MemoryRepoMapper memoryRepoMapper;
    private IPlugin pluginService;
    private ModelServiceManager modelServiceManager;
    private ShareResourceManagerService shareResourceManagerService;
    private MgObsService mgObsService;
    private IPluginBase pluginBase;
    private ResourceService resourceService;
    private ShareInnerService shareInnerService;
    private IMcpBase mcpBase;
    private SkillMapper skillMapper;
    private KnowledgeBaseServiceImpl knowledgeBaseService;
    private McpServiceDao serviceDao;
    private ShareScopeMapper shareScopeMapper;

    private RelationManagementService relationManagementService;

    @BeforeEach
    void setUp() {
        releaseVersionMapper = mock(ReleaseVersionMapper.class);
        agentMapper = mock(AgentMapper.class);
        mappingMapper = mock(MappingMapper.class);
        workflowMapper = mock(WorkflowMapper.class);
        historyWorkflowMapper = mock(HistoryWorkflowMapper.class);
        pluginMapper = mock(PluginMapper.class);
        toolMapper = mock(ToolMapper.class);
        workspaceMapper = mock(WorkspaceMapper.class);
        memoryRepoMapper = mock(MemoryRepoMapper.class);
        pluginService = mock(IPlugin.class);
        modelServiceManager = mock(ModelServiceManager.class);
        shareResourceManagerService = mock(ShareResourceManagerService.class);
        mgObsService = mock(MgObsService.class);
        pluginBase = mock(IPluginBase.class);
        resourceService = mock(ResourceService.class);
        shareInnerService = mock(ShareInnerService.class);
        mcpBase = mock(IMcpBase.class);
        skillMapper = mock(SkillMapper.class);
        knowledgeBaseService = mock(KnowledgeBaseServiceImpl.class);
        serviceDao = mock(McpServiceDao.class);
        shareScopeMapper = mock(ShareScopeMapper.class);

        MockitoAnnotations.openMocks(this);
        relationManagementService = new RelationManagementService();
        ReflectionTestUtils.setField(relationManagementService, "releaseVersionMapper", releaseVersionMapper);
        ReflectionTestUtils.setField(relationManagementService, "agentMapper", agentMapper);
        ReflectionTestUtils.setField(relationManagementService, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(relationManagementService, "workflowMapper", workflowMapper);
        ReflectionTestUtils.setField(relationManagementService, "historyWorkflowMapper", historyWorkflowMapper);
        ReflectionTestUtils.setField(relationManagementService, "pluginMapper", pluginMapper);
        ReflectionTestUtils.setField(relationManagementService, "toolMapper", toolMapper);
        ReflectionTestUtils.setField(relationManagementService, "workspaceMapper", workspaceMapper);
        ReflectionTestUtils.setField(relationManagementService, "memoryRepoMapper", memoryRepoMapper);
        ReflectionTestUtils.setField(relationManagementService, "pluginService", pluginService);
        ReflectionTestUtils.setField(relationManagementService, "modelServiceManager", modelServiceManager);
        ReflectionTestUtils.setField(relationManagementService, "shareResourceManagerService", shareResourceManagerService);
        ReflectionTestUtils.setField(relationManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(relationManagementService, "pluginBase", pluginBase);
        ReflectionTestUtils.setField(relationManagementService, "resourceService", resourceService);
        ReflectionTestUtils.setField(relationManagementService, "shareInnerService", shareInnerService);
        ReflectionTestUtils.setField(relationManagementService, "mcpBase", mcpBase);
        ReflectionTestUtils.setField(relationManagementService, "skillMapper", skillMapper);
        ReflectionTestUtils.setField(relationManagementService, "knowledgeBaseService", knowledgeBaseService);
        ReflectionTestUtils.setField(relationManagementService, "serviceDao", serviceDao);
        ReflectionTestUtils.setField(relationManagementService, "shareScopeMapper", shareScopeMapper);
        ReflectionTestUtils.setField(relationManagementService, "toolBoundLimit", 20);
        ReflectionTestUtils.setField(relationManagementService, "knowledgeRepoBoundLimit", 3);
        ReflectionTestUtils.setField(relationManagementService, "workflowBoundLimit", 5);
        ReflectionTestUtils.setField(relationManagementService, "controllerWorkflowLimit", 5);
        ReflectionTestUtils.setField(relationManagementService, "controllerSubAgentLimit", 3);
        ReflectionTestUtils.setField(relationManagementService, "mcpBoundLimit", 5);
        ReflectionTestUtils.setField(relationManagementService, "defaultMcpIcon", "default-mcp-icon");
    }

    @Test
    void testDeleteAgentResourceMapping_Success() {
        assertDoesNotThrow(() ->
            relationManagementService.deleteAgentResourceMapping("agent-1", List.of("0.0.1")));
    }

    @Test
    void testListResourcesRelations_EmptyResult() {
        ListResourcesRelationsQo qo = new ListResourcesRelationsQo();
        qo.setResourceIds(List.of("resource-1"));
        qo.setResourceType("tool");
        qo.setWorkspaceId("w1");
        qo.setOffset(0);
        qo.setLimit(10);

        when(mappingMapper.getByIds(anyList())).thenReturn(Collections.emptyList());

        var result = relationManagementService.listResourcesRelations("p1", qo);

        assertNotNull(result);
    }

    @Test
    void testListAppRelations_EmptyResult() {
        ListAppRelationsQo qo = new ListAppRelationsQo();
        qo.setWorkspaceId("w1");
        qo.setResourceType("tool");

        var result = relationManagementService.listAppRelations("p1", "app-1", qo);

        assertNotNull(result);
    }

    @Test
    void testListResourceRelations_EmptyResult() {
        ListResourceRelationsQo qo = new ListResourceRelationsQo();
        qo.setWorkspaceId("w1");
        qo.setResourceType("tool");
        qo.setOffset(0);
        qo.setLimit(10);

        when(mappingMapper.selectByResourceIdAndVersionId(anyString(), any(), any(), any(), any()))
            .thenReturn(Collections.emptyList());

        var result = relationManagementService.listResourceRelations("p1", "resource-1", qo);

        assertNotNull(result);
    }

    /** mock工作流DSL：包含带一个输入参数的node_start节点，满足parseWorkflowInput2ResourceParameter解析 */
    private void mockWorkflowDsl() {
        String dsl = "{\"nodes\":[{\"id\":\"node_start\",\"type\":\"Start\",\"outputs\":"
            + "[{\"name\":\"query\",\"type\":\"string\",\"description\":\"用户输入\",\"required\":true,"
            + "\"value\":{\"default\":\"\",\"type\":\"literal\"}}]}]}";
        when(mgObsService.downloadObsFile(anyString())).thenReturn(dsl);
    }

    @Test
    void testCreateAgentWorkflow_DanglingReferencedVersion_FallbackToLatest() {
        // 原引用的工作流版本已被删除（存量脏数据）：应回退跟随last_version_id，而不是沿用悬空版本号
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            Agent agent = new Agent();
            agent.setAgentId("agent-1");
            agent.setName("test-agent");
            agent.setType("agent");
            when(agentMapper.selectByProjectIdAndWorkspaceId(anyString(), anyString(), anyString())).thenReturn(agent);

            WorkflowEntity workflow = new WorkflowEntity();
            workflow.setId("wf-1");
            workflow.setName("wf");
            workflow.setWorkspaceId("w1");
            workflow.setDslPath("workflow/flow/wf-1/wf-1.json");
            workflow.setLastVersionId("v2");
            when(workflowMapper.selectByWorkflowIds(anyString(), anyString(), anyList()))
                .thenReturn(List.of(workflow));

            // 原引用版本v1已被删除（查询返回null），现存最新版本v2
            when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(null);
            mockWorkflowDsl();

            MappingEntity reference = new MappingEntity();
            reference.setResourceId("wf-1");
            reference.setResourceVersion("v1");
            reference.setResourceName("wf");

            relationManagementService.createAgentWorkflow("p1", "w1", "agent-1", null, List.of(reference));

            ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
            verify(mappingMapper).insertBatch(captor.capture());
            MappingEntity inserted = captor.getValue().get(0);
            // 悬空版本v1应被替换为last_version_id（v2），且下载DSL使用v2
            assertEquals("v2", inserted.getResourceVersion());
            verify(mgObsService).downloadObsFile("workflow/flow/wf-1/wf-1_v2.json");
        }
    }

    @Test
    void testCreateAgentWorkflow_ExistingReferencedVersion_Kept() {
        // 原引用的工作流版本仍存在：保持版本固定语义，不回退
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            Agent agent = new Agent();
            agent.setAgentId("agent-1");
            agent.setName("test-agent");
            agent.setType("agent");
            when(agentMapper.selectByProjectIdAndWorkspaceId(anyString(), anyString(), anyString())).thenReturn(agent);

            WorkflowEntity workflow = new WorkflowEntity();
            workflow.setId("wf-1");
            workflow.setName("wf");
            workflow.setWorkspaceId("w1");
            workflow.setDslPath("workflow/flow/wf-1/wf-1.json");
            workflow.setLastVersionId("v2");
            when(workflowMapper.selectByWorkflowIds(anyString(), anyString(), anyList()))
                .thenReturn(List.of(workflow));

            // 原引用版本v1仍然存在
            ReleaseVersion existing = new ReleaseVersion();
            existing.setAppId("wf-1");
            existing.setVersionId("v1");
            when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(existing);
            mockWorkflowDsl();

            MappingEntity reference = new MappingEntity();
            reference.setResourceId("wf-1");
            reference.setResourceVersion("v1");
            reference.setResourceName("wf");

            relationManagementService.createAgentWorkflow("p1", "w1", "agent-1", null, List.of(reference));

            ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
            verify(mappingMapper).insertBatch(captor.capture());
            MappingEntity inserted = captor.getValue().get(0);
            // 版本存在时沿用原版本号v1，不受last_version_id影响
            assertEquals("v1", inserted.getResourceVersion());
            verify(mgObsService).downloadObsFile("workflow/flow/wf-1/wf-1_v1.json");
        }
    }

    @Test
    void testHandleAgentWorkflow_DanglingBoundVersion_HealedToLatestVersion() {
        // 已绑定工作流的版本号悬空（版本已被删除）：保存时自愈回退到最新现存版本v2（保持锁定具体版本语义），
        // modify路径正常执行。workspaceId传null（共享工作流跳过空间过滤），stub需用nullable匹配
        // DB中已绑定的草稿引用，resource_version指向已删版本v1
        MappingEntity bound = new MappingEntity();
        bound.setAppId("agent-1");
        bound.setResourceId("wf-1");
        bound.setResourceVersion("v1");
        bound.setResourceType("workflow");
        bound.setValid(true);
        when(mappingMapper.selectByAppIdAndResourceType("agent-1", "workflow")).thenReturn(List.of(bound));
        // v1已被删除
        when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(null);
        // wf-1最新现存版本为v2
        WorkflowEntity workflow = new WorkflowEntity();
        workflow.setId("wf-1");
        workflow.setLastVersionId("v2");
        when(workflowMapper.selectByWorkflowIds(anyString(), nullable(String.class), anyList()))
            .thenReturn(List.of(workflow));

        // 前端保存时传回原绑定（版本未变更）
        MappingEntity incoming = new MappingEntity();
        incoming.setResourceId("wf-1");
        incoming.setResourceVersion("v1");
        incoming.setResourceType("workflow");

        relationManagementService.handleAgentWorkflow("p1", "w1", "agent-1", List.of(incoming));

        // 悬空引用被CAS回退到最新现存版本v2（保持锁定具体版本语义）
        verify(mappingMapper).updateResourceVersionIfMatch("wf-1", "v1", "v2");
        // 已绑定记录落入modify路径，且入参中的悬空版本号被同步规整为v2，
        // 避免updateResourceParameterByAppIDAndResourceId无条件回写resource_version时把脏值写回
        ArgumentCaptor<MappingEntity> modifyCaptor = ArgumentCaptor.forClass(MappingEntity.class);
        verify(mappingMapper).updateResourceParameterByAppIDAndResourceId(modifyCaptor.capture());
        assertEquals("v2", modifyCaptor.getValue().getResourceVersion());
    }

    @Test
    void testHandleAgentWorkflow_DanglingBoundVersion_NoRemainingVersion_HealedToNull() {
        // 悬空版本且工作流已无任何版本（版本全删）：无版本可回退，自愈为null（跟随最新）
        MappingEntity bound = new MappingEntity();
        bound.setAppId("agent-1");
        bound.setResourceId("wf-1");
        bound.setResourceVersion("v1");
        bound.setResourceType("workflow");
        bound.setValid(true);
        when(mappingMapper.selectByAppIdAndResourceType("agent-1", "workflow")).thenReturn(List.of(bound));
        when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(null);
        // wf-1无任何版本，last_version_id为null
        WorkflowEntity workflow = new WorkflowEntity();
        workflow.setId("wf-1");
        when(workflowMapper.selectByWorkflowIds(anyString(), nullable(String.class), anyList()))
            .thenReturn(List.of(workflow));

        MappingEntity incoming = new MappingEntity();
        incoming.setResourceId("wf-1");
        incoming.setResourceVersion("v1");
        incoming.setResourceType("workflow");

        relationManagementService.handleAgentWorkflow("p1", "w1", "agent-1", List.of(incoming));

        // 无版本可回退时CAS回退为null（跟随最新）
        verify(mappingMapper).updateResourceVersionIfMatch("wf-1", "v1", null);
        ArgumentCaptor<MappingEntity> modifyCaptor = ArgumentCaptor.forClass(MappingEntity.class);
        verify(mappingMapper).updateResourceParameterByAppIDAndResourceId(modifyCaptor.capture());
        assertNull(modifyCaptor.getValue().getResourceVersion());
    }

    @Test
    void testHandleAgentWorkflow_ExistingBoundVersion_NoHeal() {
        // 已绑定工作流的版本号仍存在：不触发自愈，正常路径零行为变化
        MappingEntity bound = new MappingEntity();
        bound.setAppId("agent-1");
        bound.setResourceId("wf-1");
        bound.setResourceVersion("v1");
        bound.setResourceType("workflow");
        bound.setValid(true);
        when(mappingMapper.selectByAppIdAndResourceType("agent-1", "workflow")).thenReturn(List.of(bound));
        ReleaseVersion existing = new ReleaseVersion();
        existing.setAppId("wf-1");
        existing.setVersionId("v1");
        when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(existing);

        MappingEntity incoming = new MappingEntity();
        incoming.setResourceId("wf-1");
        incoming.setResourceVersion("v1");
        incoming.setResourceType("workflow");

        relationManagementService.handleAgentWorkflow("p1", "w1", "agent-1", List.of(incoming));

        // 版本存在时不执行任何回退
        verify(mappingMapper, never()).updateResourceVersionIfMatch(anyString(), anyString(), any());
        verify(mappingMapper).updateResourceParameterByAppIDAndResourceId(any(MappingEntity.class));
    }

    private MappingEntity buildToolMapping(String appId, String appWorkspaceId, String referenceType) {
        MappingEntity entity = new MappingEntity();
        entity.setMappingId("m-" + appId);
        entity.setAppId(appId);
        entity.setAppType("agent");
        entity.setAppWorkspaceId(appWorkspaceId);
        entity.setResourceId("plugin-1#tool-1");
        entity.setResourceType("tool");
        entity.setResourceVersion("v1");
        entity.setReferenceType(referenceType);
        entity.setValid(true);
        return entity;
    }

    @Test
    void testListResourceRelations_CrossSpaceOnly_PlazaRefsNotCoveredByShareCounted() {
        // #1733 测试反馈：插件共享+上架并存时，广场引用落库同为 'share'，
        // 下架统计不能再按 reference_type 排除 share，而应按共享范围判定。
        // 属主 W1，共享给 W3；W2 从广场引用。下架统计应只保留 W2 的引用：
        // W3 在共享范围内下架后仍可经共享解析，W1 为属主同空间引用。
        String ownerWs = "w1-owner";
        String inScopeWs = "w3-shared";
        String plazaWs = "w2-plaza";
        ListResourceRelationsQo qo = new ListResourceRelationsQo();
        qo.setResourceType("tool");
        qo.setWorkspaceId(ownerWs);
        qo.setCrossSpaceOnly(true);

        PluginEntity plugin = new PluginEntity();
        plugin.setWorkspaceId(ownerWs);
        when(pluginMapper.selectByPrimaryKey("plugin-1", "p1")).thenReturn(plugin);

        ShareScopeEntity scope = new ShareScopeEntity();
        scope.setWorkspaceId(inScopeWs);
        when(shareScopeMapper.selectShareScopesByResourceId("plugin-1")).thenReturn(List.of(scope));

        when(mappingMapper.selectByResourceIdAndVersionId(eq("plugin-1"), any(), any(), any(), any()))
            .thenReturn(List.of(
                buildToolMapping("app-owner", ownerWs, "direct"),
                buildToolMapping("app-shared", inScopeWs, "share"),
                buildToolMapping("app-plaza", plazaWs, "share")));

        var result = relationManagementService.listResourceRelations("p1", "plugin-1", qo);

        assertEquals(1, result.getCount());
        assertEquals(1, result.getRelations().size());
        assertEquals("app-plaza", result.getRelations().get(0).getAppId());
    }

    @Test
    void testListResourceRelations_ShareQuery_OnlyInScopeConsumersCounted() {
        // #1733 测试反馈：共享"被引用"统计只保留共享范围覆盖的跨空间消费方引用；
        // 广场消费方（W2，不在共享范围）与属主自身引用均不计入。
        String ownerWs = "w1-owner";
        String inScopeWs = "w3-shared";
        String plazaWs = "w2-plaza";
        ListResourceRelationsQo qo = new ListResourceRelationsQo();
        qo.setResourceType("tool");
        qo.setWorkspaceId(ownerWs);
        qo.setReferenceType("share");

        PluginEntity plugin = new PluginEntity();
        plugin.setWorkspaceId(ownerWs);
        when(pluginMapper.selectByPrimaryKey("plugin-1", "p1")).thenReturn(plugin);

        ShareScopeEntity scope = new ShareScopeEntity();
        scope.setWorkspaceId(inScopeWs);
        when(shareScopeMapper.selectShareScopesByResourceId("plugin-1")).thenReturn(List.of(scope));

        when(mappingMapper.selectByResourceIdAndVersionId(eq("plugin-1"), any(), any(), any(), any()))
            .thenReturn(List.of(
                buildToolMapping("app-owner", ownerWs, "direct"),
                buildToolMapping("app-shared", inScopeWs, "share"),
                buildToolMapping("app-plaza", plazaWs, "share")));

        var result = relationManagementService.listResourceRelations("p1", "plugin-1", qo);

        assertEquals(1, result.getCount());
        assertEquals("app-shared", result.getRelations().get(0).getAppId());
    }

    @Test
    void testListResourceRelations_CrossSpaceOnly_ShareToAll_NoPlazaDependentRefs() {
        // 全员共享（scope='all'）时所有跨空间引用都被共享覆盖，下架不影响任何引用。
        String ownerWs = "w1-owner";
        ListResourceRelationsQo qo = new ListResourceRelationsQo();
        qo.setResourceType("tool");
        qo.setWorkspaceId(ownerWs);
        qo.setCrossSpaceOnly(true);

        PluginEntity plugin = new PluginEntity();
        plugin.setWorkspaceId(ownerWs);
        when(pluginMapper.selectByPrimaryKey("plugin-1", "p1")).thenReturn(plugin);

        ShareScopeEntity scopeAll = new ShareScopeEntity();
        scopeAll.setWorkspaceId("all");
        when(shareScopeMapper.selectShareScopesByResourceId("plugin-1")).thenReturn(List.of(scopeAll));

        when(mappingMapper.selectByResourceIdAndVersionId(eq("plugin-1"), any(), any(), any(), any()))
            .thenReturn(List.of(
                buildToolMapping("app-owner", ownerWs, "direct"),
                buildToolMapping("app-plaza", "w2-plaza", "share")));

        var result = relationManagementService.listResourceRelations("p1", "plugin-1", qo);

        assertEquals(0, result.getCount());
    }

    @Test
    void testListResourceRelations_CrossSpaceOnly_SkillOwnerResolvedFromSkillTable() {
        // #1733 测试反馈：Skill 下架统计同样按跨空间口径，属主空间从 t_skill 解析。
        String ownerWs = "w1-owner";
        ListResourceRelationsQo qo = new ListResourceRelationsQo();
        qo.setResourceType("skill");
        qo.setWorkspaceId(ownerWs);
        qo.setCrossSpaceOnly(true);

        SkillDetails skill = new SkillDetails();
        skill.setWorkspaceId(ownerWs);
        when(skillMapper.searchBySkillId("skill-1")).thenReturn(skill);
        when(shareScopeMapper.selectShareScopesByResourceId("skill-1")).thenReturn(Collections.emptyList());

        MappingEntity ownerRef = buildToolMapping("app-owner", ownerWs, "direct");
        ownerRef.setResourceId("skill-1");
        MappingEntity crossRef = buildToolMapping("app-cross", "w2-cross", "direct");
        crossRef.setResourceId("skill-1");
        when(mappingMapper.selectByResourceIdAndVersionId(eq("skill-1"), any(), any(), any(), any()))
            .thenReturn(List.of(ownerRef, crossRef));

        var result = relationManagementService.listResourceRelations("p1", "skill-1", qo);

        assertEquals(1, result.getCount());
        assertEquals("app-cross", result.getRelations().get(0).getAppId());
    }

    @Test
    void testListAppRelations_PlazaAnchorOverridesLatestForCrossSpaceRef() {
        // #1735 测试反馈：跨空间直接引用广场已上架插件时，升级提示的目标版本应为广场锚定版本
        // （plaza_version_id），而非插件最新发布版本；当前版本名称也应回填用于弹窗展示。
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w2");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ListAppRelationsQo qo = new ListAppRelationsQo();
            qo.setWorkspaceId("w2");
            qo.setVersion("latest");
            qo.setShowlatest(true);

            // 跨空间直接引用（app 在 w2，插件在 w1-owner）
            MappingEntity mapping = buildToolMapping("app-w2", "w2", "direct");
            mapping.setAppType("workflow");
            mapping.setAppName("wf");
            mapping.setResourceVersion("v1-id");
            when(mappingMapper.selectByAppIdAndAppVersion("app-w2", "latest", null, null))
                .thenReturn(new ArrayList<>(List.of(mapping)));
            when(mappingMapper.selectByAppIdAndAppVersion("app-w2", null, null, null))
                .thenReturn(Collections.emptyList());

            WorkspaceEntity ws = new WorkspaceEntity();
            ws.setId("w2");
            ws.setName("W2");
            when(workspaceMapper.selectWorkspaceByWorkspaceIdList(anyList())).thenReturn(List.of(ws));

            // 插件最新发布版本
            ReleaseVersion latest = new ReleaseVersion();
            latest.setAppId("plugin-1");
            latest.setVersionId("latest-id");
            latest.setVersionName("v-latest");
            latest.setAppType("tool");
            when(releaseVersionMapper.queryLastVersionByAppIds(anySet())).thenReturn(List.of(latest));
            // 当前引用版本名称回填
            ReleaseVersion current = new ReleaseVersion();
            current.setAppId("plugin-1");
            current.setVersionId("v1-id");
            current.setVersionName("v1");
            when(releaseVersionMapper.queryByWfVersions(anyList())).thenReturn(List.of(current));
            // 广场锚定版本
            PluginEntity plazaPlugin = new PluginEntity();
            plazaPlugin.setPluginId("plugin-1");
            plazaPlugin.setPlatformPublished(1);
            plazaPlugin.setPlazaVersionId("anchor-id");
            plazaPlugin.setWorkspaceId("w1-owner");
            when(pluginMapper.selectByIds(anyList())).thenReturn(List.of(plazaPlugin));
            ReleaseVersion anchor = new ReleaseVersion();
            anchor.setAppId("plugin-1");
            anchor.setVersionId("anchor-id");
            anchor.setVersionName("v-anchor");
            when(releaseVersionMapper.selectByAppIdAndVersionId("plugin-1", "anchor-id")).thenReturn(anchor);

            when(shareResourceManagerService.queryShareResourceEntityByResourceIdList(anyList()))
                .thenReturn(Collections.emptyList());
            when(skillMapper.searchBySkillIds(anyList(), any())).thenReturn(Collections.emptyList());

            var result = relationManagementService.listAppRelations("p1", "app-w2", qo);

            assertEquals(1, result.getCount());
            var relation = result.getRelations().get(0);
            assertEquals("anchor-id", relation.getResourceLatestVersion());
            assertEquals("v-anchor", relation.getResourceLatestVersionName());
            assertEquals("v1", relation.getResourceVersionName());
        }
    }

    @Test
    void testListAppRelations_PlazaAnchorAppliedForSameSpaceRef() {
        // 同空间引用（属主自己的插件）同样按锚定版本提示：锚定版本是广场上唯一可见可用的版本，
        // 属主空间若提示到未锚定的更新发布版，消费方升级后会与广场契约不一致。
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1-owner");
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ListAppRelationsQo qo = new ListAppRelationsQo();
            qo.setWorkspaceId("w1-owner");
            qo.setVersion("latest");
            qo.setShowlatest(true);

            MappingEntity mapping = buildToolMapping("app-owner", "w1-owner", "direct");
            mapping.setAppType("workflow");
            mapping.setAppName("wf");
            mapping.setResourceVersion("v1-id");
            when(mappingMapper.selectByAppIdAndAppVersion("app-owner", "latest", null, null))
                .thenReturn(new ArrayList<>(List.of(mapping)));
            when(mappingMapper.selectByAppIdAndAppVersion("app-owner", null, null, null))
                .thenReturn(Collections.emptyList());

            WorkspaceEntity ws = new WorkspaceEntity();
            ws.setId("w1-owner");
            ws.setName("W1");
            when(workspaceMapper.selectWorkspaceByWorkspaceIdList(anyList())).thenReturn(List.of(ws));

            ReleaseVersion latest = new ReleaseVersion();
            latest.setAppId("plugin-1");
            latest.setVersionId("latest-id");
            latest.setVersionName("v-latest");
            latest.setAppType("tool");
            when(releaseVersionMapper.queryLastVersionByAppIds(anySet())).thenReturn(List.of(latest));
            when(releaseVersionMapper.queryByWfVersions(anyList())).thenReturn(Collections.emptyList());

            PluginEntity plazaPlugin = new PluginEntity();
            plazaPlugin.setPluginId("plugin-1");
            plazaPlugin.setPlatformPublished(1);
            plazaPlugin.setPlazaVersionId("anchor-id");
            plazaPlugin.setWorkspaceId("w1-owner");
            when(pluginMapper.selectByIds(anyList())).thenReturn(List.of(plazaPlugin));
            ReleaseVersion anchor = new ReleaseVersion();
            anchor.setAppId("plugin-1");
            anchor.setVersionId("anchor-id");
            anchor.setVersionName("v-anchor");
            when(releaseVersionMapper.selectByAppIdAndVersionId("plugin-1", "anchor-id")).thenReturn(anchor);

            when(shareResourceManagerService.queryShareResourceEntityByResourceIdList(anyList()))
                .thenReturn(Collections.emptyList());
            when(skillMapper.searchBySkillIds(anyList(), any())).thenReturn(Collections.emptyList());

            var result = relationManagementService.listAppRelations("p1", "app-owner", qo);

            var relation = result.getRelations().get(0);
            assertEquals("anchor-id", relation.getResourceLatestVersion());
            assertEquals("v-anchor", relation.getResourceLatestVersionName());
        }
    }
}
