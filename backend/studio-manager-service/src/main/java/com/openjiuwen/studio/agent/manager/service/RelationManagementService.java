/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListDependencyQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourceRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourcesRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.McpServerReference;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolEntity;
import com.openjiuwen.studio.agent.manager.dto.Relation;
import com.openjiuwen.studio.agent.manager.dto.RelationList;
import com.openjiuwen.studio.agent.manager.dto.ResourceMapping;
import com.openjiuwen.studio.agent.manager.dto.ResourceMappingList;
import com.openjiuwen.studio.agent.manager.dto.ResourceDependency;
import com.openjiuwen.studio.agent.manager.dto.ResourceDependencyResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.SkillReference;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.plugin.ResourceParam;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInfo;
import com.openjiuwen.studio.agent.manager.dto.plugin.ToolInputSchema;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.AgentType;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.HistoryWorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.models.assistant.KnowledgeRepoListRsp;
import com.openjiuwen.studio.agent.manager.service.mcp.auth.IMcpBase;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.utils.CommonUtil;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.McpJsonUtils;
import com.openjiuwen.studio.agent.manager.utils.WorkflowUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 依赖管理
 *
 */
@Slf4j
@Service
public class RelationManagementService implements IRelationManagementService {
    /**
     * 最大递归深度
     */
    private static final int NESTED_DEEP = 10;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private HistoryWorkflowMapper historyWorkflowMapper;

    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private ToolMapper toolMapper;

    @Autowired
    private WorkspaceMapper workspaceMapper;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    @Autowired
    private IPlugin pluginService;

    @Value("${tool.bound.limit:20}")
    private int toolBoundLimit;

    @Value("${knowledge.bound.limit:3}")
    private int knowledgeRepoBoundLimit;

    @Value("${workflow.bound.limit:5}")
    private int workflowBoundLimit;

    @Value("${controller.workflow-limit}")
    private int controllerWorkflowLimit;

    @Value("${controller.sub-agent-limit}")
    private int controllerSubAgentLimit;

    @Value("${agent.mcp-bound-limit:5}")
    private int mcpBoundLimit;

    @Value("${mcp.default-icon}")
    private String defaultMcpIcon;

    @Resource
    private McpServiceDao serviceDao;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private ShareScopeMapper shareScopeMapper;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private IPluginBase pluginBase;

    @Autowired
    private ResourceService resourceService;

    @Autowired
    private ShareInnerService shareInnerService;

    @Autowired
    private IMcpBase mcpBase;

    @Autowired
    private SkillMapper skillMapper;

    @Autowired
    private KnowledgeBaseServiceImpl knowledgeBaseService;

    private @NotNull List<Relation> buildRelationsFromMapping(List<MappingEntity> mappingEntities,
        Map<String, String> workspaceInfoMap) {
        return mappingEntities.stream().map(entity -> {
            Relation relation = new Relation();

            relation.setRelationId(entity.getMappingId());

            relation.setAppId(entity.getAppId());
            relation.setAppVersion(entity.getAppVersion());
            relation.setAppType(entity.getAppType());
            // 获取应用名称，根据语言环境和应用类型决定是否从WorkflowEntity获取中文名称
            String appName = entity.getAppName();
            if (LanguageUtils.isChinese() && Constants.AppType.WORKFLOW.equals(entity.getAppType())) {
                WorkflowEntity workflow = workflowMapper.getWorkflowById(entity.getAppId());
                if (!ObjectUtils.isEmpty(workflow)) {
                    appName = workflow.getName();
                }
            }
            relation.setAppName(appName);
            relation.setResourceId(entity.getResourceId());
            relation.setResourceVersion(entity.getResourceVersion());
            relation.setResourceType(entity.getResourceType());
            relation.setResourceName(entity.getResourceName());
            relation.setIsController(false);
            if (Strings.CS.equals(entity.getAppType(), CommonConstant.AGENT)) {
                Agent agent = agentMapper.selectById(entity.getAppId());
                relation.setIsController(
                        agent != null && Strings.CS.equals(agent.getType(), CommonConstant.CONTROLLER));
            }
            String pluginId = StringUtils.substringBefore(entity.getResourceId(), "#");
            PluginEntity plugin = pluginMapper.selectByPrimaryKeyAndWorkspace(pluginId, null, null);
            if (StringUtils.isEmpty(relation.getResourceVersion()) && plugin != null) {
                relation.setResourceVersion(plugin.getLastVersionId());
            }
            relation.setValid(entity.isValid());
            relation.setReferenceType(entity.getReferenceType());
            relation.setAppWorkspaceId(entity.getAppWorkspaceId());
            relation.setAppWorkspaceName(workspaceInfoMap.get(entity.getAppWorkspaceId()));

            // skill版本系统号
            if (ResourceTypeEnum.SKILL.toString().equals(entity.getReferenceType())) {
                relation.setResourceVersionName(entity.getExtendInfo());
            }

            return relation;
        }).collect(Collectors.toList());
    }

    private static @NotNull Relation buildRelationFromMapping(MappingEntity entity) {
        Relation relation = new Relation();
        relation.setRelationId(entity.getMappingId());
        relation.setAppId(entity.getAppId());
        relation.setAppVersion(entity.getAppVersion());
        relation.setAppType(entity.getAppType());
        relation.setAppName(entity.getAppName());
        relation.setResourceId(entity.getResourceId());
        relation.setResourceVersion(entity.getResourceVersion());
        relation.setResourceType(entity.getResourceType());
        relation.setResourceName(entity.getResourceName());
        relation.setReferenceType(entity.getReferenceType());
        relation.setValid(entity.isValid());
        return relation;
    }

    /**
     * 根据传入的知识库绑定信息关联agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param knowledgeReferences knowledgeReferences
     * @return List
     */
    @Transactional
    public List<MappingEntity> createAgentKnowledge(String projectId, String workspaceId, String agentId,
        String versionId, List<MappingEntity> knowledgeReferences) {
        log.debug(
            "Entering createAgentKnowledge with parameters: projectId={}, workspaceId={}, agentId={}, versionId={}, knowledgeReferences.size={}",
            projectId, workspaceId, agentId, versionId, knowledgeReferences != null ? knowledgeReferences.size() : 0);

        if (CollectionUtils.isEmpty(knowledgeReferences)) {
            return new ArrayList<>();
        }
        if (knowledgeReferences.size() > knowledgeRepoBoundLimit) {
            throw new AgentStudioException(StudioError.KNOWLEDGE_REPO_NUMBER_EXCEED_LIMIT);
        }

        // 校验agent是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        // 校验知识库是否存在
        List<String> knowledgeRepoIds = knowledgeReferences.stream()
            .map(MappingEntity::getResourceId)
            .distinct()
            .toList();
        final List<KnowledgeRepoEntity> knowledgeRepos = getExistKnowledgeRepos(projectId, workspaceId,
            knowledgeRepoIds);
        final List<String> existRepoIds = knowledgeRepos.stream()
            .map(KnowledgeRepoEntity::getKnowledgeRepoId)
            .toList(); // 取出目前存在所有知识库id
        List<String> notExistRepoIds = knowledgeRepoIds.stream().filter(id -> !existRepoIds.contains(id)).toList();
        if (!CollectionUtils.isEmpty(notExistRepoIds)) {
            log.error("These knowledge repos does not exist: {}", notExistRepoIds);
        }

        // 校验知识库绑定数量
        final List<MappingEntity> agentKnowledgeList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.REPO_TYPE);
        if (!CollectionUtils.isEmpty(agentKnowledgeList) && versionId == null) {
            List<String> boundRepoIds = agentKnowledgeList.stream().map(MappingEntity::getResourceId).toList();
            knowledgeRepos.removeIf(knowledgeRepo -> boundRepoIds.contains(knowledgeRepo.getKnowledgeRepoId()));

            // 传入的知识库都是已绑定的，直接返回
            if (CollectionUtils.isEmpty(knowledgeRepos)) {
                return knowledgeReferences;
            }
            if (knowledgeRepos.size() + boundRepoIds.size() > knowledgeRepoBoundLimit) {
                throw new AgentStudioException(StudioError.KNOWLEDGE_REPO_NUMBER_EXCEED_LIMIT);
            }
        }

        // 关联agent和knowledgeRepos
        List<MappingEntity> agentKnowledges = new ArrayList<>();
        for (KnowledgeRepoEntity knowledgeRepo : knowledgeRepos) {
            MappingEntity agentKnowledge = new MappingEntity();
            agentKnowledge.setMappingId(UUID.randomUUID().toString());
            agentKnowledge.setAppId(agentId);
            agentKnowledge.setAppType(CommonConstant.AGENT_TYPE);
            agentKnowledge.setAppName(agent.getName());
            agentKnowledge.setAppVersion(versionId);
            agentKnowledge.setResourceId(knowledgeRepo.getKnowledgeRepoId());
            agentKnowledge.setResourceType(CommonConstant.REPO_TYPE);
            agentKnowledge.setResourceName(knowledgeRepo.getDisplayName());
            agentKnowledges.add(agentKnowledge);
        }

        if (!CollectionUtils.isEmpty(agentKnowledges)) {
            mappingMapper.insertBatch(agentKnowledges);
        }
        return knowledgeReferences;
    }

    /**
     * 根据传入的插件绑定信息关联agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param toolReferences toolReferences
     * @return List
     */
    @Transactional
    public List<MappingEntity> createAgentTool(String projectId, String workspaceId, String agentId, String versionId,
        List<MappingEntity> toolReferences) {
        if (toolReferences == null || toolReferences.isEmpty()) {
            return new ArrayList<>();
        }
        if (toolReferences.size() > toolBoundLimit) {
            throw new AgentStudioException(StudioError.TOOL_NUMBER_EXCEED_LIMIT);
        }

        // 校验agent是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        // 校验tools是否都存在
        List<MappingEntity> uniqueToolReferences = toolReferences.stream()
            .collect(Collectors.collectingAndThen(
                Collectors.toCollection(() -> new TreeSet<>(Comparator.comparing(MappingEntity::getResourceId))),
                ArrayList::new));

        List<String> pluginIds = uniqueToolReferences.stream()
            .map(MappingEntity::getResourceId)
            .map(id -> id.split("#"))
            .map(id -> id[0])
            .toList();

        final List<PluginEntity> pluginLists = pluginService.getPlugin(projectId, workspaceId, pluginIds);
        Set<String> dbPluginAndToolIdSet = new HashSet<>();
        for (PluginEntity pluginEntity : pluginLists) {
            if (StringUtils.isNotBlank(pluginEntity.getRequestInfo())) {
                dbPluginAndToolIdSet.add(pluginEntity.getPluginId());
            } else {
                // 未知格式
                throw new AgentStudioException(StudioError.TOOL_INPUT_INVALID);
            }
        }

        List<String> extrasPluginAndToolId = uniqueToolReferences.stream()
            .map(MappingEntity::getResourceId)
            .map(id -> id.split("#"))
            .map(id -> id[0])
            .filter(id -> !dbPluginAndToolIdSet.contains(id))
            .toList();
        if (!CollectionUtils.isEmpty(extrasPluginAndToolId)) {
            log.error("These tool does not exist: {}", extrasPluginAndToolId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST,
                String.format("tool ids %s not exist", extrasPluginAndToolId));
        }

        // 去除已绑定的ToolReference
        List<MappingEntity> mappingAgentTools = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.TOOL_TYPE);

        if (!CollectionUtils.isEmpty(mappingAgentTools) && versionId == null) {
            List<String> boundToolId = mappingAgentTools.stream().map(MappingEntity::getResourceId).toList();
            log.info("These tools have been bound: {}", boundToolId);
            uniqueToolReferences.removeIf(toolReference -> boundToolId.contains(toolReference.getResourceId()));
            if (uniqueToolReferences.size() + boundToolId.size() > toolBoundLimit) {
                throw new AgentStudioException(StudioError.TOOL_NUMBER_EXCEED_LIMIT);
            }
        }

        // 传入的ToolReference都是已绑定的，直接返回
        if (CollectionUtils.isEmpty(uniqueToolReferences)) {
            return toolReferences;
        }

        // 关联agent和tools
        List<MappingEntity> agentToolSet = new ArrayList<>();
        for (PluginEntity pluginEntity : pluginLists) {
            if (StringUtils.isNotBlank(pluginEntity.getRequestInfo())) {
                if (pluginService.isNewTool(pluginEntity)) {
                    JSONObject jsonObject = JSON.parseObject(pluginEntity.getRequestInfo());
                    List<ToolInfo> toolsInfo = jsonObject.getList("tool_info", ToolInfo.class);
                    for (ToolInfo tool : toolsInfo) {
                        String resourceId = pluginEntity.getPluginId() + "#" + tool.getToolId();
                        if (uniqueToolReferences.stream()
                            .noneMatch(toolReference -> toolReference.getResourceId().equals(resourceId))) {
                            continue;
                        }
                        MappingEntity agentTools = new MappingEntity();
                        agentTools.setMappingId(UUID.randomUUID().toString());
                        agentTools.setAppId(agentId);
                        agentTools.setAppType(CommonConstant.AGENT_TYPE);
                        agentTools.setAppName(agent.getName());
                        agentTools.setAppVersion(versionId);
                        agentTools.setResourceId(resourceId);
                        agentTools.setAppWorkspaceId(workspaceId);
                        // 获取插件版本号
                        for (MappingEntity toolReference : toolReferences) {
                            if (toolReference.getResourceId().equals(resourceId)) {
                                agentTools.setResourceVersion(toolReference.getResourceVersion());
                                break;
                            }
                        }
                        agentTools.setResourceType(CommonConstant.TOOL_TYPE);
                        agentTools.setResourceName(tool.getToolDisplayName());
                        agentTools.setResourceDesc(tool.getToolDesc());
                        agentTools.setReferenceType(toolReferences.stream()
                            .filter(toolReference -> toolReference.getResourceId().equals(resourceId))
                            .findFirst()
                            .map(MappingEntity::getReferenceType)
                            .orElse(ReferenceTypeEnum.DIRECT.getValue()));
                        String resourceVersion = agentTools.getResourceVersion();
                        agentTools.setExtendInfo(
                            parseToolInput2ResourceParameter(resourceId, resourceVersion, tool.getToolId(),
                                pluginService.isNewTool(pluginEntity)));
                        agentToolSet.add(agentTools);
                    }
                } else {
                    MappingEntity agentTools = new MappingEntity();
                    agentTools.setMappingId(UUID.randomUUID().toString());
                    agentTools.setAppId(agentId);
                    agentTools.setAppType(CommonConstant.AGENT_TYPE);
                    agentTools.setAppName(agent.getName());
                    agentTools.setAppVersion(versionId);
                    agentTools.setResourceId(pluginEntity.getPluginId() + "#0");
                    // 获取插件版本号
                    for (MappingEntity toolReference : toolReferences) {
                        if (toolReference.getResourceId().equals(pluginEntity.getPluginId() + "#0")) {
                            agentTools.setResourceVersion(toolReference.getResourceVersion());
                            break;
                        }
                    }
                    agentTools.setResourceType(CommonConstant.TOOL_TYPE);
                    agentTools.setResourceName(pluginEntity.getPluginDisplayName());
                    agentTools.setResourceDesc(pluginEntity.getPluginDesc());
                    agentTools.setReferenceType(toolReferences.stream()
                        .filter(
                            toolReference -> toolReference.getResourceId().equals(pluginEntity.getPluginId() + "#0"))
                        .findFirst()
                        .map(MappingEntity::getReferenceType)
                        .orElse(ReferenceTypeEnum.DIRECT.getValue()));
                    agentTools.setAppWorkspaceId(workspaceId);
                    String resourceVersion = agentTools.getResourceVersion();
                    agentTools.setExtendInfo(
                        parseToolInput2ResourceParameter(pluginEntity.getPluginId(), resourceVersion, null,
                            pluginService.isNewTool(pluginEntity)));
                    agentToolSet.add(agentTools);
                }
            } else {
                // 未知格式
                throw new AgentStudioException(StudioError.TOOL_INPUT_INVALID);
            }
        }
        log.debug("Mappings to insert: {}", agentToolSet);

        if (!CollectionUtils.isEmpty(agentToolSet)) {
            mappingMapper.insertBatch(agentToolSet);
        }
        return toolReferences;
    }

    /**
     * 解析工具的InputSchema
     *
     * @param resourceId 资源Id
     * @param versionId 版本Id
     * @param toolId 工具Id
     * @param newTool
     * @return resourceParameter
     */
    private String parseToolInput2ResourceParameter(String resourceId, String versionId, String toolId,
        boolean newTool) {
        // 未发布的工具查询tool表，已发布的查询obs
        ToolEntity toolEntity;
        String inputSchemaStr;
        if (StringUtils.isBlank(versionId)) {
            toolEntity = toolMapper.selectById(resourceId.split("#")[0]);
            inputSchemaStr = toolEntity != null ? toolEntity.getInputSchema() : null;
            if (!newTool) {
                return buildResourceInputSchema(inputSchemaStr);
            }
            // 若为新工具类型,根据toolId更新inputSchemaStr
            if (toolId != null && inputSchemaStr != null) {
                JSONArray jsonArray = JSON.parseArray(inputSchemaStr);
                for (int i = 0; i < jsonArray.size(); i++) {
                    ToolInputSchema toolInputSchema = jsonArray.getObject(i, ToolInputSchema.class);
                    if (toolId.equals(toolInputSchema.getToolId())) {
                        inputSchemaStr = toolInputSchema.getInputSchema();
                        break;
                    }
                }
            }
        } else {
            toolEntity = pluginBase.getToolEntityByVersion(resourceId, versionId);
            inputSchemaStr = toolEntity.getInputSchema();
        }

        return buildResourceInputSchema(inputSchemaStr);
    }

    private String buildResourceInputSchema(String inputSchemaStr) {
        // 如果inputSchemaStr为空，则抛异常
        if (inputSchemaStr == null || inputSchemaStr.isEmpty()) {
            throw new AgentStudioException(StudioError.TOOL_INPUT_SCHEMA_INVALID);
        }

        SchemaConfig inputSchema = JSON.parseObject(inputSchemaStr, SchemaConfig.class);
        Set<String> requiredSet = new HashSet<>(inputSchema.getRequired());

        List<ResourceParam> toolParams = new ArrayList<>();
        for (String paramName : inputSchema.getProperties().keySet()) {
            SchemaConfig property = inputSchema.getProperties().get(paramName);
            ResourceParam resourceParam = ResourceParam.builder()
                .name(paramName)
                .type(property.getType())
                .description(property.getDescription())
                .defaultValue(parseDefaultValue(property.getDefaultValue(), property.getType()))
                .value(ResourceParam.ValueDTO.builder()
                    // 参数类型默认 literal
                    .type("literal")
                    // 设置为默认值
                    .content(parseDefaultValue(property.getDefaultValue(), property.getType()))
                    .build())
                // 参数可见性默认 true
                .visibility(true)
                .required(requiredSet.contains(paramName))
                .build();
            // 处理Object类型多层嵌套
            if (property.getProperties() != null && "object".equals(property.getType())) {
                resourceParam.setSchema(parseNestedProperties(property.getProperties()));
            }
            // 处理Array类型
            if (property.getItems() != null && "array".equals(property.getType())) {
                Map<String, Object> schema = new HashMap<>();
                schema.put("type", property.getItems().getType());
                // <Array<Object>类型
                if ("object".equals(property.getItems().getType())) {
                    List<Map<String, Object>> schemaList = parseNestedProperties(property.getItems().getProperties());
                    schema.put("schema", schemaList);
                }
                resourceParam.setSchema(schema);
            }
            toolParams.add(resourceParam);
        }
        return JSON.toJSONString(toolParams);
    }

    /**
     * 解析defaultValue
     * @param defaultValue defaultValue
     * @param type type
     * @return object
     */
    private static Object parseDefaultValue(Object defaultValue, String type) {
        if ("boolean".equals(type)) {
            return Boolean.parseBoolean(String.valueOf(defaultValue));
        }
        return defaultValue == null ? "" : defaultValue;
    }

    /**
     * 解析工具插件InputSchema复杂嵌套逻辑
     * @param properties Map<String, SchemaConfig>
     * @return List<Map<String, Object>>
     */
    public List<Map<String, Object>> parseNestedProperties(Map<String, SchemaConfig> properties) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map.Entry<String, SchemaConfig> entry : properties.entrySet()) {
            String paramName = entry.getKey();
            SchemaConfig property = entry.getValue();
            Map<String, Object> parsedObject = new HashMap<>();
            parsedObject.put("description", property.getDescription());
            parsedObject.put("name", paramName);
            parsedObject.put("type", property.getType());
            // 处理Object类型
            if (property.getProperties() != null && "object".equals(property.getType())) {
                List<Map<String, Object>> schemaList = parseNestedProperties(property.getProperties());
                parsedObject.put("schema", schemaList);
            }
            // 处理Array类型
            if (property.getItems() != null && "array".equals(property.getType())) {
                Map<String, Object> schema = new HashMap<>();
                schema.put("type", property.getItems().getType());
                // Array<Object>类型
                if ("object".equals(property.getItems().getType())) {
                    List<Map<String, Object>> schemaList = parseNestedProperties(property.getItems().getProperties());
                    schema.put("schema", schemaList);
                }
                parsedObject.put("schema", schema);
            }
            // value字段
            parsedObject.put("value", ResourceParam.ValueDTO.builder()
                .type("literal")
                .content(parseDefaultValue(property.getDefaultValue(), property.getType()))
                .build());
            result.add(parsedObject);
        }
        return result;
    }

    /**
     * 根据传入的工作流绑定信息关联agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workflowReferences workflowReferences
     * @return List
     */
    @Transactional
    public void createAgentWorkflow(String projectId, String workspaceId, String agentId, String versionId,
        List<MappingEntity> workflowReferences) {
        // 静态代码检查G.OTH.02：日志中全角冒号替换为半角冒号，避免日志采集系统解析异常
        log.info("input param: projectId={}, workspaceId={}, agentId={}, versionId={}, workflowReferences.size={}",
            projectId, workspaceId, agentId, versionId, workflowReferences == null ? 0 : workflowReferences.size());

        if (CollectionUtils.isEmpty(workflowReferences)) {
            return;
        }

        // 查询Agent
        Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        log.info("find Agent, agentId={}, agentType={}", agentId, agent.getType());

        // 构建工作流版本映射
        Map<String, MappingEntity> versionMap = workflowReferences.stream()
            .collect(Collectors.toMap(
                MappingEntity::getResourceId,
                Function.identity(),
                (existing, replacement) -> existing
            ));

        // 校验工作流数量是否超出限制
        int limit = (AgentType.naValueOf(agent.getType()) == AgentType.CONTROLLER) ? controllerWorkflowLimit : workflowBoundLimit;
        if (workflowReferences.size() > limit) {
            throw new AgentStudioException(StudioError.WORKFLOW_NUMBER_EXCEED_LIMIT);
        }

        List<String> workflowIds = workflowReferences.stream()
            .map(MappingEntity::getResourceId)
            .distinct()
            .collect(Collectors.toList());
        List<WorkflowEntity> workflowEntityList = workflowMapper.selectByWorkflowIds(projectId, workspaceId, workflowIds);

        // 获取共享的工作流
        List<ShareResourceEntity> shareResourceEntities = shareResourceManagerService.queryShareResourceEntityByResourceIdList(workflowIds);
        List<String> shareWorkflowIdList = shareResourceEntities.stream()
            .map(ShareResourceEntity::getResourceId)
            .collect(Collectors.toList());

        Map<String, WorkflowEntity> shareWorkflowEntityMap = new HashMap<>();
        if (CollectionUtils.isNotEmpty(shareWorkflowIdList)) {
            List<WorkflowEntity> shareWorkflowList = workflowMapper.selectByWorkflowIds(projectId, null, workflowIds);
            List<WorkflowEntity> filteredShareWorkflowList = shareWorkflowList.stream()
                .filter(workflow -> !RequestContextUtils.getRequestWorkspaceId().equals(workflow.getWorkspaceId()))
                .toList();
            shareWorkflowEntityMap = filteredShareWorkflowList.stream()
                .collect(Collectors.toMap(WorkflowEntity::getId, Function.identity()));
            workflowEntityList.addAll(filteredShareWorkflowList);
        }

        // 校验工作流是否存在
        List<String> notExistWorkflowIds = workflowIds.stream()
            .filter(id -> workflowEntityList.stream().noneMatch(workflow -> workflow.getId().equals(id)))
            .collect(Collectors.toList());

        if (!notExistWorkflowIds.isEmpty()) {
            log.error("These workflows do not exist: {}", notExistWorkflowIds);
        }

        // 校验工作流绑定数量是否超出限制
        List<MappingEntity> agentWorkflowList = mappingMapper.selectByAppIdAndResourceType(agentId, CommonConstant.WORKFLOW_TYPE);
        if (!agentWorkflowList.isEmpty() && versionId == null) {
            List<String> boundWorkflowIds = agentWorkflowList.stream().map(MappingEntity::getResourceId).toList();

            workflowEntityList.removeIf(workflow -> boundWorkflowIds.contains(workflow.getId()));

            if (workflowEntityList.size() + boundWorkflowIds.size() > workflowBoundLimit) {
                throw new AgentStudioException(StudioError.WORKFLOW_NUMBER_EXCEED_LIMIT);
            }

            // 传入的工作流都是已绑定的，直接返回
            if (workflowEntityList.isEmpty()) {
                return;
            }
        }

        List<MappingEntity> agentWorkflows = new ArrayList<>();
        for (WorkflowEntity workflow : workflowEntityList) {
            MappingEntity originMapping = versionMap.get(workflow.getId());
            MappingEntity workflowMapping = createWorkflowMapping(workflow, originMapping, agent, versionId, shareWorkflowEntityMap);
            agentWorkflows.add(workflowMapping);
        }

        // 发布版本失效的子工作流，关联关系需要创建
        if (!notExistWorkflowIds.isEmpty()) {
            for (String notExistWorkflowId : notExistWorkflowIds) {
                MappingEntity originMapping = versionMap.get(notExistWorkflowId);
                MappingEntity workflowMapping = createWorkflowMapping(new WorkflowEntity(), originMapping, agent, versionId, shareWorkflowEntityMap);
                workflowMapping.setValid(false);
                agentWorkflows.add(workflowMapping);
            }
        }

        log.info("create {} MappingEntities and insert", agentWorkflows.size());

        if (!agentWorkflows.isEmpty()) {
            mappingMapper.insertBatch(agentWorkflows);
        }
    }

    private MappingEntity createWorkflowMapping(WorkflowEntity workflow, MappingEntity originMapping, Agent agent,
        String versionId, Map<String, WorkflowEntity> shareWorkflowEntityMap) {
        MappingEntity workflowMapping = new MappingEntity();
        workflowMapping.setMappingId(UUID.randomUUID().toString());
        workflowMapping.setAppId(agent.getAgentId());
        workflowMapping.setAppType(CommonConstant.AGENT_TYPE);
        workflowMapping.setAppName(agent.getName());
        workflowMapping.setAppVersion(versionId);
        workflowMapping.setAppWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
        workflowMapping.setResourceId(StringUtils.isNotEmpty(workflow.getId()) ? workflow.getId() : originMapping.getResourceId());
        workflowMapping.setResourceType(CommonConstant.WORKFLOW_TYPE);
        workflowMapping.setResourceVersion(StringUtils.isEmpty(originMapping.getResourceVersion())
            ? workflow.getLastVersionId()
            : originMapping.getResourceVersion());
        workflowMapping.setResourceName(StringUtils.isEmpty(originMapping.getResourceName())
            ? workflow.getName()
            : originMapping.getResourceName());
        workflowMapping.setResourceWorkspaceId(StringUtils.isNotEmpty(workflow.getWorkspaceId())
            ? workflow.getWorkspaceId()
            : originMapping.getResourceWorkspaceId());
        workflowMapping.setReferenceType(shareWorkflowEntityMap.containsKey(
            StringUtils.isNotEmpty(workflow.getId()) ? workflow.getId() : originMapping.getResourceId())
            ? ReferenceTypeEnum.SHARE.getValue()
            : ReferenceTypeEnum.DIRECT.getValue());
        workflowMapping.setExtendInfo(
            StringUtils.isNotEmpty(workflow.getDslPath()) ? parseWorkflowInput2ResourceParameter(workflow.getDslPath(),
                workflowMapping.getResourceVersion()) : null);
        return workflowMapping;
    }

    /**
     * 解析workflowDSL文件中开始节点node_start输入参数
     * @param workflowDslPath workflowDsl路径
     * @return resourceParameter
     */
    public String parseWorkflowInput2ResourceParameter(String workflowDslPath, String resourceVersion) {
        String workflowDslPathWithVersion = resourceVersion != null
            ? workflowDslPath.replace(".json", "_" + resourceVersion + ".json")
            : workflowDslPath;
        String workflowJson = mgObsService.downloadObsFile(workflowDslPathWithVersion);

        WorkflowVO workflowDetail = JSON.parseObject(workflowJson, WorkflowVO.class);
        List<WorkflowNodeVO> workflowNodes = workflowDetail.getNodes();
        WorkflowNodeVO startNode = WorkflowUtils.getWorkflowNodeID("node_start", workflowNodes);
        List<WorkflowFieldVO> inputs = startNode == null ? null : startNode.getOutputs();

        // 将开始节点参数复制到ResourceParam
        List<ResourceParam> workflowParams = new ArrayList<>();
        if (inputs != null) {
            for (WorkflowFieldVO input : inputs) {
                // 跳过sys参数
                if (input.getName().startsWith(CommonConstant.SYS)) {
                    continue;
                }
                // 如果存在schema字段，表明为Object，Array类型
                if (input.getSchema() != null) {
                    Object schema = parseSchema(input.getSchema(), input.getType());
                    input.setSchema(schema);
                }
                Object defaultValue = parseDefaultValue(input.getValue().getDefault()
                    , input.getType());
                ResourceParam workflowParam = ResourceParam.builder()
                    .defaultValue(defaultValue)
                    .name(input.getName())
                    .type(input.getType())
                    .description(input.getDescription())
                    .schema(input.getSchema())
                    .value(ResourceParam.ValueDTO.builder()
                        // 参数类型默认 literal
                        .type("literal")
                        .content(defaultValue)
                        .build())
                    // 参数可见性默认 true
                    .visibility(true)
                    .required(input.isRequired())
                    .build();
                workflowParams.add(workflowParam);
            }
        }
        return JSON.toJSONString(workflowParams);
    }

    /**
     * 解析开始节点输入参数的schema字段
     * @param schema 输入参数schema字段
     * @param inputType 输入参数的类型（Object\Array)
     * @return Object 如果是Object类型，返回List，如果是Array类型，返回Map
     */
    private static Object parseSchema(Object schema, String inputType) {
        ObjectMapper objectMapper = new ObjectMapper();
        // type为Object或Array时分别处理
        if ("object".equals(inputType)) {
            List<Map<String, Object>> result = new ArrayList<>();
            WorkflowFieldVO[] schemaConfigs = objectMapper.convertValue(schema, WorkflowFieldVO[].class);
            for (WorkflowFieldVO schemaConfig : schemaConfigs) {
                Map<String, Object> parsedObject = new HashMap<>();
                Object defaultValue = parseDefaultValue(schemaConfig.getValue().getDefault()
                    , schemaConfig.getType());
                parsedObject.put("name", schemaConfig.getName());
                parsedObject.put("description", schemaConfig.getDescription());
                parsedObject.put("type", schemaConfig.getType());
                parsedObject.put("value", ResourceParam.ValueDTO.builder()
                    .type("literal")
                    .content(defaultValue)
                    .build());
                // 涉及多层Object类型嵌套
                if (schemaConfig.getSchema() != null) {
                    Object schemaList = parseSchema(schemaConfig.getSchema(),
                        schemaConfig.getType());
                    parsedObject.put("schema", schemaList);
                }
                result.add(parsedObject);
            }
            return result;
        } else {
            WorkflowFieldVO schemaConfig = objectMapper.convertValue(schema, WorkflowFieldVO.class);
            Map<String, Object> parsedObject = new HashMap<>();
            parsedObject.put("type", schemaConfig.getType());
            // Array<Object>
            if ("object".equals(schemaConfig.getType())) {
                Object schemaList = parseSchema(schemaConfig.getSchema(), schemaConfig.getType());
                parsedObject.put("schema", schemaList);
            }
            return parsedObject;
        }
    }

    /**
     * 根据传入的agent绑定信息关联agent
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param agentId agentId
     * @param agentReferences agentReferences
     */
    @Transactional
    public void createAgentSubController(String projectId, String workspaceId, String agentId, String versionId,
        List<MappingEntity> agentReferences) {
        if (CollectionUtils.isEmpty(agentReferences)) {
            return;
        }
        // 校验agent是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_VERSION_NOT_EXIST, agentId, versionId);
        }

        if (agentReferences.size() > controllerSubAgentLimit) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_NUMBER_EXCEED_LIMIT);
        }

        Map<String, MappingEntity> versionMap = new HashMap<>();
        agentReferences.forEach(agentRef -> versionMap.put(agentRef.getResourceId(), agentRef));

        // 校验agent是否存在
        List<String> agentIds = agentReferences.stream().map(MappingEntity::getResourceId).distinct().toList();
        final List<Agent> agents = agentMapper.selectByAgentIds(projectId, AgentType.CONTROLLER.getValue(), agentIds);
        final List<String> existAgentIds = agents.stream().map(Agent::getAgentId).toList();
        List<String> notExistAgentIds = agentIds.stream().filter(id -> !existAgentIds.contains(id)).toList();
        if (!CollectionUtils.isEmpty(notExistAgentIds)) {
            log.error("These agent not exist: {}", notExistAgentIds);
        }

        // 校验agents绑定数量
        final List<MappingEntity> agentSubAgentList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.AGENT_TYPE);
        if (!CollectionUtils.isEmpty(agentSubAgentList) && versionId == null) {
            List<String> boundAgentIds = agentSubAgentList.stream().map(MappingEntity::getResourceId).toList();
            agents.removeIf(item -> boundAgentIds.contains(item.getAgentId()));

            // 传入的agent都是已绑定的，直接返回
            if (CollectionUtils.isEmpty(agents)) {
                return;
            }
            if (agents.size() + boundAgentIds.size() > controllerSubAgentLimit) {
                throw new AgentStudioException(StudioError.MULTI_AGENT_NUMBER_EXCEED_LIMIT);
            }
        }

        // 关联controller和子agent
        List<MappingEntity> agentSubAgent = new ArrayList<>();
        for (Agent item : agents) {
            MappingEntity originMapping = versionMap.get(item.getAgentId());
            MappingEntity agentMapping = new MappingEntity();
            agentMapping.setMappingId(UUID.randomUUID().toString());
            agentMapping.setAppId(agentId);
            agentMapping.setAppType(CommonConstant.AGENT_TYPE);
            agentMapping.setAppName(agent.getName());
            agentMapping.setAppVersion(versionId);
            agentMapping.setResourceId(item.getAgentId());
            agentMapping.setResourceType(CommonConstant.CONTROLLER);
            agentMapping.setResourceVersion(originMapping.getResourceVersion());
            agentMapping.setResourceName(StringUtils.isEmpty(originMapping.getResourceName())
                ? item.getName()
                : originMapping.getResourceName());
            agentSubAgent.add(agentMapping);
        }
        if (!CollectionUtils.isEmpty(agentSubAgent)) {
            mappingMapper.insertBatch(agentSubAgent);
        }
    }

    /**
     * 发布版本时，将 controller 引用的单智能体（resource_type=agent）草稿 mapping 复制为版本 mapping。
     *
     * 背景：controller 保存时（ControllerManagementService.recordRefAgent）把引用的单智能体写入 t_mapping，
     * app_version=null（草稿态），resource_type=agent。发布时需为这些引用创建 app_version=versionId 的版本记录，
     * 否则版本导出（依赖 t_mapping）查不到单智能体，导致导出包丢失、导入后单智能体缺失。
     * 对齐子多智能体的 createAgentSubController，区别仅在校验的 AgentType 与写入的 resource_type。
     *
     * @param projectId      项目ID
     * @param workspaceId    工作空间ID
     * @param agentId        controller（多智能体）ID
     * @param versionId      发布版本ID；null 表示草稿态（仅校验，不写版本记录）
     * @param agentReferences 草稿态单智能体引用 mapping 列表
     */
    public void createAgentSubAgent(String projectId, String workspaceId, String agentId, String versionId,
        List<MappingEntity> agentReferences) {
        if (CollectionUtils.isEmpty(agentReferences)) {
            return;
        }
        // 校验 controller 是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.MULTI_AGENT_VERSION_NOT_EXIST, agentId, versionId);
        }

        Map<String, MappingEntity> versionMap = new HashMap<>();
        agentReferences.forEach(agentRef -> versionMap.put(agentRef.getResourceId(), agentRef));

        // 校验引用的单智能体是否存在（仅查 type=agent）
        List<String> agentIds = agentReferences.stream().map(MappingEntity::getResourceId).distinct().toList();
        final List<Agent> agents = agentMapper.selectByAgentIds(projectId, AgentType.AGENT.getValue(), agentIds);
        final List<String> existAgentIds = agents.stream().map(Agent::getAgentId).toList();
        List<String> notExistAgentIds = agentIds.stream().filter(id -> !existAgentIds.contains(id)).toList();
        if (!CollectionUtils.isEmpty(notExistAgentIds)) {
            log.error("These single agent not exist: {}", notExistAgentIds);
        }

        // 草稿态（versionId==null）才做重复绑定与数量校验；版本态直接复制版本记录
        if (versionId == null) {
            final List<MappingEntity> agentSubAgentList = mappingMapper.selectByAppIdAndResourceType(agentId,
                CommonConstant.AGENT_TYPE);
            if (!CollectionUtils.isEmpty(agentSubAgentList)) {
                List<String> boundAgentIds = agentSubAgentList.stream().map(MappingEntity::getResourceId).toList();
                agents.removeIf(item -> boundAgentIds.contains(item.getAgentId()));
                if (CollectionUtils.isEmpty(agents)) {
                    return;
                }
                if (agents.size() + boundAgentIds.size() > controllerSubAgentLimit) {
                    throw new AgentStudioException(StudioError.MULTI_AGENT_NUMBER_EXCEED_LIMIT);
                }
            }
        }

        // 复制版本 mapping：resource_type=agent，app_version=versionId
        List<MappingEntity> agentSubAgent = new ArrayList<>();
        for (Agent item : agents) {
            MappingEntity originMapping = versionMap.get(item.getAgentId());
            MappingEntity agentMapping = new MappingEntity();
            agentMapping.setMappingId(UUID.randomUUID().toString());
            agentMapping.setAppId(agentId);
            agentMapping.setAppType(CommonConstant.AGENT_TYPE);
            agentMapping.setAppName(agent.getName());
            agentMapping.setAppVersion(versionId);
            agentMapping.setResourceId(item.getAgentId());
            agentMapping.setResourceType(CommonConstant.AGENT_TYPE);
            agentMapping.setResourceVersion(originMapping.getResourceVersion());
            agentMapping.setResourceName(StringUtils.isEmpty(originMapping.getResourceName())
                ? item.getName()
                : originMapping.getResourceName());
            agentSubAgent.add(agentMapping);
        }
        if (!CollectionUtils.isEmpty(agentSubAgent)) {
            mappingMapper.insertBatch(agentSubAgent);
        }
    }

    /**
     * 根据传入的Mcp server绑定信息关联agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param mcpReferences mcpReferences
     * @return List
     */
    @Transactional
    public List<MappingEntity> createAgentMcp(String projectId, String workspaceId, String agentId, String versionId,
        List<MappingEntity> mcpReferences) {
        if (CollectionUtils.isEmpty(mcpReferences)) {
            return new ArrayList<>();
        }
        if (mcpReferences.size() > mcpBoundLimit) {
            throw new AgentStudioException(StudioError.MCP_NUMBER_EXCEED_LIMIT);
        }

        // 校验agent是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        // 校验Mcp server是否存在
        List<String> mcpIds = mcpReferences.stream().map(MappingEntity::getResourceId).distinct().toList();
        List<McpServiceEntity> mcpServerInfo = serviceDao.listMcpServiceByIdAndTenant(mcpIds, CommonUtil.getTenantId(),
            CommonUtil.getDeptCode(), workspaceId);
        Set<String> ownerMcpIds = mcpServerInfo.stream().map(McpServiceEntity::getId).collect(Collectors.toSet());
        // 查共享给该空间的mcp
        mcpServerInfo.addAll(shareInnerService.getShareMcp(mcpIds, workspaceId));

        final List<String> existMcpIds = mcpServerInfo.stream().map(McpServiceEntity::getId).toList();
        List<String> notExistMcpIds = mcpIds.stream().filter(id -> !existMcpIds.contains(id)).toList();
        if (!CollectionUtils.isEmpty(notExistMcpIds)) {
            log.error("These Mcp servers not exist: {}", notExistMcpIds);
        }

        final List<MappingEntity> agentMcpList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.MCP_TYPE);
        if (!CollectionUtils.isEmpty(agentMcpList) && versionId == null) {
            List<String> boundMcpIds = agentMcpList.stream().map(MappingEntity::getResourceId).toList();
            log.info("These MCP servers have been bound: {}", boundMcpIds);
            mcpServerInfo.removeIf(mcp -> boundMcpIds.contains(mcp.getServerId()));
            if (mcpServerInfo.size() + boundMcpIds.size() > mcpBoundLimit) {
                throw new AgentStudioException(StudioError.MCP_NUMBER_EXCEED_LIMIT);
            }
        }

        // 关联Agent和Mcp servers
        Map<String, MappingEntity> mcpReferencesDict = mcpReferences.stream()
                .collect(Collectors.toMap(
                        MappingEntity::getResourceId,
                        entity -> entity,
                        (oldValue, newValue) -> newValue));
        List<MappingEntity> agentMcpServers = new ArrayList<>();
        for (McpServiceEntity mcpServer : mcpServerInfo) {
            MappingEntity mcpMappings = new MappingEntity();
            mcpMappings.setMappingId(UUID.randomUUID().toString());
            mcpMappings.setAppId(agentId);
            mcpMappings.setAppType(CommonConstant.AGENT_TYPE);
            mcpMappings.setAppName(agent.getName());
            mcpMappings.setAppVersion(versionId);
            mcpMappings.setResourceId(mcpServer.getId());
            mcpMappings.setResourceType(CommonConstant.MCP_TYPE);
            mcpMappings.setResourceName(mcpServer.getName());
            mcpMappings.setResourceDesc(mcpServer.getDescription());
            mcpMappings.setReferenceType(ownerMcpIds.contains(mcpServer.getId())
                    ? ReferenceTypeEnum.DIRECT.getValue() : ReferenceTypeEnum.SHARE.getValue());
            mcpMappings.setResourceChooseTools(mcpReferencesDict.get(mcpServer.getId()).getResourceChooseTools());
            mcpMappings.setExtendInfo(mcpBase.parseMcpInput2ResourceParameter(mcpServer));
            agentMcpServers.add(mcpMappings);
        }

        if (!CollectionUtils.isEmpty(agentMcpServers)) {
            mappingMapper.insertBatch(agentMcpServers);
        }
        return mcpReferences;
    }

    /**
     * 根据传入的Mcp server绑定信息更新关联agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param mcpReferences mcpReferences
     * @return List
     */
    @Transactional
    public List<MappingEntity> updateAgentMcp(String projectId, String workspaceId, String agentId, String versionId,
                                              List<MappingEntity> mcpReferences) {
        if (CollectionUtils.isEmpty(mcpReferences)) {
            return new ArrayList<>();
        }

        // 校验agent是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        final List<MappingEntity> agentMcpList = mappingMapper.selectByAppIdAndResourceType(agentId,
                CommonConstant.MCP_TYPE);
        List<String> boundMcpIds = agentMcpList.stream().map(MappingEntity::getResourceId).toList();

        // 关联Agent和Mcp servers
        List<MappingEntity> agentMcpServers = new ArrayList<>();
        for (MappingEntity mcpReference : mcpReferences) {
            if (!boundMcpIds.contains(mcpReference.getResourceId())) {
                log.warn("This Mcp server not bound on agent, resourceId:{}, agentId:{}",
                        mcpReference.getResourceId(), agentId);
                continue;
            }
            MappingEntity mcpMappings = new MappingEntity();
            mcpMappings.setAppId(agentId);
            mcpMappings.setAppVersion(versionId);
            mcpMappings.setResourceId(mcpReference.getResourceId());
            mcpMappings.setResourceType(CommonConstant.MCP_TYPE);
            mcpMappings.setResourceChooseTools(mcpReference.getResourceChooseTools());
            agentMcpServers.add(mcpMappings);
        }

        // 更新mcp选择的工具
        if (!CollectionUtils.isEmpty(agentMcpServers)) {
            mappingMapper.updateMcpServerBatch(agentMcpServers);
        }
        return mcpReferences;
    }

    /**
     * 删除agent和资源绑定关系
     *
     * @param agentId agentId
     * @param resourceIds resourceIds
     */
    @Transactional
    public void deleteAgentResourceMapping(String agentId, List<String> resourceIds) {
        if (CollectionUtils.isEmpty(resourceIds)) {
            return;
        }

        // 解绑资源
        mappingMapper.deleteBatch(agentId, resourceIds);
    }

    /**
     * agent和tool绑定关系批量处理，根据入参判断绑定或解绑
     *
     * @param projectId 项目id
     * @param agentId agent id
     * @param tools 需要处理的tool列表
     */
    @Transactional
    public void handleAgentTool(String projectId, String workspaceId, String agentId, List<MappingEntity> tools) {
        List<MappingEntity> hasBoundToolList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.TOOL_TYPE);
        List<String> hasBoundToolIdList = hasBoundToolList.stream().map(MappingEntity::getResourceId).toList();

        // 入参tools为null时，默认不处理，直接返回
        if (tools == null) {
            return;
        }

        // 已绑定tool为空时，直接绑定入参tools
        if (hasBoundToolList.isEmpty()) {
            log.info("The create bound tool mappings: {}", tools);
            createAgentTool(projectId, workspaceId, agentId, null, tools);
            return;
        }

        // 入参tools为空时，直接解绑
        if (tools.isEmpty()) {
            log.info("The delete bound tool mappings: {}", hasBoundToolList);
            deleteAgentResourceMapping(agentId, hasBoundToolIdList);
            return;
        }

        // 排查已绑定的toolIds和入参toolIds中的差集，即为需要解绑列表
        List<String> toolIds = tools.stream().map(MappingEntity::getResourceId).toList();
        List<String> deleteMappingList = new ArrayList<>();
        // 检查是否存在版本更新
        // 传入的tool id与version
        Map<String, String> toolVersionMap = tools.stream()
            .filter(tool -> tool.getResourceVersion() != null)
            .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getResourceVersion));
        // 已绑定tool id和version
        Map<String, String> hasBoundToolIdVersionMap = hasBoundToolList.stream()
            .filter(tool -> tool.getResourceVersion() != null)
            .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getResourceVersion));
        for (String toolId : hasBoundToolIdList) {
            String toolVersion = toolVersionMap.get(toolId);
            String boundVersion = hasBoundToolIdVersionMap.get(toolId);
            if (!toolIds.contains(toolId) ||
                (toolVersion != null && boundVersion != null
                    && !toolVersion.equals(boundVersion))) {
                deleteMappingList.add(toolId);
            }
        }
        log.info("The delete bound tool mappings: {}", deleteMappingList);
        deleteAgentResourceMapping(agentId, deleteMappingList);
        // 更新 hasBoundToolIdList，移除已删除的工具
        hasBoundToolIdList = hasBoundToolIdList.stream()
            .filter(toolId -> !deleteMappingList.contains(toolId))
            .collect(Collectors.toList());
        // 入参tools排查已绑定的tool，即为需要绑定列表
        List<MappingEntity> createMappingList = new ArrayList<>();
        List<MappingEntity> modifyMappingList = new ArrayList<>();
        for (MappingEntity toolReference : tools) {
            if (!hasBoundToolIdList.contains(toolReference.getResourceId())) {
                createMappingList.add(toolReference);
            } else {
                toolReference.setAppWorkspaceId(workspaceId);
                modifyMappingList.add(toolReference);
            }
        }
        log.info("The create bound tool mappings: {}", createMappingList);
        createAgentTool(projectId, workspaceId, agentId, null, createMappingList);
        log.info("The modify bound tool mappings: {}", modifyMappingList);
        // 修改Tool入参
        if (!modifyMappingList.isEmpty()) {
            for (MappingEntity mappingEntity : modifyMappingList) {
                mappingMapper.updateResourceParameterByAppIDAndResourceId(mappingEntity);
                log.info("update resource parameter, {}", mappingEntity);
            }
        }
    }

    @Transactional
    public void handleAgentMemoryRepo(String projectId, String workspaceId, String agentId, String memoryRepoId, String agentType) {
        // 如果memoryRepoId为空，直接解绑
        if (StringUtils.isEmpty(memoryRepoId)) {
            deleteAgentResourceMapping(agentId, List.of(memoryRepoId));
            return;
        }
        List<MappingEntity> mappings = mappingMapper.selectByAppIdAndResourceType(agentId, ResourceTypeEnum.MEMORY.toString());
        if (!mappings.isEmpty()) {
            deleteAgentResourceMapping(agentId, List.of(mappings.get(0).getResourceId()));
        }
        createAgentMemory(projectId, workspaceId, agentId, null, memoryRepoId, agentType);
    }

    private void createAgentMemory(String projectId, String workspaceId, String agentId, String versionId, String memoryRepoId, String agentType) {
        // 校验agent是否存在
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectById(memoryRepoId);
        if (Objects.isNull(memoryRepoEntity)) {
            throw new AgentStudioException(StudioError.MEMORY_REPO_NOT_EXIST);
        }

        // 关联agent和knowledgeRepos
        MappingEntity agentMemoryMapping = new MappingEntity();
        agentMemoryMapping.setMappingId(UUID.randomUUID().toString());
        agentMemoryMapping.setAppId(agentId);
        agentMemoryMapping.setAppType(agentType);
        agentMemoryMapping.setAppName(agent.getName());
        agentMemoryMapping.setAppVersion(versionId);
        agentMemoryMapping.setResourceId(memoryRepoId);
        agentMemoryMapping.setResourceType(CommonConstant.MEMORY);
        agentMemoryMapping.setResourceName(memoryRepoEntity.getName());
        mappingMapper.insertBatch(List.of(agentMemoryMapping));
    }

    /**
     * agent和knowledgeRepo绑定关系批量处理，根据入参判断绑定或解绑
     *
     * @param agentId agent id
     * @param knowledgeRepos 待处理的知识库列表
     */
    @Transactional
    public void handleAgentKnowledgeRepo(String projectId, String workspaceId, String agentId,
        List<MappingEntity> knowledgeRepos) {
        // 入参knowledge为null时，默认不处理，直接返回
        if (knowledgeRepos == null) {
            return;
        }

        // 查询所有已经绑定的知识库
        List<MappingEntity> boundKnowledgeMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.REPO_TYPE);
        List<String> boundKnowledgeRepoIds = boundKnowledgeMappings.stream().map(MappingEntity::getResourceId).toList();

        // 已绑定knowledge为空时，直接绑定入参knowledge
        if (boundKnowledgeMappings.isEmpty()) {
            log.info("The create bound repo mappings: {}", knowledgeRepos);
            createAgentKnowledge(projectId, workspaceId, agentId, null, knowledgeRepos);
            return;
        }

        // 入参knowledge为空时，直接解绑
        if (knowledgeRepos.isEmpty()) {
            log.info("The delete bound repo mappings: {}", boundKnowledgeMappings);
            deleteAgentResourceMapping(agentId, boundKnowledgeRepoIds);
            return;
        }

        // 排查已绑定的knowledge和入参knowledge中的差集，即为需要解绑列表
        List<String> knowledgeRepoIds = knowledgeRepos.stream().map(MappingEntity::getResourceId).toList();
        List<String> deleteMappingList = new ArrayList<>();
        for (String toolId : boundKnowledgeRepoIds) {
            if (!knowledgeRepoIds.contains(toolId)) {
                deleteMappingList.add(toolId);
            }
        }
        log.info("The delete bound repo mappings: {}", deleteMappingList);
        deleteAgentResourceMapping(agentId, deleteMappingList);

        // 入参knowledge排除已绑定列表，即为需要绑定的列表
        List<MappingEntity> createMappingList = new ArrayList<>();
        for (MappingEntity knowledgeReference : knowledgeRepos) {
            if (!boundKnowledgeRepoIds.contains(knowledgeReference.getResourceId())) {
                createMappingList.add(knowledgeReference);
            }
        }
        log.info("The create bound repo mappings: {}", createMappingList);
        createAgentKnowledge(projectId, workspaceId, agentId, null, createMappingList);
    }

    /**
     * agent和workflow绑定关系批量处理，根据入参判断绑定或解绑
     *
     * @param agentId agent id
     * @param workflows 知识库列表
     */
    @Transactional
    public void handleAgentWorkflow(String projectId, String workspaceId, String agentId,
        List<MappingEntity> workflows) {
        // 入参workflows为null时，默认不处理，直接返回
        if (workflows == null) {
            return;
        }

        // 查询所有已经绑定的工作流
        List<MappingEntity> boundWorkflowMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.WORKFLOW_TYPE);
        List<String> boundWorkflowIds = boundWorkflowMappings.stream().map(MappingEntity::getResourceId).toList();

        // 已绑定工作流为空时，直接绑定入参workflows
        if (boundWorkflowMappings.isEmpty()) {
            log.info("The create bound workflow mappings: {}", workflows);
            createAgentWorkflow(projectId, workspaceId, agentId, null, workflows);
            return;
        }

        // 入参workflows为空时，直接解绑
        if (workflows.isEmpty()) {
            log.info("The delete bound workflow mappings: {}", boundWorkflowMappings);
            deleteAgentResourceMapping(agentId, boundWorkflowIds);
            return;
        }

        // 排查已绑定的工作流和入参工作流中的差集，即为需要解绑列表
        List<String> workflowIds = workflows.stream().map(MappingEntity::getResourceId).toList();
        List<String> deleteMappingList = new ArrayList<>();
        // 判断是否更新版本，如更新，则删去老版本，绑定新版本
        // 传入的workflow id和version
        Map<String, String> workflowVersionMap = workflows.stream()
            .filter(tool -> tool.getResourceVersion() != null)
            .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getResourceVersion));
        // 已绑定workflow id和version
        Map<String, String> hasBoundWorkflowIdVersionMap = boundWorkflowMappings.stream()
            .filter(workflow -> workflow.getResourceVersion() != null)
            .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getResourceVersion));
        for (String workflowId : boundWorkflowIds) {
            String workflowVersion = workflowVersionMap.get(workflowId);
            String boundVersion = hasBoundWorkflowIdVersionMap.get(workflowId);
            if (!workflowIds.contains(workflowId) ||
                (workflowVersion != null && boundVersion != null
                    && !workflowVersion.equals(boundVersion))) {
                deleteMappingList.add(workflowId);
            }
        }
        log.info("The delete bound workflow mappings: {}", deleteMappingList);
        deleteAgentResourceMapping(agentId, deleteMappingList);
        // 更新 hasBoundToolIdList，移除已删除的工具
        boundWorkflowIds = boundWorkflowIds.stream()
            .filter(workflowId -> !deleteMappingList.contains(workflowId))
            .collect(Collectors.toList());
        // 入参工作流排除已绑定列表，即为需要绑定的列表
        List<MappingEntity> createMappingList = new ArrayList<>();
        List<MappingEntity> modifyMappingList = new ArrayList<>();
        for (MappingEntity mappingEntity : workflows) {
            if (!boundWorkflowIds.contains(mappingEntity.getResourceId())) {
                createMappingList.add(mappingEntity);
            } else {
                modifyMappingList.add(mappingEntity);
            }
        }
        log.info("The create bound workflow mappings: {}", createMappingList);
        createAgentWorkflow(projectId, workspaceId, agentId, null, createMappingList);
        log.info("The modify bound workflow mappings: {}", modifyMappingList);
        // 修改Workflow入参
        if (!modifyMappingList.isEmpty()) {
            for (MappingEntity mappingEntity : modifyMappingList) {
                mappingMapper.updateResourceParameterByAppIDAndResourceId(mappingEntity);
                log.info("update resource parameter, {}", mappingEntity);
            }
        }
    }

    /**
     * agent和Mcp server绑定关系批量处理，根据入参判断绑定或解绑
     *
     * @param agentId agent id
     * @param mcpServers mcpServer列表
     */
    @Transactional
    public void handleAgentMcp(String projectId, String workspaceId, String agentId, List<MappingEntity> mcpServers) {
        // 入参mcpServers为null时，默认不处理，直接返回
        if (mcpServers == null) {
            return;
        }

        // 查询所有已经绑定的Mcp server
        List<MappingEntity> boundMcpMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.MCP_TYPE);
        List<String> boundMcpIds = boundMcpMappings.stream().map(MappingEntity::getResourceId).toList();

        // 已绑定Mcp server为空时，直接绑定入参mcpServers
        if (boundMcpMappings.isEmpty()) {
            log.info("The create bound Mcp server mappings: {}", mcpServers);
            createAgentMcp(projectId, workspaceId, agentId, null, mcpServers);
            return;
        }

        // 入参mcpServers为空时，直接解绑
        if (mcpServers.isEmpty()) {
            log.info("The delete bound Mcp server mappings: {}", boundMcpMappings);
            deleteAgentResourceMapping(agentId, boundMcpIds);
            return;
        }

        // 排查已绑定的Mcp server和入参mcpServers中的差集，即为需要解绑列表
        List<String> mcpServerIds = mcpServers.stream().map(MappingEntity::getResourceId).toList();
        List<String> deleteMappingList = new ArrayList<>();
        for (String boundMcpId : boundMcpIds) {
            if (!mcpServerIds.contains(boundMcpId)) {
                deleteMappingList.add(boundMcpId);
            }
        }
        log.info("The delete bound Mcp server mappings: {}", deleteMappingList);
        deleteAgentResourceMapping(agentId, deleteMappingList);

        // boundMcpIds排除已删除的mcp，再对剩下的mcp分类
        boundMcpIds = boundMcpIds.stream()
                .filter(mcpId -> !deleteMappingList.contains(mcpId))
                .collect(Collectors.toList());

        // 入参mcpServers排除已绑定列表，即为需要绑定的列表
        List<MappingEntity> createMappingList = new ArrayList<>();
        List<MappingEntity> modifyMappingList = new ArrayList<>();

        for (MappingEntity mappingEntity : mcpServers) {
            if (!boundMcpIds.contains(mappingEntity.getResourceId())) {
                createMappingList.add(mappingEntity);
            } else {
                modifyMappingList.add(mappingEntity);
            }
        }
        log.info("The create bound Mcp server mappings: {}", createMappingList);
        createAgentMcp(projectId, workspaceId, agentId, null, createMappingList);
        log.info("The update bound Mcp server mappings: {}", modifyMappingList);
        updateAgentMcp(projectId, workspaceId, agentId, null, modifyMappingList);

        // 修改mcp入参
        if (!modifyMappingList.isEmpty()) {
            for (MappingEntity mappingEntity : modifyMappingList) {
                mappingMapper.updateResourceParameterByAppIDAndResourceId(mappingEntity);
                log.info("update mcp resource parameter, {}", mappingEntity);
            }
        }
    }

    /**
     * 查询agent绑定的插件列表
     *
     * @param projectId projectId
     * @param agentId agentId
     * @return List
     */
    public List<ToolReference> listAgentTools(String projectId, String workspaceId, String agentId, Integer offset,
        Integer limit) {
        PageHelper.offsetPage(offset, limit);
        List<MappingEntity> agentTools = mappingMapper.selectByAppIdAndResourceType(agentId, CommonConstant.TOOL_TYPE);
        PageInfo<MappingEntity> pageInfo = new PageInfo<>(agentTools);
        if (pageInfo.getTotal() == 0) {
            return new ArrayList<>();
        }
        // 获取插件的输入详情
        Map<String, String> resourceParameters = new HashMap<>();
        for (MappingEntity agentTool : agentTools) {
            String pluginId = agentTool.getResourceId();
            String resourceParameter = agentTool.getExtendInfo();
            resourceParameters.put(pluginId, resourceParameter);
        }
        List<String> pluginIds = agentTools.stream().map(MappingEntity::getResourceId).toList();
        List<ToolReference> toolReferences = pluginService.getToolReferences(projectId, workspaceId, pluginIds);
        for (ToolReference toolReference : toolReferences) {
            String pluginId = toolReference.getToolId();
            if (resourceParameters.containsKey(pluginId)) {
                toolReference.setToolParameter(resourceParameters.get(pluginId));
            }
        }
        return toolReferences;
    }

    /**
     * 查询agent绑定的知识库列表
     *
     * @param projectId projectId
     * @param agentId agentId
     * @return List
     */
    public KnowledgeRepoListRsp listAgentKnowledge(String projectId, String workspaceId, String agentId, Integer offset,
        Integer limit) {
        PageHelper.offsetPage(offset, limit);
        final List<MappingEntity> agentKnowledgeList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.REPO_TYPE);
        PageInfo<MappingEntity> pageInfo = new PageInfo<>(agentKnowledgeList);

        KnowledgeRepoListRsp knowledgeRepoListRsp = new KnowledgeRepoListRsp();
        knowledgeRepoListRsp.setTotalCount(pageInfo.getTotal());
        knowledgeRepoListRsp.setKnowledgeRepoEntityList(knowledgeRepoListRsp.getTotalCount() == 0
            ? new ArrayList<>()
            : getExistKnowledgeRepos(projectId, workspaceId,
                agentKnowledgeList.stream().map(MappingEntity::getResourceId).toList()));
        return knowledgeRepoListRsp;
    }

    /**
     * 查询agent绑定的工作流列表
     *
     * @param projectId projectId
     * @param agentId agentId
     * @return List
     */
    public List<WorkflowEntity> listAgentWorkflows(String projectId, String workspaceId, String agentId) {
        List<MappingEntity> agentWorkflowList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.WORKFLOW_TYPE);
        List<String> workflowIds = agentWorkflowList.stream().map(MappingEntity::getResourceId).distinct().toList();

        List<WorkflowEntity> workflowEntityListInCurrentWorkspace = workflowMapper.selectByWorkflowIds(projectId,
            workspaceId, workflowIds);

        // 获取ID列表，对于未查询到的工作流，需要二次查询删除的历史资源表
        Set<String> existIds = workflowEntityListInCurrentWorkspace.stream()
            .map(WorkflowEntity::getId)
            .collect(Collectors.toSet());

        // 对于已删除的工作流，需要查询历史资源表
        List<String> deleteWorkflowIds = agentWorkflowList.stream()
            .filter(mapping -> !mapping.isValid() && !existIds.contains(mapping.getResourceId()))
            .map(MappingEntity::getResourceId)
            .distinct()
            .toList();
        if (ObjectUtils.isNotEmpty(deleteWorkflowIds)) {
            List<WorkflowEntity> historyWorkflows = historyWorkflowMapper.selectByWorkflowIds(projectId, workspaceId,
                deleteWorkflowIds);
            workflowEntityListInCurrentWorkspace.addAll(historyWorkflows);
        }

        ArrayList<WorkflowEntity> agenetWorkflowEntityList = new ArrayList<>(workflowEntityListInCurrentWorkspace);

        List<String> shareResourceIdList = agentWorkflowList.stream()
            .filter(mapping -> ReferenceTypeEnum.SHARE.getValue().equals(mapping.getReferenceType()))
            .map(MappingEntity::getResourceId)
            .distinct()
            .toList();

        if (CollectionUtils.isEmpty(shareResourceIdList)) {
            return agenetWorkflowEntityList;
        }

        List<WorkflowEntity> shareWorkflowEntityList = workflowMapper.selectByWorkflowIds(projectId, null,
            shareResourceIdList);

        agenetWorkflowEntityList.addAll(shareWorkflowEntityList);

        return agenetWorkflowEntityList;
    }

    /**
     * 查询agent绑定的指定版本的工作流列表
     *
     * @param projectId 项目id
     * @param workspaceId 工作空间id
     * @return 查询工作流列表
     */
    public List<WorkflowEntity> listAgentWorkflowVersions(String projectId, String workspaceId, Map<String, MappingEntity> agentWorkflowMap) {

        List<String> workflowIds = agentWorkflowMap.keySet().stream().toList();
        List<WorkflowEntity> workflowEntities = workflowMapper.selectByWorkflowIds(projectId, workspaceId, workflowIds);
        workflowEntities.forEach(workflowEntity -> {
            if (ObjectUtils.isNotEmpty(agentWorkflowMap.get(workflowEntity.getId()))) {
                // 替换指定版本IrPath
                ReleaseVersion workflowReleaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(
                    workflowEntity.getId(), agentWorkflowMap.get(workflowEntity.getId()).getResourceVersion());
                if (workflowReleaseVersion != null) {
                    workflowEntity.setIrPath(workflowReleaseVersion.getIrPath());
                }

            }
        });
        return workflowEntities;
    }

    /**
     * 查询agent绑定的Mcp server列表
     *
     * @param agentId agentId
     * @return List
     */
    public List<McpServerReference> listAgentMcpServers(String agentId) {
        final List<MappingEntity> agentMcpList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.MCP_TYPE);
        List<McpServerReference> mcpReferences = new ArrayList<>();
        for (MappingEntity agentMcp : agentMcpList) {
            McpServerReference mcpServerReference = new McpServerReference();
            mcpServerReference.setMcpServerId(agentMcp.getResourceId());
            mcpServerReference.setMcpServerName(agentMcp.getResourceName());
            String icon = defaultMcpIcon;
            int toolNum = 0;
            if (agentMcp.isValid()) {
                McpServiceEntity mcpService = this.serviceDao.selectById(agentMcp.getResourceId(),
                    CommonUtil.getTenantId(), CommonUtil.getDeptCode(), RequestContextUtils.getRequestWorkspaceId());
                icon = null == mcpService ? icon : mcpService.getIcon();
                if (mcpService != null && mcpService.getTools() != null) {
                    List<McpServiceToolEntity> tools =
                            McpJsonUtils.parseToolFromString(mcpService.getTools(), mcpService.getName());
                    toolNum = tools.size();
                }
            }
            mcpServerReference.setToolsNum(toolNum);
            mcpServerReference.setMcpServerIcon(icon);
            mcpServerReference.setDesc(agentMcp.getResourceDesc());
            mcpServerReference.setValid(agentMcp.isValid());
            // 填充旧版mcp的请求头到关系映射表中
            mcpBase.fillExtendInfoOfMcpWhenRetrieveAgent(agentMcp);
            mcpServerReference.setMcpParameter(agentMcp.getExtendInfo());
            List<String> mcpChooseTools = JsonUtils.json2Obj(agentMcp.getResourceChooseTools(),
                    new com.fasterxml.jackson.core.type.TypeReference<List<String>>() {});
            mcpServerReference.setMcpChooseTools(mcpChooseTools);
            mcpReferences.add(mcpServerReference);
        }
        return mcpReferences;
    }

    /**
     * 从待绑定的知识库id中，查询真实存在的知识库列表
     *
     * @param projectId projectId
     * @param needBoundRepoIds 待绑定的知识库id列表
     * @return 真实存在的知识库列表
     */
    public List<KnowledgeRepoEntity> getExistKnowledgeRepos(String projectId, String workspaceId,
        List<String> needBoundRepoIds) {
        // 非CUSTOM类型的知识库，从数据库中查询判断
        ListKnowledgeBasesQo knowledgeBaseQo = new ListKnowledgeBasesQo();
        knowledgeBaseQo.setKnowledgeBaseIds(needBoundRepoIds);
        knowledgeBaseQo.setWorkspaceId(workspaceId);
        List<KnowledgeBaseListItem> items = knowledgeBaseService.listKnowledgeBaseByShareScope(projectId,
            knowledgeBaseQo).getItems();
        List<KnowledgeRepoEntity> knowledgeRepoEntities = new ArrayList<>();
        if (!CollectionUtils.isEmpty(items)) {
            items.forEach(item -> {
                KnowledgeRepoEntity knowledgeRepoEntity = new KnowledgeRepoEntity();
                knowledgeRepoEntity.setKnowledgeRepoId(item.getKnowledgeBaseId());
                knowledgeRepoEntity.setIcon(item.getIcon());
                knowledgeRepoEntity.setDesc(item.getDescription());
                knowledgeRepoEntity.setCreator(item.getCreatedUserName());
                knowledgeRepoEntity.setCreatorId(item.getCreatedUserId());
                knowledgeRepoEntity.setStatus(item.getStatus().toString());
                knowledgeRepoEntity.setDisplayName(item.getName());
                knowledgeRepoEntity.setProjectId(projectId);
                knowledgeRepoEntity.setConnectionId(item.getKnowledgeBaseConnectionId());
                knowledgeRepoEntities.add(knowledgeRepoEntity);
            });
        }
        return knowledgeRepoEntities;
    }

    @Override
    public ResourceMappingList listResourcesRelations(String projectId,
        ListResourcesRelationsQo listResourcesRelationsQo) {
        // 校验资源是否存在，防止横向越权
        resourceService.validResourceExist(listResourcesRelationsQo.getResourceIds(),
            listResourcesRelationsQo.getResourceType(), projectId, listResourcesRelationsQo.getWorkspaceId());

        PageHelper.offsetPage(listResourcesRelationsQo.getOffset(), listResourcesRelationsQo.getLimit());
        List<ResourceMapping> mappings = mappingMapper.getByIds(listResourcesRelationsQo.getResourceIds());
        PageInfo<ResourceMapping> pageInfo = new PageInfo<>(mappings);

        return new ResourceMappingList().setResourceList(mappings).setCount(pageInfo.getTotal());
    }

    @Override
    public ResourceDependencyResponseBody listDependency(String projectId, String resourceId,
        ListDependencyQo listDependencyQo) {
        if (StringUtils.isEmpty(listDependencyQo.getVersionId())) {
            listDependencyQo.setVersionId(Constants.LATEST_PUBLISH_VERSION);
        }
        List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(
            resourceId, listDependencyQo.getVersionId(), null, null);
        if (CollectionUtils.isEmpty(mappingEntities)) {
            log.info("mapping is null, resourceId:{}, version:{}", resourceId, listDependencyQo.getVersionId());
            return new ResourceDependencyResponseBody().setDependencies(new ArrayList<>());
        }
        List<ResourceDependency> dependencies = mappingEntities.stream()
            .filter(MappingEntity::isValid)
            .map(entity -> new ResourceDependency()
                .setResourceId(entity.getResourceId())
                .setResourceName(entity.getResourceName())
                .setResourceVersion(entity.getResourceVersion())
                .setResourceType(entity.getResourceType())
                .setParentId(entity.getAppId()))
            .collect(Collectors.toList());
        return new ResourceDependencyResponseBody().setDependencies(dependencies);
    }

    @Override
    public ResourceVersionResponseBody listVersions(String projectId, String resourceId,
        ListVersionsQo listVersionsQo) {
        List<VersionInfo> versionInfoList = new ArrayList<>();
        boolean isSameSpace = false;
        if (ResourceTypeEnum.WORKFLOW.toString().equals(listVersionsQo.getResourceType())) {
            WorkflowEntity workflowEntity = workflowMapper.getWorkflowById(resourceId);
            isSameSpace = workflowEntity != null
                && Strings.CS.equals(workflowEntity.getWorkspaceId(), listVersionsQo.getWorkspaceId());
        } else {
            Agent agent = agentMapper.selectById(resourceId);
            isSameSpace = agent != null
                && Strings.CS.equals(agent.getWorkspaceId(), listVersionsQo.getWorkspaceId());
        }
        if (isSameSpace) {
            List<ReleaseVersion> releaseVersions = releaseVersionMapper.selectByAppId(resourceId);
            versionInfoList = releaseVersions.stream().map(ReleaseVersion::convertToInfo).collect(Collectors.toList());
            return new ResourceVersionResponseBody().setVersions(versionInfoList);
        }
        ShareResourceEntity shareResourceEntity = shareResourceMapper.selectShareResourceEntityByResourceId(resourceId);
        if (Objects.isNull(shareResourceEntity)) {
            log.info("share info is null, resourceId:{}, type:{}", resourceId, listVersionsQo.getResourceType());
            return new ResourceVersionResponseBody().setVersions(versionInfoList);
        }
        List<ShareScopeEntity> shareScopeEntities = shareScopeMapper.selectShareScopesByResourceId(resourceId);
        boolean isShareScope = shareScopeEntities.stream()
            .anyMatch(p -> Strings.CS.equals(p.getWorkspaceId(), listVersionsQo.getWorkspaceId())
                || Strings.CS.equals(p.getWorkspaceId(), CommonConstant.ALL));
        if (!isShareScope) {
            log.info("workspace not shared, resourceId:{}, type:{}", resourceId, listVersionsQo.getResourceType());
            return new ResourceVersionResponseBody().setVersions(versionInfoList);
        }
        List<VersionInfo> shareResourceVersions = JSONObject.parseObject(shareResourceEntity.getVersionList(),
            new TypeReference<>() {});
        return new ResourceVersionResponseBody().setVersions(shareResourceVersions);
    }

    @Override
    public RelationList listAppRelations(String projectId, String appId, ListAppRelationsQo listAppRelationsQo) {
        this.validateAppId(projectId, appId, listAppRelationsQo.getWorkspaceId());
        if (StringUtils.isBlank(listAppRelationsQo.getResourceType())) {
            return this.listAppRelationsAllResources(appId, listAppRelationsQo);
        }
        return this.listAppRelationsWorkFlowResources(appId, listAppRelationsQo);
    }

    private void validateAppId(String projectId, String appId, String workspaceId) {
        List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(appId, null, null, null);
        if (CollectionUtils.isEmpty(mappingEntities)) {
            return;
        }
        MappingEntity mappingEntity = mappingEntities.get(0);
        if (ResourceTypeEnum.WORKFLOW.toString().equalsIgnoreCase(mappingEntity.getAppType())) {
            resourceService.validResourceExist(Collections.singletonList(appId),
                ResourceTypeEnum.WORKFLOW.toString(), projectId, workspaceId);
        } else if (CommonConstant.AGENT.equalsIgnoreCase(mappingEntity.getAppType())) {
            resourceService.validResourceExist(Collections.singletonList(appId),
                ResourceTypeEnum.AGENT.toString(), projectId, workspaceId);
        }
    }

    private RelationList listAppRelationsWorkFlowResources(String appId, ListAppRelationsQo listAppRelationsQo) {
        int recursionCount = listAppRelationsQo.isNestedCheck() ? NESTED_DEEP : 0;
        List<Relation> relations = recursionHandleResources(appId, new ArrayList<>(), recursionCount,
            listAppRelationsQo.getVersion(), listAppRelationsQo);
        RelationList relationList = new RelationList();
        relationList.setRelations(relations);
        relationList.setCount((long) relations.size());
        return relationList;
    }

    /**
     * 递归解析工作流中的模型
     */
    private List<Relation> recursionHandleResources(String appId, List<Relation> mappings, int recursionCount,
        String version, ListAppRelationsQo listAppRelationsQo) {
        if (recursionCount < 0) {
            return mappings;
        }
        List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(appId, version, null, null);
        List<MappingEntity> resourceMappingInWorkflow = mappingEntities.stream()
            .filter(entity -> Strings.CS.equals(entity.getResourceType(), listAppRelationsQo.getResourceType())
                || Strings.CS.equals(entity.getResourceType(), ResourceTypeEnum.WORKFLOW.toString()))
            .toList();
        for (MappingEntity mappingEntity : resourceMappingInWorkflow) {
            if (mappingEntity == null) {
                continue;
            }
            Relation relation = buildRelationFromMapping(mappingEntity);
            if (Boolean.TRUE.equals(listAppRelationsQo.isShowlatest()) && CollectionUtils.isNotEmpty(mappingEntities)) {
                // 查询所有关联资源的最新版本
                Set<String> resourceIds = Set.of(mappingEntity.getResourceId());
                List<ReleaseVersion> releaseVersions = releaseVersionMapper.queryLastVersionByAppIds(resourceIds);

                // 更新List<Relation>
                Map<String, ReleaseVersion> latestVersionMap = releaseVersions.stream()
                    .collect(Collectors.toMap(ReleaseVersion::getAppId, releaseVersion -> releaseVersion));
                ReleaseVersion releaseVersion = latestVersionMap.get(relation.getResourceId());
                if (releaseVersion != null) {
                    relation.setResourceLatestVersion(releaseVersion.getVersionId());
                    relation.setResourceLatestVersionName(releaseVersion.getVersionName());
                }
            }
            if (Strings.CS.equals(mappingEntity.getResourceType(), listAppRelationsQo.getResourceType())) {
                mappings.add(relation);
                continue;
            }
            if (Strings.CS.equals(mappingEntity.getResourceType(), ResourceTypeEnum.WORKFLOW.toString())
                && mappingEntity.isValid()) {
                this.recursionHandleResources(mappingEntity.getResourceId(), mappings, recursionCount - 1,
                    mappingEntity.getResourceVersion(), listAppRelationsQo);
            }
        }
        return mappings;
    }

    private RelationList listAppRelationsAllResources(String appId, ListAppRelationsQo listAppRelationsQo) {
        // 查询关联关系
        List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(appId,
            listAppRelationsQo.getVersion(), null, null);

        if (ObjectUtils.isEmpty(mappingEntities)) {
            return new RelationList().setCount(0L).setRelations(new ArrayList<>());
        }

        // 预处理
        List<MappingEntity> subControllerMappingList = new ArrayList<>();
        List<MappingEntity> queryList = new ArrayList<>();
        for (MappingEntity mappingEntity : mappingEntities) {
            // 处理插件ID
            if ("tool".equals(mappingEntity.getResourceType()) && mappingEntity.getResourceId().contains("#")) {
                mappingEntity.setResourceId(mappingEntity.getResourceId().split("#")[0]);
            }
            // 针对二层子控制器进一步查询子工作流状态，方便前端展示
            if ("controller".equals(mappingEntity.getResourceType())) {
                MappingEntity queryEntity = new MappingEntity();
                queryEntity.setAppId(mappingEntity.getResourceId());
                queryEntity.setAppVersion(mappingEntity.getResourceVersion());
                queryEntity.setResourceType(ResourceTypeEnum.WORKFLOW.toString());
                queryList.add(queryEntity);
            }
        }
        if (ObjectUtils.isNotEmpty(queryList)) {
            subControllerMappingList = mappingMapper.selectByMappingList(queryList);
        }
        mappingEntities.addAll(subControllerMappingList);

        List<String> workspaceIdList = mappingEntities.stream().map(MappingEntity::getAppWorkspaceId).toList();
        List<WorkspaceEntity> workspaceEntityList = workspaceMapper.selectWorkspaceByWorkspaceIdList(workspaceIdList);
        Map<String, String> workspaceInfoMap = workspaceEntityList.stream()
            .collect(Collectors.toMap(WorkspaceEntity::getId, WorkspaceEntity::getName));

        List<Relation> relations = buildRelationsFromMapping(mappingEntities, workspaceInfoMap);
        if (Boolean.TRUE.equals(listAppRelationsQo.isShowlatest()) && CollectionUtils.isNotEmpty(mappingEntities)) {
            // 查询所有关联资源的最新版本
            Set<String> resourceIds = mappingEntities.stream()
                .map(MappingEntity::getResourceId)
                .collect(Collectors.toSet());
            List<ReleaseVersion> releaseVersions = releaseVersionMapper.queryLastVersionByAppIds(resourceIds);

            // 查询共享资源元素
            List<ShareResourceEntity> shareResources
                = shareResourceManagerService.queryShareResourceEntityByResourceIdList((new ArrayList<>(resourceIds)));

            // 更新List<Relation>
            Map<String, ReleaseVersion> latestVersionMap = releaseVersions.stream()
                .collect(Collectors.toMap(ReleaseVersion::getAppId, Function.identity(), (existing, replacement) -> existing));

            // 如果存在共享元素，需要获取共享元素共享的最新版本
            Map<String, ShareResourceEntity> shareResourceMap = new HashMap<>();
            if (ObjectUtils.isNotEmpty(shareResources)) {
                shareResourceMap = shareResources.stream()
                    .collect(Collectors.toMap(ShareResourceEntity::getResourceId,
                        shareResourceEntity -> shareResourceEntity));
            }

            Map<String, ShareResourceEntity> finalShareResourceMap = shareResourceMap;
            relations.forEach(relation -> {
                ReleaseVersion releaseVersion = latestVersionMap.get(relation.getResourceId());
                if (releaseVersion != null) {
                    relation.setResourceLatestVersion(releaseVersion.getVersionId());
                    relation.setResourceLatestVersionName(releaseVersion.getVersionName());
                    if (releaseVersion.getAppType().equals(ResourceTypeEnum.AGENT.toString())) {
                        relation.setLatestVersionAppSubType(releaseVersion.getSubType());
                    }
                }
                // 针对引用资源做特殊处理，需要获取共享元素共享的最新版本
                if (ReferenceTypeEnum.SHARE.getValue().equals(relation.getReferenceType()) && finalShareResourceMap.containsKey(
                    relation.getResourceId())) {
                    List<ResourceVersionInfo> shareResourceVersionInfoList = JSONObject.parseObject(
                        finalShareResourceMap.get(relation.getResourceId()).getVersionList(),
                        new TypeReference<>() { });
                    shareResourceVersionInfoList.sort(Comparator.comparing(ResourceVersionInfo::getVersionName));
                    ResourceVersionInfo shareResourceVersionLast = shareResourceVersionInfoList.get(
                        shareResourceVersionInfoList.size() - 1);

                    relation.setResourceLatestVersion(shareResourceVersionLast.getVersionId());
                    relation.setResourceLatestVersionName(shareResourceVersionLast.getVersionName());
                }
            });
            // 2. 更新skill类型资源的最新版本
            searchSkillResourceLatestVersion(relations, mappingEntities);
        }

        RelationList relationList = new RelationList();
        relationList.setRelations(relations);
        relationList.setCount((long) relations.size());
        return relationList;
    }

    private void searchSkillResourceLatestVersion(List<Relation> relations, List<MappingEntity> mappingEntities) {
        List<String> resourceIdsSKill = mappingEntities.stream()
            .filter(mappingEntity ->
                ResourceTypeEnum.SKILL.toString().equals(mappingEntity.getResourceType()))
            .map(MappingEntity::getResourceId)
            .toList();
        List<SkillDetails> skillDetailsList = skillMapper.searchBySkillIds(resourceIdsSKill);
        Map<String, SkillDetails> latestSkillVersionMap = skillDetailsList.stream()
            .collect(Collectors.toMap(SkillDetails::getSkillId, skillDetails -> skillDetails));
        relations.forEach(relation -> {
            SkillDetails skillDetails = latestSkillVersionMap.get(relation.getResourceId());
            if (skillDetails != null) {
                relation.setResourceLatestVersion(skillDetails.getUsedVersion());
            }
        });
    }

    @Override
    public RelationList listResourceRelations(String projectId, String resourceId,
                                              ListResourceRelationsQo listResourceRelationsQo) {
        log.info("Start listResourceRelations method. Parameters: projectId={}, resourceId={}, listResourceRelationsQo={}",
                projectId, resourceId, listResourceRelationsQo);

        try {
            // 校验资源是否存在，防止横向越权
            log.info("Validating resource existence. resourceId={}, resourceType={}, projectId={}, workspaceId={}",
                    resourceId, listResourceRelationsQo.getResourceType(), projectId, listResourceRelationsQo.getWorkspaceId());
            resourceService.validResourceExist(Arrays.asList(resourceId),
                    listResourceRelationsQo.getResourceType(), projectId, listResourceRelationsQo.getWorkspaceId());
            log.info("Resource validation passed.");

            // 分页查询关联关系
            log.info("Starting pagination query. Offset: {}, Limit: {}",
                    listResourceRelationsQo.getOffset(), listResourceRelationsQo.getLimit());
            PageHelper.offsetPage(listResourceRelationsQo.getOffset(), listResourceRelationsQo.getLimit());

            log.info("Calling mappingMapper.selectByResourceIdAndVersionId with parameters: resourceId={}, version={}, workspaceId={}, appType={}, referenceType={}",
                    resourceId,
                    listResourceRelationsQo.getVersion(),
                    listResourceRelationsQo.getWorkspaceId(),
                    listResourceRelationsQo.getAppType(),
                    listResourceRelationsQo.getReferenceType());

            List<MappingEntity> mappingEntities = mappingMapper.selectByResourceIdAndVersionId(resourceId,
                    listResourceRelationsQo.getVersion(), listResourceRelationsQo.getWorkspaceId(),
                    listResourceRelationsQo.getAppType(), listResourceRelationsQo.getReferenceType());

            log.info("Selected {} mapping entities from database.", mappingEntities.size());

            // 提取 workspaceId 列表
            List<String> workspaceIdList = mappingEntities.stream()
                    .map(MappingEntity::getAppWorkspaceId)
                    .filter(Objects::nonNull)
                    .distinct()
                    .toList();

            log.info("Extracted {} unique workspace IDs from mapping entities.", workspaceIdList.size());

            // 查询 workspace 信息
            List<WorkspaceEntity> workspaceEntityList = workspaceMapper.selectWorkspaceByWorkspaceIdList(workspaceIdList);

            PageInfo<MappingEntity> pageInfo = new PageInfo<>(mappingEntities);

            // 构建返回结果
            RelationList relationList = new RelationList();
            relationList.setCount(pageInfo.getTotal());

            // 构建 workspace 信息 map
            Map<String, String> workspaceInfoMap = workspaceEntityList.stream()
                    .collect(Collectors.toMap(WorkspaceEntity::getId, WorkspaceEntity::getName));

            log.info("Built workspace info map with {} entries.", workspaceInfoMap.size());

            // 构建 relation 列表
            List<Relation> relations = buildRelationsFromMapping(mappingEntities, workspaceInfoMap);
            log.info("Built {} relations from mapping entities.", relations.size());

            relationList.setRelations(relations);
            log.info("Method completed successfully. Returning result: {}", relationList);

            return relationList;

        } catch (Exception e) {
            log.error("Error occurred in listResourceRelations method. Parameters: projectId={}, resourceId={}, listResourceRelationsQo={}",
                    projectId, resourceId, listResourceRelationsQo, e);
            throw new AgentStudioException("Failed to list resource relations");
        }
    }

    /**
     * agent和模型绑定关系，根据入参判断绑定或解绑
     */
    @Transactional
    public void handleAgentModel(String projectId, String workspaceId, String agentId,
        List<MappingEntity> modelReferences) {
        if (CollectionUtils.isEmpty(modelReferences)) {
            return;
        }
        List<MappingEntity> boundModelMappings = mappingMapper.selectByAppIdAndResourceType(agentId,
            ResourceTypeEnum.MODEL.toString());
        List<String> boundModelIds = boundModelMappings.stream().map(MappingEntity::getResourceId).toList();
        List<String> newBoundModelIds = modelReferences.stream().map(MappingEntity::getResourceId).toList();
        List<String> addModelIds = new ArrayList<>(newBoundModelIds);
        List<String> deleteModelIds = new ArrayList<>(boundModelIds);
        addModelIds.removeAll(boundModelIds);
        deleteModelIds.removeAll(newBoundModelIds);
        if (!CollectionUtils.isEmpty(deleteModelIds)) {
            deleteAgentResourceMapping(agentId, deleteModelIds);
        }
        List<MappingEntity> addModelMapping = modelReferences.stream()
            .filter(modelReference -> addModelIds.contains(modelReference.getResourceId()))
            .toList();
        if (!CollectionUtils.isEmpty(addModelMapping)) {
            createAgentModel(projectId, workspaceId, agentId, null, addModelMapping);
        }
    }

    /**
     * 绑定模型信息关联agent
     */
    @Transactional
    public void createAgentModel(String projectId, String workspaceId, String agentId, String versionId,
        List<MappingEntity> modelReferences) {
        if (CollectionUtils.isEmpty(modelReferences)) {
            return;
        }
        Set<String> modelIds = modelReferences.stream().map(MappingEntity::getResourceId).collect(Collectors.toSet());
        if (CollectionUtils.isEmpty(modelIds)) {
            return;
        }
        List<ModelServiceBase> modelServiceBases = this.modelServiceManager.queryAllModelByIds(projectId, workspaceId,
            modelIds);
        Map<String, ModelServiceBase> models = modelServiceBases.stream()
            .collect(Collectors.toMap(ModelServiceBase::getId, model -> model));
        List<MappingEntity> mappingModel = modelReferences.stream()
            .filter(model -> models.containsKey(model.getResourceId()))
            .peek(model -> {
                ModelServiceBase modelServiceBase = models.get(model.getResourceId());
                if (StringUtils.isNotBlank(versionId)) {
                    model.setAppVersion(versionId);
                    model.setResourceDesc(modelServiceBase.getModelDescription());
                }
                model.setAppId(agentId);
                model.setResourceName(modelServiceBase.getModelName());
                if (StringUtils.isBlank(model.getMappingId())) {
                    model.setMappingId(UUID.randomUUID().toString());
                }
            })
            .toList();
        if (!CollectionUtils.isEmpty(mappingModel)) {
            mappingMapper.insertBatch(mappingModel);
        }
    }

    @Transactional
    public void handleAgentSkill(String projectId, String workspaceId, String agentId, List<MappingEntity> skillReferences) {
        List<MappingEntity> hasBoundSkillList = mappingMapper.selectByAppIdAndResourceType(agentId, CommonConstant.SKILL_TYPE);
        List<String> hasBoundSkillIdList = hasBoundSkillList.stream().map(MappingEntity::getResourceId).toList();
        // 入参skills为null时，默认不处理，直接返回
        if (skillReferences == null) {
            return;
        }
        // 已绑定skill为空时，直接绑定入参skills
        if (hasBoundSkillList.isEmpty()) {
            log.info("The create bound skill mappings: {}", skillReferences);
            createAgentSkill(projectId, workspaceId, agentId, null, skillReferences);
            return;
        }
        // 入参skills为空时，直接解绑
        if (skillReferences.isEmpty()) {
            log.info("The delete bound skill mappings: {}", hasBoundSkillList);
            deleteAgentResourceMapping(agentId, hasBoundSkillIdList);
            return;
        }
        // 排查已绑定的skillIds和入参skillIds中的差集，即为需要解绑列表
        List<String> skillIds = skillReferences.stream().map(MappingEntity::getResourceId).toList();
        List<String> deleteMappingList = new ArrayList<>();
        // 检查是否存在版本更新
        // 传入的skill id与version
        Map<String, String> skillVersionMap = skillReferences.stream()
            .filter(skill -> skill.getResourceVersion() != null)
            .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getResourceVersion, (v1, v2) -> v1));
        // 已绑定skill id和version
        Map<String, String> hasBoundSkillIdVersionMap = hasBoundSkillList.stream()
            .filter(skill -> skill.getResourceVersion() != null)
            .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getResourceVersion, (v1, v2) -> v1));
        for (String skillId : hasBoundSkillIdList) {
            String skillVersion = skillVersionMap.get(skillId);
            String boundVersion = hasBoundSkillIdVersionMap.get(skillId);
            if (!skillIds.contains(skillId) ||
                (skillVersion != null && boundVersion != null
                    && !skillVersion.equals(boundVersion))) {
                deleteMappingList.add(skillId);
            }
        }
        log.info("The delete bound skill mappings: {}", deleteMappingList);
        deleteAgentResourceMapping(agentId, deleteMappingList);
        // 更新 hasBoundSkillIdList，移除已删除的技能
        hasBoundSkillIdList = hasBoundSkillIdList.stream()
            .filter(skillId -> !deleteMappingList.contains(skillId))
            .collect(Collectors.toList());
        // 入参skills排查已绑定的skill，即为需要绑定列表
        List<String> finalHasBoundSkillIdList = hasBoundSkillIdList;
        List<MappingEntity> createMappingList = skillReferences.stream()
            .filter(skill -> !finalHasBoundSkillIdList.contains(skill.getResourceId()))
            .collect(Collectors.toList());
        log.info("The create bound skill mappings: {}", createMappingList);
        createAgentSkill(projectId, workspaceId, agentId, null, createMappingList);
    }

    /**
     * 创建agent和skill的绑定关系
     *
     * @param agentId agent id
     * @param versionId version id
     * @param skillReferences 需要绑定的技能列表
     */
    @Transactional
    public void createAgentSkill(String projectId, String workspaceId, String agentId, String versionId, List<MappingEntity> skillReferences) {
        if (CollectionUtils.isEmpty(skillReferences)) {
            return;
        }
        final Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);
        if (Objects.isNull(agent)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        List<MappingEntity> skillMappingList = new ArrayList<>();
        for (MappingEntity mappingEntity : skillReferences) {
            // 设置基本属性
            mappingEntity.setMappingId(UUID.randomUUID().toString());
            mappingEntity.setAppName(agent.getName());
            mappingEntity.setAppVersion(versionId);
            mappingEntity.setAppId(agentId);
            mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
            skillMappingList.add(mappingEntity);
        }
        if (!CollectionUtils.isEmpty(skillMappingList)) {
            mappingMapper.insertBatch(skillMappingList);
        }
    }

    public List<SkillReference> listAgentSkills(String agentId) {
        final List<MappingEntity> agentSkillList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.SKILL_TYPE);
        final List<String> skillIds = agentSkillList.stream()
            .map(MappingEntity::getResourceId)
            .collect(Collectors.toList());
        List<SkillDetails> skillDetailsList = skillMapper.searchBySkillIds(skillIds);
        if (CollectionUtils.isEmpty(skillDetailsList)) {
            return Collections.emptyList();
        }

        // 按照agentSkillList的顺序遍历，保证结果有序
        Map<String, SkillDetails> skillMapTemp = skillDetailsList.stream()
            .filter(Objects::nonNull)
            .collect(Collectors.toMap(SkillDetails::getSkillId, skill -> skill,
                (existing, replacement) -> existing, HashMap::new));

        return agentSkillList.stream()
            .map(agentSkill -> {
                SkillDetails skillDetails = skillMapTemp.get(agentSkill.getResourceId());
                SkillReference skillReference = new SkillReference();
                skillReference.setSkillId(agentSkill.getResourceId());
                skillReference.setSkillName(agentSkill.getResourceName());
                skillReference.setDescription(agentSkill.getResourceDesc());
                if (skillDetails != null) {
                    skillReference.setIcon(skillDetails.getIcon());
                }
                return skillReference;
            })
            .collect(Collectors.toList());
    }

}
