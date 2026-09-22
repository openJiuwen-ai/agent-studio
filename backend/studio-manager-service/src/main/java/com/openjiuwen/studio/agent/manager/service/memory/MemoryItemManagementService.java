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
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.MemoryServiceInstanceEntity;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryServiceInstanceMapper;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.IMemoryItemManagementService;
import com.openjiuwen.studio.agent.manager.utils.OkHttpUtils;
import com.openjiuwen.studio.agent.manager.entity.plugin.RequestResult;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.apache.commons.lang3.StringUtils;

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

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    @Autowired
    private MemoryServiceInstanceMapper memoryServiceInstanceMapper;

    @Autowired
    private OkHttpUtils okHttpUtils;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Override
    public ListMemoryItemResponseBody listMemoryItems(String projectId, String memoryRepoId, Integer pageNum,
        Integer pageSize, String memoryType) {
        String userId = RequestContextUtils.getRequestUserId();
        if (userId == null || userId.isEmpty()) {
            throw new AgentStudioException(StudioError.AUTHENTICATION_ERROR, "User ID not found in request context");
        }

        // Branch dispatch: EXTERNAL → agent-memory 2.0 direct; BUILTIN → runtime internal API
        MemoryRepoEntity repo = memoryRepoMapper.selectById(memoryRepoId);
        if (repo != null && "EXTERNAL".equalsIgnoreCase(repo.getMemoryBackendType())) {
            return listMemoryItemsExternal(repo, userId.toLowerCase(Locale.ROOT), pageNum, pageSize);
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

        // Branch dispatch: EXTERNAL → agent-memory 2.0 direct; BUILTIN → runtime internal API
        MemoryRepoEntity repo = memoryRepoMapper.selectById(memoryRepoId);
        if (repo != null && "EXTERNAL".equalsIgnoreCase(repo.getMemoryBackendType())) {
            batchDeleteMemoryItemsExternal(repo, memoryIds, userId.toLowerCase(Locale.ROOT));
            return;
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
        } catch (AgentStudioException e) {
            // partial 时已在上方抛出语义化异常，直接透传，避免被下方 catch(Exception) 二次包装
            throw e;
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

        // Branch dispatch: EXTERNAL → agent-memory 2.0 direct; BUILTIN → runtime internal API
        MemoryRepoEntity repo = memoryRepoMapper.selectById(memoryRepoId);
        if (repo != null && "EXTERNAL".equalsIgnoreCase(repo.getMemoryBackendType())) {
            return searchMemoryItemsExternal(repo, userId.toLowerCase(Locale.ROOT), body);
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

        // Branch dispatch: EXTERNAL → agent-memory 2.0 direct; BUILTIN → runtime internal API
        MemoryRepoEntity repo = memoryRepoMapper.selectById(memoryRepoId);
        if (repo != null && "EXTERNAL".equalsIgnoreCase(repo.getMemoryBackendType())) {
            clearUserMemoryItemsExternal(repo, userId.toLowerCase(Locale.ROOT));
            return;
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

    // ==================== EXTERNAL branch: agent-memory 2.0 API calls ====================

    private MemoryServiceInstanceEntity resolveInstance(MemoryRepoEntity repo) {
        String instanceId = repo.getMemoryServiceInstanceId();
        if (instanceId == null || instanceId.isEmpty()) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_NOT_EXIST,
                "EXTERNAL repo has no instance_id");
        }
        MemoryServiceInstanceEntity instance = memoryServiceInstanceMapper.selectById(instanceId);
        if (instance == null) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_NOT_EXIST);
        }
        return instance;
    }

    private Map<String, String> buildAuthHeaders(MemoryServiceInstanceEntity instance) {
        Map<String, String> headers = new HashMap<>();
        String apiKey = encryptionAdapter.decrypt(instance.getApiKey(),
            RequestContextUtils.getRequestUserDomainId());
        if (apiKey != null && !apiKey.isEmpty()) {
            headers.put("Authorization", "Bearer " + apiKey);
        }
        return headers;
    }

    private JSONObject buildScope(String repoId, String userId) {
        JSONObject scope = new JSONObject();
        scope.put("org", "studio");
        scope.put("space", "");
        scope.put("user", repoId + ":" + userId);
        scope.put("agent", "");
        scope.put("session", "");
        return scope;
    }

    private ListMemoryItemResponseBody listMemoryItemsExternal(
        MemoryRepoEntity repo, String userId, Integer pageNum, Integer pageSize) {
        MemoryServiceInstanceEntity instance = resolveInstance(repo);
        try {
            String url = instance.getBaseUrl().replaceAll("/+$", "") + "/v1/list";
            Map<String, String> headers = buildAuthHeaders(instance);

            JSONObject body = new JSONObject();
            body.put("scope", buildScope(repo.getId(), userId));
            body.put("offset", (pageNum != null ? pageNum - 1 : 0) * (pageSize != null ? pageSize : 10));
            body.put("limit", pageSize != null ? pageSize : 10);

            RequestResult result = okHttpUtils.call(url, OkHttpUtils.Method.POST, headers, body.toJSONString());
            if (!result.isSuccess() || result.getResponse() == null) {
                return emptyListResponse(pageNum, pageSize);
            }

            JSONObject resp = JSONObject.parseObject(result.getResponse());
            int total = resp.getIntValue("count", 0);
            JSONArray itemsArray = resp.getJSONArray("items");

            ListMemoryItemResponseBody response = new ListMemoryItemResponseBody();
            response.setPageNum(pageNum);
            response.setPageSize(pageSize);
            response.setTotal(total);

            if (itemsArray != null && !itemsArray.isEmpty()) {
                List<ListMemoryItemResponseBody.MemoryItemInfo> items = itemsArray.stream()
                    .map(obj -> {
                        JSONObject mem = (JSONObject) obj;
                        ListMemoryItemResponseBody.MemoryItemInfo item = new ListMemoryItemResponseBody.MemoryItemInfo();
                        item.setId(mem.getString("id"));
                        // 2.0: content is in segments[0].content, not top-level
                        JSONArray segments = mem.getJSONArray("segments");
                        if (segments != null && !segments.isEmpty()) {
                            JSONObject firstSeg = (JSONObject) segments.get(0);
                            item.setContent(firstSeg.getString("content"));
                        }
                        item.setType(mem.getString("tier"));
                        item.setUserId(userId);
                        item.setAgentId(null);
                        item.setScore(null);
                        return item;
                    })
                    .collect(Collectors.toList());
                response.setItems(items);
            } else {
                response.setItems(Collections.emptyList());
            }
            return response;
        } catch (Exception e) {
            log.error("Failed to list external memories for repo {}: {}", repo.getId(), e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to list external memories: " + e.getMessage());
        }
    }

    /**
     * 清空当前用户在 EXTERNAL 记忆库下的全部记忆。
     * agent-memory 2.0 的 delete 不接受仅按 scope 的 selector（需 unit_ids/tags/before/filters 之一），
     * 故采用分页 list 取全量 id → 按 unit_ids purge 的循环，直至列表清空。
     */
    private void clearUserMemoryItemsExternal(MemoryRepoEntity repo, String userId) {
        MemoryServiceInstanceEntity instance = resolveInstance(repo);
        String baseUrl = instance.getBaseUrl().replaceAll("/+$", "");
        Map<String, String> headers = buildAuthHeaders(instance);
        JSONObject scope = buildScope(repo.getId(), userId);
        try {
            int pageSize = 200;
            // 上限防御：避免异常响应导致死循环
            int maxRounds = 1000;
            for (int round = 0; round < maxRounds; round++) {
                JSONObject listBody = new JSONObject();
                listBody.put("scope", scope);
                listBody.put("offset", 0);
                listBody.put("limit", pageSize);
                RequestResult listResult = okHttpUtils.call(baseUrl + "/v1/list",
                    OkHttpUtils.Method.POST, headers, listBody.toJSONString());
                if (!listResult.isSuccess() || listResult.getResponse() == null) {
                    throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                        "Failed to list external memories for clear: HTTP " + listResult.getCode());
                }
                JSONArray items = JSONObject.parseObject(listResult.getResponse()).getJSONArray("items");
                if (items == null || items.isEmpty()) {
                    return;
                }
                List<String> ids = items.stream()
                    .map(obj -> ((JSONObject) obj).getString("id"))
                    .filter(StringUtils::isNotBlank)
                    .collect(Collectors.toList());
                if (ids.isEmpty()) {
                    log.warn("External clear for repo {} got items without ids, aborting", repo.getId());
                    return;
                }

                JSONObject selector = new JSONObject();
                selector.put("unit_ids", ids);
                selector.put("scope", scope);
                selector.put("mode", "purge");
                JSONObject deleteBody = new JSONObject();
                deleteBody.put("selector", selector);
                RequestResult deleteResult = okHttpUtils.call(baseUrl + "/v1/delete",
                    OkHttpUtils.Method.POST, headers, deleteBody.toJSONString());
                if (!deleteResult.isSuccess()) {
                    throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                        "Failed to clear external memories: HTTP " + deleteResult.getCode());
                }
            }
            log.error("External clear for repo {} exceeded {} rounds, aborting", repo.getId(), maxRounds);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to clear external memories: too many rounds");
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Exception clearing external memories for repo {}: {}",
                repo.getId(), e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to clear external memories: " + e.getMessage());
        }
    }

    private void batchDeleteMemoryItemsExternal(MemoryRepoEntity repo, List<String> memoryIds, String userId) {
        MemoryServiceInstanceEntity instance = resolveInstance(repo);
        try {
            String url = instance.getBaseUrl().replaceAll("/+$", "") + "/v1/delete";
            Map<String, String> headers = buildAuthHeaders(instance);

            JSONObject selector = new JSONObject();
            selector.put("unit_ids", memoryIds);
            selector.put("scope", buildScope(repo.getId(), userId));
            selector.put("mode", "purge");
            JSONObject body = new JSONObject();
            body.put("selector", selector);

            RequestResult result = okHttpUtils.call(url, OkHttpUtils.Method.POST, headers, body.toJSONString());
            if (!result.isSuccess()) {
                log.error("Failed to batch delete external memories for repo {}: code={}",
                    repo.getId(), result.getCode());
                throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                    "Failed to delete external memories: HTTP " + result.getCode());
            }
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Exception batch deleting external memories for repo {}: {}",
                repo.getId(), e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to delete external memories: " + e.getMessage());
        }
    }

    private ListMemoryItemResponseBody searchMemoryItemsExternal(
        MemoryRepoEntity repo, String userId, SearchMemoryItemRequestBody body) {
        MemoryServiceInstanceEntity instance = resolveInstance(repo);
        try {
            String url = instance.getBaseUrl().replaceAll("/+$", "") + "/v1/search";
            Map<String, String> headers = buildAuthHeaders(instance);

            JSONObject scope = buildScope(repo.getId(), userId);
            JSONObject context = new JSONObject();
            context.put("scope", scope);

            JSONObject searchBody = new JSONObject();
            searchBody.put("query", body.getQuery());
            searchBody.put("context", context);
            searchBody.put("top_k", body.getTopK() != null ? body.getTopK() : 10);
            searchBody.put("disclosure", "l2");
            searchBody.put("with_trajectory", false);

            RequestResult result = okHttpUtils.call(url, OkHttpUtils.Method.POST, headers, searchBody.toJSONString());
            if (!result.isSuccess() || result.getResponse() == null) {
                ListMemoryItemResponseBody response = new ListMemoryItemResponseBody();
                response.setItems(Collections.emptyList());
                response.setTotal(0);
                return response;
            }

            JSONObject resp = JSONObject.parseObject(result.getResponse());
            JSONArray itemsArray = resp.getJSONArray("items");
            int count = resp.getIntValue("count", itemsArray != null ? itemsArray.size() : 0);

            ListMemoryItemResponseBody response = new ListMemoryItemResponseBody();
            response.setTotal(count);

            if (itemsArray != null && !itemsArray.isEmpty()) {
                List<ListMemoryItemResponseBody.MemoryItemInfo> items = itemsArray.stream()
                    .map(obj -> {
                        JSONObject mem = (JSONObject) obj;
                        ListMemoryItemResponseBody.MemoryItemInfo item = new ListMemoryItemResponseBody.MemoryItemInfo();
                        item.setId(mem.getString("unit_id"));
                        item.setContent(mem.getString("content"));
                        item.setUserId(userId);
                        item.setAgentId(null);
                        item.setScore(mem.getDouble("score") != null ? mem.getDouble("score").floatValue() : null);
                        return item;
                    })
                    .collect(Collectors.toList());
                response.setItems(items);
            } else {
                response.setItems(Collections.emptyList());
            }
            return response;
        } catch (Exception e) {
            log.error("Failed to search external memories for repo {}: {}", repo.getId(), e.getMessage(), e);
            throw new AgentStudioException(StudioError.CSS_UNI_SEARCH_SERVICE_EXCEPTION,
                "Failed to search external memories: " + e.getMessage());
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
