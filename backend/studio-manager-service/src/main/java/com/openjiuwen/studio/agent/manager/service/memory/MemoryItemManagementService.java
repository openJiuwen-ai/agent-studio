/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.memory;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryItemResponseBody;
import com.openjiuwen.studio.agent.manager.dto.SearchMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.IMemoryItemManagementService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class MemoryItemManagementService implements IMemoryItemManagementService {
    private static final Logger log = LoggerFactory.getLogger(MemoryItemManagementService.class);

    @Autowired
    private AgentRuntimeClient agentRuntimeClient;

    @Override
    public ListMemoryItemResponseBody listMemoryItems(String projectId, String memoryRepoId, Integer pageNum,
        Integer pageSize, String memoryType) {
        String userId = RequestContextUtils.getRequestUserId();
        if (userId == null || userId.isEmpty()) {
            throw new AgentStudioException(StudioError.AUTHENTICATION_ERROR, "User ID not found in request context");
        }

        try {
            // 静态代码检查G.OTH.04：toLowerCase指定Locale.ROOT，避免在土耳其语等环境下产生大小写转换异常
            ResponseEntity<Object> response = agentRuntimeClient.listMemories(
                memoryRepoId, userId.toLowerCase(Locale.ROOT), pageSize, pageNum, memoryType);

            if (response.getBody() == null) {
                return emptyListResponse(pageNum, pageSize);
            }

            // Parse runtime response: {"total": N, "memories": [...]}
            JSONObject body = JSONObject.from(response.getBody());
            JSONArray memoriesArray = body.getJSONArray("memories");
            int total = body.getIntValue("total", 0);

            ListMemoryItemResponseBody result = new ListMemoryItemResponseBody();
            result.setPageNum(pageNum);
            result.setPageSize(pageSize);
            result.setTotal(total);

            if (memoriesArray != null && !memoriesArray.isEmpty()) {
                List<ListMemoryItemResponseBody.MemoryItemInfo> items = memoriesArray.stream()
                    .map(obj -> {
                        JSONObject mem = (JSONObject) obj;
                        ListMemoryItemResponseBody.MemoryItemInfo item = new ListMemoryItemResponseBody.MemoryItemInfo();
                        item.setId(mem.getString("memory_id"));
                        item.setContent(mem.getString("content"));
                        item.setType(mem.getString("type"));
                        item.setLastUpdateTime(mem.getString("last_update_time"));
                        item.setUserId(userId);
                        item.setAgentId(null); // Not available in runtime response
                        item.setScore(null); // Not applicable for list
                        return item;
                    })
                    .collect(Collectors.toList());
                result.setItems(items);
            } else {
                result.setItems(Collections.emptyList());
            }

            return result;
        } catch (Exception e) {
            log.error("Failed to list memories from runtime for repo {}: {}", memoryRepoId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to list memories: " + e.getMessage());
        }
    }

    @Override
    public void deleteMemoryItem(String projectId, String memoryRepoId, String memoryId) {
        // Use batch delete with single ID
        BatchDeleteMemoryItemRequestBody body = new BatchDeleteMemoryItemRequestBody();
        body.setMemoryIds(Collections.singletonList(memoryId));
        batchDeleteMemoryItems(projectId, memoryRepoId, body);
    }

    @Override
    public void batchDeleteMemoryItems(String projectId, String memoryRepoId, BatchDeleteMemoryItemRequestBody body) {
        List<String> memoryIds = body.getMemoryIds();
        if (memoryIds == null || memoryIds.isEmpty()) {
            throw new AgentStudioException(StudioError.MEMORY_REPO_NOT_EXIST,
                "memoryIds must not be empty for batch delete");
        }

        String userId = RequestContextUtils.getRequestUserId();
        if (userId == null || userId.isEmpty()) {
            throw new AgentStudioException(StudioError.AUTHENTICATION_ERROR, "User ID not found in request context");
        }

        try {
            Map<String, List<String>> requestBody = new HashMap<>();
            requestBody.put("memory_ids", memoryIds);

            // 静态代码检查G.OTH.04：toLowerCase指定Locale.ROOT，避免在土耳其语等环境下产生大小写转换异常
            ResponseEntity<Object> response = agentRuntimeClient.batchDeleteMemories(
                memoryRepoId, userId.toLowerCase(Locale.ROOT), requestBody);

            if (response.getBody() != null) {
                JSONObject result = JSONObject.from(response.getBody());
                String status = result.getString("status");
                if ("partial".equals(status)) {
                    JSONArray errors = result.getJSONArray("errors");
                    log.warn("Batch delete partially failed for repo {}: {}", memoryRepoId, errors);
                    // 与批量修改一致的保守策略：任一条失败则整体失败，避免前端误提示删除成功
                    throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                        "Failed to delete memories, partial errors: " + errors);
                }
            }
        } catch (Exception e) {
            log.error("Failed to batch delete memories from runtime for repo {}: {}",
                memoryRepoId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to delete memories: " + e.getMessage());
        }
    }

    @Override
    public ListMemoryItemResponseBody searchMemoryItems(String projectId, String memoryRepoId,
        SearchMemoryItemRequestBody body) {
        String userId = RequestContextUtils.getRequestUserId();
        if (userId == null || userId.isEmpty()) {
            throw new AgentStudioException(StudioError.AUTHENTICATION_ERROR, "User ID not found in request context");
        }

        try {
            Map<String, Object> searchBody = new HashMap<>();
            searchBody.put("query", body.getQuery());
            searchBody.put("top_k", body.getTopK() != null ? body.getTopK() : 10);
            searchBody.put("threshold", body.getThreshold() != null ? body.getThreshold().doubleValue() : 0.3);

            // 静态代码检查G.OTH.04：toLowerCase指定Locale.ROOT，避免在土耳其语等环境下产生大小写转换异常
            ResponseEntity<Object> response = agentRuntimeClient.searchMemories(
                memoryRepoId, userId.toLowerCase(Locale.ROOT), searchBody);

            if (response.getBody() == null) {
                ListMemoryItemResponseBody result = new ListMemoryItemResponseBody();
                result.setItems(Collections.emptyList());
                result.setTotal(0);
                return result;
            }

            // Parse runtime response: {"total": N, "memories": [...]}
            JSONObject responseBody = JSONObject.from(response.getBody());
            if (responseBody.containsKey("error")) {
                // runtime 以 200 + error 字段返回失败，不能当作空结果静默成功
                throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                    "Failed to search memories: " + responseBody.getString("error"));
            }
            JSONArray memoriesArray = responseBody.getJSONArray("memories");
            int total = responseBody.getIntValue("total", 0);

            ListMemoryItemResponseBody result = new ListMemoryItemResponseBody();
            result.setTotal(total);

            if (memoriesArray != null && !memoriesArray.isEmpty()) {
                List<ListMemoryItemResponseBody.MemoryItemInfo> items = memoriesArray.stream()
                    .map(obj -> {
                        JSONObject mem = (JSONObject) obj;
                        ListMemoryItemResponseBody.MemoryItemInfo item = new ListMemoryItemResponseBody.MemoryItemInfo();
                        item.setId(mem.getString("memory_id"));
                        item.setContent(mem.getString("content"));
                        item.setUserId(userId);
                        item.setAgentId(null);
                        item.setScore(mem.getDouble("score") != null ? mem.getDouble("score").floatValue() : null);
                        return item;
                    })
                    .collect(Collectors.toList());
                result.setItems(items);
            } else {
                result.setItems(Collections.emptyList());
            }

            return result;
        } catch (Exception e) {
            log.error("Failed to search memories from runtime for repo {}: {}", memoryRepoId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to search memories: " + e.getMessage());
        }
    }

    @Override
    public void updateMemoryItems(String projectId, String memoryRepoId, UpdateMemoryItemRequestBody body) {
        List<UpdateMemoryItemRequestBody.UpdateMemoryItem> memories = body.getMemories();
        if (memories == null || memories.isEmpty()) {
            throw new AgentStudioException(StudioError.MEMORY_REPO_NOT_EXIST,
                "memories must not be empty for batch update");
        }

        String userId = RequestContextUtils.getRequestUserId();
        if (userId == null || userId.isEmpty()) {
            throw new AgentStudioException(StudioError.AUTHENTICATION_ERROR, "User ID not found in request context");
        }

        // 静态代码检查G.OTH.04：toLowerCase指定Locale.ROOT，避免在土耳其语等环境下产生大小写转换异常
        String lowerUserId = userId.toLowerCase(Locale.ROOT);

        // 保守策略（2A）：任一条失败则整体失败，并记录失败条目id；已成功条目不回滚
        List<String> failedIds = new ArrayList<>();
        List<String> failedReasons = new ArrayList<>();
        for (UpdateMemoryItemRequestBody.UpdateMemoryItem item : memories) {
            try {
                Map<String, String> requestBody = new HashMap<>();
                requestBody.put("user_id", lowerUserId);
                requestBody.put("content", item.getContent());

                ResponseEntity<Object> response = agentRuntimeClient.updateMemory(
                    memoryRepoId, item.getMemoryId(), requestBody);
                JSONObject result = response.getBody() == null ? null : JSONObject.from(response.getBody());
                String status = result == null ? null : result.getString("status");
                if (!"ok".equals(status)) {
                    // 非 ok（含 skipped/error）都视为该条未写入，避免用户编辑被静默丢弃
                    failedIds.add(item.getMemoryId());
                    failedReasons.add(item.getMemoryId() + ": " + (result == null ? "empty response" : status));
                }
            } catch (Exception e) {
                log.error("Failed to update memory {} in repo {}: {}",
                    item.getMemoryId(), memoryRepoId, e.getMessage(), e);
                failedIds.add(item.getMemoryId());
                failedReasons.add(item.getMemoryId() + ": " + e.getMessage());
            }
        }

        if (!failedIds.isEmpty()) {
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to update memories, failed ids: " + failedIds + ", reasons: " + failedReasons);
        }
    }

    @Override
    public void clearUserMemoryItems(String projectId, String memoryRepoId) {
        String userId = RequestContextUtils.getRequestUserId();
        if (userId == null || userId.isEmpty()) {
            throw new AgentStudioException(StudioError.AUTHENTICATION_ERROR, "User ID not found in request context");
        }

        try {
            // 静态代码检查G.OTH.04：toLowerCase指定Locale.ROOT，避免在土耳其语等环境下产生大小写转换异常
            ResponseEntity<Object> response = agentRuntimeClient.clearUserMemories(
                memoryRepoId, userId.toLowerCase(Locale.ROOT));
            JSONObject result = response.getBody() == null ? null : JSONObject.from(response.getBody());
            String status = result == null ? null : result.getString("status");
            // skipped = 记忆库未初始化（无数据可清空），视为幂等成功
            if (!"ok".equals(status) && !"skipped".equals(status)) {
                throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                    "Failed to clear memories: " + (result == null ? "empty response" : status));
            }
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to clear memories from runtime for repo {}: {}", memoryRepoId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to clear memories: " + e.getMessage());
        }
    }

    private ListMemoryItemResponseBody emptyListResponse(Integer pageNum, Integer pageSize) {
        ListMemoryItemResponseBody response = new ListMemoryItemResponseBody();
        response.setItems(Collections.emptyList());
        response.setTotal(0);
        response.setPageNum(pageNum);
        response.setPageSize(pageSize);
        return response;
    }
}
