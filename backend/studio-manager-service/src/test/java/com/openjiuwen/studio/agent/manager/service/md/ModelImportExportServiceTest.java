/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.md;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.common.dto.ImportRes;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewItem;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewRsp;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelExportLine;
import com.openjiuwen.studio.agent.manager.entity.ProviderExportMetadata;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthMetadataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.UserModelServiceProviderMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * {@link ModelImportExportService} 单测。纯 Mockito Mock，对齐 {@code AgentExportServiceTest} 风格。
 * 真实构件：{@code ObjectMapper}、{@code UrlCheckUtils}
 * （enableUrlCheck=false 使 checkUrl 放通，validateEnvVarPlaceholders 走真实逻辑）。
 *
 * <p>本模块已移除签名/HMAC 与 cipher 适配检测（特性未上线，无向后兼容）。
 * 导出 JSONL 仅含 import_type + payload，不再签名；导入不验签；preview 用 line_valid 表示行级硬错误。
 */
class ModelImportExportServiceTest {

    private ModelServiceMgmtService modelServiceMgmtService;
    private ModelServiceManager modelServiceManager;
    private ModelServiceMapper modelServiceMapper;
    private UserModelServiceProviderMapper userModelServiceProviderMapper;
    private ProviderAuthMetadataMapper providerAuthMetadataMapper;
    private ProviderAuthDataMapper providerAuthDataMapper;
    private ModelLicenseCtrlService licenseCtrlService;

    private ModelImportExportService service;
    private ObjectMapper testObjectMapper;

    @BeforeEach
    void setUp() {
        modelServiceMgmtService = mock(ModelServiceMgmtService.class);
        modelServiceManager = mock(ModelServiceManager.class);
        modelServiceMapper = mock(ModelServiceMapper.class);
        userModelServiceProviderMapper = mock(UserModelServiceProviderMapper.class);
        providerAuthMetadataMapper = mock(ProviderAuthMetadataMapper.class);
        providerAuthDataMapper = mock(ProviderAuthDataMapper.class);
        licenseCtrlService = mock(ModelLicenseCtrlService.class);

        ObjectMapper objectMapper = new ObjectMapper();
        testObjectMapper = objectMapper;
        UrlCheckUtils urlCheckUtils = new UrlCheckUtils();
        ReflectionTestUtils.setField(urlCheckUtils, "enableUrlCheck", false);

        service = new ModelImportExportService();
        ReflectionTestUtils.setField(service, "modelServiceMgmtService", modelServiceMgmtService);
        ReflectionTestUtils.setField(service, "modelServiceManager", modelServiceManager);
        ReflectionTestUtils.setField(service, "modelServiceMapper", modelServiceMapper);
        ReflectionTestUtils.setField(service, "userModelServiceProviderMapper", userModelServiceProviderMapper);
        ReflectionTestUtils.setField(service, "providerAuthMetadataMapper", providerAuthMetadataMapper);
        ReflectionTestUtils.setField(service, "providerAuthDataMapper", providerAuthDataMapper);
        ReflectionTestUtils.setField(service, "urlCheckUtils", urlCheckUtils);
        ReflectionTestUtils.setField(service, "jacksonObjectMapper", objectMapper);
        ReflectionTestUtils.setField(service, "licenseCtrlService", licenseCtrlService);
    }

    /** 直接把 payload 序列化成一行 JSONL（{@code {"import_type":"model_service","payload":{...}}}），绕过导出签名。 */
    private byte[] toJsonlLine(ModelExportEntity entity) throws Exception {
        ModelExportLine line = new ModelExportLine();
        line.setImportType("model_service");
        line.setPayload(entity);
        return (testObjectMapper.writeValueAsString(line) + "\n").getBytes(StandardCharsets.UTF_8);
    }

    @Test
    void testRoundTrip_importPreservesId() throws Exception {
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "p1");

        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
        assertEquals("m1", captor.getValue().getId());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testConflictSkip() throws Exception {
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] jsonl = toJsonlLine(entity);
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1");

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        verify(modelServiceManager, never()).deleteModelService(any());
        // SKIP + 冲突 → 归类为 SKIPPED（非 FAILED），对齐 importOneModel 的 skippedRes 分支
        assertEquals(1, rsp.getSkippedLen());
        assertEquals(0, rsp.getFailedLen());
    }

    @Test
    void testConflictCover() throws Exception {
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] jsonl = toJsonlLine(entity);
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "COVER", "p1");

        // COVER 走事务化 coverModelService(DB) + 缓存补偿，不再直接调 delete/create（其内部逻辑已迁入 cover）
        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).coverModelService(captor.capture(), eq("old-id"));
        assertEquals("m1", captor.getValue().getId());
        verify(modelServiceManager).removeModelCaches("old-id");
        verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
        verify(modelServiceManager, never()).deleteModelService(any());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testEnvVarPlaceholderValid() throws Exception {
        ModelExportEntity entity = buildEntity("m1", "https://${_env.plugin_url_params.HOST}/v1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1");

        verify(modelServiceManager).createModelServiceForImport(any());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testEnvVarPlaceholderInvalid() throws Exception {
        ModelExportEntity entity = buildEntity("m1", "https://${evil.var}/x");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1");

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getFailedLen());
    }

    @Test
    void testMaskedAuthExport() throws Exception {
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(new ProviderAuthMetadata().setProviderId("p1").setAuthInfo("secret-cipher"));
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        entity.setProviderMetadata(pm);

        // 通过 buildLine 路径走 service.exportModels 验证 maskProviderAuth 生效
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));

        // maskProviderAuth 把 ProviderAuthMetadata.authInfo 置空，密文不外泄
        assertEquals(" ", pm.getProviderAuthMetadata().getAuthInfo());
        String content = new String(jsonl, StandardCharsets.UTF_8);
        assertFalse(content.contains("secret-cipher"), "auth_info must be masked, got: " + content);
        // 契约：导出 JSONL 不再含 signature 字段
        assertFalse(content.contains("\"signature\""), "export must not contain signature field, got: " + content);
    }

    // ============================== previewImport 路径 ==============================

    @Test
    void testPreviewImport_normalWithConflict() throws Exception {
        // 用单行 JSONL（一个 entity 装两个同 provider 模型）覆盖冲突预检路径。
        ModelServiceData m1 = new ModelServiceData();
        m1.setId("m1"); m1.setServiceName("svc-m1"); m1.setProviderId("p1"); m1.setApiUrl("https://x.com/v1");
        ModelServiceData m2 = new ModelServiceData();
        m2.setId("m2"); m2.setServiceName("svc-m2"); m2.setProviderId("p1"); m2.setApiUrl("https://y.com/v2");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(m1, m2)));
        entity.setProviderMetadata(null);
        // m1 无冲突，m2 同名冲突
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m1"), any()))
            .thenReturn(Collections.emptyList());
        ModelServiceBase existing = new ModelServiceBase().setId("existing").setServiceName("svc-m2").setProviderId("p1");
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m2"), any()))
            .thenReturn(List.of(existing));

        byte[] jsonl = toJsonlLine(entity);
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(2, rsp.getTotalCount());
        assertEquals(1, rsp.getConflictCount());
        // 预检不落库
        verify(modelServiceManager, never()).createModelServiceForImport(any());
        verify(modelServiceManager, never()).deleteModelService(any());
        ModelImportPreviewItem m2Item = rsp.getItems().get(1);
        assertTrue(m2Item.getConflict());
        assertTrue(m2Item.getLineValid());
        assertTrue(m2Item.getApiUrlValid());
    }

    @Test
    void testPreviewImport_urlInvalid() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://${evil.var}/x")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getTotalCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        // 行合法（解析通过）但 apiUrl/占位符校验失败
        assertTrue(item.getLineValid());
        // checkUrl 对含 ${...} 占位符的 URL 放通(enableUrlCheck=false 亦放通)→ apiUrlValid=true；
        // 仅 validateEnvVarPlaceholders 失败 → envVarValid=false
        assertTrue(item.getApiUrlValid());
        assertFalse(item.getEnvVarValid());
        assertNotNull(item.getDetail());
    }

    // ============================== 冲突说明（detectConflict 三情况 + 硬校验合并） ==============================

    @Test
    void testPreviewImport_noConflict_detailIsNull() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryById(any())).thenReturn(null);

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getTotalCount());
        assertEquals(0, rsp.getConflictCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertFalse(item.getConflict());
        // 无冲突且无硬校验失败 → detail=null（前端展示"无"）
        assertNull(item.getDetail());
        assertTrue(item.getLineValid());
        assertTrue(item.getApiUrlValid());
        assertTrue(item.getEnvVarValid());
    }

    @Test
    void testPreviewImport_conflictByName_resolvesProviderName() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        // 情况1：本空间同供应商+同服务名命中
        ModelServiceBase existing = new ModelServiceBase().setId("old").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m1"), eq("p1")))
            .thenReturn(List.of(existing));
        // 供应商名查询返回显示名（getLogosAndProviderNamesByProviderIds 覆盖平台+用户两类供应商）
        ModelServiceProviderDetail provider = new ModelServiceProviderDetail();
        provider.setProviderName("华为云");
        provider.setProviderNameEn("HuaweiCloud");
        when(modelServiceMapper.getLogosAndProviderNamesByProviderIds(any()))
            .thenReturn(List.of(provider));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getConflictCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertTrue(item.getConflict());
        assertNotNull(item.getDetail());
        // 冲突说明须含供应商显示名 + 服务名
        assertTrue(item.getDetail().contains("华为云"), "detail should contain provider display name");
        assertTrue(item.getDetail().contains("svc-m1"), "detail should contain service name");
    }

    @Test
    void testPreviewImport_conflictByName_providerNotFound_fallsBackToProviderId() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        ModelServiceBase existing = new ModelServiceBase().setId("old").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));
        // 供应商名查不到 → 回退显示 providerId
        when(modelServiceMapper.getLogosAndProviderNamesByProviderIds(any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertTrue(item.getConflict());
        assertNotNull(item.getDetail());
        assertTrue(item.getDetail().contains("p1"), "fallback to providerId when name unresolved");
    }

    @Test
    void testPreviewImport_conflictBySameScopeModelId() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        // queryByName 未命中（无同名/同供应商）
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 情况2：queryById 命中同 scope（同 projectId + 同 workspaceId）
        ModelServiceBase existing = new ModelServiceBase().setId("m1")
            .setProjectId("proj").setWorkspaceId("ws");
        when(modelServiceMapper.queryById(eq("m1"))).thenReturn(existing);

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getConflictCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertTrue(item.getConflict());
        assertNotNull(item.getDetail());
        assertTrue(item.getDetail().contains("本空间下已存在相同的模型ID"), "same-scope id conflict");
        assertTrue(item.getDetail().contains("m1"), "detail should contain model id");
    }

    @Test
    void testPreviewImport_conflictByCrossScopeModelId() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 情况3：queryById 命中不同 scope（不同 workspaceId）→ 跨空间冲突，按用户决策不显示具体空间名
        ModelServiceBase existing = new ModelServiceBase().setId("m1")
            .setProjectId("proj").setWorkspaceId("other-ws");
        when(modelServiceMapper.queryById(eq("m1"))).thenReturn(existing);

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getConflictCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertTrue(item.getConflict());
        assertNotNull(item.getDetail());
        assertTrue(item.getDetail().contains("其他工作空间已存在相同的模型ID"), "cross-scope id conflict");
        // 不泄漏具体空间名
        assertFalse(item.getDetail().contains("other-ws"), "must not leak workspace name");
    }

    @Test
    void testPreviewImport_conflictMergedWithHardCheckFailure() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://${evil.var}/x")));
        // 情况1冲突 + 非法占位符硬校验失败 → detail 拼接两者
        ModelServiceBase existing = new ModelServiceBase().setId("old").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));
        when(modelServiceMapper.getLogosAndProviderNamesByProviderIds(any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getConflictCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertTrue(item.getConflict());
        // 既有冲突说明又有硬校验失败说明，用 "；" 分隔（冲突在前、硬校验在后）
        assertNotNull(item.getDetail());
        assertTrue(item.getDetail().contains("本空间下供应商"), "conflict desc present");
        assertTrue(item.getDetail().contains("；"), "merged with hard-check desc by separator");
        assertFalse(item.getEnvVarValid(), "env var hard-check failed");
    }

    @Test
    void testPreviewImport_blankProviderId_noFalseConflict() throws Exception {
        // MEDIUM-1 回归：providerId 空值时 previewOneModel 不应跑 detectConflict（与导入侧 validateModel
        // 前置一致），避免 queryByName 退化为 serviceName-only 误报冲突、且空 providerId 回退进说明括号。
        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId(null); // 空 providerId
        model.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        // 带 provider_metadata → 非 model-only 文件，绕过 targetProviderId 校验，保留模型 null providerId 以测试 blank-provider 逻辑
        ProviderExportMetadata pm = new ProviderExportMetadata();
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p1");
        pm.setModelServiceProviderMetadata(provider);
        entity.setProviderMetadata(pm);
        byte[] jsonl = toJsonlLine(entity);

        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl));

        assertEquals(1, rsp.getTotalCount());
        assertEquals(0, rsp.getConflictCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertFalse(item.getConflict(), "blank providerId must not trigger conflict detection");
        assertNotNull(item.getDetail());
        assertTrue(item.getDetail().contains("blank providerId"));
        // detectConflict 未跑 → queryByName / queryById 均不应被调用（无误报冲突、无空括号说明）
        verify(modelServiceMapper, never()).queryByName(any(), any(), any(), any());
        verify(modelServiceMapper, never()).queryById(any());
    }

    // ============================== 导入落库边界分支 ==============================

    @Test
    void testImport_formatInvalidLine() {
        byte[] jsonl = ("{\"import_type\":\"model_service\",\"payload\":\"not-json\"}\n").getBytes(StandardCharsets.UTF_8);

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "p1");

        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testImport_emptyFile() {
        // 全空/空白行文件 → 整文件无合法模型行，顶层 fast-fail 抛 400
        byte[] jsonl = "\n  \n".getBytes(StandardCharsets.UTF_8);

        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testImport_multipleLines_rejectedAsSingleLineRequired() throws Exception {
        // R5b：模型导出文件为单行 JSONL（每行一个完整 JSON 对象，一个文件只包含一行）。
        // 若包含多有效行（通常是被文本编辑器 pretty-print），直接顶层抛错，不再逐行处理。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenAnswer(inv -> {
                List<String> ids = inv.getArgument(2);
                return List.of(buildEntity(ids.get(0), "https://x.com/v1?m=" + ids.get(0)));
            });

        byte[] l1 = service.exportModels("proj", "ws", List.of("m1"));
        byte[] l2 = service.exportModels("proj", "ws", List.of("m2"));
        byte[] jsonl = (new String(l1, StandardCharsets.UTF_8) + new String(l2, StandardCharsets.UTF_8))
            .getBytes(StandardCharsets.UTF_8);

        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "message must hint single-line JSONL, got: " + e.getMessage());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testImport_multipleModelsInLine() throws Exception {
        // 一行 JSONL 含两个模型 → 均导入成功
        ModelServiceData m1 = new ModelServiceData();
        m1.setId("m1");
        m1.setServiceName("svc-m1");
        m1.setProviderId("p1");
        m1.setApiUrl("https://x.com/v1");
        ModelServiceData m2 = new ModelServiceData();
        m2.setId("m2");
        m2.setServiceName("svc-m2");
        m2.setProviderId("p1");
        m2.setApiUrl("https://y.com/v2");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(m1, m2)));
        entity.setProviderMetadata(null);
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1");

        assertEquals(2, rsp.getSucceedLen());
        verify(modelServiceManager, times(2)).createModelServiceForImport(any());
    }

    @Test
    void testImport_nullPayload() {
        // payload 缺失（`{import_type:model_service}`）→ failedRes
        byte[] jsonl = ("{\"import_type\":\"model_service\"}\n").getBytes(StandardCharsets.UTF_8);

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1");

        assertEquals(1, rsp.getFailedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testUpsertProviderMetadata_insertIfMissing() throws Exception {
        // 目标环境无该 provider 元数据 → insert 被调，且 model.authMetadataId 重链到新插入记录的 ID
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = buildEntityWithProvider("m1", "https://x.com/v1", "p1");
        entity.setProviderMetadata(pm);
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP");

        // round-trip 反序列化产生新实例，用 captor 捕获实际插入对象并校验 re-scope + 脱敏
        ArgumentCaptor<ProviderAuthMetadata> captor = ArgumentCaptor.forClass(ProviderAuthMetadata.class);
        verify(providerAuthMetadataMapper).insert(captor.capture());
        ProviderAuthMetadata inserted = captor.getValue();
        assertEquals("p1", inserted.getProviderId());
        assertEquals("proj", inserted.getProjectId());
        assertEquals("ws", inserted.getWorkspaceId());
        assertEquals(" ", inserted.getAuthInfo());
    }

    @Test
    void testUpsertProviderMetadata_alreadyExists() throws Exception {
        // 目标工作空间已有该 provider 元数据(按作用域查命中) → 跳过 insert，但 model.authMetadataId 重链到已有记录的 ID
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = buildEntityWithProvider("m1", "https://x.com/v1", "p1");
        entity.setProviderMetadata(pm);
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        // 目标工作空间已存在该 provider 的 auth metadata，ID="target-meta-id"
        ProviderAuthMetadata existingMeta = new ProviderAuthMetadata();
        existingMeta.setId("target-meta-id");
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(List.of(existingMeta));

        byte[] jsonl = toJsonlLine(entity);
        service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP");

        verify(providerAuthMetadataMapper, never()).insert(any(ProviderAuthMetadata.class));
        // model.authMetadataId 被重链到目标环境的 ID（非源环境旧值）
        ArgumentCaptor<ModelServiceBase> modelCaptor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(modelCaptor.capture());
        assertEquals("target-meta-id", modelCaptor.getValue().getAuthMetadataId());
    }

    @Test
    void testLicenseCheck_invoked() throws Exception {
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1");

        // importModels 入口须做 license 校验
        verify(licenseCtrlService).canAccessIntegrationModel();
    }

    @Test
    void testCreateModelServiceInfraException_recordedAsFailed_not500() throws Exception {
        // HIGH-3 回归：无冲突路径的 DB insert 抛非 AgentStudioException 时，
        // 兜底 catch 转 failed，不抛异常中断整批。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 模拟 DB insert 异常（createModelServiceForImport 抛出 → importOneModel catch(Exception)）
        doThrow(new RuntimeException("DB insert duplicate key")).when(modelServiceManager)
            .createModelServiceForImport(any());

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "p1");

        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
    }

    @Test
    void testUpsertProviderMetadataFailure_doesNotAbortImport() throws Exception {
        // HIGH-2 回归：upsertProviderMetadata 抛异常时（best-effort），模型导入不被中断。
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = buildEntityWithProvider("m1", "https://x.com/v1", "p1");
        entity.setProviderMetadata(pm);
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByIds(any()))
            .thenThrow(new RuntimeException("DB connection lost"));

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP");

        // provider 元数据失败不阻断，模型本身仍导入成功
        assertEquals(1, rsp.getSucceedLen());
        verify(modelServiceManager).createModelServiceForImport(any());
    }

    // ============================== HIGH-4 回归：COVER 事务化 + 缓存补偿 ==============================

    @Test
    void testCover_dbFailure_recordsFailed_noCacheSync() throws Exception {
        // HIGH-4 回归：coverModelService(DB 事务)失败时，旧记录由事务回滚保护，
        // 且不触发缓存同步（DB 未提交，写缓存无意义）。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] jsonl = toJsonlLine(entity);
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));
        doThrow(new RuntimeException("DB insert duplicate key")).when(modelServiceManager)
            .coverModelService(any(), any());

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "COVER", "p1");

        // DB 事务失败 → 记 failed（如实反映"什么都没改"，旧记录完好），缓存同步未触发
        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
        verify(modelServiceManager, never()).removeModelCaches(any());
        verify(modelServiceManager, never()).saveModelInfoToObsAndRedis(any(), any(), any());
    }

    @Test
    void testCover_success_clearsOldCacheBeforeWritingNew() throws Exception {
        // HIGH-4 回归：缓存同步顺序须"先清旧(existingId)后写新(importId)"，
        // 避免同文件二次导入同空间时 existingId==importId 自删（先写后清会把刚写的缓存删掉）。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] jsonl = toJsonlLine(entity);
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));

        service.importModels("proj", "ws", toMultipartFile(jsonl), "COVER", "p1");

        // 顺序校验：coverModelService(DB 提交) → removeModelCaches(清旧) → saveModelInfoToObsAndRedis(写新)
        InOrder inOrder = inOrder(modelServiceManager);
        inOrder.verify(modelServiceManager).coverModelService(any(), eq("old-id"));
        inOrder.verify(modelServiceManager).removeModelCaches("old-id");
        inOrder.verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
    }

    @Test
    void testCover_cacheWriteFails_doesNotFailImport() throws Exception {
        // HIGH-4 回归：coverModelService(DB)已提交后，缓存写失败不致导入失败（best-effort，DB 为 source of truth）。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] jsonl = toJsonlLine(entity);
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));
        doThrow(new RuntimeException("OBS putObject failed")).when(modelServiceManager)
            .saveModelInfoToObsAndRedis(any(), any(), any());

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "COVER", "p1");

        // DB 已提交，缓存写失败仅告警，导入仍成功；旧缓存清理仍被调用（best-effort 各自独立 try/catch）
        assertEquals(1, rsp.getSucceedLen());
        assertEquals(0, rsp.getFailedLen());
        verify(modelServiceManager).removeModelCaches("old-id");
    }

    // ============================== Finding 1 回归：无冲突路径缓存 best-effort ==============================

    @Test
    void testNoConflict_cacheWriteFails_doesNotFailImport() throws Exception {
        // Finding 1 回归：无冲突路径缓存写失败时（DB 已提交），导入仍成功——与 COVER 路径语义一致。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] jsonl = toJsonlLine(entity);
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        doThrow(new RuntimeException("OBS putObject failed")).when(modelServiceManager)
            .saveModelInfoToObsAndRedis(any(), any(), any());

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "p1");

        // DB insert(createModelServiceForImport)已提交，缓存写失败被 syncCachesForCreate best-effort 吞掉 → 仍成功
        assertEquals(1, rsp.getSucceedLen());
        assertEquals(0, rsp.getFailedLen());
        verify(modelServiceManager).createModelServiceForImport(any());
        verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
    }

    // ============================== Finding 2 回归：预检 null-payload 不丢失 ==============================

    @Test
    void testPreviewImport_nullPayloadShown() {
        // Finding 2 回归：payload 缺失时，预检须展示该行（与导入报 FAILED 对齐），
        // lineValid=true（解析通过，import_type 对），detail="payload is missing"。
        byte[] jsonl = ("{\"import_type\":\"model_service\"}\n").getBytes(StandardCharsets.UTF_8);
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "p1");

        assertEquals(1, rsp.getTotalCount());
        assertEquals(1, rsp.getItems().size());
        assertTrue(rsp.getItems().get(0).getLineValid());
        assertEquals("payload is missing", rsp.getItems().get(0).getDetail());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== 新增契约：line_valid 行级硬错误 ==============================

    @Test
    void testPreview_lineFailure_setsLineValidFalse() {
        // 构造 JSON 非法行（payload 不是合法对象）→ preview 返回 item.line_valid=false 并展示错误原因。
        String badLine = "{\"import_type\":\"model_service\",\"payload\":{broken-json!!!}}\n";
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws",
            toMultipartFile(badLine.getBytes(StandardCharsets.UTF_8)), "p1");

        assertEquals(1, rsp.getTotalCount());
        assertEquals(1, rsp.getItems().size());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertFalse(item.getLineValid(), "parse failure must set line_valid=false");
        assertNotNull(item.getDetail());
    }

    @Test
    void testImport_lineWithCipherNameField_parsesButIsIgnored() throws Exception {
        // 契约：外部文件 payload.provider_auth_data 若带 cipher_name 字段（旧加密环境遗留），
        // 因 @JsonIgnoreProperties(ignoreUnknown=true) 不抛 UnrecognizedPropertyException，
        // 行正常解析并导入（cipher 适配检测已删除，任何 cipher_name 都被静默忽略）。
        String line = "{\"import_type\":\"model_service\",\"payload\":{\"model_metadata\":"
            + "[{\"id\":\"m1\",\"service_name\":\"svc-m1\",\"provider_id\":\"p1\",\"api_url\":\"https://x.com/v1\"}],"
            + "\"provider_metadata\":{\"model_service_provider_metadata\":{\"id\":\"p1\"},"
            + "\"provider_auth_metadata\":{\"provider_id\":\"p1\",\"auth_info\":\" \"},"
            + "\"provider_auth_data\":{\"cipher_name\":\"AES_GCM\",\"auth_info\":\" \"}"
            + "}}}\n";
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        ImportRsp rsp = service.importModels("proj", "ws",
            toMultipartFile(line.getBytes(StandardCharsets.UTF_8), "a.jsonl"), "SKIP");

        assertEquals(1, rsp.getSucceedLen(), "cipher_name field should be ignored (unknown property), line imported");
        assertEquals(0, rsp.getFailedLen());
        verify(modelServiceManager).createModelServiceForImport(any());
    }

    // ============================== R3-1 回归：auth 作用域化 + MASKED 不插入 auth_data ==============================

    @Test
    void testAuthMetadata_scopedQuery_insertsMetadata_skipsBlankAuthData() throws Exception {
        // R3-1 回归：旧实现按全局 PROVIDER_ID 查，目标环境任一工作空间有同 provider 即误判已存在→漏插。
        // 修复后按 (providerId, projectId, workspaceId) 作用域查，目标工作空间无则插入。
        //
        // 注：MASKED 导出路径下 authInfo 是 " " 占位符，upsertAuthData 会 skip auth_data insert（符合"脱敏导入
        // 需用户重填密钥"语义，同时避免详情页 500）。故本测只验证 auth_metadata 插入 + 不插入 auth_data。
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setId("exported-meta-id");
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderAuthData authData = new ProviderAuthData();
        authData.setProviderId("p1");
        authData.setAuthInfo(" "); // MASKED 占位符 → auth_data insert 被 skip
        authData.setAuthMetadataId("old-source-meta-id"); // 源环境旧值，因 authData 不插入此值无影响
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);
        ModelExportEntity entity = buildEntityWithProvider("m1", "https://x.com/v1", "p1");
        entity.setProviderMetadata(pm);
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        // 目标工作空间无 auth metadata（即使其他工作空间有同 providerId，作用域查也返回空→插入）
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(providerAuthDataMapper.selectByProviderId(any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP");

        // auth metadata 插入（未因跨工作空间误判跳过）
        verify(providerAuthMetadataMapper).insert(any(ProviderAuthMetadata.class));
        // MASKED 脱敏导入：auth_data 不应 insert（authInfo 为空格占位符，需用户在 UI 补填密钥）
        verify(providerAuthDataMapper, never()).insert(any(ProviderAuthData.class));
    }

    // ============================== R3-2 回归：跨工作空间 COPY 时 auth_metadata id UUID 再生，避免 DuplicateKey 孤儿行 ==============================

    @Test
    void testCrossWorkspaceCopy_regeneratesAuthMetadataIdAndRemapsModelFk() throws Exception {
        // 复现 0729 残留供应商 bug：第二次导入到不同工作空间时，源 id 在其他空间已存在 → 必须生成新 UUID，
        // 否则 t_provider_auth_metadata.PRIMARY 冲突，DuplicateKeyException 被 catch 吞掉，
        // t_model_service.auth_metadata_id 保留源值（悬空 FK），模型在 UI 不可见但删除供应商时全局 COUNT(*)
        // 统计到 → 1042 死锁。
        //
        // 注意：MASKED 导出模式下 authInfo 被置为 " "，upsertAuthData 会 skip auth_data insert（符合"脱敏导入
        // 需用户重填密钥"的产品语义）——故本测只验证 auth_metadata id 再生 + model FK 正确重链。
        String srcMetaId = "exported-meta-id";
        String srcProviderId = "p1";
        String srcModelId = "m1";

        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setId(srcMetaId);
        authMeta.setProviderId(srcProviderId);
        authMeta.setAuthInfo(" ");
        ProviderAuthData authData = new ProviderAuthData();
        authData.setId("exported-data-id");
        authData.setProviderId(srcProviderId);
        authData.setAuthInfo(" ");
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId(srcProviderId);
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);

        ModelServiceData model = new ModelServiceData();
        model.setId(srcModelId);
        model.setServiceName("svc-m1");
        model.setProviderId(srcProviderId);
        model.setApiUrl("https://x.com/v1");
        model.setAuthMetadataId(srcMetaId);

        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);

        // 目标工作空间内无同名/同 provider 冲突（queryByName 空）
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryById(any())).thenReturn(null);

        // provider 作用域内不存在，但全局 selectByIds 命中其他空间 → COPY 分支
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        ModelServiceProvider otherWsProvider = new ModelServiceProvider();
        otherWsProvider.setId(srcProviderId);
        otherWsProvider.setProjectId("other-proj");
        otherWsProvider.setWorkspaceId("other-ws");
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(List.of(otherWsProvider));

        // authMetadata 作用域查无，但全局 selectById 命中其他空间 → 必须生成新 UUID
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        ProviderAuthMetadata otherWsMeta = new ProviderAuthMetadata();
        otherWsMeta.setId(srcMetaId);
        when(providerAuthMetadataMapper.selectById(eq(srcMetaId))).thenReturn(otherWsMeta);

        when(providerAuthDataMapper.selectByProviderId(any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = toJsonlLine(entity);
        service.importModels("proj", "ws-new", toMultipartFile(jsonl), "COVER");

        // 断言 1：provider 被 COPY（生成新 id 插入，而非源 id）
        ArgumentCaptor<ModelServiceProvider> provCaptor = ArgumentCaptor.forClass(ModelServiceProvider.class);
        verify(userModelServiceProviderMapper).insert(provCaptor.capture());
        String insertedProviderId = provCaptor.getValue().getId();
        assertNotEquals("provider id must be regenerated on cross-ws COPY", srcProviderId, insertedProviderId);
        assertNotNull(insertedProviderId);

        // 断言 2：auth_metadata 被 COPY（生成新 id 插入，避免 DuplicateKey 孤儿行）
        ArgumentCaptor<ProviderAuthMetadata> metaCaptor = ArgumentCaptor.forClass(ProviderAuthMetadata.class);
        verify(providerAuthMetadataMapper).insert(metaCaptor.capture());
        ProviderAuthMetadata insertedMeta = metaCaptor.getValue();
        assertNotEquals("auth_metadata id must be regenerated on cross-ws COPY", srcMetaId, insertedMeta.getId());
        assertEquals(insertedProviderId, insertedMeta.getProviderId());

        // 断言 3：model 成功 insert，且 authMetadataId 指向新插入的 metadata id（非源空间悬空 UUID），
        // providerId 也已重映射到新插入的 provider id。
        ArgumentCaptor<ModelServiceBase> modelCaptor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(modelCaptor.capture());
        ModelServiceBase insertedModel = modelCaptor.getValue();
        assertEquals(insertedProviderId, insertedModel.getProviderId(),
            "model.providerId must be remapped to the new provider id on cross-ws COPY");
        assertEquals(insertedMeta.getId(), insertedModel.getAuthMetadataId(),
            "model.authMetadataId must point to the newly inserted metadata (not dangling source UUID)");
    }

    @Test
    void testUpsertProvider_sameNameInTarget_reusesExistingProviderId_doesNotInsertOrUpdate() throws Exception {
        // 新需求：目标空间已有同 provider name（不同 id）的供应商 → 复用其 id
        String srcProviderId = "p-src";
        String existingProviderId = "p-existing";
        String providerName = "阿里";

        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId(srcProviderId);
        provider.setProviderName(providerName);
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        pm.setProviderAuthMetadata(null);

        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId(srcProviderId);
        model.setApiUrl("https://x.com/v1");

        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);

        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryById(any())).thenReturn(null);

        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        ModelServiceProvider existingProvider = new ModelServiceProvider();
        existingProvider.setId(existingProviderId);
        existingProvider.setProviderName(providerName);
        when(userModelServiceProviderMapper.selectUserDataByName(any(), any(), eq(providerName)))
            .thenReturn(List.of(existingProvider));

        byte[] jsonl = toJsonlLine(entity);
        service.importModels("proj", "ws", toMultipartFile(jsonl), "COVER");

        verify(userModelServiceProviderMapper, never()).insert(any());

        ArgumentCaptor<ModelServiceBase> modelCaptor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(modelCaptor.capture());
        assertEquals(existingProviderId, modelCaptor.getValue().getProviderId(),
            "model.providerId must be remapped to the reused existing provider id (not the source id)");
    }

    @Test
    void testImport_whenAuthMetadataUpsertFails_modelAuthMetadataIdIsSetToNull_notDanglingSource() throws Exception {
        // defense-in-depth：metadata 插入失败 → 模型 authMetadataId 显式置 null，不能保留源 UUID
        String srcMetaId = "src-meta-id";
        String srcProviderId = "p1";

        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setId(srcMetaId);
        authMeta.setProviderId(srcProviderId);
        authMeta.setAuthInfo(" ");
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId(srcProviderId);
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        pm.setProviderAuthMetadata(authMeta);

        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId(srcProviderId);
        model.setApiUrl("https://x.com/v1");
        model.setAuthMetadataId(srcMetaId);

        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);

        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryById(any())).thenReturn(null);
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectById(any())).thenReturn(null);
        org.springframework.dao.DuplicateKeyException dke =
            new org.springframework.dao.DuplicateKeyException("simulated auth_metadata PK conflict");
        doThrow(dke).when(providerAuthMetadataMapper).insert(any(ProviderAuthMetadata.class));
        doNothing().when(modelServiceManager).createModelServiceForImport(any(ModelServiceBase.class));

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "COVER");

        assertEquals(1, rsp.getSucceedLen(), "model should still be inserted best-effort");
        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        assertNull(captor.getValue().getAuthMetadataId(),
            "when metadata upsert fails, model.authMetadataId must be null, not the dangling source UUID");
    }

    // ============================== R3-3 回归：providerId 非空校验 ==============================

    @Test
    void testImport_blankProviderId_rejected() throws Exception {
        // R3-3 回归：providerId 空值会使 queryByName 退化为 serviceName-only → 拒绝导入。
        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId(null);
        model.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        // 带 provider_metadata → 非 model-only 文件，绕过 targetProviderId 校验，保留模型 null providerId 以测试 blank-provider 逻辑
        ProviderExportMetadata pm = new ProviderExportMetadata();
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p1");
        pm.setModelServiceProviderMetadata(provider);
        entity.setProviderMetadata(pm);

        byte[] jsonl = toJsonlLine(entity);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP");

        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== 只导模型 / 按供应商导出（R4：两种模式） ==============================

    @Test
    void testExportModelOnly_noProviderMetadata() {
        // R4：includeProvider=false → 4参 buildModelExportEntity 被调，payload.provider_metadata 为 null
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        String content = new String(jsonl, StandardCharsets.UTF_8);

        assertTrue(content.contains("\"provider_metadata\":null"));
        verify(modelServiceMgmtService).buildModelExportEntity(any(), any(), any(), eq(false));
        verify(modelServiceMgmtService, never()).batchGetProviderExportMetadata(any(), any(), any());
        // 契约：导出不包含 signature
        assertFalse(content.contains("\"signature\""), "model-only export must not contain signature");
    }

    @Test
    void testExportByProvider_resolvesModelIdsViaQueryByProviders() {
        // R4：卡片入口 exportModelsByProvider → queryByProviders 取该供应商下模型
        ModelServiceBase m1 = new ModelServiceData();
        m1.setId("m1");
        ModelServiceBase m2 = new ModelServiceData();
        m2.setId("m2");
        ModelServiceProvider p = new ModelServiceProvider();
        p.setId("p1");
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(List.of(p));
        when(modelServiceMapper.queryByProviders(any(), any(), eq("p1")))
            .thenReturn(List.of(m1, m2));
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModelsByProvider("proj", "ws", "p1");

        verify(modelServiceMapper).queryByProviders(any(), any(), eq("p1"));
        ArgumentCaptor<List<String>> idsCaptor = ArgumentCaptor.forClass(List.class);
        verify(modelServiceMgmtService).buildModelExportEntity(any(), any(), idsCaptor.capture());
        assertTrue(idsCaptor.getValue().containsAll(List.of("m1", "m2")));
        assertTrue(new String(jsonl, StandardCharsets.UTF_8).contains("svc-m1"));
    }

    @Test
    void testImportModelOnly_redirectsProviderId() throws Exception {
        // R4：model-only 文件（provider_metadata=null）+ targetProviderId → 模型 providerId 重定向到 target
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        ProviderAuthMetadata existingMeta = new ProviderAuthMetadata();
        existingMeta.setId("target-meta");
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), eq("target-provider")))
            .thenReturn(List.of(existingMeta));
        when(modelServiceMapper.queryByName(any(), any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "target-provider");

        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        assertEquals("target-provider", captor.getValue().getProviderId());
        assertEquals("target-meta", captor.getValue().getAuthMetadataId());
        verify(userModelServiceProviderMapper, never()).insert(any());
        verify(providerAuthMetadataMapper, never()).insert(any());
        verify(providerAuthDataMapper, never()).insert(any());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testImportModelOnly_conflictUsesRedirectedProviderId() throws Exception {
        // R4：model-only 导入冲突判定用重定向后的 providerId
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryByName(any(), any(), any(), eq("target-provider")))
            .thenReturn(List.of(new ModelServiceData()));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "target-provider");

        verify(modelServiceMapper).queryByName(any(), any(), any(), eq("target-provider"));
        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getSkippedLen());
        assertEquals(0, rsp.getFailedLen());
    }

    @Test
    void testPreviewModelOnly_redirectsProviderId_shownInItem() throws Exception {
        // R4：model-only 预检传 target → 预检项 provider_id 显示重定向值
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "target-provider");

        assertEquals(1, rsp.getItems().size());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertEquals("target-provider", item.getProviderId());
        assertEquals(Boolean.FALSE, item.getConflict());
        assertTrue(item.getApiUrlValid());
        assertTrue(item.getEnvVarValid());
        assertTrue(item.getLineValid());
    }

    @Test
    void testImportModelOnly_noTarget_throws() throws Exception {
        // R4：model-only 文件（无 provider_metadata）+ targetProviderId 缺失 → 顶层抛 400，避免模型以源 providerId 落库成孤儿。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testPreviewModelOnly_noTarget_throws() throws Exception {
        // R4：预检与导入一致：只导模型文件缺少 targetProviderId 直接 400。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.previewImport("proj", "ws", toMultipartFile(jsonl), null));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
    }

    @Test
    void testImport_providerPlusModelFile_withTarget_ignoresTargetForProviderLines() throws Exception {
        // R4：provider+模型文件（provider_metadata 非空）+ target 非空 → 仍 upsert 文件自带 provider
        ModelExportEntity entity = buildEntityWithProvider("m1", "https://x.com/v1", "p1");
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), true);
        service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP", "target-provider");

        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        assertEquals("p1", captor.getValue().getProviderId());
        verify(userModelServiceProviderMapper, atLeastOnce()).selectByIds(any());
    }

    @Test
    void testExportByProvider_noModels_exportsProviderShell() {
        // 修复「空供应商导出空文件/抛异常无法再导入」：queryByProviders 返回空 → 导出单行壳
        ModelServiceProvider p = new ModelServiceProvider();
        p.setId("p-empty");
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(List.of(p));
        when(modelServiceMapper.queryByProviders(any(), any(), eq("p-empty")))
            .thenReturn(Collections.emptyList());
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(new ProviderAuthMetadata());
        when(modelServiceMgmtService.getProviderExportMetadataByIds(any()))
            .thenReturn(Collections.singletonMap("p-empty", pm));

        byte[] jsonl = service.exportModelsByProvider("proj", "ws", "p-empty");
        String content = new String(jsonl, StandardCharsets.UTF_8);

        assertEquals(1, content.trim().split("\n").length,
            "empty provider should export exactly one line, got: " + content);
        assertTrue(content.contains("\"model_metadata\":[]"),
            "empty provider must export empty model_metadata, got: " + content);
        verify(modelServiceMgmtService).getProviderExportMetadataByIds(any());
        verify(modelServiceMgmtService, never()).buildModelExportEntity(any(), any(), any());
        assertFalse(content.contains("\"signature\""), "provider-shell export must not contain signature");
    }

    @Test
    void testExportByProvider_noModels_providerNotFound_throws() {
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.exportModelsByProvider("proj", "ws", "p-missing"));
        assertEquals(StudioError.MD_PROVIDER_NOT_EXIST, e.getErrorCode());
    }

    @Test
    void testPreview_emptyProviderShell_producesOneItem() {
        // 空供应商壳预检：须产出 1 条供应商壳条目（totalCount=1），lineValid=true 放行导入。
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p-shell");
        provider.setProviderName("shell-provider");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(List.of(provider));
        when(modelServiceMapper.queryByProviders(any(), any(), eq("p-shell")))
            .thenReturn(Collections.emptyList());
        when(modelServiceMgmtService.getProviderExportMetadataByIds(any()))
            .thenReturn(Collections.singletonMap("p-shell", pm));

        byte[] jsonl = service.exportModelsByProvider("proj", "ws", "p-shell");
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl));

        assertEquals(1, rsp.getTotalCount(), "empty provider shell should produce 1 preview item");
        assertEquals(1, rsp.getItems().size());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertEquals(Boolean.TRUE, item.getLineValid(), "empty shell line should be valid");
        assertEquals("p-shell", item.getProviderId());
        assertEquals("shell-provider", item.getServiceName());
        assertNull(item.getDetail(), "non-conflicting shell should have null detail (renders 无)");
    }

    @Test
    void testImport_emptyProviderShell_reportsSuccess() {
        // 空供应商壳导入：upsertProviderMetadata 建出供应商（0 模型），须产出 1 条 SUCCESS
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p-shell");
        provider.setProviderName("shell-provider");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(List.of(provider));
        when(modelServiceMapper.queryByProviders(any(), any(), eq("p-shell")))
            .thenReturn(Collections.emptyList());
        when(modelServiceMgmtService.getProviderExportMetadataByIds(any()))
            .thenReturn(Collections.singletonMap("p-shell", pm));
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModelsByProvider("proj", "ws", "p-shell");
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            "SKIP");

        assertEquals(1, rsp.getSucceedLen(), "empty provider shell should report 1 success");
        assertEquals(0, rsp.getFailedLen());
        ImportRes res = rsp.getImportList().get(0);
        assertEquals("SUCCESS", res.getStatus());
        assertEquals("p-shell", res.getId());
        assertEquals("shell-provider", res.getName());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testExport_setsImportType_modelService() {
        // R5：导出端写入 import_type=model_service。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        String content = new String(jsonl, StandardCharsets.UTF_8);

        assertTrue(content.contains("\"import_type\":\"model_service\""),
            "export line must carry import_type=model_service, got: " + content);
        assertFalse(content.contains("\"signature\""), "export must not contain signature field");
    }

    @Test
    void testImport_mixedWorkflowAndModelLines_rejectedAsMultiLine() throws Exception {
        // R5b：单行 JSONL 校验先于逐行处理——workflow 行 + model_service 行的混合文件被顶层拒绝，
        // 不再逐行"部分成功"。单文件纯 workflow 走 fast-fail（见 testImport_fileWithoutAnyModelLine_throwsTopLevel）。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] modelLineBytes = toJsonlLine(entity);
        String workflowLine = "{\"import_type\":\"workflow\",\"dsl\":{},\"metadata\":{}}\n";
        String mixedContent = workflowLine + new String(modelLineBytes, StandardCharsets.UTF_8);

        AgentStudioException e = assertThrows(AgentStudioException.class, () -> service.importModels("proj", "ws",
            toMultipartFile(mixedContent.getBytes(StandardCharsets.UTF_8)),
            "SKIP", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "message must hint single-line, got: " + e.getMessage());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== A. readLines() 前置文件校验 ==============================

    @Test
    void testImport_emptyMultipartFile_throws400() {
        MultipartFile file = toMultipartFile(new byte[0], "a.jsonl", true);
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("上传文件不能为空"));
    }

    @Test
    void testImport_nullBytesMultipartFile_throws400() {
        MultipartFile file = toMultipartFile(null, "a.jsonl", true);
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("上传文件不能为空"));
    }

    @Test
    void testImport_wrongExtension_txt_throws400() {
        MultipartFile file = toMultipartFile("hello".getBytes(StandardCharsets.UTF_8), "a.txt");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains(".jsonl"), "reason should mention .jsonl");
    }

    @Test
    void testImport_nullFilename_throws400() {
        MultipartFile file = toMultipartFile("hello".getBytes(StandardCharsets.UTF_8), null);
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains(".jsonl"));
    }

    @Test
    void testImport_upperCaseJsonlExtension_accepted() {
        MultipartFile file = toMultipartFile("{\"x\":1}\n".getBytes(StandardCharsets.UTF_8), "A.JSONL");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertTrue(e.getMessage().contains("请使用模型管理页面导出的文件"),
            "upper-case .JSONL should pass extension check, reason=" + e.getMessage());
    }

    @Test
    void testImport_binaryFileWithNulByte_throws400() {
        byte[] bin = new byte[]{'{', '}', '\0', '\n'};
        MultipartFile file = toMultipartFile(bin, "a.jsonl");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("UTF-8"), "binary detection should mention UTF-8");
    }

    @Test
    void testImport_multiLinePrettyPrinted_throwsSingleLineError() {
        // 模拟用户用文本编辑器 pretty-print 后的多行 JSON（对齐用户实测的 provider_no_model.jsonl 场景）：
        // 虽然整体是合法 JSON 对象，但被拆成多行，每一行都不是完整 JSON 对象，单行 JSONL 校验应在解析之前就顶层拒绝。
        String pretty = "{\n"
            + "  \"import_type\": \"model_service\",\n"
            + "  \"payload\": {\n"
            + "    \"model_metadata\": [],\n"
            + "    \"provider_metadata\": null\n"
            + "  }\n"
            + "}\n";
        MultipartFile file = toMultipartFile(pretty.getBytes(StandardCharsets.UTF_8), "pretty.jsonl");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"),
            "pretty-printed multi-line must be rejected with single-line hint, got: " + e.getMessage());
    }

    @Test
    void testImport_multiLineTwoObjects_throwsSingleLineError() {
        // 两行合法 JSONL 对象（两个独立 entity）也必须拒绝——导出始终是单行。
        String two = "{\"import_type\":\"model_service\",\"payload\":{\"model_metadata\":[]}}\n"
            + "{\"import_type\":\"model_service\",\"payload\":{\"model_metadata\":[]}}\n";
        MultipartFile file = toMultipartFile(two.getBytes(StandardCharsets.UTF_8), "two.jsonl");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "two-object file rejected, got: " + e.getMessage());
    }

    @Test
    void testImport_singleLineWithLeadingTrailingBlankLines_accepted() throws Exception {
        // 首尾空行/纯空白行应被 trim+过滤，仅剩 1 有效行 → 合法导入。
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        byte[] body = toJsonlLine(buildEntity("m1", "https://x.com/v1"));
        String withBlankLines = "\n\n   \n" + new String(body, StandardCharsets.UTF_8) + "\n\n";
        ImportRsp rsp = service.importModels("proj", "ws",
            toMultipartFile(withBlankLines.getBytes(StandardCharsets.UTF_8), "a.jsonl"), "SKIP", "p1");
        assertEquals(1, rsp.getSucceedLen(), "blank lines around single valid line must be tolerated");
        verify(modelServiceManager, times(1)).createModelServiceForImport(any());
    }

    @Test
    void testPreview_multiLinePrettyPrinted_throwsSingleLineError() {
        // preview 路径同样要拦截多行 pretty 文件（对称覆盖）。
        String pretty = "{\n  \"import_type\":\"model_service\",\n  \"payload\":{}\n}\n";
        MultipartFile file = toMultipartFile(pretty.getBytes(StandardCharsets.UTF_8), "pretty.jsonl");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.previewImport("proj", "ws", file));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "preview path must also reject multi-line, got: " + e.getMessage());
    }

    @Test
    void testPreview_sameFileChecks_applyToPreview() {
        MultipartFile empty = toMultipartFile(new byte[0], "a.jsonl", true);
        AgentStudioException e1 = assertThrows(AgentStudioException.class,
            () -> service.previewImport("proj", "ws", empty));
        assertTrue(e1.getMessage().contains("上传文件不能为空"));

        MultipartFile txt = toMultipartFile("x".getBytes(StandardCharsets.UTF_8), "a.txt");
        AgentStudioException e2 = assertThrows(AgentStudioException.class,
            () -> service.previewImport("proj", "ws", txt));
        assertTrue(e2.getMessage().contains(".jsonl"));

        byte[] bin = new byte[]{'{', '\0', '}'};
        MultipartFile binary = toMultipartFile(bin, "a.jsonl");
        AgentStudioException e3 = assertThrows(AgentStudioException.class,
            () -> service.previewImport("proj", "ws", binary));
        assertTrue(e3.getMessage().contains("UTF-8"));
    }

    // ============================== B. conflict_strategy 解析校验 ==============================

    @Test
    void testImport_conflictStrategy_invalidValue_throws() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", toMultipartFile(jsonl), "MERGE", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("conflict_strategy"));
        assertTrue(e.getMessage().contains("SKIP/COVER"), "expected values listed, got: " + e.getMessage());
    }

    @Test
    void testImport_conflictStrategy_caseInsensitive_accepted() throws Exception {
        // conflict_strategy 大小写不敏感：skip/cover/Skip/Cover 都等价于 SKIP/COVER（不抛 400）
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenAnswer(inv -> {
                List<String> ids = inv.getArgument(2);
                return List.of(buildEntity(ids.get(0), "https://x.com/v1?m=" + ids.get(0)));
            });
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jLower = service.exportModels("proj", "ws", List.of("case-lower"));
        ImportRsp r1 = service.importModels("proj", "ws", toMultipartFile(jLower), "skip", "p1");
        assertEquals(1, r1.getSucceedLen(), "lowercase 'skip' must be accepted");

        byte[] jMixed = service.exportModels("proj", "ws", List.of("case-mixed"));
        ImportRsp r2 = service.importModels("proj", "ws", toMultipartFile(jMixed), "Cover", "p1");
        assertEquals(1, r2.getSucceedLen(), "mixed-case 'Cover' must be accepted");
    }

    @Test
    void testImport_conflictStrategy_withWhitespace_trimmedAndAccepted() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), "  SKIP  ", "p1");
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testImport_conflictStrategy_nullOrBlank_defaultsToSkip() throws Exception {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));

        ImportRsp r1 = service.importModels("proj", "ws", toMultipartFile(jsonl), null, "p1");
        assertEquals(1, r1.getSucceedLen(), "null should default to SKIP");

        ImportRsp r2 = service.importModels("proj", "ws", toMultipartFile(jsonl), "", "p1");
        assertEquals(1, r2.getSucceedLen(), "empty string should default to SKIP");

        ImportRsp r3 = service.importModels("proj", "ws", toMultipartFile(jsonl), "   ", "p1");
        assertEquals(1, r3.getSucceedLen(), "blank should default to SKIP");
    }

    // ============================== C. 整文件 fast-fail 路径 ==============================

    @Test
    void testPreview_fileWithoutAnyModelLine_multiLineRejected() {
        // 多非 model_service 行首先命中"单行 JSONL"校验（readLines 先拦），
        // 单文件纯非 model_service 走 fast-fail，见 testImport_fileWithoutAnyModelLine_throwsTopLevel。
        String content = "{\"import_type\":\"workflow\"}\n{\"import_type\":\"agent\"}\n";
        MultipartFile file = toMultipartFile(content.getBytes(StandardCharsets.UTF_8), "a.jsonl");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.previewImport("proj", "ws", file));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "multi-line must hit single-line guard first, got: " + e.getMessage());
    }

    @Test
    void testImport_fileWithoutAnyModelLine_throwsTopLevel() {
        String content = "{\"import_type\":\"workflow\",\"dsl\":{}}\n";
        MultipartFile file = toMultipartFile(content.getBytes(StandardCharsets.UTF_8), "a.jsonl");
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", file, "SKIP"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
    }

    @Test
    void testImport_mixedLines_oneModelOneBad_rejectedAsMultiLine() throws Exception {
        // R5b：workflow 行 + model_service 行混合属于多行，被 readLines 顶层拒绝。
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        byte[] modelLineBytes = toJsonlLine(entity);

        String content = "{\"import_type\":\"workflow\",\"dsl\":{}}\n" + new String(modelLineBytes, StandardCharsets.UTF_8);
        AgentStudioException e = assertThrows(AgentStudioException.class, () -> service.importModels("proj", "ws",
            toMultipartFile(content.getBytes(StandardCharsets.UTF_8), "a.jsonl"), "SKIP", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "multi-line rejected, got: " + e.getMessage());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== D. 多故障混合场景 ==============================

    @Test
    void testImport_threeLines_multiLineRejected() throws Exception {
        // R5b：3 有效行（坏 JSON + 冲突模型 + 新模型）被"单行 JSONL"校验顶层拒绝，不再逐行计数。
        // 逐行语义通过单行坏 payload / 单行冲突 / 单行成功等用例覆盖（见 testImport_nullPayload、testConflictSkip、
        // testImport_multipleModelsInLine 等）。
        String badLine = "{\"import_type\":\"model_service\",\"payload\":{broken!!!}\n"; // 故意缺闭合括号

        byte[] line2 = toJsonlLine(buildEntity("m2", "https://x.com/v1?m=m2"));
        byte[] line3 = toJsonlLine(buildEntity("m3", "https://x.com/v1?m=m3"));

        byte[] jsonl = (badLine
            + new String(line2, StandardCharsets.UTF_8)
            + new String(line3, StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8);

        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.importModels("proj", "ws", toMultipartFile(jsonl), "SKIP", "p1"));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
        assertTrue(e.getMessage().contains("单行 JSONL"), "multi-line rejected, got: " + e.getMessage());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== E. target_provider_id 边界 ==============================

    @Test
    void testImport_modelOnly_targetProviderIdNonExistent_modelInsertedWithNullAuthMeta() throws Exception {
        // 只导模型（无 provider_metadata）+ targetProviderId 不存在 → model 仍插入（best-effort），
        // authMetadataId 为 null
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        String line = "{\"import_type\":\"model_service\",\"payload\":{\"model_metadata\":"
            + "[{\"id\":\"m1\",\"service_name\":\"svc-m1\",\"provider_id\":\"src-p\",\"api_url\":\"https://x.com/v1\"}],"
            + "\"provider_metadata\":null}}\n";
        ImportRsp rsp = service.importModels("proj", "ws",
            toMultipartFile(line.getBytes(StandardCharsets.UTF_8), "a.jsonl"),
            "SKIP", "non-existent-target");

        assertEquals(1, rsp.getSucceedLen(), "model still inserted when target provider missing (best-effort)");
        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        assertNull(captor.getValue().getAuthMetadataId(),
            "authMetadataId should be null when target provider missing");
    }

    @Test
    void testPreview_targetProviderId_withSpecialCharacters_doesNotThrow() {
        // 防 SQL 注入回归：targetProviderId 含特殊字符不应抛 SQL 异常（MyBatis 预处理）
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        String line = "{\"import_type\":\"model_service\",\"payload\":{\"model_metadata\":"
            + "[{\"id\":\"m1\",\"service_name\":\"svc-m1\",\"provider_id\":\"src-p\",\"api_url\":\"https://x.com/v1\"}],"
            + "\"provider_metadata\":null}}\n";
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws",
            toMultipartFile(line.getBytes(StandardCharsets.UTF_8), "a.jsonl"),
            "'; DROP TABLE --");
        assertNotNull(rsp);
        assertEquals(1, rsp.getTotalCount());
    }

    // ============================== F. 导出参数校验 ==============================

    @Test
    void testExport_nullOrEmptyModelIds_throws() {
        // null model_ids
        AgentStudioException e1 = assertThrows(AgentStudioException.class,
            () -> service.exportModels("proj", "ws", (List<String>) null));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e1.getErrorCode());

        // 空数组
        AgentStudioException e2 = assertThrows(AgentStudioException.class,
            () -> service.exportModels("proj", "ws", Collections.emptyList()));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e2.getErrorCode());

        // 全空白字符串元素
        AgentStudioException e3 = assertThrows(AgentStudioException.class,
            () -> service.exportModels("proj", "ws", Arrays.asList("", "  ", null)));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e3.getErrorCode());

        // 4 参重载 includeProvider=false 同等校验
        AgentStudioException e4 = assertThrows(AgentStudioException.class,
            () -> service.exportModels("proj", "ws", Collections.emptyList(), false));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e4.getErrorCode());

        // buildModelExportEntity 不应被调用（在入口就抛）
        verify(modelServiceMgmtService, never()).buildModelExportEntity(any(), any(), any());
        verify(modelServiceMgmtService, never()).buildModelExportEntity(any(), any(), any(), anyBoolean());
    }

    @Test
    void testExport_modelsContainingBlanks_validOnesStillPass() {
        // 非空 id 夹杂空白：入口校验只看"是否存在至少一个非空 id"，放行；下游 stub 返回一个最小合法 entity
        ModelServiceData m = new ModelServiceData();
        m.setId("m1");
        m.setServiceName("svc-m1");
        m.setProviderId("p1");
        m.setApiUrl("https://example.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(m)));
        entity.setProviderMetadata(null);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(Collections.singletonList(entity));
        byte[] out = service.exportModels("proj", "ws", Arrays.asList("  ", "m1", ""));
        assertNotNull(out);
        assertTrue(out.length > 0, "mixed blank/valid ids → valid ids exported");
    }

    @Test
    void testExportByProvider_blankProviderId_throws() {
        AgentStudioException e1 = assertThrows(AgentStudioException.class,
            () -> service.exportModelsByProvider("proj", "ws", null));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e1.getErrorCode());

        AgentStudioException e2 = assertThrows(AgentStudioException.class,
            () -> service.exportModelsByProvider("proj", "ws", ""));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e2.getErrorCode());

        AgentStudioException e3 = assertThrows(AgentStudioException.class,
            () -> service.exportModelsByProvider("proj", "ws", "   "));
        assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e3.getErrorCode());

        // 不应进入下游查询
        verify(userModelServiceProviderMapper, never()).selectByProjectIdAndWorkspaceId(any(), any(), any());
    }

    @Test
    void testExport_buildEntityReturnsFewerModels_exportsOnlyReturned() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] out = service.exportModels("proj", "ws", List.of("m1", "ghost"));
        String content = new String(out, StandardCharsets.UTF_8);
        assertEquals(1, content.trim().split("\n").length, "exports what buildModelExportEntity returns");
        assertTrue(content.contains("m1"));
        assertFalse(content.contains("ghost"));
    }

    @Test
    void testExport_byProvider_notFound_throws() {
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        AgentStudioException e = assertThrows(AgentStudioException.class,
            () -> service.exportModelsByProvider("proj", "ws", "no-such"));
        assertEquals(StudioError.MD_PROVIDER_NOT_EXIST, e.getErrorCode());
    }

    @Test
    void testExport_authMetadataFieldIsMasked() {
        // maskProviderAuth 对 ProviderAuthMetadata.authInfo 置 " "，真实密钥不出域。
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo("sk-real-secret-xxxxxxxx");
        ProviderAuthData authData = new ProviderAuthData();
        // 按下游契约：authData.authInfo 已由 buildModelExportEntity 置为 " "（真实密钥不出域）。
        // cipher_name 字段已从 ProviderAuthData 删除；若外部文件带该字段会被 ignoreUnknown 忽略。
        authData.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        ModelServiceProvider p = new ModelServiceProvider();
        p.setId("p1");
        pm.setModelServiceProviderMetadata(p);
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);

        ModelServiceData m = new ModelServiceData();
        m.setId("m1"); m.setServiceName("svc-m1"); m.setProviderId("p1"); m.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(m)));
        entity.setProviderMetadata(pm);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        String content = new String(jsonl, StandardCharsets.UTF_8);

        assertFalse(content.contains("sk-real-secret-xxxxxxxx"),
            "provider_auth_metadata.auth_info must be masked, content=" + content);
        assertFalse(content.contains("\"cipher_name\""),
            "export must not write cipher_name field, content=" + content);
    }

    // ============================== G. 其他防御性回归 ==============================

    @Test
    void testImport_crlfLineEndings_singleLineAccepted() throws Exception {
        // Windows CRLF 结尾的单行文件应正确解析（CRLF 被当作换行 trim 后仅剩 1 有效行）。
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] l1 = toJsonlLine(buildEntity("crlf1", "https://x.com/v1?m=crlf1"));
        // 将 LF 结尾换成 CRLF
        String s1 = new String(l1, StandardCharsets.UTF_8).replaceAll("\\n$", "\r\n");
        byte[] singleLineCrlf = s1.getBytes(StandardCharsets.UTF_8);

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(singleLineCrlf), "SKIP", "p1");
        assertEquals(1, rsp.getSucceedLen(), "single CRLF-terminated line must import");
    }

    private ModelExportEntity buildEntity(String modelId, String apiUrl) {
        ModelServiceData model = new ModelServiceData();
        model.setId(modelId);
        model.setServiceName("svc-" + modelId);
        model.setProviderId("p1");
        model.setApiUrl(apiUrl);
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(null);
        return entity;
    }

    private ModelExportEntity buildEntityWithProvider(String modelId, String apiUrl, String providerId) {
        ModelServiceData model = new ModelServiceData();
        model.setId(modelId);
        model.setServiceName("svc-" + modelId);
        model.setProviderId(providerId);
        model.setApiUrl(apiUrl);
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId(providerId);
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId(providerId);
        authMeta.setAuthInfo(" ");
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);
        return entity;
    }

    private MultipartFile toMultipartFile(byte[] bytes) {
        return toMultipartFile(bytes, "a.jsonl");
    }

    private MultipartFile toMultipartFile(byte[] bytes, String filename) {
        return toMultipartFile(bytes, filename, bytes == null || bytes.length == 0);
    }

    private MultipartFile toMultipartFile(byte[] bytes, String filename, boolean empty) {
        MultipartFile file = mock(MultipartFile.class);
        try {
            when(file.getBytes()).thenReturn(empty ? new byte[0] : bytes);
        } catch (java.io.IOException e) {
            throw new RuntimeException(e);
        }
        when(file.getOriginalFilename()).thenReturn(filename);
        when(file.isEmpty()).thenReturn(empty);
        return file;
    }
}
