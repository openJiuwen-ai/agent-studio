/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.memory;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryServiceInstancesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.MemoryServiceInstanceListItem;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ShowMemoryServiceInstanceResponseBody;
import com.openjiuwen.studio.agent.manager.entity.MemoryServiceInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.RequestResult;
import com.openjiuwen.studio.agent.manager.mapper.MemoryServiceInstanceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.IMemoryServiceInstanceService;
import com.openjiuwen.studio.agent.manager.utils.OkHttpUtils;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 外部记忆服务实例管理实现类
 */
@Service
@Slf4j
public class MemoryServiceInstanceService implements IMemoryServiceInstanceService {

    /**
     * OBS auth 文件路径模板：memory-auth/{instanceId}.json
     * runtime 按 IR 的 instance_id 从此路径惰性取 api_key（镜像 model-auth 约定）
     */
    private static final String MEMORY_AUTH_PATH = "memory-auth/%s.json";

    @Autowired
    private MemoryServiceInstanceMapper instanceMapper;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private OkHttpUtils okHttpUtils;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    // ==================== CRUD ====================

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "MemoryServiceInstance",
        description = "创建外部记忆服务实例",
        resourceId = "-1",
        resourceName = "body.name"
    )
    public CreateMemoryServiceInstanceResponseBody createInstance(String projectId, String workspaceId,
        CreateMemoryServiceInstanceRequestBody body) {
        MemoryServiceInstanceEntity entity = MemoryServiceInstanceEntity.builder()
            .id(UUID.randomUUID().toString())
            .name(body.getName())
            .baseUrl(body.getBaseUrl())
            .apiKey(encryptionAdapter.encrypt(body.getApiKey(), RequestContextUtils.getRequestUserDomainId()))
            .workspaceId(workspaceId)
            .projectId(projectId)
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .healthStatus("UNKNOWN")
            .deployMeta(body.getDeployMeta())
            .createdUserId(RequestContextUtils.getRequestUserId())
            .createdUserName(RequestContextUtils.getRequestUserName())
            .lastUpdateUserId(RequestContextUtils.getRequestUserId())
            .lastUpdateUserName(RequestContextUtils.getRequestUserName())
            .build();

        instanceMapper.insert(entity);

        // 将 api_key 写入 OBS auth 文件，供 runtime 惰性取（对齐 model-auth 存储约定）
        saveApiKeyToObsAuth(entity.getId(), body.getApiKey());

        CreateMemoryServiceInstanceResponseBody response = new CreateMemoryServiceInstanceResponseBody();
        response.setInstanceId(entity.getId());
        return response;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "MemoryServiceInstance",
        description = "删除外部记忆服务实例",
        resourceId = "instanceId",
        resourceName = ""
    )
    public void deleteInstance(String projectId, String instanceId, String workspaceId) {
        MemoryServiceInstanceEntity entity = instanceMapper.selectById(instanceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_NOT_EXIST);
        }

        // 删除前校验是否有记忆库在用
        int repoCount = instanceMapper.countReposByInstanceId(instanceId);
        if (repoCount > 0) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_IN_USE,
                "该实例已被 " + repoCount + " 个记忆库引用，无法删除");
        }

        instanceMapper.deleteById(instanceId);

        // 清理 OBS auth 文件
        try {
            obsService.deleteObject(String.format(MEMORY_AUTH_PATH, instanceId));
        } catch (Exception e) {
            log.warn("Failed to delete OBS auth file for instance {}: {}", instanceId, e.getMessage());
        }
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "MemoryServiceInstance",
        description = "修改外部记忆服务实例",
        resourceId = "instanceId",
        resourceName = "body.name"
    )
    public void modifyInstance(String projectId, String instanceId, String workspaceId,
        ModifyMemoryServiceInstanceRequestBody body) {
        MemoryServiceInstanceEntity existing = instanceMapper.selectById(instanceId);
        if (existing == null) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_NOT_EXIST);
        }

        MemoryServiceInstanceEntity.MemoryServiceInstanceEntityBuilder builder = MemoryServiceInstanceEntity.builder()
            .id(instanceId)
            .projectId(projectId)
            .lastUpdateUserId(RequestContextUtils.getRequestUserId())
            .lastUpdateUserName(RequestContextUtils.getRequestUserName());

        if (StringUtils.isNotBlank(body.getName())) {
            builder.name(body.getName());
        }
        if (StringUtils.isNotBlank(body.getBaseUrl())) {
            builder.baseUrl(body.getBaseUrl());
        }
        if (StringUtils.isNotBlank(body.getApiKey())) {
            String encrypted = encryptionAdapter.encrypt(body.getApiKey(),
                RequestContextUtils.getRequestUserDomainId());
            builder.apiKey(encrypted);
            // 更新 OBS auth 文件
            saveApiKeyToObsAuth(instanceId, body.getApiKey());
        }
        if (body.getDeployMeta() != null) {
            builder.deployMeta(body.getDeployMeta());
        }

        instanceMapper.updateById(builder.build());
    }

    @Override
    @Transactional
    public ListMemoryServiceInstancesResponseBody listInstances(String projectId, String workspaceId,
        String name) {
        PageHelper.offsetPage(0, 1000); // 实例数量通常不大
        List<MemoryServiceInstanceEntity> entities = instanceMapper.selectByCondition(
            projectId, workspaceId, RequestContextUtils.getRequestUserDomainId(), name);
        PageInfo<MemoryServiceInstanceEntity> pageInfo = new PageInfo<>(entities);

        List<MemoryServiceInstanceListItem> items = entities.stream()
            .map(this::toListItem)
            .collect(Collectors.toList());

        ListMemoryServiceInstancesResponseBody response = new ListMemoryServiceInstancesResponseBody();
        response.setItems(items);
        response.setTotal(pageInfo.getTotal());
        return response;
    }

    @Override
    @Transactional
    public ShowMemoryServiceInstanceResponseBody showInstance(String projectId, String instanceId,
        String workspaceId) {
        MemoryServiceInstanceEntity entity = instanceMapper.selectById(instanceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_NOT_EXIST);
        }
        return toShowResponse(entity);
    }

    // ==================== 健康检查 ====================

    @Override
    @Transactional
    public ShowMemoryServiceInstanceResponseBody healthCheck(String projectId, String instanceId,
        String workspaceId) {
        MemoryServiceInstanceEntity entity = instanceMapper.selectById(instanceId);
        if (entity == null) {
            throw new AgentStudioException(StudioError.MEMORY_SERVICE_INSTANCE_NOT_EXIST);
        }

        String healthStatus = checkHealth(entity);
        entity.setHealthStatus(healthStatus);
        entity.setLastCheckAt(new Date());
        entity.setProjectId(projectId);
        instanceMapper.updateById(entity);

        return toShowResponse(instanceMapper.selectById(instanceId));
    }

    /**
     * 调 agent-memory 2.0 GET /healthz，返回 HEALTHY/UNHEALTHY
     */
    private String checkHealth(MemoryServiceInstanceEntity entity) {
        try {
            String healthUrl = StringUtils.removeEnd(entity.getBaseUrl(), "/") + "/healthz";
            Map<String, String> headers = new HashMap<>();
            String apiKey = encryptionAdapter.decrypt(entity.getApiKey(),
                RequestContextUtils.getRequestUserDomainId());
            if (StringUtils.isNotBlank(apiKey)) {
                headers.put("Authorization", "Bearer " + apiKey);
            }
            log.info("Health check calling {} for instance {}, apiKey present: {}",
                healthUrl, entity.getId(), apiKey != null && !apiKey.isEmpty());
            RequestResult result = okHttpUtils.call(healthUrl, OkHttpUtils.Method.GET, headers, "");
            if (result.isSuccess()) {
                log.info("Health check SUCCESS for instance {}: code={}", entity.getId(), result.getCode());
                return "HEALTHY";
            }
            log.warn("Health check failed for instance {}: code={}, response={}, exception={}",
                entity.getId(), result.getCode(),
                result.getResponse() != null ? result.getResponse().substring(0, Math.min(result.getResponse().length(), 200)) : "",
                result.getExceptionMessage());
            return "UNHEALTHY";
        } catch (Exception e) {
            log.warn("Health check exception for instance {}: {}", entity.getId(), e.getMessage(), e);
            return "UNHEALTHY";
        }
    }

    // ==================== agent-memory 2.0 API 调用（管理通路，Java 直连） ====================

    @Override
    public void pushScopeConfig(String instanceId, String scopeId, String scopeModelConfig) {
        // agent-memory 2.0 不支持 per-scope 模型热加载（set_scope_config 已移除）。
        // 模型配置由实例启动配置决定。此方法保留为空实现以维持接口兼容。
        log.info("pushScopeConfig is no-op in agent-memory 2.0 (scope={}, instance={})", scopeId, instanceId);
    }

    @Override
    public void deleteMemByScope(String instanceId, String scopeId) {
        MemoryServiceInstanceEntity entity = instanceMapper.selectById(instanceId);
        if (entity == null) {
            log.warn("Instance {} not found for delete_mem_by_scope, skipping", instanceId);
            return;
        }
        try {
            String baseUrl = StringUtils.removeEnd(entity.getBaseUrl(), "/");
            Map<String, String> headers = new HashMap<>();
            String apiKey = encryptionAdapter.decrypt(entity.getApiKey(),
                RequestContextUtils.getRequestUserDomainId());
            if (StringUtils.isNotBlank(apiKey)) {
                headers.put("Authorization", "Bearer " + apiKey);
            }

            // scope.user 写入路径为 "{repoId}:{userId}"，删库时无具体 userId，
            // 用 "{scopeId}:" 作为 user 前缀以匹配该 repo 下所有用户的数据。
            JSONObject scope = new JSONObject();
            scope.put("org", "studio");
            scope.put("space", "");
            scope.put("user", scopeId + ":");
            scope.put("agent", "");
            scope.put("session", "");

            // agent-memory 2.0 的 delete 不接受仅按 scope 的 selector（需 unit_ids 之一），
            // 故采用分页 list 取全量 id → 按 unit_ids purge 的循环，直至列表清空。
            int pageSize = 200;
            int maxRounds = 1000;
            for (int round = 0; round < maxRounds; round++) {
                JSONObject listBody = new JSONObject();
                listBody.put("scope", scope);
                listBody.put("offset", 0);
                listBody.put("limit", pageSize);
                RequestResult listResult = okHttpUtils.call(baseUrl + "/v1/list",
                    OkHttpUtils.Method.POST, headers, listBody.toJSONString());
                if (!listResult.isSuccess() || listResult.getResponse() == null) {
                    log.error("Failed to list for delete_mem_by_scope on instance {} scope {}: code={}",
                        instanceId, scopeId, listResult.getCode());
                    return;
                }
                JSONArray items = JSONObject.parseObject(listResult.getResponse()).getJSONArray("items");
                if (items == null || items.isEmpty()) {
                    log.info("delete_mem_by_scope completed on instance {} scope {} after {} round(s)",
                        instanceId, scopeId, round);
                    return;
                }
                List<String> ids = items.stream()
                    .map(obj -> ((JSONObject) obj).getString("id"))
                    .filter(StringUtils::isNotBlank)
                    .collect(Collectors.toList());
                if (ids.isEmpty()) {
                    log.warn("delete_mem_by_scope on instance {} scope {} got items without ids, aborting",
                        instanceId, scopeId);
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
                    log.error("Failed to delete_mem_by_scope on instance {} scope {}: code={}, response={}",
                        instanceId, scopeId, deleteResult.getCode(), deleteResult.getResponse());
                    return;
                }
            }
            log.error("delete_mem_by_scope on instance {} scope {} exceeded {} rounds, aborting",
                instanceId, scopeId, maxRounds);
        } catch (Exception e) {
            log.error("Exception deleting by scope on instance {} for scope {}: {}",
                instanceId, scopeId, e.getMessage(), e);
        }
    }

    // ==================== OBS auth 凭证下发 ====================

    /**
     * 将 api_key 写入 OBS auth 文件 memory-auth/{instanceId}.json
     * runtime 按 IR 的 instance_id 从此路径惰性取 api_key（镜像 model_service.resolver 的 model-auth 约定）
     */
    private void saveApiKeyToObsAuth(String instanceId, String apiKey) {
        try {
            String path = String.format(MEMORY_AUTH_PATH, instanceId);
            JSONObject authData = new JSONObject();
            authData.put("instance_id", instanceId);
            authData.put("api_key", apiKey);
            obsService.putObject(path, authData.toJSONString());
            log.info("Saved memory auth file to OBS: {}", path);
        } catch (Exception e) {
            log.error("Failed to save memory auth file to OBS for instance {}: {}", instanceId, e.getMessage(), e);
            throw new AgentStudioException(StudioError.OBS_FAILED,
                "Failed to save memory auth: " + e.getMessage());
        }
    }

    // ==================== 转换方法 ====================

    private MemoryServiceInstanceListItem toListItem(MemoryServiceInstanceEntity entity) {
        MemoryServiceInstanceListItem item = new MemoryServiceInstanceListItem();
        item.setInstanceId(entity.getId());
        item.setName(entity.getName());
        item.setBaseUrl(entity.getBaseUrl());
        item.setHealthStatus(entity.getHealthStatus());
        item.setLastCheckAt(entity.getLastCheckAt());
        item.setDeployMeta(entity.getDeployMeta());
        item.setCreatedUserId(entity.getCreatedUserId());
        item.setCreatedUserName(entity.getCreatedUserName());
        item.setCreateTime(entity.getCreateTime());
        item.setUpdateTime(entity.getUpdateTime());
        return item;
    }

    private ShowMemoryServiceInstanceResponseBody toShowResponse(MemoryServiceInstanceEntity entity) {
        ShowMemoryServiceInstanceResponseBody response = new ShowMemoryServiceInstanceResponseBody();
        response.setInstanceId(entity.getId());
        response.setName(entity.getName());
        response.setBaseUrl(entity.getBaseUrl());
        response.setHealthStatus(entity.getHealthStatus());
        response.setLastCheckAt(entity.getLastCheckAt());
        response.setDeployMeta(entity.getDeployMeta());
        response.setCreatedUserId(entity.getCreatedUserId());
        response.setCreatedUserName(entity.getCreatedUserName());
        response.setCreateTime(entity.getCreateTime());
        response.setUpdateTime(entity.getUpdateTime());
        return response;
    }
}
