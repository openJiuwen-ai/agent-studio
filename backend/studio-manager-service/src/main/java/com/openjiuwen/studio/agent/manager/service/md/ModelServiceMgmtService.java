/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.md;

import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.EN_LANGUAGE;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.core.type.TypeReference;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckRsp;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AvailableModelServicesQo;
import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.manager.dto.MaasServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelInvokeDataListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelInvokeDataRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelNameResp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListQo;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceReq;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelStatusReq;
import com.openjiuwen.studio.agent.manager.dto.ProviderListRsp;
import com.openjiuwen.studio.agent.manager.dto.ProviderModelList;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ProviderExportMetadata;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceCondition;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;
import com.openjiuwen.studio.agent.manager.entity.md.ModelStrategy;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthMetadata;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.entity.md.RouterStrategyEntityCondition;
import com.openjiuwen.studio.agent.manager.entity.md.mapper.ModelServiceBasePoMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthMetadataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.SysModelServiceProviderMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.UserModelServiceProviderMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.CustomModelManagerClient;
import com.openjiuwen.studio.agent.manager.rce.models.CustomModelListRsp;
import com.openjiuwen.studio.agent.manager.service.IModelServiceMgmtService;
import com.openjiuwen.studio.prompt.engineering.utils.HttpUtil;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 模型服务管理
 */
@Slf4j
@Service
public class ModelServiceMgmtService implements IModelServiceMgmtService {
    private static final String HC_ENV = "hc";

    @Autowired
    private RouterStrategyMapper routerStrategyMapper;

    @Value("${agentBuilder_provider_id:101}")
    private String agentBuilderProviderId;

    @Value("${model.platform.provider:100}")
    private String platformProvider;

    @Value("${model.platform.intent_recommendation_models_id:maas-deeseek-v32,185}")
    private String intentModelRecommendation;

    @Value("#{'${model.maas.show_black_list:}'.split(',')}")
    private Set<String> showMaasBlackList;

    private static final String INTENT_MODEL_PROVIDER_NAME_EN = "Intent Recognition Recommendation";

    private static final String INTENT_MODEL_PROVIDER_NAME_CN = "意图识别推荐";

    private static final String INTENT_MODEL_PROVIDER_ID = "intent_recognition";

    @Value("${model.free-model.enable:false}")
    private boolean freeModelEnable;

    @Autowired
    private ProviderAuthMetadataMapper providerAuthMetadataMapper;

    @Autowired
    private CustomModelManagerClient customModelManagerClient;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private ProviderAuthDataMapper providerAuthDataMapper;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ProviderAuthService authService;

    @Autowired
    private ProviderAuthDataMapper authDataMapper;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private MappingMapper mappingMapper;

    @Autowired
    private FreeModelServiceMapper freeModelMapper;

    @Autowired
    private UserModelServiceProviderMapper userModelServiceProviderMapper;

    @Autowired
    private SysModelServiceProviderMapper sysModelServiceProviderMapper;

    @Autowired
    private ProviderAuthDataMapper authMapper;

    @Value("${model.protocol.mapping:}")
    private String protocolCfg;

    private Map<String, String> protocolMapping;

    @Autowired
    private ModelLicenseCtrlService licenseCtrlService;

    @Value("${feign.client.config.customModelManager.enabled}")
    private boolean customEnabled;

    @Value("${model.platform.provider:100}")
    private String platformProviderId;

    @Value("${env.type}")
    private String envType;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    @Autowired
    private RouterStrategyMgmtService routerStrategyMgmtService;

    private static final String MODEL_PATH = "model-service/ir/%s";

    private static final String REDIS_PREFIX = "model_service_";

    private final Map<String, ModelServiceBase> freeModels = new HashMap<>(2);

    private static final Pattern SERVICE_NAME_PATTERN = Pattern.compile(
        "^[\\u4e00-\\u9fa5a-zA-Z0-9:. _/|\\\\-]{1,64}$");

    @PostConstruct
    public void postConstruct() {
        protocolMapping = new HashMap<>();
        if (StringUtils.isNotBlank(protocolCfg)) {
            String[] vs = protocolCfg.split(",");
            for (String value : vs) {
                String[] kv = value.split("#");
                protocolMapping.put(kv[0], kv[1]);
            }
        }
    }

    ModelServiceBase queryFreeModel(String modelId) {
        if (!freeModelEnable) {
            return null;
        }
        if (freeModels.isEmpty()) {
            List<ModelServiceData> dataList = freeModelMapper.queryAllFreeModels(new ModelServiceCondition());
            dataList.forEach(md -> freeModels.put(md.getId(), md));
        }
        return freeModels.get(modelId);
    }

    public int getModelServicePriority(String modelName) {
        if (modelName.toLowerCase(Locale.ROOT).contains("deepseek")) {
            return 600;
        }

        if (modelName.toLowerCase(Locale.ROOT).contains("qwen")) {
            return 700;
        }

        if (modelName.toLowerCase(Locale.ROOT).contains("agentBuilder")) {
            return 500;
        }
        return 1000;
    }

    private void checkModelAvailable(String projectId, ModelServiceBase model) {
        ProviderAuthData authData = authDataMapper.selectByMetaId(projectId, model.getWorkspaceId(),
            model.getAuthMetadataId());
        if (authData == null) {
            log.error("Not found provider auth data.");
            throw new AgentStudioException(StudioError.MD_PROVIDER_AUTH_DATA_NOT_EXIST);
        }

        ModelServiceCheckRsp rsp = modelServiceManager.checkModelAvailable(projectId, model.getModelName(),
            model.getModelType(), model.getApiUrl(), model.getInterfaceProtocol(), authData.getAuthType(),
            authData.getAuthInfo(), true);

        if (rsp != null && !rsp.isSuccess()) {
            log.error("Model service not available. {} {}", rsp.getReason(), rsp.getDetail());
            AgentStudioException exp = modelServiceManager.createAgentStudioException(rsp.getStatusCode(),
                rsp.getReason() == null ? "" : rsp.getReason());
            if (exp != null) {
                throw exp;
            }
        }
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "ModelService",
        description = "创建模型服务",
        resourceId = "-1",
        resourceName = "body.serviceName"
    )
    public String createModelService(String projectId, String workspaceId, Boolean availableCheck,
        ModelServiceReq body) {
        licenseCtrlService.canAccessIntegrationModel();

        List<ProviderAuthMetadata> metadataList = authService.selectProviderMetadataAndPermissionCheck(projectId,
            workspaceId, body.getProviderId(), false);

        List<ModelServiceBase> existMS = modelServiceMapper.queryByName(projectId, workspaceId, body.getServiceName(),
            body.getProviderId());
        if (!existMS.isEmpty()) {
            log.error("Model service name is already exist. name:{}", body.getServiceName());
            throw new AgentStudioException(StudioError.MODEL_NAME_REPEATED);
        }
        List<ModelServiceBase> existModelName = modelServiceMapper.queryByModelName(projectId, workspaceId,
            body.getModelName(), body.getProviderId());
        if (!existModelName.isEmpty()) {
            log.error("Model name is already exist. name:{}", body.getModelName());
            throw new AgentStudioException(StudioError.MODEL_NAME_ALREADY_EXIST);
        }
        if (body.getModelTags() != null && body.getModelTags().split(",").length > 5) {
            log.error("The number of model_tags exceeds the limit:{}", body.getModelTags());
            throw new AgentStudioException(StudioError.MD_MODEL_TAGS_LIMIT);
        }

        ModelServiceReq.ThrottlingPolicyEnum policyEnum = body.getThrottlingPolicy();
        if (policyEnum == null) {
            throw new AgentStudioException(StudioError.MD_INVALID_THROTTLING_POLICY);
        }
        Integer throttlingPolicy = null;
        if (!policyEnum.equals(ModelServiceReq.ThrottlingPolicyEnum.EMPTY)) {
            throttlingPolicy = Integer.parseInt(policyEnum.toString());
        }
        ModelServiceBase base = new ModelServiceBase();
        Boolean isReasoning = body.isIsReasoning();
        Boolean isSupportCloseReasoning = body.isIsSupportCloseReasoning();
        if (Boolean.TRUE.equals(isReasoning)) {
            // 只有在原字段为 true 的前提下，新增字段才起作用
            base.setIsSupportCloseReasoning(isSupportCloseReasoning);
        } else {
            base.setIsSupportCloseReasoning(false);
        }
        urlCheckUtils.checkUrl(projectId, body.getApiUrl());

        String id = UUID.randomUUID().toString();
        base.setId(id)
            .setServiceName(body.getServiceName())
            .setServiceKey("integration:" + workspaceId + ":" + body.getServiceName())
            .setModelName(body.getModelName())
            .setModelVersion(body.getModelName())
            .setModelType(body.getModelType())
            .setModelTags(body.getModelTags())
            .setModelDescription(body.getModelDescription())
            .setModelDeployType("PRIVATE-INTEGRATION")
            .setDocumentUrl("")
            .setPublic(Boolean.TRUE.equals(body.isIsPublic()))
            .setModelSize(body.getModelSize())
            .setContextLength(body.getContextLength())
            .setCreatedByUser(RequestContextUtils.getRequestUserName())
            .setLastUpdatedByUser(RequestContextUtils.getRequestUserName())
            .setCreatedDate(System.currentTimeMillis())
            .setLastUpdatedDate(System.currentTimeMillis())
            .setApiUrl(body.getApiUrl())
            .setDomainId(RequestContextUtils.getRequestUserDomainId())
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setIsSupportFunction(body.isIsSupportFunction())
            .setProviderId(body.getProviderId())
            .setAuthMetadataId(metadataList.get(0).getId())
            .setIsNetwork(body.isIsNetwork())
            .setPublishStatus("offline")
            .setInterfaceProtocol(body.getInterfaceProtocol())
            .setModelPriority(getModelServicePriority(body.getModelName()))
            .setIsSupportStream(body.isIsSupportStream())
            .setIsReasoning(body.isIsReasoning())
            .setThrottlingPolicy(throttlingPolicy)
            .setLogo(body.getLogo())
            .setIdentityId(id)
            .setModelDescriptionEn(body.getModelDescription());

        for (Map.Entry<String, String> entry : protocolMapping.entrySet()) {
            if (body.getApiUrl().contains(entry.getKey())) {
                base.setInterfaceProtocol(entry.getValue());
                break;
            }
        }

        if (Boolean.TRUE.equals(availableCheck)) {
            checkModelAvailable(projectId, base);
            base.setStatus("success");
        }

        modelServiceManager.createModelService(base);
        return id;
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "ModelService",
        description = "删除模型服务",
        resourceId = "id",
        resourceName = ""
    )
    public Void deleteModelService(String projectId, String workspaceId, String id) {
        ModelServiceBase base = queryMSAndPermissionCheck(projectId, workspaceId, id, false);
        if ("online".equals(base.getPublishStatus())) {
            log.error("Model service publish status is already publish. cannot delete. {}", id);
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_IS_PUBLISH);
        }
        // 被路由策略引用的模型不能删除
        routerStrategyMgmtService.checkReferencedStrategies(projectId, workspaceId, id);

        // 设置关联的资源为已失效
        mappingMapper.updateValidByResourceIdAndVersionId(id, null);
        modelServiceManager.deleteModelService(id);
        return null;
    }

    @Override
    public ModelNameResp existsModelName(String projectId, String workspaceId, String modelName) {
        return new ModelNameResp().setExistModelName(
            modelServiceMapper.countByModelName(projectId, workspaceId, modelName) > 0);
    }

    @Override
    public MaasServiceRsp maasModelServiceList(String projectId) {
        return new MaasServiceRsp();
    }

    private ModelServiceBase queryMSAndPermissionCheck(String projectId, String workspaceId, String id,
        boolean containPlatform) {
        ModelServiceBase modelServiceBase = modelServiceMapper.queryModelServiceDetail(id);
        if (modelServiceBase == null) {
            log.error("Model service does not exist. id:{}", id);
            throw new AgentStudioException(StudioError.MD_DATA_NOT_EXIST);
        }
        List<String> projects = containPlatform
            ? Arrays.asList(projectId, "SYSTEM")
            : Collections.singletonList(projectId);
        if (!projects.contains(modelServiceBase.getProjectId())) {
            log.error("User no model service permission. id:{} userProject:{} dataProject:{}", id, projectId,
                modelServiceBase.getProjectId());
            throw new AgentStudioException(StudioError.MD_SERVICE_PERMISSION);
        }
        List<String> workspaces = containPlatform
            ? Arrays.asList(workspaceId, "SYSTEM")
            : Collections.singletonList(workspaceId);
        if (!workspaces.contains(modelServiceBase.getWorkspaceId())) {
            log.error("User no model service permission. id:{} userWorkspace:{} dataWorkspace:{}", id, workspaceId,
                modelServiceBase.getWorkspaceId());
            throw new AgentStudioException(StudioError.MD_SERVICE_PERMISSION);
        }
        return modelServiceBase;
    }

    @Override
    public ModelServiceRsp modelServiceDetail(String projectId, String workspaceId, String id) {
        ModelServiceBase modelServiceBase = queryMSAndPermissionCheck(projectId, workspaceId, id, true);

        ModelServiceRsp modelServiceRsp = ModelServiceBasePoMapper.INSTANCE.toModelServiceRsp(modelServiceBase);

        ModelServiceProvider modelServiceProvider;
        if ("SYSTEM".equals(modelServiceBase.getProjectId()) && "SYSTEM".equals(modelServiceBase.getWorkspaceId())) {
            modelServiceProvider = sysModelServiceProviderMapper.selectById(modelServiceBase.getProviderId());
            if (HttpUtil.getLanguage().equals(EN_LANGUAGE)) {
                modelServiceRsp.setModelDescription(
                    modelServiceBase.getModelDescriptionEn() == null ? "" : modelServiceBase.getModelDescriptionEn());
                modelServiceRsp.setDisclaimer(modelServiceBase.getDisclaimerEn());
            }
        } else {
            modelServiceProvider = userModelServiceProviderMapper.selectById(modelServiceBase.getProviderId());
        }
        if (modelServiceProvider != null) {
            modelServiceRsp.setProviderName(
                modelServiceProvider.getProviderName() == null ? "" : modelServiceProvider.getProviderName());
            modelServiceRsp.setProviderNameEn(
                modelServiceProvider.getProviderNameEn() == null ? "" : modelServiceProvider.getProviderNameEn());
        }

        ProviderAuthData auth = authDataMapper.selectByMetaId(projectId, workspaceId,
            modelServiceBase.getAuthMetadataId());
        modelServiceRsp.setAuthId(auth == null || auth.getAuthInfo() == null ? null : auth.getId());

        return modelServiceRsp;
    }

    @Override
    public ModelServiceListRsp modelServiceList(String projectId, ModelServiceListQo qopParam) {
        if (StringUtils.isNotEmpty(qopParam.getServiceName()) && !SERVICE_NAME_PATTERN.matcher(
            qopParam.getServiceName()).matches()) {
            log.error("Invalid model service name: {}, pattern: {}", qopParam.getServiceName(),
                SERVICE_NAME_PATTERN.pattern());
            return new ModelServiceListRsp().setTotal(0).setData(Collections.emptyList());
        }

        if (Boolean.FALSE.equals(qopParam.isIsSubscribed()) && Strings.CS.equals(platformProviderId,
            qopParam.getProviderId())) {
            return new ModelServiceListRsp().setTotal(0).setData(Collections.emptyList());
        }

        log.info("Start to query model service. param:{}", qopParam);
        ModelServiceCondition condition = new ModelServiceCondition().setModelName(qopParam.getModelName())
            .setModelType(qopParam.getModelType())
            .setFunctioncall(qopParam.isFunctioncall())
            .setPublishStatus(qopParam.getPublishStatus())
            .setId(qopParam.getId())
            .setProjectId(projectId)
            .setProviderId(qopParam.getProviderId())
            .setServiceName(qopParam.getServiceName())
            .setWorkspaceId(qopParam.getWorkspaceId());

        condition.sqlEscapeChar();

        int total = modelServiceMapper.countByCondition(condition);
        int offset = (qopParam.getPageNum() - 1) * qopParam.getPageSize();
        if (total == 0 || offset >= total) {
            return new ModelServiceListRsp().setTotal(total).setData(Collections.emptyList());
        }

        List<ModelServiceData> datas = modelServiceMapper.queryByCondition(condition, qopParam.getPageSize(), offset);
        if (datas.isEmpty()) {
            return new ModelServiceListRsp().setData(Collections.emptyList()).setTotal(total);
        }
        Set<String> providerIds = datas.stream().map(ModelServiceData::getProviderId).collect(Collectors.toSet());
        List<ProviderAuthData> auths = authDataMapper.selectByProviders(projectId, qopParam.getWorkspaceId(),
            providerIds);
        Map<String, ProviderAuthData> authMap = new HashMap<>(auths.size());
        for (ProviderAuthData auth : auths) {
            authMap.put(auth.getProviderId(), auth);
        }

        for (ModelServiceData data : datas) {
            ProviderAuthData authData = authMap.get(data.getProviderId());
            data.setAuthId(authData == null ? null : authData.getId());
        }

        List<ModelServiceRsp> result = transToModelServicesRsp(datas);
        if (HttpUtil.getLanguage().equals(EN_LANGUAGE)) {
            for (ModelServiceRsp res : result) {
                res.setModelDescription(
                    res.getModelDescriptionEn() == null ? res.getModelDescription() : res.getModelDescriptionEn());
            }
        }
        return new ModelServiceListRsp().setData(result).setTotal(total);
    }

    private void fillMaasModelInfo(boolean canUseFreeModel, ModelServiceCondition condition,
        List<ModelServiceData> datas) {
        if (HC_ENV.equals(envType) && canUseFreeModel && StringUtils.isEmpty(condition.getProviderId())
            || platformProviderId.equals(condition.getProviderId())) {
            datas.stream()
                .filter(modelService -> platformProviderId.equals(modelService.getProviderId()))
                .forEach(modelService -> modelService.setIsInFreeTrial(canUseFreeModel));
        }
    }

    private List<ModelServiceRsp> transToModelServicesRsp(List<ModelServiceData> datas) {
        List<ModelServiceRsp> result = new ArrayList<>(datas.size());
        for (ModelServiceData ms : datas) {
            Boolean isReasoning = ms.getIsReasoning();
            Boolean isSupportCloseReasoning = ms.getIsSupportCloseReasoning();
            if (Boolean.TRUE.equals(isReasoning)) {
                ms.setIsSupportCloseReasoning(isSupportCloseReasoning);
            } else {
                ms.setIsSupportCloseReasoning(false);
            }
            ModelServiceRsp rsp = new ModelServiceRsp();
            BeanUtils.copyProperties(ms, rsp);
            rsp.setType("model");

            if (!HC_ENV.equals(envType)) {
                rsp.setIsSubscribed(true);
            }

            result.add(rsp);
        }
        return result;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ModelService",
        description = "下线模型服务",
        resourceId = "id",
        resourceName = ""
    )
    public Void offlineModelService(String projectId, String workspaceId, String id) {
        ModelServiceBase base = queryMSAndPermissionCheck(projectId, workspaceId, id, false);
        if ("offline".equals(base.getPublishStatus())) {
            log.error("Model service publish status is already offline. cannot change. {}", id);
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_CANNOT_CHANGE);
        }
        routerStrategyMgmtService.checkReferencedStrategies(projectId, workspaceId, id);
        changeModelServiceStatus(id, "offline");
        return null;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ModelService",
        description = "发布模型服务",
        resourceId = "id",
        resourceName = ""
    )
    public Void onlineModelService(String projectId, String workspaceId, Boolean availableCheck, String id) {
        ModelServiceBase serviceBase = queryMSAndPermissionCheck(projectId, workspaceId, id, false);
        if ("online".equals(serviceBase.getPublishStatus())) {
            log.error("Model service publish status is already publish. cannot change. {}", id);
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_CANNOT_CHANGE);
        }

        if (Boolean.TRUE.equals(availableCheck)) {
            checkModelAvailable(projectId, serviceBase);
            serviceBase.setStatus("success");
        }
        changeModelServiceStatus(id, "online");
        modelServiceManager.updateModelService(serviceBase);
        return null;
    }

    private List<ModelInvokeDataRsp> queryRouterStrategyInvokeData(String projectId, String modelId,
        String workspaceId) {
        RouterStrategyEntity entity = routerStrategyMapper.selectInfoById(modelId);
        if (entity == null) {
            return new ArrayList<>();
        }
        if (!projectId.equals(entity.getProjectId()) && !workspaceId.equals(entity.getWorkspaceId())) {
            log.error("User no model router permission. id:{} userProject:{} dataProject:{}", modelId, projectId,
                entity.getProjectId());
            throw new AgentStudioException(StudioError.MD_SERVICE_PERMISSION);
        }
        String[] modelIds = entity.getServiceIdList().split(",");
        List<ModelInvokeDataRsp> rsp = new ArrayList<>(modelIds.length);
        for (String id : modelIds) {
            rsp.add(queryModelBaseInvokeData(projectId, id, workspaceId));
        }
        return rsp;
    }

    private ModelInvokeDataRsp queryModelBaseInvokeData(String projectId, String modelId, String workspaceId) {
        ModelServiceBase base = queryFreeModel(modelId);
        if (base == null) {
            base = queryMSAndPermissionCheck(projectId, workspaceId, modelId, true);
        }

        ModelInvokeDataRsp rsp = new ModelInvokeDataRsp().setModelName(base.getModelName())
            .setModelType(base.getModelType())
            .setApiUrl(base.getApiUrl())
            .setInterfaceProtocol(base.getInterfaceProtocol());

        ProviderAuthData auth = authDataMapper.selectByMetaId(projectId, workspaceId, base.getAuthMetadataId());
        if (auth != null) {
            rsp.setAuthType(auth.getAuthType());
            rsp.setAuthInfo(JsonUtils.decode(auth.getAuthInfo(), Map.class));
        }
        return rsp;
    }

    @Override
    public ModelInvokeDataListRsp queryModelInvokeData(String projectId, String modelId, String workspaceId) {
        List<ModelInvokeDataRsp> datas = queryRouterStrategyInvokeData(projectId, modelId, workspaceId);
        if (!datas.isEmpty()) {
            return new ModelInvokeDataListRsp().setData(datas);
        }
        ModelInvokeDataRsp base = queryModelBaseInvokeData(projectId, modelId, workspaceId);
        datas.add(base);
        return new ModelInvokeDataListRsp().setData(datas);
    }

    @Override
    @Transactional
    public BaseResp syncModelService(String projectId, String workspaceId, String providerId) {

        // 获取providerurl地址
        ModelServiceProvider modelServiceProvider = userModelServiceProviderMapper.selectById(providerId);
        if (StringUtils.isEmpty(modelServiceProvider.getProviderUrl())) {
            throw new AgentStudioException(StudioError.MD_PROVIDER_URL_IS_NULL);
        }
        // 获取请求头的配置信息，并解密
        Map<String, String> authMap = buildSyncModelServiceHeader(projectId, workspaceId, providerId);

        // 发送http请求，获取服务列表
        String response = syncModeServiceFromProvider(modelServiceProvider.getProviderUrl(), authMap);

        // 处理模型列表数据
        saveResponse(response, projectId, workspaceId, providerId);
        return new BaseResp().setCode(CommonConstant.RESP_SUCCESS_CODE).setMessage(CommonConstant.RESP_SUCCESS_MSG);
    }

    /**
     * 保存模型服务列表返回数据
     */
    private void saveResponse(String response, String projectId, String workspaceId, String providerId) {
        JSONObject jsonObject = JSON.parseObject(response);
        JSONArray dataArray = jsonObject.getJSONArray("data");
        if (!dataArray.isEmpty()) {
            List<ModelServiceBase> currentModelServices = dataArray.toJavaList(ModelServiceBase.class);
            if (!currentModelServices.isEmpty()) {
                List<ModelServiceBase> originModelServices = modelServiceMapper.queryByProviders(projectId, workspaceId,
                    providerId);
                if (!originModelServices.isEmpty()) {
                    List<ModelServiceBase> updateModelServices = getUpdatedModelSerivces(currentModelServices,
                        originModelServices);
                    List<ModelServiceBase> deleteModelServices = getDifferenceModelSerivces(originModelServices,
                        currentModelServices);
                    List<ModelServiceBase> insertModelServices = getDifferenceModelSerivces(currentModelServices,
                        originModelServices);
                    createtModelSerivces(insertModelServices, projectId, workspaceId, providerId);
                    deleteModelServices(deleteModelServices);
                    updateModelServices(updateModelServices);
                } else {
                    createtModelSerivces(currentModelServices, projectId, workspaceId, providerId);
                }
            }
        }
    }

    /**
     * 更新模型服务
     */
    private void updateModelServices(List<ModelServiceBase> updateModelServices) {
        if (!updateModelServices.isEmpty()) {
            updateModelServices.forEach(updateModelService -> {
                modelServiceMapper.updateModelTags(updateModelService.getId(), updateModelService.getModelTags());
            });
            for (ModelServiceBase modelServiceBase : updateModelServices) {
                String path = String.format(MODEL_PATH, modelServiceBase.getId() + ".json");
                String content = JsonUtils.encode(new ModelStrategy().setType("model").setData(modelServiceBase));
                obsService.putObject(path, content);
                redisClient.set(REDIS_PREFIX + modelServiceBase.getId(), content);
            }
        }
    }

    /**
     * 删除模型信息,挪到备份表
     */
    private void deleteModelServices(List<ModelServiceBase> deleteModelServices) {
        if (!deleteModelServices.isEmpty()) {
            syncModelServiceTobackup(deleteModelServices);
            List<String> ids = deleteModelServices.stream().map(ModelServiceBase::getId).toList();
            modelServiceMapper.batchDeleteByIds(ids);
        }
        for (ModelServiceBase modelServiceBase : deleteModelServices) {
            String path = String.format(MODEL_PATH, modelServiceBase.getId() + ".json");
            try {
                obsService.deleteObject(path);
            } catch (Exception e) {
                log.warn("Delete model service config fail. path:{}", path, e);
            }
            redisClient.delete(REDIS_PREFIX + modelServiceBase.getId());
        }
    }

    /**
     * 新增模型信息
     */
    private void createtModelSerivces(List<ModelServiceBase> insertModelServices, String projectId, String workspaceId,
        String providerId) {
        if (!insertModelServices.isEmpty()) {
            List<ProviderAuthMetadata> metadataList = authService.selectProviderMetadataAndPermissionCheck(projectId,
                workspaceId, providerId, false);
            insertModelServices.forEach(item -> {
                String id = UUID.randomUUID().toString();
                item.setId(id)
                    .setModelVersion(item.getModelName())
                    .setServiceKey("integration:" + workspaceId + ":" + item.getServiceName())
                    .setModelDeployType("PRIVATE-INTEGRATION")
                    .setDocumentUrl("")
                    .setCreatedByUser(RequestContextUtils.getRequestUserName())
                    .setLastUpdatedByUser(RequestContextUtils.getRequestUserName())
                    .setCreatedDate(System.currentTimeMillis())
                    .setLastUpdatedDate(System.currentTimeMillis())
                    .setDomainId(RequestContextUtils.getRequestUserDomainId())
                    .setProjectId(projectId)
                    .setWorkspaceId(workspaceId)
                    .setProviderId(providerId)
                    .setAuthMetadataId(metadataList.get(0).getId())
                    .setPublishStatus("offline")
                    .setIdentityId(id)
                    .setInterfaceProtocol("abmodel");
            });
            modelServiceMapper.batchInsert(insertModelServices);
            for (ModelServiceBase modelServiceBase : insertModelServices) {
                String path = String.format(MODEL_PATH, modelServiceBase.getId() + ".json");
                String content = JsonUtils.encode(new ModelStrategy().setType("model").setData(modelServiceBase));
                obsService.putObject(path, content);
                redisClient.set(REDIS_PREFIX + modelServiceBase.getId(), content);
            }
        }
    }

    /**
     * 根据service_name获取交集
     */
    private List<ModelServiceBase> getUpdatedModelSerivces(List<ModelServiceBase> current,
        List<ModelServiceBase> origin) {
        // 已经存在的数据，与AB对齐只会有tag的变化
        Map<String, ModelServiceBase> currentMap = current.stream()
            .collect(Collectors.toMap(ModelServiceBase::getServiceName, model -> model));
        return origin.stream()
            .filter(model -> model.getServiceName() != null && currentMap.containsKey(model.getServiceName())
                && !Objects.equals(model.getModelTags(), currentMap.get(model.getServiceName()).getModelTags()))
            .map(model -> model.setModelTags(currentMap.get(model.getServiceName()).getModelTags()))
            .toList();
    }

    /**
     * 获取差集
     */
    private List<ModelServiceBase> getDifferenceModelSerivces(List<ModelServiceBase> current,
        List<ModelServiceBase> origin) {
        Set<String> comparisonSet = origin.stream()
            .map(ModelServiceBase::getServiceName)
            .filter(Objects::nonNull)
            .collect(Collectors.toSet());

        return current.stream()
            .filter(model -> model.getServiceName() != null && !comparisonSet.contains(model.getServiceName()))
            .collect(Collectors.toList());
    }

    private String syncModeServiceFromProvider(String providerUrl, Map<String, String> authMap) {
        Request.Builder requestBuilder = new Request.Builder().url(providerUrl);
        for (Map.Entry<String, String> entry : authMap.entrySet()) {
            requestBuilder.addHeader(entry.getKey(), entry.getValue());
        }
        Request request = requestBuilder.build();
        try (Response response = okHttpClientUtils.getHttpClient().newCall(request).execute()) {
            if (!response.isSuccessful()) {
                if (response.body() != null) {
                    log.error("syncModeServiceFromProvider  response error, the reason is {}",
                        response.body().string());
                }
                throw new AgentStudioException(StudioError.TST_API_SERVICE_EXCEPTION);
            }
            // 解析响应
            ResponseBody responseBody = response.body();
            return Objects.requireNonNull(responseBody).string();
        } catch (IOException e) {
            log.error("syncModeServiceFromProvider error, the reason is {}", e.getMessage());
            throw new AgentStudioException(StudioError.TST_API_SERVICE_EXCEPTION);
        }
    }

    private void syncModelServiceTobackup(List<ModelServiceBase> list) {
        if (!list.isEmpty()) {
            modelServiceMapper.batchInsertBackup(list);
        }
    }

    private Map<String, String> buildSyncModelServiceHeader(String projectId, String workspaceId, String providerId) {
        List<ProviderAuthMetadata> authConfigs = authMapper.selectProviderAuthData(projectId, workspaceId, providerId);
        Map<String, String> authMap = new HashMap<String, String>();
        Optional<ProviderAuthMetadata> firstOptional = authConfigs.stream()
            .filter(item -> "CUSTOM_APIKEY".equals(item.getAuthType()))
            .findFirst();
        if (firstOptional.isPresent()) {
            ProviderAuthMetadata firstConfig = firstOptional.get();
            Map<String, String> m = JsonUtils.decode(firstConfig.getAuthConfig(), new TypeReference<>() {});
            for (Map.Entry<String, String> entry : m.entrySet()) {
                String value = CryptoUtils.decrypt(entry.getValue());
                authMap.put(entry.getKey(), value);
            }
        }
        return authMap;
    }

    private void changeModelServiceStatus(String id, String targetStatus) {
        modelServiceMapper.changePublishStatus(id, targetStatus, RequestContextUtils.getRequestUserName(),
            System.currentTimeMillis());
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ModelService",
        description = "更新模型服务",
        resourceId = "id",
        resourceName = "serviceReq.serviceName"
    )
    public Void updateModelService(String projectId, String workspaceId, Boolean availableCheck, String id,
        ModelServiceReq serviceReq) {
        ModelServiceBase base = queryMSAndPermissionCheck(projectId, workspaceId, id, false);
        if ("online".equals(base.getPublishStatus())) {
            log.error("Model service publish status is already publish. cannot change. {}", id);
            throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_CANNOT_CHANGE);
        }
        if (!base.getServiceName().equals(serviceReq.getServiceName())) {
            List<ModelServiceBase> existMS = modelServiceMapper.queryByName(projectId, workspaceId,
                serviceReq.getServiceName(), base.getProviderId());
            if (!existMS.isEmpty()) {
                log.error("Model service name is already exist. Can not update. name:{}", serviceReq.getServiceName());
                throw new AgentStudioException(StudioError.MODEL_NAME_REPEATED);
            }
        }
        if (!base.getModelName().equals(serviceReq.getModelName())) {
            List<ModelServiceBase> existModelName = modelServiceMapper.queryByModelName(projectId, workspaceId,
                serviceReq.getModelName(), base.getProviderId());
            if (!existModelName.isEmpty()) {
                log.error("Model name is already exist. Can not update. name:{}", serviceReq.getModelName());
                throw new AgentStudioException(StudioError.MODEL_NAME_ALREADY_EXIST);
            }
        }
        if (serviceReq.getModelTags() != null && serviceReq.getModelTags().split(",").length > 5) {
            log.error("The number of model_tags exceeds the limit:{}", serviceReq.getModelTags());
            throw new AgentStudioException(StudioError.MD_MODEL_TAGS_LIMIT);
        }
        ModelServiceReq.ThrottlingPolicyEnum policyEnum = serviceReq.getThrottlingPolicy();
        if (policyEnum == null) {
            throw new AgentStudioException(StudioError.MD_INVALID_THROTTLING_POLICY);
        }
        Integer throttlingPolicy = null;
        if (!policyEnum.equals(ModelServiceReq.ThrottlingPolicyEnum.EMPTY)) {
            throttlingPolicy = Integer.parseInt(policyEnum.toString());
        }
        Boolean isReasoning = serviceReq.isIsReasoning();
        Boolean isSupportCloseReasoning = serviceReq.isIsSupportCloseReasoning();
        if (Boolean.TRUE.equals(isReasoning)) {
            base.setIsSupportCloseReasoning(isSupportCloseReasoning);
        } else {

            base.setIsSupportCloseReasoning(false);
        }
        urlCheckUtils.checkUrl(projectId, serviceReq.getApiUrl());

        base.setServiceName(serviceReq.getServiceName())
            .setServiceKey("integration:" + workspaceId + ":" + serviceReq.getServiceName())
            .setModelName(serviceReq.getModelName())
            .setModelVersion(serviceReq.getModelName())
            .setModelSize(serviceReq.getModelSize())
            .setContextLength(serviceReq.getContextLength())
            .setLastUpdatedByUser(RequestContextUtils.getRequestUserName())
            .setIsReasoning(serviceReq.isIsReasoning())
            .setInterfaceProtocol(serviceReq.getInterfaceProtocol())
            .setIsNetwork(serviceReq.isIsNetwork())
            .setLogo(serviceReq.getLogo())
            .setLastUpdatedDate(System.currentTimeMillis())
            .setApiUrl(serviceReq.getApiUrl())
            .setIsSupportFunction(serviceReq.isIsSupportFunction())
            .setModelPriority(getModelServicePriority(serviceReq.getModelName()))
            .setIsSupportStream(serviceReq.isIsSupportStream())
            .setModelType(serviceReq.getModelType())
            .setModelTags(serviceReq.getModelTags())
            .setModelDescription(serviceReq.getModelDescription())
            .setPublic(Boolean.TRUE.equals(serviceReq.isIsPublic()))
            .setThrottlingPolicy(throttlingPolicy);

        for (Map.Entry<String, String> entry : protocolMapping.entrySet()) {
            if (serviceReq.getApiUrl().contains(entry.getKey())) {
                base.setInterfaceProtocol(entry.getValue());
                break;
            }
        }

        if (Boolean.TRUE.equals(availableCheck)) {
            checkModelAvailable(projectId, base);
            base.setStatus("success");
        }
        modelServiceManager.updateModelService(base);
        return null;
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "ModelService",
        description = "更新模型调测状态",
        resourceId = "body.modelId",
        resourceName = ""
    )
    public Void updateModelStatus(String projectId, String workspaceId, ModelStatusReq body) {
        modelServiceMapper.updateModelStatus(body.getModelId(), body.getStatus(), projectId, workspaceId);
        return null;
    }

    private List<ModelServiceData> queryPublicModels(boolean onlyPrivate, ModelServiceCondition condition) {
        if (onlyPrivate) {
            return Collections.emptyList();
        }
        List<ModelServiceData> models = modelServiceMapper.queryPublicAvailableServices(condition);
        models.forEach(md -> {
            md.setModelTags(StringUtils.isEmpty(md.getModelTags()) ? "Public" : md.getModelTags() + ",Public");
        });
        return models;
    }

    @Override
    public Object availableModelServices(String projectId, AvailableModelServicesQo param) {
        long startTime = System.currentTimeMillis();
        String workspaceId = param.getWorkspaceId();
        ModelServiceCondition condition = new ModelServiceCondition().setModelName(param.getModelName())
            .setFunctioncall(param.isFunctioncall())
            .setServiceName(param.getServiceName())
            .setId(param.getId())
            .setProviderId(param.getProviderId())
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId);

        if (param.getPublishStatus() == null || param.getPublishStatus().isEmpty()) {
            condition.setPublishStatus("online");
        } else {
            condition.setPublishStatus("all".equals(param.getPublishStatus()) ? null : param.getPublishStatus());
        }

        if (StringUtils.isNotEmpty(param.getModelType())) {
            condition.setModelTypes(Arrays.asList(param.getModelType().split(",")));
        }

        condition.sqlEscapeChar();

        if (licenseCtrlService.canUseFreeModel()) {
            condition.setFreeProviderId(platformProviderId);
        }

        List<ModelServiceData> datas;
        if (!customEnabled) {
            datas = new ArrayList<>(modelServiceMapper.queryAvailableServices(condition));
            datas.addAll(queryPublicModels(Boolean.TRUE.equals(param.isOnlyPrivate()), condition));
            datas = datas.stream().filter(t -> !showMaasBlackList.contains(t.getId())).toList();
            try {
                fillMaasModelInfo(licenseCtrlService.canUseFreeModel(), condition, datas);
            } catch (Exception ignore) {
                log.error("query mass model fail, msg: {}", ignore.getMessage());
            }
        } else {
            Set<String> ids = getCustomModelList(projectId, RequestContextUtils.getRequestUserId());
            if (ids.isEmpty()) {
                datas = new ArrayList<>();
            } else {
                condition.setIdList(ids);
                datas = new ArrayList<>(modelServiceMapper.queryAvailableServices(condition));
                datas.addAll(queryPublicModels(Boolean.TRUE.equals(param.isOnlyPrivate()), condition));
            }
        }

        // 设置供应商鉴权配置状态
        List<String> providerIds = datas.stream()
            .map(ModelServiceData::getProviderId)
            .filter(StringUtils::isNotEmpty)
            .distinct()
            .toList();
        if (CollectionUtils.isNotEmpty(providerIds)) {
            Set<String> existsProviderAuthIds = authDataMapper.selectByProviders(projectId, workspaceId, providerIds)
                .stream()
                .filter(t -> StringUtils.isNotEmpty(t.getAuthInfo()))
                .map(ProviderAuthData::getProviderId)
                .collect(Collectors.toSet());
            datas.forEach(modelService -> modelService.setIsAuthConfigured(
                existsProviderAuthIds.contains(modelService.getProviderId())));
        }

        if ("provider".equals(param.getGroupby())) {
            ProviderListRsp rsp = availableProviderModelServices(datas, param.isIntentRecognition());
            if (Boolean.TRUE.equals(param.isWithRouter())) {
                List<ModelServiceRsp> routerStrategies = queryStrategy(projectId, workspaceId, param.getServiceName(),
                    param.getModelType());

                if (!routerStrategies.isEmpty()) {
                    ProviderModelList pd = new ProviderModelList();
                    pd.setId("AgentBuilderRouter")
                        .setProviderName("路由策略")
                        .setType("router")
                        .setLogo("")
                        .setSource("platform")
                        .setModels(routerStrategies);
                    if (HttpUtil.getLanguage().equals(EN_LANGUAGE)) {
                        pd.setProviderName("Routing Policy");
                    }
                    rsp.getData().add(pd);
                }
            }

            return rsp;
        }

        List<ModelServiceRsp> result = transToModelServicesRsp(datas);

        if (Boolean.TRUE.equals(param.isWithRouter())) {
            result.addAll(queryStrategy(projectId, workspaceId, param.getServiceName(), param.getModelType()));
        }
        return new ModelServiceListRsp().setData(result).setTotal(result.size());
    }

    ModelServiceRsp routerToModelServiceRsp(RouterStrategyEntity entity) {
        ModelServiceRsp rsp = new ModelServiceRsp();
        rsp.setModelName(entity.getStrategyName())
            .setServiceName(entity.getStrategyName())
            .setId(entity.getId())
            .setType("router")
            .setStatus("success")
            .setPublishStatus("online")
            .setModelType("LLM");
        return rsp;
    }

    private List<ModelServiceRsp> queryStrategy(String projectId, String workspaceId, String query, String modelType) {
        if (modelType != null && !modelType.toUpperCase(Locale.ROOT).contains("LLM")) {
            return Collections.emptyList();
        }
        RouterStrategyEntityCondition condition = new RouterStrategyEntityCondition().setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setQuery(query)
            .setLimit(10000)
            .setOffset(0);

        condition.sqlEscapeChar();
        List<RouterStrategyEntity> routerStrategies = routerStrategyMapper.selectInfoByQueryParameter(condition);
        List<ModelServiceRsp> result = new ArrayList<>(routerStrategies.size());
        for (RouterStrategyEntity entity : routerStrategies) {
            result.add(routerToModelServiceRsp(entity));
        }
        return result;
    }

    private Map<String, List<ModelServiceRsp>> transToModelServicesMapRsp(List<ModelServiceData> datas) {
        Map<String, List<ModelServiceRsp>> result = new HashMap<>();
        for (ModelServiceData ms : datas) {
            ModelServiceRsp rsp = new ModelServiceRsp();
            BeanUtils.copyProperties(ms, rsp);

            result.computeIfAbsent(ms.getProviderId(), key -> new ArrayList<>()).add(rsp);
        }
        return result;
    }

    private ProviderListRsp availableProviderModelServices(List<ModelServiceData> datas, Boolean intentRecognition) {
        if (datas.isEmpty()) {
            return new ProviderListRsp().setData(new ArrayList<>());
        }

        // 转换数据
        Map<String, List<ModelServiceRsp>> result = transToModelServicesMapRsp(datas);
        List<ModelServiceRsp> intentModelData = getIntentModelData(result, intentRecognition);
        List<ModelServiceProviderDetail> providerList = modelServiceMapper.getLogosAndProviderNamesByProviderIds(
            result.keySet());

        // 构建模型列表
        List<ProviderModelList> data = buildProviderModelList(providerList, result, intentModelData, intentRecognition);
        return new ProviderListRsp().setData(data);
    }

    private List<ModelServiceRsp> getIntentModelData(Map<String, List<ModelServiceRsp>> result,
        Boolean intentRecognition) {
        List<String> intentModelList = Arrays.asList(intentModelRecommendation.split(","));
        List<ModelServiceRsp> intentModelData = new ArrayList<>();

        if (intentRecognition && result.containsKey(platformProvider)) {
            intentModelData = result.get(platformProvider)
                .stream()
                .filter(model -> intentModelList.contains(model.getId()))
                .toList();
            result.get(platformProvider).removeAll(intentModelData);
        }

        return intentModelData;
    }

    private List<ProviderModelList> buildProviderModelList(List<ModelServiceProviderDetail> providerList,
        Map<String, List<ModelServiceRsp>> result, List<ModelServiceRsp> intentModelData, Boolean intentRecognition) {
        List<ProviderModelList> data = new ArrayList<>(providerList.size());
        ProviderModelList recommendPd = null;

        for (ModelServiceProviderDetail provider : providerList) {
            ProviderModelList pd = createProviderModelList(provider, result);
            if (provider.getId().equals(agentBuilderProviderId)) {
                recommendPd = pd;
            } else {
                data.add(pd);
            }
        }

        if (recommendPd != null) {
            data.add(0, recommendPd);
        }

        if (intentRecognition && !intentModelData.isEmpty()) {
            data.add(0, createIntentModelList(intentModelData));
        }

        return data;
    }

    private ProviderModelList createProviderModelList(ModelServiceProviderDetail provider,
        Map<String, List<ModelServiceRsp>> result) {
        ProviderModelList pd = new ProviderModelList();
        pd.setId(provider.getId())
            .setProviderName(provider.getProviderName())
            .setLogo(provider.getLogo())
            .setSource(provider.getSource())
            .setType("model")
            .setModels(result.get(provider.getId()));

        if (HttpUtil.getLanguage().equals(EN_LANGUAGE)) {
            pd.setProviderName(
                provider.getProviderNameEn() == null ? provider.getProviderName() : provider.getProviderNameEn());
        }

        return pd;
    }

    private ProviderModelList createIntentModelList(List<ModelServiceRsp> intentModelData) {
        ProviderModelList pd = new ProviderModelList();
        pd.setId(INTENT_MODEL_PROVIDER_ID)
            .setProviderName(INTENT_MODEL_PROVIDER_NAME_CN)
            .setLogo("")
            .setSource("")
            .setModels(intentModelData);

        if (HttpUtil.getLanguage().equals(EN_LANGUAGE)) {
            pd.setProviderName(INTENT_MODEL_PROVIDER_NAME_EN);
        }

        return pd;
    }

    private Set<String> getCustomModelList(String projectId, String userId) {
        ResponseEntity<CustomModelListRsp> responseJson = customModelManagerClient.getAvailableModelByUserId(userId,
            projectId);
        if (!responseJson.getStatusCode().is2xxSuccessful()) {
            log.error("fail query custom models. status:{} rsp:{}", responseJson.getStatusCode(),
                JsonUtils.encode(responseJson.getBody()));
            throw new AgentStudioException(StudioError.MD_GET_CUSTOM_MODELS_FAIL);
        }
        if (Objects.isNull(responseJson.getBody())) {
            log.info("Response body is null!");
            return Collections.emptySet();
        }
        List<CustomModelListRsp.Result> result = responseJson.getBody().getResult();
        if (ObjectUtils.isEmpty(result)) {
            log.info("AvailableModel is null!");
            return Collections.emptySet();
        }
        Set<String> ids = new HashSet<>();
        for (CustomModelListRsp.Result value : result) {
            ids.add(value.getModelNameEn());
        }
        return ids;
    }

    public List<ModelExportEntity> buildModelExportEntity(String projectId, String workspaceId, List<String> modelIds) {

        try {
            List<ModelServiceData> modelList = getValidatedModels(projectId, workspaceId, modelIds);
            Map<String, ProviderExportMetadata> providerExportMap = batchGetProviderExportMetadata(projectId,
                workspaceId, modelList);
            // 按 providerId 对模型进行分组
            Map<String, List<ModelServiceData>> groupedModels = modelList.stream()
                .filter(Objects::nonNull)
                .collect(Collectors.groupingBy(m -> Objects.toString(m.getProviderId(), "UNKNOWN")));
            List<ModelExportEntity> exportEntityList = new ArrayList<>();

            for (Map.Entry<String, List<ModelServiceData>> entry : groupedModels.entrySet()) {
                String providerId = entry.getKey();
                List<ModelServiceData> models = entry.getValue();
                ModelExportEntity exportEntity = new ModelExportEntity();
                exportEntity.setModelMetadata(new ArrayList<>(models));

                // 获取对应的 Provider 复合对象
                ProviderExportMetadata providerExport = providerExportMap.get(providerId);
                if (providerExport == null && !providerId.equals("UNKNOWN")) {
                    log.warn("Models {} reference provider {} but its metadata is missing",
                        models.stream().map(ModelServiceData::getId).toList(), providerId);
                }

                exportEntity.setProviderMetadata(providerExport);
                exportEntityList.add(exportEntity);
            }

            return exportEntityList;
        } catch (Exception e) {
            log.error("Failed to build model export entity. Project: {}, Workspace: {}", projectId, workspaceId, e);
            throw new AgentStudioException(StudioError.MODEL_EXPORT_DATA);
        }
    }

    public List<ModelServiceData> getValidatedModels(String projectId, String workspaceId, List<String> modelIds) {
        if (CollectionUtils.isEmpty(modelIds)) {
            log.warn("No found modelIds: {}", modelIds);
            return Collections.emptyList();
        }
        List<ModelServiceData> models = modelServiceMapper.selectByIds(modelIds);
        if (CollectionUtils.isEmpty(models)) {
            log.warn("Models not found for Ids: {}", modelIds);
            return Collections.emptyList();
        }
        return models;
    }

    public Map<String, ProviderExportMetadata> batchGetProviderExportMetadata(String projectId, String workspaceId,
        List<ModelServiceData> models) {
        Set<String> providerIds = models.stream()
            .map(ModelServiceData::getProviderId)
            .filter(StringUtils::isNotBlank)
            .collect(Collectors.toSet());

        if (providerIds.isEmpty()) {
            log.error("providerIds is empty");
            return Collections.emptyMap();
        }

        List<ModelServiceProvider> providerList = userModelServiceProviderMapper.selectByIds(providerIds);
        Map<String, ModelServiceProvider> providerInfoMap = providerList.stream()
            .collect(Collectors.toMap(ModelServiceProvider::getId, p -> p, (a, b) -> a));

        List<ProviderAuthMetadata> authList = providerAuthMetadataMapper.selectByIds(providerIds);
        Map<String, ProviderAuthMetadata> authInfoMap = authList.stream()
            .collect(Collectors.toMap(ProviderAuthMetadata::getProviderId, a -> a, (a, b) -> a));

        List<ProviderAuthData> authDataList = providerAuthDataMapper.selectByProviderIds(providerIds);
        Map<String, ProviderAuthData> authDataMap = authDataList.stream()
            .peek(am -> am.setAuthInfo(" "))
            .collect(Collectors.toMap(ProviderAuthData::getProviderId, d -> d, (a, b) -> a));

        Map<String, ProviderExportMetadata> exportProviderMap = new HashMap<>();
        for (String pid : providerIds) {
            ModelServiceProvider modelServiceProvider = providerInfoMap.get(pid);
            ProviderAuthMetadata providerAuthMetadata = authInfoMap.get(pid);
            ProviderAuthData providerAuthData = authDataMap.get(pid); // 获取新增的数据
            if (modelServiceProvider == null && providerAuthMetadata != null) {
                if ("SYSTEM".equals(providerAuthMetadata.getProjectId()) && "SYSTEM".equals(
                    providerAuthMetadata.getWorkspaceId())) {
                    modelServiceProvider = sysModelServiceProviderMapper.selectById(
                        providerAuthMetadata.getProviderId());
                }
            }
            if (modelServiceProvider != null || providerAuthData != null) {
                ProviderExportMetadata exportMeta = new ProviderExportMetadata();
                exportMeta.setModelServiceProviderMetadata(modelServiceProvider);
                exportMeta.setProviderAuthMetadata(providerAuthMetadata);
                exportMeta.setProviderAuthData(providerAuthData); // 设置到复合对象中
                exportProviderMap.put(pid, exportMeta);
            }
        }

        return exportProviderMap;
    }

    /**
     * 根据导出的实体（JSON结构）创建模型服务
     *
     * @param createdModels 列表
     */
    public void importModels(String projectId, String workspaceId, List<ModelServiceData> createdModels,
        Boolean availableCheck) {
        licenseCtrlService.canAccessIntegrationModel();
        if (createdModels == null) {
            log.warn("Import model metadata is empty.");
            throw new AgentStudioException(StudioError.MODEL_NOT_EXIST);
        }
        for (ModelServiceBase modelData : createdModels) {
            if (modelData == null) {
                continue;
            }
            List<ModelServiceBase> existMS = modelServiceMapper.queryByName(projectId, workspaceId,
                modelData.getServiceName(), modelData.getProviderId());
            if (CollectionUtils.isNotEmpty(existMS)) {
                log.warn("Model service {} already exists in project {}, skipping.", modelData.getServiceName(),
                    projectId);
                continue;
            }
            if (modelData.getModelTags() != null && modelData.getModelTags().split(",").length > 5) {
                log.error("The number of model_tags exceeds the limit:{}", modelData.getModelTags());
                throw new AgentStudioException(StudioError.MD_MODEL_TAGS_LIMIT);
            }
            urlCheckUtils.checkUrl(projectId, modelData.getApiUrl());
            if (Boolean.TRUE.equals(availableCheck)) {
                try {
                    modelData.setStatus("success");
                } catch (Exception e) {
                    log.error("Available check failed for imported model: {}", modelData.getServiceName(), e);
                    modelData.setStatus("failed");
                }
            }
            modelServiceManager.createModelService(modelData);
            log.info("Successfully imported model: {} with new ID: {}", modelData.getServiceName());
        }
    }
}
