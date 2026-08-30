/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.md;

import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.ListRouterStrategyQo;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyBaseInfo;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyListResponse;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyRequest;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelStrategyExportEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceCondition;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProvider;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceProviderDetail;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.entity.md.RouterStrategyEntityCondition;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.service.IRouterStrategyMgmtService;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
public class RouterStrategyMgmtService implements IRouterStrategyMgmtService {
    private static final long FIVE_MINUTES = 5L * 60 * 1000L;

    @Value("${model.free-model.enable:false}")
    private boolean freeModelEnable;

    @Value("${model.soft.delete.enable:false}")
    private boolean modelSoftDelete;

    @Value("${model.platform.provider:100}")
    private String platformProviderId;

    @Autowired
    @Lazy
    private ModelServiceMgmtService modelServiceMgmtService;

    @Autowired
    private RouterStrategyMapper routerStrategyMapper;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private ModelLicenseCtrlService licenseCtrlService;

    @Autowired
    private FreeModelServiceMapper freeModelServiceMapper;

    private List<ModelServiceData> freeModelCache = new ArrayList<>();

    private long lastRefreshTime;

    private List<ModelServiceData> queryFreeModels(Set<String> modelIds) {
        if (!freeModelEnable) {
            return new ArrayList<>();
        }
        if (System.currentTimeMillis() - lastRefreshTime > FIVE_MINUTES) {
            freeModelCache = freeModelServiceMapper.queryAllFreeModels(new ModelServiceCondition());
            lastRefreshTime = System.currentTimeMillis();
        }
        List<ModelServiceData> models = new ArrayList<>();
        for (ModelServiceData model : freeModelCache) {
            if (modelIds.contains(model.getId())) {
                models.add(model);
            }
        }
        return models;
    }

    private List<ModelServiceData> checkModelServices(String projectId, String workspaceId, List<ModelServiceRsp> req) {
        // 校验路由里的serviceId是否可以访问
        Set<String> modelIds = req.stream()
            .map(ModelServiceRsp::getId)
            .collect(Collectors.toCollection(LinkedHashSet::new));

        if (modelIds.size() < req.size()) {
            log.error("Duplicate model exists.");
            throw new AgentStudioException(StudioError.MD_REQUEST_BODY_INVALID);
        }

        if (modelIds.isEmpty()) {
            log.error("Model is empty.");
            throw new AgentStudioException(StudioError.MD_REQUEST_BODY_INVALID_MODEL);
        }


        List<ModelServiceData> freeModels = queryFreeModels(modelIds);

        List<ModelServiceData> projectModels = modelServiceMapper.queryByIds(modelIds, projectId, workspaceId);

        List<ModelServiceData> allModels = new ArrayList<>(freeModels);
        allModels.addAll(projectModels);

        // 构建 id 到 ModelServiceData 的映射
        Map<String, ModelServiceData> modelMap = allModels.stream()
            .collect(Collectors.toMap(ModelServiceData::getId, Function.identity()));

        // 按照原始请求顺序重新构建 models 列表
        List<ModelServiceData> models = new ArrayList<>();
        for (ModelServiceRsp service : req) {
            String id = service.getId();
            String providerId = service.getProviderId();
            if (modelMap.containsKey(id)) {
                ModelServiceData modelServiceData = modelMap.get(id);
                modelServiceData.setProviderId(providerId);
                models.add(modelMap.get(id));
            }
        }

        if (models.size() < req.size()) {
            log.error("Some model is not exist. {}", modelIds);
            throw new AgentStudioException(StudioError.MD_REQUEST_BODY_INVALID_MODEL_NOT_EXIST);
        }

        for (ModelServiceData model : models) {
            if (StringUtils.isEmpty(model.getAuthId())) {
                if (model.getProviderId().equals(platformProviderId) && licenseCtrlService.canUseFreeModel()) {
                    continue;
                }

                log.error("Model auth info is missing. modelId:{} modelName:{} project:{} workspace:{}", model.getId(),
                    model.getModelName(), projectId, workspaceId);
                throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_AUTH_NOT_EXIST, model.getModelName());
            }
        }

        return models;
    }

    @Override
    @OperationLog(
        operationType = OperationType.CREATE,
        resourceType = "RouterStrategy",
        description = "创建路由策略",
        resourceId = "-1",
        resourceName = "body.strategyName"
    )
    public RouterStrategyBaseInfo createRouterStrategy(String projectId, String workspaceId,
        RouterStrategyRequest body) {
        // 重名校验
        List<RouterStrategyEntity> entityList = routerStrategyMapper.selectInfoByStrategyName(projectId, workspaceId,
            body.getStrategyName());
        if (!entityList.isEmpty()) {
            log.error("Router strategy name is already exist. name:{}", body.getStrategyName());
            throw new AgentStudioException(StudioError.ROUTER_STRATEGY_NAME_REPEATED);
        }

        List<ModelServiceData> models = checkModelServices(projectId, workspaceId, body.getModelServiceList());

        // 保存
        String strategyId = UUID.randomUUID().toString();
        RouterStrategyEntity entity = transformCreateStrategyReqToEntity(strategyId, projectId, workspaceId, body,
            models);

        modelServiceManager.saveRouterStrategy(entity);

        RouterStrategyBaseInfo res = new RouterStrategyBaseInfo();
        res.setId(entity.getId());
        res.setStrategyKey(entity.getStrategyKey());
        res.setStrategyName(entity.getStrategyName());
        return res;
    }

    @Override
    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "RouterStrategy",
        description = "删除路由策略",
        resourceId = "strategyId",
        resourceName = ""
    )
    public Void deleteRouterStrategy(String projectId, String workspaceId, String strategyId) {
        RouterStrategyEntity routerStrategy = routerStrategyMapper.selectInfoById(strategyId); // 从数据查询
        checkAuth(projectId, workspaceId, routerStrategy); // 权限校验

        // 数据删除备份
        if (modelSoftDelete) {
            modelServiceManager.backupRouterStrategy(strategyId);
        }
        modelServiceManager.deleteRouterStrategy(strategyId);
        return null;
    }

    @Override
    public RouterStrategyListResponse listRouterStrategy(String projectId, ListRouterStrategyQo listRouterStrategyQo) {
        RouterStrategyEntityCondition condition = new RouterStrategyEntityCondition().setProjectId(projectId)
            .setWorkspaceId(listRouterStrategyQo.getWorkspaceId())
            .setQuery(listRouterStrategyQo.getQuery());

        condition.sqlEscapeChar();

        // 查询总数
        int totalSize = routerStrategyMapper.selectTotalSizeByQueryParameter(condition);

        int offset = (listRouterStrategyQo.getPageNum() - 1) * listRouterStrategyQo.getPageSize();
        if (totalSize <= offset) {
            return new RouterStrategyListResponse().setTotal(totalSize).setData(new ArrayList<>());
        }

        condition.setLimit(listRouterStrategyQo.getPageSize()).setOffset(offset);

        // 查询详细数据，分页
        List<RouterStrategyBaseInfo> entityList = routerStrategyMapper.selectInfoByQueryParameter(condition)
            .stream()
            .map(this::transformStrategyEntityToVo)
            .collect(Collectors.toList());

        // 返回
        RouterStrategyListResponse res = new RouterStrategyListResponse();
        res.setTotal(totalSize);
        res.setData(entityList);
        return res;
    }

    @Override
    public RouterStrategyBaseInfo strategyDetail(String projectId, String workspaceId, String strategyId) {
        // 根据strategyId、projectId、workspaceId查询
        RouterStrategyEntity routerStrategyEntity = routerStrategyMapper.selectInfoById(strategyId);

        checkAuth(projectId, workspaceId, routerStrategyEntity);

        return transformStrategyEntityToVo(routerStrategyEntity);
    }

    @Override
    @OperationLog(
        operationType = OperationType.UPDATE,
        resourceType = "RouterStrategy",
        description = "修改路由策略",
        resourceId = "strategyId",
        resourceName = "body.strategyName"
    )
    public Void updateRouterStrategy(String projectId, String workspaceId, String strategyId,
        RouterStrategyRequest body) {
        RouterStrategyEntity routerStrategyEntity = routerStrategyMapper.selectInfoById(strategyId);

        // 查询原数据
        checkAuth(projectId, workspaceId, routerStrategyEntity);

        if (!Strings.CS.equals(body.getStrategyName(), routerStrategyEntity.getStrategyName())) {
            // 重名校验
            List<RouterStrategyEntity> entityList = routerStrategyMapper.selectInfoByStrategyName(projectId,
                workspaceId, body.getStrategyName());
            if (!entityList.isEmpty()) {
                log.error("Router strategy updated name is already exist. name:{}", body.getStrategyName());
                throw new AgentStudioException(StudioError.ROUTER_STRATEGY_NAME_REPEATED);
            }
        }

        List<ModelServiceData> models = checkModelServices(projectId, workspaceId, body.getModelServiceList());

        routerStrategyEntity.setLastUpdatedByUserName(RequestContextUtils.getRequestUserName())
            .setLastUpdatedDate(System.currentTimeMillis())
            .setStrategyName(body.getStrategyName())
            .setStrategyDescription(body.getStrategyDescription())
            .setStrategyTimeout(body.getStrategyTimeout())
            .setStrategyRetryCount(body.getStrategyRetryCount())
            .setServiceIdList(models.stream().map(ModelServiceData::getId).collect(Collectors.joining(",")))
            .setAuthIdList(models.stream().map(ModelServiceData::getAuthId).collect(Collectors.joining(",")))
            .setServiceCount(body.getModelServiceList().size())
            .setStrategyKey(genStrategyKey(workspaceId, body.getStrategyName()));

        // 更新
        modelServiceManager.updateRouterStrategy(routerStrategyEntity);
        return null;
    }

    private void checkAuth(String projectId, String workspaceId, RouterStrategyEntity routerStrategy) {
        if (routerStrategy == null || !routerStrategy.getProjectId().equals(projectId)
            || !routerStrategy.getWorkspaceId().equals(workspaceId)) {
            throw new AgentStudioException(StudioError.MD_ROUTER_STRATEGY_NOT_EXIST);
        }
    }

    private RouterStrategyEntity transformCreateStrategyReqToEntity(String strategyId, String projectId,
        String workspaceId, RouterStrategyRequest body, List<ModelServiceData> models) {
        return new RouterStrategyEntity().setId(strategyId)
            .setProjectId(projectId)
            .setWorkspaceId(workspaceId)
            .setDomainId(RequestContextUtils.getRequestUserDomainId())
            .setLastUpdatedByUserName(RequestContextUtils.getRequestUserName())
            .setCreatedByUserName(RequestContextUtils.getRequestUserName())
            .setCreatedDate(System.currentTimeMillis())
            .setLastUpdatedDate(System.currentTimeMillis())
            .setStrategyName(body.getStrategyName())
            .setStrategyType("default")
            .setStrategyDescription(body.getStrategyDescription())
            .setStrategyTimeout(body.getStrategyTimeout())
            .setStrategyRetryCount(body.getStrategyRetryCount())
            .setServiceCount(body.getModelServiceList().size())
            .setServiceIdList(models.stream().map(ModelServiceData::getId).collect(Collectors.joining(",")))
            .setAuthIdList(models.stream().map(ModelServiceData::getAuthId).collect(Collectors.joining(",")))
            .setServiceCount(body.getModelServiceList().size())
            .setStrategyKey(genStrategyKey(workspaceId, body.getStrategyName()))
            .setTraceId(strategyId);
    }

    private RouterStrategyBaseInfo transformStrategyEntityToVo(RouterStrategyEntity routerStrategy) {
        RouterStrategyBaseInfo routerStrategyBaseInfo = new RouterStrategyBaseInfo();
        BeanUtils.copyProperties(routerStrategy, routerStrategyBaseInfo);

        List<String> serviceIds = Arrays.asList(routerStrategy.getServiceIdList().split(","));

        // 查询 model_name 和 provider_id
        List<ModelServiceBase> modelServiceList = modelServiceMapper.getModelNamesAndProviderIdsByIds(serviceIds);

        Map<String, ModelServiceBase> modelServiceMap = new HashMap<>();
        for (ModelServiceBase data : modelServiceList) {
            modelServiceMap.put(data.getId(), data);
        }

        List<String> providerIds = modelServiceList.stream()
            .map(ModelServiceBase::getProviderId)
            .filter(Objects::nonNull)
            .distinct()
            .collect(Collectors.toList());

        List<ModelServiceProviderDetail> providerList;
        if (providerIds.isEmpty()) {
            log.error("Provider ids is empty. serviceList:{}", routerStrategy.getServiceIdList());
            providerList = new ArrayList<>(0);
        } else {
            providerList = modelServiceMapper.getLogosAndProviderNamesByProviderIds(providerIds);
        }

        Map<String, ModelServiceProvider> providerMap = new HashMap<>();
        for (ModelServiceProviderDetail provider : providerList) {
            providerMap.put(provider.getId(), provider);
        }

        List<ModelServiceRsp> serviceList = serviceIds.stream().map(serviceId -> {
            ModelServiceBase modelData = modelServiceMap.get(serviceId);
            String modelName = null;
            String providerId = null;
            String serviceName = null;

            if (modelData != null) {
                modelName = modelData.getModelName();
                providerId = modelData.getProviderId();
                serviceName = modelData.getServiceName();
            } else {
                log.warn("modelData is null serviceId: {}", serviceId);
            }

            ModelServiceProvider providerData = null;
            String logo = null;
            String providerName = null;

            if (providerId != null) {
                providerData = providerMap.get(providerId);
                if (providerData != null) {
                    logo = providerData.getLogo();
                    providerName = providerData.getProviderName();
                } else {
                    log.warn("providerData is null, providerId: {}", providerId);
                }
            }

            ModelServiceRsp service = new ModelServiceRsp();
            service.setId(serviceId);
            service.setModelName(modelName);
            service.setServiceName(serviceName);
            service.setLogo(logo);
            service.setProviderName(providerName);
            return service;
        }).collect(Collectors.toList());

        routerStrategyBaseInfo.setServiceList(serviceList);
        return routerStrategyBaseInfo;
    }

    private String genStrategyKey(String workspaceId, String strategyName) {
        return String.format("strategy:%s:%s", workspaceId, strategyName);
    }

    public void checkReferencedStrategies(String projectId, String workspaceId, String modelId) {
        List<RouterStrategyEntity> strategyEntities = routerStrategyMapper.queryStrategiesByModelId(projectId, workspaceId, modelId);
        if (!CollectionUtils.isEmpty(strategyEntities)) {
            String strategyNames = strategyEntities.stream().map(RouterStrategyEntity::getStrategyName).collect(Collectors.joining(","));
            log.error("Model service cannot offline or delete (because used by router strategy). strategies: {}", strategyNames);
            throw new AgentStudioException(StudioError.MD_MODEL_FORBID_DELETE_OR_UNPUBLISH, strategyNames);
        }
    }

    public List<ModelStrategyExportEntity> buildModelStrategyExport(String projectId, String workspaceId, List<String> strategyIds) {
        if (org.apache.commons.collections4.CollectionUtils.isEmpty(strategyIds)) {
            return Collections.emptyList();
        }
        try {
            List<RouterStrategyEntity> strategyList = routerStrategyMapper.queryByRouterIds(strategyIds);
            if (org.apache.commons.collections4.CollectionUtils.isEmpty(strategyList)) {
                return Collections.emptyList();
            }
            List<ModelStrategyExportEntity> exportModelStrategyList = new ArrayList<>();
            for (RouterStrategyEntity strategy : strategyList) {
                // 解析策略中关联的模型 ID 列表
                String serviceIdStr = strategy.getServiceIdList();
                if (StringUtils.isBlank(serviceIdStr)) {
                    log.warn("Strategy {} has no associated service IDs", strategy.getId());
                    continue;
                }
                List<String> modelIds = Arrays.asList(serviceIdStr.split(","));
                // 组装导出实体
                List<ModelExportEntity> modelExportEntities = modelServiceMgmtService.buildModelExportEntity(projectId,
                    workspaceId, modelIds, true, false);
                ModelStrategyExportEntity exportEntity = new ModelStrategyExportEntity();
                exportEntity.setModelExportEntity(modelExportEntities);
                exportEntity.setRouterStrategyEntityMetadata(strategy);
                exportModelStrategyList.add(exportEntity);
            }

            return exportModelStrategyList;

        } catch (Exception e) {
            log.error("Failed to build model strategy export. Project: {}", projectId, e);
            throw new AgentStudioException(StudioError.MODEL_EXPORT_DATA);
        }
    }

    public void createRouterStrategy(String projectId, String workspaceId,
        RouterStrategyEntity metadata) {

        // 重名校验
        List<RouterStrategyEntity> entityList = routerStrategyMapper.selectInfoByStrategyName(projectId, workspaceId,
            metadata.getStrategyName());

        if (!entityList.isEmpty()) {
            log.error("Router strategy name is already exist. name:{}", metadata.getStrategyName());
            throw new AgentStudioException(StudioError.ROUTER_STRATEGY_NAME_REPEATED);
        }
        List<String> modelIds = Collections.emptyList();
        if (StringUtils.isNotBlank(metadata.getServiceIdList())) {
            modelIds = Arrays.asList(metadata.getServiceIdList().split(","));
        }
        checkModelServicesStatus(projectId, workspaceId, modelIds);
        // 5. 调用 Manager 层保存到数据库
        modelServiceManager.saveRouterStrategy( metadata);

    }
    public void checkModelServicesStatus(String projectId, String workspaceId, List<String> modelIds) {
        if (org.apache.commons.collections4.CollectionUtils.isEmpty(modelIds)) {
            log.error("Model ID list is empty.");
            throw new AgentStudioException(StudioError.MD_REQUEST_BODY_INVALID_MODEL);
        }

        // 重复性校验
        Set<String> uniqueIds = new HashSet<>(modelIds);
        if (uniqueIds.size() < modelIds.size()) {
            log.error("Duplicate model IDs found in request.");
            throw new AgentStudioException(StudioError.MD_REQUEST_BODY_INVALID);
        }

        // 获取所有可用模型（包括公共免费模型和当前项目私有模型）
        List<ModelServiceData> freeModels = queryFreeModels(uniqueIds);
        List<ModelServiceData> projectModels = modelServiceMapper.queryByIds(uniqueIds, projectId, workspaceId);

        List<ModelServiceData> allModels = new ArrayList<>(freeModels);
        allModels.addAll(projectModels);

        // 3. 校验数量：查出来的数量必须等于传入的数量
        if (allModels.size() < uniqueIds.size()) {
            log.error("Some models do not exist or no permission. Requested: {}, Found: {}", uniqueIds, allModels.size());
            throw new AgentStudioException(StudioError.MD_REQUEST_BODY_INVALID_MODEL_NOT_EXIST);
        }

        // 4. 认证信息校验
        for (ModelServiceData model : allModels) {
            // 如果没有 AuthId，则检查是否属于平台免费模型
            if (StringUtils.isEmpty(model.getAuthId())) {
                boolean isFreePlatformModel = platformProviderId.equals(model.getProviderId())
                    && licenseCtrlService.canUseFreeModel();
                if (!isFreePlatformModel) {
                    log.error("Model auth info is missing. modelId:{} modelName:{}", model.getId(), model.getModelName());
                    throw new AgentStudioException(StudioError.MD_MODEL_SERVICE_AUTH_NOT_EXIST, model.getModelName());
                }
            }
        }
    }
}
