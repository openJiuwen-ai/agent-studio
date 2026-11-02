/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.RuntimeAssetManifest;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.RuntimeAssetManifest.ManifestAsset;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.RuntimeAssetManifest.ManifestResource;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.RuntimeAssetManifest.ManifestSummary;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Component;

import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 运行时资产导出器（对应 SDD 4.2）。
 * <p>从 t_mapping 依赖图收集资产清单，从 OBS 读取文件，按 OBS object key 组织成 ZIP + manifest.json。
 * <p>已实现：版本解析前置（latest→具体版本号）+ t_mapping 递归遍历（不过滤共享资源）+
 * 根 IR/子 IR/model-service/model-auth/KB 连接+引用/skill/metadata 收集 + 平台模型特判 +
 * STRATEGY 递归（service_id_list + auth_id_list）+ KB reranker/model 模型递归 +
 * 子 IR 版本以父 IR 内嵌 ir_path 为准（含 SubWorkflow components[].configs.reference.path）+
 * authId 从 IR 5 处提取 + 流式 ZIP 打包（二进制技能走 readObsFileStream，逐资产不常驻内存）+
 * manifest + SHA256 + 根 IR/metadata 缺失终止 + resourceId 归属校验（防越权 IDOR）+ assets 上限 + 并发信号量。
 * <p>留增量补全：资产预览接口（preview，PRD 5.2/SDD 4.3.2）。
 */
@Slf4j
@Component
public class RuntimeAssetExporter {

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private SkillMapper skillMapper;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private PublishUtils publishUtils;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    /** t_mapping 递归深度上限（防止异常循环引用导致栈溢出） */
    private static final int MAX_MAPPING_DEPTH = 20;

    /** JSON 树递归深度上限（extractAuthIds 遍历用户构建的 IR，防深嵌套栈溢出，对齐 MAX_MAPPING_DEPTH 防护思路） */
    private static final int MAX_JSON_DEPTH = 50;

    /** assets 数量上限默认值（SDD 9.1）：@Value 缺省值 + 非法配置（<=0）回退值，单一来源 */
    private static final int DEFAULT_MAX_ASSETS = 100;

    /** assets 数量上限（SDD 9.1：超限报错提示，防大型智能体导出超时） */
    @org.springframework.beans.factory.annotation.Value("${export.runtime-asset.max-assets:" + DEFAULT_MAX_ASSETS + "}")
    private int maxAssets;

    /** 并发导出上限（SDD 4.5：Semaphore 信号量，快速失败） */
    @org.springframework.beans.factory.annotation.Value("${export.runtime-asset.max-concurrent:5}")
    private int maxConcurrent;

    /** manifest source.environment 来源：spring.profiles.active（可能逗号分隔多 profile，取首个），缺省 dev */
    @org.springframework.beans.factory.annotation.Value("${spring.profiles.active:dev}")
    private String springProfile;

    /**
     * manifest.json 序列化器：用 Jackson 识别 {@link RuntimeAssetManifest} 上的
     * {@code com.fasterxml.jackson.annotation.JsonProperty} 蛇形契约
     * （manifest_version/export_id/total_size_bytes/...）；fastjson2 不识别 Jackson 注解会输出驼峰，
     * 破坏导入工具读取的蛇形契约（bug004 #2）。NON_NULL 纳入策略对齐 fastjson2 默认省空字段行为。
     */
    private static final ObjectMapper MANIFEST_MAPPER = new ObjectMapper()
        .setSerializationInclusion(JsonInclude.Include.NON_NULL);

    private java.util.concurrent.Semaphore exportSemaphore;

    @PostConstruct
    private void initSemaphore() {
        // 兜底：maxConcurrent 配 0 或负数时 Semaphore 永远拿不到许可，会导致导出永久 busy。
        this.exportSemaphore = new java.util.concurrent.Semaphore(Math.max(1, maxConcurrent));
        // 兜底（巡检 #11）：maxAssets 配 0 或负数时，根 IR 入包即触发 EXPORT_LENGTH_TOO_LARGE，致运行时资产导出
        // 完全不可用。非正值视为误配，回退默认上限。注意不能像 maxConcurrent 仅 clamp 到 1：最小导出需
        // 根 IR + metadata ≥ 2 个 asset，maxAssets=1 时 metadata（第 2 个，failOnLimit=true）入包仍抛异常。
        if (maxAssets <= 0) {
            maxAssets = DEFAULT_MAX_ASSETS;
        }
    }

    /** 资产类型常量（manifest 中 type 字段取值） */
    private static final String TYPE_AGENT_IR = "agent_ir";
    private static final String TYPE_WORKFLOW_IR = "workflow_ir";
    private static final String TYPE_MODEL_SERVICE = "model_service";
    private static final String TYPE_MODEL_AUTH = "model_auth";
    private static final String TYPE_KB_CONNECTION = "kb_connection";
    private static final String TYPE_KB_REFERENCE = "kb_reference";
    private static final String TYPE_METADATA = "metadata";
    private static final String TYPE_SKILL = "skill";

    /** 平台模型 project_id 取值（runtime PLATFORM_PROJECT_IDS = {"SYSTEM"}） */
    private static final String PLATFORM_SYSTEM = "SYSTEM";

    /** t_mapping resourceType 常量 */
    private static final String RES_TYPE_WORKFLOW = "workflow";
    private static final String RES_TYPE_AGENT = "agent";
    private static final String RES_TYPE_CONTROLLER = "controller";
    private static final String RES_TYPE_MODEL = "model";
    private static final String RES_TYPE_STRATEGY = "strategy";
    private static final String RES_TYPE_REPO = "repo";
    private static final String RES_TYPE_SKILL = "skill";

    /**
     * 导出运行时资产，返回 ZIP 资源（供前端直接下载，不走 staging bucket）。
     * 复用 doExportRuntimeAssetZip 的收集+打包逻辑；ZIP 先落临时文件，响应读取后删除，避免整包常驻内存。
     *
     * @param projectId    请求显式 projectId（与 RequestContext 校验一致性，防越权）
     * @param workspaceId  请求显式 workspaceId（与 RequestContext 校验一致性，防越权）
     */
    public Resource exportRuntimeAssetZip(String projectId, String workspaceId,
        String resourceType, String resourceId, String version) {
        // 越权校验：显式 projectId/workspaceId 必须与 RequestContext（拦截器从鉴权注入）一致。
        // bug005 #3：上下文为空时直接拒绝（fail-closed），不再放行——否则 validateResourceOwnership
        // 会完全信任请求参数中的 project_id/workspace_id，攻击者可传他人 project/workspace/resourceId
        // 越权导出他人 IR+模型鉴权+KB+技能。导出 API 走鉴权，无合法的空上下文场景。
        String ctxProjectId = RequestContextUtils.getRequestProjectId();
        String ctxWorkspaceId = RequestContextUtils.getRequestWorkspaceId();
        if (StringUtils.isBlank(ctxProjectId) || !ctxProjectId.equals(projectId)) {
            log.error("runtime_asset_export_forbidden|request_project_id={}|ctx_project_id={}", projectId, ctxProjectId);
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID,
                "project_id does not match the authenticated context");
        }
        if (StringUtils.isBlank(ctxWorkspaceId) || !ctxWorkspaceId.equals(workspaceId)) {
            log.error("runtime_asset_export_forbidden|request_workspace_id={}|ctx_workspace_id={}",
                workspaceId, ctxWorkspaceId);
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID,
                "workspace_id does not match the authenticated context");
        }
        // 越权校验：resourceId 必须归属当前 (projectId, workspaceId)。
        // 复用现有编辑态导出的归属校验（AgentExportService.validExportWorkflows / AgentMapper.selectByProjectIdAndWorkspaceId），
        // 否则用户可传他人 workspace 的 resourceId 越权导出其 IR+模型鉴权+KB+技能（OBS 路径与 t_mapping 均不带 workspace 过滤）。
        validateResourceOwnership(projectId, workspaceId, resourceType, resourceId);
        if (!exportSemaphore.tryAcquire()) {
            throw new AgentStudioException(StudioError.EXPORT_RESOURCE_COMMON_ERROR,
                "export task busy, try later");
        }
        try {
            return doExportRuntimeAssetZip(resourceType, resourceId, version);
        } finally {
            exportSemaphore.release();
        }
    }

    /**
     * 校验 resourceId 归属当前 (projectId, workspaceId)，防越权导出他人资产（SDD 安全/巡检 #2）。
     * 复用现有编辑态导出的归属校验语义：
     * <ul>
     *   <li>agent/controller → {@link AgentMapper#selectByProjectIdAndWorkspaceId}，null 即无权限</li>
     *   <li>workflow → {@link WorkflowMapper#selectByWorkflowIds}，空即无权限（对齐 AgentExportService.validExportWorkflows）</li>
     * </ul>
     */
    private void validateResourceOwnership(String projectId, String workspaceId, String resourceType,
        String resourceId) {
        if (RES_TYPE_WORKFLOW.equals(resourceType)) {
            List<com.openjiuwen.studio.agent.manager.entity.WorkflowEntity> workflows =
                workflowMapper.selectByWorkflowIds(projectId, workspaceId, List.of(resourceId));
            if (workflows == null || workflows.isEmpty()) {
                log.error("runtime_asset_export_forbidden|resource_type={}|resource_id={}|project_id={}|workspace_id={}",
                    resourceType, resourceId, projectId, workspaceId);
                throw new AgentStudioException(StudioError.WORKFLOW_NO_PERMISSION, resourceId);
            }
            return;
        }
        // agent / controller
        if (agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, resourceId) == null) {
            log.error("runtime_asset_export_forbidden|resource_type={}|resource_id={}|project_id={}|workspace_id={}",
                resourceType, resourceId, projectId, workspaceId);
            throw new AgentStudioException(StudioError.USER_WORKSPACE_PERMISSION_INVALID,
                "resource does not belong to the authenticated workspace");
        }
    }

    private Resource doExportRuntimeAssetZip(String resourceType, String resourceId, String version) {
        String projectId = RequestContextUtils.getRequestProjectId();
        String workspaceId = RequestContextUtils.getRequestWorkspaceId();
        String exportId = UUID.randomUUID().toString();
        long startMs = System.currentTimeMillis();
        log.info("runtime_asset_export_start|export_id={}|resource_type={}|resource_id={}|version={}",
            exportId, resourceType, resourceId, version);

        // 0. 版本解析（前置，必须）—— latest → 具体发布版本号
        String resolvedVersion = resolvePublishVersion(resourceType, resourceId, version);
        log.info("runtime_asset_export_resolved_version|export_id={}|resource_id={}|resolved_version={}",
            exportId, resourceId, resolvedVersion);

        // 1. 复用现有依赖遍历（不调 filterShareResource —— 运行态按父 IR 内嵌 ir_path 加载共享子资源）
        List<MappingEntity> allMappings = new ArrayList<>();
        List<MappingEntity> rootMappings =
            mappingMapper.selectByAppIdAndAppVersion(resourceId, resolvedVersion, null, null);
        collectMappingsRecursive(allMappings, rootMappings);

        // 2. 构建 OBS object key 清单（根资产按 resourceType 分流）
        Set<String> collectedKeys = new HashSet<>();
        List<ManifestAsset> assets = new ArrayList<>();
        // 单次导出内 OBS 读取缓存：收集阶段（提 skill/authId）与打包阶段会读同一批 IR/model-service，
        // 去重避免 2~3 倍重复 OBS 往返（model-service 在 collectModelAssets/collectModelAuthFromIrs/build 各读一次）。
        Map<String, String> obsCache = new HashMap<>();
        // 2a. 根 IR
        String rootIrKey = buildRootIrKey(resourceType, resourceId, resolvedVersion);
        addAsset(assets, collectedKeys, rootIrKey, rootIrType(resourceType));
        // 2b. 子 IR（workflow/agent/controller）+ model + KB + skill，从 t_mapping 收集
        collectAssetKeysFromMappings(assets, collectedKeys, allMappings, projectId, obsCache);
        // 2c. 发布元数据
        String metadataKey = buildMetadataKey(resourceId);
        addAsset(assets, collectedKeys, metadataKey, TYPE_METADATA);
        // 2d. 从根/子 IR 提取 skill/子IR ir_path 对齐/authId（SDD 5.1/5.2/5.4）
        List<ManifestAsset> irAssets = assets.stream()
            .filter(a -> TYPE_AGENT_IR.equals(a.getType()) || TYPE_WORKFLOW_IR.equals(a.getType()))
            .toList();
        Set<String> irAuthIds = collectIrDerivedAssets(assets, collectedKeys, irAssets, projectId, obsCache);
        // 2e. model/KB：按版本对齐后的最终 IR 版本查 t_mapping 收集（巡检 P1-2，防旧版本 model/KB 残留）
        collectModelKbAssetsFromFinalIrs(assets, collectedKeys, projectId, obsCache);
        // 2f. model-auth：用 IR 提取的 authId 补充 model-auth 资产（SDD 5.2，优先于 model-service.auth_id）
        collectModelAuthFromIrs(assets, collectedKeys, irAssets, irAuthIds, projectId, obsCache);

        // SDD 9.1：assets 数量上限校验（防大型智能体导出超时）
        if (assets.size() > maxAssets) {
            throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE,
                "assets count " + assets.size() + " exceeds max " + maxAssets);
        }

        // 3. 读取 OBS 文件 + 打包 ZIP + 构建 manifest
        RuntimeAssetManifest manifest = buildManifest(exportId, resourceType, resourceId, resolvedVersion,
            projectId, workspaceId, assets);
        boolean isHistoryExport = StringUtils.isNotBlank(version)
            && !Constants.LATEST_PUBLISH_VERSION.equals(version);
        // 收集阶段缓存只用于避免重复 OBS 往返；打包前释放，避免全部文本资产随缓存常驻内存。
        obsCache.clear();
        Resource zipResource = buildZipWithManifest(manifest, assets, rootIrKey, isHistoryExport,
            resolvedVersion, resourceType);

        // 返回临时文件资源（供前端下载，不走 staging bucket）：写响应时流式读取，关流后删除临时文件。
        long durationMs = System.currentTimeMillis() - startMs;
        int missingCount = (int) assets.stream().filter(a -> "missing".equals(a.getStatus())).count();
        String status = missingCount == 0 ? "completed" : "completed_with_missing";
        log.info("runtime_asset_export_end|export_id={}|resource_type={}|resource_id={}|status={}"
            + "|asset_count={}|missing_count={}|duration_ms={}|total_size={}",
            exportId, resourceType, resourceId, status, assets.size(), missingCount, durationMs,
            manifest.getSummary().getTotalSizeBytes());
        return zipResource;
    }

    /**
     * 版本解析（SDD 5.0，前置）：latest → 具体发布版本号。
     * 禁止把 null/"latest" 传给 selectByAppIdAndAppVersion。
     */
    private String resolvePublishVersion(String resourceType, String resourceId, String version) {
        if (StringUtils.isBlank(version) || Constants.LATEST_PUBLISH_VERSION.equals(version)) {
            // SDD 5.0: Redis 优先回退 OBS。未发布资源在 OBS 无元数据 → PublishUtils.getPublish 经
            // getObjectOrNull→fileStore.readOrNull 特判 404 返回 null（仅此收敛点 404→null），
            // getPublish 据此返回 null → meta==null 抛 EXPORT_RESOURCE_NOT_EXISTS(400)。{0} 占位填 resourceType。
            // 注：read/downloadObsFile 在 404 时仍抛 OBS_FAILED（5xx 亦抛），404→null 语义仅经 readOrNull 收敛于此。
            com.openjiuwen.studio.agent.common.bo.AgentMetadata meta =
                publishUtils.getPublish(resourceId, Constants.LATEST_PUBLISH_VERSION, mgObsService);
            if (meta == null || StringUtils.isBlank(meta.getVersionId())) {
                log.error("resolvePublishVersion failed, metadata not found for: {}", resourceId);
                throw new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS, resourceType);
            }
            return meta.getVersionId();
        }
        // 具体版本号 → 校验存在
        ReleaseVersion rv = releaseVersionMapper.selectByAppIdAndVersionId(resourceId, version);
        if (rv == null) {
            // 对外仍用 EXPORT_RESOURCE_NOT_EXISTS（保持 03601001 契约）, 日志带 version 区分两种失败模式。
            log.error("resolvePublishVersion failed, release version not exist for: {}/{}", resourceId, version);
            throw new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS, resourceType);
        }
        return version;
    }

    /**
     * 递归收集 t_mapping（复用 buildSubExportResources 语义，不过滤共享资源）。
     * SDD 5.1：不调 filterShareResource，运行态按父 IR 内嵌 ir_path 加载共享子资源。
     * <p>去重：同一 (resourceId, resourceType, resourceVersion) 只处理一次，防止循环引用无限递归。
     */
    private void collectMappingsRecursive(List<MappingEntity> acc, List<MappingEntity> mappings) {
        collectMappingsRecursive(acc, mappings, new HashSet<>(), 0);
    }

    private void collectMappingsRecursive(List<MappingEntity> acc, List<MappingEntity> mappings,
        Set<String> visited, int depth) {
        if (mappings == null || mappings.isEmpty() || depth > MAX_MAPPING_DEPTH) {
            return;
        }
        List<MappingEntity> nextLevel = new ArrayList<>();
        for (MappingEntity m : mappings) {
            // 去重：同一资源（resourceId+resourceType+resourceVersion）只处理一次
            String key = mappingKey(m);
            if (!visited.add(key)) {
                continue;
            }
            // 巡检 #8（@336）+ 巡检 #13（依赖丢失）：子资源 resourceVersion 为 null（跟随 latest）时，
            // 之前直接 continue 既不入 acc 也不递归，致其 t_mapping 引用的 model/KB/strategy/skill 依赖
            // 整体丢失（运行包不完整）。现补齐具体发布版本后递归收集依赖；补齐失败（未发布/异常）才保留
            // 本体入 acc、跳过递归（不阻断导出，本体正确版本由版本对齐阶段从父 IR ir_path 补齐）。
            if (RES_TYPE_WORKFLOW.equals(m.getResourceType()) || RES_TYPE_AGENT.equals(m.getResourceType())
                || RES_TYPE_CONTROLLER.equals(m.getResourceType())) {
                String resVer = m.getResourceVersion();
                if (StringUtils.isBlank(resVer)) {
                    try {
                        resVer = resolvePublishVersion(m.getResourceType(), m.getResourceId(), null);
                        m.setResourceVersion(resVer); // 补齐具体发布版本，使本体 buildKey 正确 + 依赖可按版本递归
                    } catch (Exception e) {
                        log.warn("runtime_asset_export_skip_null_version_mapping|resource_id={}|type={}|reason=null_version_resolve_failed|{}",
                            m.getResourceId(), m.getResourceType(), e.getMessage());
                        acc.add(m); // 保留本体（版本对齐阶段从父 IR ir_path 补正确版本），跳过依赖递归
                        continue;
                    }
                }
                acc.add(m);
                List<MappingEntity> childMappings =
                    mappingMapper.selectByAppIdAndAppVersion(m.getResourceId(), m.getResourceVersion(), null, null);
                if (childMappings != null && !childMappings.isEmpty()) {
                    nextLevel.addAll(childMappings);
                }
            } else {
                // 巡检（P1-2）：model/KB/strategy/skill 不在此收集。model/KB 收集挪到
                // collectModelKbAssetsFromFinalIrs，按版本对齐后的最终 IR 版本查 t_mapping 收集，
                // 避免 t_mapping 旧版本 model/KB 入包后版本对齐替换子 IR 时无法撤销（新 IR + 旧依赖错配）。
                // skill 在 collectIrDerivedAssets 从 IR JSON 提取。
            }
        }
        if (!nextLevel.isEmpty()) {
            collectMappingsRecursive(acc, nextLevel, visited, depth + 1);
        }
    }

    private static String mappingKey(MappingEntity m) {
        return (m.getResourceId() == null ? "" : m.getResourceId()) + "|"
            + (m.getResourceType() == null ? "" : m.getResourceType()) + "|"
            + (m.getResourceVersion() == null ? "" : m.getResourceVersion());
    }

    /**
     * 从 t_mapping 收集子 IR 资产 key（SDD 4.2.4）。
     * <p>仅收集 workflow/agent/controller 子 IR。model/KB 收集挪到 collectModelKbAssetsFromFinalIrs
     * （巡检 P1-2，按版本对齐后最终 IR 版本查 t_mapping，防旧版本 model/KB 残留）；
     * skill 在 collectIrDerivedAssets 从 IR JSON 提取。
     */
    private void collectAssetKeysFromMappings(List<ManifestAsset> assets, Set<String> collectedKeys,
        List<MappingEntity> mappings, String rootProjectId, Map<String, String> obsCache) {
        for (MappingEntity m : mappings) {
            String resType = m.getResourceType();
            String resId = m.getResourceId();
            String resVer = m.getResourceVersion();
            switch (resType) {
                case RES_TYPE_WORKFLOW:
                    addAsset(assets, collectedKeys, buildWorkflowIrKey(resId, resVer), TYPE_WORKFLOW_IR);
                    break;
                case RES_TYPE_AGENT:
                case RES_TYPE_CONTROLLER:
                    addAsset(assets, collectedKeys, buildAgentIrKey(resId, resVer), TYPE_AGENT_IR);
                    break;
                // 巡检（P1-2）：model/strategy/repo 收集挪到 collectModelKbAssetsFromFinalIrs，
                // 按版本对齐后的最终 IR 版本查 t_mapping 收集（防 t_mapping 旧版本 model/KB 残留）。
                // skill 在 collectIrDerivedAssets 从 IR JSON 提取。
                default:
                    break;
            }
        }
    }

    /**
     * 从根/子 IR 提取 skill 资产 + 子 IR ir_path 对齐 + authId 提取（SDD 5.1/5.2/5.4）。
     * <p>工作队列（worklist）逐个处理已收集的 agent_ir/workflow_ir 资产，读 IR JSON：
     * <ul>
     *   <li>SDD 5.4：取 configs.skills.skill_info[].skill_path（skill 资产）</li>
     *   <li>SDD 5.1：取 configs.workflows[].ir_path / configs.agents[].ir_path
     *       （子资产版本以父 IR 内嵌 ir_path 为准，t_mapping 版本仅交叉校验）</li>
     *   <li>SDD 5.2：递归提取所有 extension.authId（5 处：modelConfig/工作流model/LLM节点/Questioner/意图检测）</li>
     * </ul>
     * <p>版本对齐产生的新版本子 IR（替换 t_mapping 旧版本）入队继续抽取其 skill/child ir_path/authId
     * （bug004 #3：原遍历调用前快照，新版本子 IR 不再回扫致漏导依赖）；
     * processedKeys+collectedKeys 去重防环。
     * @return 提取到的 authId 集合（供 model-auth 收集使用）
     */
    private Set<String> collectIrDerivedAssets(List<ManifestAsset> assets, Set<String> collectedKeys,
        List<ManifestAsset> irAssets, String rootProjectId, Map<String, String> obsCache) {
        Set<String> authIds = new HashSet<>();
        // resourceId → 已收集的 IR asset（用于子 IR 版本冲突检测：t_mapping 版本 vs 父 IR 内嵌 ir_path 版本）
        Map<String, ManifestAsset> irByResourceId = new HashMap<>();
        for (ManifestAsset existing : irAssets) {
            String rid = parseResourceIdFromIrKey(existing.getKey());
            if (rid != null) {
                irByResourceId.put(rid, existing);
            }
        }
        // 工作队列：初始为调用前快照；版本对齐新增的子 IR 入队继续抽取（bug004 #3）。processedKeys 防同 key 重复处理。
        Deque<ManifestAsset> worklist = new ArrayDeque<>(irAssets);
        Set<String> processedKeys = new HashSet<>();
        while (!worklist.isEmpty()) {
            ManifestAsset asset = worklist.poll();
            if (!processedKeys.add(asset.getKey())) {
                continue; // 同 key 已处理（去重防环）
            }
            String irJson;
            try {
                irJson = getCachedObject(asset.getKey(), obsCache);
            } catch (Exception e) {
                continue;
            }
            if (StringUtils.isBlank(irJson)) {
                continue;
            }
            Set<String> childIrPaths = new HashSet<>();
            try {
                JSONObject ir = JSON.parseObject(irJson);
                JSONObject configs = ir.getJSONObject("configs");
                // 巡检（P1）：configs==null 不再 continue，否则 collectSubWorkflowPaths/extractAuthIds
                // 被整体跳过——这两处不依赖顶层 configs（SubWorkflow 子工作流在 components[].configs.reference.path，
                // authId 递归遍历整个 IR 树），漏执行会漏导 SubWorkflow 子 IR / model-auth，运行包不完整。
                // 仅在读取 configs 下技能和 workflows/agents 子 IR 路径时判空。
                if (configs != null) {
                    // SDD 5.4：skill_info[].skill_path
                    JSONObject skills = configs.getJSONObject("skills");
                    if (skills != null) {
                        JSONArray skillInfo = skills.getJSONArray("skill_info");
                        if (skillInfo != null) {
                            for (int i = 0; i < skillInfo.size(); i++) {
                                JSONObject skill = skillInfo.getJSONObject(i);
                                String skillPath = skill.getString("skill_path");
                                if (StringUtils.isNotBlank(skillPath)) {
                                    // bug007 #1：skill_path 必须归属当前用户（格式 {userId}/skills/...），
                                    // 防 IR 可构造 user-{他人userId}/skills/... 跨用户读取他人技能。
                                    if (!isOwnedSkillPath(skillPath)) {
                                        log.warn("runtime_asset_export_skill_skipped|skill_path={}|reason=unowned",
                                            skillPath);
                                        continue;
                                    }
                                    addAsset(assets, collectedKeys, skillPath, TYPE_SKILL);
                                }
                            }
                        }
                    }
                    // SDD 5.1：configs.workflows[].ir_path / configs.agents[].ir_path（子资产版本对齐）
                    collectChildIrPaths(configs, "workflows", childIrPaths);
                    collectChildIrPaths(configs, "agents", childIrPaths);
                }
                // SDD 2.5/5.1：SubWorkflow 节点子工作流路径 components[].configs.reference.path（不依赖顶层 configs，始终执行）
                collectSubWorkflowPaths(ir, childIrPaths);
                // SDD 5.2：递归提取所有 extension.authId（不依赖顶层 configs，始终执行）
                extractAuthIds(ir, authIds);
            } catch (Exception e) {
                log.warn("collectIrDerivedAssets parse IR failed, key={}. {}", asset.getKey(), e.getMessage());
            }
            // SDD 5.1：子资产版本以父 IR 内嵌 ir_path 为准。t_mapping 版本与 ir_path 版本冲突时，
            // ir_path 胜出（运行态按父 IR 内嵌 ir_path 加载子资产），并在 manifest note 记录差异（巡检 #3/#4）。
            // 版本对齐产生的新子 IR 入队，使其 skill/更深 child ir_path/authId 也被收集（bug004 #3）。
            for (String irPath : childIrPaths) {
                String type = irPath.startsWith("workflow/") ? TYPE_WORKFLOW_IR : TYPE_AGENT_IR;
                String rid = parseResourceIdFromIrKey(irPath);
                // bug007 #1：子 IR ir_path 合法性（防路径遍历/跨租户 OBS 读取）是主防线，必须通过。
                // 巡检 #12（🔴 越权）：子 IR 须归属当前 workspace 或经 t_share_resource 共享授权给当前
                // workspace 才放行，否则 fail-closed（continue，不读 OBS、不入包）。此前仅 warn 不跳过，
                // 任意 agent/ir/、workflow/ir/ 合法前缀路径只要 rid 可枚举/泄露即被跨工作空间读取打包进 ZIP。
                // isOwnedOrSharedChildIr：归属通过→放行；归属不通过但 checkWorkspaceAuthByResourceOrNot
                // 共享授权→放行（跨 workspace 共享子 IR 是合法场景，复用 retrieveAgent 同模式）；两者皆否→拒绝。
                if (!isValidAssetKey(irPath, type)) {
                    log.warn("runtime_asset_export_child_ir_skipped|ir_path={}|resource_id={}|reason=invalid_key",
                        irPath, rid);
                    continue;
                }
                if (!isOwnedOrSharedChildIr(rid, type)) {
                    log.warn("runtime_asset_export_child_ir_skipped|ir_path={}|resource_id={}|reason=not_owned_not_shared",
                        irPath, rid);
                    continue;
                }
                ManifestAsset existing = (rid != null) ? irByResourceId.get(rid) : null;
                if (existing != null) {
                    if (existing.getKey().equals(irPath)) {
                        continue; // 同 key 已收集，去重
                    }
                    // 版本冲突：ir_path 为准，移除 t_mapping 版本，加入 ir_path 版本（校验已通过，安全 remove）
                    String oldVer = parseVersionFromIrKey(existing.getKey());
                    String oldKey = existing.getKey();
                    assets.remove(existing);
                    collectedKeys.remove(oldKey);
                    // 巡检 #9（@472/@489）：旧版本子 IR 从 worklist 移除并标记已处理，防止其继续被 poll
                    // 处理产生陈旧派生（旧 skill/authId/child-ir 入包，与新 IR 版本错配）。
                    // worklist.remove 是 O(n)，worklist 通常小（IR 数量个位数），可接受。
                    // processedKeys.add(oldKey) 防止旧 IR 若已被 poll 但派生尚未清理时重复处理。
                    worklist.remove(existing);
                    processedKeys.add(oldKey);
                    ManifestAsset added = addAsset(assets, collectedKeys, irPath, type);
                    if (added != null) {
                        added.setNote("version aligned to parent IR ir_path; t_mapping version=" + oldVer);
                        if (rid != null) {
                            irByResourceId.put(rid, added);
                        }
                        worklist.add(added);
                    }
                    log.warn("runtime_asset_export_version_mismatch|resource_id={}|mapping_version={}|ir_path={}",
                        rid, oldVer, irPath);
                } else {
                    ManifestAsset added = addAsset(assets, collectedKeys, irPath, type);
                    if (added != null) {
                        if (rid != null) {
                            irByResourceId.put(rid, added);
                        }
                        worklist.add(added);
                    }
                }
            }
        }
        return authIds;
    }

    /**
     * 按版本对齐后的最终 IR 集合收集 model/KB 资产（巡检 P1-2）。
     * <p>model/KB 收集延后到版本对齐后，按每个 IR 的最终版本查 t_mapping 收集，天然按新版本收集，
     * 无旧版本残留（修复"新 IR + 旧依赖"错配）。
     * <p>此前 model/KB 在 collectAssetKeysFromMappings 按 t_mapping 版本（可能旧）收集，版本对齐替换
     * 子 IR 时，旧版本 model/KB 已入 assets 无法撤销（旧子 IR 的 t_mapping 派生无归属信息，
     * worklist.remove 只移除旧 IR 本体不撤销其 model/KB 派生）；多层场景下旧孙 IR 派生已入包也不回滚。
     * <p>共享资源去重由 collectedKeys 保证：多个 IR 引用同一 model/KB，首个收集入包，后续跳过。
     * @param rootProjectId 根应用 projectId（平台模型 project_id=SYSTEM 时 authProjectId 回退用）
     */
    private void collectModelKbAssetsFromFinalIrs(List<ManifestAsset> assets, Set<String> collectedKeys,
        String rootProjectId, Map<String, String> obsCache) {
        // 遍历所有最终版本 IR（根 + 子 + 孙，版本对齐后旧版本已移除），按各自最终版本查 t_mapping 收集 model/KB
        List<ManifestAsset> finalIrs = assets.stream()
            .filter(a -> TYPE_AGENT_IR.equals(a.getType()) || TYPE_WORKFLOW_IR.equals(a.getType()))
            .toList();
        for (ManifestAsset irAsset : finalIrs) {
            String rid = parseResourceIdFromIrKey(irAsset.getKey());
            String rver = parseVersionFromIrKey(irAsset.getKey());
            if (rid == null || "?".equals(rver)) {
                continue; // 非标准 IR key，无法查 t_mapping
            }
            List<MappingEntity> irMappings;
            try {
                irMappings = mappingMapper.selectByAppIdAndAppVersion(rid, rver, null, null);
            } catch (Exception e) {
                log.warn("collectModelKbAssetsFromFinalIrs query t_mapping failed, rid={}, ver={}. {}",
                    rid, rver, e.getMessage());
                continue;
            }
            if (irMappings == null || irMappings.isEmpty()) {
                continue;
            }
            for (MappingEntity m : irMappings) {
                String resType = m.getResourceType();
                String resId = m.getResourceId();
                if (RES_TYPE_MODEL.equals(resType) || RES_TYPE_STRATEGY.equals(resType)) {
                    collectModelAssets(assets, collectedKeys, resId, resType, rootProjectId, obsCache, null);
                } else if (RES_TYPE_REPO.equals(resType)) {
                    collectKbAssets(assets, collectedKeys, resId, rootProjectId, obsCache);
                }
                // workflow/agent/controller/skill 跳过：IR 已收集（版本对齐完成）；skill 在 collectIrDerivedAssets 提取
            }
        }
    }

    /** 从 configs.workflows / configs.agents 数组提取 ir_path */
    private void collectChildIrPaths(JSONObject configs, String key, Set<String> childIrPaths) {
        JSONArray arr = configs.getJSONArray(key);
        if (arr == null) {
            return;
        }
        for (int i = 0; i < arr.size(); i++) {
            JSONObject item = arr.getJSONObject(i);
            String irPath = item.getString("ir_path");
            if (StringUtils.isNotBlank(irPath)) {
                childIrPaths.add(irPath);
            }
        }
    }

    /**
     * 从 components[].configs.reference.path 提取 SubWorkflow 子工作流 IR 路径（SDD 2.5/5.1）。
     * SubWorkflow 节点的子工作流引用不在 configs.workflows/agents 数组里，而在 components[].configs.reference.path。
     */
    private void collectSubWorkflowPaths(JSONObject ir, Set<String> childIrPaths) {
        JSONArray components = ir.getJSONArray("components");
        if (components == null) {
            return;
        }
        for (int i = 0; i < components.size(); i++) {
            JSONObject component = components.getJSONObject(i);
            if (component == null) {
                continue;
            }
            JSONObject configs = component.getJSONObject("configs");
            if (configs == null) {
                continue;
            }
            JSONObject reference = configs.getJSONObject("reference");
            if (reference != null) {
                String irPath = reference.getString("path");
                if (StringUtils.isNotBlank(irPath)) {
                    childIrPaths.add(irPath);
                }
            }
        }
    }

    /**
     * 递归提取 IR 中所有 extension.authId（SDD 5.2，5 处位置）。
     * 策略：递归遍历 JSON 树，对每个含 "extension" 的对象，取 extension.authId。
     * 覆盖 modelConfig/工作流model/LLM节点/Questioner/意图检测等所有含 modelName+extension 的位置，
     * 不逐个硬编码路径（防新增节点类型遗漏）。
     */
    private void extractAuthIds(Object node, Set<String> authIds) {
        extractAuthIds(node, authIds, 0);
    }

    private void extractAuthIds(Object node, Set<String> authIds, int depth) {
        if (node == null || depth > MAX_JSON_DEPTH) {
            return;
        }
        if (node instanceof JSONObject obj) {
            JSONObject ext = obj.getJSONObject("extension");
            if (ext != null) {
                String authId = ext.getString("authId");
                if (StringUtils.isNotBlank(authId)) {
                    authIds.add(authId);
                }
            }
            for (String k : obj.keySet()) {
                extractAuthIds(obj.get(k), authIds, depth + 1);
            }
        } else if (node instanceof JSONArray arr) {
            for (int i = 0; i < arr.size(); i++) {
                extractAuthIds(arr.get(i), authIds, depth + 1);
            }
        }
    }

    /**
     * 用 IR 提取的 authId 补充 model-auth 资产（SDD 5.2，作为 collectModelAssets 的防御性补充）。
     * <p>对全部 IR authId × 全部已收集 model-service 的 (providerId, projectId) 做笛卡尔积构建 auth key。
     * 这是"宁可多导不漏导"的取舍，正确性不受影响：
     * <ul>
     *   <li>正确组合（IR authId + 其所属 model-service 的 provider/project）必然在笛卡尔积中 → 不漏；
     *       且 collectModelAssets 已按 model-service.auth_metadata_id 构建过同一正确 key（collectedKeys 去重）。</li>
     *   <li>错误组合的 key 要么 OBS 不存在（标 missing、不入包），要么是别的模型的 auth 文件（运行态不会按此 key 加载），
     *       仅产生 manifest 噪声，无错配风险。</li>
     * </ul>
     * 不做精确 (modelName→model-service→provider) 映射：IR 中 extension.authId 与 modelName 的同级关系
     * 在 5 处位置命名不一（modelName/model_name），精确提取有漏导 authId 风险（运行态缺 auth 会调用失败），
     * 而"多导"仅是噪声——故保持笛卡尔。
     */
    private void collectModelAuthFromIrs(List<ManifestAsset> assets, Set<String> collectedKeys,
        List<ManifestAsset> irAssets, Set<String> irAuthIds, String rootProjectId, Map<String, String> obsCache) {
        if (irAuthIds.isEmpty()) {
            return;
        }
        // 收集所有已收集的 model-service 资产,读其 providerId/projectId
        List<ManifestAsset> modelServiceAssets = assets.stream()
            .filter(a -> TYPE_MODEL_SERVICE.equals(a.getType())).toList();
        for (ManifestAsset msAsset : modelServiceAssets) {
            String msJson;
            try {
                msJson = getCachedObject(msAsset.getKey(), obsCache);
            } catch (Exception e) {
                continue;
            }
            if (StringUtils.isBlank(msJson)) {
                continue;
            }
            // bug006：parseObject 包 try/catch —— model-service 文件损坏/非 JSON 时跳过该资产，不让 JSONException 冒泡返回 500。
            JSONObject msObj;
            try {
                msObj = JSON.parseObject(msJson);
            } catch (Exception e) {
                log.warn("collectModelAuthFromIrs parse model-service failed, key={}, skip. {}",
                    msAsset.getKey(), e.getMessage());
                continue;
            }
            // 巡检（P2）：JSON 字面量 "null" → parseObject 返回 null（不抛异常），按损坏/缺失处理，防后续 NPE。
            if (msObj == null) {
                log.warn("collectModelAuthFromIrs parse model-service null literal, key={}, skip.",
                    msAsset.getKey());
                continue;
            }
            // model-service 文件结构：{"type":"model", "data": {...}}
            JSONObject msData = msObj.getJSONObject("data");
            if (msData == null) {
                msData = msObj;
            }
            String providerId = msData.getString("provider_id");
            String modelProjectId = msData.getString("project_id");
            String authProjectId = (modelProjectId != null && PLATFORM_SYSTEM.equals(modelProjectId))
                ? rootProjectId : modelProjectId;
            // 对每个 IR 提取的 authId,构建 model-auth key(笛卡尔积,去重保证不遗漏)
            for (String authId : irAuthIds) {
                addModelAuthAsset(assets, collectedKeys, authProjectId, providerId, authId);
            }
        }
    }

    /**
     * 收集模型资产：model-service 配置 + model-auth 鉴权配置（SDD 5.2）。
     * <p>1. 读 model-service/ir/{modelServiceId}.json 取 providerId/projectId
     * <p>2. 平台模型特判：project_id=SYSTEM → authProjectId 用根应用 projectId（复刻 runtime _auth_project_id）
     * <p>3. authId 选取：explicitAuthId（STRATEGY auth_id_list 指定）优先，否则回退 model-service.auth_metadata_id
     * <p>4. STRATEGY 路由策略递归：读 service_id_list + auth_id_list（一一对应）逐子模型处理
     * <p>5. authId 空值回退：list 前缀下全部对象导出
     * <p>6. modelName 格式 deploymentId|serviceId 取第一段
     *
     * @param explicitAuthId 调用方指定的 authId（STRATEGY auth_id_list 逐子模型传入）；null 时回退 auth_metadata_id
     */
    private void collectModelAssets(List<ManifestAsset> assets, Set<String> collectedKeys,
        String modelServiceId, String resType, String rootProjectId, Map<String, String> obsCache,
        String explicitAuthId) {
        // modelServiceId 格式处理：deploymentId|serviceId 取第一段
        String serviceId = modelServiceId;
        if (modelServiceId != null && modelServiceId.contains("|")) {
            serviceId = modelServiceId.split("\\|")[0];
        }
        String modelServiceKey = buildModelServiceKey(serviceId);
        if (!collectedKeys.contains(modelServiceKey)) {
            addAsset(assets, collectedKeys, modelServiceKey, TYPE_MODEL_SERVICE);
        }
        // 防御式 gate（巡检 #10）：addAsset 已对非法 key 记 warn 跳过不入包，此处复核确保不以非法 key 读 OBS
        // （modelServiceId 来自 IR/service_id_list，可被构造；OBS key 扁平暂无跨租户，但防无效/越界读取放大）。
        if (!isValidAssetKey(modelServiceKey, TYPE_MODEL_SERVICE)) {
            return;
        }
        // 读 model-service 文件取 providerId/projectId
        String msJson;
        try {
            msJson = getCachedObject(modelServiceKey, obsCache);
        } catch (Exception e) {
            log.warn("collectModelAssets read model-service failed, key={}, skip model-auth. {}",
                modelServiceKey, e.getMessage());
            return;
        }
        if (StringUtils.isBlank(msJson)) {
            return;
        }
        // bug006：parseObject 包 try/catch —— model-service 文件损坏/非 JSON 时按 SDD 5.6 标 missing 继续，
        // 不让 JSONException 冒泡到 doExportRuntimeAssetZip 返回 500（破坏可靠性约定）。
        JSONObject msObj;
        try {
            msObj = JSON.parseObject(msJson);
        } catch (Exception e) {
            log.warn("collectModelAssets parse model-service failed, key={}, skip. {}", modelServiceKey, e.getMessage());
            return;
        }
        // 巡检（P2）：JSON 字面量 "null" → parseObject 返回 null（不抛异常），按损坏/缺失处理，防后续 NPE。
        if (msObj == null) {
            log.warn("collectModelAssets parse model-service null literal, key={}, skip.", modelServiceKey);
            return;
        }
        // model-service 文件结构：{"type":"model", "data": {provider_id, project_id, auth_metadata_id, ...}}
        // 字段在 data 嵌套对象里，非顶层
        JSONObject msData = msObj.getJSONObject("data");
        if (msData == null) {
            // 兼容：部分文件可能直接顶层存字段
            msData = msObj;
        }
        String providerId = msData.getString("provider_id");
        String modelProjectId = msData.getString("project_id");
        // 平台模型特判：project_id=SYSTEM → authProjectId 用根应用 projectId
        String authProjectId = (modelProjectId != null && PLATFORM_SYSTEM.equals(modelProjectId))
            ? rootProjectId : modelProjectId;

        if (RES_TYPE_STRATEGY.equals(resType)) {
            // SDD 5.2 STRATEGY 路由策略递归：service_id_list 与 auth_id_list 一一对应（auth_id_list 可为空/较短），
            // 逐子模型递归收集，并把对应 auth_id_list[i] 作为 explicitAuthId 传入（runtime _build_router_strategy 逐子模型 fail-fast）。
            String serviceIdList = msData.getString("service_id_list");
            String authIdList = msData.getString("auth_id_list");
            if (StringUtils.isNotBlank(serviceIdList)) {
                String[] svcIds = serviceIdList.split(",");
                String[] authIds = StringUtils.isNotBlank(authIdList) ? authIdList.split(",") : new String[0];
                for (int i = 0; i < svcIds.length; i++) {
                    String subServiceId = svcIds[i].trim();
                    if (StringUtils.isBlank(subServiceId)) {
                        continue;
                    }
                    String subAuthId = (i < authIds.length) ? authIds[i].trim() : null;
                    if (StringUtils.isBlank(subAuthId)) {
                        subAuthId = null;
                    }
                    collectModelAssets(assets, collectedKeys, subServiceId, RES_TYPE_MODEL, rootProjectId, obsCache,
                        subAuthId);
                }
            }
            return;
        }
        // authId 选取：explicitAuthId（STRATEGY auth_id_list 指定）优先，否则回退 model-service.auth_metadata_id。
        // IR 中 extension.authId 由 collectModelAuthFromIrs 笛卡尔补充（宁可多导不漏导）。
        String authId = StringUtils.isNotBlank(explicitAuthId) ? explicitAuthId : msData.getString("auth_metadata_id");
        addModelAuthAsset(assets, collectedKeys, authProjectId, providerId, authId);
    }

    /**
     * 添加 model-auth 资产。authId 为空时（V1 回退）list 前缀下全部对象导出。
     */
    private void addModelAuthAsset(List<ManifestAsset> assets, Set<String> collectedKeys,
        String authProjectId, String providerId, String authId) {
        if (StringUtils.isAnyBlank(authProjectId, providerId)) {
            return;
        }
        if (StringUtils.isBlank(authId)) {
            // SDD 5.2 V1 回退：authId 空时 list 前缀下全部 auth 对象导出
            String prefix = String.format("model-auth/auth/%s/%s/", authProjectId, providerId);
            log.info("model-auth authId empty, V1 fallback listing prefix: {}", prefix);
            try {
                List<String> authKeys = mgObsService.listObsObjectKeys(prefix);
                if (authKeys != null) {
                    for (String authKey : authKeys) {
                        if (StringUtils.isNotBlank(authKey)) {
                            addAsset(assets, collectedKeys, authKey, TYPE_MODEL_AUTH, false);
                        }
                    }
                }
            } catch (Exception e) {
                log.warn("model-auth V1 fallback list failed, prefix={}. {}", prefix, e.getMessage());
            }
            return;
        }
        String authKey = String.format("model-auth/auth/%s/%s/%s.json", authProjectId, providerId, authId);
        addAsset(assets, collectedKeys, authKey, TYPE_MODEL_AUTH, false);
    }

    /**
     * 收集知识库资产：KB 引用 + KB 连接（SDD 5.3）。
     * <p>1. 导出 kb-connection/ir/knowledge-base/{kbId}.json
     * <p>2. 从该文件读 connectionId，导出 kb-connection/ir/connection/{connId}.json
     */
    private void collectKbAssets(List<ManifestAsset> assets, Set<String> collectedKeys, String kbId,
        String rootProjectId, Map<String, String> obsCache) {
        String kbRefKey = buildKbReferenceKey(kbId);
        if (!collectedKeys.contains(kbRefKey)) {
            addAsset(assets, collectedKeys, kbRefKey, TYPE_KB_REFERENCE);
        }
        // 防御式 gate（巡检 #10）：非法 kbId 构造的 key 不读 OBS（addAsset 已记 warn 跳过不入包）。
        if (!isValidAssetKey(kbRefKey, TYPE_KB_REFERENCE)) {
            return;
        }
        // 读 KB 引用文件取 connectionId
        String kbJson;
        try {
            kbJson = getCachedObject(kbRefKey, obsCache);
        } catch (Exception e) {
            log.warn("collectKbAssets read kb-reference failed, key={}, skip kb-connection. {}",
                kbRefKey, e.getMessage());
            return;
        }
        if (StringUtils.isBlank(kbJson)) {
            return;
        }
        // bug006：parseObject 包 try/catch —— KB 引用文件损坏/非 JSON 时跳过，不让 JSONException 冒泡返回 500。
        JSONObject kbObj;
        try {
            kbObj = JSON.parseObject(kbJson);
        } catch (Exception e) {
            log.warn("collectKbAssets parse kb-reference failed, key={}, skip. {}", kbRefKey, e.getMessage());
            return;
        }
        // 巡检（P2）：JSON 字面量 "null" → parseObject 返回 null（不抛异常），按损坏/缺失处理，防后续 NPE。
        if (kbObj == null) {
            log.warn("collectKbAssets parse kb-reference null literal, key={}, skip.", kbRefKey);
            return;
        }
        String connectionId = kbObj.getString("connectionId");
        if (StringUtils.isNotBlank(connectionId)) {
            String connKey = String.format("kb-connection/ir/connection/%s.json", connectionId);
            addAsset(assets, collectedKeys, connKey, TYPE_KB_CONNECTION);
            // SDD 5.3：KB 连接配置可能含 reranker_config/model_config（引用模型），递归收集模型
            collectKbReferencedModels(assets, collectedKeys, connectionId, rootProjectId, obsCache);
        }
    }

    /**
     * KB 连接配置中 reranker_config/model_config 引用的模型，递归收集 model-service + model-auth（SDD 5.3，巡检 #5）。
     * <p>连接配置结构：{@code params[]} 数组，每项 {@code {code, value}}；其中 code=model_config/reranker_config
     * 的 value 是 JSON 字符串，含 {@code model_service_id}（embedding/reranker 模型）。
     * <p>对每个 model_service_id 调 collectModelAssets（explicitAuthId=null，authId 取 model-service.auth_metadata_id）。
     * 防御式：字段缺失/解析失败则 debug 跳过，不阻断导出。
     */
    private void collectKbReferencedModels(List<ManifestAsset> assets, Set<String> collectedKeys,
        String connectionId, String rootProjectId, Map<String, String> obsCache) {
        String connKey = String.format("kb-connection/ir/connection/%s.json", connectionId);
        // 防御式 gate（巡检 #10）：connKey 由 collectKbAssets 的 addAsset 校验并入包；复核合法性，
        // 非法 connectionId（来自 KB 引用文件，可被构造）构造的 key 不读 OBS（防无效/越界读取）。
        if (!isValidAssetKey(connKey, TYPE_KB_CONNECTION)) {
            return;
        }
        String connJson;
        try {
            connJson = getCachedObject(connKey, obsCache);
        } catch (Exception e) {
            log.warn("collectKbReferencedModels read connection failed, key={}, skip reranker. {}",
                connKey, e.getMessage());
            return;
        }
        if (StringUtils.isBlank(connJson)) {
            return;
        }
        try {
            JSONObject conn = JSON.parseObject(connJson);
            JSONArray params = conn.getJSONArray("params");
            if (params == null) {
                return;
            }
            for (int i = 0; i < params.size(); i++) {
                JSONObject param = params.getJSONObject(i);
                if (param == null) {
                    continue;
                }
                String code = param.getString("code");
                if (!"model_config".equals(code) && !"reranker_config".equals(code)) {
                    continue;
                }
                String valueJson = param.getString("value");
                if (StringUtils.isBlank(valueJson)) {
                    continue;
                }
                JSONObject mc = JSON.parseObject(valueJson);
                String modelServiceId = mc.getString("model_service_id");
                if (StringUtils.isNotBlank(modelServiceId)) {
                    collectModelAssets(assets, collectedKeys, modelServiceId, RES_TYPE_MODEL, rootProjectId, obsCache, null);
                }
            }
        } catch (Exception e) {
            log.warn("collectKbReferencedModels parse connection failed, connectionId={}. {}", connectionId,
                e.getMessage());
        }
    }

    // ===== object key 构建（对齐 SDD 2.2 路径模板，前缀与 runtime build_*_ir_path 一致）=====

    private String buildRootIrKey(String resourceType, String resourceId, String version) {
        if (RES_TYPE_WORKFLOW.equals(resourceType)) {
            return buildWorkflowIrKey(resourceId, version);
        }
        return buildAgentIrKey(resourceId, version);
    }

    private String buildAgentIrKey(String agentId, String version) {
        return String.format("%s/%s/%s/%s_%s.json", CommonConstant.AGENT, CommonConstant.Workflow.IR,
            agentId, agentId, version);
    }

    private String buildWorkflowIrKey(String workflowId, String version) {
        return String.format("%s/%s/%s/%s_%s.json", CommonConstant.WORKFLOW, CommonConstant.Workflow.IR,
            workflowId, workflowId, version);
    }

    private String buildModelServiceKey(String modelServiceId) {
        return String.format("model-service/ir/%s.json", modelServiceId);
    }

    private String buildKbReferenceKey(String kbId) {
        return String.format("kb-connection/ir/knowledge-base/%s.json", kbId);
    }

    private String buildMetadataKey(String resourceId) {
        return String.format("%s/%s/%s_%s.json", Constants.OBS_METADATA_DIR, resourceId, resourceId,
            Constants.LATEST_PUBLISH_VERSION);
    }

    private String rootIrType(String resourceType) {
        return RES_TYPE_WORKFLOW.equals(resourceType) ? TYPE_WORKFLOW_IR : TYPE_AGENT_IR;
    }

    /**
     * 读取 OBS 对象，按 object key 缓存（单次导出内去重，避免收集阶段与打包阶段重复读同一对象）。
     * <p>异常不缓存：抛出由调用方处理（收集阶段 catch 后 skip/标 missing；打包阶段 catch 后按 critical 终止或标 missing），
     * 下次同一 key 重读，行为与无缓存时一致。
     * <p>含 null 缓存：getObject 在内容为空时缓存 null（用 containsKey 区分"已读过且为空"与"未读过"）；
     * 404 不返 null（read 404→抛 OBS_FAILED），由调用方 catch 后标 missing。
     */
    private String getCachedObject(String key, Map<String, String> obsCache) {
        if (obsCache.containsKey(key)) {
            return obsCache.get(key);
        }
        String value = mgObsService.getObject(key);
        obsCache.put(key, value);
        return value;
    }

    private ManifestAsset addAsset(List<ManifestAsset> assets, Set<String> collectedKeys, String key, String type) {
        return addAsset(assets, collectedKeys, key, type, true);
    }

    /**
     * 添加资产到清单（去重 + 路径合法性校验）。
     * <p>路径校验（bug005 #2）：IR 内容（skill_path / ir_path / reference.path）可被构造（如导入的智能体包），
     * 未校验直接作为 OBS key 读取 + ZIP entry 名写入 → 跨租户 OBS 读取泄露 / Zip Slip 解压越界。
     * {@link #isValidAssetKey} 拒绝绝对路径、.. 路径段、反斜杠、控制字符；非法 key 记 warn 跳过（不入包、不读 OBS）。
     * <p>超限处理（巡检 #6）：failOnLimit=true（critical 资产：根 IR/metadata/IR/model-service 等）超限仍抛异常
     * （防恶意/异常 IR 在上限前触发大量 OBS 读取 DoS）；failOnLimit=false（非 critical 资产：model-auth 笛卡尔积
     * 产生的可能不存在的 key）超限仅记 warn 跳过，不整体失败 —— model-auth 缺失标 missing 继续，符合
     * isCriticalAsset 语义，避免合法笛卡尔积（如 10×10）误判 EXPORT_LENGTH_TOO_LARGE 整体失败。
     */
    private ManifestAsset addAsset(List<ManifestAsset> assets, Set<String> collectedKeys, String key, String type,
        boolean failOnLimit) {
        if (!isValidAssetKey(key, type)) {
            if (StringUtils.isNotBlank(key)) {
                log.warn("runtime_asset_export_invalid_key_skipped|key={}|type={}", key, type);
            }
            return null; // 空 or 非法路径（跳过，不入包）
        }
        if (!collectedKeys.add(key)) {
            return null; // 已收集（去重）
        }
        // bug007 #3 + 巡检 #6：上限前置校验。addAsset 是所有资产入清单的单一收口点，在此提前校验，
        // 防恶意/异常 IR 在上限前触发大量 OBS 读取（DoS）。critical 资产超限抛异常；非 critical 资产
        // （model-auth 笛卡尔积）超限记 warn 跳过，避免合法导出因笛卡尔积数量误判整体失败。
        if (assets.size() >= maxAssets) {
            if (failOnLimit) {
                throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE,
                    "assets count " + assets.size() + " exceeds max " + maxAssets);
            }
            log.warn("runtime_asset_export_limit_skip|key={}|type={}|current={}|max={}",
                key, type, assets.size(), maxAssets);
            collectedKeys.remove(key); // 撤回去重标记，避免占用 collectedKeys 配额却不入清单
            return null; // 非 critical 资产超限，跳过不整体失败（缺失标 missing 继续）
        }
        ManifestAsset asset = new ManifestAsset();
        asset.setType(type);
        asset.setKey(key);
        assets.add(asset);
        return asset;
    }

    /** 资产 object key 合法前缀白名单（bug006 #1：约束 IR 可构造路径到已知合法前缀，防跨租户 OBS 读取）。 */
    private static final List<String> ASSET_KEY_PREFIXES = List.of(
        CommonConstant.AGENT + "/" + CommonConstant.Workflow.IR + "/",       // agent/ir/  (agent/controller IR)
        CommonConstant.WORKFLOW + "/" + CommonConstant.Workflow.IR + "/",     // workflow/ir/  (workflow IR)
        "model-service/ir/",        // model-service 配置
        "model-auth/auth/",         // model-auth 鉴权配置
        "kb-connection/ir/",        // KB 引用 + 连接配置
        Constants.OBS_METADATA_DIR + "/"   // metadata/  发布元数据
        // 技能 skill_path 格式 {userId}/skills/...，userId 非固定前缀，不纳入白名单；
        // 由 isOwnedSkillPath（bug007 #1）校验首段 userId 匹配当前用户，归属通过即放行。
    );

    /**
     * 校验资产 object key 合法性（bug005 #2 防路径遍历 + bug006 #1 防跨租户读取 + bug007 #1 技能归属）。
     * <p>两层校验：
     * <ul>
     *   <li>黑名单（bug005 #2）：拒绝绝对路径、.. 路径段、反斜杠（Zip Slip）、控制字符（\0 截断）。</li>
     *   <li>白名单前缀（bug006 #1）：非 skill 类型 key 必须以已知合法前缀开头（agent/ir/、workflow/ir/、
     *       model-service/ir/、model-auth/auth/、kb-connection/ir/、metadata/）。技能 skill_path 由调用方
     *       经 {@link #isOwnedSkillPath}（bug007 #1）校验 userId 归属，不纳入固定前缀白名单（userId 非固定前缀）。</li>
     * </ul>
     * @param type 资产类型（TYPE_SKILL 等），用于决定是否跳过前缀白名单
     * @return true 合法；false 非法（调用方跳过该资产，不读 OBS、不写 ZIP entry）
     */
    private boolean isValidAssetKey(String key, String type) {
        if (StringUtils.isBlank(key)) {
            return false;
        }
        String k = key.trim();
        if (k.isEmpty() || k.charAt(0) == '/') {
            return false; // 绝对路径
        }
        if (k.indexOf('\\') >= 0) {
            return false; // 反斜杠（Windows 路径分隔符，防 Zip Slip on Windows）
        }
        for (int i = 0; i < k.length(); i++) {
            if (k.charAt(i) < 0x20) {
                return false; // 控制字符（含 \0，防截断）
            }
        }
        for (String seg : k.split("/")) {
            if ("..".equals(seg)) {
                return false; // .. 路径段遍历
            }
        }
        // 技能 skill_path 格式 {userId}/skills/...，userId 非固定前缀，由 isOwnedSkillPath 校验归属，
        // 跳过前缀白名单（仅过黑名单）。
        if (TYPE_SKILL.equals(type)) {
            return true;
        }
        // 白名单前缀（bug006 #1）：约束到已知合法前缀，防 IR 可构造路径跨租户读取
        for (String prefix : ASSET_KEY_PREFIXES) {
            if (k.startsWith(prefix)) {
                return true;
            }
        }
        return false; // 不在合法前缀白名单内（跨租户/未知前缀）
    }

    /**
     * 校验子 IR ir_path 的 resourceId 是否归属当前 workspace 或经 t_share_resource 共享授权给当前
     * workspace（bug007 #1 防跨租户读取 + 巡检 #12 🔴 越权 fail-closed）。
     * <p>复用 {@link #validateResourceOwnership} 语义：workflow → WorkflowMapper，agent/controller → AgentMapper。
     * 归属通过→放行；归属不通过→复用 {@link ShareResourceManagerService#checkWorkspaceAuthByResourceOrNot}
     * 校验共享授权（跨 workspace 共享子 IR 是合法场景，与 retrieveAgent 同模式）；两者皆否→拒绝。
     * rid 为 null（非标准 ir key）/ 上下文为空 / 校验异常 → 拒绝（fail-closed，不入包、不读 OBS）。
     * @return true 归属当前 workspace 或经共享授权；false 不归属且未共享或无法判定（调用方 skip 该子 IR）
     */
    private boolean isOwnedOrSharedChildIr(String rid, String type) {
        if (StringUtils.isBlank(rid)) {
            return false; // 非标准 ir key，无法校验归属 → 拒绝
        }
        String projectId = RequestContextUtils.getRequestProjectId();
        String workspaceId = RequestContextUtils.getRequestWorkspaceId();
        if (StringUtils.isBlank(projectId) || StringUtils.isBlank(workspaceId)) {
            // bug005 #3：上下文为空时 fail-closed（已在 exportRuntimeAssetZip 前置校验，此处防御性再判）
            return false;
        }
        String resType = TYPE_WORKFLOW_IR.equals(type) ? RES_TYPE_WORKFLOW : RES_TYPE_AGENT;
        try {
            if (RES_TYPE_WORKFLOW.equals(resType)) {
                List<com.openjiuwen.studio.agent.manager.entity.WorkflowEntity> workflows =
                    workflowMapper.selectByWorkflowIds(projectId, workspaceId, List.of(rid));
                if (workflows != null && !workflows.isEmpty()) {
                    return true; // 归属当前 workspace
                }
            } else if (agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, rid) != null) {
                return true; // 归属当前 workspace（agent / controller）
            }
            // 归属不通过：校验是否经 t_share_resource 共享授权给当前 workspace（跨 workspace 共享子 IR）
            return shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(workspaceId, rid);
        } catch (Exception e) {
            log.warn("isOwnedOrSharedChildIr ownership/share check failed, rid={}. {}. skip child IR.", rid, e.getMessage());
            return false;
        }
    }

    /**
     * 校验 skill_path 是否归属当前 workspace（bug007 #1 防跨用户读取 + 巡检 #5 修过严）。
     * <p>skill_path 格式 {@code {userId}/skills/{skillId}/{version}/{name}.zip}
     * （[CommonConstant.Skill.SKILL_VERSION_FILE_PATH_TEMPLATE](../../constant/CommonConstant.java)）。
     * <p>原 bug007 #1 仅校验首段 userId == 当前请求用户，跨用户共享/团队级技能（同 workspace 不同 userId
     * 创建）被静默丢弃，与本 PR"支持共享子资源"定位冲突（巡检 #5）。改为 workspace 级校验：从 skill_path
     * 提取 skillId（第 2 段），{@link SkillMapper#searchBySkillIds} 查库，校验其 workspaceId == 当前 workspace。
     * 仍防跨租户（攻击者无法导出其他 workspace 的技能），但不误杀同 workspace 内跨用户共享技能。
     * @return true 归属当前 workspace；false 不归属或无法判定（调用方跳过该 skill，fail-closed）
     */
    private boolean isOwnedSkillPath(String skillPath) {
        if (StringUtils.isBlank(skillPath)) {
            return false;
        }
        // skill_path 格式 {userId}/skills/{skillId}/{version}/{name}.zip，取第 2 段 skillId
        String[] parts = skillPath.split("/");
        if (parts.length < 3 || !"skills".equals(parts[1])) {
            return false; // 非标准 skill_path 格式，无法提取 skillId → fail-closed
        }
        String skillId = parts[2];
        if (StringUtils.isBlank(skillId)) {
            return false;
        }
        String projectId = RequestContextUtils.getRequestProjectId();
        String workspaceId = RequestContextUtils.getRequestWorkspaceId();
        if (StringUtils.isBlank(projectId) || StringUtils.isBlank(workspaceId)) {
            return false; // 无法校验归属 → fail-closed
        }
        try {
            List<SkillDetails> skills = skillMapper.searchBySkillIds(List.of(skillId));
            if (skills == null || skills.isEmpty()) {
                return false; // skill 不存在或不归属 → fail-closed
            }
            // 校验 skill 归属当前 workspace（任一匹配即放行，skillId 全局唯一通常只返回 1 条）
            return skills.stream().anyMatch(s -> workspaceId.equals(s.getWorkspaceId()));
        } catch (Exception e) {
            log.warn("isOwnedSkillPath ownership check failed, skillPath={}. {}. skip skill.",
                skillPath, e.getMessage());
            return false; // 查库异常 → fail-closed
        }
    }

    /**
     * 从 IR object key 解析 resourceId（SDD 5.1 版本冲突检测用）。
     * key 形如 agent/ir/{rid}/{rid}_{ver}.json 或 workflow/ir/{rid}/{rid}_{ver}.json → 返回 {rid}。
     */
    private static String parseResourceIdFromIrKey(String key) {
        if (key == null) {
            return null;
        }
        String[] parts = key.split("/");
        if (parts.length >= 4 && "ir".equals(parts[1])
            && (CommonConstant.AGENT.equals(parts[0]) || CommonConstant.WORKFLOW.equals(parts[0]))) {
            return parts[2];
        }
        return null;
    }

    /** 从 IR object key 解析版本号（note 记录用，无法解析返回 "?"）。 */
    private static String parseVersionFromIrKey(String key) {
        String rid = parseResourceIdFromIrKey(key);
        if (rid == null) {
            return "?";
        }
        String fname = key.substring(key.lastIndexOf('/') + 1);
        if (fname.startsWith(rid + "_") && fname.endsWith(".json")) {
            return fname.substring(rid.length() + 1, fname.length() - 5);
        }
        return "?";
    }

    /**
     * 读取 OBS 资产文件 + 打包 ZIP + 构建 manifest（SDD 4.5/5.6）。
     * <p>内存策略：不将全部资产 byte[] 常驻内存（移除原 dataList 全量缓存）：
     * <ul>
     *   <li>文本资产（IR/model-service/model-auth/KB/metadata）：走 getCachedObject（String，UTF-8），
     *       逐资产 getBytes 写入 zos；metadata 命中历史版本导出时先 rewriteMetadataVersionId。</li>
     *   <li>二进制资产（TYPE_SKILL）：走 {@link MgObsService#readObsFileStream} 字节流，
     *       逐资产缓冲（同一时刻仅一个技能 ZIP 在内存）后写入 zos、MessageDigest 流式计 sha256——
     *       技能 ZIP 经文本通道（getObject/UTF-8 解码）会损坏二进制，必须走字节流（巡检 #1）；
     *       流式读取过程中失败则丢弃缓冲、不写 entry（避免 ZIP 残留半截损坏 entry）。</li>
     * </ul>
     * <p>SDD 5.6：根 IR（rootIrKey）+ metadata 缺失即终止；其他缺失标 missing 继续（不入包）。
     * <p>manifest.json 作为最后一个 entry 写入（summary 在资产循环内累计完成后回填）。
     * @param rootIrKey 根 IR 的 object key（用于区分根 IR vs 子 IR 的缺失处理）
     */
    private Resource buildZipWithManifest(RuntimeAssetManifest manifest, List<ManifestAsset> assets,
        String rootIrKey, boolean isHistoryExport, String resolvedVersion, String resourceType) {
        int missingCount = 0;
        long totalSize = 0;
        int irCount = 0, modelCount = 0, kbCount = 0, skillCount = 0, metadataCount = 0;

        Path zipPath = createTempZipFile();
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(zipPath))) {
            for (ManifestAsset asset : assets) {
                // 二进制资产（技能 ZIP）走字节流落盘；其余文本资产逐 asset 读取后直接写入
                if (TYPE_SKILL.equals(asset.getType())) {
                    long[] sizeSha = streamBinaryAsset(zos, asset);
                    if (sizeSha == null) {
                        // 读取失败/空：critical 终止（技能非 critical，此处理论上不触发）；否则已标 missing
                        if (isCriticalAsset(asset, rootIrKey)) {
                            // key 串进日志（运维可追溯，不进 i18n error_msg）；{0} 填 resourceType（与 03601001 语义一致，不泄露 OBS 路径）。
                            log.error("runtime_asset_export_critical_asset_missing|key={}|type={}",
                                asset.getKey(), asset.getType());
                            throw new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS, resourceType);
                        }
                        missingCount++;
                        continue;
                    }
                    totalSize += sizeSha[0];
                    skillCount++;
                    continue;
                }
                // 文本资产
                String content;
                try {
                    content = mgObsService.getObject(asset.getKey());
                } catch (Exception e) {
                    if (isCriticalAsset(asset, rootIrKey)) {
                        // key 串进日志（运维可追溯，不进 i18n error_msg）；{0} 填 resourceType（与 03601001 语义一致，不泄露 OBS 路径）。
                        log.error("runtime_asset_export_critical_asset_missing|key={}|type={}",
                            asset.getKey(), asset.getType());
                        throw new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS, resourceType);
                    }
                    log.warn("runtime_asset_export_asset_missing|key={}|type={}|reason={}",
                        asset.getKey(), asset.getType(), e.getMessage());
                    asset.setStatus("missing");
                    asset.setErrorReason(e.getMessage());
                    asset.setSha256(null);
                    missingCount++;
                    continue;
                }
                if (StringUtils.isBlank(content)) {
                    if (isCriticalAsset(asset, rootIrKey)) {
                        // key 串进日志（运维可追溯，不进 i18n error_msg）；{0} 填 resourceType（与 03601001 语义一致，不泄露 OBS 路径）。
                        log.error("runtime_asset_export_critical_asset_empty|key={}|type={}",
                            asset.getKey(), asset.getType());
                        throw new AgentStudioException(StudioError.EXPORT_RESOURCE_NOT_EXISTS, resourceType);
                    }
                    asset.setStatus("missing");
                    asset.setErrorReason("OBS object empty");
                    missingCount++;
                    continue;
                }
                // SDD 5.5：导出历史版本时，_latest.json 内容仍指向当前最新版本，
                // 运行态按 _latest.json 加载会拉错版本。导出前改写 versionId 为 resolvedVersion。
                if (isHistoryExport && TYPE_METADATA.equals(asset.getType())) {
                    content = rewriteMetadataVersionId(content, resolvedVersion);
                }
                byte[] data = content.getBytes(StandardCharsets.UTF_8);
                String sha = sha256Hex(data);
                asset.setSize(data.length);
                asset.setSha256(sha);
                asset.setStatus("ok");
                zos.putNextEntry(new ZipEntry(asset.getKey()));
                zos.write(data);
                zos.closeEntry();
                totalSize += data.length;
                switch (asset.getType()) {
                    case TYPE_AGENT_IR:
                    case TYPE_WORKFLOW_IR:
                        irCount++;
                        break;
                    case TYPE_MODEL_SERVICE:
                    case TYPE_MODEL_AUTH:
                        modelCount++;
                        break;
                    case TYPE_KB_CONNECTION:
                    case TYPE_KB_REFERENCE:
                        kbCount++;
                        break;
                    case TYPE_METADATA:
                        metadataCount++;
                        break;
                    default:
                        break;
                }
            }
            // 回填 summary（manifest 作为最后 entry，summary 须在序列化前完整）
            ManifestSummary summary = manifest.getSummary();
            summary.setTotalAssets(assets.size());
            summary.setTotalSizeBytes(totalSize);
            summary.setIrCount(irCount);
            summary.setModelCount(modelCount);
            summary.setKbCount(kbCount);
            summary.setSkillCount(skillCount);
            summary.setMetadataCount(metadataCount);
            summary.setMissingCount(missingCount);

            zos.putNextEntry(new ZipEntry("manifest.json"));
            // bug004 #2：用 Jackson 序列化 manifest（识别 @JsonProperty 蛇形契约），fastjson2 不识别 Jackson
            // 注解会输出驼峰（manifestVersion/exportId/...），破坏导入工具 tools/import_asset_zip.py 的蛇形契约。
            zos.write(MANIFEST_MAPPER.writeValueAsBytes(manifest));
            zos.closeEntry();
            zos.finish();
            return new DeleteOnCloseFileSystemResource(zipPath);
        } catch (AgentStudioException e) {
            deleteQuietly(zipPath);
            throw e;
        } catch (Exception e) {
            deleteQuietly(zipPath);
            log.error("buildZipWithManifest error", e);
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }
    }

    /**
     * 读取二进制资产（技能 ZIP）并写入 ZIP entry（巡检 #1）。
     * <p>技能经文本通道 getObject 会 UTF-8 解码损坏二进制，故必须走 readObsFileStream 字节流。
     * <p>内存策略：技能先流式落临时文件并计算 sha256，再从临时文件流式写入 ZIP；
     * 不把技能 ZIP 读入内存缓冲，避免大体积技能导致内存峰值/OOM。
     * <p>正确性：OBS 流读取失败/为空时不写 entry（避免 ZIP 残留半截损坏 entry）；仅在完整落盘后写 entry。
     * @return {size}（成功），null（失败/空，已标 missing，调用方计数）
     */
    private long[] streamBinaryAsset(ZipOutputStream zos, ManifestAsset asset) {
        Path skillPath = null;
        try (InputStream is = mgObsService.readObsFileStream(asset.getKey())) {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            skillPath = Files.createTempFile("runtime-asset-skill-", ".zip");
            long size = 0;
            try (OutputStream out = Files.newOutputStream(skillPath)) {
                byte[] buffer = new byte[8192];
                int n;
                while ((n = is.read(buffer)) != -1) {
                    out.write(buffer, 0, n);
                    md.update(buffer, 0, n);
                    size += n;
                }
            }
            if (size == 0) {
                asset.setStatus("missing");
                asset.setErrorReason("OBS object empty");
                asset.setSha256(null);
                return null;
            }
            zos.putNextEntry(new ZipEntry(asset.getKey()));
            try (InputStream in = Files.newInputStream(skillPath)) {
                byte[] buffer = new byte[8192];
                int n;
                while ((n = in.read(buffer)) != -1) {
                    zos.write(buffer, 0, n);
                }
            }
            zos.closeEntry();
            asset.setSize(size);
            asset.setSha256(hexDigest(md));
            asset.setStatus("ok");
            return new long[] {size};
        } catch (Exception e) {
            log.warn("runtime_asset_export_asset_missing|key={}|type={}|reason={}",
                asset.getKey(), asset.getType(), e.getMessage());
            asset.setStatus("missing");
            asset.setErrorReason(e.getMessage());
            asset.setSha256(null);
            return null;
        } finally {
            deleteQuietly(skillPath);
        }
    }

    private Path createTempZipFile() {
        try {
            return Files.createTempFile("runtime-asset-export-", ".zip");
        } catch (IOException e) {
            log.error("create runtime asset export temp file failed", e);
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }
    }

    private static void deleteQuietly(Path path) {
        if (path == null) {
            return;
        }
        try {
            Files.deleteIfExists(path);
        } catch (Exception ignore) {
            // 临时文件清理失败不影响导出主流程
        }
    }

    /** 响应写完后删除临时 ZIP 的 FileSystemResource（contentLength 仍走文件元数据，不消耗流）。 */
    private static final class DeleteOnCloseFileSystemResource extends FileSystemResource {
        private final Path path;

        private DeleteOnCloseFileSystemResource(Path path) {
            super(path);
            this.path = path;
        }

        @Override
        public InputStream getInputStream() throws IOException {
            return new FilterInputStream(Files.newInputStream(path)) {
                @Override
                public void close() throws IOException {
                    try {
                        super.close();
                    } finally {
                        deleteQuietly(path);
                    }
                }
            };
        }
    }

    private String hexDigest(MessageDigest md) {
        byte[] hash = md.digest();
        StringBuilder sb = new StringBuilder(hash.length * 2);
        for (byte b : hash) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    /**
     * 判断资产是否为 critical（缺失即终止）。SDD 5.6：根 IR + metadata 缺失终止。
     * 子 IR（非根的 agent_ir/workflow_ir）缺失标 missing 继续。
     */
    private boolean isCriticalAsset(ManifestAsset asset, String rootIrKey) {
        if (TYPE_METADATA.equals(asset.getType())) {
            return true;
        }
        // 根 IR（key 与 rootIrKey 相同）；子 IR 不终止
        return asset.getKey().equals(rootIrKey);
    }

    private RuntimeAssetManifest buildManifest(String exportId, String resourceType, String resourceId,
        String resolvedVersion, String projectId, String workspaceId, List<ManifestAsset> assets) {
        RuntimeAssetManifest manifest = new RuntimeAssetManifest();
        manifest.setManifestVersion("1.0");
        manifest.setExportId(exportId);
        manifest.setExportedAt(OffsetDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
        manifest.setExportedBy(RequestContextUtils.getRequestUserId());

        RuntimeAssetManifest.ManifestSource source = new RuntimeAssetManifest.ManifestSource();
        // spring.profiles.active 可能是逗号分隔多 profile，取首个非空段；空则兜底 dev
        String env = StringUtils.isNotBlank(springProfile)
            ? springProfile.split(",")[0].trim() : "dev";
        source.setEnvironment(env);
        source.setStorageType("OBS");
        manifest.setSource(source);

        // 根资源记录（version 为 resolvedVersion，即具体发布版本号，非 latest）
        ManifestResource res = new ManifestResource();
        res.setResourceId(resourceId);
        res.setResourceType(resourceType);
        res.setIrPath(buildRootIrKey(resourceType, resourceId, resolvedVersion));
        res.setVersion(resolvedVersion);
        res.setProjectId(projectId);
        res.setWorkspaceId(workspaceId);
        manifest.setResources(List.of(res));

        manifest.setAssets(assets);
        manifest.setSummary(new ManifestSummary());
        return manifest;
    }

    /**
     * 元数据历史版本重写（SDD 5.5）：把 _latest.json 的 versionId 改为 resolvedVersion，
     * 使运行态按 _latest.json 加载到正确的导出版本 IR。updatedAt 同步更新为导出时间戳。
     * 仅发生在导出包内，不回写开发态 OBS。
     */
    private String rewriteMetadataVersionId(String metadataJson, String resolvedVersion) {
        try {
            JSONObject meta = JSON.parseObject(metadataJson);
            meta.put("versionId", resolvedVersion);
            meta.put("updatedAt", System.currentTimeMillis());
            return JSON.toJSONString(meta);
        } catch (Exception e) {
            log.warn("rewriteMetadataVersionId failed, keep original. {}", e.getMessage());
            return metadataJson;
        }
    }

    private String sha256Hex(byte[] data) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(data);
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return null;
        }
    }
}
