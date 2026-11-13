
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.entity;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.enums.ToolType;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.Strings;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 公共元数据
 *
 */
@Slf4j
@Data
public class CommonMeta {
    private String id;

    private String name;

    private String domainId;

    private String projectId;

    private String workspaceId;

    public static Map<String, CommonMeta> fromAgents(List<Agent> entities) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(entities)) {
            for (Agent entity : entities) {
                if (entity == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getAgentId());
                commonMeta.setName(entity.getName());
                commonMeta.setDomainId(entity.getDomainId());
                commonMeta.setProjectId(entity.getProjectId());
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getAgentId(), commonMeta);
            }
        }
        return map;
    }

    public static Map<String, CommonMeta> fromWorkflows(List<WorkflowEntity> entities) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(entities)) {
            for (WorkflowEntity entity : entities) {
                if (entity == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getId());
                commonMeta.setName(entity.getName());
                commonMeta.setDomainId(entity.getDomainId());
                commonMeta.setProjectId(entity.getProjectId());
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getId(), commonMeta);
            }
        }
        return map;
    }

    public static Map<String, CommonMeta> fromTools(List<ToolEntity> entities, String workspaceId) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(entities)) {
            for (ToolEntity entity : entities) {
                if (entity == null) {
                    continue;
                }
                if (entity.getType().equals(ToolType.CUSTOM.type) && !Strings.CS.equals(entity.getWorkspaceId(), workspaceId)) {
                    // 资产广场已上架插件（platform_published=1 且 published=1）支持跨工作空间可见（FRS-091，口径与 listPlugins 一致）
                    boolean plazaPublished = entity.getPlatformPublished() != null
                        && entity.getPlatformPublished() == 1
                        && entity.getPublished() != null
                        && entity.getPublished() == 1;
                    if (!plazaPublished) {
                        throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION,
                            String.format("%s.", entity.getToolId()));
                    }
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getToolId());
                commonMeta.setName(entity.getToolDisplayName());
                commonMeta.setDomainId(entity.getDomainId());
                commonMeta.setProjectId(entity.getProjectId());
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getToolId(), commonMeta);
            }
        }
        return map;
    }
    public static Map<String, CommonMeta> fromMcps(List<McpServiceEntity> entities) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(entities)) {
            for (McpServiceEntity entity : entities) {
                if (entity == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getId());
                commonMeta.setName(entity.getName());
                commonMeta.setDomainId(entity.getDomainId());
                commonMeta.setProjectId(entity.getProjectId());
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getId(), commonMeta);
            }
        }
        return map;
    }

    public static Map<String, CommonMeta> fromRepos(List<KnowledgeBaseListItem> entities, String projectId) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(entities)) {
            for (KnowledgeBaseListItem entity : entities) {
                if (entity == null || entity.getKnowledgeBaseId() == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getKnowledgeBaseId());
                commonMeta.setName(entity.getName());
                commonMeta.setProjectId(projectId);
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getKnowledgeBaseId(), commonMeta);
            }
        }
        return map;
    }

    public static Map<String, CommonMeta> fromModels(List<? extends ModelServiceBase> entities) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(entities)) {
            for (ModelServiceBase entity : entities) {
                if (entity == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getId());
                commonMeta.setName(entity.getModelName());
                commonMeta.setProjectId(entity.getProjectId());
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getId(), commonMeta);
            }
        }
        return map;
    }

    public static Map<String, CommonMeta> fromMemoryRepos(List<MemoryRepoEntity> memoryRepoEntities) {
        Map<String, CommonMeta> map = new HashMap<>();
        if (!CollectionUtils.isEmpty(memoryRepoEntities)) {
            for (MemoryRepoEntity entity : memoryRepoEntities) {
                if (entity == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getId());
                commonMeta.setName(entity.getName());
                commonMeta.setProjectId(entity.getProjectId());
                commonMeta.setWorkspaceId(entity.getWorkspaceId());
                map.put(entity.getId(), commonMeta);
            }
        }
        return map;
    }

    /**
     * 从 Skill 获取元数据
     */
    public static Map<String, CommonMeta> fromSkills(List<SkillDetails> skillEntities) {
        Map<String, CommonMeta> map = new HashMap<String, CommonMeta>();
        if (!CollectionUtils.isEmpty(skillEntities)) {
            for (SkillDetails entity : skillEntities) {
                if (entity == null) {
                    continue;
                }
                CommonMeta commonMeta = new CommonMeta();
                commonMeta.setId(entity.getSkillId());
                commonMeta.setName(entity.getName());
                map.put(entity.getSkillId(), commonMeta);
            }
        }
        return map;
    }
}
