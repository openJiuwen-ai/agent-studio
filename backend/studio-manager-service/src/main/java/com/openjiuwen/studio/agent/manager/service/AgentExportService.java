/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceVersion;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelStrategyExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.enums.relation.ReferenceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceMgmtService;
import com.openjiuwen.studio.agent.manager.service.md.RouterStrategyMgmtService;
import com.openjiuwen.studio.agent.manager.utils.DatetimeUtils;
import com.openjiuwen.studio.agent.manager.workflow.resource.adapt.ResourceAdapterFactory;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportInfo;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResourceUnit;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResp;
import com.openjiuwen.studio.agent.manager.workflow.resource.model.ExportResult;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.jetbrains.annotations.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Slf4j
public class AgentExportService {

    @Value("${env.type:}")
    private String envType;

    private final static String CONTROLLER_FILE_TYPE = "Multi-agent";

    @Value("${export.max-length}")
    private int importMaxLen;

    @Autowired
    SkuManageService skuManageService;

    @Autowired
    private ResourceAdapterFactory resourceAdapterFactory;

    public static final List<ResourceTypeEnum> EXPORT_RESOURCE_TYPE_LIST = List.of(ResourceTypeEnum.AGENT,
        ResourceTypeEnum.CONTROLLER, ResourceTypeEnum.WORKFLOW, ResourceTypeEnum.MCP,
        ResourceTypeEnum.MODEL, ResourceTypeEnum.TOOL, ResourceTypeEnum.STRATEGY, ResourceTypeEnum.SKILL);

    public static final List<String> EXPORT_RESOURCE_ROOT_TYPE_LIST = List.of(ResourceTypeEnum.AGENT.toString(),
        ResourceTypeEnum.CONTROLLER.toString(), ResourceTypeEnum.WORKFLOW.toString());

    @Autowired
    private WorkflowMapper workflowMapper;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private AgentMapper agentMapper;

    @Autowired
    private ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    private ObjectMapper jacksonObjectMapper;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private ModelServiceMgmtService modelServiceMgmtService;

    @Autowired
    private RouterStrategyMgmtService strategyMgmtService;

    @Autowired
    private I18nUtil i18nUtil;

    public ExportResourceRsp exportResource(String projectId, String workspaceId, ExportResourceParams body) {
        ExportResourceRsp exportRsp;
        // 兼容前端两种传参：resource_versions（含版本）或 resource_ids（不含版本）。
        // 优先用 resource_versions；为空时由 resource_ids 兜底构建（version 留空，后续转 latest）。
        if (CollectionUtils.isEmpty(body.getResourceVersions())) {
            List<ExportResourceVersion> versions = body.getResourceIds().stream()
                .map(id -> new ExportResourceVersion().setResourceId(id))
                .collect(Collectors.toList());
            body.setResourceVersions(versions);
        } else if (CollectionUtils.isEmpty(body.getResourceIds())) {
            // 前端只传 resource_versions 时，回填 resource_ids 供后续校验/命名使用
            body.setResourceIds(body.getResourceVersions().stream()
                .map(ExportResourceVersion::getResourceId)
                .collect(Collectors.toList()));
        }
        // 判断是否超出最大导出数量限制
        if (body.getResourceIds().size() > importMaxLen) {
            log.error("Exceeded the maximum export limit. The maximum number of exports is {}.", importMaxLen);
            throw new AgentStudioException(StudioError.EXPORT_LENGTH_TOO_LARGE, importMaxLen);
        }
        skuManageService.validateAttrEnable(CommonConstant.SKU_ATTR_CODE.EXPORT_AND_IMPORT);
        ResourceTypeEnum resourceTypeEnum = ResourceTypeEnum.fromValue(body.getResourceType());
        // 规范化 resourceType 为枚举标准值（小写），避免用户传 "Agent" 等大写导致 buildSubResource 大小写敏感匹配失败
        body.setResourceType(resourceTypeEnum.toString());
        switch (resourceTypeEnum) {
            case AGENT, CONTROLLER:
                exportRsp = exportAgents(projectId, workspaceId, body);
                break;
            case WORKFLOW:
                exportRsp = exportWorkflow(projectId, workspaceId, body);
                break;
            default:
                log.error("resource type:{} not exists", body.getResourceType());
                throw new AgentStudioException(StudioError.ERROR_REFRESH_ENVIRONMENT);

        }
        return exportRsp;
    }

    private ExportResourceRsp exportWorkflow(String projectId, String workspaceId, ExportResourceParams body) {
        List<String> workflowIds = body.getResourceIds();
        log.debug("Processing {} workflows: {}", workflowIds.size(), workflowIds);
        validExportWorkflows(projectId, workspaceId, workflowIds);

        // 工作流导出逻辑
        try {
            List<ExportResp> exportResps = new ArrayList<>();
            for (ExportResourceVersion exportResourceVersion : body.getResourceVersions()) {
                String workflowId = exportResourceVersion.getResourceId();
                // 空 version 转 latest（对齐旧版 lumina AgentExportService.exportWorkflow 行 152-154）
                String versionId = StringUtils.isEmpty(exportResourceVersion.getResourceVersion())
                    ? Constants.LATEST_PUBLISH_VERSION : exportResourceVersion.getResourceVersion();
                log.debug("Processing workflow ID: {} version:{}", workflowId, versionId);
                WorkflowEntity currentWorkflow = workflowMapper.getWorkflowById(workflowId);
                // 指定版本时校验版本存在性：不存在则记录失败项并跳过该资源（对齐旧版 lumina validResource）
                if (validReleaseVersion(workflowId, versionId, currentWorkflow.getName(), body.getResourceType(),
                    exportResps)) {
                    continue;
                }
                // 获取该版本下所有资源（versionId=latest 查草稿 mapping，具体 versionId 查版本 mapping）
                List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(workflowId,
                    versionId, null, null);
                List<MappingEntity> subExportResources = new ArrayList<>();
                buildSubExportResources(subExportResources, mappingEntities);
                // 过滤共享资源
                subExportResources = filterShareResource(workspaceId, subExportResources);
                List<ExportResourceUnit> exportResourceUnits = convertMapping2ExportParam(subExportResources);
                // 模型供应商查询
                List<ModelExportEntity> modelProviders = getModelProviders(projectId, workspaceId,
                    subExportResources);
                // 添加当前节点（透传 versionId，使 ExportResourceUnit.resourceVersion 携带具体版本）
                exportResourceUnits.add(
                    addCurrentResource(workflowId, currentWorkflow.getName(), body.getResourceType(), versionId,
                        subExportResources, modelProviders));
                for (ResourceTypeEnum resourceTypeEnum : EXPORT_RESOURCE_TYPE_LIST) {
                    ExportResp exportResp = buildSubResource(exportResourceUnits, workflowId, resourceTypeEnum);
                    if (Objects.nonNull(exportResp)) {
                        exportResps.add(exportResp);
                    }
                }
            }

            String exportFilePath = buildExportFile(exportResps, body);
            ExportResourceRsp exportResourceRsp = new ExportResourceRsp();
            exportResourceRsp.setExportResult(getExportResults(exportResps));
            exportResourceRsp.setDownloadUrl(exportFilePath);
            return exportResourceRsp;
        } catch (Exception e) {
            log.error("Failed to export the workflow.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_EXPORT_FILE);
        }
    }

    /**
     * 校验发布版本存在性。versionId=latest 时跳过；否则查 t_release_version，不存在则把该资源作为失败项加入 exportResps 并返回 true（调用方 continue 跳过该资源）。
     * 对齐旧版 lumina AgentExportService.validResource：不中断整个导出，容错记录失败项。
     *
     * @return true 表示版本不存在（调用方应 continue）；false 表示版本存在或为 latest，继续导出。
     */
    private boolean validReleaseVersion(String appId, String versionId, String resourceName, String resourceType,
        List<ExportResp> exportResps) {
        if (Strings.CS.equals(Constants.LATEST_PUBLISH_VERSION, versionId)) {
            return false;
        }
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(appId, versionId);
        if (Objects.isNull(releaseVersion)) {
            log.info("Failed to export. Release version does not exist. appId:{} version:{}", appId, versionId);
            ExportResourceUnit resourceUnit = new ExportResourceUnit();
            resourceUnit.setResourceId(appId);
            resourceUnit.setResourceType(resourceType);
            resourceUnit.setResourceName(resourceName);
            exportResps.add(buildCommonError(List.of(resourceUnit)));
            return true;
        }
        return false;
    }

    private List<ModelExportEntity> getModelProviders(String projectId, String workspaceId, List<MappingEntity> subExportResources) {
        List<String> modelIds = subExportResources.stream()
            .filter(p -> Strings.CS.equals(p.getResourceType(), ResourceTypeEnum.MODEL.toString()))
            .map(MappingEntity::getResourceId)
            .toList();
        List<ModelExportEntity> modelExportEntities = modelServiceMgmtService.buildModelExportEntity(projectId,
            workspaceId, modelIds);
        List<String> strategyIds = subExportResources.stream()
            .filter(p -> Strings.CS.equals(p.getResourceType(), ResourceTypeEnum.STRATEGY.toString()))
            .map(MappingEntity::getResourceId)
            .toList();
        List<ModelStrategyExportEntity> modelStrategyExportEntities = strategyMgmtService.buildModelStrategyExport(
            projectId, workspaceId, strategyIds);
        if (CollectionUtils.isNotEmpty(modelStrategyExportEntities)) {
            List<ModelExportEntity> strategyModelExportEntities = modelStrategyExportEntities.stream()
                .map(ModelStrategyExportEntity::getModelExportEntity)
                .filter(CollectionUtils::isNotEmpty)
                .flatMap(List::stream)
                .toList();
            if (CollectionUtils.isNotEmpty(strategyModelExportEntities)) {
                modelExportEntities.addAll(strategyModelExportEntities);
            }
        }
        return modelExportEntities;
    }

    @NotNull
    private static List<MappingEntity> filterShareResource(String workspaceId, List<MappingEntity> subExportResources) {
        //过滤非本空间共享资源
        subExportResources = subExportResources.stream()
            .filter(p -> !Strings.CS.equals(ReferenceTypeEnum.SHARE.getValue(), p.getReferenceType())
                || Strings.CS.equals(p.getResourceWorkspaceId(), workspaceId))
            .collect(Collectors.toList());
        return subExportResources;
    }

    private ExportResourceUnit addCurrentResource(String resourceId, String resourceName, String resourceType, String versionId,
        List<MappingEntity> subExportResources, List<ModelExportEntity> modelProviders) {
        ExportResourceUnit currentResource = new ExportResourceUnit();
        currentResource.setResourceId(resourceId);
        currentResource.setResourceType(resourceType);
        currentResource.setResourceName(resourceName);
        currentResource.setResourceVersion(versionId);
        Set<String> l2ResourceIds = subExportResources.stream()
            .map(MappingEntity::getResourceId)
            .collect(Collectors.toSet());
        // l2资源增加供应商和模型id
        if (CollectionUtils.isNotEmpty(modelProviders)) {
            l2ResourceIds.addAll(modelProviders.stream()
                .map(p -> p.getProviderMetadata().getModelServiceProviderMetadata().getId())
                .collect(Collectors.toSet()));
            List<ModelServiceData> modelServiceDatas = modelProviders.stream()
                .map(ModelExportEntity::getModelMetadata)
                .filter(CollectionUtils::isNotEmpty)
                .flatMap(List::stream)
                .collect(Collectors.toList());
            if (CollectionUtils.isNotEmpty(modelServiceDatas)) {
                l2ResourceIds.addAll(
                    modelServiceDatas.stream().map(ModelServiceData::getId).collect(Collectors.toSet()));
            }
        }
        currentResource.setLevel2Resources(new ArrayList<>(l2ResourceIds));
        currentResource.setResourceLevel(1);
        return currentResource;
    }

    @NotNull
    private static List<ExportResult> getExportResults(List<ExportResp> exportResps) {
        List<ExportResult> exportResults = exportResps.stream()
            .map(ExportResp::getExportResults)
            .filter(CollectionUtils::isNotEmpty)
            .flatMap(List::stream)
            .toList();
        // 去重
        exportResults = exportResults.stream()
            .collect(Collectors.toMap(ExportResult::getResourceId, p -> p, (p1, p2) -> p1))
            .values()
            .stream()
            .toList();
        // 分组：主资源 resourceLevel=1（对齐旧版 lumina，不依赖 level2Resources）
        List<ExportResult> level1Results = exportResults.stream()
            .filter(p -> p.getResourceLevel() != null && p.getResourceLevel() == 1)
            .toList();
        for (ExportResult rootResult : level1Results) {
            if (CollectionUtils.isEmpty(rootResult.getLevel2Resources())) {
                continue;
            }
            List<ExportResult> childResults = new ArrayList<>();
            for (ExportResult result : exportResults) {
                if (CollectionUtils.containsAny(rootResult.getLevel2Resources(), result.getResourceId())) {
                    childResults.add(result);
                }
            }
            rootResult.setChildResults(childResults);
        }
        return level1Results;
    }

    private String buildExportFile(List<ExportResp> exportResps, ExportResourceParams resourceParams) throws JsonProcessingException {
        StringBuilder tempJson = new StringBuilder();
        List<ExportInfo> exportInfos = exportResps.stream()
            .map(ExportResp::getExportInfos)
            .filter(CollectionUtils::isNotEmpty)
            .flatMap(List::stream)
            .collect(Collectors.toList());
        exportInfos = new ArrayList<>(exportInfos.stream()
            .collect(Collectors.toMap(
                p -> p.getResourceId() + "|" + p.getResourceLevel() + "|"
                    + (p.getReleaseVersion() != null ? p.getReleaseVersion().getVersionId() : ""),
                p -> p,
                (p1, p2) -> {
                    List<String> mergedParents = new ArrayList<>();
                    if (CollectionUtils.isNotEmpty(p1.getParents())) {
                        mergedParents.addAll(p1.getParents());
                    }
                    if (CollectionUtils.isNotEmpty(p2.getParents())) {
                        mergedParents.addAll(p2.getParents());
                    }
                    p1.setParents(mergedParents.stream().distinct().toList());
                    return p1;
                }))
            .values());
        for (ExportInfo exportInfo : exportInfos) {
            tempJson.append(jacksonObjectMapper.writeValueAsString(exportInfo)).append("\n");
        }

        String fileName = getFileName(resourceParams);
        String todayStr = DatetimeUtils.dateFormat(new Date(), DatetimeUtils.DATE_FORMAT);
        String resourceType = Strings.CS.equals(resourceParams.getResourceType(),
            ResourceTypeEnum.CONTROLLER.toString())
            ? ResourceTypeEnum.AGENT.toString()
            : resourceParams.getResourceType();
        String obsKey = String.format("%s/%s/%s/%s.jsonl", CommonConstant.EXPORT, resourceType, todayStr, fileName);
        log.info("upload export to obs:{}", obsKey);
        if (Strings.CI.equals(envType, CommonConstant.EnvType.HC)) {
            String obsFileKey = obsService.uploadStagingBucket(obsKey, tempJson.toString(), 30);
            return obsService.getTemporaryGetRsp(true, obsFileKey, 3600);
        }
        String obsFileKey = obsService.uploadObsFile(obsKey, tempJson.toString(), 30);
        return obsService.getTemporaryGetRsp(false, obsFileKey, 3600);
    }

    @NotNull
    private String getFileName(ExportResourceParams resourceParams) {
        String resourceType = resourceParams.getResourceType();
        String singleName = "export";
        StringBuilder fileNameBuilder = new StringBuilder();
        if (Strings.CS.equals(ResourceTypeEnum.CONTROLLER.toString(), resourceParams.getResourceType())) {
            fileNameBuilder.append(CONTROLLER_FILE_TYPE);
        } else {
            fileNameBuilder.append(resourceType);
        }
        if (CollectionUtils.size(resourceParams.getResourceIds()) == 1) {
            if (Strings.CS.equals(ResourceTypeEnum.AGENT.toString(), resourceParams.getResourceType())
                || Strings.CS.equals(ResourceTypeEnum.CONTROLLER.toString(), resourceParams.getResourceType())) {
                Agent agent = agentMapper.selectById(resourceParams.getResourceIds().get(0));
                singleName = Optional.ofNullable(agent).map(Agent::getName).orElse(StringUtils.EMPTY);
            }
            if (Strings.CS.equals(ResourceTypeEnum.WORKFLOW.toString(), resourceParams.getResourceType())) {
                if (CollectionUtils.size(resourceParams.getResourceIds()) == 1) {
                    WorkflowEntity workflowEntity = workflowMapper.selectByWorkflowId(
                        RequestContextUtils.getRequestProjectId(), RequestContextUtils.getRequestWorkspaceId(),
                        resourceParams.getResourceIds().get(0));
                    singleName = Optional.ofNullable(workflowEntity)
                        .map(WorkflowEntity::getName)
                        .orElse(StringUtils.EMPTY);
                }
            }
            fileNameBuilder.append("_").append(singleName);
        } else {
            fileNameBuilder.append("_")
                .append("[")
                .append(CollectionUtils.size(resourceParams.getResourceIds()))
                .append("]")
                .append("items");
        }
        fileNameBuilder.append("_").append(DatetimeUtils.dateFormat(new Date(), DatetimeUtils.DATE_FORMAT_YYYYMMDDHHMMSS));
        return fileNameBuilder.toString();
    }

    private ExportResp buildSubResource(List<ExportResourceUnit> exportResourceUnits, String appId,
        ResourceTypeEnum resourceType) {
        if (CollectionUtils.isEmpty(exportResourceUnits)) {
            return null;
        }
        List<ExportResourceUnit> buildResources = exportResourceUnits.stream()
            .filter(p -> Strings.CS.equals(p.getResourceType(), resourceType.toString()))
            .toList();
        try {
            return resourceAdapterFactory.getAdapter(resourceType.toString()).parseExport(buildResources);
        } catch (Exception e) {
            log.error("builder app:{} type:{} model error", appId, resourceType.toString(), e);
            return buildCommonError(buildResources);
        }
    }

    private void buildSubExportResources(List<MappingEntity> subExportResources, List<MappingEntity> mappingEntities) {
        if (CollectionUtils.isEmpty(mappingEntities)) {
            return;
        }
        List<MappingEntity> leafEntities = mappingEntities.stream()
            .filter(p -> !EXPORT_RESOURCE_ROOT_TYPE_LIST.contains(p.getResourceType())).toList();
        if (CollectionUtils.isNotEmpty(leafEntities)) {
            subExportResources.addAll(leafEntities);
        }
        List<MappingEntity> workflowEntities = mappingEntities.stream()
            .filter(p -> EXPORT_RESOURCE_ROOT_TYPE_LIST.contains(p.getResourceType()))
            .toList();
        if (CollectionUtils.isNotEmpty(workflowEntities)) {
            subExportResources.addAll(workflowEntities);
            // 查询子资源下的mapping
            workflowEntities = workflowEntities.stream().map(p -> {
                MappingEntity mappingEntity = new MappingEntity();
                mappingEntity.setAppId(p.getResourceId());
                mappingEntity.setAppType(p.getResourceType());
                mappingEntity.setAppVersion(p.getResourceVersion());
                return mappingEntity;
            }).toList();
            List<MappingEntity> workflowMappings = mappingMapper.selectByMappingList(workflowEntities);
            buildSubExportResources(subExportResources, workflowMappings);
        }
    }

    private ExportResp buildCommonError(List<ExportResourceUnit> resources) {
        List<ExportResult> exportResults = resources.stream().map(p -> {
            ExportResult exportResult = new ExportResult();
            exportResult.setResourceId(p.getResourceId());
            exportResult.setResourceName(p.getResourceName());
            exportResult.setResourceType(p.getResourceType());
            exportResult.setReason(i18nUtil.getMessage(StudioError.EXPORT_RESOURCE_COMMON_ERROR));
            return exportResult;
        }).toList();
        return new ExportResp(null, exportResults);
    }

    private List<ExportResourceUnit> convertMapping2ExportParam(List<MappingEntity> resources) {
        return resources.stream().map(p -> {
            ExportResourceUnit resourceUnit = new ExportResourceUnit();
            resourceUnit.setResourceId(p.getResourceId());
            resourceUnit.setResourceName(p.getResourceName());
            resourceUnit.setResourceType(p.getResourceType());
            resourceUnit.setResourceVersion(p.getResourceVersion());
            resourceUnit.setParentResourceId(p.getAppId());
            resourceUnit.setAppId(p.getAppId());
            resourceUnit.setAppType(p.getAppType());
            return resourceUnit;
        }).collect(Collectors.toList());
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

    private ExportResourceRsp exportAgents(String projectId, String workspaceId, ExportResourceParams body) {
        List<String> agentIds = body.getResourceIds();
        validAgent(projectId, workspaceId, agentIds);
        List<ExportResp> exportResps = new ArrayList<>();
        try {
            for (ExportResourceVersion exportResourceVersion : body.getResourceVersions()) {
                String agentId = exportResourceVersion.getResourceId();
                // 空 version 转 latest（对齐旧版 lumina AgentExportService.exportAgents）
                String versionId = StringUtils.isEmpty(exportResourceVersion.getResourceVersion())
                    ? Constants.LATEST_PUBLISH_VERSION : exportResourceVersion.getResourceVersion();
                log.info("parse Processing:{} version:{}", agentId, versionId);
                Agent currentAgent = agentMapper.selectById(agentId);
                // 指定版本时校验版本存在性：不存在则记录失败项并跳过该资源（对齐旧版 lumina validResource）
                if (validReleaseVersion(agentId, versionId, currentAgent.getName(), body.getResourceType(),
                    exportResps)) {
                    continue;
                }
                // 获取该版本下所有资源（versionId=latest 查草稿 mapping，具体 versionId 查版本 mapping）
                List<MappingEntity> mappingEntities = mappingMapper.selectByAppIdAndAppVersion(agentId,
                    versionId, null, null);
                List<MappingEntity> subExportResources = new ArrayList<>();
                buildSubExportResources(subExportResources, mappingEntities);

                subExportResources = filterShareResource(workspaceId, subExportResources);
                List<ExportResourceUnit> exportResourceUnits = convertMapping2ExportParam(subExportResources);
                // 模型供应商查询
                List<ModelExportEntity> modelProviders = getModelProviders(projectId, workspaceId, subExportResources);
                exportResourceUnits.add(addCurrentResource(agentId, currentAgent.getName(), body.getResourceType(), versionId,
                    subExportResources, modelProviders));
                for (ResourceTypeEnum resourceTypeEnum : EXPORT_RESOURCE_TYPE_LIST) {
                    ExportResp exportResp = buildSubResource(exportResourceUnits, agentId, resourceTypeEnum);
                    if (Objects.nonNull(exportResp)) {
                        exportResps.add(exportResp);
                    }
                }
            }
            String exportFilePath = buildExportFile(exportResps, body);
            ExportResourceRsp exportResourceRsp = new ExportResourceRsp();
            exportResourceRsp.setExportResult(getExportResults(exportResps));
            exportResourceRsp.setDownloadUrl(exportFilePath);
            return exportResourceRsp;
        } catch (Exception e) {
            log.error("Failed to export the agent.", e);
            throw new AgentStudioException(StudioError.AGENT_EXPORT_FILE);
        }
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
}
