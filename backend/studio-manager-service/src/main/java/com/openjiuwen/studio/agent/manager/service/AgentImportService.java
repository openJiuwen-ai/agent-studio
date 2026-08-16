/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.COMMON_AGENT_TYPE;
import static com.openjiuwen.studio.agent.manager.constant.CommonConstant.KB;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.FileCommonUtils;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.ControllerIR;
import com.openjiuwen.studio.agent.manager.dto.ControllerNodeVO;
import com.openjiuwen.studio.agent.manager.dto.ControllerVO;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.common.dto.ImportRes;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.McpServerReference;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionInfo;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.WorkflowReference;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareInfo;
import com.openjiuwen.studio.agent.manager.entity.SpaciousInfo;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginVO;
import com.openjiuwen.studio.agent.manager.enums.ExportModeEnum;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.controller.AgentNodeType;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthMetadataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.MapReadUtil;
import com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapterFactory;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportCheckResult;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportExportStatusEnum;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ImportResourceResult;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

@Service
@Slf4j
public class AgentImportService {

    @Value("${agent.max-upload-file-size}")
    private long fileMaxSize;

    @Value("${export.max-length}")
    private int importMaxLen;

    private static final String IMPORT_FILE_TYPE = ".jsonl";

    public static final String LATEST_PARAM = "{{latest}}";

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private SkuManageService skuManageService;

    @Autowired
    private ResourceAdapterFactory resourceAdapterFactory;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private MgObsService mgObsService;

    @Autowired
    private AgentCommonService agentCommonService;

    @Autowired
    private IrAdapterService irAdapterService;

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private WorkflowCommonService workflowCommonService;

    @Autowired
    private ControllerManagementService controllerManagementService;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private ProviderAuthMetadataMapper providerAuthMetadataMapper;

    @Autowired
    private RouterStrategyMapper routerStrategyMapper;

    @Autowired
    private MemoryRepoMapper memoryRepoMapper;

    /**
     * 导入前检查
     *
     * @param projectId projectId
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，其中一条jsonl表示一个资源的配置
     * @return listImportFile 根据文件内容解析出来的配置
     */
    public List<ImportListInfo> checkBeforeImportFile(String workspaceId, String projectId, MultipartFile file) {
        List<ImportInfo> resourceList = getAndValidateImportInfos(workspaceId, file);
        List<ImportListInfo> result = new ArrayList<>();
        resourceList.forEach(p -> {
            initImportData(workspaceId, projectId, p);
            ImportCheckResult importCheckResult = setBaseImportCheckResult(p);
            try {
                resourceAdapterFactory.getAdapter(p.getResourceType()).checkBeforeImport(importCheckResult, p);
            } catch (Exception e) {
                log.error(e.getMessage(), e);
            }
            result.add(importCheckResult2Info(importCheckResult));
        });
        return handleCheckResult(resourceList, result);
    }

    @NotNull
    private List<ImportInfo> getAndValidateImportInfos(String workspaceId, MultipartFile file) {
        checkImportFile(file);
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        List<ImportInfo> resourceList = getImportInfos(file);
        validateImportAppCount(workspaceId, resourceList);
        return resourceList.stream().sorted((v1, v2) -> {
            int orderCompare = Integer.compare(v1.getOrder(), v2.getOrder());
            if (orderCompare != 0) {
                return orderCompare;
            }
            return Integer.compare(v2.getLevel(), v1.getLevel());
        }).collect(Collectors.toList());
    }

    private void initImportData(String workspaceId, String projectId, ImportInfo p) {
        p.setTargetProjectId(projectId);
        p.setTargetWorkspaceId(workspaceId);
        p.setTargetWorkspaceName(RequestContextUtils.getRequestWorkspaceName());
        p.setTargetDomainId(RequestContextUtils.getRequestUserDomainId());
        p.setCreator(RequestContextUtils.getRequestUserName());
        p.setCreatorId(RequestContextUtils.getRequestUserId());
    }

    private List<ImportInfo> getImportInfos(MultipartFile file) {
        List<ImportInfo> resourceList = new ArrayList<>();
        try (BufferedReader bufferedReader = new BufferedReader(
            new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            // 逐行读取文件中的jsonl配置
            while (StringUtils.isNotEmpty(line = bufferedReader.readLine())) {
                ImportInfo importInfo = jacksonObjectMapper.readValue(line, ImportInfo.class);
                if (importInfo.getOrder() == 404) {
                    log.error("the file exist unsupported resource: {}", importInfo.getResourceType());
                    throw new AgentStudioException(StudioError.UNSUPPORTED_RESOURCE_IMPORT, importInfo.getResourceType());
                }
                if (!Strings.CS.equals(importInfo.getResourceType(), CommonConstant.EXPORT_V2_TYPE)) {
                    resourceList.add(importInfo);
                }
                if (resourceList.size() >= importMaxLen) {
                    break;
                }
            }

        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("listImportFile file:{}, error: {}", i18nUtil.getMessage(StudioError.FILE_RESOLVE_FILE),
                e.getMessage());
            throw new AgentStudioException(StudioError.FILE_RESOLVE_FILE);
        }
        return resourceList;
    }

    private void validateImportAppCount(String workspaceId, List<ImportInfo> resourceList) {
        List<String> importAgentList = resourceList.stream()
            .filter(v -> Strings.CS.equals(ResourceTypeEnum.AGENT.toString(), v.getResourceType()))
            .map(ImportInfo::getResourceId)
            .distinct()
            .toList();
        List<String> importWorkflowList = resourceList.stream()
            .filter(v -> Strings.CS.equals(ResourceTypeEnum.WORKFLOW.toString(), v.getResourceType()))
            .map(ImportInfo::getResourceId)
            .distinct()
            .toList();
        skuManageService.validateImportAppCountExceededLimitOrNot(importAgentList, importWorkflowList, workspaceId);
    }

    private List<ImportListInfo> handleCheckResult(List<ImportInfo> resourceList, List<ImportListInfo> resultList) {
        List<ImportListInfo> result = new ArrayList<>();
        Map<String, ImportListInfo> resultMap = resultList.stream()
            .collect(Collectors.toMap(ImportListInfo::getId, p -> p, (existing, incoming) -> existing));
        resourceList.stream().filter(v -> v.getResourceLevel() != null && v.getResourceLevel() == 1).forEach(p -> {
            ImportListInfo parentInfo = resultMap.get(p.getResourceId());
            if (CollectionUtils.isNotEmpty(p.getLevel2Resources())) {
                List<ImportListInfo> dependencies = new ArrayList<>();
                p.getLevel2Resources().forEach(resourceId -> {
                    resourceId = StringUtils.substringBefore(resourceId, "#");
                    if (resultMap.get(resourceId) != null) {
                        dependencies.add(resultMap.get(resourceId));
                    }
                });
                parentInfo.setDependencies(dependencies);
            }
            result.add(parentInfo);
        });
        return result;
    }

    /**
     * 文件导入
     *
     * @param projectId projectId
     * @param workspaceId 空间id
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，每个资源一行
     * @return ImportRsp
     */
    public ImportRsp importFile(String projectId, String workspaceId, MultipartFile file) {
        return importFile(projectId, workspaceId, file, null);
    }

    /**
     * 文件导入
     *
     * @param projectId projectId
     * @param workspaceId 空间id
     * @param file 前端传入的导入文件，文件内容格式为多条jsonl，每个资源一行
     * @param mode 导入模式
     * @return ImportRsp
     */
    public ImportRsp importFile(String projectId, String workspaceId, MultipartFile file, String mode) {
        List<ImportInfo> resourceList = getAndValidateImportInfos(workspaceId, file);
        List<ImportResourceResult> result = new ArrayList<>();
        resourceList.forEach(p -> {
            initImportData(workspaceId, projectId, p);
            ImportResourceResult importResourceResult = setBaseImportResult(p);
            try {
                resourceAdapterFactory.getAdapter(p.getResourceType()).parseImport(importResourceResult, p);
            } catch (AgentStudioException e) {
                importResourceResult.setStatus(ImportExportStatusEnum.FAILED.getCode());
                importResourceResult.setErrorMsg(i18nUtil.getMessage(e.getErrorCode()));
                importResourceResult.setSuggestion(i18nUtil.getSuggestion(e.getErrorCode()));
            } catch (Exception e) {
                log.error("resourceAdapter error,resourceType:{},resourceId:{},resourceName:{}", p.getResourceType(),
                    p.getResourceId(), p.getResourceName(), e);
                importResourceResult.setStatus(ImportExportStatusEnum.FAILED.getCode());
                importResourceResult.setErrorMsg(i18nUtil.getMessage(StudioError.UNEXPECTED_ERROR));
            }
            result.add(importResourceResult);
        });
        if (Strings.CS.equals(mode, ExportModeEnum.SPACIOUS.getCode())) {
            handleSpaciousImport(projectId, workspaceId, resourceList, result);
        } else {
            handleStrictImport(projectId, resourceList, result);
        }
        return handleImportRsp(resourceList, result);
    }

    /**
     * 宽松导入模式
     *
     * @param projectId
     * @param workspaceId
     * @param resourceList
     * @param result
     */
    private void handleSpaciousImport(String projectId, String workspaceId, List<ImportInfo> resourceList,
        List<ImportResourceResult> result) {
        Map<String, ImportResourceResult> resultMap = result.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, r -> r, (existing, incoming) -> existing));

        resourceList = resourceList.stream()
            .filter(p -> Strings.CS.equalsAny(p.getResourceType(), ResourceTypeEnum.WORKFLOW.toString(),
                ResourceTypeEnum.CONTROLLER.toString()))
            .filter(p -> p.getDsl() != null)
            .toList();
        for (ImportInfo importInfo : resourceList) {
            ImportResourceResult importResult = resultMap.get(importInfo.getResourceId());
            try {
                if (importResult == null || Strings.CS.equals(importResult.getStatus(),
                    ImportExportStatusEnum.FAILED.getCode())) {
                    continue;
                }
                List<MappingEntity> l1Mappings = importInfo.getL1Mappings();
                if (CollectionUtils.isEmpty(l1Mappings)) {
                    continue;
                }
                // 最新版本的信息构造
                List<SpaciousInfo> spaciousInfoList = getSpaciousInfos(projectId, workspaceId, l1Mappings);
                String dslJson = JSON.toJSONString(importInfo.getDsl());

                if (Strings.CS.equals(importInfo.getResourceType(), ResourceTypeEnum.WORKFLOW.toString())) {
                    WorkflowVO workflowVO = JSONObject.parseObject(dslJson, WorkflowVO.class);
                    handleSpaciousWorkflowDsl(workflowVO, spaciousInfoList);
                    importInfo.setDsl(workflowVO);
                } else if (Strings.CS.equals(importInfo.getResourceType(), ResourceTypeEnum.CONTROLLER.toString())) {
                    ControllerVO controllerVO = JSONObject.parseObject(dslJson, ControllerVO.class);
                    handleSpaciousControllerWorkflow(importInfo, controllerVO, projectId, workspaceId, spaciousInfoList);
                    handleSpaciousSubController(controllerVO, projectId, workspaceId, spaciousInfoList);
                    importInfo.setDsl(controllerVO);
                } else {
                    continue;
                }
                handleSpaciousMappingAndDsl(importInfo, spaciousInfoList, result);
            } catch (AgentStudioException e) {
                log.error("import spacious error, resourceId:{}, resourceType:{}", importInfo.getResourceId(), importInfo.getResourceType());
                // 删除插入的主数据
                importResult.setStatus(ImportExportStatusEnum.FAILED.getCode());
                importResult.setErrorMsg(i18nUtil.getMessage(e.getErrorCode()));
                importResult.setSuggestion(i18nUtil.getSuggestion(e.getErrorCode()));
                handleException(importInfo, importResult);
            } catch (Exception e) {
                log.error("resourceAdapter error,resourceType:{},resourceId:{},resourceName:{}", importInfo.getResourceType(),
                    importInfo.getResourceId(), importInfo.getResourceName(), e);
                importResult.setStatus(ImportExportStatusEnum.FAILED.getCode());
                importResult.setErrorMsg(i18nUtil.getMessage(StudioError.UNEXPECTED_ERROR));
                handleException(importInfo, importResult);
            }

        }
    }

    private void handleException(ImportInfo importInfo, ImportResourceResult importResult) {
        if (importResult.getAddTag()){
            String resourceId = StringUtils.isEmpty(importResult.getNewId()) ? importInfo.getResourceId() : importResult.getNewId();
            if (Strings.CS.equals(importInfo.getResourceType(), ResourceTypeEnum.WORKFLOW.toString())) {
                workflowMapper.deleteByPrimaryKeys(List.of(resourceId));
            }
            if (Strings.CS.equals(importInfo.getResourceType(), ResourceTypeEnum.CONTROLLER.toString())) {
                agentMapper.deleteByPrimaryKeys(List.of(resourceId));
            }
        }
    }

    private @NotNull List<SpaciousInfo> getSpaciousInfos(String projectId, String workspaceId,
        List<MappingEntity> l1Mappings) {
        List<SpaciousInfo> spaciousInfoList = new ArrayList<>();
        for (MappingEntity mapping : l1Mappings) {
            String latestVersionId = null;
            String latestVersionName = null;
            String targetResourceId = null;
            if (Strings.CS.equals(mapping.getResourceType(), ResourceTypeEnum.WORKFLOW.toString())) {
                List<WorkflowEntity> workflows = workflowMapper.selectByTraceId(projectId, workspaceId,
                    mapping.getTraceId());
                if (CollectionUtils.isNotEmpty(workflows)) {
                    WorkflowEntity wf = workflows.get(0);
                    targetResourceId = wf.getId();
                    List<ReleaseVersion> versions = releaseVersionMapper.selectByAppId(targetResourceId);
                    if (CollectionUtils.isNotEmpty(versions)) {
                        latestVersionId = versions.get(0).getVersionId();
                        latestVersionName = versions.get(0).getVersionName();
                    }
                }
            } else if (Strings.CS.equals(mapping.getResourceType(), ResourceTypeEnum.CONTROLLER.toString())) {
                List<Agent> agents = agentMapper.selectAgentByTraceIdAndWorkspaceId(projectId, workspaceId,
                    mapping.getTraceId());
                if (CollectionUtils.isNotEmpty(agents)) {
                    Agent agent = agents.get(0);
                    targetResourceId = agent.getAgentId();
                    List<ReleaseVersion> versions = releaseVersionMapper.selectByAppId(agent.getAgentId());
                    if (CollectionUtils.isNotEmpty(versions)) {
                        latestVersionId = versions.get(0).getVersionId();
                        latestVersionName = versions.get(0).getVersionName();
                    }
                }
            } else if (Strings.CS.equals(mapping.getResourceType(), ResourceTypeEnum.MODEL.toString())) {
                // 宽松导入：按模型 identityId 在目标空间匹配等价模型。源空间模型的 mapping.resourceId 即其 id，
                // 首建模型 id==identityId，可直接作为查询键；导入来的模型 id!=identityId 时查不到则保持原值（不抛异常）。
                List<ModelServiceBase> models = modelServiceMapper.queryByIdentityId(projectId, workspaceId,
                    mapping.getResourceId());
                if (CollectionUtils.isNotEmpty(models)) {
                    targetResourceId = models.get(0).getId();
                }
            }
            if (StringUtils.isNotEmpty(targetResourceId)) {
                SpaciousInfo spaciousInfo = new SpaciousInfo();
                spaciousInfo.setTargetResourceId(targetResourceId);
                spaciousInfo.setOriginalResourceId(mapping.getResourceId());
                spaciousInfo.setLatestVersionId(latestVersionId);
                spaciousInfo.setLatestVersionName(latestVersionName);
                spaciousInfoList.add(spaciousInfo);
            }
        }
        return spaciousInfoList;
    }

    private void handleSpaciousWorkflowDsl(WorkflowVO workflowVO, List<SpaciousInfo> spaciousInfoList) {
        workflowVO.getNodes().forEach(node -> {
            if (!Strings.CI.equals(node.getType(), NodeType.WORKFLOW.getType())) {
                return;
            }
            Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
            SpaciousInfo relationInfo = spaciousInfoList.stream()
                .filter(p -> Strings.CS.equals(p.getOriginalResourceId(), String.valueOf(configs.get("id"))))
                .findFirst().orElse(null);
            handleSpaciousVersionResource(configs, relationInfo);
            node.setConfigs(configs);
        });
    }

    private void handleSpaciousMappingAndDsl(ImportInfo importInfo, List<SpaciousInfo> spaciousInfoList,
        List<ImportResourceResult> result) {
        List<MappingEntity> l1Mappings = importInfo.getL1Mappings();
        if (CollectionUtils.isEmpty(l1Mappings)) {
            log.info("spacious mapping is null");
            return;
        }
        Map<String, SpaciousInfo> spaciousInfoMap = new HashMap<>();
        if (CollectionUtils.isNotEmpty(spaciousInfoList)) {
            spaciousInfoMap = spaciousInfoList.stream()
                .collect(
                    Collectors.toMap(SpaciousInfo::getOriginalResourceId, v -> v, (existing, incoming) -> existing));
        }

        Map<String, ImportResourceResult> importResourceResultMap = result.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, v -> v, (existing, incoming) -> existing));
        ImportResourceResult importResourceResult = importResourceResultMap.get(importInfo.getResourceId());

        String appId = (importResourceResult == null || StringUtils.isEmpty(importResourceResult.getNewId()))
            ? importInfo.getResourceId()
            : importResourceResult.getNewId();
        String appVersion = null;
        String importInfoResourceType = importInfo.getResourceType();
        if (Objects.nonNull(importInfo.getReleaseVersion())) {
            ReleaseVersion releaseVersion = importInfo.getReleaseVersion();
            appVersion = (importResourceResult == null || StringUtils.isEmpty(importResourceResult.getNewVersion()))
                ? releaseVersion.getVersionId()
                : importResourceResult.getNewVersion();
            String obsKey = appId + Constants.UNDERLINE_STR + appVersion;
            if (Strings.CS.equals(importInfoResourceType, ResourceTypeEnum.CONTROLLER.toString())) {
                uploadControllerDsl(importInfo, appId, appVersion);
            } else {
                uploadWorkflowDsl(importInfo, appId, obsKey, appVersion);
            }
            insertMapping(l1Mappings, spaciousInfoMap, appId, appVersion);
        }
        // 草稿态：先删除旧草稿态mapping，再重新上传替换后的草稿DSL和插入新草稿态mapping，
        // 确保草稿DSL中子流节点version_id已被替换，mapping表指向目标空间子资源最新版本
        mappingMapper.deleteBatchByAppId(appId, null, false);
        if (Strings.CS.equals(importInfoResourceType, ResourceTypeEnum.CONTROLLER.toString())) {
            uploadControllerDsl(importInfo, appId, null);
        } else {
            uploadWorkflowDsl(importInfo, appId, appId, null);
        }
        insertMapping(l1Mappings, spaciousInfoMap, appId, null);

    }

    private void insertMapping(List<MappingEntity> l1Mappings, Map<String, SpaciousInfo> spaciousInfoMap, String appId,
        String appVersion) {
        List<MappingEntity> mappingEntities = new ArrayList<>();
        for (MappingEntity l1Mapping : l1Mappings) {
            SpaciousInfo spaciousInfo = spaciousInfoMap.get(l1Mapping.getResourceId());
            MappingEntity mappingEntity = new MappingEntity();
            BeanUtils.copyProperties(l1Mapping, mappingEntity);
            mappingEntity.setMappingId(UUID.randomUUID().toString());
            mappingEntity.setAppId(appId);
            mappingEntity.setAppVersion(appVersion);
            mappingEntity.setValid(false);
            if (spaciousInfo != null) {
                mappingEntity.setValid(true);
                mappingEntity.setResourceId(spaciousInfo.getTargetResourceId());
                mappingEntity.setResourceName(spaciousInfo.getLatestVersionName());
                mappingEntity.setResourceVersion(spaciousInfo.getLatestVersionId());
            }
            mappingEntities.add(mappingEntity);
        }
        mappingMapper.insertBatch(mappingEntities);
    }

    private void handleSpaciousSubController(ControllerVO controllerVO, String projectId, String workspaceId,
        List<SpaciousInfo> spaciousInfoList) {
        controllerVO.getNodes().forEach(node -> {
            if (Strings.CS.equals(node.getType(), AgentNodeType.SUB_CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                SpaciousInfo relationInfo = getNodeSpaciousInfo(spaciousInfoList, node, String.valueOf(configs.get("id")));
                handleSpaciousVersionResource(configs, relationInfo);
                // 宽松模式：SubController 节点自身的 model 和 workflows[] 引用一并替换。
                // 源空间 workflow 的 id==traceId，selectByTraceId 在目标空间命中后替换为新 id；
                // version_id 为 {{latest}} 时用命中工作流最新发布版本替换。命中不到则保持原值。
                replaceSpaciousModel(configs, spaciousInfoList);
                replaceSpaciousWorkflows(configs, projectId, workspaceId);
                node.setConfigs(configs);
            }
            if (Strings.CS.equals(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                List<Map<String, Object>> agents = MapReadUtil.safeCastToListWithMap(configs.get("agents"));
                agents.forEach(agentMap -> {
                    String resourceId = String.valueOf(agentMap.get("id"));
                    Map<String, Object> agentConfigs = MapReadUtil.safeCastToMapWithStringKey(agentMap.get("configs"));
                    SpaciousInfo relationInfo = getSpaciousInfo(spaciousInfoList, agentMap, resourceId);
                    handleSpaciousVersionResource(agentConfigs, relationInfo);
                    agentMap.put("configs", agentConfigs);
                });
                configs.put("agents", agents);
                node.setConfigs(configs);
            }
        });
    }


    private static @Nullable SpaciousInfo getNodeSpaciousInfo(List<SpaciousInfo> spaciousInfoList, ControllerNodeVO node,
        String dslId) {
        return spaciousInfoList.stream()
            .filter(p -> Strings.CS.equals(p.getOriginalResourceId(), dslId))
            .findFirst().orElse(null);
    }

    private void handleSpaciousControllerWorkflow(ImportInfo importInfo, ControllerVO controllerVO, String projectId,
        String workspaceId, List<SpaciousInfo> spaciousInfoList) {
        controllerVO.getNodes().stream().forEach(node -> {
            if (Strings.CS.equals(node.getType(), AgentNodeType.WORKFLOW.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                SpaciousInfo relationInfo = getNodeSpaciousInfo(spaciousInfoList, node, String.valueOf(configs.get("id")));
                handleSpaciousVersionResource(configs, relationInfo);
                // 顶层 Workflow 节点：test 等工作流可能不在一级 L1Mappings（recordRefWorkflow 只记主Controller的workflows），
                // 导致无 SpaciousInfo。用 selectByTraceId 兜底：按 configs.id（源空间 workflow id==traceId）查目标空间，命中则替换 id；
                // version_id 为 {{latest}} 时用命中工作流最新版本替换。命中不到则保持原值。
                replaceSpaciousWorkflowConfigs(configs, projectId, workspaceId);
                node.setConfigs(configs);
            }
            if (Strings.CS.equals(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                List<Map<String, Object>> workflows = MapReadUtil.safeCastToListWithMap(configs.get("workflows"));
                workflows.forEach(workflowMap -> {
                    String resourceId = String.valueOf(workflowMap.get("id"));
                    SpaciousInfo relationInfo = getSpaciousInfo(spaciousInfoList, workflowMap, resourceId);
                    Map<String, Object> workflowConfigs = MapReadUtil.safeCastToMapWithStringKey(
                        workflowMap.get("configs"));
                    handleSpaciousVersionResource(workflowConfigs, relationInfo);
                    workflowMap.put("configs", workflowConfigs);
                });
                configs.put("workflows", workflows);
                // 宽松模式：主 Controller 节点的 model 按 model_deployment_id 匹配 MODEL 类 SpaciousInfo 替换
                replaceSpaciousModel(configs, spaciousInfoList);
                node.setConfigs(configs);
            }
        });

    }

    private static @Nullable SpaciousInfo getSpaciousInfo(List<SpaciousInfo> spaciousInfoList,
        Map<String, Object> workflowMap, String resourceId) {
        SpaciousInfo relationInfo = spaciousInfoList.stream()
            .filter(p -> Strings.CS.equals(p.getOriginalResourceId(), resourceId))
            .findFirst().orElse(null);
        // 替换为目标id
        if (Objects.nonNull(relationInfo) && StringUtils.isNotEmpty(relationInfo.getTargetResourceId())) {
            workflowMap.put("id", relationInfo.getTargetResourceId());
        }
        return relationInfo;
    }

    private void handleStrictImport(String projectId, List<ImportInfo> resourceList, List<ImportResourceResult> result) {
        // 处理供应商与模型的关系
        handleProviderModel(resourceList, result);
        // 处理路由策略与模型的关系
        handleStrategyModel(resourceList, result);
        // 处理依赖信息（mapping关系）
        handleMapping(resourceList, result);
        // 更新资源dsl
        try {
            handleResourceDsl(resourceList, result);
        } catch (Exception e) {
            log.error("handleResourceDsl error.", e);
        }

        // 处理分享信息
        handleShareInfo(resourceList, result, projectId);
    }

    private ImportRsp handleImportRsp(List<ImportInfo> resourceList, List<ImportResourceResult> result) {
        ImportRsp importRsp = new ImportRsp();

        Set<String> parentResourceIds = resourceList.stream()
            .filter(v -> CollectionUtils.isEmpty(v.getParents()) && !Strings.CS.equals(v.getResourceType(),
                ResourceTypeEnum.PROVIDER.toString()))
            .map(ImportInfo::getResourceId)
            .collect(Collectors.toSet());

        Map<String, ImportResourceResult> resultMap = result.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, p -> p, (existing, incoming) -> existing));
        List<ImportRes> parentImportRes = new ArrayList<>();

        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failedCount = new AtomicInteger(0);
        resourceList.stream().filter(v -> parentResourceIds.contains(v.getResourceId())).forEach(p -> {
            ImportResourceResult importResourceResult = resultMap.get(p.getResourceId());
            ImportRes importRes = importResult2Info(importResourceResult);
            List<ImportRes> dependencies = new ArrayList<>();
            if (CollectionUtils.isNotEmpty(p.getLevel2Resources())) {
                p.getLevel2Resources().forEach(resourceId -> {
                    resourceId = StringUtils.substringBefore(resourceId, "#");
                    if (resultMap.get(resourceId) != null) {
                        dependencies.add(importResult2Info(resultMap.get(resourceId)));
                    }
                });
            }
            importRes.setDependencies(dependencies);
            parentImportRes.add(importRes);
            if (ImportExportStatusEnum.SUCCESS.getCode().equals(importRes.getStatus())) {
                successCount.incrementAndGet();
            } else {
                failedCount.incrementAndGet();
            }
        });
        importRsp.setImportList(parentImportRes);
        importRsp.setSucceedLen(successCount.get());
        importRsp.setFailedLen(failedCount.get());
        importRsp.setCount(successCount.get() + failedCount.get());
        return importRsp;
    }

    private ImportRes importResult2Info(ImportResourceResult importResourceResult) {
        ImportRes info = new ImportRes();
        BeanUtils.copyProperties(importResourceResult, info);
        if (StringUtils.isNotEmpty(importResourceResult.getNewId())) {
            info.setId(importResourceResult.getNewId());
        }
        if (StringUtils.isNotEmpty(importResourceResult.getNewName())) {
            info.setName(importResourceResult.getNewName());
        }
        info.setDetail(importResourceResult.getErrorMsg());
        return info;
    }

    private ImportListInfo importCheckResult2Info(ImportCheckResult importCheckResult) {
        ImportListInfo info = new ImportListInfo();
        BeanUtils.copyProperties(importCheckResult, info);
        if (importCheckResult.getImportDesc() != null) {
            info.setImportDescription(importCheckResult.getImportDesc().getCode());
        }
        return info;
    }

    private void checkImportFile(MultipartFile file) {
        FileCommonUtils.validatedFile(file, fileMaxSize * KB, IMPORT_FILE_TYPE);
    }

    private ImportCheckResult setBaseImportCheckResult(ImportInfo importInfo) {
        ImportCheckResult result = new ImportCheckResult();
        result.setId(importInfo.getResourceId());
        result.setName(importInfo.getResourceName());
        result.setType(importInfo.getResourceType());
        return result;
    }

    /**
     * 初始化导入功能的返回结果
     * @return
     */
    private ImportResourceResult setBaseImportResult(ImportInfo importInfo) {
        ImportResourceResult result = new ImportResourceResult();
        result.setId(importInfo.getResourceId());
        result.setName(importInfo.getResourceName());
        result.setType(importInfo.getResourceType());
        result.setStatus(ImportExportStatusEnum.SUCCESS.getCode());
        return result;
    }

    private void handleShareInfo(List<ImportInfo> resourceList, List<ImportResourceResult> resultList,
        String projectId) {
        if (CollectionUtils.isEmpty(resourceList) || CollectionUtils.isEmpty(resultList)) {
            return;
        }
        // 将resultList转换为Map以提高查找效率
        Map<String, ImportResourceResult> resultMap = resultList.stream()
            .collect(Collectors.toMap(v -> v.getId(), v -> v, (existing, incoming) -> existing));

        resourceList.stream().filter(v -> v.getShareInfo() != null).forEach(p -> {
            ImportResourceResult result = resultMap.get(p.getResourceId());
            if (result == null || Strings.CS.equals(result.getStatus(), ImportExportStatusEnum.FAILED.getCode())) {
                return;
            }
            ShareInfo shareInfo = updateShare(p);
            handleResourceIdAndName(result, shareInfo, p);
            handleVersionInfo(result, shareInfo);
            shareResourceManagerService.importShareResourceInfo(projectId, shareInfo.getResourceId(), shareInfo);
            shareResourceManagerService.importShareResourceScope(projectId, shareInfo.getResourceId(),
                shareInfo.getShareScopeEntityList());
        });
    }

    private ShareInfo updateShare(ImportInfo p) {
        ShareInfo shareInfo = p.getShareInfo();
        shareInfo.setWorkspaceId(p.getTargetWorkspaceId());
        shareInfo.setProjectId(p.getTargetProjectId());
        shareInfo.setWorkspaceName(p.getTargetWorkspaceName());
        shareInfo.setCreator(p.getCreator());
        shareInfo.setCreatorId(p.getCreatorId());
        shareInfo.setCreateTime(new Date());
        shareInfo.setUpdater(p.getCreator());
        shareInfo.setUpdaterId(p.getCreatorId());
        shareInfo.setUpdateTime(new Date());
        return shareInfo;
    }

    private void handleResourceIdAndName(ImportResourceResult result, ShareInfo shareInfo, ImportInfo p) {
        if (StringUtils.isEmpty(result.getNewId())) {
            return;
        }
        shareInfo.setResourceId(result.getNewId());
        shareInfo.setResourceName(StringUtils.isNotEmpty(result.getNewName()) ? result.getNewName() : result.getName());
        shareInfo.getShareScopeEntityList().forEach(sp -> {
            sp.setResourceId(result.getNewId());
            sp.setProjectId(p.getTargetProjectId());
        });
    }

    private void handleVersionInfo(ImportResourceResult result, ShareInfo shareInfo) {
        if (StringUtils.isNotEmpty(result.getNewVersion())) {
            List<ResourceVersionInfo> versionInfos = JsonUtils.json2Array(shareInfo.getVersionList(),
                ResourceVersionInfo.class);
            ResourceVersionInfo versionInfo = new ResourceVersionInfo();
            versionInfo.setVersionId(result.getNewVersion());
            ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(shareInfo.getResourceId(),
                result.getNewVersion());
            if (releaseVersion != null) {
                versionInfo.setVersionName(releaseVersion.getVersionName());
            }
            versionInfos.add(versionInfo);
            shareInfo.setVersionList(JSONObject.toJSONString(versionInfos));
        }
    }

    private void handleProviderModel(List<ImportInfo> resourceList, List<ImportResourceResult> resultList) {
        if (CollectionUtils.isEmpty(resourceList) || CollectionUtils.isEmpty(resultList)) {
            return;
        }
        // 将 resultList 转换为 Map 以提高查找效率
        Map<String, ImportResourceResult> resultMap = resultList.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, result -> result, (existing, incoming) -> existing));
        resourceList.stream()
            .filter(v -> Strings.CS.equals(v.getResourceType(), ResourceTypeEnum.MODEL.toString()))
            .forEach(p -> {
                ModelServiceData model = JsonUtils.objectToClassType(p.getMetadata(), ModelServiceData.class);
                ImportResourceResult modelResult = resultMap.get(model.getId());
                if (modelResult == null || Strings.CS.equals(modelResult.getStatus(),
                    ImportExportStatusEnum.FAILED.getCode())) {
                    return;
                }
                ImportResourceResult providerResult = resultMap.get(model.getProviderId());
                if (providerResult == null || Strings.CS.equals(providerResult.getStatus(),
                    ImportExportStatusEnum.FAILED.getCode()) || StringUtils.isEmpty(providerResult.getNewId())) {
                    return;
                }
                String modelId = StringUtils.isNotEmpty(modelResult.getNewId())
                    ? modelResult.getNewId()
                    : modelResult.getId();

                List<ProviderAuthMetadata> metaDatas = providerAuthMetadataMapper.selectByProvider(
                    providerResult.getNewId());
                ProviderAuthMetadata metaData = metaDatas.stream().findFirst().orElse(null);
                String authMetadataId = metaData == null ? null : metaData.getId();
                // 更新模型所属的供应商id
                modelServiceMapper.updateModelProvider(modelId, providerResult.getNewId(), authMetadataId);
                ModelServiceBase modelBase = modelServiceMapper.queryById(modelId);
                modelServiceManager.saveModelInfoToObsAndRedis("model", modelId, modelBase);
            });
    }

    private void handleStrategyModel(List<ImportInfo> resourceList, List<ImportResourceResult> resultList) {
        if (CollectionUtils.isEmpty(resourceList) || CollectionUtils.isEmpty(resultList)) {
            return;
        }
        // 将 resultList 转换为 Map 以提高查找效率
        Map<String, ImportResourceResult> resultMap = resultList.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, result -> result, (existing, incoming) -> existing));
        resourceList.stream()
            .filter(v -> Strings.CS.equals(v.getResourceType(), ResourceTypeEnum.STRATEGY.toString()))
            .forEach(p -> {
                RouterStrategyEntity routerStrategy = JsonUtils.objectToClassType(p.getMetadata(),
                    RouterStrategyEntity.class);
                ImportResourceResult strategyResult = resultMap.get(routerStrategy.getId());
                if (strategyResult == null || Strings.CS.equals(strategyResult.getStatus(),
                    ImportExportStatusEnum.FAILED.getCode())) {
                    return;
                }
                if (StringUtils.isBlank(routerStrategy.getServiceIdList())) {
                    return;
                }
                String[] modelIds = StringUtils.split(routerStrategy.getServiceIdList(), ",");
                List<String> newModelIds = new ArrayList<>();
                Arrays.stream(modelIds).forEach(id -> {
                    ImportResourceResult modelResult = resultMap.get(id);
                    if (modelResult == null || Strings.CS.equals(modelResult.getStatus(),
                        ImportExportStatusEnum.FAILED.getCode())) {
                        return;
                    }
                    newModelIds.add(
                        StringUtils.isEmpty(modelResult.getNewId()) ? modelResult.getId() : modelResult.getNewId());
                });
                RouterStrategyEntity rsEntity = new RouterStrategyEntity();
                rsEntity.setId(StringUtils.isEmpty(strategyResult.getNewId())
                    ? strategyResult.getId()
                    : strategyResult.getNewId());
                rsEntity.setServiceIdList(String.join(",", newModelIds));
                routerStrategyMapper.update(rsEntity);
                RouterStrategyEntity strategy = routerStrategyMapper.selectInfoById(rsEntity.getId());
                modelServiceManager.saveModelInfoToObsAndRedis("router", strategy.getId(), strategy);
            });
    }

    private void handleMapping(List<ImportInfo> resourceList, List<ImportResourceResult> resultList) {
        if (CollectionUtils.isEmpty(resourceList) || CollectionUtils.isEmpty(resultList)) {
            return;
        }
        // 将 resultList 转换为 Map 以提高查找效率
        Map<String, ImportResourceResult> resultMap = resultList.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, result -> result, (existing, incoming) -> existing));
        List<MappingEntity> mappingList = new ArrayList<>();
        resourceList.stream().filter(v -> CollectionUtils.isNotEmpty(v.getParents())).forEach(p -> {
            ImportResourceResult result = resultMap.get(p.getResourceId());
            if (result == null || Strings.CS.equals(result.getStatus(), ImportExportStatusEnum.FAILED.getCode())) {
                return;
            }
            MappingEntity currentMapping = createMappingEntity(p, result);

            // 处理父资源
            handleParentMappings(p, resultMap, mappingList, currentMapping);
        });

        if (CollectionUtils.isNotEmpty(mappingList)) {
            // 分组并删除旧数据
            groupedDelete(mappingList);
            // 批量插入新数据
            mappingMapper.insertBatch(mappingList);
        }
    }

    private MappingEntity createMappingEntity(ImportInfo p, ImportResourceResult result) {
        if (result == null || ImportExportStatusEnum.FAILED.getCode().equals(result.getStatus())) {
            return null;
        }
        MappingEntity mappingEntity = new MappingEntity();
        mappingEntity.setResourceId(StringUtils.isNotEmpty(result.getNewId()) ? result.getNewId() : p.getResourceId());
        mappingEntity.setResourceName(
            StringUtils.isNotEmpty(result.getNewName()) ? result.getNewName() : p.getResourceName());
        mappingEntity.setResourceType(p.getResourceType());
        mappingEntity.setResourceVersion(
            StringUtils.isNotEmpty(result.getNewVersion()) ? result.getNewVersion() : result.getVersion());
        mappingEntity.setResourceDesc(result.getDescription());
        mappingEntity.setResourceWorkspaceId(p.getTargetWorkspaceId());
        mappingEntity.setValid(result.isValid());
        mappingEntity.setCreatedOn(new Date());
        return mappingEntity;
    }

    private void handleParentMappings(ImportInfo importInfo, Map<String, ImportResourceResult> resultMap,
        List<MappingEntity> mappingList, MappingEntity currentMapping) {
        Set<String> uniqueSet = new HashSet<>(importInfo.getParents());
        uniqueSet.forEach(parentId -> {
            ImportResourceResult parentResult = resultMap.get(parentId);
            if (parentResult != null && !ImportExportStatusEnum.FAILED.getCode().equals(parentResult.getStatus())) {
                if (ResourceTypeEnum.TOOL.toString().equals(importInfo.getResourceType())) {
                    handlePluginSituation(importInfo, mappingList, currentMapping, parentResult);
                } else {
                    MappingEntity parentMapping = getMappingEntity(currentMapping, parentResult,
                        importInfo.getTargetWorkspaceId());
                    mappingList.add(parentMapping);

                    // 发布态导入时 parentMapping.appVersion 非空，需额外插入一份 app_version=null 的草稿态 mapping
                    // 确保 buildComplexAgentInfo 的 selectByAppIdAndResourceType（and app_version is null）能查到
                    // 草稿态导入时 parentMapping.appVersion 已为 null，无需重复插入
                    if (StringUtils.isNotEmpty(parentMapping.getAppVersion())) {
                        MappingEntity draftMapping = new MappingEntity();
                        BeanUtils.copyProperties(parentMapping, draftMapping);
                        draftMapping.setMappingId(UUID.randomUUID().toString());
                        draftMapping.setAppVersion(null);
                        mappingList.add(draftMapping);
                    }
                }
            }
        });
    }

    private static void handlePluginSituation(ImportInfo importInfo, List<MappingEntity> mappingList,
        MappingEntity currentMapping, ImportResourceResult parentResult) {
        PluginVO pluginVO = JsonUtils.objectToClassType(importInfo.getMetadata(), PluginVO.class);
        for (String toolId : Objects.requireNonNull(pluginVO).getToolIds()) {
            MappingEntity parentMapping = getMappingEntity(currentMapping, parentResult,
                importInfo.getTargetWorkspaceId());
            parentMapping.setResourceId(parentMapping.getResourceId() + "#" + toolId);
            mappingList.add(parentMapping);

            // 发布态导入时 parentMapping.appVersion 非空，需额外插入草稿态 mapping
            // 草稿态导入时 parentMapping.appVersion 已为 null，无需重复插入
            if (StringUtils.isNotEmpty(parentMapping.getAppVersion())) {
                MappingEntity draftMapping = new MappingEntity();
                BeanUtils.copyProperties(parentMapping, draftMapping);
                draftMapping.setMappingId(UUID.randomUUID().toString());
                draftMapping.setAppVersion(null);
                mappingList.add(draftMapping);
            }
        }
    }

    private static @NotNull MappingEntity getMappingEntity(MappingEntity currentMapping,
        ImportResourceResult parentResult, String targetWorkspaceId) {
        MappingEntity parentMapping = new MappingEntity();
        BeanUtils.copyProperties(currentMapping, parentMapping);
        parentMapping.setMappingId(UUID.randomUUID().toString());
        parentMapping.setAppId(
            StringUtils.isNotEmpty(parentResult.getNewId()) ? parentResult.getNewId() : parentResult.getId());
        parentMapping.setAppName(
            StringUtils.isNotEmpty(parentResult.getNewName()) ? parentResult.getNewName() : parentResult.getName());
        parentMapping.setAppType(parentResult.getType());
        parentMapping.setAppVersion(StringUtils.isNotEmpty(parentResult.getNewVersion())
            ? parentResult.getNewVersion()
            : parentResult.getVersion());
        parentMapping.setAppWorkspaceId(targetWorkspaceId);
        return parentMapping;
    }

    private void groupedDelete(List<MappingEntity> mappingList) {
        if (CollectionUtils.isEmpty(mappingList)) {
            return;
        }
        Map<String, List<MappingEntity>> groupedMapping = mappingList.stream()
            .collect(Collectors.groupingBy(MappingEntity::getAppId));

        groupedMapping.forEach((appId, entities) -> {
            List<String> resourceIds = entities.stream()
                .map(MappingEntity::getResourceId)
                .distinct()
                .collect(Collectors.toList());
            mappingMapper.deleteBatch(appId, resourceIds);
        });
    }

    private List<MappingEntity> buildDraftMappings(List<MappingEntity> mappingList) {
        List<MappingEntity> draftMappings = new ArrayList<>();
        for (MappingEntity mapping : mappingList) {
            if (StringUtils.isNotEmpty(mapping.getAppVersion())) {
                boolean hasDraft = mappingList.stream()
                    .anyMatch(m -> m.getAppId().equals(mapping.getAppId())
                        && m.getResourceId().equals(mapping.getResourceId())
                        && StringUtils.isEmpty(m.getAppVersion()));
                if (!hasDraft) {
                    MappingEntity draftMapping = new MappingEntity();
                    BeanUtils.copyProperties(mapping, draftMapping);
                    draftMapping.setMappingId(UUID.randomUUID().toString());
                    draftMapping.setAppVersion(null);
                    draftMappings.add(draftMapping);
                }
            }
        }
        return draftMappings;
    }

    private void handleResourceDsl(List<ImportInfo> resourceList, List<ImportResourceResult> resultList) {
        if (CollectionUtils.isEmpty(resourceList) || CollectionUtils.isEmpty(resultList)) {
            return;
        }
        // 将 resultList 转换为 Map 以提高查找效率
        Map<String, ImportResourceResult> resultMap = resultList.stream()
            .collect(Collectors.toMap(ImportResourceResult::getId, result -> result, (existing, incoming) -> existing));
        Map<String, ImportInfo> resourceMap = resourceList.stream()
            .collect(Collectors.toMap(ImportInfo::getResourceId, result -> result, (existing, incoming) -> existing));
        // 按 resourceId+versionId 联合构建版本映射，解决同 resourceId 多版本去重问题：
        // resourceMap 按 resourceId 去重后只剩1个 ImportInfo，导致多版本上传 DSL 时取到同一份。
        // versionedResourceMap 按 resourceId+versionId 区分，确保每个版本用各自的 ImportInfo。
        // 无版本资源（model/tool/mcp 等）versionId 为空串，仍可正确匹配。
        Map<String, ImportInfo> versionedResourceMap = resourceList.stream()
            .collect(Collectors.toMap(
                p -> p.getResourceId() + "|" + (p.getReleaseVersion() != null
                    ? p.getReleaseVersion().getVersionId() : ""),
                result -> result, (existing, incoming) -> existing));
        // 按 resourceId 分组所有版本 ImportInfo，用于子资源引用更新时遍历同 resourceId 的所有版本
        // （resourceMap 去重后只剩1个，会导致同 resourceId 多版本只有1个的 dsl 引用被更新）
        Map<String, List<ImportInfo>> resourceListMap = resourceList.stream()
            .collect(Collectors.groupingBy(ImportInfo::getResourceId));

        // 构建完整 ID 映射：resource_id 和 metadata.trace_id 都映射到 newId
        // 解决导出包 DSL 里 configs.id 是上次导入生成的旧 ID（= trace_id）而非原始 resource_id 的问题
        Map<String, String> allIdMappings = new HashMap<>();
        for (ImportResourceResult result : resultList) {
            String newId = StringUtils.isNotEmpty(result.getNewId()) ? result.getNewId() : result.getId();
            allIdMappings.put(result.getId(), newId);
            ImportInfo info = resourceMap.get(result.getId());
            if (info != null && info.getMetadata() != null) {
                try {
                    WorkflowEntity workflowMeta = JsonUtils.objectToClassType(info.getMetadata(), WorkflowEntity.class);
                    if (StringUtils.isNotEmpty(workflowMeta.getTraceId())
                        && !Strings.CS.equals(workflowMeta.getTraceId(), result.getId())) {
                        allIdMappings.put(workflowMeta.getTraceId(), newId);
                    }
                } catch (Exception ignored) {
                }
            }
        }
        resourceList.stream().filter(v -> CollectionUtils.isNotEmpty(v.getParents())).forEach(p -> {
            ImportResourceResult result = resultMap.get(p.getResourceId());
            
            if (result == null) {
                
                return;
            }
            if (Strings.CS.equals(result.getStatus(), ImportExportStatusEnum.FAILED.getCode())) {
                
                return;
            }
            
            // 若当前资源id与版本无变化，则无需更新父资源的dsl
            if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewVersion())) {
                
                return;
            }
            p.getParents().forEach(parentId -> {
                ImportResourceResult parentResult = resultMap.get(parentId);
                if (parentResult == null) {
                    return;
                }
                if (Strings.CS.equals(parentResult.getStatus(), ImportExportStatusEnum.FAILED.getCode())) {
                    return;
                }
                // 遍历该 parentId 的所有版本 ImportInfo（同 resourceId 多版本），对每个版本都更新子资源引用。
                // resourceMap 去重后只剩1个，会导致多版本只有1个版本的 dsl 引用被更新。
                List<ImportInfo> parentResources = resourceListMap.getOrDefault(parentId,
                    Collections.singletonList(resourceMap.get(parentId)));
                parentResources.forEach(parentResource -> {
                    if (parentResource == null) {
                        return;
                    }
                    switch (ResourceTypeEnum.fromValue(parentResource.getResourceType())) {
                        case WORKFLOW -> handleWorkflowDsl(parentResource, parentResult, result);
                        case AGENT -> handleAgentDsl(parentResource, parentResult, result);
                        case CONTROLLER -> {
                            handleControllerDsl(parentResource, parentResult, result, allIdMappings);
                            if (CollectionUtils.isNotEmpty(parentResource.getParents())) {
                                parentResource.getParents().forEach(grandParentId -> {
                                    ImportInfo grandParentResource = resourceMap.get(grandParentId);
                                    ImportResourceResult grandParentResult = resultMap.get(grandParentId);
                                    if (grandParentResult == null || Strings.CS.equals(grandParentResult.getStatus(),
                                        ImportExportStatusEnum.FAILED.getCode())) {
                                        return;
                                    }
                                    handleGrandControllerDsl(grandParentResource, grandParentResult, result);
                            });
                        }
                    }
                }
                });
            });
        });

        resultList.forEach(result -> {
            String id = StringUtils.isNotEmpty(result.getNewId()) ? result.getNewId() : result.getId();
            String versionId = StringUtils.isNotEmpty(result.getNewVersion())
                ? result.getNewVersion()
                : result.getVersion();
            String objectKey = id;
            if (StringUtils.isNotEmpty(versionId)) {
                objectKey = id + Constants.UNDERLINE_STR + versionId;
            }
            switch (ResourceTypeEnum.fromValue(result.getType())) {
                case WORKFLOW -> {
                    // 草稿 DSL 上传：仅首次导入（addTag=true，资源新建）或草稿态导入（versionId 空）时上传。
                    // 已发布版本导入到已有资源（addTag=false 且 versionId 非空）时跳过，避免覆盖用户草稿。
                    if (Boolean.TRUE.equals(result.getAddTag()) || StringUtils.isEmpty(versionId)) {
                        uploadWorkflowDsl(resourceMap.get(result.getId()), id, id, null);
                    }
                    if (StringUtils.isNotEmpty(versionId)) {
                        // 版本 DSL 用按版本区分的 ImportInfo，避免同 resourceId 多版本取到同一份
                        ImportInfo versionedInfo = versionedResourceMap.get(result.getId() + "|" + result.getVersion());
                        uploadWorkflowDsl(
                            versionedInfo != null ? versionedInfo : resourceMap.get(result.getId()), id, objectKey,
                            versionId);
                    }
                }
                case AGENT -> {
                    // 草稿 DSL 上传：与 workflow/controller 一致，仅首次导入或草稿态导入时上传。
                    // agent 通用模式草稿走 buildComplexAgentInfo 从 DB 重建（不读 OBS 草稿文件），
                    // 但为一致性与防御（避免 OBS 草稿文件被版本快照覆盖），同样加 addTag 守卫。
                    if (Boolean.TRUE.equals(result.getAddTag()) || StringUtils.isEmpty(versionId)) {
                        uploadAgentDsl(resourceMap.get(result.getId()), id, id);
                    }
                    if (StringUtils.isNotEmpty(versionId)) {
                        ImportInfo versionedInfo = versionedResourceMap.get(result.getId() + "|" + result.getVersion());
                        uploadAgentDsl(
                            versionedInfo != null ? versionedInfo : resourceMap.get(result.getId()), id, objectKey);
                    }
                }
                case CONTROLLER -> {
                    if (StringUtils.isNotEmpty(versionId)) {
                        ImportInfo versionedInfo = versionedResourceMap.get(result.getId() + "|" + result.getVersion());
                        uploadControllerDsl(
                            versionedInfo != null ? versionedInfo : resourceMap.get(result.getId()), id, versionId);
                    }
                    // 草稿 DSL 上传：仅首次导入或草稿态导入时上传，避免已发布版本导入覆盖用户草稿。
                    if (Boolean.TRUE.equals(result.getAddTag()) || StringUtils.isEmpty(versionId)) {
                        uploadControllerDsl(resourceMap.get(result.getId()), id, null);
                    }
                }
            }
        });

        // 宽松模式先导入父资源（controller/workflow）时，子工作流尚不存在，mapping 写的是子工作流
        // 的旧 resource_id（=trace_id）且 valid=false。后续严格模式导入子工作流后，需要把这些 mapping 的
        // resource_id 更新为新 ID 并置 valid=true，否则 retrieveAgent 查不到子工作流关联（"工作流不存在"）。
        // 严格模式自身 handleMapping 已用新 ID 插入 mapping，selectByResourceId(旧ID) 查不到记录，不受影响。
        resultList.forEach(result -> {
            if (!Boolean.TRUE.equals(result.getAddTag()) || StringUtils.isEmpty(result.getNewId())
                || Strings.CS.equals(result.getNewId(), result.getId())) {
                return;
            }
            if (!Strings.CS.equalsAny(result.getType(), ResourceTypeEnum.WORKFLOW.toString(),
                ResourceTypeEnum.CONTROLLER.toString())) {
                return;
            }
            List<MappingEntity> staleMappings = mappingMapper.selectByResourceId(result.getId());
            if (CollectionUtils.isEmpty(staleMappings)) {
                return;
            }
            for (MappingEntity mapping : staleMappings) {
                if (mapping.isValid()) {
                    continue;
                }
                MappingEntity update = new MappingEntity();
                update.setMappingId(mapping.getMappingId());
                update.setResourceId(result.getNewId());
                update.setResourceName(
                    StringUtils.isNotEmpty(result.getNewName()) ? result.getNewName() : result.getName());
                update.setValid(true);
                mappingMapper.updateById(update);
            }
        });
    }

    private void uploadWorkflowDsl(ImportInfo importInfo, String id, String objectKey, String versionId) {
        try {
            WorkflowVO workflowVO = JsonUtils.objectToClassType(importInfo.getDsl(), WorkflowVO.class);
            workflowVO.setId(id);
            verifyingAndReplaceWorkflowResourceInfo(workflowVO);
            mgObsService.uploadObsFile(id, objectKey, CommonConstant.WORKFLOW,
                JSON.toJSONString(workflowVO, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.FLOW);
            WorkflowEntity workflowEntity = workflowMapper.getWorkflowById(id);
            workflowCommonService.workflowDslToIr(id, workflowEntity, workflowVO, versionId);
        } catch (Exception e) {
            log.error("handleWorkflowDsl error.", e);
        }
    }

    public void uploadAgentDsl(ImportInfo importInfo, String id, String objectKey) {
        try {
            Agent agent = agentMapper.selectById(id);
            AgentInfo agentInfo = null;
            String agentSubType = Optional.ofNullable(agent.getSubType()).orElse(COMMON_AGENT_TYPE);
            switch (agentSubType) {
                // 通用模式
                case (CommonConstant.COMMON_AGENT_TYPE) -> {
                    agent.setDslPath(null);
                    agentInfo = agentCommonService.buildComplexAgentInfo(agent);
                    // 用导入包版本快照（importInfo.getDsl()）覆盖用户配置类字段，恢复版本特有内容。
                    // buildComplexAgentInfo 从 DB agent 表重建，agent 表只有草稿态一份，
                    // 导致所有版本的用户配置类字段（instructions/prologue/suggestQueries 等）都被草稿态覆盖，版本差异丢失。
                    // ID 类、关联资源类（tools/mcp/skills/knowledge/workflows）保留 DB 重建值（目标空间新 ID/新关联）。
                    AgentInfo versionedInfo = JsonUtils.objectToClassType(importInfo.getDsl(), AgentInfo.class);
                    if (versionedInfo != null) {
                        agentInfo.setName(versionedInfo.getName());
                        agentInfo.setDescription(versionedInfo.getDescription());
                        agentInfo.setIcon(versionedInfo.getIcon());
                        agentInfo.setInstructions(versionedInfo.getInstructions());
                        agentInfo.setPrologue(versionedInfo.getPrologue());
                        agentInfo.setSuggestQueries(versionedInfo.getSuggestQueries());
                        agentInfo.setAdditionalQuestionsConfig(versionedInfo.getAdditionalQuestionsConfig());
                        agentInfo.setTriggerList(versionedInfo.getTriggerList());
                        agentInfo.setMemoryVariables(versionedInfo.getMemoryVariables());
                        agentInfo.setMemoryConfig(versionedInfo.getMemoryConfig());
                        agentInfo.setAgentVariables(versionedInfo.getAgentVariables());
                        agentInfo.setInputVariables(versionedInfo.getInputVariables());
                        agentInfo.setKnowledgeRetrievePolicy(versionedInfo.getKnowledgeRetrievePolicy());
                        agentInfo.setWorkflowSwitchEnabled(versionedInfo.isWorkflowSwitchEnabled());
                        agentInfo.setSchedulingMode(versionedInfo.getSchedulingMode());
                        agentInfo.setVoiceInteraction(versionedInfo.getVoiceInteraction());
                        agentInfo.setSafetyBarrier(versionedInfo.isSafetyBarrier());
                        agentInfo.setContentReview(versionedInfo.getContentReview());
                        // 模型为版本特有（不同版本可能用不同 model），modelDeploymentId 已由 handleAgentDsl 更新为新 ID
                        agentInfo.setModelDeploymentId(versionedInfo.getModelDeploymentId());
                        agentInfo.setModelName(versionedInfo.getModelName());
                        agentInfo.setModelType(versionedInfo.getModelType());
                        agentInfo.setModel(versionedInfo.getModel());
                        agentInfo.setModelConfig(versionedInfo.getModelConfig());
                    }
                }
                // 规划模式
                case (CommonConstant.PLANEXECUTE_TYPE) -> {
                    agentInfo = JsonUtils.objectToClassType(importInfo.getDsl(), AgentInfo.class);
                }
                // 深度研究模式
                case (CommonConstant.DEEPRESEARCH_TYPE) -> {
                    agentInfo = JsonUtils.objectToClassType(importInfo.getDsl(), AgentInfo.class);
                }
                default -> {
                    log.error("Unsupported agent sub type: {}", agent.getSubType());
                    throw new IllegalArgumentException("Unsupported agent sub type");
                }
            }
            agentInfo.setAgentId(id);
            String jsonContent = JsonUtils.serializeWithFallback(agentInfo, log,
                "AgentInfo for obs upload, agentId: " + agent.getAgentId());
            mgObsService.uploadObsFile(agent.getAgentId(), objectKey, CommonConstant.AGENT, jsonContent,
                CommonConstant.DSL_STR);
            // 上传dsl后，再处理元数据和IR信息
            Map<String, Object> agentMetadata = agentCommonService.parseMetadata(agent);
            Map<String, Object> irInfo = CommonConstant.DEEPRESEARCH_TYPE.equals(agent.getSubType())
                ? irAdapterService.adaptAgentDeepResearch(agentInfo, agentMetadata)
                : irAdapterService.adaptAgent(agent, agentMetadata);
            // 上传IR
            mgObsService.uploadObsFile(agent.getAgentId(), objectKey, CommonConstant.AGENT, JSON.toJSONString(irInfo),
                CommonConstant.Workflow.IR);
        } catch (Exception e) {
            log.error("uploadAgentDsl error.", e);
        }
    }

    public void uploadControllerDsl(ImportInfo importInfo, String id, String versionId) {
        try {
            Agent agent = agentMapper.selectById(id);
            verifyingAndReplaceControllerResourceInfo(importInfo.getDsl());
            if (StringUtils.isNotEmpty(versionId)) {
                agentCommonService.uploadToObsWithVersion(agent, importInfo.getDsl(), CommonConstant.Workflow.FLOW,
                    versionId);
            } else {
                agentCommonService.uploadToObs(agent, importInfo.getDsl(), CommonConstant.Workflow.FLOW);
            }
            ControllerVO controllerVO = JsonUtils.objectToClassType(importInfo.getDsl(), ControllerVO.class);
            Map<String, Map<String, ControllerNodeVO>> nodesGroupByTypeId = controllerManagementService.groupDslNodes(
                controllerVO);
            ControllerIR ir = controllerManagementService.dslToIr(controllerVO, nodesGroupByTypeId);
            // 上传IR文件
            if (StringUtils.isNotEmpty(versionId)) {
                agentCommonService.uploadToObsNoNullWithVersion(agent, ir, CommonConstant.Workflow.IR, versionId);
            } else {
                agentCommonService.uploadToObsNoNull(agent, ir, CommonConstant.Workflow.IR);
            }
        } catch (Exception e) {
            log.error("uploadControllerDsl error.", e);
        }
    }

    /**
     * 工作流导入时做资源越权校验
     *
     * @param workflowVO
     */
    @SuppressWarnings("unchecked")
    private void verifyingAndReplaceWorkflowResourceInfo(WorkflowVO workflowVO) {
        if (workflowVO == null) {
            return;
        }
        Object memoryConfigs = workflowVO.getConfigs().get(Constants.MEMORY_CONFIG);
        if (memoryConfigs instanceof Map) {
            // 如果memoryConfig已经是Map类型，直接使用
            Map<String, Object> configs = (Map<String, Object>) memoryConfigs;
            MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectByIdAndWorkspaceId(
                configs.get(CommonConstant.MEMORY_REPO_ID).toString(), RequestContextUtils.getRequestWorkspaceId());
            if (Objects.isNull(memoryRepoEntity)) {
                // 记忆库不存在，则清空dsl中的记忆库配置
                configs.clear();
                configs.put(CommonConstant.MEMORY_REPO_ID, "");
            }
        }
    }

    /**
     * 多智能体导入时做资源越权校验
     *
     * @param dsl
     */
    @SuppressWarnings("unchecked")
    private void verifyingAndReplaceControllerResourceInfo(Object dsl) {
        if (dsl == null) {
            return;
        }
        if (dsl instanceof ControllerVO controllerVO) {
            AgentMemoryConfig memoryConfig = controllerVO.getMemoryConfig();
            if (Objects.nonNull(memoryConfig)) {
                MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectByIdAndWorkspaceId(
                    memoryConfig.getMemoryRepoId(), RequestContextUtils.getRequestWorkspaceId());
                if (Objects.isNull(memoryRepoEntity)) {
                    // 记忆库不存在，则清空dsl中的记忆库配置
                    controllerVO.setMemoryConfig(null);
                }
            }
        } else if (dsl instanceof Map) {
            Map<String, Object> dslMap = (Map<String, Object>) dsl;
            Object memoryConfigs = dslMap.get(Constants.MEMORY_CONFIG);
            if (memoryConfigs instanceof Map) {
                // 如果memoryConfig已经是Map类型，直接使用
                Map<String, Object> configs = (Map<String, Object>) memoryConfigs;
                MemoryRepoEntity memoryRepoEntity = memoryRepoMapper.selectByIdAndWorkspaceId(
                    configs.get(CommonConstant.MEMORY_REPO_ID).toString(), RequestContextUtils.getRequestWorkspaceId());
                if (Objects.isNull(memoryRepoEntity)) {
                    // 记忆库不存在，则清空dsl中的记忆库配置
                    configs.clear();
                    configs.put(CommonConstant.MEMORY_REPO_ID, "");
                }
            }
        }
    }

    private void handleControllerDsl(ImportInfo parentResource, ImportResourceResult parentResult,
        ImportResourceResult result, Map<String, String> allIdMappings) {
        ControllerVO controllerVO = JsonUtils.objectToClassType(parentResource.getDsl(), ControllerVO.class);
        controllerVO.setProjectId(parentResource.getTargetProjectId());
        controllerVO.setWorkspaceId(parentResource.getTargetWorkspaceId());
        if (StringUtils.isNotBlank(parentResult.getNewId())) {
            controllerVO.setId(parentResult.getNewId());
        }
        if (StringUtils.isNotBlank(parentResult.getNewName())) {
            controllerVO.setName(parentResult.getNewName());
        }
        switch (ResourceTypeEnum.fromValue(result.getType())) {
            case WORKFLOW -> handleControllerWorkflow(result, controllerVO, allIdMappings);
            case CONTROLLER -> handleSubController(result, controllerVO);
            case MODEL -> handleControllerModel(result, controllerVO);
            case AGENT -> handleControllerAgent(result, controllerVO);
        }
        parentResource.setDsl(controllerVO);
    }

    private void handleGrandControllerDsl(ImportInfo grandParentResource, ImportResourceResult grandParentResult,
        ImportResourceResult result) {
        ControllerVO controllerVO = JsonUtils.objectToClassType(grandParentResource.getDsl(), ControllerVO.class);
        controllerVO.setProjectId(grandParentResource.getTargetProjectId());
        if (StringUtils.isNotBlank(grandParentResult.getNewId())) {
            controllerVO.setId(grandParentResult.getNewId());
        }
        if (StringUtils.isNotBlank(grandParentResult.getNewName())) {
            controllerVO.setName(grandParentResult.getNewName());
        }
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        switch (ResourceTypeEnum.fromValue(result.getType())) {
            case WORKFLOW -> handleGrandControllerWorkflow(result, controllerVO);
            case MODEL -> handleGrandControllerModel(result, controllerVO);
        }
        grandParentResource.setDsl(controllerVO);
    }

    private void handleControllerWorkflow(ImportResourceResult result, ControllerVO controllerVO,
        Map<String, String> allIdMappings) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        controllerVO.getNodes().stream().forEach(node -> {
            if (Strings.CS.equals(node.getType(), AgentNodeType.WORKFLOW.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                String configId = configs.get("id") != null ? configs.get("id").toString() : "";
                boolean match = Strings.CS.equals(configId, result.getId());
                // 如果 configId 不匹配 result.id，检查 allIdMappings（可能是上次导入生成的旧 ID = trace_id）
                if (!match && allIdMappings.containsKey(configId)) {
                    String mappedNewId = allIdMappings.get(configId);
                    // 用 allIdMappings 里的 newId 替换（不是当前 result 的 newId）
                    configs.put("id", mappedNewId);
                    node.setConfigs(configs);
                    return;
                }
                handleVersionResource(result, configs);
                node.setConfigs(configs);
            }
            if (Strings.CS.equals(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                List<Map<String, Object>> workflows = MapReadUtil.safeCastToListWithMap(configs.get("workflows"));
                workflows.forEach(workflowMap -> {
                    if (!Strings.CS.equals((String) workflowMap.get("id"), result.getId())) {
                        return;
                    }
                    if (StringUtils.isNotEmpty(result.getNewId())) {
                        workflowMap.put("id", result.getNewId());
                    }
                    Map<String, Object> workflowConfigs = MapReadUtil.safeCastToMapWithStringKey(
                        workflowMap.get("configs"));
                    handleVersionResource(result, workflowConfigs);
                    workflowMap.put("configs", workflowConfigs);
                });
                configs.put("workflows", workflows);
                node.setConfigs(configs);
            }
        });
    }

    private void handleSubController(ImportResourceResult result, ControllerVO controllerVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        controllerVO.getNodes().stream().forEach(node -> {
            if (Strings.CS.equals(node.getType(), AgentNodeType.SUB_CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                handleVersionResource(result, configs);
                node.setConfigs(configs);
            }
            if (Strings.CS.equals(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                List<Map<String, Object>> agents = MapReadUtil.safeCastToListWithMap(configs.get("agents"));
                agents.forEach(agentMap -> {
                    if (!Strings.CS.equals((String) agentMap.get("id"), result.getId())) {
                        return;
                    }
                    if (StringUtils.isNotEmpty(result.getNewId())) {
                        agentMap.put("id", result.getNewId());
                    }
                    Map<String, Object> agentConfigs = MapReadUtil.safeCastToMapWithStringKey(agentMap.get("configs"));
                    handleVersionResource(result, agentConfigs);
                    agentMap.put("configs", agentConfigs);
                });
                configs.put("agents", agents);
                node.setConfigs(configs);
            }
        });
    }

    private void handleGrandControllerWorkflow(ImportResourceResult result, ControllerVO controllerVO) {
        controllerVO.getNodes().stream().forEach(node -> {
            if (Strings.CS.equals(node.getType(), AgentNodeType.WORKFLOW.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                handleVersionResource(result, configs);
                node.setConfigs(configs);
            }
            if (Strings.CS.equals(node.getType(), AgentNodeType.SUB_CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                List<Map<String, Object>> workflows = MapReadUtil.safeCastToListWithMap(configs.get("workflows"));
                if (putSubWorfklowConfig(result, workflows)) {
                    return;
                }
                configs.put("workflows", workflows);
                node.setConfigs(configs);
            }
            if (Strings.CS.equals(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                List<Map<String, Object>> agents = MapReadUtil.safeCastToListWithMap(configs.get("agents"));
                if (CollectionUtils.isEmpty(agents)) {
                    return;
                }
                agents.forEach(agentMap -> {
                    Map<String, Object> agentConfigs = MapReadUtil.safeCastToMapWithStringKey(agentMap.get("configs"));
                    List<Map<String, Object>> workflows = MapReadUtil.safeCastToListWithMap(
                        agentConfigs.get("workflows"));
                    if (putSubWorfklowConfig(result, workflows)) {
                        return;
                    }
                    agentConfigs.put("workflows", workflows);
                    agentMap.put("configs", agentConfigs);
                });
                configs.put("agents", agents);
                node.setConfigs(configs);
            }
        });
    }

    private boolean putSubWorfklowConfig(ImportResourceResult result, List<Map<String, Object>> workflows) {
        if (CollectionUtils.isEmpty(workflows)) {
            return true;
        }
        workflows.forEach(workflowMap -> {
            if (!Strings.CS.equals((String) workflowMap.get("id"), result.getId())) {
                return;
            }
            if (StringUtils.isNotEmpty(result.getNewId())) {
                workflowMap.put("id", result.getNewId());
            }
            Map<String, Object> workflowConfigs = MapReadUtil.safeCastToMapWithStringKey(workflowMap.get("configs"));
            handleVersionResource(result, workflowConfigs);
            workflowMap.put("configs", workflowConfigs);
        });
        return false;
    }

    private void handleControllerModel(ImportResourceResult result, ControllerVO controllerVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        controllerVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), AgentNodeType.CONTROLLER.getType()))
            .forEach(node -> {
                Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                Map<String, Object> model = MapReadUtil.safeCastToMapWithStringKey(configs.get("model"));
                updateModelIfMatch(result, model);
                configs.put("model", model);
                node.setConfigs(configs);
            });
    }

    private void handleGrandControllerModel(ImportResourceResult result, ControllerVO controllerVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        controllerVO.getNodes().stream().forEach(node -> {
            if (Strings.CS.equalsAny(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                handleControllerNode(result, node);
            } else if (Strings.CS.equalsAny(node.getType(), AgentNodeType.AGENT.getType(),
                AgentNodeType.SUB_CONTROLLER.getType())) {
                handleAgentOrSubControllerNode(result, node);
            }
        });
    }

    private void handleControllerNode(ImportResourceResult result, ControllerNodeVO node) {
        Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
        List<Map<String, Object>> agents = MapReadUtil.safeCastToListWithMap(configs.get("agents"));
        if (CollectionUtils.isEmpty(agents)) {
            return;
        }
        agents.forEach(agent -> {
            Map<String, Object> agentConfig = MapReadUtil.safeCastToMapWithStringKey(agent.get("configs"));
            Map<String, Object> model = MapReadUtil.safeCastToMapWithStringKey(agentConfig.get("model"));
            updateModelIfMatch(result, model);
            agentConfig.put("model", model);
        });
        configs.put("agents", agents);
        node.setConfigs(configs);
    }

    private void handleAgentOrSubControllerNode(ImportResourceResult result, ControllerNodeVO node) {
        Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
        Map<String, Object> model = MapReadUtil.safeCastToMapWithStringKey(configs.get("model"));
        updateModelIfMatch(result, model);
        configs.put("model", model);
        node.setConfigs(configs);
    }

    private void updateModelIfMatch(ImportResourceResult result, Map<String, Object> model) {
        if (!Strings.CS.equals((String) model.get("model_deployment_id"), result.getId())) {
            return;
        }
        if (StringUtils.isNotEmpty(result.getNewId())) {
            model.put("model_deployment_id", result.getNewId());
            model.put("id", result.getNewId());
        }
    }

    private void handleControllerAgent(ImportResourceResult result, ControllerVO controllerVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        controllerVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), AgentNodeType.CONTROLLER.getType(),
                AgentNodeType.AGENT.getType()))
            .forEach(node -> {
                if (Strings.CS.equalsAny(node.getType(), AgentNodeType.CONTROLLER.getType())) {
                    Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                    List<Map<String, Object>> agents = MapReadUtil.safeCastToListWithMap(configs.get("agents"));
                    agents.forEach(agent -> {
                        if (!Strings.CS.equals((String) agent.get("id"), result.getId())) {
                            return;
                        }
                        handleNoVersionResource(result, agent);
                        Map<String, Object> agentConfigs = MapReadUtil.safeCastToMapWithStringKey(agent.get("configs"));
                        handleVersionResource(result, agentConfigs);
                        agent.put("configs", agentConfigs);
                    });
                    configs.put("agents", agents);
                    node.setConfigs(configs);
                }
                if (Strings.CS.equalsAny(node.getType(), AgentNodeType.AGENT.getType())) {
                    Map<String, Object> configs = MapReadUtil.safeCastToMapWithStringKey(node.getConfigs());
                    handleVersionResource(result, configs);
                    node.setConfigs(configs);
                }
            });
    }

    private void handleAgentDsl(ImportInfo parentResource, ImportResourceResult parentResult,
        ImportResourceResult result) {
        AgentInfo agentInfo = JsonUtils.objectToClassType(parentResource.getDsl(), AgentInfo.class);
        if (StringUtils.isNotBlank(parentResult.getNewId())) {
            agentInfo.setAgentId(parentResult.getNewId());
        }
        if (StringUtils.isNotBlank(parentResult.getNewName())) {
            agentInfo.setName(parentResult.getNewName());
        }
        switch (ResourceTypeEnum.fromValue(result.getType())) {
            case MODEL, STRATEGY -> handleAgentModel(result, agentInfo);
            case WORKFLOW -> handleAgentWorkflow(result, agentInfo);
            case TOOL -> handleAgentPlugin(result, agentInfo);
            case MCP -> handleAgentMcp(result, agentInfo);
        }
        parentResource.setDsl(agentInfo);
    }

    private void handleAgentModel(ImportResourceResult result, AgentInfo agentInfo) {
        if (!Strings.CS.equals(result.getId(), agentInfo.getModelDeploymentId())) {
            return;
        }
        if (StringUtils.isNotEmpty(result.getNewId())) {
            agentInfo.setModelDeploymentId(result.getNewId());
            // 更新agent表中的模型id
            Agent record = new Agent();
            record.setAgentId(agentInfo.getAgentId());
            record.setProjectId(agentInfo.getProjectId());
            record.setModelDeploymentId(agentInfo.getModelDeploymentId());
            record.setModel(agentInfo.getModel());
            agentMapper.updateByPrimaryKeySelective(record);
        }
    }

    private void handleAgentWorkflow(ImportResourceResult result, AgentInfo agentInfo) {
        List<WorkflowReference> workflows = agentInfo.getWorkflows();
        workflows.stream().filter(v -> Strings.CS.equals(v.getWorkflowId(), result.getId())).forEach(workflow -> {
            if (StringUtils.isNotEmpty(result.getNewId())) {
                workflow.setWorkflowId(result.getNewId());
            }
            if (StringUtils.isNotEmpty(result.getNewName())) {
                workflow.setWorkflowName(result.getNewName());
            }
            if (StringUtils.isNotEmpty(result.getNewVersion())) {
                workflow.setLastVersionId(result.getNewVersion());
            }
        });
    }

    private void handleAgentMcp(ImportResourceResult result, AgentInfo agentInfo) {
        List<McpServerReference> mcps = agentInfo.getMcpServers();
        mcps.stream().filter(v -> Strings.CS.equals(v.getMcpServerId(), result.getId())).forEach(mcp -> {
            if (StringUtils.isNotEmpty(result.getNewId())) {
                mcp.setMcpServerId(result.getNewId());
            }
            if (StringUtils.isNotEmpty(result.getNewName())) {
                mcp.setMcpServerName(result.getNewName());
            }
        });
    }

    private void handleAgentPlugin(ImportResourceResult result, AgentInfo agentInfo) {
        List<ToolReference> tools = agentInfo.getTools();
        String oldPluginId = result.getId();
        String newPluginId = result.getNewId();
        tools.stream().filter(v -> {
            String toolPluginId = v.getToolId().contains("#")
                ? v.getToolId().substring(0, v.getToolId().indexOf("#"))
                : v.getToolId();
            return Strings.CS.equals(toolPluginId, oldPluginId);
        }).forEach(tool -> {
            if (StringUtils.isNotEmpty(newPluginId)) {
                String newToolId = tool.getToolId().contains("#")
                    ? newPluginId + tool.getToolId().substring(tool.getToolId().indexOf("#"))
                    : newPluginId;
                tool.setToolId(newToolId);
            }
            if (StringUtils.isNotEmpty(result.getNewName())) {
                tool.setPluginDisplayName(result.getNewName());
                tool.setPluginChineseName(result.getNewName());
            }
            if (StringUtils.isNotEmpty(result.getNewVersion())) {
                tool.setLastVersionId(result.getNewVersion());
            }
        });
    }

    private void handleWorkflowDsl(ImportInfo parentResource, ImportResourceResult parentResult,
        ImportResourceResult result) {

        WorkflowVO workflowVO = JsonUtils.objectToClassType(parentResource.getDsl(), WorkflowVO.class);
        if (StringUtils.isNotBlank(parentResult.getNewId())) {
            workflowVO.setId(parentResult.getNewId());
        }
        if (StringUtils.isNotBlank(parentResult.getNewName())) {
            workflowVO.setName(parentResult.getNewName());
        }
        switch (ResourceTypeEnum.fromValue(result.getType())) {
            case MODEL, STRATEGY -> handleWorkflowModel(result, workflowVO, parentResource.getTargetProjectId(),
                parentResource.getTargetWorkspaceId());
            case TOOL -> handleWorkflowPlugin(result, workflowVO);
            case MCP -> handleWorkflowNoVersionNode(result, workflowVO);
            case WORKFLOW -> handleWorkflowVersionNode(result, workflowVO);
            case FUNCTIONGRAPH -> handleWorkflowFunction(result, workflowVO);
        }
        parentResource.setDsl(workflowVO);
    }

    private void handleWorkflowModel(ImportResourceResult result, WorkflowVO workflowVO, String projectId,
        String workspaceId) {
        if (StringUtils.isEmpty(result.getNewId())) {
            return;
        }
        // 处理含大模型的节点
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), NodeType.LLM.getType(), NodeType.AGENT.getType()))
            .forEach(node -> {
                Map<String, Object> config = node.getConfigs();
                if (config.get("model") == null) {
                    return;
                }
                Map<String, Object> model = MapReadUtil.safeCastToMapWithStringKey(config.get("model"));
                updateModelIfMatch(result, model);
                config.put("model", model);
            });
        Map<String, Object> workflowConfig = workflowVO.getConfigs();
        // 处理workflow dsl config中的default_model
        if (workflowConfig.get("default_model") == null) {
            return;
        }
        Map<String, String> defaultModel = JsonUtils.objectToClass(workflowConfig.get("default_model"));
        if (Strings.CS.equals(defaultModel.get("model_deployment_id"), result.getId())) {
            defaultModel.put("model_deployment_id", result.getNewId());
        } else if (StringUtils.isNotEmpty(defaultModel.get("model_deployment_id"))) {
            // 兜底：default_model 引用的模型若在目标空间不存在（如源空间已删该模型，配置残留为无效引用），
            // 用本工作流 LLM 节点的 model（已被 updateModelIfMatch 替换为有效 newId）替换，保证运行时可用。
            // 仅对无效引用兜底，有效引用不动。
            String defaultModelDeploymentId = defaultModel.get("model_deployment_id");
            List<ModelServiceData> existModels = modelServiceMapper.queryByIds(
                Collections.singletonList(defaultModelDeploymentId), projectId, workspaceId);
            if (CollectionUtils.isEmpty(existModels)) {
                Optional<Map<String, Object>> llmModel = workflowVO.getNodes().stream()
                    .filter(n -> Strings.CS.equals(n.getType(), NodeType.LLM.getType()))
                    .map(n -> MapReadUtil.safeCastToMapWithStringKey(
                        n.getConfigs() == null ? null : n.getConfigs().get("model")))
                    .filter(m -> MapUtils.isNotEmpty(m) && m.get("model_deployment_id") != null)
                    .findFirst();
                if (llmModel.isPresent()) {
                    defaultModel.put("model_deployment_id", String.valueOf(llmModel.get().get("model_deployment_id")));
                    defaultModel.put("model", String.valueOf(llmModel.get().get("model_deployment_id")));
                    defaultModel.put("model_name", String.valueOf(llmModel.get().get("model_name")));
                    defaultModel.put("model_type", String.valueOf(llmModel.get().get("model_type")));
                    // IR 生成读 configs.default_model（见 IrAdapterService.adaptConfigs），兜底替换后须写回该 key 才生效
                    workflowConfig.put("default_model", defaultModel);
                }
            }
        }
        workflowConfig.put("model", defaultModel);
    }

    private void handleWorkflowPlugin(ImportResourceResult result, WorkflowVO workflowVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), NodeType.PLUGIN.getType(),
                NodeType.AGENT.getType()))
            .forEach(node -> {
                if (Strings.CS.equals(node.getType(), NodeType.PLUGIN.getType())) {
                    handleVersionResource(result, node.getConfigs());
                }
                if (Strings.CS.equals(node.getType(), NodeType.AGENT.getType())) {
                    Map<String, Object> config = node.getConfigs();
                    if (config.get("plugins") == null) {
                        return;
                    }
                    JSONArray plugins = JSONArray.from(config.get("plugins"));
                    for (int i = 0; i < plugins.size(); i++) {
                        Map<String, Object> plugin = JsonUtils.objectToClass(plugins.get(i));
                        handleVersionResource(result, plugin);
                        plugins.set(i, plugin);
                    }
                    config.put("plugins", plugins);
                }
            });
    }

    private void handleWorkflowVersionNode(ImportResourceResult result, WorkflowVO workflowVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName()) && StringUtils.isEmpty(
            result.getNewVersion())) {
            return;
        }
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), NodeType.WORKFLOW.getType(),
                NodeType.PARAM_EXTRACTION.getType(), NodeType.INTENT_DETECTION_CONTAINER.getType()))
            .forEach(node -> {
                if (Strings.CS.equals(node.getType(), NodeType.WORKFLOW.getType())) {
                    handleVersionResource(result, node.getConfigs());
                } else if (Strings.CS.equals(node.getType(), NodeType.PARAM_EXTRACTION.getType())) {
                    handleParamExtractionNode(result, node.getConfigs());
                } else if (Strings.CS.equals(node.getType(), NodeType.INTENT_DETECTION_CONTAINER.getType())) {
                    handleIntentDetectionNode(result, node);
                }
            });
    }

    @SuppressWarnings("unchecked")
    private void handleParamExtractionNode(ImportResourceResult result, Map<String, Object> configs) {
        if (MapUtils.isEmpty(configs)) {
            return;
        }
        // Update processing_workflows in domain_objects
        Object domainObjectsObj = configs.get("domain_objects");
        if (domainObjectsObj instanceof List<?> domainObjects) {
            List<Object> updatedDomainObjects = new ArrayList<>();
            for (Object doItem : domainObjects) {
                Map<String, Object> domainObjectMap = JsonUtils.objectToClassType(doItem, Map.class);
                if (domainObjectMap == null) {
                    updatedDomainObjects.add(doItem);
                    continue;
                }
                Object processingWorkflowsObj = domainObjectMap.get("processing_workflows");
                if (processingWorkflowsObj instanceof List<?> processingWorkflows) {
                    List<Object> updatedProcessingWorkflows = new ArrayList<>();
                    for (Object pw : processingWorkflows) {
                        Map<String, Object> pwMap = JsonUtils.objectToClassType(pw, Map.class);
                        if (pwMap != null) {
                            updateSubWorkflowConfig(result, pwMap);
                            updatedProcessingWorkflows.add(pwMap);
                        } else {
                            updatedProcessingWorkflows.add(pw);
                        }
                    }
                    domainObjectMap.put("processing_workflows", updatedProcessingWorkflows);
                }
                updatedDomainObjects.add(domainObjectMap);
            }
            configs.put("domain_objects", updatedDomainObjects);
        }
        // Update extension_workflows
        Object extensionWorkflowsObj = configs.get("extension_workflows");
        if (extensionWorkflowsObj instanceof List<?> extensionWorkflows) {
            List<Object> updatedExtensionWorkflows = new ArrayList<>();
            for (Object ew : extensionWorkflows) {
                Map<String, Object> ewMap = JsonUtils.objectToClassType(ew, Map.class);
                if (ewMap != null) {
                    updateSubWorkflowConfig(result, ewMap);
                    updatedExtensionWorkflows.add(ewMap);
                } else {
                    updatedExtensionWorkflows.add(ew);
                }
            }
            configs.put("extension_workflows", updatedExtensionWorkflows);
        }
    }

    @SuppressWarnings("unchecked")
    private void handleIntentDetectionNode(ImportResourceResult result, WorkflowNodeVO node) {
        if (node.getBranches() == null) {
            return;
        }
        for (var branch : node.getBranches()) {
            Map<String, Object> branchConfigs = branch.getConfigs();
            if (branchConfigs == null || branchConfigs.get("workflow_id") == null
                || !Strings.CS.equals(branchConfigs.get("workflow_id").toString(), result.getId())) {
                continue;
            }
            if (StringUtils.isNotEmpty(result.getNewId())) {
                branchConfigs.put("workflow_id", result.getNewId());
            }
            if (StringUtils.isNotEmpty(result.getNewName()) && branchConfigs.containsKey("workflow_name")) {
                branchConfigs.put("workflow_name", result.getNewName());
            }
            if (StringUtils.isNotEmpty(result.getNewVersion()) && branchConfigs.containsKey("workflow_version_id")
                && Strings.CS.equals(branchConfigs.get("workflow_version_id").toString(), result.getVersion())) {
                branchConfigs.put("workflow_version_id", result.getNewVersion());
            }
        }
    }

    private void updateSubWorkflowConfig(ImportResourceResult result, Map<String, Object> config) {
        if (MapUtils.isEmpty(config) || config.get("id") == null) {
            return;
        }
        if (!Strings.CS.equals(config.get("id").toString(), result.getId())) {
            return;
        }
        if (StringUtils.isNotEmpty(result.getNewId())) {
            config.put("id", result.getNewId());
        }
        if (StringUtils.isNotEmpty(result.getNewName())) {
            config.put("name", result.getNewName());
        }
        if (config.get("version_id") != null
            && Strings.CS.equals(config.get("version_id").toString(), result.getVersion())
            && StringUtils.isNotEmpty(result.getNewVersion())) {
            config.put("version_id", result.getNewVersion());
        }
    }

    private void handleVersionResource(ImportResourceResult result, Map<String, Object> config) {
        if (MapUtils.isEmpty(config)) {
            return;
        }
        handleNoVersionResource(result, config);
        if (ObjectUtils.isEmpty(config.get("version_id")) && StringUtils.isNotEmpty(result.getNewVersion())) {
            config.put("version_id", result.getNewVersion());
        }
        if (Strings.CS.equals(config.get("version_id").toString(), result.getVersion()) && StringUtils.isNotEmpty(
            result.getNewVersion())) {
            config.put("version_id", result.getNewVersion());
        }
    }

    private void handleSpaciousVersionResource(Map<String, Object> config, SpaciousInfo relationInfo) {
        if (MapUtils.isEmpty(config)) {
            return;
        }
        String resourceId = String.valueOf(config.get("id"));
        // 替换为目标id
        if (Objects.nonNull(relationInfo) && StringUtils.isNotEmpty(relationInfo.getTargetResourceId())) {
            config.put("id", relationInfo.getTargetResourceId());
        }
        // 替换版本
        if (Strings.CS.equals(String.valueOf(config.get("version_id")), LATEST_PARAM)) {
            if (Objects.isNull(relationInfo)) {
                log.error("can not find relation info:{}", resourceId);
                throw new AgentStudioException(StudioError.LATEST_REPLACE_NOT_EXISTS);
            }
            config.put("version_id", relationInfo.getLatestVersionId());
            config.put("version_name", relationInfo.getLatestVersionName());
        }
    }

    /**
     * 宽松模式：按 model_deployment_id 匹配 MODEL 类 SpaciousInfo，命中则把模型引用替换为目标空间模型 ID。
     * 与 strict 的 updateModelIfMatch 对齐，同时写 model_deployment_id 和 id 两个 key。
     * 命中不到则保持原值（不抛异常），仅宽松模式调用。
     */
    private void replaceSpaciousModel(Map<String, Object> configs, List<SpaciousInfo> spaciousInfoList) {
        if (MapUtils.isEmpty(configs)) {
            return;
        }
        Object modelObj = configs.get("model");
        if (!(modelObj instanceof Map)) {
            return;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> model = (Map<String, Object>) modelObj;
        Object modelDeploymentId = model.get("model_deployment_id");
        if (modelDeploymentId == null) {
            return;
        }
        SpaciousInfo relationInfo = spaciousInfoList.stream()
            .filter(p -> Strings.CS.equals(p.getOriginalResourceId(), String.valueOf(modelDeploymentId)))
            .findFirst().orElse(null);
        if (Objects.nonNull(relationInfo) && StringUtils.isNotEmpty(relationInfo.getTargetResourceId())) {
            model.put("model_deployment_id", relationInfo.getTargetResourceId());
            model.put("id", relationInfo.getTargetResourceId());
            configs.put("model", model);
        }
    }

    /**
     * 宽松模式：替换 configs.workflows[] 中工作流引用。每条工作流的 id（源空间 workflow id==traceId）
     * 用 selectByTraceId 在目标空间匹配，命中则替换为新 id；configs.version_id 为 {{latest}} 时
     * 用命中工作流的最新发布版本替换。命中不到则保持原值（不抛异常）。仅宽松模式调用。
     */
    @SuppressWarnings("unchecked")
    private void replaceSpaciousWorkflows(Map<String, Object> configs, String projectId, String workspaceId) {
        if (MapUtils.isEmpty(configs)) {
            return;
        }
        Object workflowsObj = configs.get("workflows");
        if (!(workflowsObj instanceof List)) {
            return;
        }
        List<Object> workflows = (List<Object>) workflowsObj;
        for (Object wfObj : workflows) {
            if (!(wfObj instanceof Map)) {
                continue;
            }
            Map<String, Object> wf = (Map<String, Object>) wfObj;
            replaceSpaciousWorkflowConfigs(wf, projectId, workspaceId);
            // SubController 的 workflows[] 条目含嵌套 configs，其 id 也要同步替换为目标空间新 id
            Map<String, Object> wfConfigs = MapReadUtil.safeCastToMapWithStringKey(wf.get("configs"));
            if (MapUtils.isNotEmpty(wfConfigs)) {
                replaceSpaciousWorkflowConfigs(wfConfigs, projectId, workspaceId);
                wf.put("configs", wfConfigs);
            }
        }
        configs.put("workflows", workflows);
    }

    /**
     * 宽松模式：按 configs.id（源空间 workflow id==traceId）用 selectByTraceId 在目标空间匹配，
     * 命中则替换 id 为目标空间新 id；version_id 为 {{latest}} 时用命中工作流最新发布版本替换。
     * 命中不到则保持原值（不抛异常）。顶层 Workflow 节点与 SubController 的 workflows[] 共用。仅宽松模式调用。
     */
    private void replaceSpaciousWorkflowConfigs(Map<String, Object> configs, String projectId, String workspaceId) {
        if (MapUtils.isEmpty(configs)) {
            return;
        }
        Object idObj = configs.get("id");
        if (idObj == null) {
            return;
        }
        List<WorkflowEntity> targetWorkflows = workflowMapper.selectByTraceId(projectId, workspaceId,
            String.valueOf(idObj));
        if (CollectionUtils.isEmpty(targetWorkflows)) {
            return;
        }
        WorkflowEntity targetWf = targetWorkflows.get(0);
        configs.put("id", targetWf.getId());
        if (Strings.CS.equals(String.valueOf(configs.get("version_id")), LATEST_PARAM)) {
            List<ReleaseVersion> versions = releaseVersionMapper.selectByAppId(targetWf.getId());
            if (CollectionUtils.isNotEmpty(versions)) {
                configs.put("version_id", versions.get(0).getVersionId());
                configs.put("version_name", versions.get(0).getVersionName());
            }
        }
    }

    private void handleWorkflowNoVersionNode(ImportResourceResult result, WorkflowVO workflowVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName())) {
            return;
        }
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), NodeType.MCP.getType(), NodeType.WORKFLOW.getType()))
            .forEach(node -> {
                handleNoVersionResource(result, node.getConfigs());
            });
    }

    private void handleWorkflowFunction(ImportResourceResult result, WorkflowVO workflowVO) {
        if (StringUtils.isEmpty(result.getNewId()) && StringUtils.isEmpty(result.getNewName())) {
            return;
        }
        workflowVO.getNodes()
            .stream()
            .filter(v -> Strings.CS.equalsAny(v.getType(), NodeType.CODE.getType()))
            .forEach(node -> {
                Map<String, Object> config = node.getConfigs();
                if (!Strings.CS.equals(config.get("fg_id").toString(), result.getId())) {
                    return;
                }
                if (StringUtils.isNotEmpty(result.getNewId())) {
                    config.put("fg_id", result.getNewId());
                }
            });
    }

    private void handleNoVersionResource(ImportResourceResult result, Map<String, Object> config) {
        String configId = config.get("id") != null ? config.get("id").toString() : "null";
        String resultId = result.getId();
        boolean match = Strings.CS.equals(configId, resultId);
        if (!match) {
            return;
        }
        if (StringUtils.isNotEmpty(result.getNewId())) {
            config.put("id", result.getNewId());
        }
        if (StringUtils.isNotEmpty(result.getNewName())) {
            config.put("name", result.getNewName());
        }
    }

}
