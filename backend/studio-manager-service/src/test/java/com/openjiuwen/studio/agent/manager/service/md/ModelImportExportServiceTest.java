/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.md;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.SignatureUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.common.dto.ImportRes;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewItem;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewRsp;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ProviderExportMetadata;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.manager.enums.ModelImportConflictStrategy;
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
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
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
 * 真实构件：{@code ObjectMapper}、{@code SignatureUtils}（按用例启用/禁用）、{@code UrlCheckUtils}
 * （enableUrlCheck=false 使 checkUrl 放通，validateEnvVarPlaceholders 走真实逻辑）。
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
        SignatureUtils signatureUtils = new SignatureUtils();
        ReflectionTestUtils.setField(signatureUtils, "signatureEnable", true);
        ReflectionTestUtils.setField(signatureUtils, "secretKey", "test-secret-key");
        UrlCheckUtils urlCheckUtils = new UrlCheckUtils();
        ReflectionTestUtils.setField(urlCheckUtils, "enableUrlCheck", false);

        service = new ModelImportExportService();
        ReflectionTestUtils.setField(service, "modelServiceMgmtService", modelServiceMgmtService);
        ReflectionTestUtils.setField(service, "modelServiceManager", modelServiceManager);
        ReflectionTestUtils.setField(service, "modelServiceMapper", modelServiceMapper);
        ReflectionTestUtils.setField(service, "userModelServiceProviderMapper", userModelServiceProviderMapper);
        ReflectionTestUtils.setField(service, "providerAuthMetadataMapper", providerAuthMetadataMapper);
        ReflectionTestUtils.setField(service, "providerAuthDataMapper", providerAuthDataMapper);
        ReflectionTestUtils.setField(service, "signatureUtils", signatureUtils);
        ReflectionTestUtils.setField(service, "urlCheckUtils", urlCheckUtils);
        ReflectionTestUtils.setField(service, "jacksonObjectMapper", objectMapper);
        ReflectionTestUtils.setField(service, "licenseCtrlService", licenseCtrlService);
    }

    @Test
    void testRoundTrip_importPreservesId() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
        assertEquals("m1", captor.getValue().getId());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testSignatureFailure_recordedAsFailed() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        // 篡改 payload：serviceName 含 "-"（标准 Base64 不含 "-"，故仅命中 payload，签名不变）→ 验签失败
        String tampered = new String(jsonl, StandardCharsets.UTF_8).replace("svc-m1", "tampered");

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(tampered.getBytes(StandardCharsets.UTF_8)),
            ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertTrue(rsp.getFailedLen() >= 1);
    }

    @Test
    void testConflictSkip() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        verify(modelServiceManager, never()).deleteModelService(any());
        assertEquals(1, rsp.getFailedLen());
    }

    @Test
    void testConflictCover() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.COVER);

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
    void testEnvVarPlaceholderValid() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://${_env.plugin_url_params.HOST}/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager).createModelServiceForImport(any());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testEnvVarPlaceholderInvalid() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://${evil.var}/x")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getFailedLen());
    }

    @Test
    void testMaskedAuthExport() {
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(new ProviderAuthMetadata().setProviderId("p1").setAuthInfo("secret-cipher"));
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        entity.setProviderMetadata(pm);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));

        // maskProviderAuth 把 ProviderAuthMetadata.authInfo 置空，密文不外泄
        assertEquals(" ", pm.getProviderAuthMetadata().getAuthInfo());
        assertTrue(!new String(jsonl, StandardCharsets.UTF_8).contains("secret-cipher"));
    }

    @Test
    void testSignatureDisabled() {
        SignatureUtils disabled = new SignatureUtils();
        ReflectionTestUtils.setField(disabled, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", disabled);

        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        // 签名禁用：导出行无 signature 字段，导入 verifySignature 直接放行
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager).createModelServiceForImport(any());
        assertEquals(1, rsp.getSucceedLen());
    }

    // ============================== previewImport 路径（此前完全未覆盖） ==============================

    @Test
    void testPreviewImport_normalWithConflict() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1"), buildEntity("m2", "https://y.com/v2")));
        // m1 无冲突，m2 同名冲突
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m1"), any()))
            .thenReturn(Collections.emptyList());
        ModelServiceBase existing = new ModelServiceBase().setId("existing").setServiceName("svc-m2").setProviderId("p1");
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m2"), any()))
            .thenReturn(List.of(existing));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1", "m2"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl));

        assertEquals(2, rsp.getTotalCount());
        assertEquals(1, rsp.getConflictCount());
        // 预检不落库
        verify(modelServiceManager, never()).createModelServiceForImport(any());
        verify(modelServiceManager, never()).deleteModelService(any());
        ModelImportPreviewItem m2Item = rsp.getItems().get(1);
        assertTrue(m2Item.getConflict());
        assertTrue(m2Item.getSignatureValid());
        assertTrue(m2Item.getApiUrlValid());
    }

    @Test
    void testPreviewImport_signatureFailureLine() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        String tampered = new String(jsonl, StandardCharsets.UTF_8).replace("svc-m1", "tampered");

        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws",
            toMultipartFile(tampered.getBytes(StandardCharsets.UTF_8)));

        // 验签失败行仍计入 total_count，signatureValid=false
        assertEquals(1, rsp.getTotalCount());
        assertEquals(1, rsp.getItems().size());
        assertFalse(rsp.getItems().get(0).getSignatureValid());
        assertNotNull(rsp.getItems().get(0).getDetail());
    }

    @Test
    void testPreviewImport_urlInvalid() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://${evil.var}/x")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl));

        assertEquals(1, rsp.getTotalCount());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        // 验签通过但 apiUrl/占位符校验失败
        assertTrue(item.getSignatureValid());
        // checkUrl 对含 ${...} 占位符的 URL 放通(enableUrlCheck=false 亦放通)→ apiUrlValid=true；
        // 仅 validateEnvVarPlaceholders 失败 → envVarValid=false（Finding 5：两标志独立判定）
        assertTrue(item.getApiUrlValid());
        assertFalse(item.getEnvVarValid());
        assertNotNull(item.getDetail());
    }

    // ============================== 导入落库边界分支 ==============================

    @Test
    void testImport_formatInvalidLine() {
        byte[] jsonl = "this is not json".getBytes(StandardCharsets.UTF_8);

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testImport_emptyFile() {
        byte[] jsonl = "\n  \n".getBytes(StandardCharsets.UTF_8);

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        // 全空行被跳过，无任何导入记录
        assertEquals(0, rsp.getCount());
        assertEquals(0, rsp.getSucceedLen());
        assertEquals(0, rsp.getFailedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testImport_multipleLines_partialSuccess() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1"), buildEntity("m2", "https://y.com/v2")));
        // m1 无冲突 → 成功；m2 同名 + SKIP → 失败
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m1"), any()))
            .thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryByName(eq("proj"), eq("ws"), eq("svc-m2"), any()))
            .thenReturn(List.of(new ModelServiceBase().setId("old").setServiceName("svc-m2").setProviderId("p1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1", "m2"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        assertEquals(1, rsp.getSucceedLen());
        assertEquals(1, rsp.getFailedLen());
    }

    @Test
    void testImport_multipleModelsInLine() {
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
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1", "m2"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        assertEquals(2, rsp.getSucceedLen());
        verify(modelServiceManager, times(2)).createModelServiceForImport(any());
    }

    @Test
    void testImport_nullPayload() {
        // 签名禁用：构造 payload 为 null 的行（`{}`），验签放行后触发 payload 缺失分支
        SignatureUtils disabled = new SignatureUtils();
        ReflectionTestUtils.setField(disabled, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", disabled);

        byte[] jsonl = "{}\n".getBytes(StandardCharsets.UTF_8);

        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        assertEquals(1, rsp.getFailedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    @Test
    void testUpsertProviderMetadata_insertIfMissing() {
        // 目标环境无该 provider 元数据 → insert 被调，且 model.authMetadataId 重链到新插入记录的 ID
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        entity.setProviderMetadata(pm);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

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
    void testUpsertProviderMetadata_alreadyExists() {
        // 目标工作空间已有该 provider 元数据(按作用域查命中) → 跳过 insert，但 model.authMetadataId 重链到已有记录的 ID
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        entity.setProviderMetadata(pm);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 目标工作空间已存在该 provider 的 auth metadata，ID="target-meta-id"
        ProviderAuthMetadata existingMeta = new ProviderAuthMetadata();
        existingMeta.setId("target-meta-id");
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(List.of(existingMeta));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        verify(providerAuthMetadataMapper, never()).insert(any(ProviderAuthMetadata.class));
        // model.authMetadataId 被重链到目标环境的 ID（非源环境旧值）
        ArgumentCaptor<ModelServiceBase> modelCaptor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(modelCaptor.capture());
        assertEquals("target-meta-id", modelCaptor.getValue().getAuthMetadataId());
    }

    @Test
    void testLicenseCheck_invoked() {
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        // importModels 入口须做 license 校验
        verify(licenseCtrlService).canAccessIntegrationModel();
    }

    @Test
    void testMalformedBase64Signature_recordedAsFailed_not500() {
        // HIGH-1 回归：畸形签名（非法 Base64）原会逃逸 IllegalArgumentException → 500；
        // 修复后 verifyLine 捕获并转为 MODEL_IMPORT_SIGNATURE_INVALID，记 failed 不中断整批。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        // 把合法签名替换为非法 Base64（含空格/中文，Base64.getDecoder().decode 必抛 IllegalArgumentException）
        String malformed = new String(jsonl, StandardCharsets.UTF_8)
            .replaceAll("\"signature\":\"[^\"]*\"", "\"signature\":\"这不是合法base64!!! \"");

        ImportRsp rsp = service.importModels("proj", "ws",
            toMultipartFile(malformed.getBytes(StandardCharsets.UTF_8)), ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
    }

    @Test
    void testCreateModelServiceInfraException_recordedAsFailed_not500() {
        // HIGH-3 回归：无冲突路径的 DB insert 抛非 AgentStudioException 时，
        // 兜底 catch 转 failed，不抛异常中断整批。（注：缓存写失败已由 syncCachesForCreate best-effort 吞掉，不会到此）
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 模拟 DB insert 异常（createModelServiceForImport 抛出 → importOneModel catch(Exception)）
        doThrow(new RuntimeException("DB insert duplicate key")).when(modelServiceManager)
            .createModelServiceForImport(any());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
    }

    @Test
    void testUpsertProviderMetadataFailure_doesNotAbortImport() {
        // HIGH-2 回归：upsertProviderMetadata 抛异常时（best-effort），模型导入不被中断。
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        entity.setProviderMetadata(pm);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByIds(any()))
            .thenThrow(new RuntimeException("DB connection lost"));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        // provider 元数据失败不阻断，模型本身仍导入成功
        assertEquals(1, rsp.getSucceedLen());
        verify(modelServiceManager).createModelServiceForImport(any());
    }

    // ============================== HIGH-4 回归：COVER 事务化 + 缓存补偿 ==============================

    @Test
    void testCover_dbFailure_recordsFailed_noCacheSync() {
        // HIGH-4 回归：coverModelService(DB 事务)失败时，旧记录由事务回滚保护，
        // 且不触发缓存同步（DB 未提交，写缓存无意义）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));
        doThrow(new RuntimeException("DB insert duplicate key")).when(modelServiceManager)
            .coverModelService(any(), any());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.COVER);

        // DB 事务失败 → 记 failed（如实反映"什么都没改"，旧记录完好），缓存同步未触发
        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
        verify(modelServiceManager, never()).removeModelCaches(any());
        verify(modelServiceManager, never()).saveModelInfoToObsAndRedis(any(), any(), any());
    }

    @Test
    void testCover_success_clearsOldCacheBeforeWritingNew() {
        // HIGH-4 回归：缓存同步顺序须"先清旧(existingId)后写新(importId)"，
        // 避免同文件二次导入同空间时 existingId==importId 自删（先写后清会把刚写的缓存删掉）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.COVER);

        // 顺序校验：coverModelService(DB 提交) → removeModelCaches(清旧) → saveModelInfoToObsAndRedis(写新)
        InOrder inOrder = inOrder(modelServiceManager);
        inOrder.verify(modelServiceManager).coverModelService(any(), eq("old-id"));
        inOrder.verify(modelServiceManager).removeModelCaches("old-id");
        inOrder.verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
    }

    @Test
    void testCover_cacheWriteFails_doesNotFailImport() {
        // HIGH-4 回归：coverModelService(DB)已提交后，缓存写失败不致导入失败（best-effort，DB 为 source of truth）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        ModelServiceBase existing = new ModelServiceBase().setId("old-id").setServiceName("svc-m1").setProviderId("p1");
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(List.of(existing));
        doThrow(new RuntimeException("OBS putObject failed")).when(modelServiceManager)
            .saveModelInfoToObsAndRedis(any(), any(), any());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.COVER);

        // DB 已提交，缓存写失败仅告警，导入仍成功；旧缓存清理仍被调用（best-effort 各自独立 try/catch）
        assertEquals(1, rsp.getSucceedLen());
        assertEquals(0, rsp.getFailedLen());
        verify(modelServiceManager).removeModelCaches("old-id");
    }

    // ============================== Finding 1 回归：无冲突路径缓存 best-effort ==============================

    @Test
    void testNoConflict_cacheWriteFails_doesNotFailImport() {
        // Finding 1 回归：无冲突路径缓存写失败时（DB 已提交），导入仍成功——与 COVER 路径语义一致。
        // 旧实现走 createModelService(insert+缓存耦合)，缓存写失败会致响应报 FAILED 但 DB 行已落（误导）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        doThrow(new RuntimeException("OBS putObject failed")).when(modelServiceManager)
            .saveModelInfoToObsAndRedis(any(), any(), any());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        // DB insert(createModelServiceForImport)已提交，缓存写失败被 syncCachesForCreate best-effort 吞掉 → 仍成功
        assertEquals(1, rsp.getSucceedLen());
        assertEquals(0, rsp.getFailedLen());
        verify(modelServiceManager).createModelServiceForImport(any());
        verify(modelServiceManager).saveModelInfoToObsAndRedis(eq("model"), eq("m1"), any());
    }

    // ============================== Finding 2 回归：预检 null-payload 不丢失 ==============================

    @Test
    void testPreviewImport_nullPayloadShown() {
        // Finding 2 回归：验签通过但 payload 缺失时，预检须展示该行（与导入报 FAILED 对齐），
        // 旧实现 modelsOf 返回空列表致该行被丢弃、totalCount 不含它，预检说 0 导入说 1 失败。
        SignatureUtils disabled = new SignatureUtils();
        ReflectionTestUtils.setField(disabled, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", disabled);

        byte[] jsonl = "{}\n".getBytes(StandardCharsets.UTF_8);
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl));

        // null-payload 行计入 totalCount，signatureValid=true（验签放行），detail="payload is missing"
        assertEquals(1, rsp.getTotalCount());
        assertEquals(1, rsp.getItems().size());
        assertTrue(rsp.getItems().get(0).getSignatureValid());
        assertEquals("payload is missing", rsp.getItems().get(0).getDetail());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== R3-1 回归：auth 作用域化 + MASKED 不插入 auth_data ==============================

    @Test
    void testAuthMetadata_scopedQuery_insertsMetadata_skipsBlankAuthData() {
        // R3-1 回归：旧实现按全局 PROVIDER_ID 查，目标环境任一工作空间有同 provider 即误判已存在→漏插。
        // 修复后按 (providerId, projectId, workspaceId) 作用域查，目标工作空间无则插入。
        //
        // 注：MASKED 导出路径下 authInfo 是 " " 占位符，upsertAuthData 会 skip auth_data insert（符合"脱敏导入
        // 需用户重填密钥"语义，同时避免详情页 500）。故本测只验证 auth_metadata 插入 + 不插入 auth_data。
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setId("exported-meta-id"); // 导出携带源环境 auth metadata 的 id（insert SQL 用 #{id}，非 DB 自增）
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderAuthData authData = new ProviderAuthData();
        authData.setProviderId("p1");
        authData.setAuthInfo(" "); // MASKED 占位符 → auth_data insert 被 skip
        authData.setAuthMetadataId("old-source-meta-id"); // 源环境旧值，因 authData 不插入此值无影响
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);
        ModelExportEntity entity = buildEntity("m1", "https://x.com/v1");
        entity.setProviderMetadata(pm);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 目标工作空间无 auth metadata（即使其他工作空间有同 providerId，作用域查也返回空→插入）
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(providerAuthDataMapper.selectByProviderId(any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        service.importModels("proj", "ws", toMultipartFile(jsonl), ModelImportConflictStrategy.SKIP);

        // auth metadata 插入（未因跨工作空间误判跳过）
        verify(providerAuthMetadataMapper).insert(any(ProviderAuthMetadata.class));
        // MASKED 脱敏导入：auth_data 不应 insert（authInfo 为空格占位符，需用户在 UI 补填密钥）
        verify(providerAuthDataMapper, never()).insert(any(ProviderAuthData.class));
    }

    // ============================== R3-2 回归：跨工作空间 COPY 时 auth_metadata id UUID 再生，避免 DuplicateKey 孤儿行 ==============================

    @Test
    void testCrossWorkspaceCopy_regeneratesAuthMetadataIdAndRemapsModelFk() {
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
        authData.setAuthInfo(" "); // MASKED 占位符 → auth_data insert 被 skip（产品预期）
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
        model.setAuthMetadataId(srcMetaId); // 源环境 authMetadataId

        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);

        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));

        // 目标工作空间内无同名/同 provider 冲突（queryByName 空）
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        // 目标工作空间内无同 id 模型（queryById 返回 null → 非跨空间模型冲突；本测只验证 auth 表）
        when(modelServiceMapper.queryById(any())).thenReturn(null);

        // provider 作用域内不存在（selectByProjectIdAndWorkspaceId 空），但全局 selectByIds 命中其他空间 → COPY 分支
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

        // authData 作用域查无（MASKED 路径下会被 skip insert，此处仅验证作用域查询行为）
        when(providerAuthDataMapper.selectByProviderId(any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of(srcModelId));
        service.importModels("proj", "ws-new", toMultipartFile(jsonl), ModelImportConflictStrategy.COVER);

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
    void testImport_whenAuthMetadataUpsertFails_modelAuthMetadataIdIsSetToNull_notDanglingSource() {
        // defense-in-depth：即使未来其他原因导致 upsertProviderMetadata 抛异常（metadata 插入失败），
        // 模型落库时 authMetadataId 必须显式置 null，不能保留源 UUID（源 UUID 指向其他空间，造成悬空 FK 孤儿行）。
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

        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryById(any())).thenReturn(null);
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        // provider insert 成功
        // metadata insert 抛异常（模拟 DB 故障 / 未来其他约束冲突）
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectById(any())).thenReturn(null);
        org.springframework.dao.DuplicateKeyException dke =
            new org.springframework.dao.DuplicateKeyException("simulated auth_metadata PK conflict");
        doThrow(dke).when(providerAuthMetadataMapper).insert(any(ProviderAuthMetadata.class));
        // 模型 insert 本身 stub（createModelServiceForImport 是 void 方法，用 doNothing）
        doNothing().when(modelServiceManager).createModelServiceForImport(any(ModelServiceBase.class));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        // 不应抛异常，模型 best-effort 落库（catch 吞 metadata 异常后继续）
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.COVER);

        assertEquals(1, rsp.getSucceedLen(), "model should still be inserted best-effort");
        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        assertNull(captor.getValue().getAuthMetadataId(),
            "when metadata upsert fails, model.authMetadataId must be null, not the dangling source UUID");
    }

    // ============================== R3-3 回归：providerId 非空校验 ==============================

    @Test
    void testImport_blankProviderId_rejected() {
        // R3-3 回归：providerId 空值会使 queryByName 退化为 serviceName-only，COVER 可能误删无关记录 → 拒绝导入。
        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId(null); // 空 providerId
        model.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(null);
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any())).thenReturn(List.of(entity));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        assertEquals(1, rsp.getFailedLen());
        assertEquals(0, rsp.getSucceedLen());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
    }

    // ============================== 只导模型 / 按供应商导出（R4：两种模式） ==============================

    @Test
    void testExportModelOnly_noProviderMetadata() {
        // R4：includeProvider=false → 4参 buildModelExportEntity 被调，payload.provider_metadata 为 null，
        // batchGetProviderExportMetadata 从未被调（不查供应商）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        String content = new String(jsonl, StandardCharsets.UTF_8);

        assertTrue(content.contains("\"provider_metadata\":null"));
        verify(modelServiceMgmtService).buildModelExportEntity(any(), any(), any(), eq(false));
        verify(modelServiceMgmtService, never()).batchGetProviderExportMetadata(any(), any(), any());
    }

    @Test
    void testExportByProvider_resolvesModelIdsViaQueryByProviders() {
        // R4：卡片入口 exportModelsByProvider → queryByProviders 取该供应商下模型 → 3参 buildModelExportEntity(供应商+模型)
        ModelServiceBase m1 = new ModelServiceData();
        m1.setId("m1");
        ModelServiceBase m2 = new ModelServiceData();
        m2.setId("m2");
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
    void testImportModelOnly_redirectsProviderId() {
        // R4：model-only 文件（provider_metadata=null）+ targetProviderId → 模型 providerId 重定向到 target，
        // 不 upsert 供应商（userModelServiceProviderMapper.insert / providerAuthMetadataMapper.insert 从未调）。
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
            ModelImportConflictStrategy.SKIP, "target-provider");

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
    void testImportModelOnly_conflictUsesRedirectedProviderId() {
        // R4：model-only 导入冲突判定用重定向后的 providerId（非源 "p1"）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());
        // queryByName 第4参必须 == target-provider（重定向后）
        when(modelServiceMapper.queryByName(any(), any(), any(), eq("target-provider")))
            .thenReturn(List.of(new ModelServiceData()));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP, "target-provider");

        // SKIP + 冲突 → failed，createModelServiceForImport 未调
        verify(modelServiceMapper).queryByName(any(), any(), any(), eq("target-provider"));
        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getFailedLen());
    }

    @Test
    void testPreviewModelOnly_redirectsProviderId_shownInItem() {
        // R4：model-only 预检传 target → 预检项 provider_id 显示重定向值，不报 blank providerId。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl), "target-provider");

        assertEquals(1, rsp.getItems().size());
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertEquals("target-provider", item.getProviderId());
        // queryByName 返回空 → 无冲突（这里验证 provider_id 重定向，不验证冲突）
        assertEquals(Boolean.FALSE, item.getConflict());
        // 重定向后 providerId 非空 → 不会走 blank-providerId 短路（apiUrlValid/envVarValid 正常判定）
        assertTrue(item.getApiUrlValid());
        assertTrue(item.getEnvVarValid());
    }

    @Test
    void testImportModelOnly_noTarget_fallsBackToBestEffort() {
        // R4 向后兼容：model-only 文件 + target=null → 模型保留源 providerId（现有 best-effort 行为不变）。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP);

        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        // 源 providerId "p1" 保留，未重定向
        assertEquals("p1", captor.getValue().getProviderId());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testImport_providerPlusModelFile_withTarget_ignoresTargetForProviderLines() {
        // R4：provider+模型文件（provider_metadata 非空）+ target 非空 → 仍 upsert 文件自带 provider，
        // model.providerId 保持源值（不被重定向）。
        ModelExportEntity entity = buildEntityWithProvider("m1", "https://x.com/v1", "p1");
        // includeProvider=true → 4参委托 3参，stub 3参
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(entity));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), any()))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), true);
        service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP, "target-provider");

        ArgumentCaptor<ModelServiceBase> captor = ArgumentCaptor.forClass(ModelServiceBase.class);
        verify(modelServiceManager).createModelServiceForImport(captor.capture());
        // provider+模型：providerId 保持源值 "p1"，未被重定向到 "target-provider"
        assertEquals("p1", captor.getValue().getProviderId());
        // upsert 供应商被调（provider_metadata 非空）
        verify(userModelServiceProviderMapper, atLeastOnce()).selectByIds(any());
    }

    @Test
    void testRoundTrip_modelOnly_signatureVerifies() {
        // R4 跨模式签名兼容：model-only 导出（provider_metadata=null）→ model-only 导入（带 target）→ 验签通过、导入成功。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any(), eq(false)))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(providerAuthMetadataMapper.selectByProjectWorkspaceProvider(any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryByName(any(), any(), any(), eq("target-provider")))
            .thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"), false);
        ImportRsp rsp = service.importModels("proj", "ws", toMultipartFile(jsonl),
            ModelImportConflictStrategy.SKIP, "target-provider");

        // 验签通过（否则 failed_len=1 且 createModelServiceForImport 未调）
        verify(modelServiceManager).createModelServiceForImport(any());
        assertEquals(0, rsp.getFailedLen());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testExportByProvider_noModels_throwsFormatInvalid() {
        // R4：queryByProviders 返回空 → exportModelsByProvider 抛 MODEL_IMPORT_FORMAT_INVALID。
        when(modelServiceMapper.queryByProviders(any(), any(), eq("p-empty")))
            .thenReturn(Collections.emptyList());

        try {
            service.exportModelsByProvider("proj", "ws", "p-empty");
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MODEL_IMPORT_FORMAT_INVALID, e.getErrorCode());
            return;
        }
        throw new AssertionError("expected AgentStudioException");
    }

    @Test
    void testExport_setsImportType_modelService() {
        // R5：导出端在签名覆盖的包装层写入 import_type=model_service。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        String content = new String(jsonl, StandardCharsets.UTF_8);

        assertTrue(content.contains("\"import_type\":\"model_service\""),
            "export line must carry import_type=model_service, got: " + content);
    }

    @Test
    void testImport_nullImportType_legacyFile_accepted() {
        // R5 向后兼容：旧模型导出文件无 import_type 字段 → 反序列化为 null → 放行导入成功。
        // 手搓一行无 import_type 的旧格式（signature 缺失，但本测试关签名校验）。
        SignatureUtils disabled = new SignatureUtils();
        ReflectionTestUtils.setField(disabled, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", disabled);

        String legacyLine = "{\"payload\":{\"model_metadata\":[{\"id\":\"m1\",\"service_name\":\"svc-m1\","
            + "\"provider_id\":\"p1\",\"api_url\":\"https://x.com/v1\"}],\"provider_metadata\":null}}\n";
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        ImportRsp rsp = service.importModels("proj", "ws",
            toMultipartFile(legacyLine.getBytes(StandardCharsets.UTF_8)),
            ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager).createModelServiceForImport(any());
        assertEquals(1, rsp.getSucceedLen());
    }

    @Test
    void testImport_wrongImportType_workflowFile_rejected() {
        // R5：工作流文件的 import_type=workflow（AgentExportEntity/WorkflowExportEntity 扁平结构带 import_type）
        // → 反序列化进 ModelExportLine.importType → validateImportType 拒绝，不落库。
        // 即便签名关闭，也据类型标识挡住错格式文件。
        SignatureUtils disabled = new SignatureUtils();
        ReflectionTestUtils.setField(disabled, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", disabled);

        String workflowLine = "{\"import_type\":\"workflow\",\"signature\":null,\"dsl\":{},\"metadata\":{}}\n";
        ImportRsp rsp = service.importModels("proj", "ws",
            toMultipartFile(workflowLine.getBytes(StandardCharsets.UTF_8)),
            ModelImportConflictStrategy.SKIP);

        verify(modelServiceManager, never()).createModelServiceForImport(any());
        assertEquals(1, rsp.getFailedLen());
        ImportRes failed = rsp.getImportList().get(0);
        assertTrue(failed.getDetail().contains("model_service"));
    }

    // ============================== 加密检测（cipher_adapted）回归 ==============================
    // 检测+提示保留：默认 MASKED/NoOp 下 cipher_adapted=true；文件中 provider_auth_data.cipher_name 为非 NoOp 值
    // （例如由其他支持加密导出的环境生成的 ENCRYPTED 文件）时，预检标 cipher_adapted=false、导入整行拒绝。
    // 实际加解密逻辑（AesGcmCipher / ENCRYPTED 导出路径 / decryptByName）已移除。

    @Test
    void testPreview_defaultExport_cipherAdaptedTrue() {
        // 本服务导出的 MASKED 文件不带 cipher_name → cipher_adapted=true，可正常导入。
        when(modelServiceMgmtService.buildModelExportEntity(any(), any(), any()))
            .thenReturn(List.of(buildEntity("m1", "https://x.com/v1")));
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        byte[] jsonl = service.exportModels("proj", "ws", List.of("m1"));
        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", toMultipartFile(jsonl));

        assertEquals(1, rsp.getItems().size());
        assertEquals(Boolean.TRUE, rsp.getItems().get(0).getCipherAdapted(),
            "default MASKED export must be cipher_adapted=true");
    }

    @Test
    void testPreview_unsupportedCipher_flagsNotAdapted() throws Exception {
        // 构造带 cipher_name=AES_GCM 的单行 JSONL（模拟加密导出环境产生的文件），
        // 本地仅 NoOp → 预检条目 cipherAdapted=false，detail 提示需重配密钥。
        ObjectMapper om = new ObjectMapper();
        com.openjiuwen.studio.agent.manager.entity.ModelExportLine line =
            new com.openjiuwen.studio.agent.manager.entity.ModelExportLine();
        line.setImportType("model_service");
        // 构造一个 provider+model 实体，authData 带 cipherName=AES_GCM
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p1");
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderAuthData authData = new ProviderAuthData();
        authData.setProviderId("p1");
        authData.setAuthInfo(" ");
        authData.setCipherName("AES_GCM"); // 关键：标识加密（无 DB 列映射，仅在 JSON 中作为识别标记）
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);
        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId("p1");
        model.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);
        line.setPayload(entity);
        line.setSignature(null);
        String oneLine = om.writeValueAsString(line) + "\n";

        SignatureUtils noSig = new SignatureUtils();
        ReflectionTestUtils.setField(noSig, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", noSig);

        MultipartFile file = toMultipartFile(oneLine.getBytes(StandardCharsets.UTF_8));
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", file);
        assertEquals(1, rsp.getTotalCount(), "should parse exactly one line");
        ModelImportPreviewItem item = rsp.getItems().get(0);
        assertEquals(Boolean.FALSE, item.getCipherAdapted(), "cipher_adapted must be false for AES_GCM under NoOp");
        assertTrue(item.getDetail() != null && item.getDetail().contains("cipher"),
            "detail must mention cipher/adaptation, got: " + item.getDetail());
    }

    @Test
    void testImport_unsupportedCipher_rejectsLine_notInserted() throws Exception {
        // 后端防御性检查：绕过预检直接调 importModels（API 直连）时，若 auth cipher 未适配 → 整行记 failed，
        // 不尝试 insert（不会因无法解密而落半残数据，也不会抛 500）。
        ObjectMapper om = new ObjectMapper();
        com.openjiuwen.studio.agent.manager.entity.ModelExportLine line =
            new com.openjiuwen.studio.agent.manager.entity.ModelExportLine();
        line.setImportType("model_service");
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p1");
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo(" ");
        ProviderAuthData authData = new ProviderAuthData();
        authData.setProviderId("p1");
        authData.setAuthInfo(" ");
        authData.setCipherName("AesGcm");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);
        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId("p1");
        model.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);
        line.setPayload(entity);
        line.setSignature(null);
        String oneLine = om.writeValueAsString(line) + "\n";

        SignatureUtils noSig = new SignatureUtils();
        ReflectionTestUtils.setField(noSig, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", noSig);

        MultipartFile file = toMultipartFile(oneLine.getBytes(StandardCharsets.UTF_8));

        ImportRsp rsp = service.importModels("proj", "ws", file, ModelImportConflictStrategy.SKIP);

        assertEquals(1, rsp.getFailedLen(), "encrypted line must be recorded as failed");
        assertEquals(0, rsp.getSucceedLen());
        // provider / authMetadata / authData / model 均不得被 insert（防御性拦截）
        verify(userModelServiceProviderMapper, never()).insert(any());
        verify(providerAuthMetadataMapper, never()).insert(any());
        verify(providerAuthDataMapper, never()).insert(any());
        verify(modelServiceManager, never()).createModelServiceForImport(any());
        verify(modelServiceManager, never()).coverModelService(any(), any());
    }

    @Test
    void testPreview_noopCipherAlias_cipherAdaptedTrue() throws Exception {
        // 兼容历史：cipher_name="NoOp"（无下划线）也应视为已适配，不得被误拒。
        ObjectMapper om = new ObjectMapper();
        com.openjiuwen.studio.agent.manager.entity.ModelExportLine line =
            new com.openjiuwen.studio.agent.manager.entity.ModelExportLine();
        line.setImportType("model_service");
        ModelServiceProvider provider = new ModelServiceProvider();
        provider.setId("p1");
        ProviderAuthMetadata authMeta = new ProviderAuthMetadata();
        authMeta.setProviderId("p1");
        authMeta.setAuthInfo("{\"API Key\":\"k\"}");
        ProviderAuthData authData = new ProviderAuthData();
        authData.setProviderId("p1");
        authData.setAuthInfo("{\"API Key\":\"k\"}");
        authData.setCipherName("NoOp");
        ProviderExportMetadata pm = new ProviderExportMetadata();
        pm.setModelServiceProviderMetadata(provider);
        pm.setProviderAuthMetadata(authMeta);
        pm.setProviderAuthData(authData);
        ModelServiceData model = new ModelServiceData();
        model.setId("m1");
        model.setServiceName("svc-m1");
        model.setProviderId("p1");
        model.setApiUrl("https://x.com/v1");
        ModelExportEntity entity = new ModelExportEntity();
        entity.setModelMetadata(new ArrayList<>(List.of(model)));
        entity.setProviderMetadata(pm);
        line.setPayload(entity);
        line.setSignature(null);
        String oneLine = om.writeValueAsString(line) + "\n";

        SignatureUtils noSig = new SignatureUtils();
        ReflectionTestUtils.setField(noSig, "signatureEnable", false);
        ReflectionTestUtils.setField(service, "signatureUtils", noSig);

        MultipartFile file = toMultipartFile(oneLine.getBytes(StandardCharsets.UTF_8));
        when(userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(any(), any(), any()))
            .thenReturn(Collections.emptyList());
        when(userModelServiceProviderMapper.selectByIds(any())).thenReturn(Collections.emptyList());
        when(modelServiceMapper.queryByName(any(), any(), any(), any())).thenReturn(Collections.emptyList());

        ModelImportPreviewRsp rsp = service.previewImport("proj", "ws", file, null);
        assertEquals(1, rsp.getTotalCount());
        assertEquals(Boolean.TRUE, rsp.getItems().get(0).getCipherAdapted(),
            "cipher_name='NoOp' must be cipher_adapted=true (NoOp alias)");
    }

    private ModelExportEntity buildEntity(String modelId, String apiUrl) {
        // 注意：setId/setServiceName/setApiUrl 继承自 ModelServiceBase，链式返回 ModelServiceBase，
        // 不能跨继承层级链式赋值给 ModelServiceData，故用分步语句。
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
        // 供应商+模型：payload.provider_metadata 非空。
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
        MultipartFile file = mock(MultipartFile.class);
        // getBytes() 声明 throws IOException，编译期强制处理
        try {
            when(file.getBytes()).thenReturn(bytes);
        } catch (java.io.IOException e) {
            throw new RuntimeException(e);
        }
        return file;
    }
}
