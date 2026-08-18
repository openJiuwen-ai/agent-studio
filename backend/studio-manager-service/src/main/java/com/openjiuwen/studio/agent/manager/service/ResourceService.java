/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.common.enums.StudioError.RESOURCE_NOT_EXISTS;

import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.entity.CommonMeta;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 资源服务
 *
 */
@Service
@Slf4j
public class ResourceService {

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private McpServiceMapper mcpServiceMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private ToolMapper toolMapper;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    @Autowired
    private SkillMapper skillMapper;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private ShareScopeMapper shareScopeMapper;

    @Autowired
    private KnowledgeBaseServiceImpl knowledgeBaseService;

    /**
     * 校验资源是否存在
     *
     * @param ids id列表
     * @param type 资源类型
     * @param projectId 项目id
     * @param workspaceId 空间id
     */
    public void validResourceExist(List<String> ids, String type, String projectId, String workspaceId) {
        Map<String, CommonMeta> map = getResourceMeta(ids, type, projectId, workspaceId);
        for (String id : ids) {
            if (map == null || !map.containsKey(id)) {
                log.error("Resource:{}, type:{}, projectId:{}, workspaceId:{} not exists.", id, type, projectId,
                    workspaceId);
                throw new AgentStudioException(RESOURCE_NOT_EXISTS, id);
            }
        }
    }

    /**
     * 获取资源元数据
     *
     * @param ids 资源ids
     * @param type 资源类型
     * @param projectId 项目id
     * @param workspaceId 空间id
     * @return 返回资源元数据
     */
    public Map<String, CommonMeta> getResourceMeta(List<String> ids, String type, String projectId,
        String workspaceId) {
        ResourceTypeEnum resourceTypeEnum = ResourceTypeEnum.fromValue(type);
        if (resourceTypeEnum == null) {
            log.error("resourceType:{} not valid.", type);
            throw new IllegalArgumentException();
        }
        switch (resourceTypeEnum) {
            case CONTROLLER, AGENT -> {
                Map<String, CommonMeta> result = CommonMeta
                    .fromAgents(agentMapper.selectByIdsAndProjectIdAndWorkspaceId(projectId, workspaceId, ids));
                // t_share_resource.resource_type 对 controller/agent(单智能体) 均为 'controller'
                return fillSharedResource(result, ids, projectId, workspaceId,
                    ResourceTypeEnum.CONTROLLER.toString());
            }
            case WORKFLOW -> {
                Map<String, CommonMeta> result = CommonMeta.fromWorkflows(
                    workflowMapper.getWorkflowEntityByIds(projectId, workspaceId, ids));
                return fillSharedResource(result, ids, projectId, workspaceId, resourceTypeEnum.toString());
            }
            case TOOL -> {
                return CommonMeta.fromTools(toolMapper.selectByToolIdsAndWorkspaceId(ids, projectId, workspaceId), workspaceId);
            }
            case MCP -> {
                return CommonMeta.fromMcps(mcpServiceMapper.selectByIdsAndWorkspace(ids, projectId, workspaceId));
            }
            case REPO -> {
                ListKnowledgeBasesQo listKnowledgeBasesQo = new ListKnowledgeBasesQo();
                listKnowledgeBasesQo.setWorkspaceId(workspaceId);
                listKnowledgeBasesQo.setKnowledgeBaseIds(ids);
                ListKnowledgeBasesResponseBody resp = knowledgeBaseService.listKnowledgeBases(
                    RequestContextUtils.getRequestProjectId(), listKnowledgeBasesQo);
                return CommonMeta.fromRepos(resp != null ? resp.getItems() : Collections.emptyList(), projectId);
            }
            case MODEL -> {
                return CommonMeta.fromModels(modelServiceMapper.queryByIds(ids, projectId, workspaceId));
            }
            case MEMORY -> {
                return CommonMeta.fromMemoryRepos((memoryRepoMapper.selectByCondition(projectId, workspaceId, null, ids, null)));
            }
            case SKILL -> {
                return CommonMeta.fromSkills(skillMapper.searchBySkillIds(ids));
            }
        }
        return null;
    }

    /**
     * 本地查不到的资源id，按 resource_id 批量查共享给当前空间的共享资源（含团队共享 'all'）补全元数据。
     * 仅对本地 map 中不存在的 id 查共享，本地已存在的不动。共享查询带授权校验，未授权不补全。
     * 固定 2 次 DB 查询（批量查 t_share_resource + 批量查 t_share_scope），无 N+1。
     * 用于 validResourceExist 校验时识别共享资源，避免共享子资源被误判为不存在。
     */
    private Map<String, CommonMeta> fillSharedResource(Map<String, CommonMeta> localResult, List<String> ids,
        String projectId, String workspaceId, String shareResourceType) {
        // localResult 后续会被重新赋值，不能在lambda中直接引用，用final引用规避
        final Map<String, CommonMeta> localRef = localResult;
        List<String> missingIds = ids.stream()
            .filter(id -> localRef == null || !localRef.containsKey(id))
            .collect(Collectors.toList());
        if (CollectionUtils.isEmpty(missingIds)) {
            return localResult;
        }
        // 批量查 t_share_resource（1次查询）
        List<ShareResourceEntity> shareResources = shareResourceMapper.selectShareResourceByResourceIds(missingIds);
        if (CollectionUtils.isEmpty(shareResources)) {
            return localResult;
        }
        // 批量查 t_share_scope 校验授权（含 'all'，1次查询）
        List<String> shareResourceIds = shareResources.stream()
            .map(ShareResourceEntity::getResourceId).collect(Collectors.toList());
        List<ShareScopeEntity> shareScopes = shareScopeMapper.selectShareScopesByResourceIdsAndWorkspaceId(
            shareResourceIds, workspaceId);
        // 有授权记录的 resource_id 集合（在 t_share_scope 命中 workspace_id=当前 or 'all'）
        java.util.Set<String> authorizedResourceIds = shareScopes.stream()
            .map(ShareScopeEntity::getResourceId).collect(Collectors.toSet());
        if (localResult == null) {
            localResult = new java.util.HashMap<>();
        }
        for (ShareResourceEntity shareResource : shareResources) {
            // 仅类型匹配且已授权给当前空间的共享资源才补全
            if (!shareResourceType.equalsIgnoreCase(shareResource.getResourceType())
                || !authorizedResourceIds.contains(shareResource.getResourceId())) {
                continue;
            }
            CommonMeta commonMeta = new CommonMeta();
            commonMeta.setId(shareResource.getResourceId());
            commonMeta.setName(shareResource.getResourceName());
            commonMeta.setProjectId(shareResource.getProjectId());
            commonMeta.setWorkspaceId(shareResource.getWorkspaceId());
            localResult.put(shareResource.getResourceId(), commonMeta);
        }
        return localResult;
    }
}
