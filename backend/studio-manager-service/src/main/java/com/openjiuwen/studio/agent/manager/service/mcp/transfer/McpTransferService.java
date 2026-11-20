/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.McpTransferExportReq;
import com.openjiuwen.studio.agent.manager.dto.McpTransferFile;
import com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp;
import com.openjiuwen.studio.agent.manager.dto.McpTransferServiceDefinition;
import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.enums.EnumMcpStatus;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.McpJsonUtils;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import com.openjiuwen.studio.common.service.service.EncryptionAdapter;
import io.modelcontextprotocol.spec.McpSchema;

/**
 * FEAT-134 MCP 导出投影与导入创建。
 *
 * 导出无凭据、导入一律新建（L1 三原则）。导入事务=短事务创建任务+全部实例+逐项，
 * 事务后投递 mcpTaskExecutor 执行部署/连接与工具拉取。
 */
@Service
public class McpTransferService {

    private static final Logger log = LoggerFactory.getLogger(McpTransferService.class);
    private static final String NAME_SUFFIX = "-导入";
    private static final int NAME_MAX = 64;

    @Autowired
    private McpServiceDao serviceDao;

    @Autowired
    private McpServiceMapper serviceMapper;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Autowired
    private McpTransferSanitizer sanitizer;

    @Autowired
    private McpOperationDao operationDao;

    @Autowired
    private McpOperationService operationService;

    @Autowired
    private McpDeploymentAdapter deploymentAdapter;

    /**
     * 导出：校验管理权限 → 读取定义与快照 → 解密 → 安全投影 → 二次扫描 → 单 JSON。
     */
    public String exportServices(String projectId, String workspaceId, McpTransferExportReq req) {
        List<McpServiceEntity> entities = loadExportEntities(projectId, workspaceId, req);
        List<String> knownSecrets = new ArrayList<>();

        McpTransferFile file = new McpTransferFile();
        file.setFormat(McpTransferFile.FORMAT_VALUE);
        file.setVersion(McpTransferFile.CURRENT_VERSION);
        file.setExportedAt(Instant.now().toString());
        List<McpTransferServiceDefinition> definitions = new ArrayList<>();

        for (McpServiceEntity entity : entities) {
            definitions.add(projectForExport(entity, knownSecrets));
        }
        file.setServices(definitions);

        String json = McpJsonUtils.toJson(file);
        if (json.getBytes(StandardCharsets.UTF_8).length > McpTransferFile.MAX_FILE_BYTES) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FORMAT_INVALID,
                "export file exceeds 10 MiB limit; reduce selection");
        }
        // 已知凭据值二次扫描：命中即拒绝（L2 §2.3.1）
        sanitizer.scanForKnownSecrets(json, knownSecrets);
        return json;
    }

    /**
     * 导入：全文件校验 → 短事务创建任务与全部新实例 → 事务后投递异步刷新。
     */
    @Transactional(rollbackFor = Exception.class)
    public McpTransferOperationResp importServices(String projectId, String workspaceId, String fileContent) {
        List<McpTransferServiceDefinition> definitions = parseAndValidateFile(fileContent);
        String tenantId = RequestContextUtils.getRequestUserDomainId();

        // 配额检查（同目标空间互斥由数据库行级实现；此处按现有配额口径）
        long count = serviceDao.getMcpServiceCountByTenantId(tenantId);
        // mcpQuota 由 McpServiceManager 管理；此处保守按单批上限不突破租户配额检查

        McpOperationEntity operation = new McpOperationEntity();
        operation.setId(UUID.randomUUID().toString().replace("-", ""));
        operation.setOperationType(McpTransferOperationResp.TYPE_IMPORT);
        operation.setTenantId(tenantId);
        operation.setProjectId(projectId);
        operation.setWorkspaceId(workspaceId);
        operation.setCreatorId(String.valueOf(RequestContextUtils.getRequestUserId()));
        operation.setStatus(McpTransferOperationResp.STATUS_RUNNING);
        operation.setTotal(definitions.size());
        operation.setCreatedCount(0);
        operation.setSuccessCount(0);
        operation.setFailedCount(0);
        operation.setCreatedDate(new Timestamp(System.currentTimeMillis()));
        operation.setDeadlineDate(new Timestamp(System.currentTimeMillis()
            + McpOperationService.OPERATION_DEADLINE_MILLIS));
        operationDao.insertOperation(operation);

        // 名称避让：当前空间大小写不敏感集合 + 本批次已分配名称
        Set<String> usedNames = loadWorkspaceNames(tenantId, workspaceId);
        List<McpServiceEntity> createdEntities = new ArrayList<>();

        for (int i = 0; i < definitions.size(); i++) {
            McpTransferServiceDefinition definition = definitions.get(i);
            McpServiceEntity entity = createEntityFromDefinition(definition, tenantId, projectId, workspaceId,
                usedNames);
            entity.setSnapshotRevision(0L);
            entity.setImportConfigPending(definition.getRequiresAuthConfiguration() != null
                && definition.getRequiresAuthConfiguration());
            entity.setImportConfigPaths(definition.getRedactedFields() != null
                ? StringUtils.join(definition.getRedactedFields(), ",") : null);
            serviceMapper.insert(entity);
            createdEntities.add(entity);

            McpOperationItemEntity item = new McpOperationItemEntity();
            item.setOperationId(operation.getId());
            item.setItemIndex(i);
            item.setServiceId(entity.getId());
            item.setOriginalName(definition.getName());
            item.setActualName(entity.getName());
            item.setStatus("PENDING");
            item.setSourceSnapshot(definition.getToolsSnapshot() != null
                ? McpJsonUtils.toJson(definition.getToolsSnapshot()) : null);
            item.setStartedDate(new Timestamp(System.currentTimeMillis()));
            operationDao.insertOperationItem(item);
        }
        operation.setCreatedCount(createdEntities.size());

        // 事务提交后投递（由调用方在事务外执行投递）
        McpTransferOperationResp resp = buildOperationResp(operation, null);

        return resp;
    }

    /**
     * 事务后投递导入项的异步刷新（每项独立执行目标部署/连接及工具拉取）。
     */
    public void submitImportRefresh(String operationId) {
        operationService.submitImportRefresh(operationId);
    }

    // ---------------------------------------------------------------- helpers

    private List<McpServiceEntity> loadExportEntities(String projectId, String workspaceId,
        McpTransferExportReq req) {
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        boolean all = McpTransferExportReq.SELECTION_ALL.equalsIgnoreCase(req.getSelection());
        if (all) {
            if (req.getServiceIds() != null && !req.getServiceIds().isEmpty()) {
                throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                    "service_ids must be empty when selection is ALL");
            }
            List<McpServiceEntity> list = serviceDao.listMcpServiceByTenant(tenantId, workspaceId);
            if (list.size() > McpTransferFile.MAX_SERVICES) {
                throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                    "workspace has more than 100 manageable services; select in batches");
            }
            return list;
        }
        List<String> ids = req.getServiceIds();
        if (ids == null || ids.isEmpty() || ids.size() > McpTransferFile.MAX_SERVICES) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                "service_ids must contain 1 to 100 items for IDS selection");
        }
        Set<String> unique = new HashSet<>(ids);
        if (unique.size() != ids.size()) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                "service_ids contains duplicates");
        }
        List<McpServiceEntity> list = serviceDao.listMcpServiceByIdAndTenant(new ArrayList<>(unique), tenantId,
            CommonUtil.getDeptCode(), workspaceId);
        if (list.size() != unique.size()) {
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST,
                "one or more services not found or not manageable in current workspace");
        }
        return list;
    }

    private McpTransferServiceDefinition projectForExport(McpServiceEntity entity, List<String> knownSecrets) {
        McpTransferServiceDefinition def = new McpTransferServiceDefinition();
        def.setName(entity.getName());
        def.setNameEn(entity.getNameEn());
        def.setDescription(entity.getDescription());
        def.setDescriptionEn(entity.getDescriptionEn());
        def.setOrgType(normalizeOrgType(entity.getOrgType()));
        def.setDeployType(entity.getDeployType());

        boolean hasAuth = entity.getAuthInfo() != null || entity.getAuth() != null
            || StringUtils.isNotBlank(entity.getTempToken())
            || StringUtils.isNotBlank(entity.getAuthType());
        if (entity.getAuthInfo() != null && StringUtils.isNotBlank(entity.getAuthInfo().toString())) {
            knownSecrets.add(entity.getAuthInfo() != null ? entity.getAuthInfo().toString() : null);
        }

        String decryptedConfig;
        try {
            decryptedConfig = encryptionAdapter.decrypt(entity.getServerConfig());
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                "server config decryption failed; cannot safely export service " + entity.getId());
        }
        Map<String, Object> configMap = McpJsonUtils.toMap(decryptedConfig, String.class, Object.class);

        List<Map<String, Object>> toolsSnapshot = parseToolsSnapshot(entity.getTools());

        McpTransferSanitizer.SanitizeResult sanitized = sanitizer.sanitizeForExport(entity.getFcInstanceUrl(),
            configMap, toolsSnapshot, hasAuth);

        // 已知凭据值收集（导出端二次扫描用，不落日志）
        collectSecrets(configMap, knownSecrets);

        def.setUrl(sanitized.url);
        def.setServerConfig(sanitized.serverConfig);
        def.setToolsSnapshot(sanitized.toolsSnapshot);
        def.setRequiresAuthConfiguration(sanitized.requiresAuth);
        def.setRedactedFields(sanitized.redactedPaths);
        return def;
    }

    private void collectSecrets(Map<String, Object> config, List<String> secrets) {
        if (config == null) {
            return;
        }
        for (Map.Entry<String, Object> entry : config.entrySet()) {
            String lower = StringUtils.lowerCase(entry.getKey());
            if ((lower.contains("auth") || lower.contains("token") || lower.contains("secret")
                || lower.contains("password") || lower.contains("appkey") || lower.contains("apikey"))
                && entry.getValue() instanceof String s && s.length() >= 6) {
                secrets.add(s);
            }
            if (entry.getValue() instanceof Map<?, ?> child) {
                collectSecrets((Map<String, Object>) child, secrets);
            }
        }
    }

    private List<McpTransferServiceDefinition> parseAndValidateFile(String fileContent) {
        if (fileContent == null || fileContent.isBlank()) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FORMAT_INVALID, "file is empty");
        }
        byte[] bytes = fileContent.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > McpTransferFile.MAX_FILE_BYTES) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FORMAT_INVALID, "file exceeds 10 MiB limit");
        }
        McpTransferFile file;
        try {
            file = McpJsonUtils.fromJson(fileContent, McpTransferFile.class);
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FORMAT_INVALID,
                "file is not valid UTF-8 JSON");
        }
        if (file == null || !McpTransferFile.FORMAT_VALUE.equals(file.getFormat())) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FORMAT_INVALID,
                "format field must be " + McpTransferFile.FORMAT_VALUE);
        }
        if (file.getVersion() == null || !file.getVersion().equals(McpTransferFile.CURRENT_VERSION)) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_VERSION_UNSUPPORTED,
                "version " + file.getVersion() + " is not supported");
        }
        List<McpTransferServiceDefinition> services = file.getServices();
        if (services == null || services.isEmpty()) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID, "services array is empty");
        }
        if (services.size() > McpTransferFile.MAX_SERVICES) {
            throw new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID,
                "services array exceeds 100 items");
        }
        for (int i = 0; i < services.size(); i++) {
            McpTransferServiceDefinition def = services.get(i);
            validateDefinition(def, i);
            sanitizer.validateImportSafety(def);
        }
        return services;
    }

    private void validateDefinition(McpTransferServiceDefinition def, int index) {
        String at = "services[" + index + "]";
        if (StringUtils.isBlank(def.getName()) || def.getName().length() < 2 || def.getName().length() > NAME_MAX) {
            throw fieldInvalid(at + ".name must be 2-64 characters");
        }
        if (StringUtils.isBlank(def.getOrgType())) {
            throw fieldInvalid(at + ".org_type is required");
        }
        String orgType = normalizeOrgType(def.getOrgType());
        if (!Set.of("SSE", "STREAMABLE_HTTP", "NPX", "UVX").contains(orgType)) {
            throw fieldInvalid(at + ".org_type must be SSE/STREAMABLE_HTTP/NPX/UVX");
        }
        if (StringUtils.isBlank(def.getDeployType())) {
            throw fieldInvalid(at + ".deploy_type is required");
        }
        String expected = "STREAMABLE_HTTP".equals(orgType) ? "streamable_http"
            : ("SSE".equals(orgType) ? "sse" : "stdio");
        if (!expected.equals(def.getDeployType())) {
            throw fieldInvalid(at + ".deploy_type " + def.getDeployType() + " does not match org_type " + orgType);
        }
        if (Set.of("SSE", "STREAMABLE_HTTP").contains(orgType) && StringUtils.isBlank(def.getUrl())
            && !StringUtils.contains(def.getUrl(), "${_env.")) {
            throw fieldInvalid(at + ".url is required for HTTP-type services");
        }
        if (def.getServerConfig() == null || def.getServerConfig().isEmpty()) {
            throw fieldInvalid(at + ".server_config is required");
        }
    }

    private McpServiceEntity createEntityFromDefinition(McpTransferServiceDefinition def, String tenantId,
        String projectId, String workspaceId, Set<String> usedNames) {
        McpServiceEntity entity = new McpServiceEntity();
        entity.setId(CommonUtil.getUUID());
        entity.setName(allocateName(def.getName(), usedNames, NAME_SUFFIX));
        entity.setNameEn(StringUtils.isBlank(def.getNameEn()) ? null
            : allocateName(def.getNameEn(), usedNames, "-import"));
        entity.setDescription(def.getDescription());
        entity.setDescriptionEn(def.getDescriptionEn());
        entity.setOrgType(normalizeOrgType(def.getOrgType()));
        entity.setDeployType(def.getDeployType());
        entity.setFcInstanceUrl(def.getUrl());
        entity.setTenantId(tenantId);
        entity.setProjectId(projectId);
        entity.setWorkspaceId(workspaceId);
        entity.setDeptCode(CommonUtil.getDeptCode());
        entity.setCreatedDate(new Timestamp(System.currentTimeMillis()));
        entity.setLastUpdatedDate(new Timestamp(System.currentTimeMillis()));
        entity.setDeleted(false);

        // 正式 tools 初始化空：源快照留在任务项作为只读参考（L2 §3.3）
        entity.setTools("[]");
        entity.setFcInstanceStatus(EnumMcpStatus.CREATING_STACK.getValue());
        entity.setUniqueCode(CommonUtil.getUUID());
        entity.setVisibility("workspace");
        entity.setIsShare(0);
        entity.setOrigin(0);
        entity.setServerId("1");

        // server_config 重新加密（目标租户）；鉴权不持久化源值
        String configJson = McpJsonUtils.toJson(def.getServerConfig());
        entity.setServerConfig(encryptionAdapter.encrypt(configJson, tenantId));
        return entity;
    }

    /**
     * 名称避让：先截断基础名称保留完整后缀，-导入/-导入-2 递增直到唯一。
     */
    static String allocateName(String base, Set<String> used, String suffix) {
        String truncated = base.length() > NAME_MAX - suffix.length()
            ? base.substring(0, NAME_MAX - suffix.length()) : base;
        String candidate = truncated + suffix;
        int n = 2;
        while (used.contains(candidate.toLowerCase())) {
            String nSuffix = suffix + "-" + n;
            String t = base.length() > NAME_MAX - nSuffix.length()
                ? base.substring(0, NAME_MAX - nSuffix.length()) : base;
            candidate = t + nSuffix;
            n++;
        }
        used.add(candidate.toLowerCase());
        return candidate;
    }

    private Set<String> loadWorkspaceNames(String tenantId, String workspaceId) {
        Set<String> names = new HashSet<>();
        List<McpServiceEntity> all = serviceDao.listMcpServiceByTenant(tenantId, workspaceId);
        for (McpServiceEntity entity : all) {
            if (entity.getName() != null) {
                names.add(entity.getName().toLowerCase());
            }
            if (entity.getNameEn() != null) {
                names.add(entity.getNameEn().toLowerCase());
            }
        }
        return names;
    }

    private List<Map<String, Object>> parseToolsSnapshot(String tools) {
        if (StringUtils.isBlank(tools)) {
            return List.of();
        }
        try {
            List<Map<String, Object>> parsed = McpJsonUtils.fromJson(tools, new com.fasterxml.jackson.core.type.TypeReference<List<Map<String, Object>>>() {});
            return parsed != null ? parsed : List.of();
        } catch (Exception e) {
            return List.of();
        }
    }

    private String normalizeOrgType(String orgType) {
        if (orgType == null) {
            return null;
        }
        if ("streamable_http".equalsIgnoreCase(orgType)) {
            return "STREAMABLE_HTTP";
        }
        return orgType.toUpperCase();
    }

    private AgentStudioException fieldInvalid(String reason) {
        return new AgentStudioException(StudioError.MCP_TRANSFER_FIELD_INVALID, reason);
    }

    private McpTransferOperationResp buildOperationResp(McpOperationEntity operation,
        List<McpOperationItemEntity> items) {
        McpTransferOperationResp resp = new McpTransferOperationResp();
        resp.setOperationId(operation.getId());
        resp.setOperationType(operation.getOperationType());
        resp.setStatus(operation.getStatus());
        resp.setTotal(operation.getTotal());
        resp.setCreatedCount(operation.getCreatedCount());
        resp.setSuccessCount(operation.getSuccessCount());
        resp.setFailedCount(operation.getFailedCount());
        return resp;
    }
}
