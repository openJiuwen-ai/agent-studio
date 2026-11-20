/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.entity.McpOperationEntity;
import com.openjiuwen.studio.agent.manager.entity.McpOperationItemEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.service.mcp.McpServiceManager;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * FEAT-134 MCP 工具快照服务（重载核心）。
 *
 * 复用 McpServiceManager.getMcpServiceToolList 的既有连接链路（智能重试/异常拆包/
 * 错误映射）——不另造连接协议；消费其返回值区分「合法空列表」与「失败」。
 * 差异按单服务内工具原始 name 精确匹配；原子提交带归属+活动操作+修订号条件。
 */
@Service
public class McpToolSnapshotService {

    private static final Logger log = LoggerFactory.getLogger(McpToolSnapshotService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    /** 通过 ApplicationContext 延迟获取，规避 Spring DI 循环（McpServiceManager ↔ transfer 包） */
    @Autowired
    private org.springframework.context.ApplicationContext applicationContext;

    private McpServiceManager getMcpServiceManager() {
        return applicationContext.getBean(McpServiceManager.class);
    }

    @Autowired
    private McpServiceDao serviceDao;

    @Autowired
    private McpServiceMapper serviceMapper;

    /** 通过 ApplicationContext 延迟获取，规避 McpOperationService ↔ McpToolSnapshotService 循环 */
    private McpOperationService getOperationService() {
        return applicationContext.getBean(McpOperationService.class);
    }

    /**
     * 拉取工具（typed 结果）。复用既有 getMcpServiceToolList 连接链路：
     * - 非空 JSON → 成功 + 工具列表
     * - 空串（合法零工具） → 成功 + 空列表
     * - 抛异常 → 失败 + 错误码与脱敏原因
     */
    public McpToolFetchResult fetchTools(McpServiceEntity entity) {
        try {
            String toolsJson = getMcpServiceManager().getMcpServiceToolList(entity);
            if (toolsJson == null || toolsJson.isBlank()) {
                // 旧链路空串=零工具（安装时折成空串）；新链路视为合法空列表（L2 §5.4）
                return McpToolFetchResult.ok(List.of());
            }
            List<Map<String, Object>> tools = MAPPER.readValue(toolsJson,
                new TypeReference<List<Map<String, Object>>>() {
                });
            // 工具名重复视为协议结果非法，不提交歧义快照（L2 §5.4）
            List<String> names = new ArrayList<>();
            for (Map<String, Object> tool : tools) {
                Object name = tool.get("name");
                if (name == null || names.contains(String.valueOf(name))) {
                    return McpToolFetchResult.fail(StudioError.MCP_TRANSFER_FIELD_INVALID.getCode(),
                        "duplicate or missing tool name in server response");
                }
                names.add(String.valueOf(name));
            }
            return McpToolFetchResult.ok(tools);
        } catch (AgentStudioException e) {
            return McpToolFetchResult.fail(e.getErrorCode() != null ? e.getErrorCode().getCode()
                : StudioError.MCP_FETCH_TOOLS_SERVER_ERROR.getCode(),
                McpOperationService.truncate(e.getMessage(), 500));
        } catch (Exception e) {
            return McpToolFetchResult.fail(StudioError.MCP_FETCH_TOOLS_SERVER_ERROR.getCode(),
                McpOperationService.truncate(e.getMessage(), 500));
        }
    }

    public String serializeTools(List<Map<String, Object>> tools) {
        try {
            return MAPPER.writeValueAsString(tools);
        } catch (Exception e) {
            return "[]";
        }
    }

    /**
     * 重载执行：工作线程开始前再次读取最新实体 → 拉取 → 差异计算 → 原子提交。
     * 失败保留原快照/配置/状态/fail_reason（L2 §3.4 保护清单）。
     */
    public void executeReload(McpOperationEntity operation, McpOperationItemEntity item) {
        McpServiceEntity entity = serviceDao.getMcpServiceById(item.getServiceId(), operation.getTenantId(),
            null, operation.getProjectId(), operation.getWorkspaceId());
        if (entity == null) {
            getOperationService().failItem(operation, item, StudioError.MCP_SERVICE_NOT_EXIST.getCode(),
                "service not found or not in scope");
            return;
        }
        if (entity.getActiveMcpOperationId() != null
            && !operation.getId().equals(entity.getActiveMcpOperationId())) {
            getOperationService().failItem(operation, item, StudioError.MCP_OPERATION_CONFLICT.getCode(),
                "another operation is active");
            return;
        }

        List<Map<String, Object>> previousTools = parseTools(entity.getTools());
        McpToolFetchResult result = fetchTools(entity);

        if (!result.success()) {
            // 失败路径：不写 tools/server_config/fc_instance_status/fail_reason（L2 §3.4）
            getOperationService().failItem(operation, item, result.errorCode(), result.safeReason());
            return;
        }

        Map<String, Object> diff = computeDiff(previousTools, result.tools());
        String toolsJson = serializeTools(result.tools());
        long expectedRevision = entity.getSnapshotRevision() == null ? 0L : entity.getSnapshotRevision();

        int updated = serviceMapper.commitToolSnapshot(entity.getId(), operation.getTenantId(),
            operation.getProjectId(), operation.getWorkspaceId(), operation.getId(), expectedRevision, toolsJson);
        if (updated != 1) {
            // 0=被删除/配置冲突/任务已过期/操作所有权丢失（L2 §5.5）
            getOperationService().failItem(operation, item, StudioError.MCP_OPERATION_CONFLICT.getCode(),
                "snapshot commit failed ownership check; original data preserved");
            return;
        }

        // 成功结果建立在数据库已提交的快照上（L2 §3.4）
        diff.put("previous_tool_count", previousTools.size());
        diff.put("requires_republish", true);
        item.setStatus("SUCCESS");
        item.setRefreshStatus("SUCCESS");
        item.setResultJson(toJson(diff));
        item.setFinishedDate(new Timestamp(System.currentTimeMillis()));
        // finishOperationItem 由 operationService.succeedItem 完成（含汇总）
        item.setResultJson(toJson(diff));
        getOperationService().succeedItemRaw(operation, item);
    }

    /**
     * 工具差异：按原始 name 精确匹配（不能用界面展示名）；同名工具内容变化列入 changed。
     */
    static Map<String, Object> computeDiff(List<Map<String, Object>> previous,
        List<Map<String, Object>> current) {
        Map<String, Map<String, Object>> prev = new LinkedHashMap<>();
        for (Map<String, Object> tool : previous) {
            prev.put(String.valueOf(tool.get("name")), tool);
        }
        Map<String, Map<String, Object>> curr = new LinkedHashMap<>();
        for (Map<String, Object> tool : current) {
            curr.put(String.valueOf(tool.get("name")), tool);
        }
        List<String> added = new ArrayList<>();
        List<String> removed = new ArrayList<>();
        List<String> changed = new ArrayList<>();
        for (String name : curr.keySet()) {
            if (!prev.containsKey(name)) {
                added.add(name);
            } else if (!jsonEquals(prev.get(name), curr.get(name))) {
                changed.add(name);
            }
        }
        for (String name : prev.keySet()) {
            if (!curr.containsKey(name)) {
                removed.add(name);
            }
        }
        Map<String, Object> diff = new HashMap<>();
        diff.put("tool_count", current.size());
        diff.put("added_count", added.size());
        diff.put("removed_count", removed.size());
        diff.put("added_tools", added);
        diff.put("removed_tools", removed);
        diff.put("changed_tools", changed);
        return diff;
    }

    private static boolean jsonEquals(Map<String, Object> a, Map<String, Object> b) {
        try {
            return MAPPER.writeValueAsString(a).equals(MAPPER.writeValueAsString(b));
        } catch (Exception e) {
            return false;
        }
    }

    private List<Map<String, Object>> parseTools(String tools) {
        if (tools == null || tools.isBlank()) {
            return List.of();
        }
        try {
            List<Map<String, Object>> parsed = MAPPER.readValue(tools,
                new TypeReference<List<Map<String, Object>>>() {
                });
            return parsed != null ? parsed : List.of();
        } catch (Exception e) {
            return List.of();
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
