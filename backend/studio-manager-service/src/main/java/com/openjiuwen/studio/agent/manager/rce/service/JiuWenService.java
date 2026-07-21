/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.service;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.models.AskModelReq;
import com.openjiuwen.studio.agent.manager.rce.models.CodeGenerateResultVo;
import com.openjiuwen.studio.agent.manager.service.md.FreeModelService;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;
import java.util.Objects;

/**
 * 功能描述
 *
 */
@Slf4j
@Service("MgJiuWenService")
public class JiuWenService {

    private static final String X_AUTH_TOKEN = "x-auth-token";

    @Autowired
    private WebClient webClient;

    @Autowired
    private AgentRuntimeClient runtimeClient;

    @Autowired
    private ProviderAuthDataMapper authDataMapper;

    @Autowired
    private FreeModelService freeModelService;

    @Value("${agent_runtime_endpoint:}")
    private String runtimeEndpoint;

    @Value("${feign.client.config.agentBuilder.url:}")
    private String agentBuilderEndpoint;

    /**
     * 调用模型
     *
     * @param request 模型请求参数
     * @return 模型响应内容
     */
    public String callModel(AskModelReq request, String workspaceId) {
        if (StringUtils.isEmpty(request.getModelName())) {
            log.error("Model is empty. {}", workspaceId);
            throw new AgentStudioException(StudioError.MODEL_CONFIG_MISS);
        }
        if (request.getModelName().contains("|")) {
            request.setModelName(request.getModelName().split("\\|")[0]);
        }
        ProviderAuthData auth = null;
        if (!freeModelService.isFreeModel(request.getModelName())) {
            auth = authDataMapper.selectByModelId(RequestContextUtils.getRequestProjectId(), workspaceId,
                request.getModelName());

            if (auth == null) {
                log.warn("Not found model auth config. model:{} project:{} workspace:{}", request.getModelName(),
                    RequestContextUtils.getRequestProjectId(), workspaceId);
            }
        }

        ResponseEntity<JSONObject> response = runtimeClient.askModel(RequestContextUtils.getRequestAuthToken(),
            auth == null ? "" : auth.getId(), request);
        String content = response.getBody()
            .getJSONArray(CommonConstant.CHOICES)
            .getJSONObject(0)
            .getJSONObject(CommonConstant.MESSAGE)
            .getString(CommonConstant.CONTENT);
        return Strings.CS.removeEnd(Strings.CS.removeStart(content, "```json"), "```");
    }

    public Object callModelStream(HttpHeaders headers, String projectId, String workspaceId, ChatCompletionRequest chatCompletionRequest) {
        Flux<String> dataFlux = webClient.post()
            .uri(runtimeEndpoint + "/v1/agent-builder/chat/completions?project_id=" + projectId + "&workspace_id="
                + workspaceId + "&refresh=true")
            .contentType(MediaType.APPLICATION_JSON)
            .header(CommonConstant.X_AUTH_TOKEN, Objects.requireNonNull(headers.get(CommonConstant.X_AUTH_TOKEN)).get(0))
            .bodyValue(chatCompletionRequest)
            .retrieve()
            .onStatus(status -> !status.is2xxSuccessful(),
                response -> response.bodyToMono(String.class).flatMap(errorBody -> {
                    // 抛出异常，终止流（不返回任何数据）
                    return Mono.error(new AgentStudioException(StudioError.CALL_MODEL_ERROR));
                }))
            .bodyToFlux(String.class)
            // 对每个chunk进行处理
            .mapNotNull(chunk -> {
                CodeGenerateResultVo response = JsonUtils.json2ObjQuietly(chunk, CodeGenerateResultVo.class);
                if (response == null || response.getChoices() == null || response.getChoices().isEmpty()) {
                    return chunk;
                }
                return response.getChoices().get(0).getDelta().getContent() != null && !response.getChoices().get(0).getDelta().getContent().trim().isEmpty() ? chunk : "";
            })
            .filter(chunk -> chunk != null && !chunk.trim().isEmpty());
        log.info("code generation completed, projectId: {}, workspaceId: {}", projectId, workspaceId);
        return dataFlux;
    }

    public Flux<Map<String, Object>> generatorAgentOrWorkflow(String token, String projectId,
        String agentType, String cid, String workspaceId, Object body) {
        return webClient.post()
            .uri(agentBuilderEndpoint + "/v1/" + projectId + "/" + agentType
                + "/generator/conversations/" + cid + "/chat?workspace_id=" + workspaceId)
            .contentType(MediaType.APPLICATION_JSON)
            .header(CommonConstant.X_AUTH_TOKEN, token)
            .bodyValue(body)
            .accept(MediaType.TEXT_EVENT_STREAM)
            .retrieve()
            .onStatus(status -> !status.is2xxSuccessful(),
                response -> response.bodyToMono(String.class).flatMap(errorBody -> {
                    log.error("generatorAgentOrWorkflow error: {}", errorBody);
                    return Mono.error(new AgentStudioException(StudioError.JIU_WEN_SERVICE_EXCEPTION));
                }))
            .bodyToFlux(String.class)
            .mapNotNull(chunk -> {
                try {
                    return JSONObject.parseObject(chunk);
                } catch (Exception e) {
                    log.warn("Failed to parse SSE chunk: {}", chunk, e);
                    return null;
                }
            });
    }
}
