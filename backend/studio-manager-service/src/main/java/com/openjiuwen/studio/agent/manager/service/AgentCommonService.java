/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UuidUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeRepoReference;
import com.openjiuwen.studio.agent.manager.dto.McpServerReference;
import com.openjiuwen.studio.agent.manager.dto.Message;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.SkillReference;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfoRefWorkflows;
import com.openjiuwen.studio.agent.manager.dto.WorkflowReference;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.HistoryAgentEntity;
import com.openjiuwen.studio.agent.manager.entity.HistoryMappingEntity;
import com.openjiuwen.studio.agent.manager.entity.HistoryReleaseVersionEntity;
import com.openjiuwen.studio.agent.manager.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelInfo;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceCondition;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.AgentType;
import com.openjiuwen.studio.agent.manager.mapper.*;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.models.AskModelReq;
import com.openjiuwen.studio.agent.manager.rce.models.assistant.KnowledgeRepoListRsp;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.utils.IconNameCheckUtils;
import com.openjiuwen.studio.agent.manager.utils.ImageBase64Utils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.codec.binary.Base64;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import javax.annotation.Resource;

/**
 * agent管理公共服务
 *
 */
@Service
@Slf4j
public class AgentCommonService {

    @Resource
    private MgObsService mgObsService;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private ToolMapper toolMapper;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private HistoryMappingMapper historyMappingMapper;

    @Autowired
    private HistoryAgentMapper historyAgentMapper;

    @Autowired
    private HistoryReleaseVersionMapper historyReleaseVersionMapper;


    @Autowired
    private RelationManagementService relationManagementService;

    @Value("${agent.default-icon}")
    private String agentDefaultIcon;

    @Value("${controller.default-icon}")
    private String controllerDefaultIcon;

    @Value("${icon.max-size}")
    private String iconMaxSize;

    @Value("${customize-node.max-size}")
    private int maxCustomizeNodeSize;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${env.type}")
    private String envType;

    @Value("${model.obs-prefix}")
    private String modelObsPrefix;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private IPlugin pluginService;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private FreeModelServiceMapper freeModelServiceMapper;

    /**
     * 上传obs ir或dsl到obs，并返回路径
     *
     * @param agent 应用
     * @param content 上传内容
     * @param type 类型是dsl或者ir
     * @return obs路径
     */
    public String uploadToObs(Agent agent, Object content, String type) {
        return mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId(), CommonConstant.AGENT,
            JSON.toJSONString(content, JSONWriter.Feature.WriteMapNullValue), type);
    }

    /**
     * 上传obs ir或dsl到obs，并返回路径
     *
     * @param agent 应用
     * @param content 上传内容
     * @param type 类型是dsl或者ir
     * @param version 版本号
     */
    public void uploadToObsWithVersion(Agent agent, Object content, String type, String version) {
        mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId() + Constants.UNDERLINE_STR + version,
            CommonConstant.AGENT, JSON.toJSONString(content, JSONWriter.Feature.WriteMapNullValue), type);
    }

    /**
     * 上传obs ir或dsl到obs，并返回路径
     *
     * @param agent 应用
     * @param content 上传内容
     * @param type 类型是dsl或者ir
     * @param version 版本号
     */
    public void uploadToObsNoNullWithVersion(Agent agent, Object content, String type, String version) {
        mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId() + Constants.UNDERLINE_STR + version,
            CommonConstant.AGENT, JSON.toJSONString(content), type);
    }

    /**
     * 上传obs ir或dsl到obs，并返回路径
     *
     * @param agent 应用
     * @param content 上传内容
     * @param type 类型是dsl或者ir
     * @return obs路径
     */
    public String uploadToObsNoNull(Agent agent, Object content, String type) {
        return mgObsService.uploadObsFile(agent.getAgentId(), agent.getAgentId(), CommonConstant.AGENT,
            JSON.toJSONString(content), type);
    }

    /**
     * 获取agent的ir或dsl obs路径
     *
     * @param id agent的id
     * @param type dsl或者obs
     * @return obs路径
     */
    public String getAgentObsPath(String id, String type) {
        return String.format("%s/%s/%s/%s.json", CommonConstant.AGENT, type, id, id);
    }

    /**
     * 获取agent的ir或dsl obs路径
     *
     * @param id agent的id
     * @param type dsl或者obs
     * @param versionId 版本id
     * @return obs路径
     */
    public String getAgentObsPath(String id, String type, String versionId) {
        return String.format("%s/%s/%s/%s.json", CommonConstant.AGENT, type, id,
            id + Constants.UNDERLINE_STR + versionId);
    }

    /**
     * 初始化Agent
     *
     * @param projectId 项目id
     * @param body 创建agent消息体
     * @return 返回agent对象
     */
    public Agent initAgent(String projectId, String workspaceId, CreateAgentReq body) {
        AgentType agentType = AgentType.naValueOf(body.getType() == null ? null : body.getType().toString());
        String defaultIcon;
        if (agentType == AgentType.CONTROLLER) {
            defaultIcon = controllerDefaultIcon;
        } else {
            defaultIcon = agentDefaultIcon;
        }

        String iconName = null;
        if (StringUtils.isEmpty(body.getIcon())) {
            body.setIcon(defaultIcon);
        } else {
            IconNameCheckUtils.validaIconName(body.getIcon());
            iconName = body.getIcon();
            String icon = ImageBase64Utils.getImageBase64(body.getIcon(), mgObsService);
            body.setIcon(icon);
        }
        Agent agent = new Agent();
        agent.setAgentId(UUID.randomUUID().toString());
        agent.setTraceId(agent.getAgentId());
        agent.setProjectId(projectId);
        agent.setName(body.getName());
        agent.setDescription(body.getDescription());
        agent.setIcon(body.getIcon());
        agent.setStatus(AgentStatus.DRAFT.toString());
        agent.setCreator(RequestContextUtils.getRequestUserName());
        agent.setCreatorId(RequestContextUtils.getRequestUserId());
        agent.setType(AgentType.naValueOf(body.getType() == null ? null : body.getType().toString()).getValue());
        agent.setIconName(iconName);
        agent.setWorkspaceId(workspaceId);
        agent.setDomainId(RequestContextUtils.getRequestUserDomainId());
        agent.setDeleted(0);

        // 检查agent icon
        checkAgentIcon(agent.getIcon());
        return agent;
    }

    /**
     * 根据agentId查询指定agent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @return Agent
     */
    @NotNull
    public Agent getAgent(String projectId, String agentId) {
        final Agent agent = agentMapper.selectByPrimaryKey(projectId, agentId);
        if (agent == null) {
            log.error("agent does not exist, projectId = {}, agentId = {}", projectId, agentId);
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        return agent;
    }

    /**
     * 根据项目ID、工作空间ID和代理ID获取代理对象。
     *
     * @param projectId 项目ID
     * @param workspaceId 工作空间ID
     * @param agentId 代理ID
     * @return 返回对应的Agent对象
     * @throws AgentStudioException 如果代理对象不存在，抛出AgentStudioException异常
     */
    @NotNull
    public Agent getAgent(String projectId, String workspaceId, String agentId) {
        Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, agentId);

        if (agent != null) {
            return agent;
        }

        if (shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(
            RequestContextUtils.getRequestWorkspaceId(), agentId)) {
            agent = agentMapper.selectById(agentId);
        }

        if (agent == null) {
            log.error("agent does not exist, projectId = {}, workspaceId = {}, agentId = {}", projectId, workspaceId,
                agentId);
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        return agent;
    }

    /**
     * 根据agentId获取关联的工作流最新版本
     *
     * @return 返回关联的工作流最新版本列表
     */
    public Map<String, WorkflowInfoRefWorkflows> getRefWfLastVersion(List<WorkflowEntity> workflowMappingList) {
        Map<String, WorkflowInfoRefWorkflows> refWorkflows = new HashMap<>();
        if (!CollectionUtils.isEmpty(workflowMappingList)) {
            Set<String> workflowIds = workflowMappingList.stream().map(m -> m.getId()).collect(Collectors.toSet());
            List<ReleaseVersion> releaseList = releaseVersionMapper.queryLastVersionByAppIds(workflowIds);
            if (!CollectionUtils.isEmpty(releaseList)) {
                refWorkflows = releaseList.stream()
                    .map(r -> new WorkflowInfoRefWorkflows().setWorkflowId(r.getAppId())
                        .setLastVersionId(r.getVersionId())
                        .setLastVersionName(r.getVersionName()))
                    .collect(Collectors.toMap(WorkflowInfoRefWorkflows::getWorkflowId, w -> w));
            }
        }
        return refWorkflows;
    }

    public void checkAgentIcon(String icon) {
        log.debug("Entering checkAgentIcon with icon: {}", icon);

        if (icon == null || icon.isEmpty()) {
            throw new AgentStudioException(StudioError.AGENT_ICON_EXIST);
        }
        String base64Image = icon.substring(icon.indexOf(',') + 1);
        log.debug("Extracted Base64 image part: length={}", base64Image.length());

        // 检查base64图片大小是否符合要求
        Base64 base64 = new org.apache.commons.codec.binary.Base64();
        byte[] imageBytes = base64.decode(base64Image);
        log.debug("Decoded image bytes length: {} KB", imageBytes.length / 1024.0);

        if (imageBytes.length / 1024 > Integer.parseInt(iconMaxSize)) {
            throw new AgentStudioException(StudioError.AGENT_ICON_SIZE_EXCEEDS_LIMIT);
        }
        log.debug("Icon check completed successfully");
    }

    /**
     * 查询版本列表
     *
     * @param id 组件Id
     * @param limit 最大查询限制
     * @return 发布版本列表
     */
    public VersionListRsp listVersions(String id, int limit) {
        List<ReleaseVersion> versionList = releaseVersionMapper.selectByAppIdWithLimit(id, limit);

        if (CollectionUtils.isEmpty(versionList)) {
            return new VersionListRsp().setVersionList(new ArrayList<>()).setCount(0);
        }

        List<VersionInfo> versionInfoList = versionList.stream().map(ReleaseVersion::convertToInfo).toList();
        return new VersionListRsp().setVersionList(versionInfoList).setCount(versionInfoList.size());
    }

    /**
     * 自定义节点是否达到最大数量限制
     *
     * @return true:已达到，false:未达到
     */
    public boolean isExceedMaxCustomizeNodeNum() {
        int customizeToolNodeCount =
            toolMapper.selectCustomizeNodeCountByProjectId(opSvcProjectId, RequestContextUtils.getRequestWorkspaceId());
        int customizeWorkflowNodeCount = workflowMapper.selectCustomizeNodeCountByProjectId(opSvcProjectId,
            RequestContextUtils.getRequestWorkspaceId());

        return customizeWorkflowNodeCount + customizeToolNodeCount >= maxCustomizeNodeSize;
    }

    /**
     * 发布为自定义节点校验
     *
     * @param projectId projectId
     * @param id 插件/工作流id
     * @param lastVersionId 最新版本
     * @param customizeNode 是否是设置自定义节点，1表示是自定义节点,0或空表示不是
     */
    public void publishCustomizeNodeCheck(String projectId, String id, String lastVersionId, Integer customizeNode) {
        // 只有op账号可以发布或取消发布自定义节点
        if (!opSvcProjectId.equals(projectId)) {
            log.error("projectId:{} don not have permission to publish or unpublish customize node", projectId);
            throw new AgentStudioException(StudioError.NO_PERMISSION_PUBLISH_CUSTOMIZE_NODE, projectId);
        }

        // 没有发布的插件/工作流不能设置为自定义节点
        if (StringUtils.isBlank(lastVersionId)) {
            log.error("tool or workflow: {} not be published and can not be set as a customize node", id);
            throw new AgentStudioException(StudioError.PUBLISH_CUSTOMIZE_NODE_ERROR);
        }

        // 自定义节点数量超过最大限制
        if (Objects.equals(customizeNode, 1) && isExceedMaxCustomizeNodeNum()) {
            log.error("The number of custom nodes exceeds the maximum limit.");
            throw new AgentStudioException(StudioError.CUSTOMIZE_NODE_NUMBER_EXCEED_LIMIT);
        }
    }

    /**
     * 构造模型调用请求体
     *
     * @param modelDeploymentId string
     * @param modelType 模型类型
     * @param model string
     * @param config 模型超参数
     * @param query 提问语句
     * @return 请求体
     */
    public AskModelReq buildAskModelReq(String modelDeploymentId, String modelType, String model, ModelConfig config,
        String query) {
        // 构建消息列表
        List<Message> messages =
            new ArrayList<>(Collections.singletonList(new Message().setRole(CommonConstant.USER).setContent(query)));

        // 构建超参数
        ModelConfig hyperParameters = new ModelConfig().setTopP(config == null ? 0.5 : config.getTopP())
            .setTemperature(config == null ? 0.5 : config.getTemperature());

        // 构建模型信息
        ModelInfo modelInfo = ModelInfo.builder()
            .modelName(modelDeploymentId + (StringUtils.isEmpty(model) ? "" : "|" + model))
            .modelType(Optional.ofNullable(modelType).orElse(CommonConstant.AGENT_BUILDER_MODEL_TYPE))
            .hyperParameters(hyperParameters)
            .build();

        // 设置模型配置路径（如果环境是POC）
        if (CommonConstant.EnvType.SIMPLE.equals(envType)) {
            modelInfo.setModelConfigPath(
                String.format("%s/%s/%s.json", modelObsPrefix, CommonConstant.Workflow.IR, modelDeploymentId));
        }

        // 构建并返回请求参数
        return AskModelReq.builder()
            .modelName(modelInfo.getModelName())
            .isStream(false)
            .messages(messages)
            .maxTokens(hyperParameters.getMaxTokens())
            .temperature(hyperParameters.getTemperature())
            .topP(hyperParameters.getTopP())
            .presencePenalty(0)
            .contentSecurityVerify(
                AskModelReq.ContentSecurityVerify.builder().isResponseVerify(false).isRequestVerify(false).build())
            .frequencyPenalty(hyperParameters.getFrequencyPenalty() != null ? hyperParameters.getFrequencyPenalty() : 0) // 默认频率惩罚
            .build();
    }

    /**
     * 校验插件权限
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param toolIds toolIds
     */
    public void validTools(String projectId, String workspaceId, List<String> toolIds) {
        if (CollectionUtils.isEmpty(toolIds)) {
            return;
        }
        pluginService.validTools(projectId, workspaceId, toolIds);
    }

    /**
     * 处理mapping表，将数据迁移到mapping历史表，删除mapping原有数据
     * @param appId app的资源ID
     */
    public void softDeleteMapping(String appId) {
        List<MappingEntity> mappingList = mappingMapper.selectAllByAppId(appId);
        List<HistoryMappingEntity> historyMappingList = new ArrayList<>();
        mappingList.forEach(mappingEntity -> {
            HistoryMappingEntity historyMapping = new HistoryMappingEntity();
            BeanUtils.copyProperties(mappingEntity, historyMapping);
            historyMapping.setHistoryId(UuidUtils.getUUID());
            historyMappingList.add(historyMapping);
        });
        if (!historyMappingList.isEmpty()) {
            historyMappingMapper.insertBatch(historyMappingList);
        }
        mappingMapper.deleteBatchByAppId(appId, null, true);
    }

    /**
     * 处理Agent版本表，迁移到新的表，旧数据删除(appId批量处理)
     * @param appId app的资源ID
     */
    public void softDeleteReleaseVersionByAppId(String appId) {
        List<ReleaseVersion> releaseVersions = releaseVersionMapper.selectByAppId(appId);
        List<HistoryReleaseVersionEntity> historyReleaseVersions = new ArrayList<>();
        releaseVersions.forEach(releaseVersion -> {
            HistoryReleaseVersionEntity existingHistory
                    = historyReleaseVersionMapper.findByAppIdAndVersionId(releaseVersion.getAppId(), releaseVersion.getVersionId());
            // 防止重复导入资源时，由于id与version相同而导致失败
            if (existingHistory == null) {
                HistoryReleaseVersionEntity historyReleaseVersionEntity = new HistoryReleaseVersionEntity();
                BeanUtils.copyProperties(releaseVersion, historyReleaseVersionEntity);
                historyReleaseVersionEntity.setHistoryId(UuidUtils.getUUID());
                historyReleaseVersions.add(historyReleaseVersionEntity);
            }
        });
        if (!historyReleaseVersions.isEmpty()) {
            historyReleaseVersionMapper.insertBatch(historyReleaseVersions);
        }

        releaseVersionMapper.deleteByAppId(appId);
    }

    /**
     * 处理Agent版本表，迁移到新的表，旧数据删除(通过ID单点处理)
     * @param releaseVersion 版本详情
     */
    public void softDeleteReleaseVersionById(ReleaseVersion releaseVersion) {
        HistoryReleaseVersionEntity historyReleaseVersion = new HistoryReleaseVersionEntity();
        BeanUtils.copyProperties(releaseVersion, historyReleaseVersion);
        historyReleaseVersion.setHistoryId(UUID.randomUUID().toString());
        historyReleaseVersionMapper.insert(historyReleaseVersion);
        releaseVersionMapper.deleteByPrimaryKey(releaseVersion.getId());
    }

    /**
     * 处理Agent资源表，迁移到新的表，旧数据删除
     * @param projectId 项目ID
     * @param agentId agent资源ID
     */
    public void softDeleteAgent(String projectId, String agentId) {
        Agent agent = agentMapper.selectByPrimaryKey(projectId, agentId);
        if (agent == null) {
            log.warn("agent does not exist, skip soft delete, projectId = {}, agentId = {}", projectId, agentId);
            return;
        }
        HistoryAgentEntity historyAgent = new HistoryAgentEntity();
        BeanUtils.copyProperties(agent, historyAgent);
        historyAgent.setHistoryId(UuidUtils.getUUID());
        historyAgent.setDeleted(0);
        historyAgentMapper.insert(historyAgent);
        agentMapper.deleteByPrimaryKey(agentId, projectId);
    }

    public Map<String, Object> parseMetadata(Agent agent) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("projectId", agent.getProjectId());
        metadata.put("workspaceId", agent.getWorkspaceId());
        metadata.put("updatedAt", agent.getUpdatedOn());
        metadata.put("memoryVariables", agent.getMemoryVariables());
        metadata.put("triggerConfigs", agent.getTriggerList());
        return metadata;
    }

    /**
     * 判断导入文件是否V2版本
     * @param file
     * @return
     */
    public boolean isExportFileV2(MultipartFile file) {
        try (BufferedReader bufferedReader = new BufferedReader(
            new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            // 逐行读取文件中的jsonl配置
            while (StringUtils.isNotEmpty(line = bufferedReader.readLine())) {
                Map<String, Object> jsonMap = jacksonObjectMapper.readValue(line, new TypeReference<>() {});
                if (jsonMap.get("schema_version") != null) {
                    return true;
                }
            }
        } catch (Exception e) {
            log.error("Failed to import the Agent ,", e);
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        return false;
    }

    public AgentInfo buildComplexAgentInfo(Agent agent) {
        // deepresearch模式
        if (StringUtils.isNotBlank(agent.getDslPath()) && CommonConstant.DEEPRESEARCH_TYPE.equals(agent.getSubType())) {
            // 如果有dsl 直接从dsl返回
            String agentJson = mgObsService.downloadObsFile(agent.getDslPath());
            return JSON.parseObject(agentJson, AgentInfo.class).setUpdateTime(agent.getUpdatedOn()).setPublishTime(agent.getPublishedOn());
        }

        AgentInfo agentInfo = agent.convertToDto();
        // 查询assistant关联的tool信息
        List<ToolReference> tools = relationManagementService.listAgentTools(agent.getProjectId(),
            agent.getWorkspaceId(), agent.getAgentId(), 0, 20);

        agentInfo.setTools(tools);

        // 查询agent关联的Mcp server信息
        List<McpServerReference> mcpReferences = relationManagementService.listAgentMcpServers(agent.getAgentId());
        agentInfo.setMcpServers(mcpReferences);

        // 查询agent关联的skill信息
        List<SkillReference> skillReferences = relationManagementService.listAgentSkills(agent.getAgentId());
        agentInfo.setSkills(skillReferences);
        // 自主动态规划模式
        if (StringUtils.isNotBlank(agent.getDslPath()) && CommonConstant.PLANEXECUTE_TYPE.equals(agent.getSubType())) {
            String agentJson = mgObsService.downloadObsFile(agent.getDslPath());
            AgentInfo agentInfoFromDSL = JSON.parseObject(agentJson, AgentInfo.class).setUpdateTime(agent.getUpdatedOn()).setPublishTime(agent.getPublishedOn());

            // 解决导入后空间内无插件和MCP问题
            // 计算当前工具和MCP数量
            int toolAndMCPCount = tools.size() + mcpReferences.size();
            // 计算DSL中工具和MCP数量
            int toolAndMCPCountFromDSL = (agentInfoFromDSL.getTools() != null ? agentInfoFromDSL.getTools().size() : 0)
                + (agentInfoFromDSL.getMcpServers() != null ? agentInfoFromDSL.getMcpServers().size() : 0);

            // 如果数量不相等，更新DSL中的工具和MCP信息
            if (toolAndMCPCount != toolAndMCPCountFromDSL) {
                agentInfoFromDSL.setTools(tools);
                agentInfoFromDSL.setMcpServers(mcpReferences);
            }
            return agentInfoFromDSL;
        }

        // 查询assistant关联的知识库信息
        KnowledgeRepoListRsp knowledgeRepoListRsp = relationManagementService.listAgentKnowledge(agent.getProjectId(),
            agent.getWorkspaceId(), agent.getAgentId(), 0, 20);
        List<KnowledgeRepoReference> knowledgeRepos = new ArrayList<>();
        for (KnowledgeRepoEntity knowledgeRepo : knowledgeRepoListRsp.getKnowledgeRepoEntityList()) {
            KnowledgeRepoReference knowledgeRepoReference = new KnowledgeRepoReference();
            knowledgeRepoReference.setKnowledgeRepoId(knowledgeRepo.getKnowledgeRepoId());
            knowledgeRepoReference.setKnowledgeRepoName(knowledgeRepo.getDisplayName());
            knowledgeRepoReference.setKnowledgeRepoIcon(knowledgeRepo.getIcon());
            knowledgeRepoReference.setStatus(knowledgeRepo.getStatus());
            knowledgeRepoReference.setDesc(knowledgeRepo.getDesc());
            knowledgeRepos.add(knowledgeRepoReference);
        }
        agentInfo.setKnowledgeRepos(knowledgeRepos);

        // 查询agent关联的工作流信息
        List<WorkflowEntity> workflowMappingList = relationManagementService.listAgentWorkflows(agent.getProjectId(),
            agent.getWorkspaceId(), agent.getAgentId());
        Map<String, WorkflowInfoRefWorkflows> wfsLastVersion = getRefWfLastVersion(
            workflowMappingList);
        // 查询关联的工作流资源参数信息
        List<MappingEntity> agentWorkflows = mappingMapper.selectByAppIdAndResourceType(agent.getAgentId(),
            CommonConstant.WORKFLOW_TYPE);
        Map<String, String> resourceParameters = new HashMap<>();
        if (!CollectionUtils.isEmpty(agentWorkflows)) {
            resourceParameters = agentWorkflows.stream()
                .filter(agentWorkflow -> agentWorkflow.getExtendInfo() != null)
                .collect(Collectors.toMap(MappingEntity::getResourceId, MappingEntity::getExtendInfo));
        }
        List<WorkflowReference> workflowReferences = new ArrayList<>();
        for (WorkflowEntity workflowEntity : workflowMappingList) {
            WorkflowReference workflowReference = new WorkflowReference();
            workflowReference.setWorkflowId(workflowEntity.getId());
            workflowReference.setWorkflowName(workflowEntity.getName());
            workflowReference.setCode(workflowEntity.getCode());
            workflowReference.setWorkflowIcon(workflowEntity.getAvatar());
            workflowReference.setDesc(workflowEntity.getDescription());
            if (resourceParameters.get(workflowEntity.getId()) != null) {
                workflowReference.setWorkflowParameter(resourceParameters.get(workflowEntity.getId()));
            }
            if (wfsLastVersion.get(workflowEntity.getId()) != null) {
                workflowReference.setLastVersionId(wfsLastVersion.get(workflowEntity.getId()).getLastVersionId());
                workflowReference.setLastVersionName(wfsLastVersion.get(workflowEntity.getId()).getLastVersionName());
            }
            workflowReferences.add(workflowReference);
        }
        agentInfo.setWorkflows(workflowReferences);

        // 设置controller details
        if (!StringUtils.isEmpty(agent.getDslPath())) {
            String controllerJson = mgObsService.downloadObsFile(agent.getDslPath());
            agentInfo.setDetails(JSONObject.parseObject(controllerJson, ControllerVO.class));
        }
        // 关联模型service_name
        ModelServiceBase modelServiceBase = modelServiceMapper.queryById(agent.getModelDeploymentId());
        if (modelServiceBase == null) {
            ModelServiceCondition condition = new ModelServiceCondition();
            condition.setId(agent.getModelDeploymentId());
            List<ModelServiceData> freeModels = freeModelServiceMapper.queryAllFreeModels(condition);
            if (CollectionUtils.isNotEmpty(freeModels)) {
                agentInfo.setServiceName(freeModels.get(0).getServiceName());
            } else {
                agentInfo.setServiceName(agentInfo.getModelName());
            }
        } else {
            agentInfo.setServiceName(modelServiceBase.getServiceName());
        }

        return agentInfo;
    }
}
