/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.md;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.dto.ImportRes;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
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
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;
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
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
 *   <li>{@link UrlCheckUtils} —— URL 校验 + {@code validateEnvVarPlaceholders} 占位符语法校验</li>
 *   <li>{@link ImportRsp} / {@link ImportRes} —— 导入响应封装</li>
 * </ul>
 *
 * <p>跨环境 id 一致：导入落库走 {@link ModelServiceManager#createModelServiceForImport}（{@code mapper.insert}
 * 用 {@code #{id}} 原值），不经过 API 层 {@code createModelService}（重生成 UUID + 硬编码 offline）。
 *
 * <p>鉴权 MASKED only（agent-studio 无加密 SPI）：导出时 authInfo 两处均置为空格占位，导入后用户在目标环境重新配置。
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
        // 防御性校验：controller 已兜底，此处再次拦截绕过 controller 直接调 service 的调用方（空列表/全空白列表）
        if (CollectionUtils.isEmpty(modelIds) || modelIds.stream().noneMatch(StringUtils::isNotBlank)) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "model_ids 不能为空，请至少选择一个模型");
        }
        // 保留原行为：直接走 3 参 buildModelExportEntity（供应商+模型），不经 4 参重载，避免 mock 环境下绕过 3 参 stub。
        List<ModelExportEntity> entities = modelServiceMgmtService.buildModelExportEntity(projectId, workspaceId,
            modelIds);
        StringBuilder jsonl = new StringBuilder();
        for (ModelExportEntity entity : entities) {
            jsonl.append(serialize(buildLine(entity))).append('\n');
        }
        return jsonl.toString().getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public byte[] exportModels(String projectId, String workspaceId, List<String> modelIds, boolean includeProvider) {
        // includeProvider=true 时委托 3 参（命中现有 3 参 mock/stub，3 参内也做参数校验）；false 走 4 参（只导模型）。
        if (includeProvider) {
            return exportModels(projectId, workspaceId, modelIds);
        }
        if (CollectionUtils.isEmpty(modelIds) || modelIds.stream().noneMatch(StringUtils::isNotBlank)) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "model_ids 不能为空，请至少选择一个模型");
        }
        List<ModelExportEntity> entities = modelServiceMgmtService.buildModelExportEntity(projectId, workspaceId,
            modelIds, false);
        StringBuilder jsonl = new StringBuilder();
        for (ModelExportEntity entity : entities) {
            jsonl.append(serialize(buildLine(entity))).append('\n');
        }
        return jsonl.toString().getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public byte[] exportModelsByProvider(String projectId, String workspaceId, String providerId) {
        // 防御性校验：controller 已兜底（isBlank 拦截），此处再次拦截绕过 controller 的调用方
        if (StringUtils.isBlank(providerId)) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "provider_id 不能为空，请指定一个供应商");
        }
        // 参照环境变量导出的校验模式：在取数据前先验证 providerId 是否属于本 project/workspace，
        // 避免传入不存在 / 跨空间的 providerId 时静默导出空 jsonl 文件（queryByProviders scoped 过滤后返回空列表），
        // 让调用方拿到一个无用的空响应。
        List<ModelServiceProvider> existing = userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(
            Collections.singleton(providerId), projectId, workspaceId);
        if (CollectionUtils.isEmpty(existing)) {
            log.error("provider not found or no permission for export: projectId={}, workspaceId={}, providerId={}",
                projectId, workspaceId, providerId);
            throw new AgentStudioException(StudioError.MD_PROVIDER_NOT_EXIST,
                "provider not found or no permission: " + providerId);
        }
        // 复用 queryByProviders 取该供应商下全部模型（含 SYSTEM 作用域，导入时 applyTargetScope 重新 scope）。
        List<ModelServiceBase> models = modelServiceMapper.queryByProviders(projectId, workspaceId, providerId);
        List<String> modelIds = models.stream()
            .map(ModelServiceBase::getId)
            .filter(StringUtils::isNotBlank)
            .distinct()
            .collect(Collectors.toList());
        if (modelIds.isEmpty()) {
            // 无模型的供应商：仍导出供应商元数据壳（空模型列表），目标环境可导入壳后再补模型。
            // 修复「空供应商导出空文件 / 抛异常无法再导入」——保证导出物含供应商元数据，可被重新导入。
            return exportEmptyProvider(projectId, workspaceId, providerId);
        }
        return exportModels(projectId, workspaceId, modelIds, true);
    }

    /**
     * 无模型供应商导出：直接按 providerId 取供应商元数据（不经模型派生），组装单行 JSONL
     * （空模型列表 + 供应商元数据），经 {@link #buildLine} 脱敏，与常规导出格式一致。
     * 导入端 {@code modelsOf} 对空模型列表返回 {@link Collections#emptyList()}，循环不执行，
     * 仅 upsert 供应商元数据——即「导入空供应商壳」成立。
     */
    private byte[] exportEmptyProvider(String projectId, String workspaceId, String providerId) {
        Map<String, ProviderExportMetadata> providerMap = modelServiceMgmtService
            .getProviderExportMetadataByIds(Collections.singleton(providerId));
        ProviderExportMetadata providerMetadata = providerMap.get(providerId);
        if (providerMetadata == null) {
            // 此分支理论上不可达：exportModelsByProvider 入口已通过 selectByProjectIdAndWorkspaceId 验证
            // providerId 属于本 project/workspace；但 SYSTEM 作用域供应商等边界情况仍可能取不到，保留兜底
            // （错误码对齐为 MD_PROVIDER_NOT_EXIST，而非导入侧的 MODEL_IMPORT_FORMAT_INVALID）。
            throw new AgentStudioException(StudioError.MD_PROVIDER_NOT_EXIST,
                "provider not found or has no metadata: " + providerId);
        }
        ModelExportEntity entity = new ModelExportEntity();
        entity.setProviderMetadata(providerMetadata);
        entity.setModelMetadata(new ArrayList<>());
        StringBuilder jsonl = new StringBuilder();
        jsonl.append(serialize(buildLine(entity))).append('\n');
        return jsonl.toString().getBytes(StandardCharsets.UTF_8);
    }

    /**
     * 组装单行（不签名）。顺序：脱敏 → 设 import_type → payload 置好 → 序列化。
     * import_type 用于导入端据类型拒绝非模型文件（工作流/agent 文件 import_type 为 workflow/agent）。
     */
    private ModelExportLine buildLine(ModelExportEntity entity) {
        maskProviderAuth(entity);
        ModelExportLine line = new ModelExportLine();
        line.setImportType(MODEL_SERVICE);
        line.setPayload(entity);
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

    // ============================== 导入预检 ==============================

    @Override
    public ModelImportPreviewRsp previewImport(String projectId, String workspaceId, MultipartFile file) {
        return previewImport(projectId, workspaceId, file, null);
    }

    @Override
    public ModelImportPreviewRsp previewImport(String projectId, String workspaceId, MultipartFile file,
        String targetProviderId) {
        List<LineContext> lines = readLines(file);
        // Fast-fail：整份文件里一行 import_type=model_service 都没有 → 直接顶层抛错，
        // 由全局异常处理器返回标准 error envelope，前端在顶部红条展示，避免对 N 行逐行列相同的英文/中文错误提示。
        // 只有混了合法模型行 + 非法行的部分损坏文件才走逐行处理（那种逐行提示才有信息量）。
        boolean atLeastOneModelLine = lines.stream()
            .anyMatch(l -> l.raw.contains("\"import_type\":\"" + MODEL_SERVICE + "\"")
                || l.raw.contains("\"import_type\": \"" + MODEL_SERVICE + "\""));
        if (!atLeastOneModelLine) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "文件格式非法，请使用模型管理页面导出的文件。");
        }
        // Fast-fail：只导模型文件（payload.provider_metadata 缺失）必须显式传 target_provider_id 指定
        // 目标供应商，否则模型会以源空间 provider_id 落库成为孤儿数据；从供应商详情页发起的导入会自动带该参数。
        if (isModelOnlyFile(lines) && StringUtils.isBlank(targetProviderId)) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "只导模型文件需要指定目标供应商，请从供应商详情页发起导入，或显式传入 target_provider_id");
        }
        List<ModelImportPreviewItem> items = new ArrayList<>();
        int conflictCount = 0;
        for (LineContext ctx : lines) {
            ModelExportLine line;
            try {
                line = parseLine(ctx);
                validateImportType(line);
            } catch (AgentStudioException e) {
                log.warn("Preview line {} failed: {}", ctx.lineNo, e.getMessage());
                items.add(previewForLineFailure(ctx, e));
                continue;
            }
            // payload 缺失时，导入侧报 FAILED("payload is missing")，预检侧须同步展示该行
            // （否则 totalCount 不含它，预检说 0 导入说 1 失败，用户困惑）。
            if (line.getPayload() == null) {
                items.add(previewForNullPayload(ctx));
                continue;
            }
            boolean modelOnly = line.getPayload().getProviderMetadata() == null;
            List<ModelServiceData> models = modelsOf(line);
            for (ModelServiceData model : models) {
                if (modelOnly) {
                    // 只导模型预检：重定向 providerId 到目标供应商，冲突判定/展示用重定向后的值。
                    model.setProviderId(targetProviderId);
                }
                ModelImportPreviewItem item = previewOneModel(projectId, workspaceId, model);
                items.add(item);
                if (Boolean.TRUE.equals(item.getConflict())) {
                    conflictCount++;
                }
            }
            // 空供应商壳：provider_metadata 非空但无模型，导入会 upsert 供应商壳（0 模型）。预检须为其产出条目，
            // 否则 totalCount=0 使前端 canConfirm 禁用确认按钮，与导入实际效果（建出供应商）不一致。
            // modelOnly 文件 provider_metadata 必为 null，不会误入此分支。
            if (!modelOnly && models.isEmpty() && line.getPayload().getProviderMetadata() != null) {
                items.add(previewProviderShell(line.getPayload().getProviderMetadata()));
            }
        }
        return new ModelImportPreviewRsp().setTotalCount(items.size()).setConflictCount(conflictCount).setItems(items);
    }

    private ModelImportPreviewItem previewOneModel(String projectId, String workspaceId, ModelServiceData model) {
        ModelImportPreviewItem item = new ModelImportPreviewItem().setId(model.getId())
            .setServiceName(model.getServiceName())
            .setProviderId(model.getProviderId())
            .setConflict(false)
            .setLineValid(true)
            .setType("MODEL");
        // providerId 空值：queryByName 的 PROVIDER_ID 条件会退化（serviceName-only 跨供应商匹配），
        // 可能误报冲突且 COVER 会误删无关记录。与导入侧 validateModel（冲突检测前抛异常）一致 →
        // 此处不跑 detectConflict，直接判非法，避免 preview 与 import 背离。
        if (StringUtils.isBlank(model.getProviderId())) {
            return item.setApiUrlValid(false)
                .setEnvVarValid(false)
                .setDetail("model " + model.getServiceName() + " has blank providerId, cannot import");
        }
        // 冲突检测：对齐 resolveConflictAndPersist 的三情况（本空间同名 / 本空间同 id / 跨空间同 id），
        // 返回结构化说明（无冲突返回 conflict=false、desc=null）。
        ConflictInfo conflictInfo = detectConflict(projectId, workspaceId, model);
        item.setConflict(conflictInfo.isConflict());
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
        String hardDetail = details.isEmpty() ? null : String.join("; ", details);
        return item.setDetail(mergeDetail(conflictInfo.getDesc(), hardDetail));
    }

    /**
     * 合并硬校验失败说明与冲突说明：冲突在前、硬校验在后，用 "；" 分隔。两者皆空返回 null（前端展示"无"）。
     */
    private String mergeDetail(String conflictDesc, String hardCheckDesc) {
        List<String> parts = new ArrayList<>(2);
        if (StringUtils.isNotBlank(conflictDesc)) {
            parts.add(conflictDesc);
        }
        if (StringUtils.isNotBlank(hardCheckDesc)) {
            parts.add(hardCheckDesc);
        }
        return parts.isEmpty() ? null : String.join("；", parts);
    }

    private ModelImportPreviewItem previewForLineFailure(LineContext ctx, AgentStudioException e) {
        return new ModelImportPreviewItem().setId(null)
            .setServiceName("(line " + ctx.lineNo + ")")
            .setProviderId(null)
            .setConflict(false)
            .setLineValid(false)
            .setApiUrlValid(false)
            .setEnvVarValid(false)
            .setType("MODEL")
            .setDetail(describe(e));
    }

    private ModelImportPreviewItem previewForNullPayload(LineContext ctx) {
        return new ModelImportPreviewItem().setId(null)
            .setServiceName("(line " + ctx.lineNo + ")")
            .setProviderId(null)
            .setConflict(false)
            .setLineValid(true)
            .setApiUrlValid(false)
            .setEnvVarValid(false)
            .setType("MODEL")
            .setDetail("payload is missing");
    }

    /**
     * 空供应商壳行的预检条目。provider_metadata 非空但无模型时，导入会 upsert 供应商壳（0 模型）；
     * 预检须产出此条目，否则 totalCount=0 使前端 canConfirm 禁用确认按钮。api_url/env_var 校验对
     * 供应商壳无意义（供应商本身无 api_url），放通为 true。
     */
    private ModelImportPreviewItem previewProviderShell(ProviderExportMetadata pem) {
        ModelServiceProvider provider = pem.getModelServiceProviderMetadata();
        String providerId = provider != null ? provider.getId() : null;
        String providerName = provider != null ? provider.getProviderName() : null;
        // 供应商壳（无模型）无冲突且可导入（导入侧 providerShellRes 报 SUCCESS）→ detail=null，
        // 前端展示"无"（success），避免在精简后的单列里误显红色 error。
        return new ModelImportPreviewItem()
            .setId(providerId)
            .setServiceName(providerName)
            .setProviderId(providerId)
            .setConflict(false)
            .setLineValid(true)
            .setApiUrlValid(true)
            .setEnvVarValid(true)
            .setType("PROVIDER");
    }

    // ============================== 导入落库 ==============================

    @Override
    public ImportRsp importModels(String projectId, String workspaceId, MultipartFile file,
        String conflictStrategy) {
        return importModels(projectId, workspaceId, file, conflictStrategy, null);
    }

    @Override
    public ImportRsp importModels(String projectId, String workspaceId, MultipartFile file,
        String conflictStrategy, String targetProviderId) {
        ModelImportConflictStrategy strategy = parseConflictStrategy(conflictStrategy);
        licenseCtrlService.canAccessIntegrationModel();
        List<LineContext> lines = readLines(file);
        // 与 previewImport 对齐：整文件没有一行合法模型行就直接顶层报错，避免逐行 N 条相同错误。
        boolean atLeastOneModelLine = lines.stream()
            .anyMatch(l -> l.raw.contains("\"import_type\":\"" + MODEL_SERVICE + "\"")
                || l.raw.contains("\"import_type\": \"" + MODEL_SERVICE + "\""));
        if (!atLeastOneModelLine) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "文件格式非法，请使用模型管理页面导出的文件。");
        }
        // 与 previewImport 对齐：只导模型文件必须显式传 target_provider_id。
        if (isModelOnlyFile(lines) && StringUtils.isBlank(targetProviderId)) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "只导模型文件需要指定目标供应商，请从供应商详情页发起导入，或显式传入 target_provider_id");
        }
        List<ImportRes> importList = new ArrayList<>();
        for (LineContext ctx : lines) {
            ModelExportLine line;
            try {
                line = parseLine(ctx);
                validateImportType(line);
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
            // 模式判定：provider_metadata 为 null → 只导模型（重定向到目标供应商，不 upsert 供应商），
            // 此时 targetProviderId 必须非空（fast-fail 已校验）；其余情况走供应商+模型 upsert 路径，targetProviderId 被忽略。
            boolean modelOnly = entity.getProviderMetadata() == null;
            String targetAuthMetadataId;
            boolean providerUpsertOk = false;
            // 单行内 id 重映射：跨工作空间 COPY 场景下 upsertProviderMetadata / resolveConflictAndPersist
            // 可能为 provider 或某个子模型生成新 UUID；同一行内后续子模型的 providerId 必须跟着重定向到新 id，
            // 否则 FK 指向源空间 id（dangling）。modelOnly 模式下 providerId 已被显式置为 targetProviderId，无需重映射。
            Map<String, String> batchIdRemap = new HashMap<>();
            if (modelOnly) {
                targetAuthMetadataId = resolveTargetAuthMetadataId(projectId, workspaceId, targetProviderId)
                    .orElse(null);
            } else {
                // provider 元数据 best-effort：单条失败仅告警不中断导入（模型本身仍按导入数据落库）。
                // 返回目标环境的 auth metadata ID，供 model 重链（源环境 authMetadataId 在目标环境无效）；
                // 同时若 provider 行跨空间 COPY 时被分配新 UUID，会记录到 batchIdRemap[oldProviderId→newProviderId]
                // 供下方 model 循环在导入前先重定向 providerId。
                targetAuthMetadataId = null;
                try {
                    targetAuthMetadataId = upsertProviderMetadata(projectId, workspaceId, entity.getProviderMetadata(),
                        batchIdRemap).orElse(null);
                    providerUpsertOk = true;
                } catch (Exception e) {
                    log.warn("Provider metadata upsert failed for line {}, continuing with model import",
                        ctx.lineNo, e);
                }
            }
            List<ModelServiceData> models = modelsOf(line);
            for (ModelServiceData model : models) {
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
                importList.add(importOneModel(projectId, workspaceId, model, strategy, targetAuthMetadataId));
                // 若跨空间 COPY 导致 id 变更，记录 old→new 供后续子模型重链 providerId。
                if (!modelOnly && StringUtils.isNotBlank(originalId) && !originalId.equals(model.getId())) {
                    batchIdRemap.put(originalId, model.getId());
                }
            }
            // 空供应商壳：无模型但供应商元数据已 upsert → 须产出一条结果条目，否则 succeed_len=0 与实际
            // "建出供应商"不一致，用户会误以为没导入成功。upsert 失败（best-effort catch）时改报 failed。
            if (!modelOnly && models.isEmpty() && entity.getProviderMetadata() != null) {
                importList.add(providerShellRes(entity.getProviderMetadata(), providerUpsertOk));
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
            // MODEL_IMPORT_CONFLICT 是 SKIP 策略命中的主动跳过（用户选择"同名跳过"时的预期行为），
            // 归类为 SKIPPED 而非 FAILED，避免前端把预期跳过显示为"失败"引起歧义。
            if (e.getErrorCode() == StudioError.MODEL_IMPORT_CONFLICT) {
                log.info("Import model {} skipped: {}", model.getServiceName(), detail);
                return skippedRes(model.getId(), model.getServiceName(), detail);
            }
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
        // COVER：事务化删旧(existingId)+插新(导入 id 或 COPY 新 id)，DB 原子；缓存补偿在事务提交后 best-effort。
        // 缓存同步顺序：先清旧(existingId)后写新(newId)，避免 existingId==newId 时自删
        // （同文件二次导入同一空间：首次无冲突落导入 id，二次 COVER 按名查到的即导入 id 那条）。
        String existingId = exist.get(0).getId();
        // COVER 路径的跨空间 PK 冲突守卫：exist 是按 (projectId,workspaceId,serviceName,providerId) 查到的同名行，
        // 只保证同名冲突会被删除。若导入包中的 model.id 被其他记录占用（其他工作空间、或同空间不同名/不同 provider），
        // deleteById(existingId) 不会释放那个 PK 槽位，直接 insert 会触发 Duplicate entry PRIMARY。
        // 此时走 COPY 语义——为导入模型分配新 UUID，保留占用方记录不动（和无冲突分支一致）。
        // case A：existingId.equals(model.getId()) → 同文件二次导入同空间，占用方就是将被删除的同名行，无需再生。
        // case B：model.getId() 全局不存在 → 直接使用导入 id，无需再生。
        if (StringUtils.isNotBlank(model.getId()) && !existingId.equals(model.getId())) {
            ModelServiceBase globalById = modelServiceMapper.queryById(model.getId());
            if (globalById != null) {
                String oldId = model.getId();
                String newId = UUID.randomUUID().toString();
                model.setId(newId);
                log.info("COVER import id collision for model '{}' (oldId={}, occupying row scope={}/{}, serviceName={}, "
                        + "existingNameConflictId={}); generating new id {} (COPY semantics, occupying row preserved)",
                    model.getServiceName(), oldId, globalById.getProjectId(), globalById.getWorkspaceId(),
                    globalById.getServiceName(), existingId, newId);
            }
        }
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
     * @return 目标环境的 auth metadata ID（无 provider auth 元数据时返回 Optional.empty()）
     */
    private Optional<String> upsertProviderMetadata(String projectId, String workspaceId, ProviderExportMetadata pem,
        Map<String, String> batchIdRemap) {
        if (pem == null) {
            return Optional.empty();
        }
        String resolvedProviderId = upsertServiceProvider(projectId, workspaceId, pem.getModelServiceProviderMetadata(),
            batchIdRemap).orElse(null);
        // 若 provider 行因跨空间 COPY 被分配新 id，auth metadata/data 的 providerId 也要跟着重定向。
        ProviderAuthMetadata am = pem.getProviderAuthMetadata();
        if (am != null && resolvedProviderId != null) {
            am.setProviderId(resolvedProviderId);
        }
        ProviderAuthData ad = pem.getProviderAuthData();
        if (ad != null && resolvedProviderId != null) {
            ad.setProviderId(resolvedProviderId);
        }
        String authMetadataId = upsertAuthMetadata(projectId, workspaceId, am).orElse(null);
        if (authMetadataId != null) {
            upsertAuthData(projectId, workspaceId, ad, authMetadataId);
        }
        return Optional.ofNullable(authMetadataId);
    }

    /**
     * 供应商行 upsert，跨工作空间 COPY 语义。
     * <ul>
     *   <li>先按 workspace 作用域查：目标空间已存在同 id 行 → 返回原 id，不插入</li>
     *   <li>目标空间已存在同 name 行（含 SYSTEM 预置供应商，与 id 查重 scope 一致）→ 复用那条的 id，不插入、
     *       不更新供应商本体（与 id 复用语义一致：只借 id，auth metadata/data 后续按 providerId 查自动复用目标空间已有）</li>
     *   <li>全局无同 id 行 → 原样插入，返回原 id</li>
     *   <li>全局存在但在其他项目/空间 → 生成新 UUID，写入 {@code batchIdRemap[oldId→newId]}，插入新行，返回新 id</li>
     * </ul>
     * name 复用与 id 复用并列为"目标空间已有则复用"的判定键（创建流程 {@code ProviderMgmtService} 已在代码层
     * 挡住同空间同名重复创建，故目标空间正常至多 1 条同名；这里取首条复用）。
     *
     * @return 目标空间实际落库的 provider id（可能等于导入 id、复用既有 id，也可能是新生成的 id）
     */
    private Optional<String> upsertServiceProvider(String projectId, String workspaceId, ModelServiceProvider provider,
        Map<String, String> batchIdRemap) {
        if (provider == null || StringUtils.isBlank(provider.getId())) {
            return Optional.empty();
        }
        String originalId = provider.getId();
        // 1) 先查目标工作空间是否已经存在同 id 行（已被导入过）→ 直接复用
        List<ModelServiceProvider> existInScope = userModelServiceProviderMapper.selectByProjectIdAndWorkspaceId(
            Collections.singletonList(originalId), projectId, workspaceId);
        if (CollectionUtils.isNotEmpty(existInScope)) {
            return Optional.of(originalId);
        }
        // 2) 目标工作空间已存在同 name 行（含 SYSTEM，与 id 查重 scope 一致）→ 复用其 id。
        //    与 id 复用语义一致：只借 id、不更新供应商本体、不碰既有 auth；后续 upsertAuthMetadata/upsertAuthData
        //    按 providerId 查会自动复用目标空间已有 auth 行。originalId→existingId 写入 batchIdRemap，
        //    让后续子模型的 providerId 重定向到复用的供应商（否则模型会挂到不存在的 originalId 下）。
        List<ModelServiceProvider> existByName = userModelServiceProviderMapper.selectUserDataByName(
            projectId, workspaceId, provider.getProviderName());
        if (CollectionUtils.isNotEmpty(existByName)) {
            String existingId = existByName.get(0).getId();
            if (batchIdRemap != null && !StringUtils.equals(originalId, existingId)) {
                batchIdRemap.put(originalId, existingId);
            }
            return Optional.of(existingId);
        }
        // 3) 全局查：selectByIds 跨所有项目/空间。命中 → 跨空间 PK 冲突，走 COPY
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
        return Optional.of(newId);
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
     * @return 目标环境的 auth metadata ID（已存在则返回已有记录的 ID，缺失则插入后返回新 ID；无鉴权元数据时返回 Optional.empty()）
     */
    private Optional<String> upsertAuthMetadata(String projectId, String workspaceId, ProviderAuthMetadata authMeta) {
        if (authMeta == null || StringUtils.isBlank(authMeta.getProviderId())) {
            return Optional.empty();
        }
        List<ProviderAuthMetadata> exist = providerAuthMetadataMapper.selectByProjectWorkspaceProvider(
            projectId, workspaceId, authMeta.getProviderId());
        if (CollectionUtils.isNotEmpty(exist)) {
            return Optional.of(exist.get(0).getId());
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
        return Optional.of(authMeta.getId());
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
     * 到目标供应商本地鉴权。目标供应商无 auth metadata 时返回 Optional.empty()（模型仍落库，仅鉴权不可用，与 best-effort 一致）。
     */
    private Optional<String> resolveTargetAuthMetadataId(String projectId, String workspaceId, String targetProviderId) {
        if (StringUtils.isBlank(targetProviderId)) {
            return Optional.empty();
        }
        List<ProviderAuthMetadata> exist = providerAuthMetadataMapper.selectByProjectWorkspaceProvider(
            projectId, workspaceId, targetProviderId);
        return CollectionUtils.isNotEmpty(exist)
            ? Optional.of(exist.get(0).getId())
            : Optional.empty();
    }

    // ============================== 解析 ==============================

    /**
     * 导入类型校验：拒绝非模型导出文件。
     * <ul>
     *   <li>{@code import_type} 为 {@link MODEL_SERVICE} → 放行</li>
     *   <li>{@code import_type} 为 null/空白或其他值（工作流/Agent/插件/其他模块导出的 jsonl，或非 jsonl 文件）→
     *       抛 {@link StudioError#MODEL_IMPORT_FORMAT_INVALID}，预检阶段即标红禁用确认按钮。</li>
     * </ul>
     */
    private void validateImportType(ModelExportLine line) {
        String importType = line.getImportType();
        if (MODEL_SERVICE.equals(importType)) {
            return;
        }
        String detail = StringUtils.isBlank(importType)
            ? "文件格式非法：该行缺少 import_type 字段。"
            : "文件格式非法：该行 import_type=" + importType + "，期望值 model_service。";
        throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID, detail);
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

    /**
     * 冲突检测：对齐 {@link #resolveConflictAndPersist} 的三情况判定，返回结构化说明供预检展示。
     * <ul>
     *   <li>情况1：{@code queryByName} 命中（本空间同供应商+同服务名）→
     *       "本空间下供应商「{provider_name}」已存在相同的模型服务「{service_name}」"</li>
     *   <li>情况2：{@code queryById} 命中同 scope（本空间同 model_id）→
     *       "本空间下已存在相同的模型ID（{model_id}）"</li>
     *   <li>情况3：{@code queryById} 命中不同 scope（跨空间同 model_id）→
     *       "其他工作空间已存在相同的模型ID（{model_id}）"（不显示具体空间名）</li>
     * </ul>
     * 无冲突返回 {@code conflict=false, desc=null}。
     */
    private ConflictInfo detectConflict(String projectId, String workspaceId, ModelServiceBase model) {
        // 情况1：本空间同供应商+同服务名
        List<ModelServiceBase> existByName = modelServiceMapper.queryByName(projectId, workspaceId,
            model.getServiceName(), model.getProviderId());
        if (CollectionUtils.isNotEmpty(existByName)) {
            String providerName = resolveProviderName(model.getProviderId());
            String desc = String.format("本空间下供应商「%s」已存在相同的模型服务「%s」",
                StringUtils.isNotBlank(providerName) ? providerName : model.getProviderId(),
                model.getServiceName());
            return new ConflictInfo(true, desc);
        }
        // 情况2/3：本空间无同名 → 全局按 id 查（跨工作空间 PK 冲突）
        if (StringUtils.isNotBlank(model.getId())) {
            ModelServiceBase existingById = modelServiceMapper.queryById(model.getId());
            if (existingById != null) {
                boolean sameScope = StringUtils.equals(existingById.getProjectId(), projectId)
                    && StringUtils.equals(existingById.getWorkspaceId(), workspaceId);
                if (sameScope) {
                    return new ConflictInfo(true,
                        String.format("本空间下已存在相同的模型ID（%s）", model.getId()));
                }
                return new ConflictInfo(true,
                    String.format("其他工作空间已存在相同的模型ID（%s）", model.getId()));
            }
        }
        return new ConflictInfo(false, null);
    }

    /**
     * 按 providerId 查供应商显示名（一次查询覆盖平台 + 用户两类供应商）。
     * 查不到返回 null（调用方回退显示 providerId）。
     */
    private String resolveProviderName(String providerId) {
        if (StringUtils.isBlank(providerId)) {
            return null;
        }
        List<ModelServiceProviderDetail> providers = modelServiceMapper
            .getLogosAndProviderNamesByProviderIds(Collections.singleton(providerId));
        if (CollectionUtils.isEmpty(providers)) {
            return null;
        }
        String name = providers.get(0).getProviderName();
        return StringUtils.isNotBlank(name) ? name : providers.get(0).getProviderNameEn();
    }

    /**
     * 冲突检测结果：conflict 布尔 + 人类可读说明（desc）。desc=null 表示无冲突。
     */
    private static class ConflictInfo {
        private final boolean conflict;
        private final String desc;

        ConflictInfo(boolean conflict, String desc) {
            this.conflict = conflict;
            this.desc = desc;
        }

        boolean isConflict() {
            return conflict;
        }

        String getDesc() {
            return desc;
        }
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

    /**
     * 解析冲突策略字符串，大小写不敏感匹配 SKIP/COVER，其他值抛 400。
     */
    /**
     * 预检/导入共用：判断该文件是否为"只导模型"文件。
     * 判定规则：存在任一 import_type=model_service 的非空行，且该行在快速文本扫描下未携带 provider_metadata 字段
     * （即 payload.provider_metadata 缺失或为 null）。
     * 只做文本层面的快速扫描（与 atLeastOneModelLine 风格一致），避免在 fast-fail 阶段重复做完整 JSON 绑定；
     * 格式错误 / 非 model_service 行交由后续逐行 parseLine 产生行级错误。
     */
    private boolean isModelOnlyFile(List<LineContext> lines) {
        for (LineContext ctx : lines) {
            String raw = ctx.raw;
            if (raw == null || !raw.contains("\"import_type\"")) {
                continue;
            }
            // 取 payload 对象的粗粒度边界：首个 "payload":{ 开始 → 匹配到对应闭合 }
            int payloadKey = raw.indexOf("\"payload\"");
            if (payloadKey < 0) {
                continue;
            }
            int payloadBrace = raw.indexOf('{', payloadKey);
            if (payloadBrace < 0) {
                continue;
            }
            int depth = 0;
            int payloadEnd = -1;
            for (int i = payloadBrace; i < raw.length(); i++) {
                char c = raw.charAt(i);
                if (c == '{') {
                    depth++;
                } else if (c == '}') {
                    depth--;
                    if (depth == 0) {
                        payloadEnd = i;
                        break;
                    }
                }
            }
            if (payloadEnd < 0) {
                continue;
            }
            String payload = raw.substring(payloadBrace + 1, payloadEnd);
            // 若 payload 内出现 "provider_metadata" 键且其后（跳过空白）不是 'n'（即不是 null），认为是供应商+模型文件；
            // 其余情况（键缺失、或显式 "provider_metadata":null）视为只导模型文件。
            int pmIdx = payload.indexOf("\"provider_metadata\"");
            if (pmIdx < 0) {
                return true;
            }
            int after = pmIdx + "\"provider_metadata\"".length();
            while (after < payload.length() && Character.isWhitespace(payload.charAt(after))) {
                after++;
            }
            if (after >= payload.length() || payload.charAt(after) != ':') {
                // 键出现但后无冒号（异常 JSON）——保守按"非 model-only"交给后续 parseLine 报错
                return false;
            }
            after++; // skip ':'
            while (after < payload.length() && Character.isWhitespace(payload.charAt(after))) {
                after++;
            }
            // 值紧跟 null → 视为 provider_metadata 缺失/置空 → 只导模型
            if (after + 3 <= payload.length()
                && payload.charAt(after) == 'n'
                && payload.startsWith("null", after)) {
                return true;
            }
            return false;
        }
        return false;
    }

    private ModelImportConflictStrategy parseConflictStrategy(String conflictStrategy) {
        if (StringUtils.isBlank(conflictStrategy)) {
            return ModelImportConflictStrategy.SKIP;
        }
        String normalized = conflictStrategy.trim().toUpperCase(java.util.Locale.ROOT);
        try {
            return ModelImportConflictStrategy.valueOf(normalized);
        } catch (IllegalArgumentException e) {
            String expected = String.join("/",
                Arrays.stream(ModelImportConflictStrategy.values())
                    .map(Enum::name).toArray(String[]::new));
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "参数 conflict_strategy 取值非法，期望值：" + expected);
        }
    }

    private List<LineContext> readLines(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID, "上传文件不能为空");
        }
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || !originalFilename.toLowerCase().endsWith(".jsonl")) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "文件格式非法，仅支持 .jsonl 文件");
        }
        String content;
        try {
            content = new String(file.getBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            log.error("Fail to read import file.", e);
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID, "文件读取失败");
        }
        // 二进制/非文本文件探测：UTF-8 解码后若包含 NUL 字符或不可打印控制字符比例过高，直接拒绝。
        // 正常 jsonl 全是可见字符 + 换行/制表符。
        if (content.indexOf('\0') >= 0) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "文件格式非法，仅支持 UTF-8 编码的 .jsonl 文本文件");
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
        if (result.isEmpty()) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "文件内容为空，请使用模型管理页面导出的 JSONL 文件");
        }
        // 模型导出文件始终是"单行 JSONL"——每行一个完整 JSON 对象，一个文件只包含一行（一个 ModelExportEntity，
        // 其 model_metadata 数组承载全部模型）。若 trim 后非空行数 > 1，通常是文件被文本编辑器 pretty-print
        // 成多行缩进格式，此时按行解析会逐行报"JSON 解析失败"，错误信息对用户不友好。这里直接给明确提示。
        if (result.size() > 1) {
            throw new AgentStudioException(StudioError.MODEL_IMPORT_FORMAT_INVALID,
                "文件格式非法：模型文件为单行 JSONL");
        }
        return result;
    }

    private ImportRsp buildImportRsp(List<ImportRes> importList) {
        List<String> succeedIds = new ArrayList<>();
        List<String> failedIds = new ArrayList<>();
        List<String> skippedIds = new ArrayList<>();
        int failedLen = 0;
        int skippedLen = 0;
        for (ImportRes res : importList) {
            if ("SUCCESS".equals(res.getStatus())) {
                if (res.getId() != null) {
                    succeedIds.add(res.getId());
                }
            } else if ("SKIPPED".equals(res.getStatus())) {
                skippedLen++;
                if (res.getId() != null) {
                    skippedIds.add(res.getId());
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
        rsp.setSkippedLen(skippedLen);
        rsp.setSkippedIds(skippedIds);
        rsp.setCount(importList.size());
        rsp.setImportList(importList);
        return rsp;
    }

    private List<ImportRes> failedForLine(LineContext ctx, AgentStudioException e) {
        // 与 previewForLineFailure/importOneModel 一致用 describe(e)：单参构造器异常
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

    /**
     * 空供应商壳导入结果条目。provider_metadata 非空但无模型时，导入仅 upsert 供应商壳（0 模型），
     * 须产出此条目，否则 succeed_len=0 与实际"建出供应商"不一致。type=PROVIDER 与 MODEL 区分；
     * ok=false（provider upsert best-effort 失败）时记 failed。
     */
    private ImportRes providerShellRes(ProviderExportMetadata pem, boolean ok) {
        ModelServiceProvider provider = pem.getModelServiceProviderMetadata();
        String providerId = provider != null ? provider.getId() : null;
        String providerName = provider != null ? provider.getProviderName() : null;
        if (ok) {
            return new ImportRes().setId(providerId).setName(providerName).setType("PROVIDER")
                .setStatus("SUCCESS").setDetail("provider shell imported (no models)");
        }
        return new ImportRes().setId(providerId).setName(providerName).setType("PROVIDER")
            .setStatus("FAILED").setDetail("provider metadata upsert failed");
    }

    private ImportRes failedRes(String id, String name, String detail) {
        return new ImportRes().setId(id).setName(name).setType("MODEL").setStatus("FAILED").setDetail(detail);
    }

    private ImportRes skippedRes(String id, String name, String detail) {
        return new ImportRes().setId(id).setName(name).setType("MODEL").setStatus("SKIPPED").setDetail(detail);
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
