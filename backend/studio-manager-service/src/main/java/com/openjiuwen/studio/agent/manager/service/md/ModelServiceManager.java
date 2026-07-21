/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.md;

import com.fasterxml.jackson.core.type.TypeReference;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckRsp;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceCondition;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ModelStrategy;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentBuilderClient;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import javax.annotation.PostConstruct;

@Service
@Slf4j
public class ModelServiceManager {
    private static final String SYNC_PLATFORM_MODELS_LOCK = "SYNC_PLATFORM_MODELS_LOCK";

    private static final String SYNC_UPGRADE_MODELS_LOCK = "SYNC_UPGRADE_MODELS_LOCK";

    private static final String REDIS_PREFIX = "model_service_";

    private static final String MODEL_PATH = "model-service/ir/%s";

    @Value("${model.free-model.enable:false}")
    private boolean freeModelEnable;

    @Value("${model.upgrade.sync.enable:false}")
    private boolean upgradeSyncEnable;

    @Value("${model.platform.provider:100}")
    private String platformProviderId;

    @Value("${model.soft.delete.enable:false}")
    private boolean modelSoftDelete;

    @Value("${model.platform.intent_recommendation_models_id:maas-deeseek-v32,185}")
    private String intentModelRecommendation;

    @Autowired
    private ModelServiceMapper modelServiceMapper;

    @Autowired
    private FreeModelServiceMapper freeModelServiceMapper;

    @Autowired
    private MgObsService obsService;

    @Autowired
    private RouterStrategyMapper routerStrategyMapper;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private AgentRuntimeClient runtimeClient;

    @Autowired
    private AgentBuilderClient builderClient;

    @Autowired
    private ProviderAuthDataMapper authDataMapper;

    @PostConstruct
    public void postConstruct() {
        CompletableFuture.runAsync(this::startSyncTasks);
    }

    void startSyncTasks() {
        syncPlatformModelsToObs();
        if (!upgradeSyncEnable) {
            log.info("model.upgrade.sync.enable value is false.");
            return;
        }
        Executors.newSingleThreadScheduledExecutor()
            .scheduleAtFixedRate(this::syncUpgradeModels, 1, 5, TimeUnit.MINUTES);
    }

    void syncUpgradeModels() {
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(SYNC_UPGRADE_MODELS_LOCK);
            if (lock.tryLock(Duration.ofSeconds(30))) {
                List<ModelServiceBase> models = modelServiceMapper.queryNotSyncModels();
                syncModelsToObsAndRedis(models);
                for (ModelServiceBase model : models) {
                    modelServiceMapper.updateSyncStatus(model.getId());
                }

                syncSysPlatformModels(modelServiceMapper.queryAllPlatformModels(platformProviderId));
            } else {
                log.warn("SyncUpgradeModels Fail get {} lock.", SYNC_UPGRADE_MODELS_LOCK);
            }
        } catch (Exception e) {
            log.error("Sync UpgradeModels models to obs exception.", e);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    void syncModelsToObsAndRedis(List<ModelServiceBase> models) {
        try {
            int count = 0;
            for (ModelServiceBase model : models) {
                saveModelInfoToObsAndRedis("model", model.getId(), model);
                ++count;
                if (count % 50 == 0) {
                    Thread.sleep(1000L); // 避免请求过多，导致obs服务异常
                }
            }
            log.info("Success sysnc {} models to obs.", count);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Sync models interrupted.", e);
        } catch (Exception e) {
            log.error("Fail sync models to obs and redis.", e);
        }
    }

    void syncSysPlatformModels(List<ModelServiceBase> models) {
        try {
            String path = "modelarts-models/" + platformProviderId + ".json";
            if (!models.isEmpty()) {
                String content = JsonUtils.encode(models);
                obsService.putObject(path, content);
            }
        } catch (Exception e) {
            log.error("Fail save modelarts models id.");
        }
    }

    public void syncPlatformModelsToObs() {
        RedisLock lock = null;
        try {
            Thread.sleep(60000L);
            lock = redisClient.getLock(SYNC_PLATFORM_MODELS_LOCK);
            if (lock.tryLock(Duration.ofSeconds(30))) {
                syncModelsToObsAndRedis(modelServiceMapper.queryAllPlatformModels(null));
                syncSysPlatformModels(modelServiceMapper.queryAllPlatformModels(platformProviderId));
            } else {
                log.warn("Fail get {} lock.", SYNC_PLATFORM_MODELS_LOCK);
            }
        } catch (Exception e) {
            log.error("Sync platform models to obs exception.", e);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    public void createModelService(ModelServiceBase model) {
        modelServiceMapper.insert(model);
        saveModelInfoToObsAndRedis("model", model.getId(), model);
    }

    public void updateModelService(ModelServiceBase model) {
        modelServiceMapper.updateModelService(model);
        saveModelInfoToObsAndRedis("model", model.getId(), model);
    }

    public void saveModelInfoToObsAndRedis(String type, String id, Object model) {
        String path = String.format(MODEL_PATH, id + ".json");
        String content = JsonUtils.encode(new ModelStrategy().setType(type).setData(model));
        obsService.putObject(path, content);
        redisClient.set(REDIS_PREFIX + id, content);
    }

    public void deleteModelService(String id) {
        // 数据删除备份
        if (modelSoftDelete) {
            ModelServiceBase modelServiceBase = modelServiceMapper.queryModelServiceDetail(id);
            modelServiceBase.setLastUpdatedDate(System.currentTimeMillis());
            modelServiceMapper.insertBackup(modelServiceBase);
        }

        modelServiceMapper.deleteById(id);
        String path = String.format(MODEL_PATH, id + ".json");
        try {
            obsService.deleteObject(path);
        } catch (Exception e) {
            log.warn("Delete model service config fail. path:{}", path, e);
        }
        redisClient.delete(REDIS_PREFIX + id);
    }

    public Set<String> queryAllAvailableServiceIds(String projectId, String workspaceId) {
        return queryAvailableServices(projectId, workspaceId, null, true).stream()
            .map(ModelServiceData::getId)
            .collect(Collectors.toSet());
    }

    public List<ModelServiceData> queryAvailableServices(String projectId, String workspaceId, String modelType,
        boolean containRouter) {
        ModelServiceCondition condition = new ModelServiceCondition().setProjectId(projectId)
            .setWorkspaceId(workspaceId).setFreeProviderId(platformProviderId);
        if (StringUtils.isNotBlank(modelType)) {
            condition.setModelType(modelType);
        }

        List<ModelServiceData> models = new ArrayList<>(modelServiceMapper.queryAvailableServices(condition));
        models.addAll(modelServiceMapper.queryPublicAvailableServices(condition));
        if (freeModelEnable) {
            models.addAll(freeModelServiceMapper.queryAllFreeModels(new ModelServiceCondition()));
        }
        if (containRouter) {
            List<RouterStrategyEntity> routerStrategies = routerStrategyMapper.selectInfoByStrategyName(projectId,
                workspaceId, null);
            for (RouterStrategyEntity routerStrategy : routerStrategies) {
                ModelServiceData data = new ModelServiceData();
                data.setId(routerStrategy.getId())
                    .setServiceName(routerStrategy.getStrategyName())
                    .setModelName(routerStrategy.getStrategyName())
                    .setModelType("LLM")
                    .setStatus("success")
                    .setPublishStatus("online");
                data.setAuthId("");
                models.add(data);
            }
        }
        List<String> intentModelList = Arrays.asList(intentModelRecommendation.split(","));
        if (!intentModelList.isEmpty()) {
            models = Stream.concat(
                            models.stream().filter(model -> model.getId().equals(intentModelList.get(0))),
                            models.stream().filter(model -> !model.getId().equals(intentModelList.get(0)))
                    )
                    .collect(Collectors.toList());
        }

        return models;
    }

    /**
     * 获取模型拓展字段
     * 兼容1.0版本
     *
     * @param id 模型 id
     * @param projectId projectId
     * @param safetyBarrier 是否开启安全护栏
     * @return 模型拓展字段
     */
    public Map<String, Object> parseModelExtension(String id, String projectId, String workspaceId,
        boolean safetyBarrier) {
        Map<String, Object> extension = new HashMap<>();
        extension.put("safetyBarrier", safetyBarrier);
        ModelServiceBase base = modelServiceMapper.queryById(id);
        if (Objects.isNull(base)) {
            log.warn("Fail query model service info. id:{}", id);
            return extension;
        }
        if (!base.isPublic() && !projectId.equals(base.getProjectId()) && !"SYSTEM".equals(base.getProjectId())) {
            log.warn("Model project is not permission. userProject:{} dataProject:{}", projectId, base.getProjectId());
            return extension;
        }
        if (!base.isPublic() && !workspaceId.equals(base.getWorkspaceId()) && !"SYSTEM".equals(base.getWorkspaceId())) {
            log.warn("Model Workspace is not permission. userWorkspace:{} dataWorkspace:{}", workspaceId,
                base.getWorkspaceId());
            return extension;
        }
        String queryProjectId = base.isPublic() ? base.getProjectId() : projectId;
        String queryWorkspaceId = base.isPublic() ? base.getWorkspaceId() : workspaceId;
        ProviderAuthData auth = authDataMapper.selectByMetaId(queryProjectId, queryWorkspaceId, base.getAuthMetadataId());

        // 当前拓展字段只保留deploymentId，其余字段引擎从obs中获取
        extension.put("authId", auth == null ? "" : auth.getId());
        extension.put("deploymentId", base.getId());
        if (StringUtils.isNotEmpty(base.getSystemPrompt())) {
            extension.put("systemPrompt", base.getSystemPrompt());
        }
        return extension;
    }

    public void saveRouterStrategy(RouterStrategyEntity entity) {
        routerStrategyMapper.insert(entity);
        saveModelInfoToObsAndRedis("router", entity.getId(), entity);
    }

    public void updateRouterStrategy(RouterStrategyEntity entity) {
        routerStrategyMapper.update(entity);
        saveModelInfoToObsAndRedis("router", entity.getId(), entity);
    }

    public void deleteRouterStrategy(String id) {
        routerStrategyMapper.deleteById(id);
        String path = String.format(MODEL_PATH, id + ".json");
        try {
            obsService.deleteObject(path);
        } catch (Exception e) {
            log.warn("Delete model service config fail. path:{}", path, e);
        }
        redisClient.delete(REDIS_PREFIX + id);
    }

    public void backupRouterStrategy(String id) {
        RouterStrategyEntity routerStrategyEntity = routerStrategyMapper.selectInfoById(id);
        routerStrategyEntity.setLastUpdatedDate(System.currentTimeMillis());
        routerStrategyMapper.insertBackup(routerStrategyEntity);
    }

    @SuppressWarnings("unchecked")
    public ModelServiceCheckRsp checkModelAvailable(String projectId, String modelName, String modelType,
        String modelApiUrl, String interfaceProtocol, String authType, Object authInfo, Boolean encrypted) {

        ModelServiceCheckReq req = new ModelServiceCheckReq().setModelType(modelType)
                .setModelName(modelName)
                .setApiUrl(modelApiUrl)
                .setInterfaceProtocol(interfaceProtocol)
                .setAuthType(authType);

        if (authInfo instanceof String) {
            String authStr = authInfo.toString();
            if (StringUtils.isBlank(authStr)) {
                authStr = "{}";
            }
            Map<String, String> authMap = JsonUtils.decode(authStr,
                    new TypeReference<Map<String, String>>() {
                    });
            if (!encrypted) {
                for (Map.Entry<String, String> entry : authMap.entrySet()) {
                    String key = entry.getKey();
                    String value = entry.getValue();
                    String encryptedValue = CryptoUtils.encrypt(value);
                    authMap.put(key, encryptedValue);
                }
            }
            req.setAuthInfo(authMap);
        } else if (authInfo instanceof Map<?, ?>) {
            Map<String, String> authMap = (Map<String, String>) authInfo;
            if (!encrypted) {
                for (Map.Entry<String, String> entry : authMap.entrySet()) {
                    String value = entry.getValue();
                    String encryptedValue = CryptoUtils.encrypt(value);
                    entry.setValue(encryptedValue);
                }
            }
            req.setAuthInfo(authMap);
        } else {
            return new ModelServiceCheckRsp().setSuccess(true);
        }

        ModelServiceCheckRsp checkRsp;
        try {
            checkRsp = builderClient.modelServiceAvailableCheck(RequestContextUtils.getRequestAuthToken(), projectId, req)
                    .getBody();
        } catch (Exception e) {
            log.error("Call model service check fail. modelName:{}, msg: {}", modelName, e.getMessage());
            throw new AgentStudioException(StudioError.CALL_MODEL_ERROR, e);
        }

        return checkRsp;
    }

    public AgentStudioException createAgentStudioException(int statusCode, String message) {
        if (401 == statusCode) {
            if (message.contains("not have access")) {
                return null;
            }
            return new AgentStudioException(StudioError.MD_PROVIDER_AUTH_DATA_INVALID,
                Collections.singletonList(message));
        }
        if (404 == statusCode) {
            if (message.toLowerCase(Locale.ROOT).contains("invalid model")) {
                return new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_EXIST,
                    Collections.singletonList(message));
            }
        }
        return new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE, Collections.singletonList(message));
    }

    public void checkProviderAuth(String projectId, String workspaceId, String authType, Object authInfo,
        String providerId, boolean isPlatform) {
        List<ModelServiceBase> modelServiceBases = modelServiceMapper.queryByProviders(projectId, workspaceId,
            providerId);
        if (modelServiceBases.isEmpty()) {
            return;
        }

        ModelServiceCheckRsp rsp = checkModelAvailable(projectId, modelServiceBases.get(0).getModelName(),
            modelServiceBases.get(0).getModelType(), modelServiceBases.get(0).getApiUrl(),
            modelServiceBases.get(0).getInterfaceProtocol(), authType, authInfo, false);
        if (rsp == null || rsp.isSuccess()) {
            // 供应商鉴权配置校验通过、不通过 都不再更新模型的status
            return;
        }

        if (isPlatform && rsp.getStatusCode() != 401 && rsp.getStatusCode() != 403) {
            // 系统默认供应商, 访问失败切非4XX返回, 应是模型问题, 而非认证信息异常, check成功返回
            return;
        }

        if (rsp.getReason() != null && rsp.getReason().contains("ModelArts.81004")) {
            // maas 模型，未开通服务。鉴权配置是正确的
            return;
        }
        if (isPlatform || rsp.getStatusCode() == 401 || rsp.getStatusCode() == 403) {
            log.warn("Auth config is invalid. {}", rsp.getReason());
            throw new AgentStudioException(StudioError.MD_PROVIDER_AUTH_DATA_INVALID,
                Collections.singletonList(rsp.getReason()));
        }
        log.warn("Auth config is invalid. or mode is invalid. {}", rsp.getReason());
        throw new AgentStudioException(StudioError.MD_MODEL_OR_AUTH_NOT_INVALID,
            Collections.singletonList(rsp.getReason()));
    }

    /**
     * 根据模型id列表，查询当前租户下的所有模型信息，包括公共模型
     *
     */
    public List<ModelServiceBase> queryAllModelByIds(String projectId, String workspaceId, Set<String> modelIds) {
        List<ModelServiceBase> modelServiceBases = modelServiceMapper.queryAllModelByIds(modelIds);
        List<ModelServiceBase> models = modelServiceBases.stream().filter(model -> {
            if (Strings.CS.equals(model.getModelDeployType(), "PRIVATE-INTEGRATION")) {
                return Strings.CS.equals(projectId, model.getProjectId()) && Strings.CS.equals(workspaceId,
                    model.getWorkspaceId());
            }
            return true;
        }).toList();
        models = new ArrayList<>(models);
        if (freeModelEnable) {
            List<ModelServiceData> freeModels = freeModelServiceMapper.queryAllFreeModels(new ModelServiceCondition());
            for (ModelServiceData data : freeModels) {
                if (modelIds.contains(data.getId())) {
                    models.add(data);
                }
            }
        }
        return models;
    }
}


