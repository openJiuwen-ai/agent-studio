/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.alibaba.fastjson2.JSONArray;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListPluginsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.PluginListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.nl.KnowledgeList;
import com.openjiuwen.studio.agent.manager.dto.nl.NLChatReq;
import com.openjiuwen.studio.agent.manager.dto.nl.NLResource;
import com.openjiuwen.studio.agent.manager.dto.nl.PluginList;
import com.openjiuwen.studio.agent.manager.dto.nl.PluginResource;
import com.openjiuwen.studio.agent.manager.dto.nl.WorkflowList;
import com.openjiuwen.studio.agent.manager.dto.nl.mapper.NLResourecModelMapper;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.entity.md.ProviderAuthData;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.manager.service.JiuwenRuntimeI18nService;
import com.openjiuwen.studio.agent.manager.service.WorkflowManagementService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.plugin.PluginService;

import io.swagger.annotations.ApiImplicitParam;
import io.swagger.annotations.ApiImplicitParams;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@Validated
@Slf4j
@RequiredArgsConstructor(onConstructor_ = {@Autowired})
public class JiuwenServiceProxyController {
    private final JiuWenService jiuWenService;

    private final ModelServiceManager modelManager;

    private final ProviderAuthDataMapper providerAuthDataMapper;

    private final KnowledgeBaseServiceImpl knowledgeBaseService;

    private final PluginService pluginService;

    private final WorkflowManagementService workflowManagementService;

    private final JiuwenRuntimeI18nService jiuwenRuntimeI18nService;

    @ApiOperation(value = "run agent", nickname = "generatorAgentOrWorkflow", notes = "运行知识型Agent",
        response = Object.class, tags = {"JiuwenRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = Object.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @ApiImplicitParams(value = {
        @ApiImplicitParam(name = "project_id", value = "项目ID", required = true, paramType = "path", dataType = "string"),
        @ApiImplicitParam(name = "agent_type", value = "Agent类型，仅支持 agents（NL2智能体生成）/ workflows（NL2工作流生成）",
            required = true, paramType = "path", dataType = "string", allowableValues = "agents,workflows"),
        @ApiImplicitParam(name = "cid", value = "会话ID", required = true, paramType = "path", dataType = "string"),
        @ApiImplicitParam(name = "workspace_id", value = "空间ID", required = true, paramType = "query", dataType = "string")
    })
    @PostMapping("/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat")
    public Object generatorAgentOrWorkflow(@PathVariable("project_id") String projectId,
        @PathVariable("agent_type") String agentType, @PathVariable("cid") String cid,
        @RequestParam("workspace_id") String workspaceId, @RequestBody @Valid NLChatReq body) {
        String token = RequestContextUtils.getRequestAuthToken();
        checkPermission(body, projectId, workspaceId);

        NLResource resource = assembleBodyResource(projectId, workspaceId);
        body.setResource(resource);

        Flux<Object> flux = jiuWenService.generatorAgentOrWorkflow(token, projectId, agentType, cid, workspaceId, body).cast(Object.class);
        return wrapToSse(flux);
    }

    private NLResource assembleBodyResource(String projectId, String workspaceId) {
        NLResource resource = new NLResource();

        try {
            ListKnowledgeBasesQo listKnowledgeBasesQo = new ListKnowledgeBasesQo();
            listKnowledgeBasesQo.setWorkspaceId(workspaceId);
            listKnowledgeBasesQo.setOffset(0);
            listKnowledgeBasesQo.setLimit(99);
            ListKnowledgeBasesResponseBody listKnowledgeBasesResponse = knowledgeBaseService.listKnowledgeBases(
                projectId, listKnowledgeBasesQo);
            KnowledgeList knowledgeList = new KnowledgeList();
            if (listKnowledgeBasesResponse != null) {
                knowledgeList.setItems(
                    NLResourecModelMapper.INSTANCE.toKnowledgeResources(listKnowledgeBasesResponse.getItems()));
            } else {
                knowledgeList.setItems(Collections.emptyList());
            }
            resource.setKnowledgeBase(knowledgeList);

            ListPluginsQo listPluginsQo = new ListPluginsQo();
            listPluginsQo.setWorkspaceId(workspaceId);
            listPluginsQo.setType(ToolType.ALL.type);
            listPluginsQo.setOffset(0);
            listPluginsQo.setLimit(200);
            PluginListRsp listPluginsRsp = pluginService.listPlugins(projectId, listPluginsQo);

            PluginList pluginList = new PluginList();
            if (listPluginsRsp != null) {
                List<PluginResource> pluginResources = JSONArray.parseArray(
                    JSONArray.toJSONString(listPluginsRsp.getPluginList()), PluginResource.class);
                pluginList.setPluginList(pluginResources);
            } else {
                pluginList.setPluginList(Collections.emptyList());
            }
            resource.setPlugins(pluginList);

            ListWorkflowLastVersionsQo listWorkflowLastVersionsQo = new ListWorkflowLastVersionsQo();
            listWorkflowLastVersionsQo.setOffset(0);
            listWorkflowLastVersionsQo.setLimit(99);
            WorkflowVersionListRsp workflowVersionListRsp = workflowManagementService.listWorkflowLastVersions(
                projectId, listWorkflowLastVersionsQo);

            WorkflowList workflowList = new WorkflowList();
            if (workflowVersionListRsp != null) {
                workflowList.setWorkflowList(NLResourecModelMapper.INSTANCE.toWorkflowResources(
                    workflowVersionListRsp.getWorkflowVersionList()));
            } else {
                workflowList.setWorkflowList(Collections.emptyList());
            }
            resource.setWorkflows(workflowList);
        } catch (Exception e) {
            log.error("Assembel body resource failed.", e);
        }

        return resource;
    }

    private void checkPermission(NLChatReq body, String projectId, String workspaceId) {
        Map<String, Object> modelMap = body.getModel();
        if (modelMap != null) {
            String modelId = String.valueOf(modelMap.get("modelName"));
            List<ModelServiceData> modelServiceDataList = modelManager.queryAvailableServices(projectId, workspaceId, null, true);
            ModelServiceData modelServiceData = modelServiceDataList.stream()
                    .filter(data -> data.getId().equals(modelId))
                    .findFirst().orElse(null);
            if (modelServiceData == null) {
                throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
            }
            if (modelServiceData.isPublic()) {
                return;
            }
            Object extension = modelMap.get("extension");
            if (extension instanceof Map) {
                @SuppressWarnings("unchecked") Map<String, Object> extractedMap = (Map<String, Object>) extension;
                if (extractedMap.containsKey("authId")) {
                    String authId = String.valueOf(extractedMap.get("authId"));
                    ProviderAuthData providerAuthData = providerAuthDataMapper.selectByIdAndProjectIdAndWorkSpaceId(
                        authId, projectId, workspaceId);
                    if (providerAuthData == null) {
                        throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
                    }
                }
            }
        }
    }

    private SseEmitter wrapToSse(Flux<Object> flux) {
        SseEmitter sseEmitter = new SseEmitter(1800000L);
        String language = RequestHeaderHolderUtils.getRequestLanguage();
        flux.subscribe(data -> {
            try {
                sseEmitter.send(SseEmitter.event().data(parseEventMsg(data, language)).build());
            } catch (IOException e) {
                log.error("JiuwenServiceProxyController error to send sse event:", e);
                throw new AgentStudioException(StudioError.JIU_WEN_SERVICE_EXCEPTION);
            }
        }, error -> {
            log.error("JiuwenServiceProxyController error to receive sse event:", error);
            try {
                Map<String, Object> errorEvent = new HashMap<>();
                errorEvent.put("event", "error");
                Map<String, Object> errorData = new HashMap<>();
                errorData.put("code", StudioError.JIU_WEN_SERVICE_EXCEPTION.getCode());
                errorData.put("message", "");
                errorEvent.put("data", errorData);
                sseEmitter.send(SseEmitter.event().data(parseEventMsg(errorEvent, language)).build());
            } catch (IOException e) {
                log.error("JiuwenServiceProxyController error to send error sse event:", e);
            }
            sseEmitter.completeWithError(new AgentStudioException(StudioError.JIU_WEN_SERVICE_EXCEPTION));
        }, sseEmitter::complete);

        return sseEmitter;
    }

    @SuppressWarnings("unchecked")
    private Object parseEventMsg(Object data, String language) {
        if (!(data instanceof Map)) {
            return data;
        }

        Map<String, Object> event = (Map<String, Object>) data;
        try {
            if(!"error".equals(event.get("event"))){
                return event;
            }
            RequestHeaderHolderUtils.setRequestLanguage(language);
            Map<String, Object> eventData = (Map<String, Object>) event.get("data");
            eventData = jiuwenRuntimeI18nService.createRuntimeErrorEvent(eventData);
            event.put("data", eventData);
            return event;
        } catch (Throwable e) {
            log.error("fail parse event message. {}", e.getMessage());
            return data;
        }
    }
}
