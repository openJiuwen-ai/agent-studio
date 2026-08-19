/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.md;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.dto.ImportRes;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.SignatureUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewItem;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewRsp;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelExportLine;
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
import com.openjiuwen.studio.agent.manager.service.IModelImportExportService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.MODEL_SERVICE;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

/**
 * 模型服务批量导入/导出服务（独立于「路径 B 资源适配器」框架）。
 *
 * <p>复用下层构件：
 * <ul>
 *   <li>{@link ModelServiceMgmtService#buildModelExportEntity} —— 纯构造导出实体</li>
 *   <li>{@link SignatureUtils} —— HMAC-SHA256 签名/验签</li>
 *   <li>{@link UrlCheckUtils} —— URL 校验 + {@code validateEnvVarPlaceholders} 占位符语法校验</li>
 *   <li>{@link ImportRsp} / {@link ImportRes} —— 导入响应封装</li>
 * </ul>
 *
 * <p>跨环境 id 一致：导入落库走 {@link ModelServiceManager#createModelServiceForImport}（{@code mapper.insert}
 * 用 {@code #{id}} 原值），不经过 API 层 {@code createModelService}（重生成 UUID + 硬编码 offline）。
 *
 * <p>鉴权 MASKED only（agent-studio 无加密 SPI）：导出时 authInfo 两处均置空，导入后用户在目标环境重新配置。
 */
@Slf4j
@Service
public class ModelImportExportService implements IModelImportExportService {

    @Autowired
    private ModelServiceMgmtService modelServiceMgmtService;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private UserModelServiceProviderMapper userModelServiceProviderMapper;

    @Autowired
    private ProviderAuthMetadataMapper providerAuthMetadataMapper;

    @Autowired
    private ProviderAuthDataMapper providerAuthDataMapper;

    @Autowired
    private SignatureUtils signatureUtils;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private ModelLicenseCtrlService licenseCtrlService;

    /** 缓存写失败后的延迟重试间隔（ms）：覆盖 OBS/Redis 短暂抖动。 */
    private static final long CACHE_RETRY_DELAY_MS = 5000L;

    // ============================== 导出 ==============================

    @Override
    public byte[] exportModels(String projectId, String workspaceId, List<String> modelIds) {
        // 保留原行为：直接走 3 参 buildModelExportEntity（供应商+模型），不经 4 参重载，避免 mock 环境下绕过 3 参 stub。
        List<ModelExportEntity> entities = modelServiceMgmtService.buildModelExportEntity(projectId, workspaceId,
            modelIds);
        StringBuilder jsonl = new StringBuilder();
        for (ModelExportEntity entity : entities) {
            jsonl.append(serialize(buildSignedLine(entity))).append('\n');
        }
        return jsonl.toString().getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public byte[] exportModels(String projectId, String workspaceId, List<String> modelIds, boolean includeProvider) {
        // includeProvider=true 时委托 3 参（命中现有 3 参 mock/stub）；false 走 4 参（只导模型）。
        if (includeProvider) {
            return exportModels(projectId, workspaceId, modelIds);
        }
        List<ModelExportEntity> entities = modelServiceMgmtService.buildModelExportEntity(projectId, workspaceId,
            modelIds, false);
        StringBuilder jsonl = new StringBuilder();
        for (ModelExportEntity entity : entities) {
            jsonl.append(serialize(buildSignedLine(entity))).append('\n');
        }
        return jsonl.toString().getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public byte[] exportModelsByProvider(String projectId, String workspaceId, String providerId) {
        // 复用 queryByProviders 取该供应商下全部模型（含 SYSTEM 作用域，导入时 applyTargetScope 重新 scope）。
        List<ModelServiceBase> models = modelServiceMapper.queryByProviders(projectId, workspaceId, providerId);
        List<String> modelIds = models.stream()
            .map(ModelServiceBase::getId)
            .filter(StringUtils::isNotBlank)
            .distinct()
            .collect(Collectors.toList());
        if (modelIds.isEmpty()) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "no models under provider " + providerId);
        }
        return exportModels(projectId, workspaceId, modelIds, true);
    }

    /**
     * 组装单行（含签名）。顺序：脱敏 → 设 import_type → payload 置好 → signature 置 null → 序列化 → 计算签名 → 回填。
     * import_type 在签名覆盖范围内，使导入端能据 type 拒绝非模型文件（工作流/agent 文件 import_type 为 workflow/agent）。
     */
    private ModelExportLine buildSignedLine(ModelExportEntity entity) {
        maskProviderAuth(entity);
        ModelExportLine line = new ModelExportLine();
        line.setImportType(MODEL_SERVICE);
        line.setPayload(entity);
        line.setSignature(null);
        String signed = serialize(line);
        line.setSignature(signatureUtils.signature(signed));
        return line;
    }

    /**
     * 脱敏：{@code buildModelExportEntity} 已把 {@code ProviderAuthData.authInfo} 置 " "，
     * 此处补 {@code ProviderAuthMetadata.authInfo}（库内密文）置空，避免密文外泄（MASKED only）。
     */
    private void maskProviderAuth(ModelExportEntity entity) {
        ProviderExportMetadata pm = entity.getProviderMetadata();
        if (pm == null || pm.getProviderAuthMetadata() == null) {
            return;
        }
        pm.getProviderAuthMetadata().setAuthInfo(" ");
    }

    /**
     * 判断导入实体的鉴权加密方式是否被当前环境适配。
     * <ul>
     *   <li>只导模型（providerMetadata=null）或无 authData → 视为适配（不含加密密钥）</li>
     *   <li>authData.cipher_name 为空 / "NoOp" → 明文 / MASKED 占位，适配</li>
     *   <li>其他 cipherName（如 "AesGcm"）→ 当前环境仅支持 NoOp，未适配</li>
     * </ul>
     * 不做实际解密——仅识别标记，未适配时预检/导入拒绝并提示用户在目标环境重配密钥。
     */
    private boolean isCipherAdapted(ModelExportEntity entity) {
        if (entity == null) {
            return true;
        }
        ProviderExportMetadata pm = entity.getProviderMetadata();
        if (pm == null || pm.getProviderAuthData() == null) {
            return true;
        }
        String cipher = pm.getProviderAuthData().getCipherName();
        // 空白字段视为明文/MASKED（旧版本导出无此字段）。
        if (StringUtils.isBlank(cipher)) {
            return true;
        }
        // 归一化（去下划线，忽略大小写）后匹配 "NOOP"：覆盖 "NoOp"、"NO_OP"、"NO_OP_CIPHER" 等变体。
        String normalized = StringUtils.remove(cipher, '_');
        return StringUtils.containsIgnoreCase(normalized, "NOOP");
    }

    // ============================== 导入预检 ==============================

    @Override
    public ModelImportPreviewRsp previewImport(String projectId, String workspaceId, MultipartFile file) {
        return previewImport(projectId, workspaceId, file, null);
    }

    @Override
    public ModelImportPreviewRsp previewImport(String projectId, String workspaceId, MultipartFile file,
        String targetProviderId) {
        List<ModelImportPreviewItem> items = new ArrayList<>();
        int conflictCount = 0;
        for (LineContext ctx : readLines(file)) {
            ModelExportLine line;
            try {
                line = parseLine(ctx);
                validateImportType(line);
                verifyLine(line);
            } catch (AgentStudioException e) {
                log.warn("Preview line {} failed: {}", ctx.lineNo, e.getMessage());
                items.add(previewForLineFailure(ctx, e));
                continue;
            }
            // 与 importModels 对齐：验签通过但 payload 缺失时，导入侧报 FAILED("payload is missing")，
            // 预检侧须同步展示该行（否则 totalCount 不含它，预检说 0 导入说 1 失败，用户困惑）。
            if (line.getPayload() == null) {
                items.add(previewForNullPayload(ctx));
                continue;
            }
            boolean modelOnly = line.getPayload().getProviderMetadata() == null
                && StringUtils.isNotBlank(targetProviderId);
            boolean cipherAdapted = isCipherAdapted(line.getPayload());
            for (ModelServiceData model : modelsOf(line)) {
                if (modelOnly) {
                    // 只导模型预检：重定向 providerId 到目标供应商，冲突判定/展示用重定向后的值。
                    model.setProviderId(targetProviderId);
                }
                ModelImportPreviewItem item = previewOneModel(projectId, workspaceId, model, cipherAdapted);
                items.add(item);
                if (Boolean.TRUE.equals(item.getConflict())) {
                    conflictCount++;
                }
            }
        }
        return new ModelImportPreviewRsp().setTotalCount(items.size()).setConflictCount(conflictCount).setItems(items);
    }

    private ModelImportPreviewItem previewOneModel(String projectId, String workspaceId, ModelServiceData model,
        boolean cipherAdapted) {
        ModelImportPreviewItem item = new ModelImportPreviewItem().setId(model.getId())
            .setServiceName(model.getServiceName())
            .setProviderId(model.getProviderId())
            .setConflict(hasConflict(projectId, workspaceId, model))
            .setCipherAdapted(cipherAdapted);
        // providerId 空值：冲突键退化、COVER 可能误删无关记录 → 与导入侧 validateModel 一致判定为非法。
        if (StringUtils.isBlank(model.getProviderId())) {
            return item.setSignatureValid(true)
                .setApiUrlValid(false)
                .setEnvVarValid(false)
                .setDetail("model " + model.getServiceName() + " has blank providerId, cannot import");
        }
        // 加密鉴权未适配：api_url/env_var 校验不再继续（加密情况下这些字段仍是明文/占位符，但密钥不可用，整体不可导入）。
        if (!cipherAdapted) {
            return item.setSignatureValid(true)
                .setApiUrlValid(true)
                .setEnvVarValid(true)
                .setDetail("auth data is encrypted by a cipher not adapted in this environment; "
                    + "please reconfigure credentials in the target environment after import");
        }
        // 两个校验独立判定：checkUrl 对含 ${...} 占位符的 URL 放通（交由 validateEnvVarPlaceholders 管语法），
        // 故非法占位符 URL 应 apiUrlValid=true、envVarValid=false。耦合在一个 try/catch 会误把两标志同时置 false。
        List<String> details = new ArrayList<>();
        try {
            urlCheckUtils.checkUrl(projectId, model.getApiUrl());
            item.setApiUrlValid(true);
        } catch (AgentStudioException e) {
            item.setApiUrlValid(false);
            details.add(describe(e));
        }
        try {
            urlCheckUtils.validateEnvVarPlaceholders(model.getApiUrl());
            item.setEnvVarValid(true);
        } catch (AgentStudioException e) {
            item.setEnvVarValid(false);
            details.add(describe(e));
        }
        if (!details.isEmpty()) {
            item.setDetail(String.join("; ", details));
        }
        return item.setSignatureValid(true);
    }

    private ModelImportPreviewItem previewForLineFailure(LineContext ctx, AgentStudioException e) {
        return new ModelImportPreviewItem().setId(null)
            .setServiceName("(line " + ctx.lineNo + ")")
            .setProviderId(null)
            .setConflict(false)
            .setSignatureValid(false)
            .setApiUrlValid(false)
            .setEnvVarValid(false)
            .setCipherAdapted(true)
            .setDetail(describe(e));
    }

    private ModelImportPreviewItem previewForNullPayload(LineContext ctx) {
        // 验签已通过但 payload 缺失：signatureValid=true，其余校验无法进行。
        return new ModelImportPreviewItem().setId(null)
            .setServiceName("(line " + ctx.lineNo + ")")
            .setProviderId(null)
            .setConflict(false)
            .setSignatureValid(true)
            .setApiUrlValid(false)
            .setEnvVarValid(false)
            .setCipherAdapted(true)
            .setDetail("payload is missing");
    }

    // ============================== 导入落库 ==============================

    @Override
    public ImportRsp importModels(String projectId, String workspaceId, MultipartFile file,
        ModelImportConflictStrategy conflictStrategy) {
        return importModels(projectId, workspaceId, file, conflictStrategy, null);
    }

    @Override
    public ImportRsp importModels(String projectId, String workspaceId, MultipartFile file,
        ModelImportConflictStrategy conflictStrategy, String targetProviderId) {
        licenseCtrlService.canAccessIntegrationModel();
        List<ImportRes> importList = new ArrayList<>();
        for (LineContext ctx : readLines(file)) {
            ModelExportLine line;
            try {
                line = parseLine(ctx);
                validateImportType(line);
                verifyLine(line);
            } catch (AgentStudioException e) {
                log.warn("Import line {} skipped: {}", ctx.lineNo, e.getMessage());
                importList.addAll(failedForLine(ctx, e));
                continue;
            }
            ModelExportEntity entity = line.getPayload();
            if (entity == null) {
                importList.add(failedRes(null, "(line " + ctx.lineNo + ")", "payload is missing"));
                continue;
            }
            // 加密鉴权未适配：整行拒绝（所有子模型），提示用户在目标环境重新配置密钥。
            // 防御性兜底——预检已会标 cipher_adapted=false 阻止前端提交；后端再次检查防止绕过预检直接调用导入接口。
            if (!isCipherAdapted(entity)) {
                String cipherName = entity.getProviderMetadata() != null
                        && entity.getProviderMetadata().getProviderAuthData() != null
                    ? entity.getProviderMetadata().getProviderAuthData().getCipherName()
                    : "<unknown>";
                String msg = "auth data uses cipher '" + cipherName
                    + "' which is not adapted in this environment (NoOp only); "
                    + "please reconfigure credentials in the target environment after import";
                log.warn("Import line {} rejected: {}", ctx.lineNo, msg);
                for (ModelServiceData model : modelsOf(line)) {
                    importList.add(failedRes(model.getId(), model.getServiceName(), msg));
                }
                continue;
            }
            // 模式判定：provider_metadata 为 null + targetProviderId 非空 → 只导模型（重定向到目标供应商，
            // 不 upsert 供应商）。其余情况走供应商+模型 upsert 路径（target 为 null 时现有 best-effort 行为不变）。
            boolean modelOnly = entity.getProviderMetadata() == null
                && StringUtils.isNotBlank(targetProviderId);
            String targetAuthMetadataId;
            // 单行内 id 重映射：跨工作空间 COPY 场景下 upsertProviderMetadata / resolveConflictAndPersist
            // 可能为 provider 或某个子模型生成新 UUID；同一行内后续子模型的 providerId 必须跟着重定向到新 id，
            // 否则 FK 指向源空间 id（dangling）。modelOnly 模式下 providerId 已被显式置为 targetProviderId，无需重映射。
            Map<String, String> batchIdRemap = new HashMap<>();
            if (modelOnly) {
                targetAuthMetadataId = resolveTargetAuthMetadataId(projectId, workspaceId, targetProviderId);
            } else {
                // provider 元数据 best-effort：单条失败仅告警不中断导入（模型本身仍按导入数据落库）。
                // 返回目标环境的 auth metadata ID，供 model 重链（源环境 authMetadataId 在目标环境无效）；
                // 同时若 provider 行跨空间 COPY 时被分配新 UUID，会记录到 batchIdRemap[oldProviderId→newProviderId]
                // 供下方 model 循环在导入前先重定向 providerId。
                targetAuthMetadataId = null;
                try {
                    targetAuthMetadataId = upsertProviderMetadata(projectId, workspaceId, entity.getProviderMetadata(),
                        batchIdRemap);
                } catch (Exception e) {
                    log.warn("Provider metadata upsert failed for line {}, continuing with model import",
                        ctx.lineNo, e);
                }
            }
            for (ModelServiceData model : modelsOf(line)) {
                if (modelOnly) {
                    // 只导模型：模型 providerId/authMetadataId 重定向到目标供应商（模型本身无密钥，
                    // api-key 在供应商侧 t_provider_auth_info 按 PROVIDER_ID 关联，目标供应商本地已有）。
                    model.setProviderId(targetProviderId);
                } else {
                    // 同一导入行内的 providerId 重映射：若 provider 行已被分配新 id，后续子模型跟着改。
                    String remapped = batchIdRemap.get(model.getProviderId());
                    if (remapped != null) {
                        model.setProviderId(remapped);
                    }
                }
                String originalId = model.getId();
                importList.add(importOneModel(projectId, workspaceId, model, conflictStrategy, targetAuthMetadataId));
                // 若跨空间 COPY 导致 id 变更，记录 old→new 供后续子模型重链 providerId。
                if (!modelOnly && StringUtils.isNotBlank(originalId) && !originalId.equals(model.getId())) {
                    batchIdRemap.put(originalId, model.getId());
                }
            }
        }
        return buildImportRsp(importList);
    }

    private ImportRes importOneModel(String projectId, String workspaceId, ModelServiceData model,
        ModelImportConflictStrategy strategy, String targetAuthMetadataId) {
        applyTargetScope(model, projectId, workspaceId);
        // 重链 authMetadataId 到目标环境（源环境值在目标环境无效；对齐 AgentImportService 的 updateModelProvider 重链）。
        // provider 元数据 upsert 失败时 targetAuthMetadataId=null：必须置 null 而非保留源值——
        // 源值指向源工作空间的 t_provider_auth_metadata 行，在目标环境不存在，会造成 t_model_service.auth_metadata_id
        // 悬空的孤儿行：前端按 auth metadata join 看不到模型，但删除供应商时全局 COUNT(*) 仍会统计到，
        // 导致 "供应商存在接入模型服务" 的死锁错误。置 null 让模型在目标环境以"未配置鉴权"形态可见、可被用户删除。
        model.setAuthMetadataId(targetAuthMetadataId);
        try {
            validateModel(model);
            urlCheckUtils.checkUrl(projectId, model.getApiUrl());
            urlCheckUtils.validateEnvVarPlaceholders(model.getApiUrl());
            resolveConflictAndPersist(projectId, workspaceId, model, strategy);
            return successRes(model);
        } catch (AgentStudioException e) {
            String detail = describe(e);
            log.warn("Import model {} failed: {}", model.getServiceName(), detail);
            return failedRes(model.getId(), model.getServiceName(), detail);
        } catch (Exception e) {
            // 兜底：DB 主键冲突 / DataAccessException / OBS / Redis 等基础设施异常，转 failed 不让整批 500。
            log.error("Import model {} failed unexpectedly", model.getServiceName(), e);
            return failedRes(model.getId(), model.getServiceName(), "unexpected error: " + e.getMessage());
        }
    }

    /**
     * 导入模型基础字段校验。providerId 是冲突键组成部分，空值会使 queryByName 退化为 serviceName-only 匹配，
     * COVER 下可能误删同 serviceName 不同 providerId 的无关记录 → 必须拒绝。预检侧 {@link #previewOneModel} 同校验。
     */
    private void validateModel(ModelServiceBase model) {
        if (StringUtils.isBlank(model.getProviderId())) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "model " + model.getServiceName() + " has blank providerId, cannot import");
        }
    }

    /**
     * 冲突判定 + 落库。冲突键 = serviceName + providerId（对齐 {@link ModelServiceMapper#queryByName}）。
     * <ul>
     *   <li>无冲突 → {@code createModelServiceForImport}（保留导入 id）</li>
     *   <li>SKIP → 记失败</li>
     *   <li>COVER → {@code coverModelService}(事务化删旧+插新, 保留导入 id) + {@code syncCachesForCover}(缓存补偿)</li>
     * </ul>
     *
     * <p>跨工作空间导入（保留导入 id）特殊处理：queryByName（工作空间作用域）查无同名，但全局按 id 查询
     * 命中其他工作空间/项目的同 UUID 行，这是全局 PK 冲突而非同名冲突：
     * <ul>
     *   <li>SKIP → 抛 MODEL_IMPORT_CONFLICT（不能 insert，否则主键重复）</li>
     *   <li>COVER → 走 COPY 语义：为导入模型生成新 UUID，不删除源工作空间行（避免把源空间数据"搬家"破坏源环境），
     *       然后按无冲突路径 create；providerId/authMetadataId 在 importOneModel 已重链到目标工作空间，无需再处理</li>
     * </ul>
     */
    private void resolveConflictAndPersist(String projectId, String workspaceId, ModelServiceBase model,
        ModelImportConflictStrategy strategy) {
        List<ModelServiceBase> exist = modelServiceMapper.queryByName(projectId, workspaceId,
            model.getServiceName(), model.getProviderId());
        // 跨工作空间导入（保留导入 id）场景：同名冲突按 workspace 作用域查可能为空，但同一 UUID 主键
        // 可能已存在于其他工作空间 → 直接 insert 会触发 t_model_service.PRIMARY 重复。补一个全局按 id 查询，
        // 区分两种情况：
        //   1) 命中同项目+空间（理论上不会发生，queryByName 应已找到）→ 防御性按同名冲突处理
        //   2) 命中其他项目/空间 → 标记为跨空间 PK 冲突，COVER 走 COPY（生成新 id，不删源行）
        ModelServiceBase existingById = null;
        boolean crossWorkspaceIdCollision = false;
        if (CollectionUtils.isEmpty(exist) && StringUtils.isNotBlank(model.getId())) {
            existingById = modelServiceMapper.queryById(model.getId());
            if (existingById != null) {
                boolean sameScope = StringUtils.equals(existingById.getProjectId(), projectId)
                    && StringUtils.equals(existingById.getWorkspaceId(), workspaceId);
                if (sameScope) {
                    // 防御性：同工作空间 id 已存在但 queryByName 未命中，按同名 COVER 路径删旧插新
                    exist = Collections.singletonList(existingById);
                } else {
                    crossWorkspaceIdCollision = true;
                }
            }
        }
        if (CollectionUtils.isEmpty(exist)) {
            if (crossWorkspaceIdCollision) {
                if (strategy == ModelImportConflictStrategy.SKIP) {
                    throw new AgentStudioException(StudioError.MODEL_IMPORT_CONFLICT,
                        "model id " + model.getId() + " already exists in another workspace/project, skipped");
                }
                // COVER 跨空间：COPY 语义——为导入模型分配新 id，源空间行保留不动。
                // 单行内（同一 provider+models 组）的 id 重映射由 importModels 中的 batchIdRemap 负责：
                // 后续子模型若仍引用 oldId 作为 providerId，会在 importOneModel 前被重定向到 newId。
                String oldId = model.getId();
                String newId = UUID.randomUUID().toString();
                model.setId(newId);
                log.info("Cross-workspace import id collision for model '{}' (oldId={}, sourceProject={}, sourceWorkspace={}); "
                        + "generating new id {} (COPY semantics, source row preserved)",
                    model.getServiceName(), oldId, existingById.getProjectId(), existingById.getWorkspaceId(), newId);
            }
            // 无冲突（或跨空间 COPY 已换新 id）：DB insert(事务化, 保留/新分配 id) + 缓存 best-effort
            modelServiceManager.createModelServiceForImport(model);
            syncCachesForCreate(model.getId(), model);
            return;
        }
        // 同名冲突（同工作空间）或同空间 id 冲突（防御性分支）：SKIP/COVER 语义保持不变。
        if (strategy == ModelImportConflictStrategy.SKIP) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_CONFLICT,
                "model service " + model.getServiceName() + " already exists, skipped");
        }
        // COVER：事务化删旧(existingId)+插新(导入id)，DB 原子；缓存补偿在事务提交后 best-effort。
        // 缓存同步顺序：先清旧(existingId)后写新(importId)，避免 existingId==importId 时自删
        // （同文件二次导入同一空间：首次无冲突落 importId，二次 COVER 按名查到的即 importId 那条）。
        String existingId = exist.get(0).getId();
        modelServiceManager.coverModelService(model, existingId);
        syncCachesForCover(model.getId(), model, existingId);
    }

    /**
     * 覆盖目标环境 scope：projectId/workspaceId 用目标端点参数覆盖；id/identityId/publishStatus 等保留导入值
     * （跨环境一致 + 溯源 + 保留原发布状态，与 API 层 createModelService 硬编码 offline 区分）。
     */
    private void applyTargetScope(ModelServiceBase model, String projectId, String workspaceId) {
        model.setProjectId(projectId);
        model.setWorkspaceId(workspaceId);
    }

    /**
     * COVER 缓存补偿（{@code coverModelService} 事务提交后 best-effort）。
     *
     * <p>顺序：先清旧(existingId)缓存 → 后写新(importId)缓存。原因：同文件二次导入同一空间时
     * existingId==importId，先写后清会自删；先清后写则以"写"收尾，两种场景都正确。
     *
     * <p>DB 已提交为 source of truth，缓存写失败触发 {@link #scheduleCacheRetry} 延迟重试一次
     * （覆盖 OBS/Redis 短暂抖动）；仍失败则记 error 提示需手动修复，不再依赖"rely on resync"假承诺
     * （全局 resync 只覆盖 SYSTEM 模型，用户工作空间模型缓存缺失不会自愈）。
     * 旧缓存清理失败仅告警（旧 id 已从 DB 删除，正常读不命中，仅遗留孤儿缓存低危）。
     */
    private void syncCachesForCover(String newId, ModelServiceBase newModel, String existingId) {
        try {
            modelServiceManager.removeModelCaches(existingId);
        } catch (Exception e) {
            log.warn("Stale cache cleanup failed for old model {}; orphaned cache may persist", existingId, e);
        }
        try {
            modelServiceManager.saveModelInfoToObsAndRedis("model", newId, newModel);
        } catch (Exception e) {
            log.error("Cache write failed for imported model {} (DB committed); scheduling retry", newId, e);
            scheduleCacheRetry(newId, newModel);
        }
    }

    /**
     * 无冲突路径缓存补偿（{@code createModelServiceForImport} 事务提交后 best-effort）。
     *
     * <p>无旧记录需清理，仅写新(importId)缓存。DB 已提交为 source of truth，缓存写失败触发重试，
     * 语义与 COVER 路径 {@link #syncCachesForCover} 一致。
     */
    private void syncCachesForCreate(String newId, ModelServiceBase newModel) {
        try {
            modelServiceManager.saveModelInfoToObsAndRedis("model", newId, newModel);
        } catch (Exception e) {
            log.error("Cache write failed for imported model {} (DB committed); scheduling retry", newId, e);
            scheduleCacheRetry(newId, newModel);
        }
    }

    /**
     * 缓存写失败后延迟重试一次（5s），覆盖 OBS/Redis 短暂抖动（最常见失败原因）。
     * 仍失败则记 error：模型已在 DB（source of truth），但缓存缺失会导致运行期读 OBS/Redis 找不到 →
     * 需用户手动更新/重导入该模型以重建缓存。异步执行，不阻塞导入响应。
     */
    private void scheduleCacheRetry(String newId, ModelServiceBase newModel) {
        CompletableFuture.runAsync(() -> {
            try {
                Thread.sleep(CACHE_RETRY_DELAY_MS);
                modelServiceManager.saveModelInfoToObsAndRedis("model", newId, newModel);
                log.info("Cache retry succeeded for imported model {}", newId);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            } catch (Exception ex) {
                log.error("Cache retry FAILED for imported model {}; model is in DB but cache missing. "
                    + "Manual action needed (update/re-import the model to rebuild cache)", newId, ex);
            }
        });
    }

    /**
     * Provider 元数据 upsert（供应商行 + 鉴权 metadata + 鉴权 data），跨工作空间 COPY 语义：
     * <ul>
     *   <li>目标工作空间内已存在同 providerId → 直接复用，不插入；返回目标空间的 authMetadataId</li>
     *   <li>全局不存在该 providerId → 原样按导入 id 插入</li>
     *   <li>全局存在但在其他工作空间（跨空间 COPY）→ 为 provider 生成新 UUID，记录 oldId→newId 到
     *       {@code batchIdRemap}，按新 id 插入；authMetadata/authData 也按新 providerId 插入</li>
     * </ul>
     * MASKED 模式下 authInfo 为空白，鉴权需用户在目标环境重新配置。best-effort：单条失败仅告警不中断导入。
     * 返回目标环境的 auth metadata ID，供调用方把 {@code model.authMetadataId} 重链到目标环境。
     *
     * <p>注意：batchIdRemap 的写入发生在这里（模型循环之前），保证后续子模型在 importOneModel 时
     * 先把自己的 providerId 重定向到新 id 再落库，避免 dangling FK。
     *
     * @return 目标环境的 auth metadata ID；无 provider auth 元数据时返回 null
     */
    private String upsertProviderMetadata(String projectId, String workspaceId, ProviderExportMetadata pem,
        Map<String, String> batchIdRemap) {
        if (pem == null) {
            return null;
        }
        String resolvedProviderId = upsertServiceProvider(projectId, workspaceId, pem.getModelServiceProviderMetadata(),
            batchIdRemap);
        // 若 provider 行因跨空间 COPY 被分配新 id，auth metadata/data 的 providerId 也要跟着重定向。
        ProviderAuthMetadata am = pem.getProviderAuthMetadata();
        if (am != null && resolvedProviderId != null) {
            am.setProviderId(resolvedProviderId);
        }
        ProviderAuthData ad = pem.getProviderAuthData();
        if (ad != null && resolvedProviderId != null) {
            ad.setProviderId(resolvedProviderId);
        }
        String authMetadataId = upsertAuthMetadata(projectId, workspaceId, am);
        if (authMetadataId != null) {
            upsertAuthData(projectId, workspaceId, ad, authMetadataId);
        }
        return authMetadataId;
    }

    /**
     * 供应商行 upsert，跨工作空间 COPY 语义。
     * <ul>
     *   <li>先按 workspace 作用域查：目标空间已存在同 id 行 → 返回原 id，不插入</li>
     *   <li>全局无同 id 行 → 原样插入，返回原 id</li>
     *   <li>全局存在但在其他项目/空间 → 生成新 UUID，写入 {@code batchIdRemap[oldId→newId]}，插入新行，返回新 id</li>
     * </ul>
     * 不依赖 name 判定（同名供应商在不同环境可能合法共存），只按 id 判定是否需要 COPY。
     *
     * @return 目标空间实际落库的 provider id（可能等于导入 id，也可能是新生成的 id）
     */
    private String upsertServiceProvider(String projectId, String workspaceId, ModelServiceProvider provider,
        Map<String, String> batchIdRemap) {
        if (provider == null || StringUtils.isBlank(provider.getId())) {
            return null;
        }
        String originalId = provider.getId();
        // 1) 先查目标工作空间是否已经存在同 id 行（已被导入过）→ 直接复用
        List<ModelServiceProvider> existInScope = userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(
            Collections.singletonList(originalId), projectId, workspaceId);
        if (CollectionUtils.isNotEmpty(existInScope)) {
            return originalId;
        }
        // 2) 全局查：selectByIds 跨所有项目/空间。命中 → 跨空间 PK 冲突，走 COPY
        Set<String> ids = new HashSet<>(Collections.singletonList(originalId));
        List<ModelServiceProvider> existGlobal = userModelServiceProviderMapper.selectByIds(ids);
        String newId = originalId;
        if (CollectionUtils.isNotEmpty(existGlobal)) {
            newId = UUID.randomUUID().toString();
            log.info("Cross-workspace COPY for provider {} → regenerate id={} in project={}/workspace={}",
                originalId, newId, projectId, workspaceId);
            provider.setId(newId);
            if (batchIdRemap != null) {
                batchIdRemap.put(originalId, newId);
            }
        }
        provider.setProjectId(projectId).setWorkspaceId(workspaceId);
        userModelServiceProviderMapper.insert(provider);
        return newId;
    }

    /**
     * Auth metadata insert-if-missing，按 providerId + 目标工作空间作用域查（非全局 PROVIDER_ID，
     * 避免跨工作空间误判"已存在"→ 漏插致 model 不可见）。
     *
     * <p>跨工作空间 COPY 语义：若作用域查无记录，但源 id 在其他项目/空间已存在（全局 PK 冲突），
     * 则为新记录分配新 UUID（对齐 {@link #upsertServiceProvider} / {@link #resolveConflictAndPersist}
     * 的 COPY 模式），避免 DuplicateKeyException 导致 auth metadata 插入失败进而造成模型行
     * {@code auth_metadata_id} 悬空的孤儿行 bug。
     *
     * @return 目标环境的 auth metadata ID（已存在则返回已有记录的 ID，缺失则插入后返回新 ID）
     */
    private String upsertAuthMetadata(String projectId, String workspaceId, ProviderAuthMetadata authMeta) {
        if (authMeta == null || StringUtils.isBlank(authMeta.getProviderId())) {
            return null;
        }
        List<ProviderAuthMetadata> exist = providerAuthMetadataMapper.selectByProjectWorkspaceProvider(
            projectId, workspaceId, authMeta.getProviderId());
        if (CollectionUtils.isNotEmpty(exist)) {
            return exist.get(0).getId();
        }
        // 跨工作空间 COPY：源 id 在其他项目/空间已存在 → 生成新 UUID，避免主键冲突。
        // 此时作用域查无(providerId, projectId, workspaceId)对应行，任何全局同 id 行都属于其他空间。
        String originalId = authMeta.getId();
        if (StringUtils.isNotBlank(originalId) && providerAuthMetadataMapper.selectById(originalId) != null) {
            String newId = UUID.randomUUID().toString();
            log.info("Cross-workspace COPY for auth_metadata {} → regenerate id={} in project={}/workspace={}",
                originalId, newId, projectId, workspaceId);
            authMeta.setId(newId);
        }
        authMeta.setProjectId(projectId).setWorkspaceId(workspaceId);
        providerAuthMetadataMapper.insert(authMeta);
        return authMeta.getId();
    }

    /**
     * Auth data insert-if-missing，按 providerId + 目标工作空间作用域查。
     * <ul>
     *   <li>跨工作空间 COPY：若源 id 在其他项目/空间已存在（全局 PK 冲突），为新记录分配新 UUID，
     *       与 {@link #upsertAuthMetadata} / {@link #upsertServiceProvider} 保持一致，避免
     *       {@code t_provider_auth_info.PRIMARY} 冲突导致整条 auth data 写入失败。</li>
     *   <li>插入前把 {@code authMetadataId} 重设为 {@code metadataId}（目标环境的 auth metadata ID）。</li>
     *   <li>MASKED 脱敏导入：auth_info 字段是空格占位符（maskProviderAuth 写入 " "），不是真实密钥。
     *       不插入 t_provider_auth_info 行——等价于"新建供应商、用户尚未填写鉴权"的初始状态，
     *       避免详情接口 transToAuthConfig 把空格当 JSON 解码抛异常导致 500；用户可在 UI 补填 API Key，
     *       与正常新建供应商流程一致。</li>
     * </ul>
     */
    private void upsertAuthData(String projectId, String workspaceId, ProviderAuthData authData,
        String metadataId) {
        if (authData == null || StringUtils.isBlank(authData.getProviderId())) {
            return;
        }
        if (CollectionUtils.isNotEmpty(providerAuthDataMapper.selectByProviderId(
            projectId, workspaceId, authData.getProviderId()))) {
            return;
        }
        // 跨工作空间 COPY：源 id 在其他项目/空间已存在 → 生成新 UUID，避免 t_provider_auth_info.PRIMARY 冲突。
        String originalDataId = authData.getId();
        if (StringUtils.isNotBlank(originalDataId) && providerAuthDataMapper.selectById(originalDataId) != null) {
            String newDataId = UUID.randomUUID().toString();
            log.info("Cross-workspace COPY for auth_data {} → regenerate id={} in project={}/workspace={}",
                originalDataId, newDataId, projectId, workspaceId);
            authData.setId(newDataId);
        }
        // MASKED 脱敏导入：auth_info 为空格占位符时不插入 auth_data 行，避免详情页 500。
        if (StringUtils.isBlank(authData.getAuthInfo()) || authData.getAuthInfo().trim().isEmpty()) {
            log.info("MASKED import: skip auth_data insert for provider={} in project={}/workspace={} (authInfo is blank placeholder); user will need to fill credentials in UI.",
                authData.getProviderId(), projectId, workspaceId);
            return;
        }
        authData.setAuthMetadataId(metadataId);
        authData.setProjectId(projectId).setWorkspaceId(workspaceId);
        providerAuthDataMapper.insert(authData);
    }

    /**
     * 只导模型导入：查目标供应商在目标工作空间已存在的 auth metadata ID（只读，不 insert）。
     * 复用 {@code upsertAuthMetadata} 的同一作用域查询；模型本身无密钥，导入只重链 authMetadataId 引用
     * 到目标供应商本地鉴权。目标供应商无 auth metadata 时返回 null（模型仍落库，仅鉴权不可用，与 best-effort 一致）。
     */
    private String resolveTargetAuthMetadataId(String projectId, String workspaceId, String targetProviderId) {
        if (StringUtils.isBlank(targetProviderId)) {
            return null;
        }
        List<ProviderAuthMetadata> exist = providerAuthMetadataMapper.selectByProjectWorkspaceProvider(
            projectId, workspaceId, targetProviderId);
        return CollectionUtils.isNotEmpty(exist) ? exist.get(0).getId() : null;
    }

    // ============================== 验签 / 解析 ==============================

    /**
     * 导入类型校验：拒绝非模型导出文件。
     * <ul>
     *   <li>{@code import_type} 为 {@link MODEL_SERVICE} → 放行（当前版本导出的模型文件）</li>
     *   <li>{@code import_type} 为 null → 放行（旧版本导出的模型文件无此字段，向后兼容）</li>
     *   <li>{@code import_type} 为其他值（如 {@code workflow}/{@code agent}/{@code Plugin}）→
     *       抛 {@link StudioError#MODEL_IMPORT_FORMAT_INVALID}，明确提示文件类型不符</li>
     * </ul>
     * 在 {@link #verifyLine} 之前执行：即便签名校验关闭（{@code export.signature.enable=false}），
     * 也能据类型标识挡住错格式文件（如把工作流 jsonl 误导入模型接口）。
     */
    private void validateImportType(ModelExportLine line) {
        String importType = line.getImportType();
        if (StringUtils.isBlank(importType) || MODEL_SERVICE.equals(importType)) {
            return;
        }
        throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
            "not a model export file (import_type=" + importType + "), expected " + MODEL_SERVICE);
    }

    /**
     * 验签：取 signature → 置 null → 序列化 → {@code verifySignature}。
     * 底层 {@code verifySignature} 不匹配抛 {@code VERIFY_SIGNATURE_FAILED}，此处转换为模型导入语义
     * {@link StudioError#MODEL_IMPORT_SIGNATURE_INVALID}（隔离模块错误码）。
     */
    private void verifyLine(ModelExportLine line) {
        String signature = line.getSignature();
        line.setSignature(null);
        String json = serialize(line);
        try {
            signatureUtils.verifySignature(json, signature);
        } catch (AgentStudioException e) {
            if (e.getErrorCode() == StudioError.VERIFY_SIGNATURE_FAILED) {
                throw new AgentStudioException(StudioError.MODEL_IMPORT_SIGNATURE_INVALID,
                    "signature verification failed");
            }
            throw e;
        } catch (IllegalArgumentException e) {
            // 畸形签名（非法 Base64）—— SignatureUtils 内部 Base64.decode 抛出，非 AgentStudioException，
            // 不加此 catch 会逃逸到全局处理器返回 500（该处理器无 IllegalArgumentException 处理分支）。
            throw new AgentStudioException(StudioError.MODEL_IMPORT_SIGNATURE_INVALID,
                "signature is malformed (not valid Base64)");
        }
    }

    private ModelExportLine parseLine(LineContext ctx) {
        try {
            return jacksonObjectMapper.readValue(ctx.raw, ModelExportLine.class);
        } catch (JsonProcessingException e) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "line " + ctx.lineNo + " parse failed: " + e.getOriginalMessage());
        }
    }

    private String serialize(ModelExportLine line) {
        try {
            return jacksonObjectMapper.writeValueAsString(line);
        } catch (JsonProcessingException e) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "serialize failed: " + e.getOriginalMessage());
        }
    }

    // ============================== 辅助 ==============================

    private boolean hasConflict(String projectId, String workspaceId, ModelServiceBase model) {
        return CollectionUtils.isNotEmpty(modelServiceMapper.queryByName(projectId, workspaceId,
            model.getServiceName(), model.getProviderId()));
    }

    /**
     * 提取异常的可读描述。{@code AgentStudioException} 用 {@code (StudioError)} 单参构造器时
     * {@code getMessage()} 为 null（如 {@code checkUrl}/{@code validateEnvVarPlaceholders} 抛的异常），
     * 直接透传会导致预检/导入失败详情空白，故按 message → details → error code name 回退取值。
     */
    private String describe(AgentStudioException e) {
        if (StringUtils.isNotBlank(e.getMessage())) {
            return e.getMessage();
        }
        if (CollectionUtils.isNotEmpty(e.getDetails())) {
            return String.join("; ", e.getDetails());
        }
        StudioError code = e.getErrorCode();
        return code != null ? code.name() : "unknown error";
    }

    private List<ModelServiceData> modelsOf(ModelExportLine line) {
        ModelExportEntity entity = line == null ? null : line.getPayload();
        if (entity == null || CollectionUtils.isEmpty(entity.getModelMetadata())) {
            return Collections.emptyList();
        }
        return entity.getModelMetadata();
    }

    private List<LineContext> readLines(MultipartFile file) {
        String content;
        try {
            content = new String(file.getBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            log.error("Fail to read import file.", e);
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID, "fail to read upload file");
        }
        String[] lines = content.split("\n");
        List<LineContext> result = new ArrayList<>();
        for (int i = 0; i < lines.length; i++) {
            String raw = lines[i].trim();
            if (raw.isEmpty()) {
                continue;
            }
            result.add(new LineContext(i + 1, raw));
        }
        return result;
    }

    private ImportRsp buildImportRsp(List<ImportRes> importList) {
        List<String> succeedIds = new ArrayList<>();
        List<String> failedIds = new ArrayList<>();
        int failedLen = 0;
        for (ImportRes res : importList) {
            if ("SUCCESS".equals(res.getStatus())) {
                if (res.getId() != null) {
                    succeedIds.add(res.getId());
                }
            } else {
                failedLen++;
                if (res.getId() != null) {
                    failedIds.add(res.getId());
                }
            }
        }
        ImportRsp rsp = new ImportRsp();
        rsp.setSucceedLen(succeedIds.size());
        rsp.setSucceedIds(succeedIds);
        rsp.setFailedLen(failedLen);
        rsp.setFailedIds(failedIds);
        rsp.setCount(importList.size());
        rsp.setImportList(importList);
        return rsp;
    }

    private List<ImportRes> failedForLine(LineContext ctx, AgentStudioException e) {
        // 与 previewForLineFailure/importOneModel 一致用 describe(e)：generateHmac 等单参构造器异常
        // getMessage() 为 null，直接透传会致 detail 空白。
        return Collections.singletonList(failedRes(null, "(line " + ctx.lineNo + ")", describe(e)));
    }

    private ImportRes successRes(ModelServiceBase model) {
        return new ImportRes().setId(model.getId())
            .setName(model.getServiceName())
            .setType("MODEL")
            .setStatus("SUCCESS")
            .setDetail("imported with preserved id: " + model.getId());
    }

    private ImportRes failedRes(String id, String name, String detail) {
        return new ImportRes().setId(id).setName(name).setType("MODEL").setStatus("FAILED").setDetail(detail);
    }

    /** 一行 JSONL 的解析上下文（行号 + 原始文本）。 */
    private static final class LineContext {
        private final int lineNo;
        private final String raw;

        private LineContext(int lineNo, String raw) {
            this.lineNo = lineNo;
            this.raw = raw;
        }
    }
}
