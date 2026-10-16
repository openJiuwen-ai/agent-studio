/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.service;

import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.constant.CommonConstant;
import com.openjiuwen.studio.prompt.engineering.dto.InvokeResp;
import com.openjiuwen.studio.prompt.engineering.dto.ModelListVo;
import com.openjiuwen.studio.prompt.engineering.dto.ModelServiceInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBody;
import com.openjiuwen.studio.prompt.engineering.entity.PePrompt;
import com.openjiuwen.studio.prompt.engineering.enums.Source;
import com.openjiuwen.studio.prompt.engineering.mapper.PeTaskMapper;
import com.openjiuwen.studio.prompt.engineering.remote.ClientTemplate;
import com.openjiuwen.studio.prompt.engineering.service.model.ModelServiceCollection;
import com.openjiuwen.studio.prompt.engineering.service.model.PromptModelService;
import com.openjiuwen.studio.prompt.engineering.utils.PromptUtil;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;
import org.springframework.web.client.ResourceAccessException;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import javax.annotation.Resource;

/**
 * ModelManagerService
 *
 */
@Component
@Slf4j
public class ModelManagerService {
    private static final Logger LOGGER = LoggerFactory.getLogger(ModelManagerService.class);

    private static final String GET_AVAILABNLE_MODEL = "/model-manager/available/model-services";

    private static final String GET_USER_MODEL = "/model-manager/integration/providers";

    private static final String GET_PRESET_MODEL = "/model-manager/platform/providers";

    private static final String API_ID = "textCompletion";

    private static final String USE_RANGE = "available";

    @Resource
    private ModelServiceCollection modelServiceCollection;

    @Resource(name = "remoteClientTemplate")
    private ClientTemplate clientTemplate;

    @Value("${model.free-model.enable}")
    private boolean freeModelEnable;

    @Value("${model.free-model.cfg}")
    private String freeModelCfg;

    @Value("${model.manager.server.endpoint}")
    private String modelManagerServerEndpoint;

    @Value("${manager.server.baseurl}")
    private String managerServerBaseurl;

    @Value("${env.type}")
    private String envType;

    @Resource
    private PromptService promptService;

    @Resource
    private PromptModelService<?> promptModelService;

    @Resource
    private PeTaskMapper peTaskMapper;

    @Resource
    private PromptObsService promptObsService;

    private static final String IMAGE_FOLDER = "image";

    @Autowired
    private I18nUtil i18nUtil;

    /**
     * COM-02：prompt-engineering 限时模型调用专用执行器（Abort 拒绝由调用点 catch 转业务错误）
     */
    @Autowired
    @Qualifier("promptModelCallExecutor")
    private ThreadPoolTaskExecutor promptModelCallExecutor;

    private boolean isFreeModel(String model) {
        if (model == null || model.isEmpty()) {
            return false;
        }

        String[] models = freeModelCfg.split(",");
        for (String item : models) {
            String modelName = item.split("#")[0];
            if (Strings.CS.equals(modelName, model)) {
                return true;
            }
        }
        return false;
    }


    public InvokeResp callModel(String projectId, String workspaceId, PromptBody body) {
        if (!Boolean.TRUE.equals(peTaskMapper.isIdExist(body.getTaskId(), workspaceId))) {
            throw new AgentStudioException(StudioError.TASK_ID_IS_NOT_EXIST, body.getTaskId());
        }

        String publishStatus = peTaskMapper.queryPublishStatusById(body.getModelConfig().getId(), body.getModel());
        String status = peTaskMapper.queryStatusById(body.getModelConfig().getId(), body.getModel());
        if (freeModelEnable && isFreeModel(body.getModelConfig().getId())) {
            log.info("free model is called, skip status and publish status validation: {}", body.getModel());
        }
        else if (!CommonConstant.MODEL_PUBLISH_TYPE.equals(publishStatus) && !CommonConstant.MODEL_STATUS.equals(status)) {
            log.error("Model status verification failed.");
            throw new AgentStudioException(StudioError.MODEL_STATUS_ERROR, body.getModel());
        }

        PromptUtil.validateModelConfig(body.getModelConfig());
        body.setModelType(
            StringUtils.isEmpty(body.getModelType()) ? CommonConstant.AGENT_BUILDER_MODEL_TYPE : body.getModelType());

        // 异步任务中，设置了一个1分钟的超时时间
        String xAuthToken = RequestContextUtils.getRequestAuthToken();
        String creator = RequestContextUtils.getRequestUserName();
        // COM-02: 迁移自 commonPool 至 prompt-engineering 专用限时模型调用执行器（超时语义保留在调用点）。
        // AbortPolicy 拒绝发生在提交时（supplyAsync 在 try 外会绕过下方异常分支），故提交纳入 catch，
        // 映射为已登记的稳定业务错误（429 语义，不新增错误码）。
        CompletableFuture<InvokeResp> future;
        try {
            future = CompletableFuture.supplyAsync(
                () -> promptModelService.queryModelCenter(workspaceId, body, xAuthToken, projectId),
                promptModelCallExecutor);
        } catch (java.util.concurrent.RejectedExecutionException e) {
            // 专用池饱和（core=2/max=4/queue=50 全满）：模型调用未被受理
            log.error("Prompt model call executor rejected (pool saturated). workspaceId:{}", workspaceId, e);
            throw new AgentStudioException(StudioError.MD_INVOKE_TOO_MANY_REQUEST);
        }

        // 执行调用LLM逻辑
        try {
            InvokeResp invokeResp = future.get(1, TimeUnit.MINUTES);
            invokeResp.setFileInfo(promptService.getFileInfoVoByFileId(body.getFileId()));
            if (!Source.HORIZONTAL.name().equals(body.getSource())) {
                PePrompt pePrompt = PePrompt.builder()
                    .id(UUID.randomUUID().toString())
                    .question(body.getQuestion())
                    .taskId(body.getTaskId())
                    .model(body.getModel())
                    .modelConfig(body.getModelConfig())
                    .source(body.getSource())
                    .answer(invokeResp.getResult())
                    .creator(creator)
                    .updater(creator)
                    .workspaceId(workspaceId)
                    .build();
                promptService.saveHistory(pePrompt,
                    !CollectionUtils.isEmpty(body.getVariables()) ? body.getVariables() : new ArrayList<>());
            }
            return invokeResp;
        } catch (InterruptedException e) {
            // 调用LLM接口异常中断
            throw new AgentStudioException(StudioError.CALL_LLM_INTERRUPTED);
        } catch (ExecutionException e) {
            // 调用LLM接口执行时异常
            log.error("Call model exception. ", e);
            throw new AgentStudioException(StudioError.CALL_LLM_EXECUTION_ERROR);
        } catch (TimeoutException e) {
            // 调用LLM接口超时异常
            throw new AgentStudioException(StudioError.CALL_LLM_TIMEOUT);
        }
    }


    public ModelListVo listModels(String projectId, String useRange, String workspaceId) {
        try {
            List<ModelServiceInfo> modelServiceInfoList = new ArrayList<>();
            String token = RequestContextUtils.getRequestAuthToken();
            List<ModelServiceInfo> userModels = getUserModels(projectId, workspaceId, token);
            if (!CollectionUtils.isEmpty(userModels)) {
                modelServiceInfoList.addAll(userModels);
            }

            ModelListVo modelListVo = new ModelListVo();
            modelListVo.setModelServiceInfoList(modelServiceInfoList);
            return modelListVo;
        } catch (ResourceAccessException e) {
            log.error("Failed to get modelList. error: {}", e.getMessage());
            throw new AgentStudioException(StudioError.QUERY_MODEL_LIST_ERROR);
        }
    }

    private List<ModelServiceInfo> getUserModels(String projectId, String workspaceId, String token) {
        List<ModelServiceInfo> modelServiceInfoList = new ArrayList<>();
        ResponseEntity<JSONObject> userModelResponse;
        try {
            userModelResponse = clientTemplate.getForEntity(
                managerServerBaseurl + "/v1/" + projectId + GET_AVAILABNLE_MODEL + "?workspace_id=" + workspaceId,
                token, JSONObject.class);

            // 获取大模型的返回值
            if (userModelResponse == null || userModelResponse.getBody() == null) {
                LOGGER.error("call model getUserModels failed for projectId: {}", projectId);
                throw new AgentStudioException(StudioError.MODEL_MANAGER_SERVICE_EXCEPTION, projectId);
            }
            LOGGER.info("ModelService.getUserModels success");
        } catch (Exception exception) {
            log.error("failed to get user modelList, projectId: {}.", projectId);
            throw new AgentStudioException(StudioError.FAILED_GET_USER_MODEL_LIST, projectId);
        }
        if (!userModelResponse.getStatusCode().is2xxSuccessful()) {
            log.error("Get user model list from model manager server error! response:{}", userModelResponse);
            return new ArrayList<>();
        }
        if (Objects.isNull(userModelResponse.getBody())) {
            log.info("get user modelList is null");
            return new ArrayList<>();
        }
        JSONArray userServices = userModelResponse.getBody().getJSONArray("data");
        if (!Objects.isNull(userServices)) {
            for (int i = 0; i < userServices.size(); i++) {
                ModelServiceInfo modelServiceInfo = new ModelServiceInfo();
                modelServiceInfo.setProjectId(projectId);
                modelServiceInfo.setName(userServices.getJSONObject(i).getString("service_name"));
                modelServiceInfo.setDeploymentId(userServices.getJSONObject(i).getString("id"));
                modelServiceInfo.setEndpoint(managerServerBaseurl);
                modelServiceInfo.setModelType(userServices.getJSONObject(i).getString("model_type"));
                modelServiceInfo.setIsPreset(false);
                modelServiceInfoList.add(modelServiceInfo);
            }
        }
        return modelServiceInfoList;
    }

    private List<ModelServiceInfo> getPresetModels(String projectId, String token, String workspaceId) {
        List<ModelServiceInfo> modelServiceInfoList = new ArrayList<>();
        ResponseEntity<JSONObject> presetModelResponse;
        try {
            presetModelResponse = clientTemplate.getForEntity(
                managerServerBaseurl + "/v1/" + projectId + GET_PRESET_MODEL + "?workspace_id=" + workspaceId, token,
                JSONObject.class);
        } catch (Exception exception) {
            log.error("failed to get preset modelList, projectId: {}.", projectId);
            throw new AgentStudioException(StudioError.FAILED_GET_PRESET_MODEL_LIST, projectId);
        }
        if (!presetModelResponse.getStatusCode().is2xxSuccessful()) {
            log.error("get preset modelList from model manager server error! response:{}", presetModelResponse);
            return new ArrayList<>();
        }
        if (Objects.isNull(presetModelResponse.getBody())) {
            log.info("get preset modelList is null");
            return new ArrayList<>();
        }
        JSONArray presetServices = presetModelResponse.getBody().getJSONArray("services");
        log.debug("get preset model list from model manager server {}", presetServices);
        if (!Objects.isNull(presetServices)) {
            for (int i = 0; i < presetServices.size(); i++) {
                ModelServiceInfo modelServiceInfo = new ModelServiceInfo();
                modelServiceInfo.setProjectId(projectId);
                modelServiceInfo.setName(presetServices.getJSONObject(i).getString("service_name"));
                modelServiceInfo.setDeploymentId(presetServices.getJSONObject(i).getString("service_id"));
                modelServiceInfo.setEndpoint(managerServerBaseurl);
                modelServiceInfo.setModelType(CommonConstant.AGENT_BUILDER_MODEL_TYPE);
                modelServiceInfo.setIsPreset(true);
                modelServiceInfoList.add(modelServiceInfo);
            }
        }
        return modelServiceInfoList;
    }
}
