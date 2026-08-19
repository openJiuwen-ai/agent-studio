/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.StrUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AppInfo;
import com.openjiuwen.studio.agent.manager.dto.AppListRsp;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.FreeTrialQuota;
import com.openjiuwen.studio.agent.manager.dto.ListAppsQo;
import com.openjiuwen.studio.agent.manager.dto.ModelConfig;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.AgentVersion;
import com.openjiuwen.studio.agent.manager.entity.App;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.enums.AgentStatus;
import com.openjiuwen.studio.agent.manager.enums.AgentType;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AgentVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

import javax.annotation.Resource;

/**
 * 功能描述 app管理service
 *
 */
@Slf4j
@Service
public class AppManagementService implements IAppManagementService {
    private final AppMapper appMapper;

    private final AgentCommonService agentCommonService;

    private final JiuWenService jiuWenService;

    /**
     * 百宝箱应用查询类型
     */
    private static final String ALL_SOURCE = "all";

    @Autowired
    MgObsService obsService;

    @Autowired
    IrAdapterService irAdapterService;

    @Autowired
    RelationManagementService relationManagementService;

    @Autowired
    AgentImportExportService agentImportExportService;

    @Autowired
    WorkflowValidationService workflowValidationService;

    @Autowired
    AgentMapper agentMapper;

    @Autowired
    WorkflowMapper workflowMapper;

    @Autowired
    AgentVersionMapper agentVersionMapper;

    @Autowired
    MappingMapper mappingMapper;

    @Autowired
    MessageSource messageSource;

    @Autowired
    AgentManagementService agentManagementService;

    @Resource
    private AssetFreeTrialMgmtService assetFreeTrialMgmtService;

    @Autowired
    private SkuManageService skuManageService;

    @Autowired
    private WorkflowManagementService workflowManagementService;

    @Value("${content-review.configs}")
    private String contentReviewConfigs;

    @Value("${front-page.selected_resource_ids:}")
    private String selectedResourceIds;

    @Value("${asset.app.free.trial-quota-limit:10}")
    private int freeTrialQuotaLimit;

    /**
     * 构造器
     *
     * @param appMapper appMapper
     */
    public AppManagementService(AppMapper appMapper, AgentCommonService agentCommonService,
        JiuWenService jiuWenService) {
        this.appMapper = appMapper;
        this.agentCommonService = agentCommonService;
        this.jiuWenService = jiuWenService;
    }

    @Override
    public AppListRsp listApps(String projectId, ListAppsQo listAppsQo) {
        List<App> appList;
        if (listAppsQo.isSelected() && StringUtils.isNotBlank(selectedResourceIds)) {
            List<String> selectedResourceIdsList = Arrays.asList(selectedResourceIds.split(","));
            appList = appMapper.selectByResourceIds(selectedResourceIdsList);
        } else {
            SearchCriteria criteria = new SearchCriteria();
            criteria.setName(StrUtils.filterSpecialWords(listAppsQo.getName()));
            criteria.setTagId(listAppsQo.getTagId());
            criteria.setSource(ALL_SOURCE.equalsIgnoreCase(listAppsQo.getSource()) ? null : listAppsQo.getSource());
            criteria.setType(listAppsQo.getType());
            if (StringUtils.isBlank(listAppsQo.getTagId())) {
                criteria.setTagId(null);
            }
            criteria.setWorkflowType(listAppsQo.getWorkflowType());
            PageHelper.offsetPage(listAppsQo.getOffset(), listAppsQo.getLimit());
            appList = appMapper.selectBySearchCriteria(criteria);
        }
        PageInfo<App> appPageInfo = new PageInfo<>(appList);

        // 创建一个新的appInfo pageInfo对象，解决分页异常
        PageInfo<AppInfo> appInfoPageInfo = new PageInfo<>();
        List<AppInfo> appInfoList = appPageInfo.getList().stream().map(App::convertToDto).toList();

        List<String> appResourceIds = appInfoList.stream().map(AppInfo::getResourceId).toList();
        Map<String, Integer> assetFreeTrialUsageQuotaMap = assetFreeTrialMgmtService.queryFreeTrialUsageQuota(
            appResourceIds, RequestContextUtils.getRequestUserDomainId());

        appInfoPageInfo.setList(appInfoList);
        AppListRsp appListRsp = new AppListRsp();

        // 根据语言处理返回结果
        Locale locale = LanguageUtils.getLanguageLocale();
        appInfoList.forEach(appInfo -> {
            appInfo.setCreator(messageSource.getMessage("agent-app.creator.official", null, locale));

            FreeTrialQuota freeTrialQuota = new FreeTrialQuota();
            freeTrialQuota.setLimit(freeTrialQuotaLimit);
            freeTrialQuota.setUsage(
                assetFreeTrialUsageQuotaMap.getOrDefault(appInfo.getResourceId(), freeTrialQuotaLimit));

            appInfo.setFreeTrialQuota(freeTrialQuota);
        });

        appListRsp.setAppList(appInfoList);
        appListRsp.setCount(appPageInfo.getTotal());
        return appListRsp;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "App",
        description = "复制应用",
        resourceId = "appId",
        resourceName = ""
    )
    public AppInfo copyApp(String projectId, String appId, String workspaceId, String targetWorkspaceId,
        SearchCriteria body) {
        String sourceType = body.getSource();
        if (sourceType == null) {
            throw new AgentStudioException(StudioError.CHECK_APP_INFO_FAILED);
        }

        // 根据sourceType判断是复制agent还是workflow
        String copyAppId = null;
        if (sourceType.equals(CommonConstant.AGENT)) {
            copyAppId = copyAgent(projectId, workspaceId, appId);
        } else if (sourceType.equals(CommonConstant.WORKFLOW)) {
            WorkflowInfo info = workflowManagementService.copyWorkflow(projectId, appId, targetWorkspaceId, true);
            copyAppId = info.getWorkflowId();
        }
        AppInfo appInfo = new AppInfo();
        appInfo.setResourceId(copyAppId);
        return appInfo;
    }

    private String copyAgent(String projectId, String workspaceId, String agentId) {
        skuManageService.validateInsertAppCountExceededLimitOrNot();
        AgentVersion onlineAgent = agentVersionMapper.selectOnlineVersion(agentId);
        if (onlineAgent == null) {
            log.error("online agent does not exist, projectId = {}, agentId = {}", projectId, agentId);
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        String agentDslJson = obsService.downloadObsFile(onlineAgent.getDslPath());
        AgentInfo agentInfo = JSON.parseObject(agentDslJson, AgentInfo.class);

        // 构建复制的agent对象入库
        Agent newAgent = new Agent();
        String newAgentId = UUID.randomUUID().toString();
        newAgent.setAgentId(newAgentId);
        newAgent.setProjectId(projectId);
        agentManagementService.generateValidName(newAgent, agentInfo.getName(), projectId);
        newAgent.setDescription(agentInfo.getDescription());
        newAgent.setIcon(agentInfo.getIcon());
        newAgent.setModelDeploymentId(agentInfo.getModelDeploymentId());
        newAgent.setModelName(agentInfo.getModelName());
        newAgent.setModelConfig(agentInfo.getModelConfig());
        newAgent.setInstructions(agentInfo.getInstructions());
        newAgent.setTriggerList(agentInfo.getTriggerList());
        newAgent.setMemoryVariables(agentInfo.getMemoryVariables());
        newAgent.setPrologue(agentInfo.getPrologue());
        newAgent.setSuggestQueries(agentInfo.getSuggestQueries());
        newAgent.setAdditionalQuestionsConfig(agentInfo.getAdditionalQuestionsConfig());
        newAgent.setStatus(AgentStatus.DRAFT.toString());
        newAgent.setCreator(RequestContextUtils.getRequestUserName());
        newAgent.setCreatorId(RequestContextUtils.getRequestUserId());
        newAgent.setModelType(agentInfo.getModelType());
        newAgent.setKnowledgeRetrievePolicy(agentInfo.getKnowledgeRetrievePolicy());
        newAgent.setWorkspaceId(workspaceId);
        newAgent.setReference(agentInfo.getReference());
        newAgent.setTraceId(newAgentId);
        newAgent.setDeleted(false);

        if (agentInfo.getContentReview() != null) {
            newAgent.setContentReview(JsonUtils.toJson(agentInfo.getContentReview()));
        }
        newAgent.setType(StringUtils.isEmpty(agentInfo.getType()) ? AgentType.AGENT.getValue() : agentInfo.getType());
        // 从广场复制的单智能体默认开启内容审核
        if (AgentType.AGENT.getValue().equals(newAgent.getType())) {
            newAgent.setContentReview(contentReviewConfigs);
        }

        // ir转换并上传obs
        Map<String, Object> metadata = agentImportExportService.parseMetadata(newAgent);
        Map<String, Object> irInfo = irAdapterService.adaptAgent(newAgent, metadata);
        String irPath = obsService.uploadObsFile(newAgent.getAgentId(), newAgent.getAgentId(), CommonConstant.AGENT,
            JSON.toJSONString(irInfo, JSONWriter.Feature.WriteMapNullValue), CommonConstant.Workflow.IR);
        newAgent.setIrPath(irPath);
        agentMapper.insert(newAgent);

        // 处理model关联关系
        if (agentInfo.getModelDeploymentId() != null) {
            MappingEntity mappingEntity = new MappingEntity();
            mappingEntity.setAppId(newAgentId)
                .setAppName(newAgent.getName())
                .setAppType(CommonConstant.AGENT_TYPE)
                .setResourceId(agentInfo.getModelDeploymentId())
                .setResourceType(ResourceTypeEnum.MODEL.toString())
                .setResourceName(agentInfo.getModelName())
                .setMappingId(UUID.randomUUID().toString());
            mappingMapper.insert(mappingEntity);
        }

        List<MappingEntity> hasBoundToolList = mappingMapper.selectByAppIdAndResourceType(agentId,
            CommonConstant.TOOL_TYPE);
        if (!hasBoundToolList.isEmpty()) {
            // 处理复制agent和tool的关联信息入库
            relationManagementService.handleAgentTool(projectId, workspaceId, newAgentId, hasBoundToolList);
        }

        // 关联关系入库后，dsl转换并上传obs
        agentInfo.setAgentId(newAgentId);
        agentInfo.setWorkspaceId(workspaceId);
        agentInfo.setProjectId(projectId);
        agentInfo.setName(newAgent.getName());

        String agentInfoJson = JsonUtils.serializeWithFallback(agentInfo, log,
            "AgentInfo for obs upload, agentId: " + agentId);
        String updatedAgentJson = JsonUtils.serializeWithFallback(newAgent, log,
            "AgentInfo for obs upload, agentId: " + agentId);

        // 合并新老信息，确保关联关系在dsl中
        String intermediateJson = JsonUtils.mergeDslData(agentInfoJson, agentDslJson, log,
            "DSL merge for agentId: " + agentId);
        String finalMergedJson = JsonUtils.mergeDslData(updatedAgentJson, intermediateJson, log,
            "DSL merge for agentId: " + agentId);

        String dslPath = obsService.uploadObsFile(newAgent.getAgentId(), newAgent.getAgentId(), CommonConstant.AGENT,
            finalMergedJson, CommonConstant.DSL_STR);
        newAgent.setDslPath(dslPath);
        agentMapper.updateByPrimaryKeySelective(newAgent);

        return newAgentId;
    }

    private Map<String, Object> parseMetadata(WorkflowEntity workflowEntity) {
        Map<String, Object> metaData = new HashMap<>();
        metaData.put("userId", workflowEntity.getCreatorId());
        metaData.put("projectId", workflowEntity.getProjectId());
        metaData.put("domainId", workflowEntity.getDomainId());
        metaData.put("updatedAt", workflowEntity.getUpdatedAt());
        metaData.put("publishedAt", workflowEntity.getPublishedAt());
        metaData.put("visibility", workflowEntity.getVisibility());
        metaData.put("status", workflowEntity.getStatus());
        return metaData;
    }

    private Map<String, String> getWorkflowModelConfigs(String workflowId) {
        // 获取工作流默认模型配置信息
        WorkflowEntity workflow = workflowMapper.getWorkflowById(workflowId);
        String workflowInfo = obsService.downloadObsFile(workflow.getDslPath());
        Map<String, Object> workflowConfig = JSON.parseObject(workflowInfo, WorkflowVO.class).getConfigs();

        // 历史数据全局配置可能为空
        if (workflowConfig == null) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED);
        }
        Object defaultModel = workflowConfig.get("default_model");
        if (defaultModel == null) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED_MODEL);
        }
        Map<String, String> modelConfigs;
        try {
            modelConfigs = new ObjectMapper().convertValue(defaultModel, new TypeReference<Map<String, String>>() { });
        } catch (Exception e) {
            throw new AgentStudioException(StudioError.GENERATE_PROLOGUE_FAILED_MODEL);
        }
        return modelConfigs;
    }

    public AutoAddResultJsonObject generatePrologue(String modelDeploymentId, String modelType, String model,
        ModelConfig config, String query,String workspaceId) {
        // 调用模型并解析返回结果
        String prologue = null;
        try {
            for (int callCounts = 0; callCounts < CommonConstant.MODEL_CALLS; callCounts++) {
                prologue = jiuWenService.callModel(
                    agentCommonService.buildAskModelReq(modelDeploymentId, modelType, model, config, query),workspaceId);
                if (!StringUtils.isBlank(prologue)) {
                    break;
                }
            }
        } catch (Exception e) {
            log.error("Call model failed.", e);
            throw new AgentStudioException(StudioError.CALL_MODEL_ERROR);
        }
        if (StringUtils.isBlank(prologue)) {
            boolean isChinese = LanguageUtils.isChinese();
            return new AutoAddResultJsonObject().setPrologue(
                isChinese ? CommonConstant.PROLOGUE : CommonConstant.PROLOGUE_EN);
        }
        return new AutoAddResultJsonObject().setPrologue(prologue);
    }
}

