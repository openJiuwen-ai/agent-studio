/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.BatchDeleteUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Feedback;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventReq;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.dto.knowledge.ListUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationReq;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationResp;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.common.dto.run.AgentExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.run.CreateTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.GetAgentExecutionInfoQo;
import com.openjiuwen.studio.agent.common.dto.run.GetControllerExecutionDetailQo;
import com.openjiuwen.studio.agent.common.dto.run.GetExecutionInsightQo;
import com.openjiuwen.studio.agent.common.dto.run.ListAgentConversationsQo;
import com.openjiuwen.studio.agent.common.dto.run.ListAgentExecutionQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListControllerExecutionsQo;
import com.openjiuwen.studio.agent.common.dto.run.ListConversationQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListExecutionQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.ModifyTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ResetUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.run.ResumeTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationMemoryQo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.run.TaskListRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskRsp;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.entity.Text2AudioReq;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteUserVariableMemoryRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.manager.dto.ServiceRunAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ServiceWorkflowRunReq;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunReq;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunRsp;
import com.openjiuwen.studio.agent.manager.dto.runtime.AgentRunRsp;
import com.openjiuwen.studio.agent.manager.dto.runtime.Audio2TextReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.StsTextResp;
import com.openjiuwen.studio.agent.manager.dto.runtime.interfaces.SecurityCheck;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.AppMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.ShareResourceManagerService;
import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;
import com.openjiuwen.studio.agent.manager.service.WorkflowRuntimeService;
import com.openjiuwen.studio.agent.manager.service.asset.AssetFreeTrialMgmtService;
import com.openjiuwen.studio.agent.manager.service.proxy.AgentServiceProxyService;

import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * 代理 agent service 接口
 *
 */
@RestController
@Validated
@Slf4j
@SuppressWarnings("checkstyle: all")
public class AgentServiceProxyController {
    public static final String X_USER_PROFILE = "x-user-profile";
    private final AgentRuntimeClient runtimeClient;

    private final RedisClient redisClient;

    private final AgentMapper agentMapper;

    private final WorkflowMapper workflowMapper;

    private AgentServiceProxyService agentServiceProxyService;

    private ShareResourceManagerService shareResourceManagerService;

    private AssetFreeTrialMgmtService assetFreeTrialMgmtService;

    private WorkflowRuntimeService workflowRuntimeService;

    private AgentRuntimeService agentRuntimeService;

    @Value("${agent_runtime_endpoint:}")
    private String runtimeEndpoint;

    @Value("${apikey.enable:false}")
    private boolean apiKeyEnable;

    @Value("${conversations.abort.enable:false}")
    private boolean abortEnable;

    @Value("${file.access.expiration-days:7}")
    private int expireDays;

    private AppMapper appMapper;

    private ReleaseVersionMapper releaseVersionMapper;

    public AgentServiceProxyController(AgentRuntimeClient runtimeClient, RedisClient redisClient,
        AgentMapper agentMapper, WorkflowMapper workflowMapper, AgentServiceProxyService agentServiceProxyService,
        ShareResourceManagerService shareResourceManagerService, AppMapper appMapper,
        AssetFreeTrialMgmtService assetFreeTrialMgmtService, ReleaseVersionMapper releaseVersionMapper,
        WorkflowRuntimeService workflowRuntimeService, AgentRuntimeService agentRuntimeService) {
        this.runtimeClient = runtimeClient;
        this.redisClient = redisClient;
        this.agentMapper = agentMapper;
        this.workflowMapper = workflowMapper;
        this.agentServiceProxyService = agentServiceProxyService;
        this.shareResourceManagerService = shareResourceManagerService;
        this.appMapper = appMapper;
        this.assetFreeTrialMgmtService = assetFreeTrialMgmtService;
        this.releaseVersionMapper = releaseVersionMapper;
        this.workflowRuntimeService = workflowRuntimeService;
        this.agentRuntimeService = agentRuntimeService;
    }

    /**
     * 从请求体中提取query，优先取顶层query，为空则从inputs.query中提取
     */
    private String extractQuery(ServiceRunAgentReq body) {
        if (body.getQuery() != null) {
            return body.getQuery();
        }
        if (body.getInputs() != null && body.getInputs().get("query") != null) {
            return body.getInputs().get("query").toString();
        }
        return null;
    }

    private Object runningAgent(String projectId, String workspaceId, String agentType, String agentId,
        String conversationId, String version, String type, Boolean stream, ServiceRunAgentReq body,
        HttpHeaders httpHeaders, String environmentId) {
        if (stream == null || stream) {
            String url = "%s/v1/%s/agents/%s/conversations/%s?workspace_id=%s";
            url = String.format(Locale.ROOT, url, runtimeEndpoint, projectId, agentId, conversationId, workspaceId);
            if (agentType != null) {
                url += "&agent_type=" + agentType;
            }
            if (version != null) {
                url += "&version=" + version;
            }
            if (type != null) {
                url += "&type=" + type;
            }
            if (StringUtils.isNotBlank(environmentId)) {
                url += "&environment_id=" + environmentId;
            }
            // 兼容X-Execution-Id不存在的场景
            if (ObjectUtils.isEmpty(httpHeaders.get("X-Execution-Id"))) {
                httpHeaders.set("X-Execution-Id", UUID.randomUUID().toString());
            }
            if (apiKeyEnable) {
                httpHeaders.set(CommonConstant.AUTHORIZATION, getApiCode(projectId, workspaceId));
            }
            if (CommonConstant.DEEPRESEARCH_TYPE.equals(agentType)) {
                return agentServiceProxyService.stream(url, httpHeaders, JsonUtils.encode(body), 7200000L);
            }

            // 判断是否为debug模式
            List<String> invokeModeList = httpHeaders.get(Constant.Agent.INVOKE_HEADER_KEY);
            String invokeMode = invokeModeList != null && !invokeModeList.isEmpty() ? invokeModeList.get(0) : "";
            boolean isDebug = Constant.Common.INVOKE_MOD_DEBUG.equalsIgnoreCase(invokeMode);

            if (isDebug) {
                String executeType = agentType != null ? agentType : (type != null ? type : Constant.AppType.AGENT);
                AgentExecuteParams executeParams = AgentExecuteParams.builder()
                    .projectId(projectId)
                    .agentId(agentId)
                    .conversationId(conversationId)
                    .workspaceId(workspaceId)
                    .query(extractQuery(body))
                    .inputs(body.getInputs())
                    .debug(true)
                    .executeType(executeType)
                    .userId(RequestContextUtils.getRequestUserId())
                    .versionId(version)
                    .modelDeploymentId(body.getModelDeploymentId())
                    .toolSwitchDict(body.getToolSwitchDict())
                    .type(type)
                    .token(RequestContextUtils.getRequestAuthToken())
                    .build();
                return agentServiceProxyService.agentStream(url, httpHeaders, JsonUtils.encode(body), executeParams);
            }

            return agentServiceProxyService.stream(url, httpHeaders, JsonUtils.encode(body));
        } else {
            return runtimeClient.runAgentWithConversation(RequestContextUtils.getRequestAuthToken(), getApiCode(projectId, workspaceId), projectId,
                agentId, conversationId, workspaceId, agentType, version, type, environmentId, body).getBody();
        }
    }

    /**
     * 执行Agent，带会话id
     */
    @ApiOperation(value = "run agent asset", nickname = "runAgentAsset", notes = "运行百宝箱Agent",
        response = Object.class, tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = Object.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents-assets/{agent_id}/conversations/{conversation_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public Object runAssetsAgentWithConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "Agent类型", schema = @Schema())
        @RequestParam(value = "agent_type", required = false) String agentType,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation id", schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @RequestParam(value = "version", required = false) String version,
        @RequestParam(value = "type", required = false) String type,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody ServiceRunAgentReq body,
        @RequestHeader HttpHeaders httpHeaders,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "环境id", schema = @Schema())
        @RequestParam(value = "environment_id", required = false) String environmentId) {
        if (!assetFreeTrialMgmtService.isInFreeTrial(agentId, RequestContextUtils.getRequestUserDomainId())) {
            log.info("Agent asset {} is not in free trial for domain {}. Reject this request.", agentId,
                RequestContextUtils.getRequestUserDomainId());

            throw new AgentStudioException(StudioError.CALL_ASSET_APP_EXCEED_FREE_TRIAL_TIMES);
        }

        log.info("Invoke agent asset {} in free trial.", agentId);
        httpHeaders.add(Constants.Header.X_ASSET_APP_INVOKE_IN_FREE_TRIAL, "true");
        httpHeaders.add(Constants.Header.X_ASSET_APP_ID, agentId);
        httpHeaders.add(Constants.Header.X_ASSET_APP_CONVERSATION_ID, conversationId);

        return runningAgent(projectId, workspaceId, agentType, agentId, conversationId, version, type, stream, body,
            httpHeaders, environmentId);
    }

    /**
     * 执行Agent，带会话id
     */
    @ApiOperation(value = "run agent", nickname = "runAgentWithConversation", notes = "运行知识型Agent",
        response = Object.class, tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = Object.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public Object runAgentWithConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "Agent类型", schema = @Schema())
        @RequestParam(value = "agent_type", required = false) String agentType,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation id", schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @RequestParam(value = "version", required = false) String version,
        @RequestParam(value = "type", required = false) String type,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody ServiceRunAgentReq body,
        @RequestHeader HttpHeaders httpHeaders,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "环境id", schema = @Schema())
        @RequestParam(value = "environment_id", required = false) String environmentId) {
        checkAgentPermission(projectId, workspaceId, agentId, version);
        return runningAgent(projectId, workspaceId, agentType, agentId, conversationId, version, type, stream, body,
            httpHeaders, environmentId);
    }

    /**
     * 执行Agent，不带会话id
     */
    @ApiOperation(value = "run agent", nickname = "runAgent", notes = "运行知识型Agent", response = Object.class,
        tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = Object.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public Object runAgent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "Agent类型", schema = @Schema())
        @RequestParam(value = "agent_type", required = false) String agentType,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @RequestParam(value = "version", required = false) String version,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody ServiceRunAgentReq body,
        @RequestHeader HttpHeaders httpHeaders,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "环境id", schema = @Schema())
        @RequestParam(value = "environment_id", required = false) String environmentId) {
        checkAgentPermission(projectId, workspaceId, agentId, version);

        if (apiKeyEnable) {
            httpHeaders.set(CommonConstant.AUTHORIZATION, getApiCode(projectId, workspaceId));
        }
        if (stream == null || stream) {
            String url = "%s/v1/%s/agents/%s/conversations?workspace_id=%s";
            url = String.format(Locale.ROOT, url, runtimeEndpoint, projectId, agentId, workspaceId);
            if (agentType != null) {
                url += "&agent_type=" + agentType;
            }
            if (version != null) {
                url += "&version=" + version;
            }
            if (StringUtils.isNotBlank(environmentId)) {
                url += "&environment_id=" + environmentId;
            }
            if (CommonConstant.DEEPRESEARCH_TYPE.equals(agentType)) {
                return agentServiceProxyService.stream(url, httpHeaders, JsonUtils.encode(body), 7200000L);
            }

            // 判断是否为debug模式
            List<String> invokeModeList = httpHeaders.get(Constant.Agent.INVOKE_HEADER_KEY);
            String invokeMode = invokeModeList != null && !invokeModeList.isEmpty() ? invokeModeList.get(0) : "";
            boolean isDebug = Constant.Common.INVOKE_MOD_DEBUG.equalsIgnoreCase(invokeMode);

            if (isDebug) {
                String executeType = agentType != null ? agentType : Constant.AppType.AGENT;
                AgentExecuteParams executeParams = AgentExecuteParams.builder()
                    .projectId(projectId)
                    .agentId(agentId)
                    .workspaceId(workspaceId)
                    .query(extractQuery(body))
                    .inputs(body.getInputs())
                    .debug(true)
                    .executeType(executeType)
                    .userId(RequestContextUtils.getRequestUserId())
                    .versionId(version)
                    .modelDeploymentId(body.getModelDeploymentId())
                    .toolSwitchDict(body.getToolSwitchDict())
                    .token(RequestContextUtils.getRequestAuthToken())
                    .build();
                return agentServiceProxyService.agentStream(url, httpHeaders, JsonUtils.encode(body), executeParams);
            }

            return agentServiceProxyService.stream(url, httpHeaders, JsonUtils.encode(body));
        } else {
            return runtimeClient.runAgent(RequestContextUtils.getRequestAuthToken(), projectId, agentId,
                workspaceId, agentType, version, environmentId, body).getBody();
        }
    }

    private Object runAssets(String projectId, String workspaceId, String environmentId, String workflowId,
        String conversationId, String version, Boolean stream, ServiceWorkflowRunReq body, HttpHeaders httpHeaders) {
        // 去掉x-user-profile,以防后续接口使用pdp5鉴权
        httpHeaders.remove(X_USER_PROFILE);
        if (apiKeyEnable) {
            httpHeaders.set(CommonConstant.AUTHORIZATION, getApiCode(projectId, workspaceId));
        }

        if (stream == null || stream) {
            String url = "%s/v1/%s/workflows/%s/conversations/%s?workspace_id=%s";
            url = String.format(Locale.ROOT, url, runtimeEndpoint, projectId, workflowId, conversationId, workspaceId);
            if (StringUtils.isNotBlank(environmentId)) {
                url += "&environment_id=" + environmentId;
            }
            if (version != null) {
                url += "&version=" + version;
            }

            // 判断是否为debug模式
            List<String> invokeModeList = httpHeaders.get("X-Invoke-Mode");
            String invokeMode = invokeModeList != null && !invokeModeList.isEmpty() ? invokeModeList.get(0) : "";
            boolean isDebug = "debug".equalsIgnoreCase(invokeMode);

            ExecuteParams executeParams = ExecuteParams.builder()
                .projectId(projectId)
                .workflowId(workflowId)
                .userId(RequestContextUtils.getRequestUserId())
                .debug(isDebug)
                .traceMode(invokeMode)
                .stream(true)
                .startTime(System.currentTimeMillis())
                .conversationId(conversationId)
                .releasedVersion(version)
                .environmentId(environmentId)
                .inputs(body.getInputs())
                .build();

            WorkflowRunResult result = new WorkflowRunResult();
            WorkflowInstanceEntity instance = new WorkflowInstanceEntity();
            instance.setConversationId(conversationId);
            instance.setWorkflowId(workflowId);
            instance.setInputs(body.getInputs());
            instance.setStatus(WorkflowRunStatus.RUNNING.getStatus().getDesc());
            instance.setStartTime(executeParams.getStartTime());
            instance.setEventList(new ArrayList<>());
            instance.setUserId(executeParams.getUserId());
            instance.setProjectId(projectId);
            result.setInstance(instance);

            return agentServiceProxyService.workflowStream(url, httpHeaders, JsonUtils.encode(body), result,
                executeParams);
        } else {
            return runtimeClient.runWorkflowWithConversation(RequestContextUtils.getRequestAuthToken(), projectId,
                workflowId, conversationId, workspaceId, environmentId, version, body).getBody();
        }
    }

    @ApiOperation(value = "run workflow applications", nickname = "runWorkflowAsset", notes = "百宝箱运行",
        response = Object.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = Object.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/workflows-assets/{workflow_id}/conversations/{conversation_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public Object runAssetsWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "环境id", schema = @Schema())
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation id", schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @RequestParam(value = "version", required = false) String version,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody ServiceWorkflowRunReq body,
        @RequestHeader HttpHeaders httpHeaders) {
        if (!assetFreeTrialMgmtService.isInFreeTrial(workflowId, RequestContextUtils.getRequestUserDomainId())) {
            log.info("Workflow asset {} is not in free trial for domain {}. Reject this request.", workflowId,
                RequestContextUtils.getRequestUserDomainId());

            throw new AgentStudioException(StudioError.CALL_ASSET_APP_EXCEED_FREE_TRIAL_TIMES);
        }

        log.info("Invoke workflow asset {} in free trial.", workflowId);
        httpHeaders.add(Constants.Header.X_ASSET_APP_INVOKE_IN_FREE_TRIAL, "true");
        httpHeaders.add(Constants.Header.X_ASSET_APP_ID, workflowId);
        httpHeaders.add(Constants.Header.X_ASSET_APP_CONVERSATION_ID, conversationId);

        return runAssets(projectId, workspaceId, environmentId, workflowId, conversationId, version, stream, body,
            httpHeaders);
    }

    /**
     * 执行 workflow
     */
    @ApiOperation(value = "run workflow applications", nickname = "runWorkflowWithConversation",
        notes = "运行场景化应用接口", response = Object.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = Object.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public Object runWorkflowWithConversation(@Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "环境id", schema = @Schema())
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation id", schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @RequestParam(value = "version", required = false) String version,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody ServiceWorkflowRunReq body,
        @RequestHeader HttpHeaders httpHeaders) {
        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runAssets(projectId, workspaceId, environmentId, workflowId, conversationId, version, stream, body,
            httpHeaders);
    }

    /**
     * agent 上传文件
     */
    @ApiOperation(value = "Agent对话上传文件", nickname = "agentUploadFile", notes = "Agent对话上传文件",
        response = FileUploadRsp.class, tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "agent文件上传响应体", response = FileUploadRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/upload-file", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    public Object agentUploadFile(@NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart("file") MultipartFile file,
        @Min(1) @Max(180) @ApiParam(value = "访问授权过期时间（天）", allowableValues = "180, 1")
        @RequestParam(value = "expires", required = false) Integer expires,
        @ApiParam(value = "是否是图片上传", defaultValue = "false")
        @RequestParam(value = "is_image", required = false, defaultValue = "false") Boolean isImage,
        @RequestHeader HttpHeaders httpHeaders) {
        int finalExpires = (expires == null) ? expireDays : expires;
        return agentServiceProxyService.uploadAgentFile(file,finalExpires,isImage);

    }

    @ApiOperation(value = "根据conversation_id重置会话记忆", nickname = "resetConversationMemory",
        notes = "根据conversation_id重置会话记忆", response = MemoryVariable.class, responseContainer = "List",
        tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "conversation记忆列表", response = MemoryVariable.class,
            responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/memory"
        + "-variables/reset", produces = {"application/json"}, method = RequestMethod.POST)
    public List<MemoryVariable> resetConversationMemory(
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "应用id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Size(max = 32) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId) {
        return agentServiceProxyService.resetConversationMemory(workspaceId, projectId, conversationId, agentId,
            versionId).getBody();
    }

    @ApiOperation(value = "根据conversation_id查询会话记忆", nickname = "retrieveConversationMemory",
        notes = "根据conversation_id查询会话记忆", response = MemoryVariable.class, responseContainer = "List",
        tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "conversation记忆列表", response = MemoryVariable.class,
            responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/memory"
        + "-variables", produces = {"application/json"}, method = RequestMethod.GET)
    public List<MemoryVariable> retrieveConversationMemory(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "agent_id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "RetrieveConversationMemoryQo: converted from multi query params") @Valid
        RetrieveConversationMemoryQo retrieveConversationMemoryQo) {
        return agentServiceProxyService.retrieveConversationMemory(projectId, agentId, conversationId, workspaceId,
            retrieveConversationMemoryQo).getBody();
    }

    @ApiOperation(value = "run workflow node execution", nickname = "runWorkflowNodeExecute",
        notes = "运行工作流单节点执行", response = WorkflowRunRsp.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = WorkflowRunRsp.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}/node_execute"
            + "/{node_id}", produces = {"application/json"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    public Object runWorkflowNodeExecute(@Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "环境id", schema = @Schema())
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation id", schema = @Schema())
        @PathVariable("conversation_id") String conversationId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "node id", schema = @Schema()) @PathVariable("node_id")
        String nodeId, @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody WorkflowRunReq body,
        @RequestHeader HttpHeaders httpHeaders) {

        return agentServiceProxyService.runWorkflowNodeExecute(projectId, workspaceId, environmentId, workflowId,
            conversationId, nodeId, body, httpHeaders);
    }

    @ApiOperation(value = "指定message创建用户反馈", nickname = "createUserFeedback", notes = "指定message创建用户反馈",
        response = String.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = String.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/apps/{app_id}/conversions/{conversation_id}/messages"
        + "/{message_id}/feedback", produces = {"application/json"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    public String createUserFeedback(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "应用ID", required = true, schema = @Schema())
        @PathVariable("app_id") String appId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "会话ID", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "消息ID", required = true, schema = @Schema())
        @PathVariable("message_id") String messageId,
        @NotNull @Size(max = 32) @ApiParam(value = "应用类型", required = true)
        @RequestParam(value = "app_type", required = true) String appType,
        @Size(max = 64) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId, @ApiParam(value = "用户反馈请求体") @Valid @RequestBody(required = false) Feedback body) {

        return agentServiceProxyService.createUserFeedback(projectId, appId, conversationId, messageId, appType,
            versionId, body).getBody();
    }

    @ApiOperation(value = "删除指定message用户反馈", nickname = "deleteFeedback", notes = "删除指定message用户反馈",
        response = ConversationDeleteResp.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversationDeleteResp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/apps/{app_id}/conversions/{conversation_id}/messages" + "/{message_id"
            + "}/feedback", produces = {"application/json"}, method = RequestMethod.DELETE)
    public ConversationDeleteResp deleteFeedback(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("app_id") String appId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("message_id") String messageId,
        @Size(max = 64) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId) {

        return agentServiceProxyService.deleteFeedback(projectId, appId, conversationId, messageId, versionId)
            .getBody();
    }

    @ApiOperation(value = "批量删除用户的变量记忆", nickname = "batchDeleteUserVariableMemory",
        notes = "批量删除用户的变量记忆（用于Agent运行时用户手动删除自己的变量记忆）",
        response = BatchDeleteUserVariableMemoryResponseBody.class, tags = {"AgentMemoryManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量删除变量记忆的响应体",
            response = BatchDeleteUserVariableMemoryResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/agents/{agent_id}/memories/variables/batch-delete",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public BatchDeleteUserVariableMemoryResponseBody batchDeleteUserVariableMemory(@Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "AgentID或Agent发布之后的短编码", required = true,
            schema = @Schema()) @PathVariable("agent_id") String agentId,
        @Size(max = 64) @ApiParam(value = "空间ID") @RequestParam(value = "workspace_id", required = false)
        String workspaceId, @NotNull @ApiParam(value = "批量删除变量记忆的请求体", required = true) @Valid @RequestBody
        BatchDeleteUserVariableMemoryRequestBody body) {

        return agentServiceProxyService.batchDeleteUserVariableMemory(projectId, agentId, workspaceId, body).getBody();
    }

    @ApiOperation(value = "查询应用中的用户的变量记忆列表", nickname = "listUserVariableMemory",
        notes = "查询应用中的用户的变量记忆列表（用于Agent运行时查询变量列表）",
        response = ListUserVariableMemoryResponseBody.class, tags = {"AgentMemoryManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "变量记忆列表", response = ListUserVariableMemoryResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/agents/{agent_id}/memories/variables",
        produces = {"application/json"}, method = RequestMethod.GET)
    public ListUserVariableMemoryResponseBody listUserVariableMemory(@Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "AgentID或Agent发布之后的短编码", required = true,
            schema = @Schema()) @PathVariable("agent_id") String agentId,
        @Size(max = 100) @ApiParam(value = "空间ID") @RequestParam(value = "workspace_id", required = false)
        String workspaceId) {

        return agentServiceProxyService.listUserVariableMemory(projectId, agentId, workspaceId).getBody();
    }

    @ApiOperation(value = "重置用户的变量记忆", nickname = "resetUserVariableMemory",
        notes = "重置用户的变量记忆（用于Agent运行时用户手动重置自己的变量记忆），重置后，用户的所有变量值将重置为默认值",
        response = ResetUserVariableMemoryResponseBody.class, tags = {"AgentMemoryManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量删除变量记忆的响应体",
            response = ResetUserVariableMemoryResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/agents/{agent_id}/memories/variables/reset",
        produces = {"application/json"}, method = RequestMethod.POST)
    public ResetUserVariableMemoryResponseBody resetUserVariableMemory(@Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "AgentID或Agent发布之后的短编码", required = true,
            schema = @Schema()) @PathVariable("agent_id") String agentId,
        @Size(max = 64) @ApiParam(value = "空间ID") @RequestParam(value = "workspace_id", required = false)
        String workspaceId) {

        return agentServiceProxyService.resetUserVariableMemory(projectId, agentId, workspaceId).getBody();
    }

    @ApiOperation(value = "查询当前对话中用户输入内容的列表", nickname = "listConversationQueries", notes = "",
        response = ConversionQueries.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversionQueries.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations",
        produces = {"application/json"}, method = RequestMethod.GET)
    public ConversionQueries listConversationQueries(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListConversationQueriesQo: converted from multi query params") @Valid
        ListConversationQueriesQo listConversationQueriesQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return workflowRuntimeService.listConversationQueries(projectId, workflowId, listConversationQueriesQo);
    }

    @ApiOperation(value = "查询当前对话中用户输入内容的列表", nickname = "listExecutionQueries", notes = "",
        response = ExecutionQueries.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ExecutionQueries.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id"
        + "}/executions", produces = {"application/json"}, method = RequestMethod.GET)
    public ExecutionQueries listExecutionQueries(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "会话id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "ListExecutionQueriesQo: converted from multi query params") @Valid
        ListExecutionQueriesQo listExecutionQueriesQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return workflowRuntimeService.listExecutionQueries(projectId, workflowId, conversationId,
            listExecutionQueriesQo);
    }

    @ApiOperation(value = "", nickname = "getExecutionInsight", notes = "", response = ExecutionInfo.class,
        tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ExecutionInfo.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/executions/{execution_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    public ExecutionInfo getExecutionInsight(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "执行id", required = true, schema = @Schema())
        @PathVariable("execution_id") String executionId,
        @ApiParam(value = "GetExecutionInsightQo: converted from multi query params") @Valid
        GetExecutionInsightQo getExecutionInsightQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return workflowRuntimeService.getExecutionInsight(projectId, workflowId, executionId, getExecutionInsightQo);
    }

    @ApiOperation(value = "根据conversation_id删除会话", nickname = "deleteConversation",
        notes = "根据conversation_id删除会话", response = ConversationDeleteResp.class,
        tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversationDeleteResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/history",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    public ConversationDeleteResp deleteConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow/agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Size(max = 32) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId, @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.deleteConversation(projectId, agentId, conversationId, versionId, workspaceId)
            .getBody();
    }

    @ApiOperation(value = "提交异步工作流任务", nickname = "createTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public TaskRsp createTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Size(max = 64) @ApiParam(value = "版本号") @RequestParam(value = "version", required = false) String version,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "创建文件请求体", required = true) @Valid @RequestBody CreateTaskReq body) {

        return agentServiceProxyService.createTask(projectId, workflowId, version, workspaceId, body).getBody();
    }

    @ApiOperation(value = "根据conversation_id查询会话", nickname = "retrieveConversation",
        notes = "根据conversation_id查询会话", response = Message.class, responseContainer = "List",
        tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "conversation消息", response = Message.class, responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id}/history",
        produces = {"application/json"}, method = RequestMethod.GET)
    public List<Message> retrieveConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow/agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "RetrieveConversationQo: converted from multi query params") @Valid
        RetrieveConversationQo retrieveConversationQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.retrieveConversation(projectId, agentId, conversationId, retrieveConversationQo,
            workspaceId).getBody();
    }

    @ApiOperation(value = "查看任务列表", nickname = "listTask", notes = "", response = TaskListRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskListRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks",
        produces = {"application/json"}, method = RequestMethod.GET)
    public TaskListRsp listTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListTaskQo: converted from multi query params") @Valid  ListTaskQo listTaskQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.listTask(projectId, workflowId, listTaskQo, workspaceId).getBody();
    }

    @ApiOperation(value = "获取异步任务详情", nickname = "retrieveTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    public TaskRsp retrieveTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.retrieveTask(projectId, workflowId, taskId, workspaceId).getBody();
    }

    @ApiOperation(value = "继续执行任务", nickname = "resumeTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    public TaskRsp resumeTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "创建文件请求体", required = true) @Valid @RequestBody ResumeTaskReq body) {

        return agentServiceProxyService.resumeTask(projectId, workflowId, taskId, workspaceId, body).getBody();
    }

    @ApiOperation(value = "修改任务信息", nickname = "modifyTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    public TaskRsp modifyTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "创建文件请求体", required = true) @Valid @RequestBody ModifyTaskReq body) {

        return agentServiceProxyService.modifyTask(projectId, workflowId, taskId, workspaceId, body).getBody();
    }

    @ApiOperation(value = "取消异步任务详情", nickname = "deleteTask", notes = "", response = CommonDeleteRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    public CommonDeleteRsp deleteTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.deleteTask(projectId, workflowId, taskId, workspaceId).getBody();
    }

    @ApiOperation(value = "取消异步任务详情", nickname = "cancelTask", notes = "", response = CancelTaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = CancelTaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}/cancel",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    public CancelTaskRsp cancelTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.cancelTask(projectId, workflowId, taskId, workspaceId).getBody();
    }

    // 此接口已弃用
    @ApiOperation(value = "测试 mcp 服务", nickname = "testServer", notes = "测试 mcp 服务",
        response = McpValidationResp.class, tags = {"McpServerRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "mcp 服务测试结果", response = McpValidationResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/test", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    public McpValidationResp testServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
                                        @NotNull @ApiParam(value = "请求参数", required = true) @Valid @RequestBody McpValidationReq body,
                                        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.testServer(projectId, body, workspaceId).getBody();
    }

    @ApiOperation(value = "重排序接口", nickname = "rerank", notes = "rerank", response = Object.class,
        tags = {"RuntimeModelServiceController"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "rerank", response = Object.class)
    })
    @PostMapping(value = "/v1/{project_id}/agent-manager/agent-builder/rerank", consumes = {"application/json"})
    public Object rerank(
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64) @RequestParam(value = "workspace_id", required = false)
        String workspaceId, @RequestHeader HttpHeaders headers, @Valid @RequestBody RankDocumentsRequest request,
        @RequestParam(value = "refresh", required = false) Boolean refresh,
        @PathVariable(value = "project_id") String projectId) {

        return agentServiceProxyService.rerank(headers, workspaceId, request, refresh, projectId);
    }

    @ApiOperation(value = "文本向量化", nickname = "textEmbeddings", notes = "textEmbeddings", response = Object.class,
        tags = {"RuntimeModelServiceController"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "textEmbeddings", response = Object.class)
    })
    @PostMapping(value = "/v1/{project_id}/agent-manager/agent-builder/embeddings", consumes = {"application/json"})
    public Object textEmbeddings(
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64) @RequestParam(value = "workspace_id", required = false)
        String workspaceId, @RequestHeader HttpHeaders headers, @RequestBody EmbeddingRequest request,
        @RequestParam(value = "refresh", required = false) Boolean refresh,
        @PathVariable(value = "project_id", required = false) String projectId) {

        return agentServiceProxyService.textEmbeddings(headers, workspaceId, request, refresh, projectId);
    }

    @ApiOperation(value = "模型调测", nickname = "chatCompletions", notes = "chatCompletions", response = Object.class,
        tags = {"RuntimeModelServiceController"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "chatCompletions", response = Object.class)
    })
    @PostMapping(value = "/v1/{project_id}/agent-manager/agent-builder/chat/completions", consumes = {"application/json"})
    @SecurityCheck
    public Object chatCompletions(
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64) @RequestParam(value = "workspace_id", required = false)
        String workspaceId, @RequestHeader HttpHeaders headers, @Valid @RequestBody ChatCompletionRequest request,
        @RequestParam(value = "refresh", required = false) Boolean refresh,
        @PathVariable(value = "project_id", required = false) String projectId) {
        return agentServiceProxyService.chatCompletions(headers, workspaceId, request, refresh, projectId);
    }

    @ApiOperation(value = "自动生成追问", nickname = "additionalQuestions", notes = "自动生成追问",
        response = AutoAddResultJsonObject.class, tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "追问列表", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id"
        + "}/additional-questions", produces = {"application/json"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    AutoAddResultJsonObject additionalQuestions(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @NotNull @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "追问请求体", required = true) @Valid @RequestBody AdditionalQuestionsReq body) {

        return agentServiceProxyService.additionalQuestions(projectId, agentId, conversationId, workspaceId, body)
            .getBody();
    }
    @ApiOperation(value = "工作流自动生成追问", nickname = "additionalQuestionsWorkflow", notes = "自动生成追问",
        response = AutoAddResultJsonObject.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "追问列表", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id"
        + "}/additional-questions", produces = {"application/json"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    AutoAddResultJsonObject additionalQuestionsWorkflow(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @NotNull @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "追问请求体", required = true) @Valid @RequestBody AdditionalQuestionsWorkflowReq body) {

        return agentServiceProxyService.additionalQuestionsWorkflow(projectId, workflowId, conversationId, workspaceId, body)
            .getBody();
    }

    @ApiOperation(value = "工具执行", nickname = "runTool", notes = "执行一个工具",
        response = RunToolResponseBody.class, tags = {"ToolRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具运行结果", response = RunToolResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}", produces = {"application/json"},
        consumes = {"application/json;charset=utf-8"}, method = RequestMethod.POST)
    RunToolResponseBody runTool(@RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "执行工具请求参数", required = true) @Valid @RequestBody RunToolRequestBody body,
        @PathVariable("tool_id") String toolId) {
        return agentServiceProxyService.runTool(workspaceId, projectId, body, toolId).getBody();
    }

    @ApiOperation(value = "text To Speech", nickname = "textToSpeech", notes = "文本转语音", response = Object.class,
        tags = {"TextToSpeech"})
    @ApiResponses(value = {@ApiResponse(code = 200, message = "OK", response = Object.class)})
    @PostMapping(value = "/v1/{project_id}/agent-manager/agents/audio/tts", consumes = {"application/json"})
    JSONObject textToSpeech(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @RequestBody Text2AudioReq request) {
        return agentServiceProxyService.textToSpeech(projectId, workspaceId, request);
    }

    @ApiOperation(value = "audio transcription", nickname = "audioTranscription", notes = "语音转写",
        response = Object.class, tags = {"AudioTranscription"})
    @ApiResponses(value = {@ApiResponse(code = 200, message = "OK", response = Object.class)})
    @PostMapping(value = "/v1/{project_id}/agent-manager/agents/audio/transcriptions", consumes = {"application/json"})
    public StsTextResp audioTranscriptions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @RequestBody Audio2TextReq request) {

        return agentServiceProxyService.audioTranscriptions(projectId, workspaceId,request).getBody();
    }

    @ApiOperation(value = "增加分析事件", nickname = "analyticsEvent",
        notes = "提供分析事件记录接口，实现（类似点赞，点踩）功能", response = AnalyticsEventResp.class,
        tags = {"AnalyticsEvent"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "事件", response = AnalyticsEventResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/analytics/event",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    AnalyticsEventResp analyticsEvent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @NotNull @ApiParam(value = "事件", required = true) @Valid @RequestBody AnalyticsEventReq body,
        @RequestParam(value = "workspace_id") String workspaceId) {

        return agentServiceProxyService.analyticsEvent(projectId, agentId, body, workspaceId).getBody();
    }

    @ApiOperation(value = "", nickname = "listAgentExecutionQueries", notes = "查询用户的Agent对话输入内容的列表",
        response = AgentExecutionQueries.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "agent对话query列表", response = AgentExecutionQueries.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations/{conversation_id"
        + "}/execution-queries", produces = {"application/json"}, method = RequestMethod.GET)
    AgentExecutionQueries listAgentExecutionQueries(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "ListAgentExecutionQueriesQo: converted from multi query params") @Valid
        ListAgentExecutionQueriesQo listAgentExecutionQueriesQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {
        return agentRuntimeService.listAgentExecutionQueries(projectId, agentId, conversationId,
            listAgentExecutionQueriesQo);
    }

    @ApiOperation(value = "", nickname = "getAgentExecutionInfo", notes = "查询 agent 会话信息",
        response = AgentExecutionInfo.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "Agent对话信息列表", response = AgentExecutionInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/executions/{execution_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    AgentExecutionInfo getAgentExecutionInfo(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("execution_id") String executionId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @ApiParam(value = "GetAgentExecutionInfoQo: converted from multi query params") @Valid
        GetAgentExecutionInfoQo getAgentExecutionInfoQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentRuntimeService.getAgentExecutionInfo(projectId, executionId, agentId, getAgentExecutionInfoQo);
    }

    @ApiOperation(value = "", nickname = "voiceRecognition", notes = "一句话语音识别", response = AsrRsp.class,
        tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "语音识别返回数据", response = AsrRsp.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/asr/short-audio", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    AsrRsp voiceRecognition(@Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "接口请求体", required = true) @Valid @RequestBody AsrReq body,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {
        return agentServiceProxyService.voiceRecognition(projectId, body, workspaceId).getBody();
    }

    @ApiOperation(value = "查询当前Agent应用的会话列表", nickname = "listAgentConversations", notes = "",
        response = ConversionQueries.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversionQueries.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/conversations", produces = {
        "application" + "/json"
    }, method = RequestMethod.GET)
    ConversionQueries listAgentConversations(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @ApiParam(value = "ListAgentConversationsQo: converted from multi query params") @Valid
        ListAgentConversationsQo listAgentConversationsQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @RequestParam(value = "type", required = false) String type) {
        return agentRuntimeService.listAgentConversations(projectId, agentId, listAgentConversationsQo);
    }

    @ApiOperation(value = "停止对话生成并清空会话", nickname = "abortConversation", notes = "", response = Status.class,
        tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = Status.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/conversations/{conversation_id}/abort",
        produces = {"application/json"}, method = RequestMethod.POST)
    Status abortConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "会话流id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {
        if (!abortEnable) {
            throw new AgentStudioException(StudioError.INTERFACE_FORBIDDEN_ACCESS);
        }
        return agentServiceProxyService.abortConversation(projectId, workflowId, conversationId, workspaceId).getBody();
    }

    ;

    @ApiOperation(value = "run web Workflow", nickname = "runWebAgent", notes = "运行网页Workflow",
        response = WorkflowRunReq.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = WorkflowRunReq.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/workflows/chat/{short_code}/conversations/{conversation_id}",
        produces = {
            "application/json"
        }, consumes = {"application/json"}, method = RequestMethod.POST)
    Object runWebWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "short_code", required = true, schema = @Schema())
        @PathVariable("short_code") String shortCode,
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @RequestHeader HttpHeaders httpHeaders,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation id", schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody WorkflowRunReq body) {
        return agentServiceProxyService.runWebWorkflow(shortCode, projectId, httpHeaders, workspaceId, conversationId,
            stream, body);
    }

    @ApiOperation(value = "run web agent", nickname = "runWebAgent", notes = "运行网页Agent",
        response = AgentRunRsp.class, tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "OK", response = AgentRunRsp.class),
        @ApiResponse(code = 400, message = "Error response", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/chat/{short_code}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    Object runWebAgent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "short_code", required = true, schema = @Schema())
        @PathVariable("short_code") String shortCode, @Pattern(regexp = "^[a-zA-Z0-9_()-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", schema = @Schema())
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @RequestHeader(value = "stream", required = false) Boolean stream,
        @NotNull @ApiParam(value = "输入参数", required = true) @Valid @RequestBody AgentRunReq body,
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @RequestHeader HttpHeaders httpHeaders) {
        return agentServiceProxyService.runWebAgent(shortCode, projectId, httpHeaders, workspaceId, stream, body);
    }

    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = Status.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/controller/{agent_id}/conversations/{conversation_id}/executions",
        produces = {"application/json"}, method = RequestMethod.GET)
    Object listControllerExecutions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "会话流id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Valid  ListControllerExecutionsQo listControllerExecutionsQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {

        return agentServiceProxyService.listControllerExecutions(projectId, agentId, conversationId,
            listControllerExecutionsQo, workspaceId).getBody();
    }

    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = Status.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/controller/{agent_id}/executions/{execution_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    Object getControllerExecutionDetail(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "会话流id", required = true, schema = @Schema())
        @PathVariable("execution_id") String executionId,
        @Valid  GetControllerExecutionDetailQo getControllerExecutionDetailQo,
        @RequestParam(value = "workspace_id", required = false) String workspaceId) {
        return agentServiceProxyService.getControllerExecutionDetail(projectId, agentId, executionId,
            getControllerExecutionDetailQo, workspaceId).getBody();
    }

    private String getApiCode(String projectId, String workspaceId) {
        if (!apiKeyEnable) {
            return null;
        }
        String apiCode = UUID.randomUUID().toString();
        Map<String, String> redisData = new HashMap<>();
        redisData.put("projectId", projectId);
        redisData.put("workspaceId", workspaceId);
        redisData.put("domainId", RequestContextUtils.getRequestUserDomainId());
        redisData.put("userId", RequestContextUtils.getRequestUserId());
        redisClient.set(apiCode, JSON.toJSONString(redisData), Duration.ofSeconds(30));
        return Constants.Header.AUTHORIZATION_PREFIX + apiCode;
    }

    private void checkAgentPermission(String projectId, String workspaceId, String agentId) {
        checkAgentPermission(projectId, workspaceId, agentId, null);
    }

    private void checkAgentPermission(String projectId, String workspaceId, String agentId, String version) {
        Agent agent = agentMapper.selectById(agentId);
        if (agent == null) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        if (version != null && !Constants.LATEST_PUBLISH_VERSION.equals(version)) {
            ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(agentId, version);
            if (releaseVersion == null) {
                throw new AgentStudioException(StudioError.AGENT_OR_VERSION_NOT_EXIST);
            }
        }

        boolean hasShareResourcePermission = shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(workspaceId,
            agentId);
        if (hasShareResourcePermission) {
            return;
        }

        if ((!Objects.equals(projectId, agent.getProjectId()) || !Objects.equals(workspaceId,
            agent.getWorkspaceId()))) {
            throw new AgentStudioException(StudioError.INSUFFICIENT_AGENT_RUN_PRIVILEGES);
        }
    }

    private void checkWorkflowPermission(String projectId, String workspaceId, String workflowId) {
        WorkflowEntity workflowEntity = workflowMapper.getWorkflowById(workflowId);
        if (workflowEntity == null) {
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }

        boolean hasShareResourcePermission = shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(workspaceId,
            workflowId);
        if (hasShareResourcePermission) {
            return;
        }

        if ((!Objects.equals(projectId, workflowEntity.getProjectId()) || !Objects.equals(workspaceId,
            workflowEntity.getWorkspaceId()))) {
            throw new AgentStudioException(StudioError.INSUFFICIENT_WORKFLOW_RUN_PRIVILEGES);
        }
    }

    private void checkAppPermission(String resourceId) {
        if (appMapper.selectByResourceId(resourceId) == null) {
            log.error("Reousrce is not exist. id:{}", resourceId);
            throw new AgentStudioException(StudioError.RESOURCE_NOT_EXISTS);
        }
    }
}
