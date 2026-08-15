/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.common.enums.NodeType.PLUGIN;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.Workflow.MODEL;
import static com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum.WORKFLOW;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SignatureUtils;
import com.openjiuwen.studio.agent.common.utils.ThreadLocalUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.bo.WfImportDataWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.ControllerIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOAgents;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOGlobalIntents;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeConfigVOWorkflows;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.ExportAgent;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.ExportWorkflow;
import com.openjiuwen.studio.agent.manager.dto.ExtraMsg;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.common.dto.ImportRes;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.common.dto.agent.ListWorkflowsQo;
import com.openjiuwen.studio.agent.manager.dto.McpServerInfo;
import com.openjiuwen.studio.agent.manager.dto.McpServerReference;
import com.openjiuwen.studio.agent.manager.dto.ModelConfigVO;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderReq;
import com.openjiuwen.studio.agent.manager.dto.ParamExtractionDomainObject;
import com.openjiuwen.studio.agent.manager.dto.ParamExtractionWorkflow;
import com.openjiuwen.studio.agent.manager.dto.Scene;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.dto.ShareInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.AgentExportEntity;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.SkillEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolExportEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowExportEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.AgentType;
import com.openjiuwen.studio.agent.manager.enums.ImportResourceType;
import com.openjiuwen.studio.agent.manager.enums.ModelTypeV2;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentMode;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentNodeType;
import com.openjiuwen.studio.agent.manager.enums.controller.IntentHandlerType;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthMetadataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.UserModelServiceProviderMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.mcp.IMcpInnerService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceMgmtService;
import com.openjiuwen.studio.agent.manager.service.md.ProviderAuthService;
import com.openjiuwen.studio.agent.manager.service.md.ProviderMgmtService;
import com.openjiuwen.studio.agent.manager.service.md.RouterStrategyMgmtService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt.WorkflowNodeAdapter;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.Nullable;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Service
@Slf4j
public class AgentImportExportService {
    /**
     * dsl id
     */
    private static final String WORKFLOW_ID = "workflow_id";

    private static final String AGENT_OBS_PATH_TEMPLATE = "%s/%s/%s/%s.json";

    /**
     * 名称冲突时变更模板
     */
    private static final String NAME_FORMAT = "%s_%s";

    private static final String AGENT_NAME_REGEX =
        "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!](?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!])?$";

    private static final Pattern AGENT_NAME_PATTERN = Pattern.compile(AGENT_NAME_REGEX);

    /**
     * 领域对象
     */
    private static final String DOMAIN_OBJECTS = "domain_objects";

    /**
     * 拓展工作流
     */
    private static final String EXTENSION_WORKFLOWS = "extension_workflows";

    /**
     * FunctionGraph
     */
    private static final String EXEC_ENV = "exec_env";

    private static final String FG_ID = "fg_id";

    private static final String FG = "fg";

    private final List<String> supportTypes =
        Arrays.asList(ModelTypeV2.LLM.toString(), ModelTypeV2.IMAGE_TO_TEXT.toString());

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private WorkflowCommonService workflowCommonService;

    @Autowired
    private EncryptionAdapter encryptionAdapter;

    @Autowired
    private ToolMapper toolMapperDiscard;

    @Autowired
    private ProviderAuthMetadataMapper providerAuthMetadataMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private IMcpInnerService mcpInnerService;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private IrAdapterService irAdapterService;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private RelationManagementService relationManagementService;

    @Autowired
    private WorkflowManagementService workflowManagementService;

    @Autowired
    private AgentCommonService agentCommonService;

    @Autowired
    private ControllerManagementService controllerManagementService;

    @Autowired
    private ModelServiceMgmtService modelServiceMgmtService;

    @Autowired
    private RouterStrategyMgmtService routerStrategyMgmtService;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private UserModelServiceProviderMapper userProviderMapper;


    @Autowired
    private SkuManageService skuManageService;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ProviderAuthService authService;

    @Autowired
    private ProviderMgmtService providerMgmtService;

    @Autowired
    private FreeModelServiceMapper freeModelServiceMapper;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private EnvironmentServiceManagerService environmentServiceManagerService;

    @Autowired
    private ShareInnerService shareInnerService;

    @Autowired
    private SignatureUtils signatureUtils;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${export.max-length}")
    private int importMaxLen;

    @Value("${model.default-model-api-url}")
    private String defaultImportModelApi;

    @Value("${tool.default-icon}")
    private String defaultImportModelIcon;

    @Value("${import.model.enable:true}")
    private boolean importModelEnable;

    @Value("${front-page.block-nodes}")
    private String blockNodes;

    @Autowired
    private IPlugin pluginAdapterImpl;

    @Autowired
    private PluginMapper pluginMapper;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Autowired
    private PluginBaseImpl pluginBaseImpl;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private SkillMapper skillMapper;

    /**
     * workflow导入
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @param importWorkflows 需要导入的工作流id列表
     * @param importTools 需要导入的插件id列表
     * @param targetWorkspaceId 空间id
     * @return ImportRsp 导入请求的响应，包括id、name、description、status和dependencies（工作流的依赖）
     */
    public ImportRsp importWorkflows(String projectId, String targetWorkspaceId, MultipartFile file,
        String importWorkflows, String importTools) {
        ImportRsp importRsp = new ImportRsp();
        WfImportDataWrapper wfImportDataWrapper = new WfImportDataWrapper();
        List<String> importWorkflowList = StringUtils.isEmpty(importWorkflows) ? new ArrayList<>() : new ArrayList<>(Arrays.asList(importWorkflows.split(",")));
        List<String> importToolList = StringUtils.isEmpty(importTools) ? new ArrayList<>() : new ArrayList<>(Arrays.asList(importTools.split(",")));
        wfImportDataWrapper.setImportWorkflowList(importWorkflowList);
        wfImportDataWrapper.setImportToolList(importToolList);

        skuManageService.validateImportAppCountExceededLimitOrNot(null, importWorkflowList, targetWorkspaceId);

        try (BufferedReader bufferedReader =
            new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;

            // 逐行读取导入文件中的jsonl
            while ((line = bufferedReader.readLine()) != null) {
                WorkflowExportEntity workflowExportEntity =
                    jacksonObjectMapper.readValue(line, new TypeReference<>() {});
                String id = workflowExportEntity.getMetadata().getId();

                // 如果环境中是否已存在该工作流配置，且用户不选择覆盖，则continue
                if (!importWorkflowList.contains(id)) {
                    continue;
                }

                // 签名验证
                String signature = workflowExportEntity.getSignature();
                workflowExportEntity.setSignature(null);
                signatureUtils.verifySignature(jacksonObjectMapper.writeValueAsString(workflowExportEntity), signature);

                // 导入工作流及关联资源
                importWorkflow(projectId, targetWorkspaceId, id, workflowExportEntity, wfImportDataWrapper);
            }
            buildImportRsp(importRsp, wfImportDataWrapper);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to import the workflow.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_IMPORT_FILE);
        }
        return importRsp;
    }

    public void importWorkflowsWithStr(String projectId, String targetWorkspaceId, String workflowStr,
        List<ImportListInfo> importListInfoList) {
        WfImportDataWrapper importDataWrapper = new WfImportDataWrapper();
        resolveDependency(importDataWrapper, importListInfoList);
        skuManageService.validateImportAppCountExceededLimitOrNot(importDataWrapper.getImportAgentList(),
            importDataWrapper.getImportWorkflowList(), targetWorkspaceId);
        try {
            WorkflowExportEntity workflowExportEntity =
                jacksonObjectMapper.readValue(workflowStr, new TypeReference<>() {});
            String id = workflowExportEntity.getMetadata().getId();
            importWorkflow(projectId, targetWorkspaceId, id, workflowExportEntity, importDataWrapper);
        } catch (Exception e) {
            log.error("Failed to import the workflow.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_IMPORT_FILE);
        }
    }

    public List<ModelServiceData> getValidatedModels(String projectId, String workspaceId, List<String> modelIds) {
        if (CollectionUtils.isEmpty(modelIds)) {
            log.warn("No found modelIds: {}", modelIds);
            return Collections.emptyList();
        }
        List<ModelServiceData> models = modelServiceMapper.queryByIds(modelIds, projectId, workspaceId);
        if (CollectionUtils.isEmpty(models)) {
            log.warn("Models not found for Ids: {}", modelIds);
            return Collections.emptyList();
        }
        return models;
    }

    public Map<String, ProviderAuthMetadata> batchGetAndValidateProviders(String projectId, String workspaceId, List<ModelServiceData> models) {

        Set<String> providerIds = models.stream()
            .map(ModelServiceData::getProviderId)
            .filter(StringUtils::isNotBlank)
            .collect(Collectors.toSet());
        if (providerIds.isEmpty()) {
            return Collections.emptyMap();
        }

        List<ProviderAuthMetadata> providers = providerAuthMetadataMapper.selectByIds(providerIds);
        return providers.stream()
            .filter(p -> p != null)
            .collect(Collectors.toMap(ProviderAuthMetadata::getProviderId, p -> p, (existing, replacement) -> existing));
    }

    private void validModelPermissions(String projectId, String workspaceId, List<String> modelIds) {

        List<ModelServiceData> modelList = modelServiceMapper.queryByIds(modelIds, projectId, workspaceId);
        if (CollectionUtils.isEmpty(modelList)) {
            log.error("Model validation failed: No models found for the given IDs in Project: {}, Workspace: {}. Model IDs: {}",
                projectId, workspaceId, modelIds);
            throw new AgentStudioException(StudioError.MODEL_NOT_EXIST, String.join(",", modelIds));
        }
        List<String> validModelIds = modelList.stream()
            .map(ModelServiceData::getId)
            .toList();
        List<String> invalidModelIds = modelIds.stream()
            .filter(id -> !validModelIds.contains(id))
            .toList();
        if (CollectionUtils.isNotEmpty(invalidModelIds)) {
            log.error("Permission denied for model IDs: {}", invalidModelIds);
             throw new AgentStudioException(StudioError.MODEL_NOT_EXIST,
                 String.join(",", invalidModelIds));
        }
    }


    public Resource exportAgents(String projectId, String workspaceId, ExportParams body) {
        Map<String, String> exportVersionMap = Optional.ofNullable(body.getAgents())
            .orElse(Collections.emptyList())
            .stream()
            .collect(Collectors.toMap(ExportAgent::getAgentId, ExportAgent::getAgentVersion, (v1, v2) -> v2));

        List<String> agentIds = getAgentIdList(body);

        AgentExportEntity agentExportEntity = new AgentExportEntity();
        // 判断是否超出最大导出数量限制
        if (agentIds.size() > importMaxLen) {
            log.error("Exceeded the maximum export limit. The maximum number of exports is {}.", importMaxLen);
            throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE, importMaxLen);
        }

        validAgent(projectId, workspaceId, agentIds);

        StringBuilder tempJson = new StringBuilder();
        try {
            for (String agentId : agentIds) {

                // 设置导出json中的Agent元数据
                Agent metadata = agentMapper.selectByPrimaryKey(projectId, agentId);
                agentExportEntity.setMetadata(metadata);

                String type = Optional.ofNullable(metadata.getType()).orElse(CommonConstant.AGENT);

                String exportAgentVersion = exportVersionMap.get(agentId);
                if (AgentType.CONTROLLER.getValue().equalsIgnoreCase(type)) {
                    // 多Agent导出
                    agentExportEntity = mergeAgents(projectId, workspaceId, metadata, exportAgentVersion);
                } else {
                    // 单Agent导出
                    handleSingleAgent(projectId, workspaceId, agentId, agentExportEntity, exportAgentVersion);
                }
                agentExportEntity.setImportType(CommonConstant.AGENT);

                // 签名
                agentExportEntity.setSignature(signatureUtils.signature(jacksonObjectMapper.writeValueAsString(
                    agentExportEntity)));
                tempJson.append(jacksonObjectMapper.writeValueAsString(agentExportEntity)).append("\n");
            }
            byte[] bytes = tempJson.toString().getBytes(StandardCharsets.UTF_8);

            // 处理响应体
            ResponseModel.TransferResource resource =
                new ResponseModel.TransferResource(new ByteArrayInputStream(bytes));
            resource.setFilename("agents.jsonl");
            resource.setLength((long) bytes.length);
            return resource;
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to export the agent.", e);
            throw new AgentStudioException(StudioError.AGENT_EXPORT_FILE);
        }
    }

    /**
     * 计算资源引用了哪些共享的资源
     *
     * @param appId 引用方ID
     * @return 引用的共享资源列表
     */
    private List<MappingEntity> buildMappingEntityList(String appId, String appVersion) {
        if (StringUtils.isEmpty(appVersion)) {
            appVersion = Constants.LATEST_PUBLISH_VERSION;
        }
        return mappingMapper.selectByAppIdAndAppVersion(appId, appVersion, null, null)
            .stream()
            .filter(mappingEntity -> ReferenceTypeEnum.SHARE.getValue().equals(mappingEntity.getReferenceType()))
            .toList();
    }

    private void validAgent(String projectId, String workspaceId, List<String> agentIds) {
        List<Agent> agentList = agentMapper.selectByIdsAndProjectIdAndWorkspaceId(projectId, workspaceId, agentIds);
        if (CollectionUtils.isEmpty(agentList)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST_OR_NO_PERMISSION, String.join(",", agentIds));
        }
        List<String> exportAgentIds = agentList.stream().map(Agent::getAgentId).toList();
        List<String> cannotExportAgentIds = new ArrayList<>();
        agentIds.forEach(agentId -> {
            if (!exportAgentIds.contains(agentId)) {
                cannotExportAgentIds.add(agentId);
            }
        });
        if (CollectionUtils.isNotEmpty(cannotExportAgentIds)) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST_OR_NO_PERMISSION,
                String.join(",", cannotExportAgentIds));
        }
    }

    public String exportAgentStr(String projectId, String workspaceId, String agentId) {
        AgentExportEntity agentExportEntity = new AgentExportEntity();
        StringBuilder tempJson = new StringBuilder();
        Agent metadata = agentMapper.selectByPrimaryKey(projectId, agentId);
        if (metadata == null) {
            return tempJson.toString();
        }
        agentExportEntity.setMetadata(metadata);
        String type = Optional.ofNullable(metadata.getType()).orElse(CommonConstant.AGENT);
        if (AgentType.CONTROLLER.getValue().equalsIgnoreCase(type)) {
            // 多Agent导出
            agentExportEntity = mergeAgents(projectId, workspaceId, metadata, null);
        } else {
            // 单Agent导出
            handleSingleAgent(projectId, workspaceId, agentId, agentExportEntity, null);
        }
        agentExportEntity.setImportType(CommonConstant.AGENT);
        try {
            tempJson.append(jacksonObjectMapper.writeValueAsString(agentExportEntity)).append("\n");
        } catch (Exception e) {
            log.error("Failed to export the agent.", e);
            throw new AgentStudioException(StudioError.AGENT_EXPORT_FILE);
        }
        return tempJson.toString();
    }

    /**
     * 单Agent导出
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param agentExportEntity 导出对象定义
     */
    private void handleSingleAgent(String projectId, String workspaceId, String agentId,
        AgentExportEntity agentExportEntity, String exportVersion) {
        // 导出agent依赖的场景Scenes
        Agent agent = agentExportEntity.getMetadata();
        if (agent != null && CommonConstant.PLANEXECUTE_TYPE.equals(agent.getSubType())) {
            // Scene定义放在了dsl中
            String agentDslJson = mgObsService.downloadObsFile(agentExportEntity.getMetadata().getDslPath());
            AgentInfo agentInfo = JSON.parseObject(agentDslJson, AgentInfo.class);
            agentExportEntity.setScenes(agentInfo.getScenes());
        }

        // 从agent和tool的关系映射表中查询当前Agent依赖的插件
        List<MappingEntity> mappingAgentTools =
            mappingMapper.selectByAppIdAndResourceType(agentId, CommonConstant.TOOL_TYPE);
        List<ToolEntity> plugins = getMappingToolsWithVersion(projectId, mappingAgentTools);
        plugins.forEach(plugin -> {
            // 预置插件屏蔽url信息
            if (Strings.CI.equals(ToolType.INNER.type, plugin.getType())) {
                plugin.getRequestInfo().setUrl(null);
            }
        });

        // 从关系映射表中查询当前Agent依赖的工作流
        if (StringUtils.isBlank(exportVersion)) {
            exportVersion = "latest";
        }
        List<MappingEntity> agentWorkflowMappingEntityList =
            mappingMapper.selectByAppIdAndAppVersion(agentId, exportVersion, CommonConstant.WORKFLOW_TYPE, true);

        Map<String, MappingEntity> workflowMap = agentWorkflowMappingEntityList.stream()
            .collect(Collectors.toMap(MappingEntity::getResourceId, entity -> entity));

        List<String> workflowIds =
            agentWorkflowMappingEntityList.stream().map(MappingEntity::getResourceId).distinct().toList();
        List<WorkflowEntity> workflows = workflowMapper.selectByWorkflowIds(projectId, workspaceId, workflowIds);
        List<WorkflowExportEntity> workflowExportEntities = new ArrayList<>();
        for (WorkflowEntity workflow : workflows) {
            MappingEntity mappingEntity = workflowMap.get(workflow.getId());
            workflowExportEntities.add(
                mergeWorkflow(projectId, workflow, mappingEntity != null ? mappingEntity.getResourceVersion() : null));
        }

        // 从关系映射表中查询当前Agent依赖的mcp server
        List<McpServerReference> mcpServerReferences = relationManagementService.listAgentMcpServers(agentId);
        List<String> validMcpServerIds = mcpServerReferences.stream()
            .filter(McpServerReference::isValid)
            .map(McpServerReference::getMcpServerId)
            .distinct()
            .toList();
        List<McpServerInfo> mcpServers = mcpInnerService.getMcpServerInfoByIds(workspaceId, validMcpServerIds);
        // 解密serviceConfig
        if (CollectionUtils.isNotEmpty(mcpServers)) {
            mcpServers.forEach(this::decryptMcpServiceConfig);
        }

        // 查询当前Agent依赖的skill
        List<MappingEntity> mappingAgentSkills = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.SKILL_TYPE);
        List<String> mappingAgentSkillsIds = mappingAgentSkills.stream().map(MappingEntity::getResourceId).toList();
        List<SkillDetails> skills = skillMapper.searchBySkillIds(mappingAgentSkillsIds);
        skills.forEach(skill -> {
            skill.setObsPath(null);
        });

        // 设置Agent导出对象各字段值
        agentExportEntity.setPlugins(plugins);
        agentExportEntity.setWorkflows(workflowExportEntities);
        agentExportEntity.setMcpServers(mcpServers);
        agentExportEntity.setSkills(skills);
    }

    private void buildMcpShareInfo(List<McpServerInfo> mcpServers) {
        for (McpServerInfo mcpServerInfo : mcpServers) {
            com.openjiuwen.studio.agent.manager.entity.ShareInfo sourceShareInfo
                = shareResourceManagerService.exportShareInfo(mcpServerInfo.getServerId());
            if (sourceShareInfo != null) {
                if (mcpServerInfo.getShareInfo() == null) {
                    mcpServerInfo.setShareInfo(new ShareInfo());
                }
                BeanUtils.copyProperties(sourceShareInfo, mcpServerInfo.getShareInfo());
            }
            mcpServerInfo.setShareReference(new ArrayList<>());
            buildMappingEntityList(mcpServerInfo.getServerId(), null).forEach(mappingEntity -> {
                com.openjiuwen.studio.agent.manager.dto.MappingEntity mappingEntity1
                    = new com.openjiuwen.studio.agent.manager.dto.MappingEntity();
                BeanUtils.copyProperties(mappingEntity, mappingEntity1);
                mcpServerInfo.getShareReference().add(mappingEntity1);
            });
        }
    }

    /**
     * 多Agent导出
     *
     * @param projectId projectId
     * @param controllerVo 节点信息
     * @param agentExportEntity 导出对象定义
     */
    private void handleMultiAgent(String projectId, String workspaceId, ControllerVO controllerVo,
        AgentExportEntity agentExportEntity) {
        agentExportEntity.setAgents(new ArrayList<>());
        List<WorkflowExportEntity> workflowExportEntityList = new ArrayList<>();
        List<AgentExportEntity> agents = new ArrayList<>();
        List<AgentExportEntity> singleAgents = new ArrayList<>();

        // 节点根据type和id分组
        Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId =
            controllerManagementService.groupDslNodes(controllerVo);
        ControllerNodeVO controllerNode = controllerManagementService.getControllerNode(nodesGroupByTypeId);

        // controller node config 不能为空
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassRef(controllerNode.getConfigs(), new TypeReference<>() {});

        // 获取主控制器绑定的工作流
        List<ControllerNodeConfigVOWorkflows> workflowNodeConfigs = null;
        if (controllerNodeConfigVo != null) {
            workflowNodeConfigs = controllerNodeConfigVo.getWorkflows();
        }
        if (!CollectionUtils.isEmpty(workflowNodeConfigs)) {
            Map<String, ControllerNodeVO> workflowNodeMap = nodesGroupByTypeId
                .get(AgentNodeType.WORKFLOW.getType());
            workflowNodeConfigs.forEach(workflowNodeConfig -> {
                ControllerNodeVO workflowNode = workflowNodeMap.get(workflowNodeConfig.getNodeId());
                exportControllerWorkflow(workflowExportEntityList, workflowNode, projectId);
            });
        }
        // 获取主控制器绑定的意图控制器
        exportGlobalIntentWorkflows(workflowExportEntityList, controllerNode, projectId);

        // 获取主控制器绑定的控制器
        List<ControllerNodeConfigVOAgents> agentNodeConfigs = null;
        if (controllerNodeConfigVo != null) {
            agentNodeConfigs = Optional.ofNullable(controllerNodeConfigVo.getAgents())
                    .orElseGet(Collections::emptyList)
                    .stream()
                    .filter(agent -> AgentMode.CONTROLLER.getMode().equals(agent.getMode()))
                    .collect(Collectors.toList());
        }
        if (!CollectionUtils.isEmpty(agentNodeConfigs)) {
            Map<String, ControllerNodeVO> controllerNodeMap = nodesGroupByTypeId
                .get(AgentNodeType.SUB_CONTROLLER.getType());
            agentNodeConfigs.forEach(agentNodeConfig -> {
                ControllerNodeVO agentNode = controllerNodeMap.get(agentNodeConfig.getNodeId());
                exportController(agents, workspaceId, agentNode, projectId);
            });
        }

        // 获取主控制器绑定的单智能体
        List<ControllerNodeConfigVOAgents> singleAgentNodeConfigs = null;
        if (controllerNodeConfigVo != null) {
            singleAgentNodeConfigs = Optional.ofNullable(controllerNodeConfigVo.getAgents())
                    .orElseGet(Collections::emptyList)
                    .stream()
                    .filter(agent -> AgentMode.PLANEXECUTE.getMode().equals(agent.getMode()))
                    .collect(Collectors.toList());
        }
        if (!CollectionUtils.isEmpty(singleAgentNodeConfigs)) {
            Map<String, ControllerNodeVO> agentNodeMap = nodesGroupByTypeId
                    .get(AgentNodeType.AGENT.getType());
            singleAgentNodeConfigs.forEach(agentNodeConfig -> {
                ControllerNodeVO agentNode = agentNodeMap.get(agentNodeConfig.getNodeId());
                exportSingleAgent(singleAgents, workspaceId, agentNode, projectId);
            });
        }
        agentExportEntity.setAgents(agents);
        agentExportEntity.setSingleAgents(singleAgents);
        agentExportEntity.setWorkflows(workflowExportEntityList);
    }

    /**
     * 合并控制器的DSL、Metadata和依赖的工作流和子控制器
     *
     * @param projectId projectId
     * @param agent 该控制器元数据
     * @return WorkflowExportEntity 合并后的控制器配置对象
     */
    private AgentExportEntity mergeAgents(String projectId, String workspaceId, Agent agent, String versionId) {
        // 构建工作流导出对象
        AgentExportEntity agentExportEntity;

        if (StringUtils.isEmpty(versionId)) {
            agentExportEntity = buildAgentExportEntity(projectId, workspaceId, agent, null);
        } else {
            agentExportEntity = buildAgentExportEntity(projectId, workspaceId, agent, versionId);
            ReleaseVersion releaseVersion =
                releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(), versionId);
            agentExportEntity.setReleaseVersion(releaseVersion);
        }
        return agentExportEntity;
    }

    private AgentExportEntity buildAgentExportEntity(String projectId, String workspaceId, Agent agent,
        String versionId) {
        AgentExportEntity agentExportEntity = new AgentExportEntity();
        try {
            String dslPath = agent.getDslPath();

            // 如果版本号不为空，取版本的dsl
            ReleaseVersion releaseVersion;
            if (!StringUtils.isEmpty(versionId)) {
                releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(), versionId);
                if (releaseVersion == null) {
                    throw new AgentStudioException(StudioError.MULTI_AGENT_VERSION_NOT_EXIST, agent.getAgentId(),
                        versionId);
                }
                dslPath = releaseVersion.getDslPath();
            }

            // 根据dslPath从OBS中获取DSL文件
            String agentInfo = mgObsService.downloadObsFile(dslPath);
            ControllerVO controllerVo = jacksonObjectMapper.readValue(agentInfo, new TypeReference<>() {});

            if (controllerVo != null) {
                handleMultiAgent(projectId, workspaceId, controllerVo, agentExportEntity);
            }
            // 设置对应字段
            agentExportEntity.setDsl(controllerVo);
            agentExportEntity.setMetadata(agent);
            agentExportEntity.setShareInfo(shareResourceManagerService.exportShareInfo(agent.getAgentId()));
            agentExportEntity.setShareResourceReferenceList(buildMappingEntityList(agent.getAgentId(), versionId));
            return agentExportEntity;
        } catch (AgentStudioException e) {
            log.error("Multi agent export failed!", e);
            throw e;
        } catch (Exception e) {
            log.error("Multi agent export failed!", e);
            throw new AgentStudioException(StudioError.MULTI_AGENT_EXPORT_FAILED);
        }
    }

    /**
     * workflow导出
     *
     * @param projectId projectId
     * @param body body 前端传入的导出请求的请求体，内容为需要导出的id列表
     * @return Resource 返回导出的文件流
     */
    public Resource exportWorkflows(String projectId, String workspaceId, ExportParams body) {
        Map<String, String> exportVersionMap = Optional.ofNullable(body.getWorkflows())
            .orElse(Collections.emptyList())
            .stream()
            .collect(
                Collectors.toMap(ExportWorkflow::getWorkflowId, ExportWorkflow::getWorkflowVersion, (v1, v2) -> v2));

        log.debug("Entering exportWorkflows with projectId={}, workflowIds={}", projectId, body.getWorkflowIds());

        List<String> workflowIds = getWorkflowList(body);
        log.debug("Processing {} workflows: {}", workflowIds.size(), workflowIds);

        // 判断是否超出最大导出数量限制
        if (workflowIds.size() > importMaxLen) {
            log.error("Exceeded the maximum export limit. The maximum number of exports is {}.", importMaxLen);
            throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE, importMaxLen);
        }

        validExportWorkflows(projectId, workspaceId, workflowIds);

        // 工作流导出逻辑
        StringBuilder tempJson = new StringBuilder();
        try {
            for (String workflowId : workflowIds) {
                log.debug("Processing workflow ID: {}", workflowId);

                // 合并该workflow的dsl和metadata
                WorkflowEntity workflowMetadata = workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId,
                    ThreadLocalUtils.getWorkspaceId(), workflowId);
                log.debug("Retrieved workflow metadata: {}", workflowMetadata);

                WorkflowExportEntity workflowExportEntity =
                    mergeWorkflow(projectId, workflowMetadata, exportVersionMap.get(workflowId));
                workflowExportEntity.setImportType(CommonConstant.WORKFLOW);
                log.debug("Merged workflow export entity: {}", workflowExportEntity);

                // 签名
                workflowExportEntity.setSignature(signatureUtils.signature(jacksonObjectMapper.writeValueAsString(
                    workflowExportEntity)));
                tempJson.append(jacksonObjectMapper.writeValueAsString(workflowExportEntity)).append("\n");
            }
            byte[] bytes = tempJson.toString().getBytes(StandardCharsets.UTF_8);
            log.debug("Generated JSONL content with length: {} bytes", bytes.length);

            // 处理响应体
            ResponseModel.TransferResource resource =
                new ResponseModel.TransferResource(new ByteArrayInputStream(bytes));
            resource.setFilename("workflows.jsonl");
            resource.setLength((long) bytes.length);
            log.debug("Created resource with filename={} and length={}", resource.getFilename(), resource.getLength());

            log.debug("Method completed successfully. Returning resource: {}", resource);
            return resource;
        } catch (AgentStudioException e) {
            log.error(e.getMessage(), e);
            throw e;
        } catch (Exception e) {
            log.error("Failed to export the workflow.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }
    }

    private List<String> getAgentIdList(ExportParams body) {
        if (body.getAgentIds() == null) {
            if (CollectionUtils.isNotEmpty(body.getAgents())) {
                return body.getAgents().stream().map(ExportAgent::getAgentId).distinct().collect(Collectors.toList());
            } else {
                return new ArrayList<>();
            }
        } else {
            return body.getAgentIds().stream().distinct().collect(Collectors.toList());
        }
    }

    private List<String> getWorkflowList(ExportParams body) {
        if (body.getWorkflowIds() == null) {
            if (CollectionUtils.isNotEmpty(body.getWorkflows())) {
                return body.getWorkflows()
                    .stream()
                    .map(ExportWorkflow::getWorkflowId)
                    .distinct()
                    .collect(Collectors.toList());
            } else {
                return new ArrayList<>();
            }
        } else {
            return body.getWorkflowIds().stream().distinct().collect(Collectors.toList());
        }
    }

    private void validExportWorkflows(String projectId, String workspaceId, List<String> workflowIds) {
        List<WorkflowEntity> workflowEntities = workflowMapper.selectByWorkflowIds(projectId, workspaceId, workflowIds);
        if (CollectionUtils.isEmpty(workflowEntities)) {
            throw new AgentStudioException(StudioError.WORKFLOW_NO_PERMISSION, String.join(",", workflowIds));
        }
        List<String> exportWorkflows = workflowEntities.stream().map(WorkflowEntity::getId).toList();
        List<String> cannotExportIds = new ArrayList<>();
        workflowIds.forEach(workflowId -> {
            if (!exportWorkflows.contains(workflowId)) {
                cannotExportIds.add(workflowId);
            }
        });
        if (CollectionUtils.isNotEmpty(cannotExportIds)) {
            throw new AgentStudioException(StudioError.WORKFLOW_NO_PERMISSION, String.join(",", cannotExportIds));
        }
    }

    public String exportWorkflowsStr(String projectId, String workspaceId, String workflowId) {
        StringBuilder tempJson = new StringBuilder();
        log.debug("Processing workflow ID: {}", workflowId);
        WorkflowEntity workflowMetadata =
            workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId, workspaceId, workflowId);
        if (workflowMetadata == null) {
            return tempJson.toString();
        }
        WorkflowExportEntity workflowExportEntity = mergeWorkflow(projectId, workflowMetadata, null);
        workflowExportEntity.setImportType(CommonConstant.WORKFLOW);
        try {
            tempJson.append(jacksonObjectMapper.writeValueAsString(workflowExportEntity)).append("\n");
        } catch (AgentStudioException e) {
            log.error(e.getMessage(), e);
            throw e;
        } catch (Exception e) {
            log.error("Failed to export the workflow.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }

        return tempJson.toString();
    }

    private void importWorkflow(String projectId, String targetWorkspaceId, String id,
        WorkflowExportEntity workflowExportEntity, WfImportDataWrapper importDataWrapper) {

        // 如果在环境中不存在，则不需要替换ID。如果是自己空间下已经有的，则把元数据中的ID替换成已经存在的
        String existingWorkflowId =
            getExistingWorkflowId(projectId, targetWorkspaceId, workflowExportEntity.getMetadata());
        if (workflowMapper.countWorkflowIdInDb(id) <= 0 || StringUtils.isNotEmpty(existingWorkflowId)) {
            if (StringUtils.isNotEmpty(existingWorkflowId)) {
                importDataWrapper.getIdToUuid().put(id, existingWorkflowId);
            } else {
                importDataWrapper.getIdToUuid().put(id, id);
            }
        }

        // 处理id替换（工作流、插件、mcp）
        workflowExportEntity =
            replaceWorkflowExportId(workflowExportEntity, targetWorkspaceId, id, projectId, importDataWrapper);

        // 导入工作流逻辑
        if (importWorkflowsHandler(projectId, targetWorkspaceId, workflowExportEntity, importDataWrapper)) {
            importDataWrapper.getSucceedIds().add(workflowExportEntity.getMetadata().getId());
            importDataWrapper.getImportResList()
                .add(buildImportRes(workflowExportEntity.getMetadata().getId(),
                    workflowExportEntity.getMetadata().getName(), ImportResourceType.WORKFLOW.toString(),
                    workflowExportEntity.getReleaseVersion(), "SUCCESS"));
        } else {
            log.error("Failed to import workflow:{}", id);
            importDataWrapper.getFailedIds().add(id);
            importDataWrapper.getImportResList()
                .add(buildImportRes(workflowExportEntity.getMetadata().getId(),
                    workflowExportEntity.getMetadata().getName(), ImportResourceType.WORKFLOW.toString(),
                    workflowExportEntity.getReleaseVersion(), "FAILED"));
        }
    }

    /**
     * 插件导入
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @param importIds 需要导入的插件id列表
     * @return ImportRsp 导入请求的响应，包括id、name、description、status
     */
    public ImportRsp importTools(String projectId, String targetWorkspaceId, MultipartFile file, String importIds) {
        List<String> importIdList = Arrays.asList(importIds.split(","));
        ImportRsp importRsp = new ImportRsp();
        WfImportDataWrapper importDataWrapper = new WfImportDataWrapper();
        importDataWrapper.setImportToolList(importIdList);
        try (BufferedReader bufferedReader =
            new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;

            // 逐行读取导入文件中的jsonl
            while ((line = bufferedReader.readLine()) != null) {
                ToolExportEntity tool = jacksonObjectMapper.readValue(line, new TypeReference<>() {});
                String toolId = tool.getMetadata().getToolId();

                // 如果环境中是否已存在该插件配置，且用户不选择覆盖，则continue
                if (!importIdList.contains(toolId)) {
                    continue;
                }

                // id冲突，则随机生成一个uuid
                if (!Objects
                    .isNull(toolMapperDiscard.selectWithoutStatus(pluginAdapterImpl.getPluginId(toolId), null, null))
                    && !isToolExistInWorkspace(projectId, targetWorkspaceId, tool.getMetadata())) {
                    tool.getMetadata().setToolId(UUID.randomUUID().toString());
                }

                // 导入插件逻辑
                if (importToolsHandler(projectId, targetWorkspaceId, tool.getMetadata(),
                    importDataWrapper.getPluginsOfAuth())) {
                    importDataWrapper.getSucceedIds().add(tool.getMetadata().getToolId());
                    importDataWrapper.getImportResList()
                        .add(buildImportRes(tool.getMetadata().getToolId(), tool.getMetadata().getToolDisplayName(),
                            ImportResourceType.PLUGIN.toString(), null, "SUCCESS"));
                } else {
                    log.error("Failed to import tool:{}", toolId);
                    importDataWrapper.getFailedIds().add(toolId);
                    importDataWrapper.getImportResList()
                        .add(buildImportRes(tool.getMetadata().getToolId(), tool.getMetadata().getToolDisplayName(),
                            ImportResourceType.PLUGIN.toString(), null, "FAILED"));
                }
            }
            buildImportRsp(importRsp, importDataWrapper);
        } catch (Exception e) {
            log.error("Failed to import the plug-in.", e);
            throw new AgentStudioException(StudioError.TOOL_IMPORT_FILE);
        }
        return importRsp;
    }

    /**
     * 导入Agent
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个插件/工作流的配置
     * @param importAgents 需要导入的Agent id
     * @param importTools 需要导入的插件id
     * @param importWorkflows 需要导入的Workflow id
     * @return ImportRsp 导入请求的响应，包括id、name、description、status和dependencies（Agent的依赖）
     */
    public ImportRsp importAgents(String projectId, MultipartFile file, String importAgents, String importTools,
        String importWorkflows) {
        log.debug("Entering importAgents with projectId={}, importAgents={}, importTools={}, importWorkflows={}",
            projectId, importAgents, importTools, importWorkflows);

        List<String> importAgentList = new ArrayList<>(Arrays.asList(importAgents.split(",")));
        List<String> importToolList = new ArrayList<>(Arrays.asList(importTools.split(",")));
        List<String> importWorkflowList = new ArrayList<>(Arrays.asList(importWorkflows.split(",")));
        ArrayList<ImportRes> importResList = new ArrayList<>();
        log.debug("Import lists initialized - Agents: {}, Tools: {}, Workflows: {}", importAgentList, importToolList,
            importWorkflowList);

        skuManageService.validateImportAppCountExceededLimitOrNot(importAgentList, importWorkflowList,
            RequestContextUtils.getRequestWorkspaceId());

        ImportRsp importRsp = new ImportRsp();
        WfImportDataWrapper importDataWrapper = new WfImportDataWrapper();
        importDataWrapper.setImportWorkflowList(importWorkflowList);
        importDataWrapper.setImportToolList(importToolList);
        importDataWrapper.setImportAgentList(importAgentList);
        importDataWrapper.setImportResList(importResList);
        log.debug("WfImportDataWrapper initialized: {}", importDataWrapper);

        try (BufferedReader bufferedReader =
            new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            log.debug("Opened file for reading: {}", file.getOriginalFilename());
            String line;

            // 逐行读取导入文件中的jsonl
            while ((line = bufferedReader.readLine()) != null) {
                log.debug("Reading line: {}", line);
                AgentExportEntity agentExport = jacksonObjectMapper.readValue(line, new TypeReference<>() {});
                log.debug("Parsed AgentExportEntity: {}", agentExport);
                String id = agentExport.getMetadata().getAgentId();
                log.debug("Processing Agent with ID: {}", id);

                // 如果环境中是否已存在该Agent配置，且用户不选择覆盖，则continue
                if (!importAgentList.contains(agentExport.getMetadata().getAgentId())) {
                    continue;
                }

                // 签名验证
                String signature = agentExport.getSignature();
                agentExport.setSignature(null);
                signatureUtils.verifySignature(jacksonObjectMapper.writeValueAsString(agentExport), signature);

                // 如果在环境中不存在，则不需要替换ID。如果是自己空间下已经有的，则把元数据中的ID替换成已经存在的
                String existingAgentId = getExistingAgentId(projectId, RequestContextUtils.getRequestWorkspaceId(),
                    agentExport.getMetadata());
                if (agentMapper.countAgentIdInDb(id) <= 0 || StringUtils.isNotEmpty(existingAgentId)) {
                    if (StringUtils.isNotEmpty(existingAgentId)) {
                        importDataWrapper.getIdToUuid().put(id, existingAgentId);
                    } else {
                        importDataWrapper.getIdToUuid().put(id, id);
                    }
                }
                agentExport = replaceAgentExportId(agentExport, RequestContextUtils.getRequestWorkspaceId(), projectId,
                    importDataWrapper);

                // 导入Agent逻辑
                if (importAgentHandler(projectId, RequestContextUtils.getRequestWorkspaceId(), agentExport,
                    importDataWrapper)) {
                    importDataWrapper.getSucceedIds().add(agentExport.getMetadata().getAgentId());
                    importDataWrapper.getImportResList()
                        .add(buildImportRes(agentExport.getMetadata().getAgentId(), agentExport.getMetadata().getName(),
                            ImportResourceType.AGENT.toString(), agentExport.getReleaseVersion(), "SUCCESS"));
                } else {
                    log.error("Failed to import agent:{}", id);
                    importDataWrapper.getFailedIds().add(id);
                    importDataWrapper.getImportResList()
                        .add(buildImportRes(agentExport.getMetadata().getAgentId(), agentExport.getMetadata().getName(),
                            ImportResourceType.AGENT.toString(), agentExport.getReleaseVersion(), "FAILED"));
                }
            }
            buildImportRsp(importRsp, importDataWrapper);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to import the Agent.", e);
            throw new AgentStudioException(StudioError.AGENT_IMPORT_FILE);
        }
        return importRsp;
    }

    private ImportRes buildImportRes(String id, String name, String type, ReleaseVersion releaseVersion,
        String status) {
        ImportRes importRes = new ImportRes();
        importRes.setId(id);
        importRes.setName(name);
        importRes.setType(type);
        if (releaseVersion != null) {
            importRes.setVersion(releaseVersion.getVersionId());
        }
        importRes.setStatus(status);
        return importRes;
    }

    public void importAgentWithStr(String projectId, String targetWorkspaceId, String agentStr,
        List<ImportListInfo> importListInfoList) {
        WfImportDataWrapper wfImportDataWrapper = new WfImportDataWrapper();
        resolveDependency(wfImportDataWrapper, importListInfoList);
        skuManageService.validateImportAppCountExceededLimitOrNot(wfImportDataWrapper.getImportAgentList(),
            wfImportDataWrapper.getImportWorkflowList(), targetWorkspaceId);

        List<String> agentList = wfImportDataWrapper.getImportAgentList();
        String agentId = agentList.get(0);
        log.debug("Entering importAgents with projectId={}, agentId={}", projectId, agentId);

        try {
            AgentExportEntity agentExportEntity = jacksonObjectMapper.readValue(agentStr, new TypeReference<>() {});

            log.debug("Parsed AgentExportEntity: {}", agentExportEntity);
            String id = agentExportEntity.getMetadata().getAgentId();
            log.debug("Processing Agent with ID: {}", id);

            if (!agentId.equals(agentExportEntity.getMetadata().getAgentId())) {
                return;
            }

            // 如果在环境中不存在，则不需要替换ID。如果是自己空间下已经有的，则把元数据中的ID替换成已经存在的
            String existingAgentId = getExistingAgentId(projectId, targetWorkspaceId, agentExportEntity.getMetadata());
            if (agentMapper.countAgentIdInDb(agentId) <= 0 || StringUtils.isNotEmpty(existingAgentId)) {
                if (StringUtils.isNotEmpty(existingAgentId)) {
                    wfImportDataWrapper.getIdToUuid().put(id, existingAgentId);
                } else {
                    wfImportDataWrapper.getIdToUuid().put(id, id);
                }
            }

            agentExportEntity =
                replaceAgentExportId(agentExportEntity, targetWorkspaceId, projectId, wfImportDataWrapper);

            if (!importAgentHandler(projectId, targetWorkspaceId, agentExportEntity, wfImportDataWrapper)) {
                log.error("Fail to import agent: {}", id);
                throw new AgentStudioException(StudioError.AGENT_IMPORT_FILE);
            }

        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to import the Agent.", e);
            throw new AgentStudioException(StudioError.AGENT_IMPORT_FILE);
        }
    }

    private void resolveDependency(WfImportDataWrapper importDataWrapper, List<ImportListInfo> importListInfoList) {
        List<String> importAgentList = importDataWrapper.getImportAgentList();
        List<String> importWorkflowList = importDataWrapper.getImportWorkflowList();
        List<String> importToolList = importDataWrapper.getImportToolList();
        for (ImportListInfo importListInfo : importListInfoList) {
            if (CommonConstant.WORKFLOW.equals(importListInfo.getType())) {
                importWorkflowList.add(importListInfo.getId());
            } else if (CommonConstant.PLUGIN.equals(importListInfo.getType())) {
                importToolList.add(importListInfo.getId());
            } else {
                importAgentList.add(importListInfo.getId());
            }
            List<ImportListInfo> dependencies = importListInfo.getDependencies();
            if (CollectionUtils.isEmpty(dependencies)) {
                continue;
            }
            importDataWrapper.setImportAgentList(importAgentList);
            importDataWrapper.setImportWorkflowList(importWorkflowList);
            importDataWrapper.setImportToolList(importToolList);
            resolveDependency(importDataWrapper, dependencies);
        }
    }

    /**
     * 导入单个Agent
     *
     * @param projectId projectId
     * @param agentExportEntity 需要导入的Agent配置对象
     * @param wfImportDataWrapper 导入中间数据
     * @param targetWorkspaceId 目标空间id
     * @return boolean 是否导入成功
     */
    public boolean importAgentHandler(String projectId, String targetWorkspaceId, AgentExportEntity agentExportEntity,
        WfImportDataWrapper wfImportDataWrapper) {
        // 校验共享资源引用的情况
        shareResourceManagerService.validateShareReferences(agentExportEntity.getShareResourceReferenceList(), targetWorkspaceId);

        // 导入资源共享信息
        shareResourceManagerService.importShareInfo(projectId, agentExportEntity.getShareInfo(), wfImportDataWrapper);

        // 导入依赖的插件
        List<ToolEntity> tools = agentExportEntity.getPlugins();
        Agent metadata = agentExportEntity.getMetadata();
        if (!importAgentTools(projectId, targetWorkspaceId, tools, metadata, wfImportDataWrapper)) {
            return false;
        }

        if (importModelEnable) {
            try {
                // 导入依赖的模型
                metadata = importModeByAgent(projectId, metadata, targetWorkspaceId);
                agentExportEntity.setMetadata(metadata);
                processControllerModel(projectId, targetWorkspaceId, agentExportEntity);
            } catch (Exception e) {
                log.warn("import {} agent model fail ", projectId, e);
            }
        }

        // 导入依赖的工作流
        List<WorkflowExportEntity> workflows = agentExportEntity.getWorkflows();
        if (!importAgentWorkflows(projectId, targetWorkspaceId, workflows, metadata, wfImportDataWrapper)) {
            return false;
        }

        // 导入依赖的子控制器
        List<AgentExportEntity> agents = agentExportEntity.getAgents();
        if (!CollectionUtils.isEmpty(agents)) {
            // 子控制器和主控制器依赖关系
            ArrayList<MappingEntity> relateAgents = new ArrayList<>();
            for (AgentExportEntity agent : agents) {
                if (!importAgentHandler(projectId, targetWorkspaceId, agent, wfImportDataWrapper)) {
                    wfImportDataWrapper.getImportResList()
                        .add(buildImportRes(agent.getMetadata().getAgentId(), agent.getMetadata().getName(),
                            ImportResourceType.AGENT.toString(), agent.getReleaseVersion(), "FAILED"));
                    return false;
                }
                wfImportDataWrapper.getImportResList()
                    .add(buildImportRes(agent.getMetadata().getAgentId(), agent.getMetadata().getName(),
                        ImportResourceType.AGENT.toString(), agent.getReleaseVersion(), "SUCCESS"));
                // 记录子控制器和主控器的关联关系
                relateAgents.add(buildSubAgentMapping(metadata, agent));
            }

            // 插入子控制器和主控制器关联关系
            // 先删除关联关系
            mappingMapper.deleteBatchByAppIdAndResourceType(metadata.getAgentId(), CommonConstant.CONTROLLER_TYPE);
            if (!CollectionUtils.isEmpty(relateAgents)) {
                mappingMapper.insertBatch(relateAgents);
            }
        }

        // 导入依赖的单智能体
        List<AgentExportEntity> singleAgents = agentExportEntity.getSingleAgents();
        if (!CollectionUtils.isEmpty(singleAgents)) {
            // 子单智能体和主控制器依赖关系
            ArrayList<MappingEntity> relateSingleAgents = new ArrayList<>();
            for (AgentExportEntity agent : singleAgents) {
                if (!importAgentHandler(projectId, targetWorkspaceId, agent, wfImportDataWrapper)) {
                    wfImportDataWrapper.getImportResList()
                            .add(buildImportRes(agent.getMetadata().getAgentId(), agent.getMetadata().getName(),
                                    ImportResourceType.AGENT.toString(), agent.getReleaseVersion(), "FAILED"));
                    return false;
                }
                wfImportDataWrapper.getImportResList()
                        .add(buildImportRes(agent.getMetadata().getAgentId(), agent.getMetadata().getName(),
                                ImportResourceType.AGENT.toString(), agent.getReleaseVersion(), "SUCCESS"));
                // 记录单智能体和主控器的关联关系
                relateSingleAgents.add(buildSingleAgentMapping(metadata, agent));
            }

            // 插入子单智能体和主控制器关联关系
            // 先删除关联关系
            mappingMapper.deleteBatchByAppIdAndResourceType(metadata.getAgentId(), CommonConstant.AGENT_TYPE);
            if (!CollectionUtils.isEmpty(relateSingleAgents)) {
                mappingMapper.insertBatch(relateSingleAgents);
            }
        }

        // 导入依赖的MCP服务
        MappingEntity mcpMapping = new MappingEntity();
        mcpMapping.setAppId(metadata.getAgentId());
        mcpMapping.setAppName(metadata.getName());
        mcpMapping.setAppType(CommonConstant.AGENT_TYPE);
        List<McpServerInfo> mcpServers = agentExportEntity.getMcpServers();
        if (!importMcpServers(projectId, targetWorkspaceId, mcpServers, mcpMapping, wfImportDataWrapper)) {
            return false;
        }

        // 导入依赖的skill
        List<SkillDetails> skills = agentExportEntity.getSkills();
        List<SkillDetails> existingSkillsInTargetWorkspace = skillMapper.search(
            new SkillEntity().setProjectId(projectId).setWorkspaceId(targetWorkspaceId).setStatus("developed"), 0,
            Integer.MAX_VALUE, null, null, 0);
        importAgentSKill(skills, existingSkillsInTargetWorkspace, metadata);

        try {
            // 导入Agent本身
            importAgentSelf(projectId, targetWorkspaceId, agentExportEntity);
        } catch (Exception e) {
            log.error(String.format("Failed to import agent: %s", metadata.getAgentId()), e);
            return false;
        }
        log.info("Succeed to import agent: {}", metadata.getAgentId());
        return true;
    }

    /**
     * 导入skill
     * @param skills skills
     * @param existingSkillsInTargetWorkspace existingSkillsInTargetWorkspace
     * @param agent agent
     */
    private void importAgentSKill(List<SkillDetails> skills, List<SkillDetails> existingSkillsInTargetWorkspace, Agent agent) {
        if (CollectionUtils.isEmpty(skills)) {
            return;
        }
        List<String> skillsNames = skills.stream().map(SkillDetails::getName).toList();
        Map<String, SkillDetails> skillMap = skills.stream()
            .collect(Collectors.toMap(
                SkillDetails::getName,
                skill -> skill
            ));
        // 先删除引用关系
        mappingMapper.deleteBatchByAppIdAndResourceType(agent.getAgentId(), CommonConstant.SKILL_TYPE);
        List<String> existSkillIntargetWorkspaceNames = existingSkillsInTargetWorkspace.stream().map(SkillDetails::getName).toList();
        Map<String, SkillDetails> existSkillMap = existingSkillsInTargetWorkspace.stream()
            .collect(Collectors.toMap(
                SkillDetails::getName,
                skill -> skill,
                (existing, replacement) -> existing
            ));
        List<MappingEntity> mappingEntities = new ArrayList<>();
        for (String name : skillsNames) {
            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setAppId(agent.getAgentId());
            mappingEntity.setAppName(agent.getName());
            mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
            mappingEntity.setMappingId(UUID.randomUUID().toString());
            mappingEntity.setResourceType(CommonConstant.SKILL_TYPE);
            mappingEntity.setReferenceType(ReferenceTypeEnum.DIRECT.getValue());
            // 匹配成功
            if (existSkillIntargetWorkspaceNames.contains(name)) {
                SkillDetails matchedSkill = existSkillMap.get(name);
                mappingEntity.setResourceId(matchedSkill.getSkillId());
                mappingEntity.setResourceName(matchedSkill.getName());
                mappingEntity.setResourceVersion(matchedSkill.getUsedVersion());
                mappingEntity.setValid(true);

            } else {
                SkillDetails oldSkill = skillMap.get(name);
                mappingEntity.setResourceId(oldSkill.getSkillId());
                mappingEntity.setResourceName(oldSkill.getName());
                mappingEntity.setResourceVersion(oldSkill.getUsedVersion());
                mappingEntity.setValid(false);
            }
            mappingEntities.add(mappingEntity);
        }

        mappingMapper.insertBatch(mappingEntities);
    }

    /**
     * 导入 Agent 场景信息
     * @param agentExportEntity Agent 导出实体
     * @param metadata Agent 元数据
     */
    private void importAgentScenes(AgentExportEntity agentExportEntity, Agent metadata) {
        List<Scene> scenes = agentExportEntity.getScenes();
        if (!CommonConstant.PLANEXECUTE_TYPE.equals(metadata.getSubType())) {
            return;
        }
        try {
            // 导入场景
            AgentInfo agentInfo = metadata.convertToDto();
            agentInfo.setScenes(agentExportEntity.getScenes());
            metadata.setDslPath(agentCommonService.getAgentObsPath(metadata.getAgentId(), CommonConstant.DSL_STR));
            agentMapper.updateAgentById(metadata.getProjectId(), metadata.getWorkspaceId(), metadata.getAgentId(), metadata);
            String updatedDslJson = JSON.toJSONString(agentInfo);
            // 上传dsl
            mgObsService.uploadObsFile(metadata.getAgentId(), metadata.getAgentId(),
                CommonConstant.AGENT, updatedDslJson, CommonConstant.DSL_STR);

            log.info("Succeed to import scenes for agent: {}, scene count: {}",
                metadata.getAgentId(), scenes.size());
        } catch (Exception e) {
            log.error(String.format("Failed to import scenes for agent: %s", metadata.getAgentId()), e);
            // 场景导入失败不影响整体导入流程
        }
    }

    private void importAgentReleaseVersion(String projectId, AgentExportEntity agentExportEntity, Agent agent) {
        ReleaseVersion releaseVersion = agentExportEntity.getReleaseVersion();
        if (releaseVersion != null) {
            // 这里用metadata.getId()，而不用releaseVersion里面的版本，因为工作流ID可能变了
            releaseVersion.setAppId(agent.getAgentId());
            ReleaseVersion existVersion =
                releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(), releaseVersion.getVersionId());

            // 版本不存在导入版本
            if (existVersion == null) {
                importAgentVersion(projectId, agentExportEntity, releaseVersion);
            }
        }
    }

    private void importAgentVersion(String projectId, AgentExportEntity agentExportEntity, ReleaseVersion version) {
        String agentId = agentExportEntity.getMetadata().getAgentId();
        String versionId = version.getVersionId();

        // 1.备份dsl和ir
        String releaseDslPath = null;
        if (CommonConstant.CONTROLLER.equals(agentExportEntity.getMetadata().getType())) {
            releaseDslPath = mgObsService.uploadObsFile(agentExportEntity.getMetadata().getAgentId(),
                agentId + Constants.UNDERLINE_STR + versionId, CommonConstant.AGENT,
                JSONObject.toJSONString(agentExportEntity.getDsl()), CommonConstant.Workflow.FLOW);
        }

        if (CommonConstant.AGENT.equals(agentExportEntity.getMetadata().getType())) {
            releaseDslPath = mgObsService.uploadObsFile(agentExportEntity.getMetadata().getAgentId(),
                agentId + Constants.UNDERLINE_STR + versionId, CommonConstant.AGENT,
                JSONObject.toJSONString(agentExportEntity.getDsl()), CommonConstant.DSL_STR);
        }

        String releaseIrPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.AGENT, CommonConstant.Workflow.IR,
            agentId, agentId + Constants.UNDERLINE_STR + versionId);

        // 2. 创建版本数据
        version.setId(UUID.randomUUID().toString());
        version.setAppId(agentId);
        version.setDslPath(releaseDslPath);
        version.setIrPath(releaseIrPath);
        version.setCreatorId(RequestContextUtils.getRequestUserId());
        version.setCreator(RequestContextUtils.getRequestUserName());
        releaseVersionMapper.insert(version);

        // 子工作流版本ir转换放到最后,保证ir转换失败时（缺少预置插件/MCP服务等情况）不影响整体导入
        try {
            if (CommonConstant.CONTROLLER.equals(agentExportEntity.getMetadata().getType())) {
                // 上传DSL
                ControllerVO entityDsl = agentExportEntity.getDsl();
                // 导入是刷新参数
                controllerManagementService.replaceDefaultSystemInput(entityDsl);
                entityDsl.setProjectId(projectId);
                agentCommonService.uploadToObsWithVersion(agentExportEntity.getMetadata(), entityDsl,
                    CommonConstant.Workflow.FLOW, versionId);
                // 上传IR
                Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId
                    = controllerManagementService.groupDslNodes(entityDsl);
                ControllerIR ir = controllerManagementService.dslToIr(entityDsl, nodesGroupByTypeId);
                agentCommonService.uploadToObsNoNullWithVersion(agentExportEntity.getMetadata(), ir,
                    CommonConstant.Workflow.IR, versionId);
                log.info("Succeed to refresh subController ir, controller id = {}", agentId);
            }

            if (CommonConstant.AGENT.equals(agentExportEntity.getMetadata().getType())) {
                AgentInfo entityDsl = agentExportEntity.getSingleAgentDsl();
                // 更新id
                entityDsl.setAgentId(agentExportEntity.getMetadata().getAgentId());
                entityDsl.setName(agentExportEntity.getMetadata().getName());
                entityDsl.setWorkspaceId(agentExportEntity.getMetadata().getWorkspaceId());
                agentCommonService.uploadToObsWithVersion(agentExportEntity.getMetadata(), entityDsl,
                    CommonConstant.DSL_STR, versionId);
                String dslJson = JSON.toJSONString(entityDsl);
                Agent agent = JSON.parseObject(dslJson, Agent.class);
                Map<String, Object> metadata = parseMetadata(agent);
                Map<String, Object> irInfo = irAdapterService.adaptAgent(agent, metadata);
                agentCommonService.uploadToObsNoNullWithVersion(agentExportEntity.getMetadata(), irInfo,
                    CommonConstant.Workflow.IR, versionId);
                log.info("Succeed to refresh Agent ir, Agent id = {}", agentId);
            }


        } catch (Exception e) {
            String errorMsg = String.format("Failed to refresh subController ir, controller id = %s", agentId);
            log.error(errorMsg, e);
        }
    }

    public void processControllerModel(String projectId, String targetWorkspaceId,
        AgentExportEntity agentExportEntity) {
        if (agentExportEntity.getDsl() == null) {
            return;
        }
        List<ControllerNodeVO> modelNodes =
            agentExportEntity.getDsl().getNodes().stream().filter((ControllerNodeVO controllerNodeVO) -> {
                boolean flag =
                    Strings.CS.equals(CommonConstant.ControllerConstants.CONTROLLER_TYPE, controllerNodeVO.getType())
                        && !Objects.isNull(controllerNodeVO.getConfigs());
                if (!flag) {
                    return false;
                }
                ControllerNodeConfigVO controllerNodeConfigVO = JsonUtils
                    .objectToClassRef(controllerNodeVO.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {});
                if (controllerNodeConfigVO != null && controllerNodeConfigVO.getModel() != null
                    && StringUtils.isNotBlank(controllerNodeConfigVO.getModel().getModelDeploymentId())
                    && StringUtils.isNotBlank(controllerNodeConfigVO.getModel().getModelName())) {
                    return true;
                }
                return false;
            }).toList();
        Map<String, String> replaceModelIdRecord = new HashMap<>();
        for (ControllerNodeVO controllerNodeVO : modelNodes) {
            // 大模型等节点配置在config中的 model下，意图识别节点为 llm
            ModelConfigVO modelConfigVO = JsonUtils
                .objectToClassRef(controllerNodeVO.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {})
                .getModel();
            String modelIdInDb = getModelIdInDatabase(projectId, targetWorkspaceId,
                modelConfigVO.getModelDeploymentId(), modelConfigVO.getModelName());
            if (Strings.CS.equals(modelConfigVO.getModelDeploymentId(), modelIdInDb)) {
                continue;
            }
            if (StringUtils.isBlank(modelIdInDb) || Strings.CS.equals("uuid", modelIdInDb)) {
                replaceModelIdRecord.put(modelConfigVO.getModelDeploymentId(), Strings.CS.equals("uuid", modelIdInDb)
                    ? UUID.randomUUID().toString() : modelConfigVO.getModelDeploymentId());
                modelConfigVO.setModelDeploymentId(replaceModelIdRecord.get(modelConfigVO.getModelDeploymentId()));
                String providerId = createProvider(projectId, targetWorkspaceId);
                Map<String, String> importMode = new HashMap<>();
                importMode.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID, modelConfigVO.getModelDeploymentId());
                importMode.put(CommonConstant.ModelParam.MODEL_NAME, modelConfigVO.getModelName());
                createModel(projectId, targetWorkspaceId, importMode, providerId);
            } else {
                // id 不存在，但是名称存在，故需替换Id
                replaceModelIdRecord.put(modelConfigVO.getModelDeploymentId(), modelIdInDb);
            }
        }
        for (ControllerNodeVO controllerNodeVO : agentExportEntity.getDsl().getNodes()) {
            if (Strings.CS.equals(CommonConstant.ControllerConstants.CONTROLLER_TYPE, controllerNodeVO.getType())
                && !Objects.isNull(controllerNodeVO.getConfigs())) {

                ControllerNodeConfigVO controllerNodeConfigVO = JsonUtils
                    .objectToClassRef(controllerNodeVO.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {});
                if (controllerNodeConfigVO == null || controllerNodeConfigVO.getModel() == null
                    || StringUtils.isBlank(controllerNodeConfigVO.getModel().getModelDeploymentId())
                    || StringUtils.isBlank(controllerNodeConfigVO.getModel().getModelName())) {
                    continue;
                }
                controllerNodeConfigVO.getModel()
                    .setModelDeploymentId(
                        replaceModelIdRecord.containsKey(controllerNodeConfigVO.getModel().getModelDeploymentId())
                            ? replaceModelIdRecord.get(controllerNodeConfigVO.getModel().getModelDeploymentId())
                            : controllerNodeConfigVO.getModel().getModelDeploymentId());
                controllerNodeConfigVO.getModel()
                    .setModelType(supportTypes.contains(controllerNodeConfigVO.getModel().getModelType())
                        ? controllerNodeConfigVO.getModel().getModelType() : ModelTypeV2.LLM.toString());
                controllerNodeVO.setConfigs(controllerNodeConfigVO);
            }
        }
    }

    public Agent importModeByAgent(String projectId, Agent metadata, String workspaceId) {
        String modelId = metadata.getModelDeploymentId();
        String modelName = metadata.getModelName();
        if (StringUtils.isBlank(modelId) || StringUtils.isBlank(modelName)) {
            return metadata;
        }
        String modelIdInDb = getModelIdInDatabase(projectId, workspaceId, modelId, modelName);
        if (Strings.CS.equals(modelId, modelIdInDb)) {
            return metadata;
        }
        metadata.setModelType(
            supportTypes.contains(metadata.getModelType()) ? metadata.getModelType() : ModelTypeV2.LLM.toString());
        if (StringUtils.isBlank(modelIdInDb) || Strings.CS.equals("uuid", modelIdInDb)) {
            metadata
                .setModelDeploymentId(Strings.CS.equals("uuid", modelIdInDb) ? UUID.randomUUID().toString() : modelId);
            // 模型不存在时 需要考虑 分别考虑 供应商 与 服务模型
            String providerId = createProvider(projectId, workspaceId);
            Map<String, String> defaultMode = new HashMap<>();
            defaultMode.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID, metadata.getModelDeploymentId());
            defaultMode.put(CommonConstant.ModelParam.MODEL_NAME, modelName);
            createModel(projectId, workspaceId, defaultMode, providerId);
            return metadata;
        } else {
            metadata.setModelDeploymentId(modelIdInDb);
            return metadata;
        }
    }

    private void importAgentSelf(String projectId, String targetWorkspaceId, AgentExportEntity agentExportEntity) {
        Agent metadata = agentExportEntity.getMetadata();

        // 设置Agent名称
        setAgentName(projectId, targetWorkspaceId, metadata);

        // 导入Agent元数据
        String type = Optional.ofNullable(metadata.getType()).orElse(CommonConstant.AGENT);
        metadata.setType(type);
        String dslPath = AgentType.CONTROLLER.getValue().equalsIgnoreCase(type)
            ? agentCommonService.getAgentObsPath(metadata.getAgentId(), CommonConstant.Workflow.FLOW) : null;
        metadata.setDslPath(dslPath);

        String irPath = agentCommonService.getAgentObsPath(metadata.getAgentId(), CommonConstant.Workflow.IR);
        metadata.setIrPath(irPath);

        metadata.setStatus(agentExportEntity.getReleaseVersion() == null ? AgentStatus.DRAFT.toString()
            : AgentStatus.PUBLISHED.toString());

        importAgentMetadata(projectId, targetWorkspaceId, metadata);
        String modelDeploymentId;
        importAgentScenes(agentExportEntity, metadata);

        if (AgentType.CONTROLLER.getValue().equalsIgnoreCase(type)) {
            // 上传DSL
            ControllerVO dsl = agentExportEntity.getDsl();

            // 导入是刷新参数
            controllerManagementService.replaceDefaultSystemInput(dsl);
            dsl.setProjectId(projectId);
            agentCommonService.uploadToObs(metadata, dsl, CommonConstant.Workflow.FLOW);

            // 导入是刷新参数
            controllerManagementService.replaceDefaultSystemInput(dsl);

            // 上传IR
            Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId =
                controllerManagementService.groupDslNodes(dsl);
            ControllerIR ir = controllerManagementService.dslToIr(dsl, nodesGroupByTypeId);
            agentCommonService.uploadToObsNoNull(metadata, ir, CommonConstant.Workflow.IR);
            modelDeploymentId = dsl.getNodes()
                .stream()
                .filter(nodeVo -> AgentType.CONTROLLER.getValue().equalsIgnoreCase(nodeVo.getType())
                    && nodeVo.getConfigs() != null)
                .map(nodeVo -> {
                    ControllerNodeConfigVO controllerNodeConfig =
                        JsonUtils.objectToClassRef(nodeVo.getConfigs(), new TypeReference<ControllerNodeConfigVO>() {});
                    if (controllerNodeConfig == null || controllerNodeConfig.getModel() == null) {
                        return "";
                    }
                    return controllerNodeConfig.getModel().getModelDeploymentId();
                })
                .toList()
                .stream()
                .findFirst()
                .orElse("");
        } else {
            // 上传IR
            Map<String, Object> agentMetadata = parseMetadata(metadata);
            Map<String, Object> irInfo = irAdapterService.adaptAgent(metadata, agentMetadata);
            // 如果场景信息存在，将场景配置添加到IR中
            if (agentExportEntity.getScenes() != null && !agentExportEntity.getScenes().isEmpty()) {
                irInfo.put("scenes", agentExportEntity.getScenes());
            }
            agentCommonService.uploadToObsNoNull(metadata, irInfo, CommonConstant.Workflow.IR);
            modelDeploymentId = metadata.getModelDeploymentId();
        }
        // 如包含版本信息，更新版本
        importAgentReleaseVersion(projectId, agentExportEntity, metadata);

        if (StringUtils.isNotBlank(modelDeploymentId)) {
            MappingEntity entity = new MappingEntity();
            entity.setAppName(metadata.getName());
            entity.setAppType(CommonConstant.AGENT_TYPE);
            entity.setResourceId(modelDeploymentId);
            entity.setResourceType(ResourceTypeEnum.MODEL.toString());
            relationManagementService.handleAgentModel(projectId, targetWorkspaceId, metadata.getAgentId(),
                List.of(entity));
        }
    }

    private void setAgentName(String projectId, String targetWorkspaceId, Agent metadata) {
        String importAgentName = metadata.getName();
        // 设置唯一agent名称
        if (!AGENT_NAME_PATTERN.matcher(metadata.getName()).matches()) {
            throw new AgentStudioException(StudioError.AGENT_EXPORT_FILE);
        }

        List<Agent> agentList =
            agentMapper.selectAgentByTraceIdAndWorkspaceId(projectId, targetWorkspaceId, metadata.getTraceId());

        if (CollectionUtils.isEmpty(agentList)) {
            return;
        }

        Agent existedAgentByTraceId = agentList.get(0);

        if (existedAgentByTraceId.getName().equalsIgnoreCase(importAgentName)) {
            return;
        }

        SearchCriteria searchCriteria = new SearchCriteria();
        searchCriteria.setWorkspaceId(targetWorkspaceId);
        List<Agent> existedAgentListInTargetWorkspace =
            agentMapper.selectByProjectIdAndSearchCriteria(projectId, searchCriteria);

        if (existedAgentListInTargetWorkspace == null || existedAgentListInTargetWorkspace.isEmpty()) {
            return;
        }

        String curName = existedAgentByTraceId.getName();

        // 排除旧名称,避免importAgentName和curName一致的情况
        Set<String> currentNameSet = existedAgentListInTargetWorkspace.stream()
            .map(Agent::getName)
            .filter(name -> !name.equalsIgnoreCase(curName))
            .collect(Collectors.toCollection(() -> new TreeSet<>(String.CASE_INSENSITIVE_ORDER)));

        // 判断是否有重复，有重复需要新生成
        if (currentNameSet.contains(importAgentName)) {
            importAgentName = subName(importAgentName, CommonConstant.NAME_MAX_LEN);
            int index = 1;
            while (currentNameSet.contains(importAgentName + Constants.UNDERLINE_STR + index)) {
                index++;
            }
            metadata.setName(importAgentName + Constants.UNDERLINE_STR + index);
        }
    }

    /**
     * 插件导出
     *
     * @param projectId projectId
     * @param body 前端传入的导出请求的请求体，内容为需要导出的id列表
     * @return Resource 返回导出的文件流
     */
    public Resource exportTools(String projectId, String workspaceId, ExportParams body) {
        List<String> bodyToolIds = body.getToolIds();
        ToolExportEntity toolExport = new ToolExportEntity();

        // 判断是否超出最大导出数量限制
        if (bodyToolIds.size() > importMaxLen) {
            log.error("Exceeded the maximum export limit. The maximum number of exports is {}.", importMaxLen);
            throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE, importMaxLen);
        }
        agentCommonService.validTools(projectId, workspaceId, bodyToolIds);
        Set<String> uniqueToolIds = new HashSet<>(bodyToolIds);
        // 插件导出逻辑
        StringBuilder tempJson = new StringBuilder();
        try {
            for (String toolId : uniqueToolIds) {

                // 从数据库查询该插件配置信息
                ToolEntity tool = toolMapperDiscard.selectByPrimaryKey(toolId, projectId);
                tool.setShareInfo(shareResourceManagerService.exportShareInfo(toolId));
                decryptedExportTool(tool);
                toolExport.setMetadata(tool);
                toolExport.setImportType(CommonConstant.PLUGIN);
                tempJson.append(jacksonObjectMapper.writeValueAsString(toolExport)).append("\n");
            }
            byte[] bytes = tempJson.toString().getBytes(StandardCharsets.UTF_8);

            // 处理响应体
            ResponseModel.TransferResource transferResource =
                new ResponseModel.TransferResource(new ByteArrayInputStream(bytes));
            transferResource.setFilename("tools.jsonl");
            transferResource.setLength((long) bytes.length);
            return transferResource;
        } catch (Exception e) {
            log.error("Failed to export the plug-in.", e);
            throw new AgentStudioException(StudioError.TOOL_EXPORT_FILE);
        }
    }

    /**
     * 同名时预处理截断name
     *
     * @param name 原始名称
     * @return 截断后的名称
     */
    private String subName(String name, int length) {
        if (name.length() > length) {
            name = name.substring(0, length);
        }
        return name;
    }

    /**
     * 导入workflow metadata
     *
     * @param projectId projectId
     * @param dlsPath OBS中存放工作流DSL文件的路径
     * @param metadata 工作流元数据
     */
    private void importWorkflowMetadata(String projectId, String targetWorkspaceId, String dlsPath, String irPath,
        WorkflowEntity metadata) {
        long curTime = new Date().getTime();
        metadata.setCreatedAt(curTime);
        metadata.setProjectId(projectId);
        metadata.setWorkspaceId(targetWorkspaceId);
        metadata.setDomainId(RequestContextUtils.getRequestUserDomainId());
        metadata.setCreatedBy(getUserName(projectId));
        metadata.setCreatorId(RequestContextUtils.getRequestUserId());
        metadata.setUpdatedBy(getUserName(projectId));
        metadata.setUpdaterId(RequestContextUtils.getRequestUserId());
        metadata.setPublishedAt(null);
        metadata.setDeployWfVersion(null);
        metadata.setDslPath(dlsPath);
        metadata.setIrPath(irPath);
        metadata.setDeleted(0);
        metadata.setUpdatedAt(curTime);
        metadata.setTestStatus(null);

        // 处理工作流元数据中的版本号
        if (metadata.getLastVersionId() != null
            && releaseVersionMapper.selectByAppIdAndVersionId(metadata.getId(), metadata.getLastVersionId()) == null) {
            metadata.setLastVersionId(null);
        }

        // 若已存在该配置走覆盖逻辑，否则插入到数据库中
        if (isWorkflowExistInWorkspace(projectId, targetWorkspaceId, metadata)) {
            workflowMapper.updateWorkflowEntityByTraceId(projectId, metadata.getTraceId(), targetWorkspaceId, metadata);
        } else {
            workflowMapper.createWorkflowEntity(metadata);
        }
    }

    private String getUserName(String projectId) {
        if (Strings.CS.equals(opSvcProjectId, projectId)) {
            return CommonConstant.DEFAULT_USERNAME;
        } else {
            return RequestContextUtils.getRequestUserName();
        }
    }

    private boolean importAgentWorkflows(String projectId, String targetWorkspaceId,
        List<WorkflowExportEntity> workflows, Agent metadata, WfImportDataWrapper wfImportDataWrapper) {
        if (CollectionUtils.isEmpty(workflows)) {
            return true;
        }

        for (WorkflowExportEntity workflow : workflows) {
            // 判断该工作流是否在需要导入的工作流中，不在的话表示：环境中已存在该工作流配置，且不选择覆盖掉该配置
            String id = workflow.getMetadata().getId();
            workflow.getMetadata()
                .setTraceId(StringUtils.isBlank(workflow.getMetadata().getTraceId()) ? id
                    : workflow.getMetadata().getTraceId());
            if (!wfImportDataWrapper.getImportWorkflowList().contains(id)) {
                continue;
            }

            // 导入该工作流
            if (!importWorkflowsHandler(projectId, targetWorkspaceId, workflow, wfImportDataWrapper)) {
                log.error("Fail to import agent: {}, caused by workflow:{} fails to be imported.",
                    metadata.getAgentId(), id);
                wfImportDataWrapper.getImportResList()
                    .add(buildImportRes(workflow.getMetadata().getId(), workflow.getMetadata().getName(),
                        ImportResourceType.WORKFLOW.toString(), workflow.getReleaseVersion(), "FAILED"));
                return false;
            }
            wfImportDataWrapper.getImportResList()
                .add(buildImportRes(workflow.getMetadata().getId(), workflow.getMetadata().getName(),
                    ImportResourceType.WORKFLOW.toString(), workflow.getReleaseVersion(), "SUCCESS"));
            log.info("Succeed to import workflow: {}", id);
        }

        // 记录agent和workflow的关联关系
        try {
            importMapperAgentWorkflows(metadata, workflows);
        } catch (Exception e) {
            log.error("Fail to import batch MapperAgentWorkflows, agent: {}.", metadata.getAgentId());
            return false;
        }
        return true;
    }

    private boolean importAgentTools(String projectId, String targetWorkspaceId, List<ToolEntity> tools, Agent metadata,
        WfImportDataWrapper wfImportDataWrapper) {
        if (CollectionUtils.isEmpty(tools)) {
            return true;
        }

        mappingMapper.deleteBatchByAppIdAndResourceType(metadata.getAgentId(), CommonConstant.TOOL_TYPE);
        for (ToolEntity tool : tools) {
            // 处理预置插件
            parseAgentInnerTool(projectId, tool, metadata);

            shareResourceManagerService.validateShareReferences(tool.getShareResourceReferenceList(),
                targetWorkspaceId);

            // 添加依赖关系
            String toolId = tool.getToolId();
            try {
                importMapperAgentTool(projectId, tool, metadata);
            } catch (Exception e) {
                log.error("Fail to import MapperAgentTool, agent: {}, tool: {}.", metadata.getAgentId(), toolId, e);
                return false;
            }

            // 判断该插件是否在需要导入的插件中，不在的话表示：环境中已存在该插件配置，且不选择覆盖掉该配置
            if (!wfImportDataWrapper.getImportToolList().contains(toolId)) {
                continue;
            }

            // 导入该插件
            if (!Strings.CS.equals(tool.getType(), ToolType.INNER.type)
                && !importToolsHandler(projectId, targetWorkspaceId, tool, wfImportDataWrapper.getPluginsOfAuth())) {
                log.error("Fail to import agent: {}, caused by tool:{} fails to be imported.", metadata.getAgentId(),
                    toolId);
                wfImportDataWrapper.getImportResList()
                    .add(buildImportRes(toolId, tool.getToolDisplayName(), ImportResourceType.PLUGIN.toString(), null,
                        "FAILED"));
                return false;
            }
            log.info("Succeed to import tool: {}", toolId);
            wfImportDataWrapper.getImportResList()
                .add(buildImportRes(toolId, tool.getToolDisplayName(), ImportResourceType.PLUGIN.toString(), null,
                    "SUCCESS"));
        }
        return true;
    }

    private void parseAgentInnerTool(String projectId, ToolEntity tool, Agent agent) {
        if (!ToolType.INNER.type.equals(tool.getType())) {
            return;
        }
        ToolEntity toolEntity = toolMapperDiscard.selectByProjectId(pluginAdapterImpl.getPluginId(tool.getToolId()),
            projectId, opSvcProjectId);
        if (toolEntity == null) {
            return;
        }

        // 已有预置插件添加绑定关系
        MappingEntity mappingAgentTool = mappingMapper.selectByAppIdAndResourceId(agent.getAgentId(), tool.getToolId());
        if (mappingAgentTool != null) {
            return;
        }
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setMappingId(UUID.randomUUID().toString());
        mappingEntity.setAppId(agent.getAgentId());
        mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
        mappingEntity.setAppName(agent.getName());
        mappingEntity.setResourceId(tool.getToolId());
        mappingEntity.setResourceType(CommonConstant.TOOL_TYPE);
        mappingEntity.setResourceName(tool.getToolDisplayName());
        mappingMapper.insert(mappingEntity);
    }

    /**
     * 导入Agent metadata
     *
     * @param projectId projectId
     * @param agentMetadata Agent元数据
     */
    private void importAgentMetadata(String projectId, String targetWorkspaceId, Agent agentMetadata) {
        Date date = new Date();
        agentMetadata.setCreatedOn(date);
        agentMetadata.setUpdatedOn(date);
        agentMetadata.setPublishedOn(null);
        agentMetadata.setProjectId(projectId);
        agentMetadata.setStatus(agentMetadata.getStatus());
        agentMetadata.setCreator(RequestContextUtils.getRequestUserName());
        agentMetadata.setCreatorId(RequestContextUtils.getRequestUserId());
        agentMetadata.setWorkspaceId(targetWorkspaceId);
        agentMetadata.setDomainId(RequestContextUtils.getRequestUserDomainId());

        // 限制推荐问最大个数
        List<String> suggestQueries = agentMetadata.getSuggestQueries();
        if (suggestQueries != null && suggestQueries.size() > CommonConstant.MAX_QUESTION_NUMS) {
            suggestQueries.subList(CommonConstant.MAX_QUESTION_NUMS, suggestQueries.size()).clear();
        }

        // 限制开场白长度
        String prologue = agentMetadata.getPrologue();
        if (prologue != null && prologue.length() > CommonConstant.MAX_PROLOGUE_LENGTH) {
            log.error("Exceed the max prologue length, Agent: {}", agentMetadata.getAgentId());
            throw new AgentStudioException(StudioError.AGENT_IMPORT_FILE);
        }

        // 若已存在该配置走覆盖逻辑，否则插入到数据库中
        if (isAgentExistInWorkspace(projectId, targetWorkspaceId, agentMetadata)) {
            agentMapper.updateAgentByTraceId(projectId, targetWorkspaceId, agentMetadata.getTraceId(), agentMetadata);
        } else {
            agentMapper.insert(agentMetadata);
        }
    }

    /**
     * 把依赖关系存到对应的数据库中
     *
     * @param tool tool
     * @param agent agent
     */
    private void importMapperAgentTool(String projectId, ToolEntity tool, Agent agent) {
        if (ToolType.INNER.type.equals(tool.getType()) && !opSvcProjectId.equals(projectId)) {
            return;
        }
        MappingEntity mappingAgentTool = mappingMapper.selectByAppIdAndResourceId(agent.getAgentId(), tool.getToolId());

        ShareResourceEntity shareWorkflow = shareResourceMapper.selectShareResourceEntityByResourceId(
            pluginAdapterImpl.getPluginId(tool.getToolId()));
        // 若已存在该配置走覆盖逻辑，否则插入到数据库中
        if (mappingAgentTool == null) {
            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setMappingId(UUID.randomUUID().toString());
            mappingEntity.setAppId(agent.getAgentId());
            mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
            mappingEntity.setAppName(agent.getName());
            mappingEntity.setResourceId(tool.getToolId());
            mappingEntity.setResourceType(CommonConstant.TOOL_TYPE);
            mappingEntity.setResourceName(tool.getToolDisplayName());
            mappingEntity.setResourceVersion(tool.getVersionId());
            if (ObjectUtils.isNotEmpty(shareWorkflow)) {
                if (Strings.CS.equals(shareWorkflow.getResourceId(), pluginAdapterImpl.getPluginId(tool.getToolId()))) {
                    mappingEntity.setReferenceType(ReferenceTypeEnum.SHARE.getValue());
                } else {
                    mappingEntity.setReferenceType(ReferenceTypeEnum.DIRECT.getValue());
                }
            }
            mappingMapper.insert(mappingEntity);
        }
    }

    /**
     * 处理预置插件
     *
     * @param projectId projectId
     * @param tool tool
     * @param innerMsg innerMsg
     */
    private void parseWorkflowInnerTool(String projectId, ToolEntity tool, Set<ExtraMsg> innerMsg) {
        if (!ToolType.INNER.type.equals(tool.getType()) || opSvcProjectId.equals(projectId)) {
            return;
        }

        // 添加预置插件提示信息
        String toolId = pluginAdapterImpl.getPluginId(tool.getToolId());
        if (toolMapperDiscard.selectByProjectId(toolId, projectId, opSvcProjectId) == null) {
            innerMsg.add(new ExtraMsg().setId(toolId).setName(tool.getToolDisplayName()));
        }
    }

    /**
     * 记录agent和workflows的关联关系
     *
     * @param agent agent元数据
     * @param workflows 工作流导出对象列表
     */
    @Transactional
    public void importMapperAgentWorkflows(Agent agent, List<WorkflowExportEntity> workflows) {
        List<MappingEntity> relateWorkflows = new ArrayList<>();

        // 先删除关联关系
        mappingMapper.deleteBatchByAppIdAndResourceType(agent.getAgentId(), CommonConstant.WORKFLOW_TYPE);
        for (WorkflowExportEntity workflow : workflows) {
            // 记录关联关系
            relateWorkflows.add(buildAgentWorkflowMapping(agent, workflow));
        }
        if (!CollectionUtils.isEmpty(relateWorkflows)) {
            mappingMapper.insertBatch(relateWorkflows);
        }
    }

    /**
     * 构造agent和workflow的关联关系
     *
     * @param agent agent元数据
     * @param workflow 工作流导出对象
     * @return agent和workflow的关联关系对象
     */
    private MappingEntity buildAgentWorkflowMapping(Agent agent, WorkflowExportEntity workflow) {
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setMappingId(UUID.randomUUID().toString());
        mappingEntity.setAppId(agent.getAgentId());
        mappingEntity.setAppName(agent.getName());
        mappingEntity.setAppType(CommonConstant.AGENT_TYPE);
        WorkflowEntity workflowMetadata = workflow.getMetadata();
        mappingEntity.setResourceId(workflowMetadata.getId());
        mappingEntity.setResourceName(workflowMetadata.getName());
        mappingEntity.setResourceDesc(workflowMetadata.getDescription());
        mappingEntity.setResourceType(CommonConstant.WORKFLOW_TYPE);
        if (workflow.getReleaseVersion() != null) {
            mappingEntity.setResourceVersion(workflow.getReleaseVersion().getVersionId());
        }
        return mappingEntity;
    }

    /**
     * 构建控制器和子控制器之间的关联关系
     *
     * @param agent agent元数据
     * @param subAgent 子agent元数据
     * @return agent和子gent的关联关系对象
     */
    private MappingEntity buildSubAgentMapping(Agent agent, AgentExportEntity subAgent) {
        MappingEntity subAgentMappingEntity = new MappingEntity();
        subAgentMappingEntity.setMappingId(UUID.randomUUID().toString());
        subAgentMappingEntity.setAppId(agent.getAgentId());
        subAgentMappingEntity.setAppName(agent.getName());
        subAgentMappingEntity.setAppType(CommonConstant.AGENT_TYPE);

        subAgentMappingEntity.setResourceId(subAgent.getMetadata().getAgentId());
        subAgentMappingEntity.setResourceName(subAgent.getMetadata().getName());
        subAgentMappingEntity.setResourceDesc(subAgent.getMetadata().getDescription());
        subAgentMappingEntity.setResourceType(CommonConstant.CONTROLLER_TYPE);
        if (ObjectUtils.isNotEmpty(subAgent.getReleaseVersion())) {
            subAgentMappingEntity.setResourceVersion(subAgent.getReleaseVersion().getVersionId());
        }
        return subAgentMappingEntity;
    }

    /**
     * 构建控制器和子控制器之间的关联关系
     *
     * @param agent agent元数据
     * @param subAgent 子agent元数据
     * @return agent和子gent的关联关系对象
     */
    private MappingEntity buildSingleAgentMapping(Agent agent, AgentExportEntity subAgent) {
        MappingEntity subAgentMappingEntity = new MappingEntity();
        subAgentMappingEntity.setMappingId(UUID.randomUUID().toString());
        subAgentMappingEntity.setAppId(agent.getAgentId());
        subAgentMappingEntity.setAppName(agent.getName());
        subAgentMappingEntity.setAppType(CommonConstant.AGENT_TYPE);

        subAgentMappingEntity.setResourceId(subAgent.getMetadata().getAgentId());
        subAgentMappingEntity.setResourceName(subAgent.getMetadata().getName());
        subAgentMappingEntity.setResourceDesc(subAgent.getMetadata().getDescription());
        subAgentMappingEntity.setResourceType(CommonConstant.AGENT_TYPE);
        if (ObjectUtils.isNotEmpty(subAgent.getReleaseVersion())) {
            subAgentMappingEntity.setResourceVersion(subAgent.getReleaseVersion().getVersionId());
        }
        return subAgentMappingEntity;
    }

    /**
     * 导出多Agent工作流节点
     *
     * @param workflows 工作流列表
     * @param node 工作流节点
     * @param projectId projectId
     */
    private void exportControllerWorkflow(List<WorkflowExportEntity> workflows, ControllerNodeVO node,
        String projectId) {
        WorkflowNodeConfigVO wfNodeConfigs = JsonUtils.objectToClassType(node.getConfigs(), WorkflowNodeConfigVO.class);
        String id = wfNodeConfigs.getId();
        String versionId = wfNodeConfigs.getVersionId();

        // 避免重复导出
        if (isWorkflowDuplicateWithVersion(workflows, id, versionId)) {
            return;
        }

        ShareResourceEntity shareResourceEntity = shareResourceManagerService.queryShareResourceEntityByResourceId(id);

        if (shareResourceEntity != null && !Strings.CS.equals(RequestContextUtils.getRequestWorkspaceId(),
            shareResourceEntity.getWorkspaceId())) {
            return;
        }

        // 导出对应版本的工作流配置
        WorkflowEntity workflowEntity =
            workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId, ThreadLocalUtils.getWorkspaceId(), id);
        WorkflowExportEntity workflow = mergeWorkflow(projectId, workflowEntity, versionId);
        workflows.add(workflow);
    }

    /**
     * 导出多Agent控制器节点全局意图中的工作流
     *
     * @param workflows 工作流列表
     * @param node 控制器节点
     * @param projectId projectId
     */
    private void exportGlobalIntentWorkflows(List<WorkflowExportEntity> workflows, ControllerNodeVO node,
        String projectId) {
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassType(node.getConfigs(), ControllerNodeConfigVO.class);
        List<ControllerNodeConfigVOGlobalIntents> globalIntents = null;
        if (controllerNodeConfigVo != null) {
            globalIntents = controllerNodeConfigVo.getGlobalIntents();
        }
        if (CollectionUtils.isEmpty(globalIntents)) {
            return;
        }

        // 从全局意图配置中获取工作流信息
        List<ControllerNodeVO> intentWorkflows = globalIntents.stream()
            .filter(intent -> IntentHandlerType.WORKFLOW.getDsl().equalsIgnoreCase(intent.getHandlerType()))
            .map(intent -> JsonUtils.objectToClassType(intent.getHandler(), ControllerNodeVO.class))
            .toList();

        // 导出工作流配置
        for (ControllerNodeVO intentWorkflow : intentWorkflows) {
            exportControllerWorkflow(workflows, intentWorkflow, projectId);
        }
    }

    /**
     * 导出多Agent子控制器节点
     *
     * @param agents 控制器列表
     * @param node 控制器节点
     * @param projectId projectId
     */
    private void exportController(List<AgentExportEntity> agents, String workspaceId, ControllerNodeVO node,
        String projectId) {
        WorkflowNodeConfigVO wfNodeConfigs = JsonUtils.objectToClassType(node.getConfigs(), WorkflowNodeConfigVO.class);
        if (wfNodeConfigs == null) {
            log.error("controller node config should not be empty!");
            return;
        }
        String id = wfNodeConfigs.getId();
        String versionId = wfNodeConfigs.getVersionId();

        // 导出对应版本的工作流配置
        Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, id);
        AgentExportEntity agentExportEntity = mergeAgents(projectId, workspaceId, agent, versionId);
        agents.add(agentExportEntity);
    }

    /**
     * 导出多Agent子控制器节点
     *
     * @param agents 控制器列表
     * @param node 控制器节点
     * @param projectId projectId
     */
    private void exportSingleAgent(List<AgentExportEntity> agents, String workspaceId, ControllerNodeVO node,
                                  String projectId) {
        WorkflowNodeConfigVO wfNodeConfigs = JsonUtils.objectToClassType(node.getConfigs(), WorkflowNodeConfigVO.class);
        if (wfNodeConfigs == null) {
            log.error("agent node config should not be empty!");
            return;
        }
        String id = wfNodeConfigs.getId();
        String versionId = wfNodeConfigs.getVersionId();

        // 导出对应版本的单智能体配置
        Agent agent = agentMapper.selectByProjectIdAndWorkspaceId(projectId, workspaceId, id);
        AgentExportEntity agentExportEntity = new AgentExportEntity();
        agentExportEntity.setMetadata(agent);
        handleSingleAgent(projectId, workspaceId, id, agentExportEntity, versionId);
        ReleaseVersion releaseVersion =
            releaseVersionMapper.selectByAppIdAndVersionId(agent.getAgentId(), versionId);
        agentExportEntity.setReleaseVersion(releaseVersion);

        String dslPath = releaseVersion.getDslPath();
        // 根据dslPath从OBS中获取DSL文件
        String agentInfo = mgObsService.downloadObsFile(dslPath);
        agentExportEntity.setSingleAgentDsl(JSON.parseObject(agentInfo, AgentInfo.class));
        agents.add(agentExportEntity);
    }

    /**
     * MCP服务相关依赖关系入库
     *
     * @param mcpServer mcpServer
     * @param mappingEntity mappingEntity
     */
    private boolean importMcpMapping(McpServerInfo mcpServer, MappingEntity mappingEntity) {
        try {
            MappingEntity mappingAgentMCp =
                mappingMapper.selectByAppIdAndResourceId(mappingEntity.getAppId(), mcpServer.getServerId());
            MappingEntity mcpMappingEntity = buildMcpMapping(mcpServer, mappingEntity);
            if (mappingAgentMCp != null) {
                // 更新依赖关系
                mcpMappingEntity.setMappingId(mappingAgentMCp.getMappingId());
                mappingMapper.updateByPrimaryKeySelective(mcpMappingEntity);
            } else {
                // 添加依赖关系
                mappingEntity.setMappingId(UUID.randomUUID().toString());
                mappingMapper.insert(mcpMappingEntity);
            }
        } catch (Exception e) {
            log.error("Failed to import mcp mapping!", e);
            return false;
        }
        return true;
    }

    private MappingEntity buildMcpMapping(McpServerInfo mcpServer, MappingEntity mappingEntity) {
        String serverId = mcpServer.getServerId();
        mappingEntity.setResourceId(serverId);
        mappingEntity.setResourceName(mcpServer.getName());
        mappingEntity.setResourceDesc(mcpServer.getDesc());
        mappingEntity.setResourceType(CommonConstant.MCP_TYPE);
        if (mcpInnerService.getMcpServerInfoById(serverId, null) == null) {
            mappingEntity.setValid(false);
        }
        return mappingEntity;
    }

    /**
     * 用UUID替换workflow导出配置中的id
     *
     * @param workflowExportEntity workflow配置对象
     * @return UUID替换后的workflow配置对象
     */
    public WorkflowExportEntity replaceWorkflowExportId(WorkflowExportEntity workflowExportEntity,
        String targetWorkspaceId, String workflowId, String projectId, WfImportDataWrapper wfImportDataWrapper) {
        List<String> workflowIds = wfImportDataWrapper.getImportWorkflowList();
        Map<String, String> idToUuid = wfImportDataWrapper.getIdToUuid();
        try {
            // 工作流id替换为UUID
            String uuid = idToUuid.getOrDefault(workflowId, UUID.randomUUID().toString());
            idToUuid.put(workflowId, uuid);
            workflowIds.add(uuid);
            workflowExportEntity.getMetadata()
                .setTraceId(StringUtils.isBlank(workflowExportEntity.getMetadata().getTraceId()) ? workflowId
                    : workflowExportEntity.getMetadata().getTraceId());
            workflowExportEntity.getMetadata().setId(uuid);
            workflowExportEntity.getDsl().setId(uuid);

            // 替换依赖的插件id为UUID
            List<ToolEntity> plugins = workflowExportEntity.getPlugins();
            List<ToolEntity> newPlugins = replaceToolsId(projectId, targetWorkspaceId, plugins, wfImportDataWrapper);
            workflowExportEntity.setPlugins(newPlugins);

            // 替换依赖的MCP id为UUID
            List<McpServerInfo> mcpServers = workflowExportEntity.getMcpServers();
            List<McpServerInfo> newMcpServers = replaceMcpServersId(targetWorkspaceId, mcpServers, wfImportDataWrapper);
            workflowExportEntity.setMcpServers(newMcpServers);

            // 替换依赖的子工作流id为UUID
            List<WorkflowExportEntity> subWorkflows = workflowExportEntity.getSubWorkflows();
            List<WorkflowExportEntity> newSubWorkflows =
                replaceWorkflowsId(projectId, targetWorkspaceId, subWorkflows, wfImportDataWrapper);
            workflowExportEntity.setSubWorkflows(newSubWorkflows);

            // 设置DSL中的节点id配置
            List<WorkflowNodeVO> nodes = workflowExportEntity.getDsl().getNodes();
            for (WorkflowNodeVO node : nodes) {
                NodeType nodeType = NodeType.fromType(node.getType());
                if (nodeType != null) {
                    switch (nodeType) {
                        case WORKFLOW, PLUGIN, MCP -> {
                            String resId = node.getConfigs().get(WorkflowNodeAdapter.ID).toString();
                            node.getConfigs().put(WorkflowNodeAdapter.ID, idToUuid.getOrDefault(resId, resId));
                        }
                        case INTENT_DETECTION_CONTAINER -> node.getBranches().forEach(branch -> {
                            String resId = branch.getConfigs().get(WORKFLOW_ID).toString();
                            branch.getConfigs().put(WORKFLOW_ID, idToUuid.getOrDefault(resId, resId));
                        });
                        case PARAM_EXTRACTION -> {
                            List<Object> domainObjects = JsonUtils.objectToClass(node.getConfigs().get(DOMAIN_OBJECTS));
                            if (CollectionUtils.isNotEmpty(domainObjects)) {
                                List<ParamExtractionDomainObject> adaptedObjects = new ArrayList<>();
                                for (Object item : domainObjects) {
                                    ParamExtractionDomainObject domainObject =
                                        JsonUtils.objectToClassType(item, ParamExtractionDomainObject.class);
                                    if (domainObject == null) {
                                        continue;
                                    }
                                    // 替换子工作流ID
                                    if (CollectionUtils.isNotEmpty(domainObject.getProcessingWorkflows())) {
                                        domainObject.getProcessingWorkflows()
                                            .forEach(processingWorkflow -> processingWorkflow.setId(idToUuid
                                                .getOrDefault(processingWorkflow.getId(), processingWorkflow.getId())));
                                    }
                                    adaptedObjects.add(domainObject);
                                }
                                node.getConfigs().put(DOMAIN_OBJECTS, adaptedObjects);
                            }
                            List<Object> extensionWorkflows =
                                JsonUtils.objectToClass(node.getConfigs().get(EXTENSION_WORKFLOWS));
                            if (CollectionUtils.isNotEmpty(extensionWorkflows)) {
                                List<ParamExtractionWorkflow> adaptedExtensions = new ArrayList<>();
                                extensionWorkflows.forEach(item -> {
                                    ParamExtractionWorkflow extensionWorkflow =
                                        JsonUtils.objectToClassType(item, ParamExtractionWorkflow.class);
                                    if (extensionWorkflow != null) {
                                        extensionWorkflow.setId(idToUuid.getOrDefault(extensionWorkflow.getId(),
                                            extensionWorkflow.getId()));
                                        adaptedExtensions.add(extensionWorkflow);
                                    }
                                });
                                node.getConfigs().put(EXTENSION_WORKFLOWS, adaptedExtensions);
                            }
                        }
                        default -> {
                        }
                    }
                }
            }
            return workflowExportEntity;
        } catch (Exception e) {
            log.error("Failed to convert UUID", e);
            throw new AgentStudioException(StudioError.ID_TO_UUID_FAIL);
        }
    }

    /**
     * 用UUID替换agent导出配置中的id
     *
     * @param agentExportEntity agent配置对象
     * @return UUID替换后的agent配置对象
     */
    public AgentExportEntity replaceAgentExportId(AgentExportEntity agentExportEntity, String targetWorkspaceId,
        String projectId, WfImportDataWrapper wfImportDataWrapper) {
        Map<String, String> idToUuid = wfImportDataWrapper.getIdToUuid();
        Agent agentMetadata = agentExportEntity.getMetadata();
        try {

            // 将该agent的id替换为UUID
            String agentId = agentMetadata.getAgentId();
            String uuid = idToUuid.computeIfAbsent(agentId, id -> UUID.randomUUID().toString());
            agentMetadata.setAgentId(uuid);
            agentMetadata
                .setTraceId(StringUtils.isBlank(agentMetadata.getTraceId()) ? agentId : agentMetadata.getTraceId());
            wfImportDataWrapper.getImportAgentList().add(uuid);

            // 替换依赖的插件id为UUID
            List<ToolEntity> plugins = agentExportEntity.getPlugins();
            List<ToolEntity> newPlugins = replaceToolsId(projectId, targetWorkspaceId, plugins, wfImportDataWrapper);
            agentExportEntity.setPlugins(newPlugins);

            // 替换依赖的MCP id为UUID
            List<McpServerInfo> mcpServers = agentExportEntity.getMcpServers();
            List<McpServerInfo> newMcpServers = replaceMcpServersId(targetWorkspaceId, mcpServers, wfImportDataWrapper);
            agentExportEntity.setMcpServers(newMcpServers);

            // 替换依赖的工作流id为UUID
            List<WorkflowExportEntity> workflows = agentExportEntity.getWorkflows();
            List<WorkflowExportEntity> newWorkflows =
                replaceWorkflowsId(projectId, targetWorkspaceId, workflows, wfImportDataWrapper);
            agentExportEntity.setWorkflows(newWorkflows);

            // 替换依赖的Agent id为UUID
            List<AgentExportEntity> agents = agentExportEntity.getAgents();
            List<AgentExportEntity> newAgents =
                replaceAgentsId(projectId, targetWorkspaceId, agents, wfImportDataWrapper);
            agentExportEntity.setAgents(newAgents);

            // 替换依赖的Single Agent id为UUID
            List<AgentExportEntity> singleAgents = agentExportEntity.getSingleAgents();
            List<AgentExportEntity> newSingleAgents =
                    replaceAgentsId(projectId, targetWorkspaceId, singleAgents, wfImportDataWrapper);
            agentExportEntity.setSingleAgents(newSingleAgents);

            // 设置多智能体DSL中的节点id配置
            if (agentExportEntity.getDsl() != null) {
                ControllerVO dsl = agentExportEntity.getDsl();
                dsl.setId(uuid);

                // 设置DSL中workflow的当前id,维持关联关系
                List<ControllerNodeVO> nodes = dsl.getNodes();
                for (ControllerNodeVO node : nodes) {
                    if (NodeType.WORKFLOW.getType().equalsIgnoreCase(node.getType())) {
                        replaceWorkflowNodeId(node, idToUuid);
                    } else if (AgentNodeType.CONTROLLER.getType()
                        .equalsIgnoreCase(node.getType())) {
                        replaceControllerNodeId(node, idToUuid);
                    } else if (AgentNodeType.SUB_CONTROLLER
                        .getType()
                        .equalsIgnoreCase(node.getType())) {
                        replaceControllerNodeId(node, idToUuid);
                    } else if (AgentNodeType.AGENT.getType()
                        .equalsIgnoreCase(node.getType())) {
                        replaceControllerNodeId(node, idToUuid);
                    }
                }
            }
            return agentExportEntity;
        } catch (Exception e) {
            log.error("Failed to convert UUID", e);
            throw new AgentStudioException(StudioError.ID_TO_UUID_FAIL);
        }
    }

    /**
     * 替换多Agent工作流节点id
     *
     * @param node 工作流节点
     * @param idToUuid UUID映射
     */
    private void replaceWorkflowNodeId(ControllerNodeVO node, Map<String, String> idToUuid) {
        WorkflowNodeConfigVO wfNodeConfigs = JsonUtils.objectToClassType(node.getConfigs(), WorkflowNodeConfigVO.class);
        if (wfNodeConfigs != null) {
            String id = wfNodeConfigs.getId();
            wfNodeConfigs.setId(idToUuid.getOrDefault(id, id));
            node.setConfigs(wfNodeConfigs);
        }
    }

    /**
     * 替换控制器节点中的工作流id
     *
     * @param node 控制器节点
     * @param idToUuid UUID映射
     */
    private void replaceControllerNodeId(ControllerNodeVO node, Map<String, String> idToUuid) {
        ControllerNodeConfigVO controllerNodeConfigVo =
            JsonUtils.objectToClassType(node.getConfigs(), ControllerNodeConfigVO.class);

        // 替换子agent id
        if (controllerNodeConfigVo != null && StringUtils.isNotEmpty(controllerNodeConfigVo.getId())) {
            controllerNodeConfigVo
                .setId(idToUuid.getOrDefault(controllerNodeConfigVo.getId(), controllerNodeConfigVo.getId()));
        }

        // 替换configs.workflows中的id
        List<ControllerNodeConfigVOWorkflows> controllerNodeConfigVOWorkflows = null;
        if (controllerNodeConfigVo != null) {
            controllerNodeConfigVOWorkflows = controllerNodeConfigVo.getWorkflows();
        }
        if (controllerNodeConfigVOWorkflows != null && !controllerNodeConfigVOWorkflows.isEmpty()) {
            controllerNodeConfigVOWorkflows
                .forEach(workflow -> workflow.setId(idToUuid.getOrDefault(workflow.getId(), workflow.getId())));
        }

        // 替换configs.agents中的id
        List<ControllerNodeConfigVOAgents> controllerNodeConfigVOAgents = null;
        if (controllerNodeConfigVo != null) {
            controllerNodeConfigVOAgents = controllerNodeConfigVo.getAgents();
        }
        if (controllerNodeConfigVOAgents != null && !controllerNodeConfigVOAgents.isEmpty()) {
            controllerNodeConfigVOAgents
                .forEach(agent -> agent.setId(idToUuid.getOrDefault(agent.getId(), agent.getId())));
        }

        // 全局意图中没有绑定工作流，直接return
        List<ControllerNodeConfigVOGlobalIntents> controllerNodeConfigVOGlobalIntents = null;
        if (controllerNodeConfigVo != null) {
            controllerNodeConfigVOGlobalIntents = controllerNodeConfigVo.getGlobalIntents();
        }
        if (CollectionUtils.isEmpty(controllerNodeConfigVOGlobalIntents)) {
            node.setConfigs(controllerNodeConfigVo);
            return;
        }

        // 替换全局意图配置中获取工作流id
        for (ControllerNodeConfigVOGlobalIntents globalIntent : controllerNodeConfigVOGlobalIntents) {
            if (!IntentHandlerType.WORKFLOW.getDsl().equalsIgnoreCase(globalIntent.getHandlerType())) {
                continue;
            }

            ControllerNodeVO controllerNodeVO =
                JsonUtils.objectToClassType(globalIntent.getHandler(), ControllerNodeVO.class);
            if (controllerNodeVO != null) {
                replaceWorkflowNodeId(controllerNodeVO, idToUuid);
                controllerNodeVO.setId(idToUuid.getOrDefault(controllerNodeVO.getId(), controllerNodeVO.getId()));
                globalIntent.setHandler(controllerNodeVO);
            }
        }
        node.setConfigs(controllerNodeConfigVo);
    }

    /**
     * 替换依赖插件的id为UUID
     *
     * @param targetWorkspaceId targetWorkspaceId
     * @param mcpServers 依赖的MCP服务列表
     * @param wfImportDataWrapper 要导入的插件ids
     * @return List<ToolEntity>
     */
    private List<McpServerInfo> replaceMcpServersId(String targetWorkspaceId, List<McpServerInfo> mcpServers,
        WfImportDataWrapper wfImportDataWrapper) {
        Map<String, String> idToUuid = wfImportDataWrapper.getIdToUuid();
        if (CollectionUtils.isEmpty(mcpServers)) {
            return mcpServers;
        }

        // 替换id保证唯一
        for (McpServerInfo mcpServer : mcpServers) {
            // 预置MCP服务id保持不变，确保可以正确关联
            if (ToolType.INNER.type.equals(mcpServer.getType())) {
                continue;
            }

            // id不冲突
            String id = mcpServer.getServerId();
            if (mcpInnerService.isMcpExist(targetWorkspaceId, mcpServer.getName())) {
                McpServiceEntity mcpServiceEntity =
                    mcpInnerService.getMcpByName(targetWorkspaceId, mcpServer.getName());
                wfImportDataWrapper.getIdToUuid().put(id, mcpServiceEntity.getId());
                mcpServer.setServerId(mcpServiceEntity.getId());
            } else {
                String uuid = idToUuid.getOrDefault(id, UUID.randomUUID().toString());
                wfImportDataWrapper.getIdToUuid().put(id, uuid);
                mcpServer.setServerId(uuid);
            }
        }
        return mcpServers;
    }

    /**
     * 替换依赖插件的id为UUID
     *
     * @param projectId projectId
     * @param plugins 依赖插件列表
     * @param wfImportDataWrapper 要导入的插件ids
     * @return List<ToolEntity>
     */
    private List<ToolEntity> replaceToolsId(String projectId, String targetWorkspaceId, List<ToolEntity> plugins,
        WfImportDataWrapper wfImportDataWrapper) {
        Map<String, String> idToUuid = wfImportDataWrapper.getIdToUuid();
        List<String> importToolList = wfImportDataWrapper.getImportToolList();
        if (plugins != null && !plugins.isEmpty()) {
            for (ToolEntity plugin : plugins) {
                if (ToolType.INNER.type.equals(plugin.getType())) {
                    continue;
                }
                String toolId = plugin.getToolId();
                plugin.setTraceId(StringUtils.isBlank(plugin.getTraceId()) ? toolId : plugin.getTraceId());
                if (CommonConstant.PLUGIN_INNER_TYPE.equals(plugin.getType())) {
                    continue;
                }
                if (!importToolList.contains(toolId) || isToolExistInWorkspace(projectId, targetWorkspaceId, plugin)
                    || toolMapperDiscard.selectWithoutStatus(pluginAdapterImpl.getPluginId(toolId), null,
                        null) == null) {
                    if (isToolExistInWorkspace(projectId, targetWorkspaceId, plugin)) {
                        List<PluginEntity> toolEntityList = pluginMapper.selectByTraceIdAndWorkspaceId(projectId,
                            targetWorkspaceId, plugin.getTraceId());
                        idToUuid.put(toolId, toolEntityList.get(0).getPluginId());
                        importToolList.add(toolEntityList.get(0).getPluginId());
                        plugin.setToolId(toolEntityList.get(0).getPluginId());
                    }
                } else {
                    String uuid = idToUuid.getOrDefault(toolId, UUID.randomUUID().toString());
                    idToUuid.put(toolId, uuid);
                    importToolList.add(uuid);
                    plugin.setToolId(uuid);
                }
            }
        }
        return plugins;
    }

    /**
     * 替换依赖控制器的id为UUID
     *
     * @param projectId projectId
     * @param agents 依赖的agent列表
     * @param importDataWrapper 导入中间变量存储类
     * @return List<AgentExportEntity>
     */
    private List<AgentExportEntity> replaceAgentsId(String projectId, String targetWorkspaceId,
        List<AgentExportEntity> agents, WfImportDataWrapper importDataWrapper) {
        List<String> agentIds = importDataWrapper.getImportAgentList();
        if (!CollectionUtils.isEmpty(agents)) {
            for (int i = 0; i < agents.size(); i++) {
                AgentExportEntity agentExportEntity = agents.get(i);
                String agentId = agentExportEntity.getMetadata().getAgentId();
                if (!agentIds.contains(agentId)) {
                    continue;
                }

                // 如果在环境中不存在，则不需要替换ID。如果是自己空间下已经有的，则把元数据中的ID替换成已经存在的
                String existingAgentId =
                    getExistingAgentId(projectId, targetWorkspaceId, agentExportEntity.getMetadata());
                if (agentMapper.countAgentIdInDb(agentId) <= 0 || StringUtils.isNotEmpty(existingAgentId)) {
                    if (StringUtils.isNotEmpty(existingAgentId)) {
                        importDataWrapper.getIdToUuid().put(agentId, existingAgentId);
                    } else {
                        importDataWrapper.getIdToUuid().put(agentId, agentId);
                    }
                }

                AgentExportEntity newAgent =
                    replaceAgentExportId(agentExportEntity, targetWorkspaceId, projectId, importDataWrapper);
                agents.set(i, newAgent);
            }
        }
        return agents;
    }

    /**
     * 替换依赖工作流的id为UUID
     *
     * @param projectId projectId
     * @param workflows 依赖的workflow列表
     * @param wfImportDataWrapper 导入包装类
     * @return List<WorkflowExportEntity>
     */
    private List<WorkflowExportEntity> replaceWorkflowsId(String projectId, String targetWorkspaceId,
        List<WorkflowExportEntity> workflows, WfImportDataWrapper wfImportDataWrapper) {
        List<String> workflowIds = wfImportDataWrapper.getImportWorkflowList();
        if (!CollectionUtils.isEmpty(workflows)) {
            for (int i = 0; i < workflows.size(); i++) {
                WorkflowExportEntity workflowExportEntity = workflows.get(i);
                String workflowId = workflowExportEntity.getMetadata().getId();
                if (!workflowIds.contains(workflowId)) {
                    continue;
                }

                // 如果在环境中不存在，则不需要替换ID。如果是自己空间下已经有的，则把元数据中的ID替换成已经存在的
                String existingWorkflowId =
                    getExistingWorkflowId(projectId, targetWorkspaceId, workflowExportEntity.getMetadata());
                if (workflowMapper.countWorkflowIdInDb(workflowId) <= 0 || StringUtils.isNotEmpty(existingWorkflowId)) {
                    if (StringUtils.isNotEmpty(existingWorkflowId)) {
                        wfImportDataWrapper.getIdToUuid().put(workflowId, existingWorkflowId);
                    } else {
                        wfImportDataWrapper.getIdToUuid().put(workflowId, workflowId);
                    }
                }

                WorkflowExportEntity newWorkflow = replaceWorkflowExportId(workflowExportEntity, targetWorkspaceId,
                    workflowId, projectId, wfImportDataWrapper);
                workflows.set(i, newWorkflow);
            }
        }
        return workflows;
    }

    /**
     * 判断当前空间下面Agent是否已经存在
     *
     * @param projectId projectId
     * @param metadata 应用元数据
     * @return Boolean
     */
    private Boolean isAgentExistInWorkspace(String projectId, String workspaceId, Agent metadata) {
        metadata.setTraceId(StringUtils.isBlank(metadata.getTraceId()) ? metadata.getAgentId() : metadata.getTraceId());
        List<Agent> agentList =
            agentMapper.selectAgentByTraceIdAndWorkspaceId(projectId, workspaceId, metadata.getTraceId());
        return !CollectionUtils.isEmpty(agentList);
    }

    /**
     * 判断当前空间下工具是否已经存在
     *
     * @param projectId projectId
     * @param tool 插件
     * @return Boolean
     */
    public Boolean isToolExistInWorkspace(String projectId, String workspaceId, ToolEntity tool) {
        tool.setTraceId(StringUtils.isBlank(tool.getTraceId()) ? tool.getToolId() : tool.getTraceId());
        List<PluginEntity> toolEntityList =
            pluginMapper.selectByTraceIdAndWorkspaceId(projectId, workspaceId, tool.getTraceId());
        return !CollectionUtils.isEmpty(toolEntityList);
    }

    /**
     * 判断当前空间下工具是否已经存在
     *
     * @param projectId projectId
     * @param tool 插件
     * @return Boolean
     */
    public Boolean isPluginExistInWorkspace(String projectId, String workspaceId, PluginEntity tool) {
        tool.setTraceId(StringUtils.isBlank(tool.getTraceId()) ? tool.getPluginId() : tool.getTraceId());
        List<PluginEntity> toolEntityList =
            pluginMapper.selectByTraceIdAndWorkspaceId(projectId, workspaceId, tool.getTraceId());
        return !CollectionUtils.isEmpty(toolEntityList);
    }

    /**
     * 判断当前空间下工作流是否已经存在
     *
     * @param projectId projectId
     * @param metadata 工作流元数据
     * @return Boolean
     */
    private Boolean isWorkflowExistInWorkspace(String projectId, String workspaceId, WorkflowEntity metadata) {
        metadata.setTraceId(StringUtils.isBlank(metadata.getTraceId()) ? metadata.getId() : metadata.getTraceId());
        List<WorkflowEntity> workflowEntityList =
            workflowMapper.selectByTraceId(projectId, workspaceId, metadata.getTraceId());
        return !CollectionUtils.isEmpty(workflowEntityList);
    }

    /**
     * 根据 traceId 查询在指定工作空间中是否已存在对应的Agent。
     */
    private String getExistingAgentId(String projectId, String workspaceId, Agent metadata) {
        metadata.setTraceId(StringUtils.isBlank(metadata.getTraceId()) ? metadata.getAgentId() : metadata.getTraceId());
        List<Agent> agentList =
            agentMapper.selectAgentByTraceIdAndWorkspaceId(projectId, workspaceId, metadata.getTraceId());

        if (CollectionUtils.isEmpty(agentList)) {
            return null;
        }
        return agentList.get(0).getAgentId();
    }

    /**
     * 根据 traceId 查询在指定工作空间中是否已存在对应的Workflow。
     */
    private String getExistingWorkflowId(String projectId, String workspaceId, WorkflowEntity metadata) {
        String traceId = StringUtils.isBlank(metadata.getTraceId()) ? metadata.getId() : metadata.getTraceId();
        List<WorkflowEntity> workflowEntityList = workflowMapper.selectByTraceId(projectId, workspaceId, traceId);
        if (CollectionUtils.isEmpty(workflowEntityList)) {
            return null;
        }
        return workflowEntityList.get(0).getId();
    }

    /**
     * 解析插件
     *
     * @param projectId projectId
     * @param importList 解析出来的配置对象list
     * @param tool 插件配置对象
     */
    public void resolveTools(String projectId, List<ImportListInfo> importList, ToolEntity tool) {

        // 设置方法返回值中的参数
        ImportListInfo importToolInfo = new ImportListInfo().setId(tool.getToolId())
            .setName(tool.getToolDisplayName())
            .setDescription(tool.getToolDesc())
            .setType(CommonConstant.PLUGIN);

        // 判断环境中是否已存在该插件配置
        importToolInfo.setStatus(isToolExistInWorkspace(projectId, RequestContextUtils.getRequestWorkspaceId(), tool));
        importToolInfo.setProhibited(ToolType.INNER.type.equals(tool.getType()) && !opSvcProjectId.equals(projectId));
        importList.add(importToolInfo);
    }

    /**
     * 解析插件
     *
     * @param projectId projectId
     * @param importList 解析出来的配置对象list
     * @param plugin 插件配置对象
     */
    public void resolvePlugins(String projectId, List<ImportListInfo> importList, PluginEntity plugin) {

        // 设置方法返回值中的参数
        ImportListInfo importToolInfo = new ImportListInfo().setId(plugin.getPluginId())
            .setName(plugin.getPluginDisplayName())
            .setDescription(plugin.getPluginDesc())
            .setType(CommonConstant.PLUGIN);

        // 判断环境中是否已存在该插件配置
        importToolInfo
            .setStatus(isPluginExistInWorkspace(projectId, RequestContextUtils.getRequestWorkspaceId(), plugin));
        importToolInfo.setProhibited(ToolType.INNER.type.equals(plugin.getType()) && !opSvcProjectId.equals(projectId));
        importList.add(importToolInfo);
    }

    /**
     * 解析workflow json
     *
     * @param projectId projectId
     * @param importList 解析出来的配置对象list
     * @param workflowExportEntity 工作流配置对象
     */
    public void resolveWorkflows(String projectId, List<ImportListInfo> importList,
        WorkflowExportEntity workflowExportEntity) {
        List<ImportListInfo> dependencyInfos = new ArrayList<>();
        // 解析工作流依赖的插件
        List<ToolEntity> plugins = workflowExportEntity.getPlugins();
        if (CollectionUtils.isNotEmpty(plugins)) {
            plugins.forEach(p -> resolveTools(projectId, dependencyInfos, p));
        }
        // 解析工作流依赖的子工作流
        List<WorkflowExportEntity> subWorkflows = workflowExportEntity.getSubWorkflows();
        if (CollectionUtils.isNotEmpty(subWorkflows)) {
            subWorkflows.forEach(p -> resolveWorkflows(projectId, dependencyInfos, p));
        }

        // 设置方法返回值中的参数
        WorkflowEntity metadata = workflowExportEntity.getMetadata();
        ImportListInfo importWorkflowInfo = new ImportListInfo().setId(metadata.getId())
            .setName(metadata.getName())
            .setDescription(metadata.getDescription())
            .setType(CommonConstant.WORKFLOW)
            .setDependencies(dependencyInfos);

        // 判断环境中是否已存在该工作流配置
        ListWorkflowsQo listWorkflowsQo = new ListWorkflowsQo();
        listWorkflowsQo.setId(metadata.getId());
        listWorkflowsQo.setWorkspaceId(RequestContextUtils.getRequestWorkspaceId());
        List<WorkflowEntity> workflowEntities =
            workflowMapper.selectByCreatorId(RequestContextUtils.getRequestUserId(), projectId, listWorkflowsQo);
        importWorkflowInfo.setStatus(CollectionUtils.isNotEmpty(workflowEntities));
        importList.add(importWorkflowInfo);
    }

    /**
     * 解析Agent json
     *
     * @param projectId projectId
     * @param importList 解析出来的配置对象list
     * @param agentExportEntity Agent配置对象
     */
    public void resolveAgents(String projectId, List<ImportListInfo> importList, AgentExportEntity agentExportEntity) {
        // 解析Agent依赖的插件
        List<ImportListInfo> dependencyInfos = new ArrayList<>();
        List<ToolEntity> plugins = agentExportEntity.getPlugins();
        if (plugins != null && !plugins.isEmpty()) {
            for (ToolEntity tool : plugins) {
                resolveTools(projectId, dependencyInfos, tool);
            }
        }

        // 解析Agent依赖的workflow
        List<WorkflowExportEntity> workflows = agentExportEntity.getWorkflows();
        if (workflows != null && !workflows.isEmpty()) {
            for (WorkflowExportEntity workflow : workflows) {
                resolveWorkflows(projectId, dependencyInfos, workflow);
            }
        }
        // 解析Agent依赖的子控制器
        List<AgentExportEntity> agents = agentExportEntity.getAgents();
        if (agents != null && !agents.isEmpty()) {
            for (AgentExportEntity agent : agents) {
                resolveAgents(projectId, dependencyInfos, agent);
            }
        }

        // 解析Agent依赖的单智能体
        List<AgentExportEntity> singleAgents = agentExportEntity.getSingleAgents();
        if (singleAgents != null && !singleAgents.isEmpty()) {
            for (AgentExportEntity singleAgent : singleAgents) {
                resolveAgents(projectId, dependencyInfos, singleAgent);
            }
        }

        // skill
        List<SkillDetails> skills = agentExportEntity.getSkills();
        if (skills != null && !skills.isEmpty()) {
            for (SkillDetails skill : skills) {
                resolveSkills(projectId, dependencyInfos, skill);
            }
        }

        // 设置agent解析字段具体值
        Agent metadata = agentExportEntity.getMetadata();
        ImportListInfo importAgentInfo = new ImportListInfo().setId(metadata.getAgentId())
            .setName(metadata.getName())
            .setDescription(metadata.getDescription())
            .setType(metadata.getType() != null ? metadata.getType() : CommonConstant.AGENT_TYPE)
            .setDependencies(dependencyInfos);

        // 判断环境中是否已存在该Agent配置
        importAgentInfo
            .setStatus(isAgentExistInWorkspace(projectId, RequestContextUtils.getRequestWorkspaceId(), metadata));
        importList.add(importAgentInfo);
    }

    /**
     * skills
     * @param projectId projectId
     * @param dependencyInfos dependencyInfos
     * @param skill skill
     */
    private void resolveSkills(String projectId, List<ImportListInfo> dependencyInfos, SkillDetails skill) {
        // 设置方法返回值中的参数
        ImportListInfo importSkillInfo = new ImportListInfo()
            .setName(skill.getName())
            .setDescription(skill.getDescription())
            .setType(CommonConstant.SKILL_TYPE)
            .setStatus(true);

        dependencyInfos.add(importSkillInfo);
    }

    /**
     * 合并workflow的DSL、Metadata和依赖的插件
     *
     * @param projectId projectId
     * @param workflowMetadata 该工作流元数据
     * @return WorkflowExportEntity 合并后的工作流配置对象
     */
    private WorkflowExportEntity mergeWorkflow(String projectId, WorkflowEntity workflowMetadata, String versionId) {
        // 构建工作流导出对象
        WorkflowExportEntity workflowExportEntity;

        if (StringUtils.isEmpty(versionId)) {
            workflowExportEntity = buildWfExportEntity(projectId, workflowMetadata, null);
        } else {
            workflowExportEntity = buildWfExportEntity(projectId, workflowMetadata, versionId);
            ReleaseVersion releaseVersion =
                releaseVersionMapper.selectByAppIdAndVersionId(workflowMetadata.getId(), versionId);
            workflowExportEntity.setReleaseVersion(releaseVersion);
        }
        return workflowExportEntity;
    }

    private WorkflowExportEntity buildWfExportEntity(String projectId, WorkflowEntity workflowMetadata,
        String versionId) {
        log.debug("Entering buildWfExportEntity with projectId={}, workflowMetadata={}, versionId={}", projectId,
            workflowMetadata, versionId);

        WorkflowExportEntity workflowExportEntity = new WorkflowExportEntity();
        try {
            String dslPath = workflowMetadata.getDslPath();
            workflowMetadata.setTraceId(StringUtils.isBlank(workflowMetadata.getTraceId()) ? workflowMetadata.getId()
                : workflowMetadata.getTraceId());

            // 如果版本号不为空，取版本的dsl
            ReleaseVersion releaseVersion;
            if (!StringUtils.isEmpty(versionId)) {
                log.debug("Processing version ID: {}", versionId);

                releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowMetadata.getId(), versionId);
                if (releaseVersion == null) {
                    throw new AgentStudioException(StudioError.DEPEND_WORKFLOW_VERSION, workflowMetadata.getId(),
                        workflowMetadata.getName(), versionId);
                }
                dslPath = releaseVersion.getDslPath();
                log.debug("Updated DSL path to version-specific path: {}", dslPath);
            }

            // 根据dslPath从OBS中获取DSL文件
            String workflowInfo = mgObsService.downloadObsFile(dslPath);

            WorkflowVO workflowDsl = jacksonObjectMapper.readValue(workflowInfo, new TypeReference<>() {});

            // 从工作流DSL文件中获取其nodes
            List<WorkflowNodeVO> nodes =
                jacksonObjectMapper.convertValue(workflowDsl.getNodes(), new TypeReference<>() {});
            log.debug("Found {} nodes in workflow", nodes.size());

            if (CollectionUtils.isNotEmpty(nodes)) {
                workflowExportEntity.setPlugins(new ArrayList<>());
                workflowExportEntity.setSubWorkflows(new ArrayList<>());
                workflowExportEntity.setMcpServers(new ArrayList<>());
                nodes.forEach(subNode -> parseWorkflowNodes(workflowMetadata.getId(), workflowExportEntity, subNode, projectId));
            }

            // 当前插件的工具ID需要单独适配，将工具id改为0
            adaptPluginNode(workflowDsl.getNodes());

            // 预置插件屏蔽url
            workflowExportEntity.getPlugins().forEach(plugin -> {
                if (Strings.CI.equals(ToolType.INNER.type, plugin.getType())) {
                    plugin.getRequestInfo().setUrl(null);
                }
            });


            // 设置对应字段
            workflowExportEntity.setDsl(workflowDsl);
            workflowExportEntity.setMetadata(workflowMetadata);
            workflowExportEntity.setShareInfo(shareResourceManagerService.exportShareInfo(workflowMetadata.getId()));
            workflowExportEntity.setShareResourceReferenceList(buildMappingEntityList(workflowMetadata.getId(), versionId));
            return workflowExportEntity;
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to export the workflow.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }
    }

    private void adaptPluginNode(List<WorkflowNodeVO> nodes) {
        // 后续重构后，需要保证工具id正确，当前先设置为0.设置为0的目的是保证工作流的插件导入之后能正确获取工具的
        // 输入输出定义、请求、输入输出是否封装、工具状态
        for (WorkflowNodeVO node : nodes) {
            if (node.getType().equals(PLUGIN.getType())) {
                node.getConfigs().put("tool_id", "0");
            }
        }
    }

    /**
     * 分类处理工作流中不同节点
     *
     * @param workflowExportEntity 工作流导出对象
     * @param node 工作流节点
     * @param projectId projectId
     */
    private void parseWorkflowNodes(String parentNodeId, WorkflowExportEntity workflowExportEntity, WorkflowNodeVO node,
        String projectId) {
        NodeType nodeType = NodeType.fromType(node.getType());
        if (nodeType == null) {
            log.error("unsupported node type {}", node.getType());
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }
        // 分类解析不同节点
        try {
            switch (nodeType) {
                case AGENT -> parseAgentNodePlugins(workflowExportEntity.getPlugins(), node, projectId);
                case PLUGIN -> parsePluginNode(workflowExportEntity.getPlugins(), node, projectId);
                case WORKFLOW -> parseSubWorkflowNode(parentNodeId, workflowExportEntity.getSubWorkflows(), node,
                    projectId);
                case INTENT_DETECTION_CONTAINER ->
                        parseIntentDetectionContainerNode(workflowExportEntity.getSubWorkflows(), node, projectId);
                case MCP -> parseMcpNode(workflowExportEntity.getMcpServers(), node, projectId);
                case PARAM_EXTRACTION ->
                    parseParamExtractionNode(parentNodeId, workflowExportEntity.getSubWorkflows(), node, projectId);
                default -> {
                }
            }
        } catch (AgentStudioException e) {
            log.error("{}", e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("parse node failed! {}", e.getMessage(), e);
            throw new AgentStudioException(StudioError.WORKFLOW_FLOW_RESOURCE_IMPORT_FAILED, node.getName());
        }
    }

    /**
     * 解析插件节点
     *
     * @param plugins 插件列表
     * @param node 插件节点
     * @param projectId projectId
     */
    private void parsePluginNode(List<ToolEntity> plugins, WorkflowNodeVO node, String projectId) {
        // 根据插件id和versionId判断是否重复，兼容引用的旧插件versionId为null
        final Map<String, Object> nodeConfigs = node.getConfigs();
        String id = nodeConfigs.get(WorkflowNodeAdapter.ID).toString();
        String toolId =
            ObjectUtils.isNotEmpty(nodeConfigs.get("tool_id")) ? nodeConfigs.get("tool_id").toString() : null;

        // 若为引用的共享插件,则跳过
        if (!isOwnSharePlugin(id)) {
            return;
        }

        // 判断 toolId 是否存在，存在则添加
        if (ObjectUtils.isNotEmpty(toolId)) {
            id = id + '#' + toolId;
        }
        String versionId =
            nodeConfigs.get(Constants.VERSION_ID) != null ? nodeConfigs.get(Constants.VERSION_ID).toString() : null;

        handleToolWithVersion(projectId, id, versionId, plugins);
        if (ObjectUtils.isNotEmpty(nodeConfigs.get("tool_id"))) {
            nodeConfigs.put("tool_id", "0");
        }
    }

    /**
     * 导出MCP节点
     *
     * @param mcpServers mcp服务列表
     * @param node MCP节点
     * @param projectId projectId
     */
    private void parseMcpNode(List<McpServerInfo> mcpServers, WorkflowNodeVO node, String projectId) {
        String id = node.getConfigs().get(WorkflowNodeAdapter.ID).toString();
        McpServerInfo mcpServerInfo = mcpInnerService.getMcpServerInfoById(id, null);
        if (mcpServerInfo == null) {
            log.error("The MCP node is invalid, mcpServerId: {}.", id);
            return;
        }

        if (!Strings.CS.equals(projectId, mcpServerInfo.getProjectId()) || !Strings.CS.equals(
            RequestContextUtils.getRequestWorkspaceId(), mcpServerInfo.getWorkspaceId())) {
            return;
        }
        if (mcpServers.stream().map(McpServerInfo::getServerId).anyMatch(id::equals)) {
            log.error("The MCP node is invalid, mcpServerId: {}.", id);
            return;
        }
        decryptMcpServiceConfig(mcpServerInfo);
        mcpServers.add(mcpServerInfo);
    }

    private void decryptMcpServiceConfig(McpServerInfo mcpServerInfo) {
        String serviceConfig = mcpServerInfo.getServiceConfig();
        if (StringUtils.isNotEmpty(serviceConfig)) {
            mcpServerInfo.setServiceConfig(encryptionAdapter.decrypt(serviceConfig));
        }
    }

    /**
     * 解析意图识别容器节点
     *
     * @param subWorkflows 子工作流列表
     * @param node 意图识别容器节点
     * @param projectId projectId
     */
    private void parseIntentDetectionContainerNode(List<WorkflowExportEntity> subWorkflows, WorkflowNodeVO node,
        String projectId) {
        log.debug("Entering parseIntentDetectionContainerNode with subWorkflows size={}, node={}, projectId={}",
            subWorkflows.size(), node, projectId);

        Map<String, Map<String, Object>> branchWorkflows = getIntentContainerWorkflows(node);
        if (branchWorkflows == null) {
            return;
        }
        log.debug("Found {} branch workflows: {}", branchWorkflows.size(), branchWorkflows);

        branchWorkflows.forEach((branchFlowId, branchFlowInfo) -> {
            log.debug("Processing branch workflow with ID={} and info={}", branchFlowId, branchFlowInfo);
            WorkflowEntity workflowEntity = workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId,
                ThreadLocalUtils.getWorkspaceId(), branchFlowId);
            if (workflowEntity == null) {
                log.error("Failed to export the workflow.");
                throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
            }
            String sonVersionId = branchFlowInfo.get(WorkflowNodeAdapter.VERSION_ID).toString();
            WorkflowExportEntity subWorkflowJsonObj = mergeWorkflow(projectId, workflowEntity, sonVersionId);
            subWorkflows.add(subWorkflowJsonObj);
            log.debug("Added merged workflow to subWorkflows. Current size={}", subWorkflows.size());
        });
        log.debug("Method completed successfully. Processed {} branch workflows", branchWorkflows.size());
    }

    /**
     * 解析参数提取节点
     *
     * @param subWorkflows 子工作流列表
     * @param node 参数提取节点
     * @param projectId projectId
     */
    private void parseParamExtractionNode(String parentNodeId, List<WorkflowExportEntity> subWorkflows, WorkflowNodeVO node,
        String projectId) {
        Map<String, Object> nodeConfigs = node.getConfigs();

        // 领域对象相关配置
        List<Object> domainObjects = JsonUtils.objectToClass(nodeConfigs.get(DOMAIN_OBJECTS));
        if (CollectionUtils.isNotEmpty(domainObjects)) {
            domainObjects.forEach(item -> {
                ParamExtractionDomainObject domainObject =
                    JsonUtils.objectToClassType(item, ParamExtractionDomainObject.class);
                if (domainObject != null && CollectionUtils.isNotEmpty(domainObject.getProcessingWorkflows())) {
                    domainObject.getProcessingWorkflows()
                        .forEach(processingWorkflow -> parseParamExtractionNode(parentNodeId, subWorkflows, processingWorkflow,
                            projectId));
                }
            });
        }

        // 拓展工作量相关配置
        List<Object> extensionWorkflows = JsonUtils.objectToClass(nodeConfigs.get(EXTENSION_WORKFLOWS));
        if (CollectionUtils.isNotEmpty(extensionWorkflows)) {
            extensionWorkflows.forEach(item -> {
                ParamExtractionWorkflow extensionWorkflow =
                    JsonUtils.objectToClassType(item, ParamExtractionWorkflow.class);
                if (extensionWorkflow != null) {
                    parseParamExtractionNode(parentNodeId, subWorkflows, extensionWorkflow, projectId);
                }
            });
        }
    }

    /**
     * 解析參數提取节点绑定的子工作流节点
     *
     * @param subWorkflows 子工作流列表
     * @param workflow 参数提取节点绑定的工作流
     * @param projectId projectId
     */
    private void parseParamExtractionNode(String parentNodeId, List<WorkflowExportEntity> subWorkflows, ParamExtractionWorkflow workflow,
        String projectId) {
        String id = workflow.getId();
        String versionId = workflow.getVersionId();

        ShareResourceEntity shareResourceEntity = shareResourceManagerService.queryShareResourceEntityByResourceId(id);

        if (shareResourceEntity != null
            && !Strings.CS.equals(RequestContextUtils.getRequestWorkspaceId(), shareResourceEntity.getWorkspaceId())) {
            if (mappingMapper.countMappingEntityListByAppIdAndResourceId(parentNodeId, null, id, versionId) <= 0) {
                log.error("Sub workflow {} of workflow {} does not exist.", parentNodeId, id);
                throw new AgentStudioException(StudioError.SUB_WORKFLOW_NOT_EXIST, parentNodeId, id);
            }
            return;
        }

        WorkflowEntity workflowEntity =
            workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId, ThreadLocalUtils.getWorkspaceId(), id);
        if (workflowEntity == null) {
            log.error("Sub workflow {} of workflow {} does not exist.", parentNodeId, id);
            throw new AgentStudioException(StudioError.SUB_WORKFLOW_NOT_EXIST, parentNodeId, id);
        }

        if (isWorkflowDuplicateWithVersion(subWorkflows, id, versionId)) {
            return;
        }

        WorkflowExportEntity subWorkflowExportEntity = mergeWorkflow(projectId, workflowEntity, versionId);
        subWorkflows.add(subWorkflowExportEntity);
    }

    /**
     * 解析子工作流节点
     *
     * @param subWorkflows 子工作流列表
     * @param node 子工作流节点
     * @param projectId projectId
     */
    private void parseSubWorkflowNode(String parentNodeId, List<WorkflowExportEntity> subWorkflows, WorkflowNodeVO node,
        String projectId) {
        String id = node.getConfigs().get(WorkflowNodeAdapter.ID).toString();
        String versionId = node.getConfigs().get(WorkflowNodeAdapter.VERSION_ID).toString();

        ShareResourceEntity shareResourceEntity = shareResourceManagerService.queryShareResourceEntityByResourceId(id);

        // 如果是共享资源，不会导出节点以及其子节点
        if (shareResourceEntity != null
            && !Strings.CS.equals(RequestContextUtils.getRequestWorkspaceId(), shareResourceEntity.getWorkspaceId())) {
            if (mappingMapper.countMappingEntityListByAppIdAndResourceId(parentNodeId, null, id, versionId) <= 0) {
                log.error("Sub workflow {} of workflow {} does not exist.", parentNodeId, id);
                throw new AgentStudioException(StudioError.SUB_WORKFLOW_NOT_EXIST, parentNodeId, id);
            }
            return;
        }

        WorkflowEntity workflowEntity =
            workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId, ThreadLocalUtils.getWorkspaceId(), id);
        if (workflowEntity == null) {
            log.error("Sub workflow {} of workflow {} does not exist.", parentNodeId, id);
            throw new AgentStudioException(StudioError.SUB_WORKFLOW_NOT_EXIST, parentNodeId, id);
        }

        if (isWorkflowDuplicateWithVersion(subWorkflows, id, versionId)) {
            return;
        }

        String sonVersionId = node.getConfigs().get(WorkflowNodeAdapter.VERSION_ID).toString();
        WorkflowExportEntity subWorkflowExportEntity = mergeWorkflow(projectId, workflowEntity, sonVersionId);
        subWorkflows.add(subWorkflowExportEntity);
    }

    /**
     * 解析Agent节点
     *
     * @param plugins 插件列表
     * @param node Agent节点
     * @param projectId projectId
     */
    private void parseAgentNodePlugins(List<ToolEntity> plugins, WorkflowNodeVO node, String projectId) {
        if (node.getConfigs().get(CommonConstant.Workflow.PLUGINS) != null) {
            List<Map<String, Object>> originPlugins =
                JsonUtils.objectToClass(node.getConfigs().get(CommonConstant.Workflow.PLUGINS));
            if (originPlugins != null) {
                for (Map<String, Object> pluginConfig : originPlugins) {
                    ToolEntity toolNode = irAdapterService.getPluginToolEntity(projectId, pluginConfig);
                    if (toolNode == null) {
                        log.error("Tool does not exits.");
                        throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
                    }
                    plugins.add(toolNode);
                }
            }
        }
    }

    // 提取意图容器节点，分支工作流信息
    private Map<String, Map<String, Object>> getIntentContainerWorkflows(WorkflowNodeVO node) {
        if (node == null || node.getBranches() == null) {
            return null;
        }

        // 字段映射
        Map<String, String> filedMaps = new HashMap<>();
        filedMaps.put(WorkflowNodeAdapter.ID, "workflow_id");
        filedMaps.put(WorkflowNodeAdapter.VERSION_ID, "workflow_version_id");

        Map<String, Map<String, Object>> workflows = new HashMap<>();
        for (WorkflowBranchVO branch : node.getBranches()) {
            if (branch == null || branch.getConfigs() == null
                || branch.getConfigs().get(filedMaps.get(WorkflowNodeAdapter.ID)) == null) {
                continue;
            }

            // 去重
            String workflowId = branch.getConfigs().get(filedMaps.get(WorkflowNodeAdapter.ID)).toString();
            if (StringUtils.isEmpty(workflowId) || workflows.containsKey(workflowId)) {
                continue;
            }

            Map<String, Object> workflow = new HashMap<>();
            workflow.put(WorkflowNodeAdapter.ID, branch.getConfigs().get(filedMaps.get(WorkflowNodeAdapter.ID)));
            workflow.put(WorkflowNodeAdapter.VERSION_ID,
                branch.getConfigs().get(filedMaps.get(WorkflowNodeAdapter.VERSION_ID)));
            workflows.put(workflowId, workflow);
        }

        return workflows;
    }

    /**
     * 导入单个插件
     *
     * @param projectId projectId
     * @param tool 需要导入的插件对象
     * @return boolean 是否导入成功
     */
    private boolean importToolsHandler(String projectId, String targetWorkspaceId, ToolEntity tool,
        Set<ExtraMsg> pluginsOfAuth) {
        try {
            // op 账号也校验，projectid直接传空
            urlCheckUtils.checkUrl(null, tool.getRequestInfo().getUrl());
        } catch (Exception e) {
            log.error(String.format("Failed to import plugin: %s", tool.getToolId()), e);
            return false;
        }
        pluginBaseImpl.adaptToolShareInfo(tool);
        shareResourceManagerService.importShareInfo(projectId, tool.getShareInfo(), new WfImportDataWrapper());
        tool.setProjectId(projectId);
        tool.setWorkspaceId(targetWorkspaceId);
        tool.setDomainId(RequestContextUtils.getRequestUserDomainId());
        tool.setCreator(opSvcProjectId.equals(projectId) ? CommonConstant.DEFAULT_USERNAME
            : RequestContextUtils.getRequestUserName());
        tool.setCreatorId(RequestContextUtils.getRequestUserId());
        Date date = new Date();
        tool.setCreatedOn(date);
        tool.setUpdatedOn(date);
        tool.setTestStatus(tool.getTestStatus());
        tool.setLastVersionId(tool.getLastVersionId());

        // 兼容旧版本插件
        adaptImportTool(tool);

        // 插件ChineseName或者DisplayName为空时，值选则其中不为空的那个
        if (StringUtils.isEmpty(tool.getToolChineseName()) && StringUtils.isEmpty(tool.getToolDisplayName())) {
            return false;
        }
        if (StringUtils.isEmpty(tool.getToolDisplayName())) {
            tool.setToolDisplayName(tool.getToolChineseName());
        }
        if (StringUtils.isEmpty(tool.getToolChineseName())) {
            tool.setToolChineseName(tool.getToolDisplayName());
        }

        if (tool.getShareInfo() != null) {
            shareResourceManagerService.importShareInfo(projectId, tool.getShareInfo(), new WfImportDataWrapper());
        }

        // 若已存在该配置走覆盖逻辑，否则插入到数据库中
        try {
            if (isToolExistInWorkspace(projectId, targetWorkspaceId, tool)) {
                // 插件visibility字段不允许修改
                tool.setVisibility(null);
                pluginAdapterImpl.updateByOldTool(tool);
                updateDisplayName(projectId, targetWorkspaceId, tool);
                pluginAdapterImpl.updateName(tool);
            } else {
                // 名称重复校验
                updateDisplayName(projectId, targetWorkspaceId, tool);
                pluginAdapterImpl.insertByTool(tool);
            }
        } catch (Exception e) {
            log.error(String.format("Failed to import tool: %s", tool.getToolId()), e);
            return false;
        }

        // 含有鉴权信息的插件
        if (tool.getAuthInfo().getScope() != null && AuthInfo.ScopeEnum.SERVICE.equals(tool.getAuthInfo().getScope())) {
            ExtraMsg authMsg = new ExtraMsg().setId(tool.getToolId()).setName(tool.getToolDisplayName());
            pluginsOfAuth.add(authMsg);
        }

        // 导入插件版本
        if (!importToolVersion(projectId, tool)) {
            return false;
        }

        // 导入的插件都重新发布一次 场景：插件已经存在，并且已经发布。
        // 工作流导入会将原插件的toolid设置为0，而dsl的toolid还是原始值。所以都重新发布一次，进行同步，dsl里的插件version后续也更新为新version
        if (!publishToolVersion(projectId, tool)) {
            return false;
        }

        log.info("Succeed to import tool: {}", tool.getToolId());
        return true;
    }

    private boolean publishToolVersion(String projectId, ToolEntity toolEntity) {
        String toolId = pluginAdapterImpl.getPluginId(toolEntity.getToolId());
        String versionId = String.valueOf(System.currentTimeMillis());
        try {
            // 版本不存在导入版本
            String versionName = "v" + new Date().getTime();
            ReleaseVersion releaseVersion =
                pluginAdapterImpl.releaseToolVersionHandler(toolId, versionId, versionName, "");
            releaseVersionMapper.insert(releaseVersion);
            toolEntity.setVersionId(versionId);
            pluginAdapterImpl.updateOldTool(projectId, versionId, toolEntity.getToolId());
        } catch (Exception e) {
            log.error("import tool:{}, version:{} failed {}", toolId, versionId, e.getMessage());
            return false;
        }
        return true;
    }

    private void updateDisplayName(String projectId, String targetWorkspaceId, ToolEntity tool) {
        int existChineseName = toolMapperDiscard.selectByChineseNameAndWorkspaceIdAndProjectId(
            tool.getToolChineseName(), targetWorkspaceId, tool.getToolId());
        int existDisplayName = toolMapperDiscard.selectByDisplayNameAndWorkspaceIdAndProjectId(
            tool.getToolDisplayName(), targetWorkspaceId, tool.getToolId());
        if (existChineseName > 0) {
            int seq = 1;
            while (true) {
                String toolChineseName = subName(tool.getToolChineseName(), CommonConstant.NAME_MAX_LEN);
                String candidateName = toolChineseName + "_" + seq;
                if (toolMapperDiscard.selectByChineseNameAndWorkspaceIdAndProjectId(candidateName, targetWorkspaceId,
                    projectId) == 0) {
                    tool.setToolChineseName(candidateName);
                    break;
                }
                seq++;
            }
        }
        if (existDisplayName > 0) {
            int seq = 1;
            while (true) {
                String toolDisplayName = subName(tool.getToolDisplayName(), CommonConstant.NAME_MAX_LEN);
                String candidateName = toolDisplayName + "_" + seq;
                if (toolMapperDiscard.selectByDisplayNameAndWorkspaceIdAndProjectId(candidateName, targetWorkspaceId,
                    projectId) == 0) {
                    tool.setToolDisplayName(candidateName);
                    break;
                }
                seq++;
            }
        }
    }

    // 导入插件版本
    private boolean importToolVersion(String projectId, ToolEntity toolEntity) {
        if (StringUtils.isBlank(toolEntity.getVersionId())) {
            toolEntity.setVersionId("0");
        }
        String toolId = pluginAdapterImpl.getPluginId(toolEntity.getToolId());
        String versionId = toolEntity.getVersionId();
        ReleaseVersion existVersion = releaseVersionMapper.selectByAppIdAndVersionId(toolId, versionId);
        if (existVersion != null) {
            return true;
        }

        try {
            // 版本不存在导入版本
            String versionName = "v" + new Date().getTime();
            ReleaseVersion releaseVersion =
                pluginAdapterImpl.releaseToolVersionHandler(toolId, versionId, versionName, "");
            releaseVersionMapper.insert(releaseVersion);
            pluginAdapterImpl.updateOldTool(projectId, versionId, toolEntity.getToolId());
        } catch (Exception e) {
            log.error("import tool:{}, version:{} failed {}", toolId, versionId, e.getMessage());
            return false;
        }
        return true;
    }

    // 获取绑定的插件列表
    private List<ToolEntity> getMappingToolsWithVersion(String projectId, List<MappingEntity> mappingTools) {
        if (mappingTools.size() == 0) {
            return Collections.emptyList();
        }
        // 获取Agent关联的插件列表
        List<ToolEntity> toolEntities = new ArrayList<>();
        Map<String, String> toolMap = mappingTools.stream()
            .collect(Collectors.toMap(MappingEntity::getResourceId,
                entity -> entity.getResourceVersion() != null ? entity.getResourceVersion() : ""));
        for (Map.Entry<String, String> entry : toolMap.entrySet()) {
            if (!isOwnSharePlugin(entry.getKey())) {
                continue;
            }
            handleToolWithVersion(projectId, entry.getKey(), entry.getValue(), toolEntities);
        }
        return toolEntities;
    }

    // 引用插件导出处理，兼容旧插件无版本
    private void handleToolWithVersion(String projectId, String toolId, String versionId, List<ToolEntity> tools) {
        // 重复插件（带版本）不再导出
        if (isToolDuplicateWithVersion(tools, toolId, versionId)) {
            return;
        }

        ToolEntity toolEntity = pluginAdapterImpl.getToolEntity(toolId, projectId, opSvcProjectId, versionId);

        if (toolEntity == null) {
            log.error("tool: {} is not exist.", toolId);
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        if (toolEntity.getToolId().contains("#")) {
            toolEntity.setToolId(toolEntity.getToolId().split("#")[0]);
        }
        toolEntity.setShareInfo(shareResourceManagerService.exportShareInfo(toolEntity.getToolId()));
        toolEntity.setShareResourceReferenceList(buildMappingEntityList(toolEntity.getToolId(), versionId));
        tools.add(toolEntity);
    }

    /**
     * 导入自定义MCP服务
     *
     * @param projectId projectId
     * @param mcpServer 需要导入的MCP服务对象
     * @return boolean 是否导入成功
     */
    private boolean importMcpHandler(String projectId, String targetWorkspaceId, McpServerInfo mcpServer,
        Set<ExtraMsg> mcpsOfAuth) {
        // 修正导入对象用户信息
        mcpServer.setProjectId(projectId);
        mcpServer.setCreator(RequestContextUtils.getRequestUserName());
        mcpServer.setCreatorId(RequestContextUtils.getRequestUserId());

        // 设置唯一MCP服务名称
        setUniqueServerName(targetWorkspaceId, mcpServer);

        // 若已存在走覆盖逻辑，否则插入到数据库中
        boolean result = mcpInnerService.createOrUpdate(mcpServer, targetWorkspaceId);
        log.info("Succeed to import MCP server: {}", mcpServer.getName());
        return result;
    }

    private boolean isWorkflowDuplicateWithVersion(List<WorkflowExportEntity> workflows, String id, String versionId) {
        List<ReleaseVersion> versionList = workflows.stream().map(WorkflowExportEntity::getReleaseVersion).toList();
        return versionList.stream()
            .anyMatch(
                version -> Objects.equals(version.getAppId(), id) && Objects.equals(version.getVersionId(), versionId));
    }

    // 根据toolId和版本号判断是否重复
    private boolean isToolDuplicateWithVersion(List<ToolEntity> tools, String id, String versionId) {
        return tools.stream()
            .anyMatch(tool -> Objects.equals(tool.getToolId(), id) && Objects.equals(tool.getVersionId(), versionId));
    }

    private void setUniqueServerName(String workspaceId, McpServerInfo mcpServer) {
        String serverName = Optional.ofNullable(mcpServer.getName()).orElse(mcpServer.getNameEn());
        List<McpServiceEntity> mcpServersByProjectId = mcpInnerService.getMcpByIds(workspaceId, null);
        if (CollectionUtils.isEmpty(mcpServersByProjectId)) {
            return;
        }
        Set<String> nameByWorkspaceId = mcpServersByProjectId.stream()
            .map(McpServiceEntity::getName)
            .filter(Objects::nonNull)
            .collect(Collectors.toCollection(() -> new TreeSet<>(String.CASE_INSENSITIVE_ORDER)));

        // 当前projectId下name不存在，不会冲突
        if (!nameByWorkspaceId.contains(serverName)) {
            return;
        }

        // 用户在当前环境中已存在该MCP服务，且name未改变，不会冲突
        McpServerInfo mcpServerById = mcpInnerService.getMcpServerInfoById(mcpServer.getServerId(), workspaceId);
        if (mcpServerById != null && Objects.equals(serverName, mcpServerById.getNameEn())) {
            return;
        }
        // 设置唯一MCP服务名称
        int index = 1;
        serverName = subName(serverName, CommonConstant.NAME_MAX_LEN);
        while (nameByWorkspaceId.contains(String.format(NAME_FORMAT, serverName, index))) {
            index++;
        }
        mcpServer.setNameEn(String.format(NAME_FORMAT, serverName, index));
    }

    /**
     * 导入单个workflow
     *
     * @param projectId projectId
     * @param targetWorkspaceId 目标空间id
     * @param workflowExportEntity 需要导入的工作流配置对象
     * @param wfImportDataWrapper 导入中间数据
     * @return boolean 是否导入成功
     */
    private boolean importWorkflowsHandler(String projectId, String targetWorkspaceId,
        WorkflowExportEntity workflowExportEntity, WfImportDataWrapper wfImportDataWrapper) {
        WorkflowEntity metadata = workflowExportEntity.getMetadata();
        if (metadata == null) {
            return false;
        }
        // 导入依赖的插件
        workflowExportEntity.getMetadata()
            .setTraceId(StringUtils.isBlank(workflowExportEntity.getMetadata().getTraceId())
                ? workflowExportEntity.getMetadata().getId() : workflowExportEntity.getMetadata().getTraceId());

        shareResourceManagerService.validateShareReferences(workflowExportEntity.getShareResourceReferenceList(), targetWorkspaceId);

        shareResourceManagerService.importShareInfo(projectId, workflowExportEntity.getShareInfo(), wfImportDataWrapper);

        importTools(projectId, targetWorkspaceId, workflowExportEntity, wfImportDataWrapper);

        pluginAdapterImpl.handleToolWithoutToolId(workflowExportEntity);
        pluginAdapterImpl.handleToolReleaseVersionId(workflowExportEntity);

        // 导入依赖的MCP服务
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setAppId(metadata.getId());
        mappingEntity.setAppName(metadata.getName());
        mappingEntity.setAppType(CommonConstant.WORKFLOW_TYPE);
        List<McpServerInfo> mcpServers = workflowExportEntity.getMcpServers();
        if (!importMcpServers(projectId, targetWorkspaceId, mcpServers, mappingEntity, wfImportDataWrapper)) {
            return false;
        }

        // 导入依赖的workflow
        List<WorkflowExportEntity> subWorkflows = workflowExportEntity.getSubWorkflows();
        if (!importSubWorkflows(projectId, targetWorkspaceId, wfImportDataWrapper, subWorkflows)) {
            return false;
        }

        // 导入工作流本身
        return importWorkflowSelf(projectId, targetWorkspaceId, workflowExportEntity, metadata);
    }

    // 清空fg_id
    private void clearWorkflowCodeNode(WorkflowVO workflowVO) {
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equals(NodeType.CODE.getType(), v.getType()))
            .forEach(p -> {
                p.getConfigs().put(FG_ID, "");
            });
    }

    private void updateWorkflowCodeNode(WorkflowVO workflowVO, String oldId, String newId) {
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equals(NodeType.CODE.getType(), v.getType()) && Strings.CS.equals(
                v.getConfigs().get(FG_ID).toString(), oldId))
            .forEach(p -> {
                p.getConfigs().put(FG_ID, newId);
            });
    }

    /**
     * 导入依赖的MCP服务及关联关系
     *
     * @param projectId projectId
     * @param mcpServers mcpServers
     * @param mappingEntity mappingEntity
     * @return boolean
     */
    private boolean importMcpServers(String projectId, String targetWorkspaceId, List<McpServerInfo> mcpServers,
        MappingEntity mappingEntity, WfImportDataWrapper wfImportDataWrapper) {
        if (CollectionUtils.isEmpty(mcpServers)) {
            return true;
        }

        // 先删除引用关系
        mappingMapper.deleteBatchByAppIdAndResourceType(mappingEntity.getAppId(), CommonConstant.MCP_TYPE);
        for (McpServerInfo mcpServer : mcpServers) {
            // url校验
            urlCheckUtils.checkUrl(null, mcpServer.getUrl());
            // 预置MCP服务只添加关联关系
            if (ToolType.INNER.type.equals(mcpServer.getType())) {
                if (!importMcpMapping(mcpServer, mappingEntity)) {
                    log.error("Failed to add inner mcp mapping");
                    return false;
                }
            } else if (mcpServer.getOrigin() != null && mcpServer.getOrigin() == 1) {
                // 判断mcp共享mcp是否有权限
                if (!shareInnerService.isShared(mcpServer.getServerId(), targetWorkspaceId)) {
                    log.error("Failed to import mcp servers, no permission to share mcp:{}", mcpServer.getName());
                    return false;
                }
                // 共享mcp只导入mapping关系
                mappingEntity.setReferenceType(ReferenceTypeEnum.SHARE.getValue());
                if (!importMcpMapping(mcpServer, mappingEntity)) {
                    log.error("Failed to add inner mcp mapping");
                    return false;
                }
            } else {
                // 导入自定义MCP服务即依赖关系
                if (!importMcpHandler(projectId, targetWorkspaceId, mcpServer, wfImportDataWrapper.getMcpsOfAuth())
                    || !importMcpMapping(mcpServer, mappingEntity)) {
                    log.error("Failed to import mcp servers");
                    return false;
                }
            }
        }
        return true;
    }

    private boolean importWorkflowSelf(String projectId, String targetWorkspaceId,
        WorkflowExportEntity workflowExportEntity, WorkflowEntity metadata) {
        Set<String> modelIds = null;

        if (importModelEnable) {
            try {
                Map<String, String> replaceModelIdRecord = new HashMap<>();
                // 导入模型
                importModelByFlow(projectId, workflowExportEntity, targetWorkspaceId, replaceModelIdRecord);
                workflowExportEntity = replaceModelId(workflowExportEntity, replaceModelIdRecord);
                workflowExportEntity = processDefaultModel(workflowExportEntity, projectId, targetWorkspaceId);
                modelIds = parseModelId(workflowExportEntity);
            } catch (Exception e) {
                // 此处仅记录异常，不抛出，不阻塞导入主流程
                log.warn("import workFlow process model fail but import continue", e);
            }
        }

        // 导入Workflow本身不包含版本
        if (!importWorkflowEntity(projectId, targetWorkspaceId, workflowExportEntity, metadata)) {
            return false;
        }

        // 导入版本
        importReleaseVersion(projectId, targetWorkspaceId, workflowExportEntity, metadata);
        if (modelIds == null) {
            return true;
        }
        // 处理流和模型的关联关系
        this.addModelMapping(projectId, RequestContextUtils.getRequestWorkspaceId(), modelIds, metadata.getId(),
            metadata.getName());
        return true;
    }

    public WorkflowExportEntity processDefaultModel(WorkflowExportEntity workflowExportEntity, String projectId,
        String workspaceId) {
        if (!workflowExportEntity.getDsl().getConfigs().containsKey(CommonConstant.ModelParam.DEFAULT_MODEL)) {
            return workflowExportEntity;
        }
        Map<String, String> defaultMode = JsonUtils
            .objectToClass(workflowExportEntity.getDsl().getConfigs().get(CommonConstant.ModelParam.DEFAULT_MODEL));
        if (Objects.isNull(defaultMode) || defaultMode.isEmpty()) {
            return workflowExportEntity;
        }
        String modelId = defaultMode.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
        String modelName = defaultMode.get(CommonConstant.ModelParam.MODEL_NAME);
        if (StringUtils.isBlank(modelId) || StringUtils.isBlank(modelName)) {
            return workflowExportEntity;
        }
        String modelIdInDb = getModelIdInDatabase(projectId, workspaceId, modelId, modelName);

        if (Strings.CS.equals(modelId, modelIdInDb)) {
            return workflowExportEntity;
        }
        if (Strings.CS.equals("uuid", modelIdInDb) || StringUtils.isBlank(modelIdInDb)) {
            defaultMode.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID,
                Strings.CS.equals("uuid", modelIdInDb) ? UUID.randomUUID().toString() : modelId);
            // 模型不存在时 需要考虑 分别考虑 供应商 与 服务模型
            String providerId = createProvider(projectId, workspaceId);
            createModel(projectId, workspaceId, defaultMode, providerId);
        } else {
            defaultMode.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID, modelIdInDb);
        }
        defaultMode.put(CommonConstant.ModelParam.MODEL_TYPE,
            supportTypes.contains(defaultMode.get(CommonConstant.ModelParam.MODEL_TYPE))
                ? defaultMode.get(CommonConstant.ModelParam.MODEL_TYPE) : ModelTypeV2.LLM.toString());
        workflowExportEntity.getDsl().getConfigs().put(CommonConstant.ModelParam.DEFAULT_MODEL, defaultMode);
        return workflowExportEntity;
    }

    public String getModelIdInDatabase(String projectId, String workspaceId, String modelId, String modelName) {
        ModelServiceBase modelServiceBase = modelServiceMapper.queryById(modelId);
        if (hasModelServiceExist(modelServiceBase, projectId, workspaceId)
            || freeModelServiceMapper.countByModelId(modelId) > 0) {
            return modelId;
        }
        List<ModelServiceBase> existMSBySystem =
            modelServiceMapper.queryByName(CommonConstant.SYSTEM_DEFAULT, CommonConstant.SYSTEM_DEFAULT,modelName,null);
        if (!existMSBySystem.isEmpty()) {
            // 模型名称存在,但Id 不存在时 需更记录导入id与新id，用于后续替换
            return existMSBySystem.get(0).getId();
        }
        List<ModelServiceBase> existMS = modelServiceMapper.queryByName(projectId, workspaceId, modelName,null);
        if (!existMS.isEmpty()) {
            return existMS.get(0).getId();
        }
        return modelServiceBase != null ? "uuid" : null;
    }

    /**
     * 更新或删除模型资源关系
     *
     */
    private void addModelMapping(String projectId, String workspaceId, Set<String> modelIds, String workflowId,
        String workflowName) {
        if (CollectionUtils.isEmpty(modelIds)) {
            return;
        }
        List<ModelServiceBase> modelServiceBases =
            this.modelServiceManager.queryAllModelByIds(projectId, workspaceId, modelIds);
        List<MappingEntity> modelMapping = modelServiceBases.stream().map(modelServiceBase -> {
            MappingEntity entity = new MappingEntity();
            entity.setMappingId(UUID.randomUUID().toString());
            entity.setAppId(workflowId);
            entity.setAppName(workflowName);
            entity.setAppType(WORKFLOW.toString());
            entity.setResourceId(modelServiceBase.getId());
            entity.setResourceName(modelServiceBase.getModelName());
            entity.setResourceDesc(modelServiceBase.getModelDescription());
            entity.setResourceType(ResourceTypeEnum.MODEL.toString());
            return entity;
        }).toList();
        if (!CollectionUtils.isEmpty(modelMapping)) {
            mappingMapper.deleteBatchByAppIdAndResourceType(workflowId, ResourceTypeEnum.MODEL.toString());
            mappingMapper.insertBatch(modelMapping);
        }
    }

    /**
     * 替换模型id
     *
     */
    public WorkflowExportEntity replaceModelId(WorkflowExportEntity workflowExportEntity,
        Map<String, String> replaceModelIdRecord) {
        for (WorkflowNodeVO workflowNodeVO : workflowExportEntity.getDsl().getNodes()) {
            if (CommonConstant.LLM_CONFIG_NODE.contains(workflowNodeVO.getType())
                && !Objects.isNull(workflowNodeVO.getConfigs())
                && (!Objects.isNull(workflowNodeVO.getConfigs().get(CommonConstant.Workflow.MODEL))
                    || !Objects.isNull(workflowNodeVO.getConfigs().get(NodeType.LLM.getType())))) {
                Map<String, String> modelConfigMap =
                    JsonUtils.objectToClass(workflowNodeVO.getConfigs().get(CommonConstant.Workflow.MODEL));
                if (Objects.isNull(modelConfigMap)) {
                    continue;
                }
                String modelDeploymentId = modelConfigMap.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
                if (StringUtils.isBlank(modelDeploymentId)) {
                    continue;
                }
                modelConfigMap.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID,
                    replaceModelIdRecord.containsKey(modelDeploymentId) ? replaceModelIdRecord.get(modelDeploymentId)
                        : modelDeploymentId);
                modelConfigMap.put(CommonConstant.ModelParam.MODEL_TYPE,
                    supportTypes.contains(modelConfigMap.get(CommonConstant.ModelParam.MODEL_TYPE))
                        ? modelConfigMap.get(CommonConstant.ModelParam.MODEL_TYPE) : ModelTypeV2.LLM.toString());
                if (workflowNodeVO.getConfigs().containsKey(CommonConstant.Workflow.MODEL)) {
                    workflowNodeVO.getConfigs().put(CommonConstant.Workflow.MODEL, modelConfigMap);
                }
                if (workflowNodeVO.getConfigs().containsKey(NodeType.LLM.getType())) {
                    workflowNodeVO.getConfigs().put(NodeType.LLM.getType(), modelConfigMap);
                }
            }
        }
        return workflowExportEntity;
    }

    /**
     * 解析导入流中的的模型id，不处理意图识别和高级意图识别节点，和流导入处理模型的逻辑保持一致
     *
     */
    public Set<String> parseModelId(WorkflowExportEntity workflowExportEntity) {
        Set<String> modelIds = new HashSet<>();
        for (WorkflowNodeVO modelNode : workflowExportEntity.getDsl().getNodes()) {
            if (CommonConstant.LLM_CONFIG_NODE.contains(modelNode.getType()) && !Objects.isNull(modelNode.getConfigs())
                && (!Objects.isNull(modelNode.getConfigs().get(CommonConstant.Workflow.MODEL))
                    || !Objects.isNull(modelNode.getConfigs().get("llm")))) {
                NodeType nodeType = NodeType.fromType(modelNode.getType());
                if (nodeType == null) {
                    continue;
                }
                Map<String, String> modelConfigMap;
                if (nodeType == NodeType.INTENT_DETECTION || nodeType == NodeType.INTENT_COMPLEX_INTENT) {
                    Object objLlm = modelNode.getConfigs().get("llm");
                    if (objLlm == null) {
                        continue;
                    }
                    Map<String, String> mapLlm = JsonUtils.objectToClass(objLlm);
                    if (org.springframework.util.CollectionUtils.isEmpty(mapLlm)) {
                        continue;
                    }
                    Object objModel = mapLlm.get(MODEL);
                    if (objModel == null) {
                        continue;
                    }
                    modelConfigMap = JsonUtils.objectToClass(objModel);
                } else {
                    modelConfigMap = JsonUtils.objectToClass(modelNode.getConfigs().get(CommonConstant.Workflow.MODEL));
                }
                if (org.springframework.util.CollectionUtils.isEmpty(modelConfigMap)) {
                    continue;
                }
                String modelDeploymentId = modelConfigMap.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
                if (StringUtils.isBlank(modelDeploymentId)) {
                    continue;
                }
                modelIds.add(modelDeploymentId);
            }
        }

        // 工作流的全局配置模型
        if (org.springframework.util.CollectionUtils.isEmpty(workflowExportEntity.getDsl().getConfigs())) {
            return modelIds;
        }

        if (!workflowExportEntity.getDsl().getConfigs().containsKey(CommonConstant.ModelParam.DEFAULT_MODEL)) {
            return modelIds;
        }
        Map<String, String> defaultMode = JsonUtils
            .objectToClass(workflowExportEntity.getDsl().getConfigs().get(CommonConstant.ModelParam.DEFAULT_MODEL));
        if (org.springframework.util.CollectionUtils.isEmpty(defaultMode)) {
            return modelIds;
        }
        String modelId = defaultMode.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
        if (StringUtils.isNotBlank(modelId)) {
            modelIds.add(modelId);
        }
        return modelIds;
    }

    /**
     * 导入工作流中的模型
     *
     */
    public void importModelByFlow(String projectId, WorkflowExportEntity workflowExportEntity, String workspaceId,
        Map<String, String> replaceModelIdRecord) {
        Map<String, Map<String, String>> modelsMap = extractModelByWorkflow(workflowExportEntity);
        if (Objects.isNull(modelsMap) || modelsMap.isEmpty()) {
            // 不包含 模型相关节点 导入结束
            return;
        }
        modelsMap.forEach((modelId, modelMap) -> {
            String modelName = modelMap.get(CommonConstant.ModelParam.MODEL_NAME);
            if (StringUtils.isBlank(modelName)) {
                return;
            }
            String modelIdInDatabase = getModelIdInDatabase(projectId, workspaceId, modelId, modelName);
            if (Strings.CS.equals(modelId, modelIdInDatabase)) {
                return;
            }
            if (Strings.CS.equals("uuid", modelIdInDatabase) || StringUtils.isBlank(modelIdInDatabase)) {
                replaceModelIdRecord.put(modelId,
                    Strings.CS.equals("uuid", modelIdInDatabase) ? UUID.randomUUID().toString() : modelId);
                modelMap.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID, replaceModelIdRecord.get(modelId));
                String providerId = createProvider(projectId, workspaceId);
                createModel(projectId, workspaceId, modelMap, providerId);
            } else {
                replaceModelIdRecord.put(modelId, modelIdInDatabase);
            }
        });
    }

    public boolean hasModelServiceExist(ModelServiceBase modelServiceBase, String projectId, String workspaceId) {
        // 是否属于预置的或者空间下自创建的
        return !Objects.isNull(modelServiceBase)
            && (projectId.equals(modelServiceBase.getProjectId())
                || CommonConstant.SYSTEM_DEFAULT.equals(modelServiceBase.getProjectId()))
            && (workspaceId.equals(modelServiceBase.getWorkspaceId())
                || CommonConstant.SYSTEM_DEFAULT.equals(modelServiceBase.getWorkspaceId()));
    }

    public void createModel(String projectId, String workspaceId, Map<String, String> modeConfig, String providerId) {
        ModelServiceBase base = buildImportModelService(modeConfig, providerId, projectId, workspaceId);
        modelServiceManager.createModelService(base);
    }

    public ModelServiceBase buildImportModelService(Map<String, String> modeConfig, String providerId, String projectId,
        String workspaceId) {
        String modename = modeConfig.get(CommonConstant.ModelParam.MODEL_NAME);
        String modeId = modeConfig.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
        List<ProviderAuthMetadata> metadataList =
            authService.selectProviderMetadataAndPermissionCheck(projectId, workspaceId, providerId, false);
        ModelServiceBase base = new ModelServiceBase().setId(modeId)
            .setServiceName(modename)
            .setServiceKey("integration:" + workspaceId + ":" + modename)
            .setModelName(modename)
            .setModelVersion(modename)
            .setModelType(NodeType.LLM.getType())
            .setModelTags("default-import")
            .setModelDescription("import default create")
            .setModelDeployType("PRIVATE-INTEGRATION")
            .setDocumentUrl("")
            .setDomainId(RequestContextUtils.getRequestUserDomainId())
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setCreatedByUser(RequestContextUtils.getRequestUserName())
            .setLastUpdatedByUser(RequestContextUtils.getRequestUserName())
            .setCreatedDate(System.currentTimeMillis())
            .setLastUpdatedDate(System.currentTimeMillis())
            .setApiUrl(defaultImportModelApi)
            .setIsSupportFunction(true)
            .setProviderId(providerId)
            .setAuthMetadataId(metadataList.get(0).getId())
            .setModelPriority(modelServiceMgmtService.getModelServicePriority(modename))
            .setIsSupportStream(true)
            .setPublishStatus("offline")
            .setInterfaceProtocol(CommonConstant.CustomModel.OPENAI)
            .setIdentityId(modeId);
        return base;
    }

    public String createProvider(String projectId, String workspaceId) {
        List<ModelServiceProvider> providerList = userProviderMapper.selectUserDataByName(projectId, workspaceId,
            CommonConstant.ProviderParam.IMPORT_DEFAULT_PROVIDER_NAME);
        if (!providerList.isEmpty()) {
            return providerList.get(0).getId();
        }
        ModelServiceProviderReq providerReq = buildProviderReq();
        return providerMgmtService.createModelServiceProviders(projectId, workspaceId, providerReq);
    }

    public ModelServiceProviderReq buildProviderReq() {
        ModelServiceProviderReq serviceProviderReq = new ModelServiceProviderReq();
        serviceProviderReq.setProviderName(CommonConstant.ProviderParam.IMPORT_DEFAULT_PROVIDER_NAME);
        serviceProviderReq.setProviderNameEn(CommonConstant.ProviderParam.IMPORT_DEFAULT_PROVIDER_NAME);
        serviceProviderReq.setAuthInfo("{}");
        serviceProviderReq.setAuthType(CommonConstant.ProviderParam.NO_AUTH);
        serviceProviderReq.setLogo(defaultImportModelIcon);
        serviceProviderReq.setDescription("import default create");
        return serviceProviderReq;
    }

    public Map<String, Map<String, String>> extractModelByWorkflow(WorkflowExportEntity workflowExportEntity) {
        List<WorkflowNodeVO> modelNodes = workflowExportEntity.getDsl()
            .getNodes()
            .stream()
            .filter((WorkflowNodeVO workflowNodeVo) -> CommonConstant.LLM_CONFIG_NODE.contains(workflowNodeVo.getType())
                && !Objects.isNull(workflowNodeVo.getConfigs())
                && !Objects.isNull(workflowNodeVo.getConfigs().get(CommonConstant.Workflow.MODEL)))
            .toList();
        Map<String, Map<String, String>> models = new HashMap<>();
        for (WorkflowNodeVO modelNodeVo : modelNodes) {
            // 大模型等节点配置在config中的 model下，意图识别节点为 llm
            Map<String, String> modelConfigsMap =
                JsonUtils.objectToClass(modelNodeVo.getConfigs().get(CommonConstant.Workflow.MODEL) != null
                    ? modelNodeVo.getConfigs().get(CommonConstant.Workflow.MODEL)
                    : modelNodeVo.getConfigs().get(NodeType.LLM.getType()));
            if (Objects.isNull(modelConfigsMap)) {
                continue;
            }
            String modelDeploymentId = modelConfigsMap.get(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID);
            if (StringUtils.isBlank(modelDeploymentId)) {
                continue;
            }
            models.put(modelDeploymentId, modelConfigsMap);
        }
        return models;
    }

    private void importReleaseVersion(String projectId, String targetWorkspaceId,
        WorkflowExportEntity workflowExportEntity, WorkflowEntity metadata) {
        ReleaseVersion releaseVersion = workflowExportEntity.getReleaseVersion();
        if (releaseVersion != null) {
            // 这里用metadata.getId()，而不用releaseVersion里面的版本，因为工作流ID可能变了
            releaseVersion.setAppId(metadata.getId());
            ReleaseVersion existVersion =
                releaseVersionMapper.selectByAppIdAndVersionId(metadata.getId(), releaseVersion.getVersionId());

            // 版本不存在导入版本
            if (existVersion == null) {
                importWorkflowVersion(projectId, targetWorkspaceId, workflowExportEntity, releaseVersion);
            }
        }
    }

    public void importWorkflowVersion(String projectId, String targetWorkspaceId, WorkflowExportEntity versionEntity,
        ReleaseVersion releaseVersion) {
        String workflowId = versionEntity.getMetadata().getId();
        String versionId = releaseVersion.getVersionId();
        // 1.备份dsl和ir
        String releaseDslPath = mgObsService.uploadObsFile(versionEntity.getMetadata().getId(),
            workflowId + Constants.UNDERLINE_STR + versionId, CommonConstant.WORKFLOW,
            JSONObject.toJSONString(versionEntity.getDsl()), CommonConstant.Workflow.FLOW);
        String releaseIrPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW,
            CommonConstant.Workflow.IR, workflowId, workflowId + Constants.UNDERLINE_STR + versionId);

        // 2. 创建版本数据
        releaseVersion.setId(UUID.randomUUID().toString());
        releaseVersion.setAppId(workflowId);
        releaseVersion.setDslPath(releaseDslPath);
        releaseVersion.setIrPath(releaseIrPath);
        releaseVersion.setCreatorId(RequestContextUtils.getRequestUserId());
        releaseVersion.setCreator(RequestContextUtils.getRequestUserName());
        releaseVersionMapper.insert(releaseVersion);

        // 3. 记录关联关系
        workflowManagementService.updateRefResources(versionEntity.getDsl(), versionId);

        // 4.更新工作流最新版本
        WorkflowEntity workflowEntity =
            workflowCommonService.getWorkflowByWorkspaceAndOpProject(projectId, targetWorkspaceId, workflowId);
        if (StringUtils.isEmpty(workflowEntity.getLastVersionId())
            || Long.parseLong(versionId) > Long.parseLong(workflowEntity.getLastVersionId())) {
            workflowEntity.setLastVersionId(versionId);
            workflowEntity.setStatus(CommonConstant.WORKFLOW_PUBLISHED);
            workflowMapper.updateWorkflowEntity(projectId, workflowId, workflowEntity);
        }

        // 子工作流版本ir转换放到最后,保证ir转换失败时（缺少预置插件/MCP服务等情况）不影响整体导入
        try {
            workflowManagementService.workflowDslToIr(workflowId, versionEntity.getMetadata(), versionEntity.getDsl(),
                versionId);
            log.info("Succeed to refresh subWorkflow ir, workflow id = {}", workflowId);
        } catch (Exception e) {
            String errorMsg = String.format("Failed to refresh subWorkflow ir, workflow id = %s", workflowId);
            log.error(errorMsg, e);
        }

        // 如果导入的工作流有版本且已发布，需要在obs中生成环境变量的副本
        if (versionEntity.getDsl().getConfigs() == null || versionEntity.getDsl().getConfigs().isEmpty()) {
            return;
        }
        if (!versionEntity.getDsl().getConfigs().containsKey(Constants.Workflow.ENVIRONMENT)
            || versionEntity.getDsl().getConfigs().get(Constants.Workflow.ENVIRONMENT) == null || StringUtils
                .isBlank(versionEntity.getDsl().getConfigs().get(Constants.Workflow.ENVIRONMENT).toString())) {
            return;
        }
        String environmentId = versionEntity.getDsl().getConfigs().get(Constants.Workflow.ENVIRONMENT).toString();
        try {
            String environmentVariables = this.environmentServiceManagerService.queryEnvironmentVariables(projectId,
                environmentId, targetWorkspaceId);
            if (StringUtils.isBlank(environmentVariables)) {
                return;
            }
            mgObsService.uploadObsFile(workflowId,
                StringUtils.join(workflowId, Constants.UNDERLINE_STR, versionId, "_env"), CommonConstant.WORKFLOW,
                environmentVariables, CommonConstant.Workflow.IR);
            log.info("Succeed to refresh environment variable file, workflow id = {}", workflowId);
        } catch (Exception e) {
            log.error("Failed to refresh environment variable file, workflow id = {}", workflowId);
        }
    }

    private boolean importWorkflowEntity(String projectId, String targetWorkspaceId,
        WorkflowExportEntity workflowExportEntity, WorkflowEntity metadata) {
        WorkflowVO dsl = JsonUtils.json2ObjQuietly(JsonUtils.toJson(workflowExportEntity.getDsl()), WorkflowVO.class);
        try {
            // 设置唯一的工作流名称
            setWorkflowName(projectId, targetWorkspaceId, metadata);

            Set<String> blockNodeSet = Arrays.stream(StringUtils.split(blockNodes, ",")).collect(Collectors.toSet());
            // 校验导入工作流是否包含隐藏节点
            if (dsl != null && dsl.getNodes() != null
                && dsl.getNodes().stream().anyMatch(node -> blockNodeSet.contains(node.getType()))) {
                log.error("workflow validate failed because contains block nodes");
                throw new AgentStudioException(StudioError.WORKFLOW_BLOCK_NODE_EXIST, blockNodes);
            }

            // 导入DSL文件和metadata
            String workflowJsonStr = jacksonObjectMapper.writeValueAsString(dsl);
            String relativePath = mgObsService.uploadObsFile(dsl.getId(), dsl.getId(), CommonConstant.WORKFLOW,
                workflowJsonStr, CommonConstant.Workflow.FLOW);
            String irPath = String.format(AGENT_OBS_PATH_TEMPLATE, CommonConstant.WORKFLOW, CommonConstant.Workflow.IR,
                dsl.getId(), dsl.getId());
            workflowManagementService.updateRefResources(dsl, null);

            // 只要存在已发布版本，均为发布状态
            List<ReleaseVersion> versionList = releaseVersionMapper.selectByAppId(metadata.getId());
            boolean isPublished =
                workflowExportEntity.getReleaseVersion() != null || CollectionUtils.isNotEmpty(versionList);
            metadata.setStatus(isPublished ? CommonConstant.WORKFLOW_PUBLISHED : CommonConstant.WORKFLOW_DEVELOP);

            importWorkflowMetadata(projectId, targetWorkspaceId, relativePath, irPath, metadata);
        } catch (Exception e) {
            log.error(String.format("Failed to import workflow: %s", metadata.getId()), e);
            return false;
        }
        log.info("Succeed to import workflow: {}", metadata.getId());

        // IR转换并上传到OBS
        try {
            Map<String, Object> metadataIr = workflowCommonService.parseMetadata(metadata);
            Map<String, Object> irInfo = irAdapterService.adaptWorkflow(dsl, metadataIr);
            mgObsService.uploadObsFile(metadata.getId(), metadata.getId(), CommonConstant.WORKFLOW,
                JSON.toJSONString(irInfo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.IR);
            log.info("Succeed to refresh ir, workflow id = {}", metadata.getId());
        } catch (Exception e) {
            log.error("Failed to refresh ir, workflow id = {}", metadata.getId());
        }
        return true;
    }

    private void setWorkflowName(String projectId, String workspaceId, WorkflowEntity metadata) {
        String importWorkflowName = metadata.getName();
        List<WorkflowEntity> workflowEntityList =
            workflowMapper.selectByTraceId(projectId, workspaceId, metadata.getTraceId());

        if (CollectionUtils.isEmpty(workflowEntityList)) {
            return;
        }

        WorkflowEntity workflow = workflowEntityList.get(0);

        if (workflow.getName().equalsIgnoreCase(importWorkflowName)) {
            return;
        }

        List<WorkflowEntity> workflowList =
            workflowMapper.getAvailableWorkflowEntityByWorkspaceId(projectId, workspaceId);

        if (CollectionUtils.isEmpty(workflowList)) {
            return;
        }

        String curName = workflow.getName();
        Set<String> currentNameSet = workflowList.stream()
            .map(WorkflowEntity::getName)
            .filter(name -> !name.equalsIgnoreCase(curName))
            .collect(Collectors.toCollection(() -> new TreeSet<>(String.CASE_INSENSITIVE_ORDER)));

        if (currentNameSet.contains(importWorkflowName)) {
            importWorkflowName = subName(importWorkflowName, CommonConstant.NAME_MAX_LEN);
            int index = 1;
            while (currentNameSet.contains(importWorkflowName + Constants.UNDERLINE_STR + index)) {
                index++;
            }
            metadata.setName(importWorkflowName + Constants.UNDERLINE_STR + index);
        }
    }

    private boolean importSubWorkflows(String projectId, String targetWorkspaceId,
        WfImportDataWrapper wfImportDataWrapper, List<WorkflowExportEntity> subWorkflows) {
        if (!CollectionUtils.isEmpty(subWorkflows)) {
            for (WorkflowExportEntity subWorkflow : subWorkflows) {
                // 判断该工作流是否在需要导入的工作流中，不在的话表示：环境中已存在该工作流配置，且不选择覆盖掉该配置
                if (!wfImportDataWrapper.getImportWorkflowList().contains(subWorkflow.getMetadata().getId())) {
                    continue;
                }

                // 导入工作流逻辑
                if (!importWorkflowsHandler(projectId, targetWorkspaceId, subWorkflow, wfImportDataWrapper)) {
                    wfImportDataWrapper.getImportResList()
                        .add(buildImportRes(subWorkflow.getMetadata().getId(), subWorkflow.getMetadata().getName(),
                            ImportResourceType.WORKFLOW.toString(), subWorkflow.getReleaseVersion(), "FAILED"));
                    return false;
                }
                log.info("Succeed to import workflow: {}", subWorkflow.getMetadata().getId());
                wfImportDataWrapper.getImportResList()
                    .add(buildImportRes(subWorkflow.getMetadata().getId(), subWorkflow.getMetadata().getName(),
                        ImportResourceType.WORKFLOW.toString(), subWorkflow.getReleaseVersion(), "SUCCESS"));
            }
        }
        return true;
    }

    private @Nullable void importTools(String projectId, String targetWorkspaceId,
        WorkflowExportEntity workflowExportEntity, WfImportDataWrapper wfImportDataWrapper) {
        List<ToolEntity> tools = workflowExportEntity.getPlugins();

        if (tools != null && !tools.isEmpty()) {
            for (ToolEntity tool : tools) {
                // 预置插件处理
                parseWorkflowInnerTool(projectId, tool, wfImportDataWrapper.getInnerPluginsMsg());

                // 判断该插件是否在需要导入的插件中，不在的话表示：环境中已存在该插件配置，且不选择覆盖掉该配置
                String toolId = tool.getToolId();
                if (!wfImportDataWrapper.getImportToolList().contains(toolId)) {
                    continue;
                }

                if (Strings.CS.equals(tool.getType(), ToolType.INNER.type) && toolMapperDiscard
                    .selectByProjectId(pluginAdapterImpl.getPluginId(toolId), projectId, opSvcProjectId) == null) {
                    wfImportDataWrapper.getInnerPluginsMsg()
                        .add(new ExtraMsg().setId(toolId).setName(tool.getToolDisplayName()));
                    continue;
                }

                // 导入该插件
                if (!Strings.CS.equals(tool.getType(), ToolType.INNER.type) && !importToolsHandler(projectId,
                    targetWorkspaceId, tool, wfImportDataWrapper.getPluginsOfAuth())) {
                    log.error("Fail to import workflow: {}, caused by tool:{} fails to be imported.",
                        workflowExportEntity.getMetadata().getId(), toolId);
                    wfImportDataWrapper.getImportResList()
                        .add(buildImportRes(tool.getToolId(), tool.getToolDisplayName(),
                            ImportResourceType.PLUGIN.toString(), workflowExportEntity.getReleaseVersion(), "FAILED"));
                    return;
                }
                log.info("Succeed to import tool: {}", toolId);
                wfImportDataWrapper.getImportResList()
                    .add(buildImportRes(tool.getToolId(), tool.getToolDisplayName(),
                        ImportResourceType.PLUGIN.toString(), workflowExportEntity.getReleaseVersion(), "SUCCESS"));
            }
        }
    }

    private void buildImportRsp(ImportRsp importResponse, WfImportDataWrapper wfImportDataWrapper) {
        importResponse.setCount(wfImportDataWrapper.getImportResList().size());
        importResponse.setSucceedIds(wfImportDataWrapper.getSucceedIds());
        importResponse.setFailedIds(wfImportDataWrapper.getFailedIds());
        importResponse.setSucceedLen(wfImportDataWrapper.getSucceedIds().size());
        importResponse.setFailedLen(wfImportDataWrapper.getFailedIds().size());
        importResponse.setAuthPluginsMsg(new ArrayList<>(wfImportDataWrapper.getPluginsOfAuth()));
        importResponse.setInnerPluginsMsg(new ArrayList<>(wfImportDataWrapper.getInnerPluginsMsg()));
        importResponse.setAuthMcpsMsg(new ArrayList<>(wfImportDataWrapper.getMcpsOfAuth()));
        importResponse.setImportList(new ArrayList<>(wfImportDataWrapper.getImportResList()));
    }

    /**
     * 导入插件兼容旧版本
     *
     * @param tool 原插件对象
     */
    private void adaptImportTool(ToolEntity tool) {
        // 为旧版本导出的插件中不含有的字段赋值
        if (StringUtils.isEmpty(tool.getVisibility())) {
            tool.setVisibility(CommonConstant.VISIBILITY_SCOPE.PROJECT);
        }
        if (StringUtils.isEmpty(tool.getToolChineseName())) {
            tool.setToolChineseName(tool.getToolDisplayName());
        }
    }

    /**
     * 导出插件时进行解密
     *
     * @param tool 插件信息
     */
    private void decryptedExportTool(ToolEntity tool) {
        if (!Objects.isNull(tool.getRequestInfo())) {
            Map<String, String> headers = tool.getRequestInfo().getHeaders();
            if (MapUtils.isEmpty(headers)) {
                return;
            }
            try {
                headers.forEach((key, value) -> headers.put(key, CryptoUtils.decrypt(value)));
            } catch (Exception e) {
                // 历史存量数据未加密，会解密失败
                log.warn("Fail to decrypt plugin header [{}].", tool.getToolDisplayName());
            }
        }
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
     * 该插件若为共享插件,是否为自有插件
     * @param toolId
     */
    public boolean isOwnSharePlugin(String toolId) {
        String[] split = toolId.split("#");
        String id = split[0];

        // 若为引用的共享插件,则跳过
        ShareResourceEntity shareResourceEntity = shareResourceManagerService.queryShareResourceEntityByResourceId(id);
        if (shareResourceEntity!= null && !Strings.CS.equals(RequestContextUtils.getRequestWorkspaceId(), shareResourceEntity.getWorkspaceId())) {
            return false;
        }
        return true;
    }





}
