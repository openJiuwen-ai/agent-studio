/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.memory;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SqlLikeEscapeHelper;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryReposResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryRepositoriesQo;
import com.openjiuwen.studio.agent.manager.dto.LongTermMemoryStrategy;
import com.openjiuwen.studio.agent.manager.dto.MemoryRepoListItem;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.IMemoryRepoManagementService;
import com.openjiuwen.studio.agent.manager.service.IMemoryServiceInstanceService;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.InvalidParameterException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 记忆库管理实现类
 */
@Service
public class MemoryRepoManagementService implements IMemoryRepoManagementService {

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private AgentRuntimeClient agentRuntimeClient;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private IMemoryServiceInstanceService memoryServiceInstanceService;

    @Value("${memory.default-icon}")
    private String memoryDefaultIcon;

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "MemoryRepo",
        description = "创建记忆库",
        resourceId = "-1",
        resourceName = "body.name"
    )
    public CreateMemoryRepoResponseBody createMemoryRepo(String projectId, String workspaceId, CreateMemoryRepoRequestBody body) {
        // 转换请求体为实体
        MemoryRepoEntity entity = buildMemoryRepoEntity(projectId, workspaceId, body);
        if (StringUtils.isNotEmpty(body.getIcon())) {
            entity.setIcon(body.getIcon());
        }
        // 校验长期策略是否合法，类型唯一/至少一个策略
        checkLongMemoryStrategies(entity.getLongTermMemoryStrategies());

        // EXTERNAL 后端校验：验证实例存在且可达
        validateExternalBackend(entity);

        // 插入数据库
        memoryRepoMapper.insert(entity);

        // 构建返回结果
        CreateMemoryRepoResponseBody response = new CreateMemoryRepoResponseBody();
        response.setMemoryRepoId(entity.getId());
        return response;
    }

    private void checkLongMemoryStrategies(List<LongTermMemoryStrategy> longTermMemoryStrategies) {
        if (longTermMemoryStrategies == null || longTermMemoryStrategies.isEmpty()) {
            throw new InvalidParameterException("至少需要一个长期记忆策略");
        }
        // 检查策略类型是否唯一
        Set<LongTermMemoryStrategy.TypeEnum> strategyTypes = new HashSet<>();
        for (LongTermMemoryStrategy strategy : longTermMemoryStrategies) {
            if (strategy == null || strategy.getType() == null) {
                throw new InvalidParameterException("记忆策略类型不能为空");
            }

            if (!strategyTypes.add(strategy.getType())) {
                throw new InvalidParameterException("记忆策略类型重复: " + strategy.getType());
            }
        }
    }

    private static MemoryRepoEntity buildMemoryRepoEntity(String projectId, String workspaceId, CreateMemoryRepoRequestBody body) {
        return MemoryRepoEntity.builder()
            .id(UUID.randomUUID().toString())
            .projectId(projectId)
            .workspaceId(workspaceId)
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .createdUserId(RequestContextUtils.getRequestUserId())
            .createdUserName(RequestContextUtils.getRequestUserName())
            .lastUpdateUserId(RequestContextUtils.getRequestUserId())
            .lastUpdateUserName(RequestContextUtils.getRequestUserName())
            .description(body.getDescription())
            .name(body.getName())
            .longTermMemoryStrategies(body.getLongTermMemoryStrategies())
            .conversationRound(body.getConversationRound())
            .timeSpan(body.getTimeSpan())
            .memoryBackendType(StringUtils.isNotEmpty(body.getMemoryBackendType())
                ? body.getMemoryBackendType() : "BUILTIN")
            .memoryServiceInstanceId(body.getMemoryServiceInstanceId())
            .scopeModelConfig(body.getScopeModelConfig())
            .build();
    }

    /**
     * EXTERNAL 后端校验：验证实例ID非空且实例存在
     */
    private void validateExternalBackend(MemoryRepoEntity entity) {
        if (!"EXTERNAL".equalsIgnoreCase(entity.getMemoryBackendType())) {
            return;
        }
        if (StringUtils.isEmpty(entity.getMemoryServiceInstanceId())) {
            throw new InvalidParameterException("EXTERNAL 后端必须指定 memory_service_instance_id");
        }
        try {
            memoryServiceInstanceService.healthCheck(
                entity.getProjectId(), entity.getMemoryServiceInstanceId(), entity.getWorkspaceId());
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                .warn("External instance {} health check failed during repo creation: {}",
                    entity.getMemoryServiceInstanceId(), e.getMessage());
        }
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "MemoryRepo",
        description = "删除记忆库",
        resourceId = "memoryRepoId",
        resourceName = ""
    )
    public DeleteMemoryRepoResponseBody deleteMemoryRepo(String projectId, String memoryRepoId, String workspaceId) {

        // 解绑关联的智能体：清除绑定了该记忆库的 Agent 的 memoryConfig
        // SQL 使用 LIKE 做粗筛，Java 层再做精确 JSON 匹配，避免误命中
        try {
            List<Agent> candidateAgents = agentMapper.selectByMemoryRepoId(memoryRepoId);
            if (candidateAgents != null && !candidateAgents.isEmpty()) {
                List<Agent> boundAgents = candidateAgents.stream()
                    .filter(a -> a.getMemoryConfig() != null
                        && memoryRepoId.equals(a.getMemoryConfig().getMemoryRepoId()))
                    .collect(Collectors.toList());
                for (Agent agent : boundAgents) {
                    agentMapper.clearMemoryConfig(agent.getAgentId());
                }
                org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                    .info("Unbound memory repo {} from {} agents (candidates: {})",
                        memoryRepoId, boundAgents.size(), candidateAgents.size());
            }
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                .warn("Failed to unbind agents from memory repo {}: {}", memoryRepoId, e.getMessage());
        }

        // 解绑关联的 Workflow：清除 DSL 中的 memory_config 引用
        try {
            List<WorkflowEntity> allWorkflows = workflowMapper.getAll();
            if (allWorkflows != null) {
                for (WorkflowEntity wf : allWorkflows) {
                    if (StringUtils.isEmpty(wf.getDslPath())) continue;
                    try {
                        String dslJson = mgObsService.downloadObsFile(wf.getDslPath());
                        JSONObject dslObj = JSON.parseObject(dslJson);
                        JSONObject configs = dslObj.getJSONObject("configs");
                        if (configs != null && configs.containsKey("memory_config")) {
                            JSONObject memCfg = configs.getJSONObject("memory_config");
                            if (memCfg != null && memoryRepoId.equals(memCfg.getString("memory_repo_id"))) {
                                configs.remove("memory_config");
                                String updatedJson = JSON.toJSONString(dslObj, JSONWriter.Feature.WriteMapNullValue);
                                mgObsService.uploadObsFile(wf.getDslPath(), updatedJson, -1);
                                org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                                    .info("Removed memory_config from workflow DSL: {}", wf.getId());
                            }
                        }
                    } catch (Exception e) {
                        org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                            .warn("Failed to clean memory config from workflow {}: {}", wf.getId(), e.getMessage());
                    }
                }
            }
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                .warn("Failed to scan workflows for memory repo cleanup {}: {}", memoryRepoId, e.getMessage());
        }

        // 先查询记忆库以获取后端类型（删除后无法再查）
        MemoryRepoEntity repoEntityBeforeDelete = null;
        try {
            repoEntityBeforeDelete = memoryRepoMapper.selectById(memoryRepoId);
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                .warn("Failed to query memory repo {} before delete: {}", memoryRepoId, e.getMessage());
        }

        // 删除记录
        int result = memoryRepoMapper.deleteById(memoryRepoId);
        if (result == 1) {
            // 按后端类型分支清理数据
            String backendType = (repoEntityBeforeDelete != null
                && StringUtils.isNotEmpty(repoEntityBeforeDelete.getMemoryBackendType()))
                ? repoEntityBeforeDelete.getMemoryBackendType() : "BUILTIN";

            if ("EXTERNAL".equalsIgnoreCase(backendType) && repoEntityBeforeDelete != null
                && StringUtils.isNotEmpty(repoEntityBeforeDelete.getMemoryServiceInstanceId())) {
                // EXTERNAL: 调 agent-memory delete API
                try {
                    memoryServiceInstanceService.deleteMemByScope(
                        repoEntityBeforeDelete.getMemoryServiceInstanceId(), memoryRepoId);
                } catch (Exception e) {
                    org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                        .error("[ORPHAN_MEMORY_DATA] Failed to delete external memory data for repo {}: {}",
                            memoryRepoId, e.getMessage(), e);
                }
            } else {
                // BUILTIN: Delete actual memory data in agent-runtime via LTM (OpenSearch/Redis)
                try {
                    agentRuntimeClient.deleteMemoryRepoData(memoryRepoId);
                } catch (Exception e) {
                    org.slf4j.LoggerFactory.getLogger(MemoryRepoManagementService.class)
                        .error("[ORPHAN_MEMORY_DATA] Failed to delete runtime data for memory repo {}: type={}, msg={}",
                            memoryRepoId, e.getClass().getSimpleName(), e.getMessage(), e);
                }
            }
        }
        DeleteMemoryRepoResponseBody res = new DeleteMemoryRepoResponseBody();

        res.setMemoryRepoId(memoryRepoId);

        return res;
    }

    @Override
    @Transactional
    public ListMemoryReposResponseBody listMemoryRepositories(String projectId, ListMemoryRepositoriesQo query) {
        PageHelper.offsetPage(query.getOffset(), query.getLimit());
        String realQueryName = SqlLikeEscapeHelper.escapeLikeCharacters(query.getName());
        // 设置查询条件
        List<MemoryRepoEntity> memoryRepos = memoryRepoMapper.selectByCondition(
            projectId,
            query.getWorkspaceId(),
            RequestContextUtils.getRequestUserDomainId(),
            query.getIds(),
            realQueryName
        );
        PageInfo<MemoryRepoEntity> memoryRepoPageInfo = new PageInfo<>(memoryRepos);

        // 转换为返回结果
        List<MemoryRepoListItem> items = memoryRepos.stream()
            .map(entity -> {
                MemoryRepoListItem memoryRepoListItem = new MemoryRepoListItem();
                memoryRepoListItem.setName(entity.getName());
                memoryRepoListItem.setMemoryRepoId(entity.getId());
                memoryRepoListItem.setDescription(entity.getDescription());
                memoryRepoListItem.setLastUpdateUserId(entity.getLastUpdateUserId());
                memoryRepoListItem.setLastUpdateUserName(entity.getLastUpdateUserName());
                memoryRepoListItem.setWorkspaceId(entity.getWorkspaceId());
                memoryRepoListItem.setCreatedUserId(entity.getCreatedUserId());
                memoryRepoListItem.setCreatedUserName(entity.getCreatedUserName());
                memoryRepoListItem.setCreateTime(entity.getCreateTime());
                memoryRepoListItem.setUpdateTime(entity.getUpdateTime());
                memoryRepoListItem.setLongTermMemoryStrategies(entity.getLongTermMemoryStrategies());
                memoryRepoListItem.setIcon(StringUtils.isEmpty(entity.getIcon()) ? memoryDefaultIcon : entity.getIcon());
                memoryRepoListItem.setMemoryBackendType(StringUtils.isNotEmpty(entity.getMemoryBackendType())
                    ? entity.getMemoryBackendType() : "BUILTIN");
                memoryRepoListItem.setMemoryServiceInstanceId(entity.getMemoryServiceInstanceId());
                return memoryRepoListItem;
            })
            .collect(Collectors.toList());

        ListMemoryReposResponseBody response = new ListMemoryReposResponseBody();
        response.setItems(items);
        response.setTotal(memoryRepoPageInfo.getTotal());
        return response;
    }

    @Override
    @Transactional
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "MemoryRepo",
        description = "修改记忆库",
        resourceId = "memoryRepoId",
        resourceName = "body.name"
    )
    public ModifyMemoryRepoResponseBody modifyMemoryRepo(String projectId, String memoryRepoId, String workspaceId, ModifyMemoryRepoRequestBody body) {
        // 查询原记录
        if (body.getLongTermMemoryStrategies() != null && !body.getLongTermMemoryStrategies().isEmpty()) {
            checkLongMemoryStrategies(body.getLongTermMemoryStrategies());
        }
        MemoryRepoEntity entity = buildMemoryRepoEntity(projectId, memoryRepoId, workspaceId, body);

        if (StringUtils.isNotEmpty(body.getIcon())) {
            entity.setIcon(body.getIcon());
        }

        // EXTERNAL 后端校验
        validateExternalBackend(entity);

        // 更新数据库
        memoryRepoMapper.updateById(entity);

        // 构建返回结果
        ModifyMemoryRepoResponseBody response = new ModifyMemoryRepoResponseBody();
        response.setMemoryRepoId(entity.getId());
        return response;
    }

    private static MemoryRepoEntity buildMemoryRepoEntity(String projectId, String memoryRepoId, String workspaceId, ModifyMemoryRepoRequestBody body) {
        return MemoryRepoEntity.builder()
            .id(memoryRepoId)
            .projectId(projectId)
            .workspaceId(workspaceId)
            .domainId(RequestContextUtils.getRequestUserDomainId())
            .description(body.getDescription())
            .name(body.getName())
            .longTermMemoryStrategies(body.getLongTermMemoryStrategies())
            .conversationRound(body.getConversationRound())
            .timeSpan(body.getTimeSpan())
            .memoryBackendType(body.getMemoryBackendType())
            .memoryServiceInstanceId(body.getMemoryServiceInstanceId())
            .scopeModelConfig(body.getScopeModelConfig())
            .lastUpdateUserId(RequestContextUtils.getRequestUserId())
            .lastUpdateUserName(RequestContextUtils.getRequestUserName())
            .build();
    }

    @Override
    @Transactional
    public ShowMemoryRepoResponseBody showMemoryRepo(String projectId, String memoryRepoId, String workspaceId) {
        MemoryRepoEntity entity = memoryRepoMapper.selectById(memoryRepoId);

        if (entity == null) {
            throw new AgentStudioException(StudioError.MEMORY_REPO_NOT_EXIST);
        }
        return convertToShowResponse(entity);
    }

    /**
     * 转换为展示响应对象
     */
    private ShowMemoryRepoResponseBody convertToShowResponse(MemoryRepoEntity entity) {
        ShowMemoryRepoResponseBody response = new ShowMemoryRepoResponseBody();
        response.setName(entity.getName());
        response.setMemoryRepoId(entity.getId());
        response.setDescription(entity.getDescription());
        response.setCreatedUserId(entity.getCreatedUserId());
        response.setCreatedUserName(entity.getCreatedUserName());
        response.setCreateTime(entity.getCreateTime());
        response.setLastUpdateUserId(entity.getLastUpdateUserId());
        response.setLastUpdateUserName(entity.getLastUpdateUserName());
        response.setUpdateTime(entity.getUpdateTime());
        response.setLongTermMemoryStrategies(entity.getLongTermMemoryStrategies());
        response.setConversationRound(entity.getConversationRound());
        response.setTimeSpan(entity.getTimeSpan());
        response.setIcon(StringUtils.isEmpty(entity.getIcon()) ? memoryDefaultIcon : entity.getIcon());
        response.setMemoryBackendType(StringUtils.isNotEmpty(entity.getMemoryBackendType())
            ? entity.getMemoryBackendType() : "BUILTIN");
        response.setMemoryServiceInstanceId(entity.getMemoryServiceInstanceId());
        response.setScopeModelConfig(entity.getScopeModelConfig());
        return response;
    }
}
