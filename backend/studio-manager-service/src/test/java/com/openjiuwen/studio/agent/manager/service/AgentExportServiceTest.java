/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceVersion;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.enums.ExportModeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceMgmtService;
import com.openjiuwen.studio.agent.manager.service.md.RouterStrategyMgmtService;
import com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapterFactory;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class AgentExportServiceTest {

    private WorkflowMapper workflowMapper;
    private MappingMapper mappingMapper;
    private AgentMapper agentMapper;
    private ReleaseVersionMapper releaseVersionMapper;
    private MgObsService obsService;
    private ModelServiceMgmtService modelServiceMgmtService;
    private RouterStrategyMgmtService strategyMgmtService;
    private SkuManageService skuManageService;
    private ResourceAdapterFactory resourceAdapterFactory;
    private I18nUtil i18nUtil;

    private AgentExportService agentExportService;

    @BeforeEach
    void setUp() {
        workflowMapper = mock(WorkflowMapper.class);
        mappingMapper = mock(MappingMapper.class);
        agentMapper = mock(AgentMapper.class);
        releaseVersionMapper = mock(ReleaseVersionMapper.class);
        obsService = mock(MgObsService.class);
        modelServiceMgmtService = mock(ModelServiceMgmtService.class);
        strategyMgmtService = mock(RouterStrategyMgmtService.class);
        skuManageService = mock(SkuManageService.class);
        resourceAdapterFactory = mock(ResourceAdapterFactory.class);
        i18nUtil = mock(I18nUtil.class);

        MockitoAnnotations.openMocks(this);
        agentExportService = new AgentExportService();
        ReflectionTestUtils.setField(agentExportService, "workflowMapper", workflowMapper);
        ReflectionTestUtils.setField(agentExportService, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(agentExportService, "agentMapper", agentMapper);
        ReflectionTestUtils.setField(agentExportService, "releaseVersionMapper", releaseVersionMapper);
        ReflectionTestUtils.setField(agentExportService, "obsService", obsService);
        ReflectionTestUtils.setField(agentExportService, "modelServiceMgmtService", modelServiceMgmtService);
        ReflectionTestUtils.setField(agentExportService, "strategyMgmtService", strategyMgmtService);
        ReflectionTestUtils.setField(agentExportService, "skuManageService", skuManageService);
        ReflectionTestUtils.setField(agentExportService, "resourceAdapterFactory", resourceAdapterFactory);
        ReflectionTestUtils.setField(agentExportService, "i18nUtil", i18nUtil);
        ReflectionTestUtils.setField(agentExportService, "jacksonObjectMapper", new ObjectMapper());
        ReflectionTestUtils.setField(agentExportService, "envType", "public");
        ReflectionTestUtils.setField(agentExportService, "importMaxLen", 10);
    }

    @Test
    void testExportResource_ExceedsMaxLength() {
        ExportResourceParams params = new ExportResourceParams();
        List<String> ids = new ArrayList<>();
        for (int i = 0; i < 15; i++) {
            ids.add("id-" + i);
        }
        params.setResourceIds(ids);
        params.setResourceType("AGENT");

        assertThrows(AgentStudioException.class, () ->
            agentExportService.exportResource("p1", "w1", null, params));
    }

    @Test
    void testExportResource_UnsupportedResourceType() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(List.of("id-1"));
        params.setResourceType("UNKNOWN_TYPE");

        assertThrows(Exception.class, () ->
            agentExportService.exportResource("p1", "w1", null, params));
    }

    @Test
    void testExportResource_NullResourceIds() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(null);
        params.setResourceType("AGENT");

        assertThrows(Exception.class, () ->
            agentExportService.exportResource("p1", "w1", null, params));
    }

    @Test
    void testExportResource_EmptyResourceIds() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(List.of());
        params.setResourceType("WORKFLOW");

        assertThrows(Exception.class, () ->
            agentExportService.exportResource("p1", "w1", null, params));
    }

    /**
     * T9: 前端不传 version（{resource_id}）→ 后端转 latest → 查草稿 mapping。
     * 对齐旧版 lumina-console 前端行为。
     */
    @Test
    void testExportWorkflow_NoVersion_TranslatesToLatest() {
        try (MockedStatic<RequestContextUtils> mockedStatic = Mockito.mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("p1");
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ExportResourceParams params = new ExportResourceParams();
            params.setResourceIds(List.of("wf-1"));
            params.setResourceVersions(List.of(new ExportResourceVersion().setResourceId("wf-1")));
            params.setResourceType("WORKFLOW");

            // mock 校验通过
            com.openjiuwen.studio.agent.manager.entity.WorkflowEntity wf = new com.openjiuwen.studio.agent.manager.entity.WorkflowEntity();
            wf.setId("wf-1");
            wf.setName("wf-name");
            when(workflowMapper.selectByWorkflowIds("p1", "w1", List.of("wf-1"))).thenReturn(List.of(wf));
            when(workflowMapper.getWorkflowById("wf-1")).thenReturn(wf);
            when(workflowMapper.selectByWorkflowId("p1", "w1", "wf-1")).thenReturn(wf);
            // 草稿 mapping 为空（无子资源）
            when(mappingMapper.selectByAppIdAndAppVersion(eq("wf-1"), eq("latest"), isNull(), isNull()))
                .thenReturn(new ArrayList<>());
            // mock OBS 上传
            mockObsForExport();

            assertDoesNotThrow(() -> agentExportService.exportResource("p1", "w1", null, params));
            // 验证用 "latest" 查了草稿 mapping
            verify(mappingMapper).selectByAppIdAndAppVersion(eq("wf-1"), eq("latest"), isNull(), isNull());
            // 未查版本（latest 不校验）
            verify(releaseVersionMapper, never()).selectByAppIdAndVersionId(anyString(), anyString());
        }
    }

    /**
     * T10: 传指定 version_id → 校验版本存在 + 用 versionId 查版本 mapping。
     */
    @Test
    void testExportWorkflow_SpecifiedVersion_QueriesVersionMapping() {
        try (MockedStatic<RequestContextUtils> mockedStatic = Mockito.mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("p1");
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ExportResourceParams params = new ExportResourceParams();
            params.setResourceIds(List.of("wf-1"));
            params.setResourceVersions(List.of(
                new ExportResourceVersion().setResourceId("wf-1").setResourceVersion("v1.0.0")));
            params.setResourceType("WORKFLOW");

            com.openjiuwen.studio.agent.manager.entity.WorkflowEntity wf = new com.openjiuwen.studio.agent.manager.entity.WorkflowEntity();
            wf.setId("wf-1");
            wf.setName("wf-name");
            when(workflowMapper.selectByWorkflowIds("p1", "w1", List.of("wf-1"))).thenReturn(List.of(wf));
            when(workflowMapper.getWorkflowById("wf-1")).thenReturn(wf);
            when(workflowMapper.selectByWorkflowId("p1", "w1", "wf-1")).thenReturn(wf);
            // 版本存在
            ReleaseVersion releaseVersion = new ReleaseVersion();
            releaseVersion.setAppId("wf-1");
            releaseVersion.setVersionId("v1.0.0");
            releaseVersion.setDslPath("workflow/wf-1/wf-1_v1.0.0.json");
            when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1.0.0")).thenReturn(releaseVersion);
            // 版本 mapping 为空
            when(mappingMapper.selectByAppIdAndAppVersion(eq("wf-1"), eq("v1.0.0"), isNull(), isNull()))
                .thenReturn(new ArrayList<>());
            // mock adapter（返回空 ExportResp，跳过子资源导出）
            com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapter adapter = mock(
                com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapter.class);
            when(resourceAdapterFactory.getAdapter(anyString())).thenReturn(adapter);
            when(adapter.parseExport(anyList())).thenReturn(null);
            // mock OBS 上传
            mockObsForExport();

            assertDoesNotThrow(() -> agentExportService.exportResource("p1", "w1", null, params));
            // 验证校验了版本存在性
            verify(releaseVersionMapper).selectByAppIdAndVersionId("wf-1", "v1.0.0");
            // 验证用 versionId 查了版本 mapping（不是 "latest"）
            verify(mappingMapper).selectByAppIdAndAppVersion(eq("wf-1"), eq("v1.0.0"), isNull(), isNull());
            verify(mappingMapper, never()).selectByAppIdAndAppVersion(eq("wf-1"), eq("latest"), isNull(), isNull());
        }
    }

    /**
     * T11: 不存在的 versionId → 容错处理（对齐旧版 lumina validResource）：
     * 不抛异常中断导出，而是把该资源作为失败项加入 exportResps 并 continue 跳过，导出仍返回 200 + downloadUrl。
     */
    @Test
    void testExportWorkflow_NonExistVersion_ToleratesAndSkips() {
        try (MockedStatic<RequestContextUtils> mockedStatic = Mockito.mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("p1");
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ExportResourceParams params = new ExportResourceParams();
            params.setResourceIds(List.of("wf-1"));
            params.setResourceVersions(List.of(
                new ExportResourceVersion().setResourceId("wf-1").setResourceVersion("non-exist")));
            params.setResourceType("WORKFLOW");

            com.openjiuwen.studio.agent.manager.entity.WorkflowEntity wf = new com.openjiuwen.studio.agent.manager.entity.WorkflowEntity();
            wf.setId("wf-1");
            wf.setName("wf-name");
            when(workflowMapper.selectByWorkflowIds("p1", "w1", List.of("wf-1"))).thenReturn(List.of(wf));
            when(workflowMapper.getWorkflowById("wf-1")).thenReturn(wf);
            when(workflowMapper.selectByWorkflowId("p1", "w1", "wf-1")).thenReturn(wf);
            // 版本不存在
            when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "non-exist")).thenReturn(null);
            // mock OBS 上传（容错后仍会走 buildExportFile 上传空 jsonl）
            mockObsForExport();

            // 不抛异常（容错，对齐旧版 lumina）
            com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp rsp1 = assertDoesNotThrow(() ->
                agentExportService.exportResource("p1", "w1", null, params));
            // 验证校验了版本存在性
            verify(releaseVersionMapper).selectByAppIdAndVersionId("wf-1", "non-exist");
            // 验证未查版本 mapping（版本不存在，continue 跳过，不进入子资源导出）
            verify(mappingMapper, never()).selectByAppIdAndAppVersion(eq("wf-1"), anyString(), isNull(), isNull());
            // 导出仍返回下载 URL（不中断）
            assertNotNull(rsp1);
            assertNotNull(rsp1.getDownloadUrl());
        }
    }

    @Test
    void testExportAgent_WithStrictMode() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(List.of("agent-1"));
        params.setResourceType("AGENT");
        params.setMode(ExportModeEnum.STRICT.getCode());

        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("test-agent");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1")))
            .thenReturn(List.of(agent));
        when(agentMapper.selectById("agent-1")).thenReturn(agent);
        when(mappingMapper.selectByAppIdAndAppVersion(eq("agent-1"), any(), any(), any()))
            .thenReturn(Collections.emptyList());
        mockObsForExport();

        ExportResourceRsp rsp = agentExportService.exportResource("p1", "w1", null, params);
        assertNotNull(rsp);
    }

    @Test
    void testExportAgent_WithSpaciousMode() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(List.of("agent-1"));
        params.setResourceType("AGENT");
        params.setMode(ExportModeEnum.SPACIOUS.getCode());

        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("test-agent");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1")))
            .thenReturn(List.of(agent));
        when(agentMapper.selectById("agent-1")).thenReturn(agent);

        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setResourceId("wf-1");
        mappingEntity.setResourceType("WORKFLOW");
        when(mappingMapper.selectByAppIdAndAppVersion(eq("agent-1"), any(), any(), any()))
            .thenReturn(List.of(mappingEntity));
        when(workflowMapper.selectByWorkflowIdList("p1", "w1", List.of("wf-1")))
            .thenReturn(Collections.emptyList());
        mockObsForExport();

        ExportResourceRsp rsp = agentExportService.exportResource("p1", "w1", null, params);
        assertNotNull(rsp);
    }

    @Test
    void testExportAgent_WithSpaciousMode_NoMappingEntities() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(List.of("agent-1"));
        params.setResourceType("AGENT");
        params.setMode(ExportModeEnum.SPACIOUS.getCode());

        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("test-agent");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1")))
            .thenReturn(List.of(agent));
        when(agentMapper.selectById("agent-1")).thenReturn(agent);
        when(mappingMapper.selectByAppIdAndAppVersion(eq("agent-1"), any(), any(), any()))
            .thenReturn(Collections.emptyList());
        mockObsForExport();

        ExportResourceRsp rsp = agentExportService.exportResource("p1", "w1", null, params);
        assertNotNull(rsp);
    }

    @Test
    void testExportWorkflow_WithSpaciousMode() {
        try (MockedStatic<RequestContextUtils> mockedStatic = Mockito.mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("p1");
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ExportResourceParams params = new ExportResourceParams();
            params.setResourceIds(List.of("wf-1"));
            params.setResourceType("WORKFLOW");
            params.setMode(ExportModeEnum.SPACIOUS.getCode());

            WorkflowEntity workflowEntity = new WorkflowEntity();
            workflowEntity.setId("wf-1");
            workflowEntity.setName("test-wf");
            when(workflowMapper.selectByWorkflowIds("p1", "w1", List.of("wf-1")))
                .thenReturn(List.of(workflowEntity));
            when(workflowMapper.getWorkflowById("wf-1")).thenReturn(workflowEntity);
            when(workflowMapper.selectByWorkflowId("p1", "w1", "wf-1")).thenReturn(workflowEntity);

            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setResourceId("sub-wf-1");
            mappingEntity.setResourceType("WORKFLOW");
            when(mappingMapper.selectByAppIdAndAppVersion(eq("wf-1"), any(), any(), any()))
                .thenReturn(List.of(mappingEntity));
            when(workflowMapper.selectByWorkflowIdList("p1", "w1", List.of("sub-wf-1")))
                .thenReturn(Collections.emptyList());
            mockObsForExport();

            ExportResourceRsp rsp = agentExportService.exportResource("p1", "w1", null, params);
            assertNotNull(rsp);
        }
    }

    @Test
    void testExportWorkflow_WithStrictMode() {
        try (MockedStatic<RequestContextUtils> mockedStatic = Mockito.mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn("p1");
            mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            ExportResourceParams params = new ExportResourceParams();
            params.setResourceIds(List.of("wf-1"));
            params.setResourceType("WORKFLOW");
            params.setMode(ExportModeEnum.STRICT.getCode());

            WorkflowEntity workflowEntity = new WorkflowEntity();
            workflowEntity.setId("wf-1");
            workflowEntity.setName("test-wf");
            when(workflowMapper.selectByWorkflowIds("p1", "w1", List.of("wf-1")))
                .thenReturn(List.of(workflowEntity));
            when(workflowMapper.getWorkflowById("wf-1")).thenReturn(workflowEntity);
            when(workflowMapper.selectByWorkflowId("p1", "w1", "wf-1")).thenReturn(workflowEntity);
            when(mappingMapper.selectByAppIdAndAppVersion(eq("wf-1"), any(), any(), any()))
                .thenReturn(Collections.emptyList());
            mockObsForExport();

            ExportResourceRsp rsp = agentExportService.exportResource("p1", "w1", null, params);
            assertNotNull(rsp);
        }
    }

    @Test
    void testExportController_WithSpaciousMode() {
        ExportResourceParams params = new ExportResourceParams();
        params.setResourceIds(List.of("controller-1"));
        params.setResourceType("CONTROLLER");
        params.setMode(ExportModeEnum.SPACIOUS.getCode());

        Agent agent = new Agent();
        agent.setAgentId("controller-1");
        agent.setName("test-controller");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("controller-1")))
            .thenReturn(List.of(agent));
        when(agentMapper.selectById("controller-1")).thenReturn(agent);

        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setResourceId("sub-controller-1");
        mappingEntity.setResourceType("CONTROLLER");
        when(mappingMapper.selectByAppIdAndAppVersion(eq("controller-1"), any(), any(), any()))
            .thenReturn(List.of(mappingEntity));
        when(agentMapper.selectByAgentIds("p1", "CONTROLLER", List.of("sub-controller-1")))
            .thenReturn(Collections.emptyList());
        mockObsForExport();

        ExportResourceRsp rsp = agentExportService.exportResource("p1", "w1", null, params);
        assertNotNull(rsp);
    }

    private void mockObsForExport() {
        when(obsService.uploadObsFile(anyString(), any(ByteArrayInputStream.class), anyInt())).thenReturn("test-obs-key");
        when(obsService.getTemporaryGetRsp(anyBoolean(), anyString(), anyLong())).thenReturn("test-signed-url");
        com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapter adapter = mock(
            com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapter.class);
        when(resourceAdapterFactory.getAdapter(anyString())).thenReturn(adapter);
        when(adapter.parseExport(anyList())).thenReturn(null);
        when(workflowMapper.selectByWorkflowId(anyString(), anyString(), anyString())).thenReturn(null);
    }
}
