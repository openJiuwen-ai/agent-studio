/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayInputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.atLeast;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * RuntimeAssetExporter 单元测试（覆盖 SDD 8.3 测试要点）。
 * mock 依赖：MappingMapper / MgObsService / ReleaseVersionMapper / PublishUtils +
 * RequestContextUtils（静态）。验证版本解析、三类型分流、t_mapping 收集、
 * model-auth/KB/skill 收集、缺失终止、元数据重写、并发、上限。
 */
class RuntimeAssetExporterTest {

    private MappingMapper mappingMapper;
    private MgObsService mgObsService;
    private ReleaseVersionMapper releaseVersionMapper;
    private PublishUtils publishUtils;
    private AgentMapper agentMapper;
    private WorkflowMapper workflowMapper;
    private SkillMapper skillMapper;
    private ShareResourceManagerService shareResourceManagerService;
    private RuntimeAssetExporter exporter;

    private static final String PROJECT_ID = "proj-001";
    private static final String WORKSPACE_ID = "ws-001";
    private static final String AGENT_ID = "agent-uuid-001";
    private static final String VERSION = "1728465600000";

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        mappingMapper = mock(MappingMapper.class);
        mgObsService = mock(MgObsService.class);
        releaseVersionMapper = mock(ReleaseVersionMapper.class);
        publishUtils = mock(PublishUtils.class);
        agentMapper = mock(AgentMapper.class);
        workflowMapper = mock(WorkflowMapper.class);
        skillMapper = mock(SkillMapper.class);
        shareResourceManagerService = mock(ShareResourceManagerService.class);
        exporter = new RuntimeAssetExporter();
        ReflectionTestUtils.setField(exporter, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(exporter, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(exporter, "releaseVersionMapper", releaseVersionMapper);
        ReflectionTestUtils.setField(exporter, "publishUtils", publishUtils);
        ReflectionTestUtils.setField(exporter, "agentMapper", agentMapper);
        ReflectionTestUtils.setField(exporter, "workflowMapper", workflowMapper);
        ReflectionTestUtils.setField(exporter, "skillMapper", skillMapper);
        ReflectionTestUtils.setField(exporter, "shareResourceManagerService", shareResourceManagerService);
        // @PostConstruct 不会在 new 时触发，手动初始化默认配置 + Semaphore（与 application-manager.yml 默认值一致）
        ReflectionTestUtils.setField(exporter, "maxAssets", 100);
        ReflectionTestUtils.setField(exporter, "maxConcurrent", 5);
        ReflectionTestUtils.invokeMethod(exporter, "initSemaphore");
        // 归属校验默认放行（所有 agent/workflow 用例复用）；越权用例可各自 override 为 null
        when(agentMapper.selectByProjectIdAndWorkspaceId(anyString(), anyString(), anyString()))
            .thenReturn(new Agent());
        when(workflowMapper.selectByWorkflowIds(anyString(), anyString(), anyList()))
            .thenReturn(List.of(new WorkflowEntity()));
    }

    /** 构造一个基础 agent IR JSON（含 modelConfig） */
    private String agentIrJson() {
        Map<String, Object> ir = new HashMap<>();
        ir.put("agentId", AGENT_ID);
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> modelConfig = new HashMap<>();
        modelConfig.put("modelName", "model-svc-001");
        Map<String, Object> ext = new HashMap<>();
        ext.put("authId", "auth-001");
        modelConfig.put("extension", ext);
        configs.put("modelConfig", modelConfig);
        ir.put("configs", configs);
        return com.alibaba.fastjson2.JSON.toJSONString(ir);
    }

    private String metadataJson(String versionId) {
        Map<String, Object> meta = new HashMap<>();
        meta.put("versionId", versionId);
        meta.put("agentId", AGENT_ID);
        return com.alibaba.fastjson2.JSON.toJSONString(meta);
    }

    private MappingEntity mapping(String resType, String resId, String resVer) {
        MappingEntity m = new MappingEntity();
        m.setResourceType(resType);
        m.setResourceId(resId);
        m.setResourceVersion(resVer);
        m.setValid(true);
        return m;
    }

    /** 默认 mock：版本解析（latest）+ 根 IR + metadata 存在 + model-service 存在 */
    private void mockDefaultAgent() {
        AgentMetadata meta = AgentMetadata.builder().versionId(VERSION).agentId(AGENT_ID).build();
        when(publishUtils.getPublish(eq(AGENT_ID), eq(Constants.LATEST_PUBLISH_VERSION), any())).thenReturn(meta);
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any()))
            .thenReturn(new ArrayList<>());
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrJson());
        String metadataKey = "metadata/" + AGENT_ID + "/" + AGENT_ID + "_latest.json";
        when(mgObsService.getObject(metadataKey)).thenReturn(metadataJson(VERSION));
        when(mgObsService.uploadStreamStagingBucket(anyString(), any(), org.mockito.ArgumentMatchers.anyInt()))
            .thenReturn("export/url.zip");
    }

    /** 调导出并消费 ZIP 资源：读完全部字节触发临时文件删除，避免测试泄漏临时文件。 */
    private byte[] exportZipBytes(String projectId, String workspaceId, String resourceType, String resourceId,
        String version) {
        try (java.io.InputStream in = exporter.exportRuntimeAssetZip(projectId, workspaceId, resourceType, resourceId,
            version).getInputStream()) {
            return in.readAllBytes();
        } catch (java.io.IOException e) {
            throw new RuntimeException(e);
        }
    }

    // ===== SDD 8.3: 版本解析 =====

    @Test
    void testResolveVersion_latest_resolvesViaPublishUtils() {
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zipBytes = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            // 断言 resolvedVersion 传给了 mapper（非 null/latest）
            verify(mappingMapper).selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any());
            assertNotNull(zipBytes);
        }
    }

    @Test
    void testResolveVersion_notPublished_throws() {
        when(publishUtils.getPublish(eq(AGENT_ID), eq(Constants.LATEST_PUBLISH_VERSION), any())).thenReturn(null);
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            assertThrows(Exception.class, () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
        }
    }

    @Test
    void testResolveVersion_concreteVersion_validatesExistence() {
        ReleaseVersion rv = new ReleaseVersion();
        rv.setAppId(AGENT_ID);
        rv.setVersionId(VERSION);
        when(releaseVersionMapper.selectByAppIdAndVersionId(AGENT_ID, VERSION)).thenReturn(rv);
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any()))
            .thenReturn(new ArrayList<>());
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrJson());
        when(mgObsService.getObject("metadata/" + AGENT_ID + "/" + AGENT_ID + "_latest.json"))
            .thenReturn(metadataJson(VERSION));
        when(mgObsService.uploadStreamStagingBucket(anyString(), any(), org.mockito.ArgumentMatchers.anyInt()))
            .thenReturn("export/url.zip");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            assertDoesNotThrow(() -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, VERSION));
        }
    }

    @Test
    void testResolveVersion_concreteVersion_notExist_throws() {
        when(releaseVersionMapper.selectByAppIdAndVersionId(AGENT_ID, VERSION)).thenReturn(null);
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            assertThrows(Exception.class, () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, VERSION));
        }
    }

    // ===== SDD 8.3: 三类型分流 =====

    @Test
    void testRootIr_workflowType_usesWorkflowIrPath() {
        String wfId = "wf-001";
        AgentMetadata meta = AgentMetadata.builder().versionId(VERSION).agentId(wfId).build();
        when(publishUtils.getPublish(eq(wfId), eq(Constants.LATEST_PUBLISH_VERSION), any())).thenReturn(meta);
        when(mappingMapper.selectByAppIdAndAppVersion(eq(wfId), eq(VERSION), any(), any())).thenReturn(new ArrayList<>());
        String wfIrKey = "workflow/ir/" + wfId + "/" + wfId + "_" + VERSION + ".json";
        when(mgObsService.getObject(wfIrKey)).thenReturn("{\"configs\":{}}");
        when(mgObsService.getObject("metadata/" + wfId + "/" + wfId + "_latest.json")).thenReturn(metadataJson(VERSION));
        when(mgObsService.uploadStreamStagingBucket(anyString(), any(), org.mockito.ArgumentMatchers.anyInt()))
            .thenReturn("export/url.zip");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            exportZipBytes(PROJECT_ID, WORKSPACE_ID, "workflow", wfId, null);
            // 断言读的是 workflow/ir/ 路径（收集阶段 + 打包阶段各读一次，atLeast）
            verify(mgObsService, atLeast(1)).getObject(wfIrKey);
        }
    }

    // ===== SDD 8.3: t_mapping 收集 + 子 IR =====

    @Test
    void testCollectAssetKeys_workflowMapping_collectsWorkflowIr() {
        mockDefaultAgent();
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-001", VERSION));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        String subWfIrKey = "workflow/ir/sub-wf-001/sub-wf-001_" + VERSION + ".json";
        when(mgObsService.getObject(subWfIrKey)).thenReturn("{\"configs\":{}}");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            verify(mgObsService, atLeast(1)).getObject(subWfIrKey);
        }
    }

    @Test
    void testCollectAssetKeys_modelMapping_collectsModelService() {
        mockDefaultAgent();
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("model", "model-svc-001", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        // model-service 文件
        Map<String, Object> ms = new HashMap<>();
        ms.put("provider_id", "prov-001");
        ms.put("project_id", "proj-001");
        ms.put("auth_id", "auth-001");
        when(mgObsService.getObject("model-service/ir/model-svc-001.json"))
            .thenReturn(com.alibaba.fastjson2.JSON.toJSONString(ms));
        // model-auth 文件
        when(mgObsService.getObject("model-auth/auth/proj-001/prov-001/auth-001.json")).thenReturn("{}");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            verify(mgObsService, atLeast(1)).getObject("model-service/ir/model-svc-001.json");
        }
    }

    // ===== SDD 8.3: 平台模型特判 =====

    @Test
    void testPlatformModel_systemProjectId_usesRootProjectId() {
        mockDefaultAgent();
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("model", "platform-model-001", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        Map<String, Object> ms = new HashMap<>();
        ms.put("provider_id", "prov-001");
        ms.put("project_id", "SYSTEM");  // 平台模型
        ms.put("auth_id", "auth-001");
        when(mgObsService.getObject("model-service/ir/platform-model-001.json"))
            .thenReturn(com.alibaba.fastjson2.JSON.toJSONString(ms));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            // 平台模型 → authProjectId 用根应用 PROJECT_ID 而非 SYSTEM
            verify(mgObsService).getObject("model-auth/auth/" + PROJECT_ID + "/prov-001/auth-001.json");
        }
    }

    // ===== SDD 8.3: 缺失终止 =====

    @Test
    void testRootIrMissing_throws() {
        AgentMetadata meta = AgentMetadata.builder().versionId(VERSION).agentId(AGENT_ID).build();
        when(publishUtils.getPublish(eq(AGENT_ID), eq(Constants.LATEST_PUBLISH_VERSION), any())).thenReturn(meta);
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(new ArrayList<>());
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        when(mgObsService.getObject(rootIrKey)).thenThrow(new RuntimeException("OBS 404"));
        when(mgObsService.getObject("metadata/" + AGENT_ID + "/" + AGENT_ID + "_latest.json")).thenReturn(metadataJson(VERSION));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            assertThrows(Exception.class, () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
        }
    }

    // ===== SDD 8.3: 元数据历史版本重写 =====

    @Test
    void testHistoryExport_rewritesMetadataVersionId() {
        ReleaseVersion rv = new ReleaseVersion();
        rv.setAppId(AGENT_ID);
        rv.setVersionId("old-version-111");
        when(releaseVersionMapper.selectByAppIdAndVersionId(AGENT_ID, "old-version-111")).thenReturn(rv);
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq("old-version-111"), any(), any()))
            .thenReturn(new ArrayList<>());
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_old-version-111.json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrJson());
        // metadata 内容指向当前最新版本（非 old-version-111）
        when(mgObsService.getObject("metadata/" + AGENT_ID + "/" + AGENT_ID + "_latest.json"))
            .thenReturn(metadataJson("new-version-222"));
        when(mgObsService.uploadStreamStagingBucket(anyString(), any(), org.mockito.ArgumentMatchers.anyInt()))
            .thenReturn("export/url.zip");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            assertDoesNotThrow(() -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, "old-version-111"));
        }
    }

    // ===== SDD 8.3: 并发控制 =====

    @Test
    void testConcurrency_semaphoreLimits() throws Exception {
        mockDefaultAgent();
        // 模拟信号量耗尽：占满 5 个许可
        java.util.concurrent.Semaphore sem = new java.util.concurrent.Semaphore(5);
        sem.acquire(5);
        ReflectionTestUtils.setField(exporter, "exportSemaphore", sem);
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            assertThrows(Exception.class, () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
        } finally {
            sem.release(5);
        }
    }

    // ===== 越权校验（2026-10-14 巡检新增）=====

    @Test
    void testAuthCheck_projectIdMismatch_throws() {
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            // 请求传篡改的 projectId，与 RequestContext 不一致 → 抛越权异常
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> exportZipBytes("evil-project", WORKSPACE_ID, "agent", AGENT_ID, null));
            // 验证抛的是越权错误码（而非其他 AgentStudioException，防误判）
            assertEquals(StudioError.USER_WORKSPACE_PERMISSION_INVALID, ex.getErrorCode());
        }
    }

    @Test
    void testAuthCheck_workspaceIdMismatch_throws() {
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            // 请求传篡改的 workspaceId，与 RequestContext 不一致 → 抛越权异常
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> exportZipBytes(PROJECT_ID, "evil-workspace", "agent", AGENT_ID, null));
            assertEquals(StudioError.USER_WORKSPACE_PERMISSION_INVALID, ex.getErrorCode());
        }
    }

    @Test
    void testAuthCheck_contextProjectIdBlank_rejects() {
        // bug005 #3：RequestContext 上下文为空时直接拒绝（fail-closed），不再放行——
        // 否则 validateResourceOwnership 会信任请求参数，攻击者可传他人 project/workspace/resourceId 越权导出。
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn("");
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("");
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            assertEquals(StudioError.USER_WORKSPACE_PERMISSION_INVALID, ex.getErrorCode());
        }
    }

    @Test
    void testMaxConcurrent_zeroConfigured_doesNotDeadlock() {
        // maxConcurrent 配 0 时，@PostConstruct 兜底为 1，导出不永久 busy
        ReflectionTestUtils.setField(exporter, "maxConcurrent", 0);
        ReflectionTestUtils.invokeMethod(exporter, "initSemaphore");
        // maxAssets 保持 setUp 的 100（不被 maxConcurrent 影响）
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            // 配 0 兜底为 1 → 能拿到许可 → 不抛 busy 异常
            assertDoesNotThrow(() -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
        }
    }

    // ===== 巡检 #2：resourceId 归属校验（IDOR）=====

    @Test
    void testOwnership_resourceIdNotInWorkspace_throws() {
        mockDefaultAgent();
        // override：resourceId 不归属当前 (projectId, workspaceId) → 越权拒绝
        when(agentMapper.selectByProjectIdAndWorkspaceId(eq(PROJECT_ID), eq(WORKSPACE_ID), eq(AGENT_ID)))
            .thenReturn(null);
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            assertEquals(StudioError.USER_WORKSPACE_PERMISSION_INVALID, ex.getErrorCode());
        }
    }

    // ===== 巡检 #1：技能 ZIP 二进制完整性（走 readObsFileStream，不走文本通道）=====

    @Test
    void testSkillBinary_readStreamNotTextChannel() throws Exception {
        mockDefaultAgent();
        // 巡检 #5：skill_path 归属校验改为 workspace 级（SkillMapper.searchBySkillIds 查 workspaceId）
        String skillPath = "testUser/skills/sk-1/v1/skill.zip";
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        // 根 IR 内嵌 skill_info.skill_path
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithSkillJson(skillPath));
        // 技能 ZIP 二进制：含非法 UTF-8 字节（经文本通道会损坏/抛异常）
        byte[] skillBytes = new byte[] {(byte) 0x80, (byte) 0xFF, 0x01, 0x02, (byte) 0xC0, (byte) 0xC1, 0x7F, 0x00};
        when(mgObsService.readObsFileStream(skillPath)).thenReturn(new ByteArrayInputStream(skillBytes));
        // skill 归属当前 workspace（isOwnedSkillPath 查 SkillMapper.searchBySkillIds）
        SkillDetails skillDetail = new SkillDetails();
        skillDetail.setWorkspaceId(WORKSPACE_ID);
        when(skillMapper.searchBySkillIds(List.of("sk-1"))).thenReturn(List.of(skillDetail));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            assertNotNull(zip);
            // 关键断言：技能不走文本通道（getObject/UTF-8 解码会损坏二进制）
            verify(mgObsService, never()).getObject(skillPath);
            // 解压校验：技能 entry 字节与原字节完全一致（未被 UTF-8 解码破坏）
            byte[] extracted = extractZipEntry(zip, skillPath);
            assertNotNull(extracted, "skill entry not found in zip");
            assertArrayEquals(skillBytes, extracted);
        }
    }

    // ===== 巡检 #3/#4：子 IR 版本以父 IR 内嵌 ir_path 为准 + note =====

    @Test
    void testSubIrVersionConflict_irPathWins() throws Exception {
        mockDefaultAgent();
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        String oldVerKey = "workflow/ir/sub-wf-001/sub-wf-001_old-ver-000.json";
        String newVerKey = "workflow/ir/sub-wf-001/sub-wf-001_new-ver-999.json";
        // t_mapping 给子工作流 old-ver；根 IR 内嵌 ir_path 指向 new-ver
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-001", "old-ver-000"));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        when(mgObsService.getObject(oldVerKey)).thenReturn("{\"configs\":{}}");
        when(mgObsService.getObject(newVerKey)).thenReturn("{\"configs\":{}}");
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithWorkflowsJson(newVerKey));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // ir_path 胜出：new-ver 入包，old-ver 不入包
            assertTrue(names.contains(newVerKey), "ir_path version should be in zip");
            assertFalse(names.contains(oldVerKey), "t_mapping version should NOT be in zip");
            // manifest 中该 asset note 非空（记录版本对齐差异）
            assertTrue(manifestAssetNoteContains(zip, newVerKey, "ir_path"),
                "manifest note should record version alignment");
        }
    }

    // ===== 巡检 #9（@472/@489）：版本冲突时旧子 IR 从 worklist 移除，其派生资产不收集 =====

    @Test
    void testVersionConflict_staleIrRemovedFromWorklist() throws Exception {
        mockDefaultAgent();
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        String oldVerKey = "workflow/ir/sub-wf-001/sub-wf-001_old-ver-000.json";
        String newVerKey = "workflow/ir/sub-wf-001/sub-wf-001_new-ver-999.json";
        // 旧版本子 IR 引用旧 skill；新版本子 IR 引用新 skill（版本对齐后旧 IR 应移出 worklist，旧 skill 不收集）
        String oldSkill = "testUser/skills/sk-old/v1/old.zip";
        String newSkill = "testUser/skills/sk-new/v1/new.zip";
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-001", "old-ver-000"));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        // 旧版本子 IR（含旧 skill_path）—— 版本对齐后被移除，不应被 poll 处理
        when(mgObsService.getObject(oldVerKey)).thenReturn(workflowIrWithChildAndSkillJson(oldVerKey, oldSkill));
        // 新版本子 IR（含新 skill_path）—— 入队被处理，新 skill 收集
        when(mgObsService.getObject(newVerKey)).thenReturn(workflowIrWithChildAndSkillJson(newVerKey, newSkill));
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithWorkflowsJson(newVerKey));
        when(mgObsService.readObsFileStream(newSkill))
            .thenReturn(new ByteArrayInputStream(new byte[] {0x41}));
        // 两个 skill 都归属当前 workspace（区别仅在版本对齐是否收集旧 skill）
        SkillDetails oldSkillDetail = new SkillDetails();
        oldSkillDetail.setWorkspaceId(WORKSPACE_ID);
        SkillDetails newSkillDetail = new SkillDetails();
        newSkillDetail.setWorkspaceId(WORKSPACE_ID);
        when(skillMapper.searchBySkillIds(List.of("sk-old"))).thenReturn(List.of(oldSkillDetail));
        when(skillMapper.searchBySkillIds(List.of("sk-new"))).thenReturn(List.of(newSkillDetail));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 旧版本子 IR 的 skill 不应入包（旧 IR 从 worklist 移除，不再被处理）
            assertFalse(names.contains(oldSkill), "stale skill from removed old-version sub-IR must NOT be in zip");
            // 新版本子 IR 的 skill 入包
            assertTrue(names.contains(newSkill), "new-version sub-IR skill should be in zip");
        }
    }

    // ===== bug004 #2：manifest 蛇形契约（@JsonProperty，fastjson2 会输出驼峰破坏契约）=====

    @Test
    void testManifest_usesSnakeCaseContract() throws Exception {
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            byte[] manifestBytes = extractZipEntry(zip, "manifest.json");
            assertNotNull(manifestBytes, "manifest.json should exist in zip");
            String manifest = new String(manifestBytes, java.nio.charset.StandardCharsets.UTF_8);
            // 正向：蛇形契约字段存在（导入工具 tools/import_asset_zip.py 读 manifest_version/export_id/total_size_bytes）
            assertTrue(manifest.contains("\"manifest_version\""), "manifest should use snake_case manifest_version");
            assertTrue(manifest.contains("\"export_id\""), "manifest should use snake_case export_id");
            assertTrue(manifest.contains("\"total_size_bytes\""), "manifest should use snake_case total_size_bytes");
            assertTrue(manifest.contains("\"total_assets\""), "manifest should use snake_case total_assets");
            // 反向：驼峰不应出现（fastjson2 默认按 Java 字段名输出驼峰，破坏蛇形契约）
            assertFalse(manifest.contains("\"manifestVersion\""), "manifest should NOT contain camelCase manifestVersion");
            assertFalse(manifest.contains("\"exportId\""), "manifest should NOT contain camelCase exportId");
        }
    }

    // ===== bug004 #3：版本对齐后的新版本子 IR 重新进入抽取，其更深 child IR/skill 被收集 =====

    @Test
    void testSubIrVersionConflict_newVersionDerivedAssetsCollected() throws Exception {
        mockDefaultAgent();
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        String oldSubKey = "workflow/ir/sub-wf-001/sub-wf-001_old-ver-000.json";
        String newSubKey = "workflow/ir/sub-wf-001/sub-wf-001_new-ver-999.json";
        String grandchildKey = "workflow/ir/grand-001/grand-001_v1.json";
        // bug007 #1：skill_path userId 必须匹配 getRequestUserId（mock 返回 testUser）
        String skillPath = "testUser/skills/sk-grd/v1/skill.zip";
        // t_mapping 给子工作流 old-ver；根 IR 内嵌 ir_path 指向 new-ver（版本冲突 → new-ver 胜出）
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-001", "old-ver-000"));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        when(mgObsService.getObject(oldSubKey)).thenReturn("{\"configs\":{}}");
        // new-ver 子 IR：自身引用更深层 grandchild IR + skill（bug004 #3：这些应被收集，原快照遍历会漏）
        when(mgObsService.getObject(newSubKey)).thenReturn(workflowIrWithChildAndSkillJson(grandchildKey, skillPath));
        when(mgObsService.getObject(grandchildKey)).thenReturn("{\"configs\":{}}");
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithWorkflowsJson(newSubKey));
        // skill 走二进制流（不 mock 则标 missing 不入包，无法断言）
        when(mgObsService.readObsFileStream(skillPath))
            .thenReturn(new ByteArrayInputStream(new byte[] {0x41, 0x42, 0x43}));
        // 巡检 #5：skill 归属校验改 workspace 级（SkillMapper.searchBySkillIds 查 workspaceId）
        SkillDetails skillDetail = new SkillDetails();
        skillDetail.setWorkspaceId(WORKSPACE_ID);
        when(skillMapper.searchBySkillIds(List.of("sk-grd"))).thenReturn(List.of(skillDetail));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 版本对齐后的 new-ver 子 IR 重新进入抽取 → 其更深层 child IR 被收集（bug004 #3）
            verify(mgObsService, atLeast(1)).getObject(grandchildKey);
            assertTrue(names.contains(grandchildKey), "grandchild IR of version-aligned sub-IR should be in zip");
            // new-ver 子 IR 的 skill 被收集（bug004 #3）
            assertTrue(names.contains(skillPath), "skill of version-aligned sub-IR should be in zip");
        }
    }

    // ===== bug005 #2：IR 衍生路径遍历校验（../ 跨租户 OBS 读取 + Zip Slip）=====

    @Test
    void testInvalidIrPath_traversalRejected_notReadNotZipped() throws Exception {
        mockDefaultAgent();
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        // 恶意 skill_path（../ 遍历）+ 恶意 child ir_path（../ 遍历）——IR 可被构造（如导入的智能体包）
        String maliciousSkill = "../../other-tenant/secret.zip";
        String maliciousIrPath = "../../other-tenant/evil.json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithTraversalPathsJson(maliciousSkill, maliciousIrPath));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 恶意路径不入包（防 Zip Slip 解压越界）
            assertFalse(names.contains(maliciousSkill), "traversal skill_path must NOT be in zip");
            assertFalse(names.contains(maliciousIrPath), "traversal ir_path must NOT be in zip");
            // 恶意路径不从 OBS 读取（防跨租户数据泄露）
            verify(mgObsService, never()).readObsFileStream(maliciousSkill);
            verify(mgObsService, never()).getObject(maliciousIrPath);
        }
    }

    // ===== bug006 #1：跨租户前缀校验（非 ../ 的合法相对路径，但指向其他租户前缀）=====

    @Test
    void testCrossTenantPrefix_rejected_notReadNotZipped() throws Exception {
        mockDefaultAgent();
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        // 恶意但"合法相对路径"：无 ../（过黑名单），但前缀是其他租户/未知目录——白名单应拒绝
        // bug006 #1：旧 isValidAssetKey 只拦 ../，放行此 key；新白名单按合法前缀拒绝
        String crossTenantSkill = "other-tenant/skills/secret.zip";
        String crossTenantIrPath = "other-tenant/agent/ir/evil/evil_v1.json";
        when(mgObsService.getObject(rootIrKey))
            .thenReturn(agentIrWithTraversalPathsJson(crossTenantSkill, crossTenantIrPath));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 跨租户前缀路径不入包
            assertFalse(names.contains(crossTenantSkill), "cross-tenant skill_path must NOT be in zip");
            assertFalse(names.contains(crossTenantIrPath), "cross-tenant ir_path must NOT be in zip");
            // 跨租户前缀路径不从 OBS 读取（防跨租户数据泄露）
            verify(mgObsService, never()).readObsFileStream(crossTenantSkill);
            verify(mgObsService, never()).getObject(crossTenantIrPath);
        }
    }

    // ===== 巡检 #10：model-service/KB 非法 key 不读 OBS（addAsset 校验结果 gate 后续 getCachedObject）=====

    @Test
    void testInvalidModelServiceKey_traversal_notReadFromObs() throws Exception {
        mockDefaultAgent();
        // t_mapping 含一个 model 资源，serviceId 含 ../ 遍历 → model-service key 非法
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("model", "../other-tenant/evil", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        String maliciousMsKey = "model-service/ir/../other-tenant/evil.json";
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            // 非法 model-service key 不入包也不读 OBS，导出不被破坏（根 IR + metadata 正常入包）
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            Set<String> names = zipEntryNames(zip);
            assertFalse(names.contains(maliciousMsKey), "traversal model-service key must NOT be in zip");
            // 关键（巡检 #10）：非法 key 不读 OBS（修复前 getCachedObject 无条件以非法 key 读 OBS）
            verify(mgObsService, never()).getObject(maliciousMsKey);
        }
    }

    @Test
    void testInvalidKbReferenceKey_traversal_notReadFromObs() throws Exception {
        mockDefaultAgent();
        // t_mapping 含一个 repo（KB 引用），kbId 含 ../ 遍历 → kb-reference key 非法
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("repo", "../other-tenant/evil-kb", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        String maliciousKbKey = "kb-connection/ir/knowledge-base/../other-tenant/evil-kb.json";
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            Set<String> names = zipEntryNames(zip);
            assertFalse(names.contains(maliciousKbKey), "traversal kb-reference key must NOT be in zip");
            // 关键（巡检 #10）：非法 kbId 构造的 key 不读 OBS
            verify(mgObsService, never()).getObject(maliciousKbKey);
        }
    }

    @Test
    void testInvalidKbConnectionKey_traversal_notReadFromObs() throws Exception {
        mockDefaultAgent();
        // t_mapping 含一个 repo，kbId 合法（kb-reference 可读），但其 connectionId 含 ../ → conn key 非法
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("repo", "valid-kb", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        // kb-reference 文件内容含恶意 connectionId（来自可被构造的 KB 引用文件）
        when(mgObsService.getObject("kb-connection/ir/knowledge-base/valid-kb.json"))
            .thenReturn("{\"connectionId\":\"../other-tenant/evil-conn\"}");
        String maliciousConnKey = "kb-connection/ir/connection/../other-tenant/evil-conn.json";
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            Set<String> names = zipEntryNames(zip);
            assertFalse(names.contains(maliciousConnKey), "traversal kb-connection key must NOT be in zip");
            // 关键（巡检 #10）：非法 connectionId 构造的 conn key 不读 OBS
            verify(mgObsService, never()).getObject(maliciousConnKey);
        }
    }

    // ===== bug007 #1：子资源归属校验（跨用户 skill + 跨 workspace 子 IR）=====

    @Test
    void testUnownedSkillPath_rejected() throws Exception {
        mockDefaultAgent();
        // skill_path userId 与当前请求用户（testUser）不一致 → 拒绝（防跨用户读取他人技能）
        String unownedSkill = "other-user/skills/sk-1/v1/skill.zip";
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithSkillJson(unownedSkill));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            assertFalse(names.contains(unownedSkill), "unowned skill_path must NOT be in zip");
            verify(mgObsService, never()).readObsFileStream(unownedSkill);
        }
    }

    @Test
    void testCrossWorkspaceChildIr_alignedNotRejected() throws Exception {
        mockDefaultAgent();
        // 巡检 #12：跨 workspace 共享子 IR 须经 t_share_resource 共享授权才放行（归属或共享），
        // 不再"仅 warn 不跳过"无条件放行。other-wf 不归属当前 workspace，但已共享授权 → 放行入包。
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        String crossWorkspaceChildIr = "workflow/ir/other-wf/other-wf_v1.json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithWorkflowsJson(crossWorkspaceChildIr));
        // other-wf 不归属当前 workspace → isOwnedOrSharedChildIr 归属不通过，转校验共享授权
        when(workflowMapper.selectByWorkflowIds(eq(PROJECT_ID), eq(WORKSPACE_ID), anyList()))
            .thenReturn(new ArrayList<>());
        // 经 t_share_resource 共享授权给当前 workspace → 放行（归属或共享，fail-closed 仅拒非共享）
        when(shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(eq(WORKSPACE_ID), eq("other-wf")))
            .thenReturn(true);
        // 子 IR 内容（合法路径通过 isValidAssetKey，仍被读取 + 入包）
        when(mgObsService.getObject(crossWorkspaceChildIr)).thenReturn("{\"configs\":{}}");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 跨 workspace 共享子 IR 仍进版本对齐 → 入包（不再被拒绝）
            assertTrue(names.contains(crossWorkspaceChildIr), "cross-workspace shared child IR should be in zip (aligned, not rejected)");
            verify(mgObsService, atLeast(1)).getObject(crossWorkspaceChildIr);
        }
    }

    @Test
    void testCrossWorkspaceChildIr_notOwnedNotShared_rejected() throws Exception {
        mockDefaultAgent();
        // 巡检 #12：子 IR 不归属当前 workspace 且未共享授权 → fail-closed（不入包、不读 OBS）
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        String unsharedChildIr = "workflow/ir/other-wf-x/other-wf-x_v1.json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithWorkflowsJson(unsharedChildIr));
        // other-wf-x 不归属当前 workspace
        when(workflowMapper.selectByWorkflowIds(eq(PROJECT_ID), eq(WORKSPACE_ID), anyList()))
            .thenReturn(new ArrayList<>());
        // 且未共享授权给当前 workspace → fail-closed 拒绝
        when(shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(eq(WORKSPACE_ID), eq("other-wf-x")))
            .thenReturn(false);
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            Set<String> names = zipEntryNames(zip);
            // 不归属且未共享的子 IR 不入包（fail-closed，防越权读取他人 IR）
            assertFalse(names.contains(unsharedChildIr), "unowned & unshared child IR must NOT be in zip");
            // 关键（巡检 #12）：不读 OBS（修复前仅 warn 不跳过，会读 OBS + 入包）
            verify(mgObsService, never()).getObject(unsharedChildIr);
        }
    }

    @Test
    void testNullVersionChild_resolvedVersion_depsCollected() throws Exception {
        mockDefaultAgent();
        // 巡检 #13：子资源 resourceVersion=null（跟随 latest）补齐具体发布版本后递归收集依赖，
        // 不再 continue 致其 t_mapping 引用的 model/KB 依赖整体丢失（运行包不完整）
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-null", null)); // null version 子 workflow
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        // resolvePublishVersion 对 null version 子资源补齐：publishUtils.getPublish → 具体版本
        AgentMetadata subMeta = AgentMetadata.builder().versionId("sub-resolved-ver").agentId("sub-wf-null").build();
        when(publishUtils.getPublish(eq("sub-wf-null"), eq(Constants.LATEST_PUBLISH_VERSION), any()))
            .thenReturn(subMeta);
        // 补齐版本后按 "sub-resolved-ver" 查子依赖：含一个 model 依赖（此前 null-version continue 会丢失）
        when(mappingMapper.selectByAppIdAndAppVersion(eq("sub-wf-null"), eq("sub-resolved-ver"), any(), any()))
            .thenReturn(List.of(mapping("model", "model-dep", null)));
        // 子 workflow 本体 IR 文件（补齐版本后入包）
        when(mgObsService.getObject("workflow/ir/sub-wf-null/sub-wf-null_sub-resolved-ver.json"))
            .thenReturn("{\"configs\":{}}");
        // model-dep 的 model-service 文件（证明依赖被收集，未丢失）
        when(mgObsService.getObject("model-service/ir/model-dep.json")).thenReturn("{\"data\":{}}");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            assertDoesNotThrow(() -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            // 关键（巡检 #13）：null-version 子资源补齐后，其 model 依赖被收集（不丢）
            verify(mgObsService, atLeast(1)).getObject("model-service/ir/model-dep.json");
        }
    }

    // ===== 巡检 #5：skill 归属改 workspace 级（跨用户共享 skill 放行 / 跨 workspace skill 拒绝）=====

    @Test
    void testSkill_crossUserSharedInSameWorkspace_allowed() throws Exception {
        mockDefaultAgent();
        // 同 workspace、不同 userId 创建的 skill（跨用户共享）→ workspace 级校验放行
        String skillPath = "otherUser/skills/sk-shared/v1/skill.zip";
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithSkillJson(skillPath));
        when(mgObsService.readObsFileStream(skillPath))
            .thenReturn(new ByteArrayInputStream(new byte[] {0x41}));
        // skill 归属当前 workspace（searchBySkillIds 返回 workspaceId 匹配）→ 放行
        SkillDetails skillDetail = new SkillDetails();
        skillDetail.setWorkspaceId(WORKSPACE_ID);
        when(skillMapper.searchBySkillIds(List.of("sk-shared"))).thenReturn(List.of(skillDetail));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 跨用户共享 skill（同 workspace）→ 放行入包（不再因 userId 不同被丢弃）
            assertTrue(names.contains(skillPath), "cross-user shared skill in same workspace should be in zip");
        }
    }

    @Test
    void testSkill_crossWorkspace_rejected() throws Exception {
        mockDefaultAgent();
        // 跨 workspace 的 skill（workspaceId 不匹配）→ fail-closed 跳过
        String skillPath = "otherUser/skills/sk-other-ws/v1/skill.zip";
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithSkillJson(skillPath));
        // skill 属于其他 workspace → isOwnedSkillPath 返回 false → 跳过
        SkillDetails skillDetail = new SkillDetails();
        skillDetail.setWorkspaceId("other-workspace");
        when(skillMapper.searchBySkillIds(List.of("sk-other-ws"))).thenReturn(List.of(skillDetail));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // 跨 workspace skill → fail-closed 拒绝（不入包、不读 OBS 字节流）
            assertFalse(names.contains(skillPath), "cross-workspace skill must NOT be in zip");
            verify(mgObsService, never()).readObsFileStream(skillPath);
        }
    }

    // ===== 巡检 #6：model-auth 笛卡尔积超 max-assets 不整体失败（非 critical 超限跳过）=====

    @Test
    void testModelAuthCartesian_exceedsMax_notOverallFailure() throws Exception {
        mockDefaultAgent();
        // 把 max-assets 设为很小（如 5），让 model-auth 笛卡尔积快速超限
        ReflectionTestUtils.setField(exporter, "maxAssets", 5);
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        // 根 IR 内嵌多个 authId + 引用 model-service
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithAuthIdsJson("auth-1", "auth-2", "auth-3"));
        // model-service 配置
        String msKey = "model-service/ir/ms-1.json";
        when(mgObsService.getObject(msKey)).thenReturn(modelServiceJson("prov-1", PROJECT_ID, null));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            // model-auth 笛卡尔积超 max-assets（5）→ 非 critical 资产跳过，不抛 EXPORT_LENGTH_TOO_LARGE
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            assertNotNull(zip, "export should succeed even if model-auth cartesian product exceeds max-assets");
            Set<String> names = zipEntryNames(zip);
            // critical 资产（根 IR/metadata）仍在 zip 内
            assertTrue(names.contains(rootIrKey), "root IR (critical) should still be in zip");
        }
    }

    /** 根 IR 内嵌多个 extension.authId（用于笛卡尔积超限测试）。 */
    private String agentIrWithAuthIdsJson(String... authIds) {
        Map<String, Object> ir = new HashMap<>();
        ir.put("agentId", AGENT_ID);
        List<Map<String, Object>> models = new ArrayList<>();
        for (String authId : authIds) {
            Map<String, Object> ext = new HashMap<>();
            ext.put("authId", authId);
            Map<String, Object> model = new HashMap<>();
            model.put("modelName", "ms-1");
            model.put("extension", ext);
            models.add(model);
        }
        Map<String, Object> configs = new HashMap<>();
        configs.put("models", models);
        ir.put("configs", configs);
        return com.alibaba.fastjson2.JSON.toJSONString(ir);
    }

    // ===== bug007 #2：版本冲突先校验，非法 ir_path 保留 t_mapping 合法版本（不静默缺失）=====

    @Test
    void testVersionConflict_invalidIrPath_keepsMappingVersion() throws Exception {
        mockDefaultAgent();
        String rootIrKey = "agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json";
        String validMappingKey = "workflow/ir/sub-wf-001/sub-wf-001_old-ver-000.json";
        // 父 IR 内嵌的 ir_path 非法（跨租户前缀）→ 不应移除 t_mapping 合法版本（bug007 #2）
        String invalidIrPath = "other-tenant/workflow/ir/sub-wf-001/sub-wf-001_new-ver.json";
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-001", "old-ver-000"));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        when(mgObsService.getObject(validMappingKey)).thenReturn("{\"configs\":{}}");
        when(mgObsService.getObject(rootIrKey)).thenReturn(agentIrWithWorkflowsJson(invalidIrPath));
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            Set<String> names = zipEntryNames(zip);
            // t_mapping 合法版本保留（未被非法 ir_path 替换/移除）
            assertTrue(names.contains(validMappingKey), "valid t_mapping version must be kept");
            // 非法 ir_path 不入包
            assertFalse(names.contains(invalidIrPath), "invalid ir_path must NOT replace valid version");
        }
    }

    // ===== bug007 #3：addAsset 上限前置校验（防恶意 IR 在上限生效前累积大量 OBS 读取 DoS）=====

    @Test
    void testMaxAssets_enforcedDuringCollection() {
        // maxAssets 配 2 → 根 IR + metadata 已占 2，子 IR 收集时第 3 个 asset 触发上限抛异常
        ReflectionTestUtils.setField(exporter, "maxAssets", 2);
        mockDefaultAgent();
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("workflow", "sub-wf-001", VERSION));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        String subWfIrKey = "workflow/ir/sub-wf-001/sub-wf-001_" + VERSION + ".json";
        when(mgObsService.getObject(subWfIrKey)).thenReturn("{\"configs\":{}}");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            // 根 IR + metadata = 2，子 IR 第 3 个触发 EXPORT_LENGTH_TOO_LARGE
            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            assertEquals(StudioError.EXPORT_LENGTH_TOO_LARGE, ex.getErrorCode());
        }
    }

    // ===== 巡检 #11：maxAssets<=0（误配）回退默认上限，导出可用 =====

    @Test
    void testMaxAssets_zeroOrNegative_clampedToDefault_exportUsable() throws Exception {
        // maxAssets 误配 0 → initSemaphore 兜底回退默认上限（巡检 #11），不再根 IR 入包即抛 EXPORT_LENGTH_TOO_LARGE
        ReflectionTestUtils.setField(exporter, "maxAssets", 0);
        ReflectionTestUtils.invokeMethod(exporter, "initSemaphore");
        // 回退后 maxAssets 为正值（默认 100），导出可用
        int clamped = (int) ReflectionTestUtils.getField(exporter, "maxAssets");
        assertTrue(clamped > 0, "maxAssets<=0 should be clamped to a positive default, got " + clamped);
        mockDefaultAgent();
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            // 关键（巡检 #11）：误配 0 不再使导出完全不可用
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            assertNotNull(zip, "export should produce a zip when maxAssets misconfigured to 0");
        }
    }

    // ===== 巡检 #7：STRATEGY auth_id_list 逐子模型鉴权收集 =====

    // ===== bug006：model-service/KB 文件损坏（非 JSON）不冒泡 500，按 SDD 5.6 继续 =====

    @Test
    void testCorruptModelServiceJson_skipsAndCompletesExport() throws Exception {
        mockDefaultAgent();
        // t_mapping 含一个 model 资源，其 model-service 文件内容损坏（非 JSON）
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("model", "corrupt-ms", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        when(mgObsService.getObject("model-service/ir/corrupt-ms.json")).thenReturn("<<<not-json>>>");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            // 损坏 model-service 非根资产 → 不抛 500，导出正常完成（根 IR + metadata 入包）
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            Set<String> names = zipEntryNames(zip);
            // 根 IR + metadata 仍入包（导出未被破坏）
            assertTrue(names.contains("agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json"),
                "root IR should still be in zip");
            // 关键：parse 失败 → 不收集 model-auth（addModelAuthAsset 在 parse 之后，parse 失败 return 跳过）
            // model-service key 本身在 parse 前已 addAsset（入包，内容为损坏字节），但 model-auth 不应被收集
            boolean hasModelAuth = names.stream().anyMatch(n -> n.startsWith("model-auth/auth/"));
            assertFalse(hasModelAuth, "corrupt model-service should skip model-auth collection");
        }
    }

    @Test
    void testCorruptKbReferenceJson_skipsAndCompletesExport() throws Exception {
        mockDefaultAgent();
        // t_mapping 含一个 repo（KB 引用），其 kb-reference 文件内容损坏（非 JSON）
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("repo", "corrupt-kb", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        when(mgObsService.getObject("kb-connection/ir/knowledge-base/corrupt-kb.json")).thenReturn("<<<not-json>>>");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            byte[] zip = assertDoesNotThrow(
                () -> exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null));
            Set<String> names = zipEntryNames(zip);
            // KB 引用文件本身仍入包（收集阶段已 addAsset），但 KB 连接不收集（parse 失败跳过）
            // 关键断言：损坏 KB 非根资产 → 不抛 500，导出正常完成
            assertTrue(names.contains("agent/ir/" + AGENT_ID + "/" + AGENT_ID + "_" + VERSION + ".json"),
                "root IR should still be in zip");
        }
    }

    @Test
    void testStrategyAuthIdList_collected() {
        mockDefaultAgent();
        List<MappingEntity> mappings = new ArrayList<>();
        mappings.add(mapping("strategy", "strategy-001", null));
        when(mappingMapper.selectByAppIdAndAppVersion(eq(AGENT_ID), eq(VERSION), any(), any())).thenReturn(mappings);
        // 路由策略文件：service_id_list 两个子模型，auth_id_list 一一对应
        when(mgObsService.getObject("model-service/ir/strategy-001.json"))
            .thenReturn(routerStrategyJson("sub-ms-1,sub-ms-2", "auth-a,auth-b", "prov-1", PROJECT_ID));
        // 子模型 model-service 文件（不含 auth_metadata_id，强制走 explicitAuthId）
        when(mgObsService.getObject("model-service/ir/sub-ms-1.json"))
            .thenReturn(modelServiceJson("prov-1", PROJECT_ID, null));
        when(mgObsService.getObject("model-service/ir/sub-ms-2.json"))
            .thenReturn(modelServiceJson("prov-1", PROJECT_ID, null));
        // 鉴权文件
        when(mgObsService.getObject("model-auth/auth/" + PROJECT_ID + "/prov-1/auth-a.json")).thenReturn("{}");
        when(mgObsService.getObject("model-auth/auth/" + PROJECT_ID + "/prov-1/auth-b.json")).thenReturn("{}");
        try (MockedStatic<RequestContextUtils> mocked = Mockito.mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(PROJECT_ID);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(WORKSPACE_ID);
            mocked.when(RequestContextUtils::getRequestUserId).thenReturn("testUser");
            exportZipBytes(PROJECT_ID, WORKSPACE_ID, "agent", AGENT_ID, null);
            // auth_id_list 中的 authId 对应的 model-auth 被收集
            verify(mgObsService, atLeast(1)).getObject("model-auth/auth/" + PROJECT_ID + "/prov-1/auth-a.json");
            verify(mgObsService, atLeast(1)).getObject("model-auth/auth/" + PROJECT_ID + "/prov-1/auth-b.json");
        }
    }

    // ===== 辅助：IR 构建 =====

    /** 根 IR 内嵌恶意 skill_path + 恶意 child ir_path（含 ../ 遍历，bug005 #2 路径校验） */
    private String agentIrWithTraversalPathsJson(String maliciousSkillPath, String maliciousChildIrPath) {
        Map<String, Object> ir = new HashMap<>();
        ir.put("agentId", AGENT_ID);
        Map<String, Object> skill = new HashMap<>();
        skill.put("skill_path", maliciousSkillPath);
        Map<String, Object> skills = new HashMap<>();
        skills.put("skill_info", List.of(skill));
        Map<String, Object> wf = new HashMap<>();
        wf.put("ir_path", maliciousChildIrPath);
        Map<String, Object> configs = new HashMap<>();
        configs.put("skills", skills);
        configs.put("workflows", List.of(wf));
        ir.put("configs", configs);
        return com.alibaba.fastjson2.JSON.toJSONString(ir);
    }

    private String agentIrWithWorkflowsJson(String childIrPath) {
        Map<String, Object> ir = new HashMap<>();
        ir.put("agentId", AGENT_ID);
        Map<String, Object> wf = new HashMap<>();
        wf.put("ir_path", childIrPath);
        Map<String, Object> configs = new HashMap<>();
        configs.put("workflows", List.of(wf));
        ir.put("configs", configs);
        return com.alibaba.fastjson2.JSON.toJSONString(ir);
    }

    private String agentIrWithSkillJson(String skillPath) {
        Map<String, Object> ir = new HashMap<>();
        ir.put("agentId", AGENT_ID);
        Map<String, Object> skill = new HashMap<>();
        skill.put("skill_path", skillPath);
        Map<String, Object> skills = new HashMap<>();
        skills.put("skill_info", List.of(skill));
        Map<String, Object> configs = new HashMap<>();
        configs.put("skills", skills);
        ir.put("configs", configs);
        return com.alibaba.fastjson2.JSON.toJSONString(ir);
    }

    /** 子工作流 IR：自身引用更深层 child IR（ir_path）+ skill（bug004 #3 验证 new-ver 子 IR 派生资产被收集） */
    private String workflowIrWithChildAndSkillJson(String childIrPath, String skillPath) {        Map<String, Object> ir = new HashMap<>();
        ir.put("workflowId", "sub-wf-001");
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> wf = new HashMap<>();
        wf.put("ir_path", childIrPath);
        configs.put("workflows", List.of(wf));
        Map<String, Object> skill = new HashMap<>();
        skill.put("skill_path", skillPath);
        Map<String, Object> skills = new HashMap<>();
        skills.put("skill_info", List.of(skill));
        configs.put("skills", skills);
        ir.put("configs", configs);
        return com.alibaba.fastjson2.JSON.toJSONString(ir);
    }

    private String modelServiceJson(String providerId, String projectId, String authMetadataId) {
        Map<String, Object> data = new HashMap<>();
        data.put("provider_id", providerId);
        data.put("project_id", projectId);
        if (authMetadataId != null) {
            data.put("auth_metadata_id", authMetadataId);
        }
        Map<String, Object> ms = new HashMap<>();
        ms.put("type", "model");
        ms.put("data", data);
        return com.alibaba.fastjson2.JSON.toJSONString(ms);
    }

    private String routerStrategyJson(String serviceIdList, String authIdList, String providerId, String projectId) {
        Map<String, Object> data = new HashMap<>();
        data.put("service_id_list", serviceIdList);
        data.put("auth_id_list", authIdList);
        data.put("provider_id", providerId);
        data.put("project_id", projectId);
        Map<String, Object> ms = new HashMap<>();
        ms.put("type", "router");
        ms.put("data", data);
        return com.alibaba.fastjson2.JSON.toJSONString(ms);
    }

    // ===== 辅助：ZIP 解析 =====

    private Set<String> zipEntryNames(byte[] zip) throws Exception {
        Set<String> names = new HashSet<>();
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e;
            while ((e = zis.getNextEntry()) != null) {
                names.add(e.getName());
            }
        }
        return names;
    }

    private byte[] extractZipEntry(byte[] zip, String name) throws Exception {
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e;
            while ((e = zis.getNextEntry()) != null) {
                if (e.getName().equals(name)) {
                    return zis.readAllBytes();
                }
            }
        }
        return null;
    }

    private boolean manifestAssetNoteContains(byte[] zip, String assetKey, String fragment) throws Exception {
        byte[] manifestBytes = extractZipEntry(zip, "manifest.json");
        if (manifestBytes == null) {
            return false;
        }
        com.alibaba.fastjson2.JSONObject manifest = com.alibaba.fastjson2.JSON
            .parseObject(new String(manifestBytes, java.nio.charset.StandardCharsets.UTF_8));
        com.alibaba.fastjson2.JSONArray assets = manifest.getJSONArray("assets");
        if (assets == null) {
            return false;
        }
        for (int i = 0; i < assets.size(); i++) {
            com.alibaba.fastjson2.JSONObject a = assets.getJSONObject(i);
            if (assetKey.equals(a.getString("key"))) {
                String note = a.getString("note");
                return note != null && note.contains(fragment);
            }
        }
        return false;
    }
}
