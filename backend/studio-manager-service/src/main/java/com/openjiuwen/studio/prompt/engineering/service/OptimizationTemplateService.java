/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.dto.TemplateOptimizeProgressResp;
import com.openjiuwen.studio.prompt.engineering.dto.TemplateOptimizeReq;
import com.openjiuwen.studio.prompt.engineering.dto.TemplateOptimizeResp;
import com.openjiuwen.studio.prompt.engineering.enums.ResponseCode;
import com.openjiuwen.studio.prompt.engineering.remote.ClientTemplate;
import com.openjiuwen.studio.prompt.engineering.utils.JsonUtil;

import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;

import java.util.Collections;
import java.util.Objects;

/**
 * 九问提示词自优化接口服务
 *
 */
@Slf4j
@Service
public class OptimizationTemplateService {
    private static final String TEMPLATES_OPTIMIZATION_CREATE_API = "/v1/prompt/templates_optimization/jobs";

    private static final String TEMPLATES_OPTIMIZATION_PROGRESS_API = "/v1/prompt/templates_optimization/jobs/%s";

    private static final String TEMPLATES_OPTIMIZATION_STOP_API = "/v1/prompt/templates_optimization/jobs/%s/stop";

    private static final String TEMPLATES_OPTIMIZATION_RESTART_API =
        "/v1/prompt/templates_optimization/jobs/%s/restart";

    private static final String TEMPLATES_OPTIMIZATION_DELETE_API = "/v1/prompt/templates_optimization/jobs/%s";

    private static final Logger logger = LoggerFactory.getLogger(OptimizationTemplateService.class);

    @Value("${agent_builder_endpoint:}")
    private String agentBuilderEndpoint;

    @Resource(name = "remoteClientTemplate")
    private ClientTemplate clientTemplate;

    public TemplateOptimizeResp createOptimization(TemplateOptimizeReq req, String token) {
        try {
            log.info("createOptimization req: {}", JsonUtil.object2Json(req));
            ResponseEntity<TemplateOptimizeResp> response =
                clientTemplate.postForEntity(agentBuilderEndpoint + TEMPLATES_OPTIMIZATION_CREATE_API, token,
                    JsonUtil.object2Json(req), TemplateOptimizeResp.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                logger.error("Create optimization task from jiuwen server error! response:{}", response);
                throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_FROM_JIUWEN_SERVICE_ERROR);
            }
            TemplateOptimizeResp templateOptimizeResp = response.getBody();
            if (Objects.isNull(templateOptimizeResp)) {
                log.error("Create optimization task resp is null");
                throw new AgentStudioException(StudioError.CREATE_OPTIMIZATION_TASK_RESP_NULL);
            }
            if (templateOptimizeResp.getCode() != ResponseCode.OK.getCode()) {
                throw new AgentStudioException(StudioError.OPTIMIZE_TEMPLATE_FAILED, Collections.singletonList(
                    templateOptimizeResp.getMessage()));
            }
            return templateOptimizeResp;
        } catch (ResourceAccessException e) {
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public TemplateOptimizeResp changeOptimization(String jiuwenTaskId, boolean ifRestart) {
        try {
            String url = ifRestart ? TEMPLATES_OPTIMIZATION_RESTART_API : TEMPLATES_OPTIMIZATION_STOP_API;
            log.info("change jiuwen optimization taskId: {}", jiuwenTaskId);
            ResponseEntity<TemplateOptimizeResp> response =
                clientTemplate.postForEntity(agentBuilderEndpoint + String.format(url, jiuwenTaskId), RequestContextUtils.getRequestAuthToken(),
                    null, TemplateOptimizeResp.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                logger.error("Change optimization task from jiuwen server error! response:{}", response);
                throw new AgentStudioException(StudioError.OPTIMIZATION_TASK_OPERATION_FAILED);
            }
            TemplateOptimizeResp templateOptimizeResp = response.getBody();
            if (Objects.isNull(templateOptimizeResp)) {
                log.error("Create optimization task resp is null");
                throw new AgentStudioException(StudioError.CREATE_OPTIMIZATION_TASK_RESP_NULL);
            }
            if (templateOptimizeResp.getCode() != ResponseCode.OK.getCode()) {
                throw new AgentStudioException(StudioError.OPTIMIZE_TEMPLATE_FAILED, Collections.singletonList(
                    templateOptimizeResp.getMessage()));
            }
            return templateOptimizeResp;
        } catch (ResourceAccessException e) {
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public TemplateOptimizeResp deleteOptimization(String jiuwenTaskId) {
        try {
            log.info("delete jiuwen optimization taskId: {}", jiuwenTaskId);
            ResponseEntity<TemplateOptimizeResp> response = clientTemplate.deleteForEntity(
                agentBuilderEndpoint + String.format(TEMPLATES_OPTIMIZATION_DELETE_API, jiuwenTaskId),
                    RequestContextUtils.getRequestAuthToken(), TemplateOptimizeResp.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                logger.error("Delete optimization task from jiuwen server error! response:{}", response);
                throw new AgentStudioException(StudioError.DELETE_OPTIMIZATION_TASK, response);
            }
            TemplateOptimizeResp templateOptimizeResp = response.getBody();
            if (Objects.isNull(templateOptimizeResp)) {
                log.error("Create optimization task resp is null");
                throw new AgentStudioException(StudioError.CREATE_OPTIMIZATION_TASK_RESP_NULL);
            }
            if (templateOptimizeResp.getCode() != ResponseCode.OK.getCode()) {
                throw new AgentStudioException(StudioError.OPTIMIZE_TEMPLATE_DELETE_FAILED);
            }
            return templateOptimizeResp;
        } catch (ResourceAccessException e) {
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }

    public TemplateOptimizeProgressResp getOptimizationProgress(String jiuwenTaskId, String token) {
        try {
            log.info("getOptimizationProgress jiuwenTaskId: {}", jiuwenTaskId);
            ResponseEntity<JSONObject> response = clientTemplate.getForEntity(
                agentBuilderEndpoint + String.format(TEMPLATES_OPTIMIZATION_PROGRESS_API, jiuwenTaskId), token,
                JSONObject.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                logger.error("Get optimization task progress from jiuwen server error! response:{}", response);
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            if (Objects.isNull(response.getBody())) {
                log.info("get optimization task progress is null");
                throw new AgentStudioException(StudioError.GET_OPTIMIZATION_TASK);
            }
            return JSON.toJavaObject(response.getBody(), TemplateOptimizeProgressResp.class);
        } catch (ResourceAccessException e) {
            throw new AgentStudioException(StudioError.OPTIMIZATION_TEMPLATE_SERVICE_ACCESS_FAILED);
        }
    }
}
