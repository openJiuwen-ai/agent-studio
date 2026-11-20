/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;
import com.openjiuwen.studio.agent.manager.dto.McpTransferOperationResp;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.mcp.McpServiceManager;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * FEAT-134 MCP 操作生命周期（导入项执行、重载执行、终态汇总、超时回收）。
 */
@Service
public class McpOperationService {

    private static final Logger log = LoggerFactory.getLogger(McpOperationService.class);

    /** 受理起 10 分钟总执行期限（含排队、分页和所有导入项）。 */
    public static final long OPERATION_DEADLINE_MILLIS = 10L * 60 * 1000;

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired
    private McpOperationDao operationDao;

    @Autowired
    private McpServiceDao serviceDao;

    @Autowired
    private McpServiceMapper serviceMapper;

    @Autowired
    private McpToolSnapshotService snapshotService;

    @Autowired
    private McpServiceManager mcpServiceManager;

    @Autowired
    private ThreadPoolTaskExecutor mcpTaskExecutor;

    /**
     * 事务后投递导入项刷新：每项独立执行目标部署/连接及工具拉取。
     */
    public void submitImportRefresh(String operationId) {
        McpOperationEntity operation = operationDao.getOperationById(operationId);
        if (operation == null || !McpTransferOperationResp.STATUS_RUNNING.equals(operation.getStatus())) {
            return;
        }
        List<McpOperationItemEntity> items = operationDao.getOperationItems(operationId);
        String authToken = RequestContextUtils.getRequestAuthToken();
        String tenantId = operation.getTenantId();
        String projectId = operation.getProjectId();
        String workspaceId = operation.getWorkspaceId();

        for (McpOperationItemEntity item : items) {
            String serviceId = item.getServiceId();
            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, projectId, tenantId);
                    executeImportItem(operation, item);
                } catch (Throwable t) {
                    log.error("import item execution failed. operation={}, service={}", operationId, serviceId, t);
                    failItem(operation, item, safeCode(t), safeReason(t));
                } finally {
                    clearContext();
                }
            });
        }
    }

    /**
     * 导入项执行：读取实体 → NPX/UVX 检查部署能力 → 连接拉工具 → 结果落库。
     */
    private void executeImportItem(McpOperationEntity operation, McpOperationItemEntity item) {
        McpServiceEntity entity = serviceDao.getMcpServiceById(item.getServiceId(), operation.getTenantId(),
            item.getSafeReason() != null ? null : null, operation.getProjectId(), operation.getWorkspaceId());
        if (entity == null) {
            failItem(operation, item, StudioError.MCP_SERVICE_NOT_EXIST.getCode(), "service not found");
            return;
        }
        if (McpDeploymentAdapter.requiresDeployment(entity.getOrgType())
            && !deploymentAdapterAvailable()) {
            failItem(operation, item, StudioError.MCP_DEPLOYMENT_UNAVAILABLE.getCode(),
                "NPX/UVX target deployment unavailable");
            return;
        }
        // 声明活动操作（导入初始刷新也声明自己的活动操作，L2 §5.6.5）
        if (!operationDao.claimOperationOnService(entity.getId(), operation.getTenantId(),
            operation.getProjectId(), operation.getWorkspaceId(), operation.getId())) {
            failItem(operation, item, StudioError.MCP_OPERATION_CONFLICT.getCode(),
                "another operation is active on this service");
            return;
        }
        try {
            McpToolFetchResult result = snapshotService.fetchTools(entity);
            if (result.success()) {
                String toolsJson = snapshotService.serializeTools(result.tools());
                int updated = serviceMapper.commitToolSnapshot(entity.getId(), operation.getTenantId(),
                    operation.getProjectId(), operation.getWorkspaceId(), operation.getId(),
                    entity.getSnapshotRevision() == null ? 0L : entity.getSnapshotRevision(), toolsJson);
                if (updated != 1) {
                    failItem(operation, item, StudioError.MCP_OPERATION_CONFLICT.getCode(),
                        "snapshot commit lost ownership race");
                } else {
                    succeedItem(operation, item, result.tools().size());
                }
            } else {
                // 导入失败策略：实例保留 stackFail、原因如实标记（L2 §3.3）
                serviceDao.updateStatusWithReason(entity.getId(), "stackFail",
                    "[" + result.errorCode() + "] " + result.safeReason(), operation.getTenantId(), null);
                operationDao.releaseOperationOnService(entity.getId(), operation.getId());
                failItem(operation, item, result.errorCode(), result.safeReason());
            }
        } finally {
            operationDao.releaseOperationOnService(entity.getId(), operation.getId());
        }
    }

    private boolean deploymentAdapterAvailable() {
        // McpDeploymentAdapter 基线返回 false；此方法留给后续真实适配器接入
        return false;
    }

    /**
     * 重载执行入口（由 API 层在受理后调用）。
     */
    public void submitReload(String operationId) {
        McpOperationEntity operation = operationDao.getOperationById(operationId);
        if (operation == null) {
            return;
        }
        List<McpOperationItemEntity> items = operationDao.getOperationItems(operationId);
        String authToken = RequestContextUtils.getRequestAuthToken();
        for (McpOperationItemEntity item : items) {
            mcpTaskExecutor.execute(() -> {
                try {
                    RequestContextUtils.setContext(authToken, operation.getProjectId(), operation.getTenantId());
                    snapshotService.executeReload(operation, item);
                } catch (Throwable t) {
                    log.error("reload execution failed. operation={}", operationId, t);
                    failItem(operation, item, safeCode(t), safeReason(t));
                } finally {
                    clearContext();
                }
            });
        }
    }

    /**
     * 重载成功路径：item 已由调用方组装（含 result_json），此处落库并汇总。
     */
    void succeedItemRaw(McpOperationEntity operation, McpOperationItemEntity item) {
        item.setStatus("SUCCESS");
        item.setRefreshStatus("SUCCESS");
        item.setFinishedDate(new Timestamp(System.currentTimeMillis()));
        operationDao.finishOperationItem(item);
        finalizeOperation(operation);
    }
    void succeedItem(McpOperationEntity operation, McpOperationItemEntity item, int toolCount) {
        Map<String, Object> result = new HashMap<>();
        result.put("tool_count", toolCount);
        result.put("requires_republish", true);
        item.setStatus("SUCCESS");
        item.setRefreshStatus("SUCCESS");
        item.setResultJson(toJson(result));
        item.setFinishedDate(new Timestamp(System.currentTimeMillis()));
        operationDao.finishOperationItem(item);
        finalizeOperation(operation);
    }

    void failItem(McpOperationEntity operation, McpOperationItemEntity item, String errorCode, String reason) {
        item.setStatus("FAILED");
        item.setRefreshStatus("FAILED");
        item.setErrorCode(errorCode);
        item.setSafeReason(truncate(reason, 500));
        item.setFinishedDate(new Timestamp(System.currentTimeMillis()));
        operationDao.finishOperationItem(item);
        finalizeOperation(operation);
    }

    private synchronized void finalizeOperation(McpOperationEntity operation) {
        McpOperationEntity fresh = operationDao.getOperationById(operation.getId());
        if (fresh == null || !McpTransferOperationResp.STATUS_RUNNING.equals(fresh.getStatus())) {
            return;
        }
        List<McpOperationItemEntity> items = operationDao.getOperationItems(operation.getId());
        int success = 0;
        int failed = 0;
        for (McpOperationItemEntity item : items) {
            if ("SUCCESS".equals(item.getStatus())) {
                success++;
            } else if ("FAILED".equals(item.getStatus())) {
                failed++;
            } else {
                return; // still PENDING
            }
        }
        String status = failed == 0 ? McpTransferOperationResp.STATUS_SUCCESS
            : (success > 0 ? McpTransferOperationResp.STATUS_PARTIAL_SUCCESS
                : McpTransferOperationResp.STATUS_FAILED);
        operationDao.finishOperation(operation.getId(), status, fresh.getCreatedCount(), success, failed);
    }

    /**
     * 超时回收：终结超期 RUNNING 任务并释放活动标记（每 30 秒由调度器调用）。
     */
    public void reclaimTimedOutOperations() {
        List<String> ids = operationDao.getTimedOutRunningOperations(50);
        for (String id : ids) {
            try {
                McpOperationEntity operation = operationDao.getOperationById(id);
                if (operation == null) {
                    continue;
                }
                List<McpOperationItemEntity> items = operationDao.getOperationItems(id);
                for (McpOperationItemEntity item : items) {
                    if ("PENDING".equals(item.getStatus())) {
                        item.setStatus("FAILED");
                        item.setErrorCode(StudioError.MCP_OPERATION_INTERRUPTED.getCode());
                        item.setSafeReason("operation timed out");
                        item.setFinishedDate(new Timestamp(System.currentTimeMillis()));
                        operationDao.finishOperationItem(item);
                    }
                    if (item.getServiceId() != null) {
                        operationDao.releaseOperationOnService(item.getServiceId(), id);
                    }
                }
                operationDao.markOperationInterrupted(id);
            } catch (Exception e) {
                log.error("failed to reclaim timed out operation {}", id, e);
            }
        }
    }

    /**
     * 查询操作结果（任务仅接受同空间用户查询）。
     */
    public McpTransferOperationResp getOperationResult(String projectId, String workspaceId, String operationId) {
        String tenantId = RequestContextUtils.getRequestUserDomainId();
        McpOperationEntity operation = operationDao.getOperationByIdAndScope(operationId, tenantId, projectId,
            workspaceId);
        if (operation == null) {
            throw new AgentStudioException(StudioError.MCP_SERVICE_NOT_EXIST, "operation not found");
        }
        McpTransferOperationResp resp = new McpTransferOperationResp();
        resp.setOperationId(operation.getId());
        resp.setOperationType(operation.getOperationType());
        resp.setStatus(operation.getStatus());
        resp.setTotal(operation.getTotal());
        resp.setCreatedCount(operation.getCreatedCount());
        resp.setSuccessCount(operation.getSuccessCount());
        resp.setFailedCount(operation.getFailedCount());
        List<McpOperationItemEntity> items = operationDao.getOperationItems(operationId);
        List<McpTransferOperationResp.Item> respItems = new ArrayList<>();
        for (McpOperationItemEntity item : items) {
            McpTransferOperationResp.Item ri = new McpTransferOperationResp.Item();
            ri.setIndex(item.getItemIndex());
            ri.setServiceId(item.getServiceId());
            ri.setOriginalName(item.getOriginalName());
            ri.setName(item.getActualName());
            ri.setStatus(item.getStatus());
            ri.setRefreshStatus(item.getRefreshStatus());
            ri.setErrorCode(item.getErrorCode());
            ri.setReason(item.getSafeReason());
            if (item.getResultJson() != null) {
                try {
                    JsonNode node = MAPPER.readTree(item.getResultJson());
                    if (node.has("tool_count")) {
                        ri.setToolCount(node.get("tool_count").asInt());
                    }
                    if (node.has("previous_tool_count")) {
                        ri.setPreviousToolCount(node.get("previous_tool_count").asInt());
                    }
                    if (node.has("added_count")) {
                        ri.setAddedCount(node.get("added_count").asInt());
                    }
                    if (node.has("removed_count")) {
                        ri.setRemovedCount(node.get("removed_count").asInt());
                    }
                    if (node.has("added_tools")) {
                        ri.setAddedTools(MAPPER.convertValue(node.get("added_tools"), List.class));
                    }
                    if (node.has("removed_tools")) {
                        ri.setRemovedTools(MAPPER.convertValue(node.get("removed_tools"), List.class));
                    }
                    if (node.has("changed_tools")) {
                        ri.setChangedTools(MAPPER.convertValue(node.get("changed_tools"), List.class));
                    }
                    if (node.has("requires_republish")) {
                        ri.setRequiresRepublish(node.get("requires_republish").asBoolean());
                    }
                } catch (Exception ignored) {
                    // result_json 损坏时仅缺结果字段，不失败查询
                }
            }
            respItems.add(ri);
        }
        resp.setItems(respItems);
        return resp;
    }

    static String safeCode(Throwable t) {
        if (t instanceof AgentStudioException ase && ase.getErrorCode() != null) {
            return ase.getErrorCode().getCode();
        }
        return StudioError.MCP_FETCH_TOOLS_SERVER_ERROR.getCode();
    }

    static String safeReason(Throwable t) {
        String message = t.getMessage();
        if (message == null) {
            message = t.getClass().getSimpleName();
        }
        return truncate(message, 500);
    }

    static String truncate(String s, int max) {
        if (s == null) {
            return null;
        }
        return s.length() <= max ? s : s.substring(0, max);
    }

    private void clearContext() {
        try {
            RequestContextUtils.remove();
        } catch (Exception ignored) {
            // 清理尽力而为
        }
    }

    private String toJson(Map<String, Object> map) {
        try {
            return MAPPER.writeValueAsString(map);
        } catch (Exception e) {
            return "{}";
        }
    }
}
