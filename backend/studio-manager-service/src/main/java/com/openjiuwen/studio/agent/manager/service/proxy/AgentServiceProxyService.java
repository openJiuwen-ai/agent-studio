/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.obs.services.model.TemporarySignatureResponse;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.BatchDeleteUserVariableMemoryResponseBody;
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
import com.openjiuwen.studio.agent.common.dto.run.*;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.common.entity.Text2AudioReq;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.*;
import com.openjiuwen.studio.agent.manager.bo.FileCheckWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.*;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteUserVariableMemoryRequestBody;
import com.openjiuwen.studio.agent.common.dto.BatchDeleteUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationReq;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.common.dto.run.ResetUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.Audio2TextReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.StsTextResp;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.manager.model.ExecuteParams;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionBriefModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionDetailModel;
import com.openjiuwen.studio.agent.manager.model.debugging.ControllerExecutionInvokeModel;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;
import com.openjiuwen.studio.agent.manager.service.debugging.ControllerDebuggingMgmtService;

import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSources;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
@Validated
@Slf4j
@SuppressWarnings("checkstyle: all")
public class AgentServiceProxyService {
    private static final String REQUEST_ID = "request-id";

    private final AgentRuntimeClient runtimeClient;

    private final RedisClient redisClient;

    private final AgentMapper agentMapper;

    private final WorkflowMapper workflowMapper;

    private final ModelServiceMapper modelServiceMapper;

    private final OkHttpClientUtils okHttpClientUtils;

    private final RouterStrategyMapper routerStrategyMapper;

    private final FreeModelServiceMapper freeModelServiceMapper;

    private final ToolMapper toolMapper;

    private final AgentRuntimeService agentRuntimeService;

    private final ControllerDebuggingMgmtService controllerDebuggingMgmtService;

    private static final int KB = 1024;

    private final MgObsService mgObsService;

    @Value("${agent_runtime_endpoint:}")
    private String runtimeEndpoint;

    @Value("${agent_builder_endpoint:}")
    private String agentBuilderEndpoint;

    @Value("${env.type}")
    private String envType;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${icon.max-size}")
    private long iconMaxSize;

    @Value("${agent.max-upload-file-size}")
    private long fileMaxSize;

    @Value("${agent.max-upload-image-size}")
    private long imageMaxSize;

    @Value("${file.max-upload-num}")
    private int maxUploadNum;

    @Value("${file.time-scope-upload-num}")
    private int timeScopeUploadNum;

    @Value("${file.max-upload-total-size}")
    private int maxUploadTotalSize;

    @Value("${file.time-scope-upload-total-size}")
    private int timeScopeUploadTotalSize;

    @Value("${obs.bucket_storage_limit:100}")
    private long bucketStorageLimit;

    @Value("${file.default-type}")
    private String allowedDefaultTypeStr;

    @Value("${file.icon-type}")
    private String allowedIconTypeStr;

    @Value("${file.img-type}")
    private String allowedImgTypeStr;

    @Value("${file.readonly.enable:false}")
    private boolean fileReadOnly;

    private Set<String> allowedIconType = new HashSet<>();

    private Set<String> allowedImgType = new HashSet<>();

    private Set<String> allowedDefaultType = new HashSet<>();

    @Autowired
    private IPlugin iPlugin;

    /**
     * 初始化
     */
    @PostConstruct
    public void init() {
        allowedIconType = Arrays.stream(allowedIconTypeStr.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
        allowedImgType = Arrays.stream(allowedImgTypeStr.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
        allowedDefaultType = Arrays.stream(allowedDefaultTypeStr.split(CommonConstant.SEPARATOR)).collect(Collectors.toSet());
    }

    private String getToken() {
        return RequestContextUtils.getRequestAuthToken();
    }

    public AgentServiceProxyService(AgentRuntimeClient runtimeClient, RedisClient redisClient, AgentMapper agentMapper,
        WorkflowMapper workflowMapper, ModelServiceMapper modelServiceMapper, OkHttpClientUtils okHttpClientUtils,
        RouterStrategyMapper routerStrategyMapper, FreeModelServiceMapper freeModelServiceMapper,
        ToolMapper toolMapper, AgentRuntimeService agentRuntimeService,
        ControllerDebuggingMgmtService controllerDebuggingMgmtService, MgObsService mgObsService) {
        this.runtimeClient = runtimeClient;
        this.redisClient = redisClient;
        this.agentMapper = agentMapper;
        this.workflowMapper = workflowMapper;
        this.modelServiceMapper = modelServiceMapper;
        this.okHttpClientUtils = okHttpClientUtils;
        this.routerStrategyMapper = routerStrategyMapper;
        this.freeModelServiceMapper = freeModelServiceMapper;
        this.toolMapper = toolMapper;
        this.agentRuntimeService = agentRuntimeService;
        this.controllerDebuggingMgmtService = controllerDebuggingMgmtService;
        this.mgObsService = mgObsService;
    }

    public ResponseEntity<List<MemoryVariable>> resetConversationMemory(String workspaceId, String projectId,
        String conversationId, String agentId, String versionId) {
        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.resetConversationMemory(getToken(), projectId, conversationId, agentId, versionId);
    }

    public ResponseEntity<List<MemoryVariable>> retrieveConversationMemory(String projectId, String agentId,
        String conversationId, String workspaceId, RetrieveConversationMemoryQo retrieveConversationMemoryQo) {

        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.retrieveConversationMemory(getToken(), projectId, conversationId, agentId,
            retrieveConversationMemoryQo);
    }

    public Object runWorkflowNodeExecute(String projectId, String workspaceId, String environmentId, String workflowId,
        String conversationId, String nodeId, WorkflowRunReq body, HttpHeaders httpHeaders) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        String url = "%s/v1/%s/workflows/%s/conversations/%s/node_execute/%s?workspace_id=%s";
        url = String.format(Locale.ROOT, url, runtimeEndpoint, projectId, workflowId, conversationId, nodeId,
            workspaceId);
        if (StringUtils.hasText(environmentId)) {
            url += "&environment_id=" + environmentId;
        }
        return stream(url, httpHeaders, JsonUtils.encode(body));
    }

    public ResponseEntity<String> createUserFeedback(String projectId, String appId, String conversationId,
        String messageId, String appType, String versionId, Feedback body) {

        return runtimeClient.createUserFeedback(getToken(), projectId, appId, conversationId, messageId, appType,
            versionId, body);
    }

    @OperationLog(
        operationType = OperationType.DELETE,
        resourceType = "ConversationFeedback",
        description = "删除用户反馈",
        resourceId = "messageId",
        resourceName = ""
    )
    public ResponseEntity<ConversationDeleteResp> deleteFeedback(String projectId, String appId, String conversationId,
        String messageId, String versionId) {

        return runtimeClient.deleteFeedback(getToken(), projectId, appId, conversationId, messageId, versionId);
    }

    ;

    public ResponseEntity<BatchDeleteUserVariableMemoryResponseBody> batchDeleteUserVariableMemory(String projectId,
        String agentId, String workspaceId, BatchDeleteUserVariableMemoryRequestBody body) {

        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.batchDeleteUserVariableMemory(getToken(), projectId, agentId, workspaceId, body);
    }

    public ResponseEntity<ListUserVariableMemoryResponseBody> listUserVariableMemory(String projectId, String agentId,
        String workspaceId) {

        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.listUserVariableMemory(getToken(), projectId, agentId, workspaceId);
    }

    public ResponseEntity<ResetUserVariableMemoryResponseBody> resetUserVariableMemory(String projectId, String agentId,
        String workspaceId) {

        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.resetUserVariableMemory(getToken(), projectId, agentId, workspaceId);
    }








    public ResponseEntity<McpValidationResp> testServer(String projectId, McpValidationReq body, String workspaceId) {

        return runtimeClient.testServer(getToken(), projectId, body, workspaceId);
    }

    public Object rerank(HttpHeaders headers, String workspaceId, RankDocumentsRequest request, Boolean refresh,
        String projectId) {
        String modelId = request.getModel();
        checkModelPermission(projectId, workspaceId, modelId);
        return runtimeClient.rerank(getToken(), projectId, workspaceId, request, refresh);
    }

    public Object textEmbeddings(HttpHeaders headers, String workspaceId, EmbeddingRequest request, Boolean refresh,
        String projectId) {

        String modelId = request.getModel();
        checkModelPermission(projectId, workspaceId, modelId);
        return runtimeClient.textEmbeddings(getToken(), projectId, workspaceId, request, refresh);
    }

    public Object chatCompletions(HttpHeaders headers, String workspaceId, ChatCompletionRequest request,
        Boolean refresh, String projectId) {

        String modelId = request.getModel();
        checkModelPermission(projectId, workspaceId, modelId);
        if (request.getStream() == null || request.getStream()) {
            String url = agentBuilderEndpoint + "/v1/agent-builder/chat/completions?project_id=" + projectId + "&workspace_id="
                + workspaceId + "&refresh=" + (Boolean.FALSE.equals(refresh) ? "false" : "true");

            return stream(url, headers, JsonUtils.encode(request));
        }
        return runtimeClient.chatCompletions(getToken(), projectId, workspaceId, request, refresh);
    }

    public ResponseEntity<AutoAddResultJsonObject> additionalQuestions(String projectId, String agentId,
        String conversationId, String workspaceId, AdditionalQuestionsReq body) {

        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.additionalQuestions(getToken(), projectId, agentId, conversationId, workspaceId, body);
    }

    public ResponseEntity<AutoAddResultJsonObject> additionalQuestionsWorkflow(String projectId, String workflowId,
        String conversationId, String workspaceId, AdditionalQuestionsWorkflowReq body) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.additionalQuestionsWorkflow(getToken(), projectId, workflowId, conversationId, workspaceId,
            body);
    }

    public ResponseEntity<RunToolResponseBody> runTool(String workspaceId, String projectId, RunToolRequestBody body,
        String toolId) {
        String[] tool = body.getToolObsKey().split("#");
        ToolEntity entity = toolMapper.selectById(tool[0]);
        checkToolsPermission(entity, projectId, workspaceId);
        return ResponseModel.success(iPlugin.runTool(projectId, body));
    }

    public ResponseEntity<RunToolResponseBody> runToolForValidateToolCredential(String workspaceId, String projectId,
        RunToolRequestBody body, String toolId) {

        return runtimeClient.runTool(getToken(), workspaceId, projectId, body, toolId);
    }

    public JSONObject textToSpeech(String projectId, String workspaceId, Text2AudioReq req) {
        return runtimeClient.textToSpeech(getToken(), projectId, workspaceId, req);
    }

    public ResponseEntity<StsTextResp> audioTranscriptions(String projectId, String workspaceId, Audio2TextReq req) {

        return runtimeClient.audioTranscriptions(getToken(), projectId, workspaceId, req);
    }

    public ResponseEntity<AnalyticsEventResp> analyticsEvent(String projectId, String agentId, AnalyticsEventReq body,
        String workspaceId) {

        return runtimeClient.analyticsEvent(getToken(), projectId, agentId, body, workspaceId);
    }

    public ResponseEntity<AsrRsp> voiceRecognition(String projectId, AsrReq body, String workspaceId) {

        return runtimeClient.voiceRecognition(getToken(), projectId, body, workspaceId);
    }

    public ResponseEntity<Status> abortConversation(String projectId, String workflowId, String conversationId,
        String workspaceId) {
        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.abortConversation(getToken(), projectId, workflowId, conversationId, workspaceId);
    }
    //  MCP\rerank\Embedding 待确认鉴权方式

    public ResponseEntity<Object> listControllerExecutions(String projectId, String agentId, String conversationId,
        ListControllerExecutionsQo listControllerExecutionsQo, String workspaceId) {
        List<ControllerExecutionBriefModel> briefModels = controllerDebuggingMgmtService.queryCtrlExecutions(
            agentId, conversationId, listControllerExecutionsQo);

        List<ControllerExecution> executions = briefModels.stream().map(brief -> {
            ControllerExecution exec = new ControllerExecution();
            exec.setExecutionId(brief.getExecutionId());
            exec.setQuery(brief.getQuery());
            exec.setStatus(brief.getStatus());
            exec.setErrorInfo(brief.getError());
            exec.setStartTime(brief.getStartTime());
            return exec;
        }).toList();

        ListControllerExecutionsResp resp = new ListControllerExecutionsResp();
        resp.setCount(executions.size());
        resp.setExecutions(executions);
        return ResponseEntity.ok(resp);
    }

    public ResponseEntity<Object> getControllerExecutionDetail(String projectId, String agentId, String executionId,
        GetControllerExecutionDetailQo body, String workspaceId) {

        ControllerExecutionDetailModel detailModel = controllerDebuggingMgmtService.queryCtrlExecutionDetail(
            agentId, executionId);
        if (detailModel == null || detailModel.getExecutionId() == null) {
            return ResponseEntity.ok(new JSONObject());
        }

        try {
            ControllerExecutionDetail detail = new ControllerExecutionDetail();
            detail.setExecutionId(detailModel.getExecutionId());
            detail.setConversationId(detailModel.getConversationId());
            detail.setStatus(detailModel.getStatus());
            detail.setStartTime(detailModel.getStartTime());
            detail.setEndTime(detailModel.getEndTime());
            detail.setErrorInfo(detailModel.getError());

            // Convert invocations
            if (detailModel.getInvocations() != null) {
                List<ControllerInvokeInfo> invokeInfos = detailModel.getInvocations().stream()
                    .map(this::convertToInvokeInfo).toList();
                detail.setInvocations(invokeInfos);
            }

            // Enrich nested workflows with names
            List<String> nestedWorkflowIds = detailModel.getNestedWorkflowIds();
            if (nestedWorkflowIds != null && !nestedWorkflowIds.isEmpty()) {
                List<WorkflowEntity> workflowEntities = workflowMapper.selectByWorkflowIds(projectId, workspaceId,
                    nestedWorkflowIds);
                List<WorkflowBaseData> workflowBaseDataList = workflowEntities.stream().map(entity -> {
                    WorkflowBaseData data = new WorkflowBaseData();
                    data.setFlowId(entity.getId());
                    data.setFlowName(entity.getName());
                    return data;
                }).toList();
                detail.setNestedWorkflows(workflowBaseDataList);
            }

            return ResponseEntity.ok(detail);
        } catch (Exception e) {
            log.error("Failed to get controller execution detail", e);
            return ResponseEntity.ok(new JSONObject());
        }
    }

    private ControllerInvokeInfo convertToInvokeInfo(ControllerExecutionInvokeModel model) {
        ControllerInvokeInfo info = new ControllerInvokeInfo();
        info.setInvokeId(model.getInvokeId());
        info.setParentInvokeId(model.getParentInvokeId());
        info.setNodeId(model.getNodeId());
        info.setNodeName(model.getNodeName());
        info.setNodeType(model.getNodeType());
        info.setNodeStatus(model.getNodeStatus());
        info.setParentNodeId(model.getParentNodeId());
        info.setModelDeploymentId(model.getModelDeploymentId());
        info.setErrorMessage(model.getErrorMsg());
        info.setInputs(model.getInput());
        info.setOutputs(model.getOutput());
        info.setStartTime(model.getStartTime());
        info.setEndTime(model.getEndTime());
        info.setApplicationId(model.getApplicationId());
        info.setParentApplicationId(model.getParentApplicationId());
        info.setMetadata(model.getMetadata());
        info.setMessages(model.getMessages());
        if (model.getStatus() != null) {
            ControllerInvokeInfoStatus invokeStatus = new ControllerInvokeInfoStatus();
            invokeStatus.setCode(model.getStatus().getCode());
            invokeStatus.setDesc(model.getStatus().getDesc());
            info.setStatus(invokeStatus);
        }
        if (model.getApplicationType() != null) {
            info.setApplicationType(
                ControllerInvokeInfo.ApplicationTypeEnum.fromValue(model.getApplicationType()));
        }
        return info;
    }

    public Object runWebWorkflow(String shortCode, String projectId, HttpHeaders httpHeaders, String workspaceId,
        String conversationId, Boolean stream, WorkflowRunReq body) {
        if (stream == null || stream) {
            String url = runtimeEndpoint + "/v1/workflows/chat/" + shortCode + "/conversations/" + conversationId
                + "?workspace_id=" + workspaceId;

            return stream(url, httpHeaders, JsonUtils.encode(body));
        }
        return runtimeClient.runWebWorkflow(getToken(), shortCode, conversationId, workspaceId, body, false).getBody();
    }

    public Object runWebAgent(String shortCode, String projectId, HttpHeaders httpHeaders, String workspaceId,
        Boolean stream, AgentRunReq body) {
        if (stream == null || stream) {
            String url = runtimeEndpoint + "/v1/agents/chat/" + shortCode + "?workspace_id=" + workspaceId;

            return stream(url, httpHeaders, JsonUtils.encode(body));
        }
        return runtimeClient.runWebAgent(getToken(), shortCode, workspaceId, false, body).getBody();
    }

    public void checkToolsPermission(ToolEntity tool, String projectId, String workspaceId) {
        if (tool == null) {
            throw new AgentStudioException(StudioError.TOOL_NOT_EXIST);
        }
        tool.setPublished(tool.getPublished() == null ? 0 : tool.getPublished());
        if ((!Objects.equals(projectId, tool.getProjectId()) || !Objects.equals(workspaceId, tool.getWorkspaceId()))) {
            if (!opSvcProjectId.equals(tool.getProjectId())) {
                throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION);
            } else if (opSvcProjectId.equals(tool.getProjectId()) && (tool.getPublished() != 1)) {
                throw new AgentStudioException(StudioError.TOOLS_NOT_EXIST_OR_NO_PERMISSION);
            }
        }
    }

    private void checkAgentPermission(String projectId, String workspaceId, String agentId) {
        Agent agent = agentMapper.selectById(agentId);
        if (agent == null) {
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }
        if ((!Objects.equals(projectId, agent.getProjectId()) || !Objects.equals(workspaceId,
            agent.getWorkspaceId()))) {
            if (!opSvcProjectId.equals(agent.getProjectId())) {
                throw new AgentStudioException(StudioError.INSUFFICIENT_AGENT_RUN_PRIVILEGES);
            } else if (opSvcProjectId.equals(agent.getProjectId()) && !agent.getStatus().equals("published")) {
                throw new AgentStudioException(StudioError.INSUFFICIENT_AGENT_RUN_PRIVILEGES);
            }
        }
    }

    public void checkModelBasePermission(ModelServiceBase model, String projectId, String workspaceId) {
        if (model.isPublic()) {
            return;
        }
        if (!"SYSTEM".equals(model.getProjectId()) && !projectId.equals(model.getProjectId())) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
        if (!"SYSTEM".equals(model.getWorkspaceId()) && !workspaceId.equals(model.getWorkspaceId())) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
    }

    public void checkRouterStrategyEntity(RouterStrategyEntity router, String projectId, String workspaceId) {
        if (!"SYSTEM".equals(router.getProjectId()) && !projectId.equals(router.getProjectId())) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
        if (!"SYSTEM".equals(router.getWorkspaceId()) && !workspaceId.equals(router.getWorkspaceId())) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
    }

    public void checkFreeModelPermission(ModelServiceBase model, String projectId, String workspaceId) {
        if (!"SYSTEM".equals(model.getProjectId()) && !projectId.equals(model.getProjectId())) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
        if (!"SYSTEM".equals(model.getWorkspaceId()) && !workspaceId.equals(model.getWorkspaceId())) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
    }

    public void checkModelPermission(String projectId, String workspaceId, String modelId) {
        ModelServiceBase model = modelServiceMapper.queryById(modelId);
        ModelServiceBase freeModel = new ModelServiceBase();
        freeModel = freeModelServiceMapper.queryById(modelId);
        if (model != null) {
            checkModelBasePermission(model, projectId, workspaceId);
            return;
        }
        if (freeModel != null) {
            checkFreeModelPermission(freeModel, projectId, workspaceId);
            return;
        }
        RouterStrategyEntity router = routerStrategyMapper.selectInfoById(modelId);
        if (router == null) {
            throw new AgentStudioException(StudioError.MODEL_SECURITY_CHECK_BLOCK);
        }
        checkRouterStrategyEntity(router, projectId, workspaceId);
    }

    private void checkWorkflowPermission(String projectId, String workspaceId, String workflowId) {
        WorkflowEntity workflowEntity = workflowMapper.getWorkflowById(workflowId);
        if (workflowEntity == null) {
            throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST);
        }
        if ((!Objects.equals(projectId, workflowEntity.getProjectId()) || !Objects.equals(workspaceId,
            workflowEntity.getWorkspaceId())) && !opSvcProjectId.equals(workflowEntity.getProjectId())) {
            throw new AgentStudioException(StudioError.INSUFFICIENT_WORKFLOW_RUN_PRIVILEGES);
        }
    }

    public Object stream(String url, HttpHeaders headers, String bodyJson) {
        return stream(url, headers, bodyJson, 900000L);
    }

    public Object stream(String url, HttpHeaders headers, String bodyJson, Long timeout) {
        RequestBody body = RequestBody.create(bodyJson, MediaType.parse("application/json; charset=utf-8"));

        Request.Builder builder = new Request.Builder();
        headers.forEach((key, value) -> {
            if (value != null && !value.isEmpty()) {
                builder.addHeader(key, String.join(",", value));
            }
        });

        Request request = builder.url(url).post(body).build();
        EventSource.Factory factory = EventSources.createFactory(okHttpClientUtils.getHttpClient());
        SseEmitter sseEmitter = new SseEmitter(timeout);

        String requestId = MDC.get(REQUEST_ID);

        CountDownLatch latch = new CountDownLatch(1);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(MDC.get(REQUEST_ID), latch, sseEmitter);

        // 创建事件
        log.info("http stream request, url: {}", url);
        EventSource eventSource = factory.newEventSource(request, listener);
        try {
            latch.await(30, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            log.error("Request agent service timeout.", e);
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        if (listener.getErrorRsp() != null) {
            return listener.getErrorRsp();
        }
        return sseEmitter;
    }

    public Object stream(String url, HttpHeaders headers, String bodyJson, Long timeout, BaseEventListener listener) {
        RequestBody body = RequestBody.create(bodyJson, MediaType.parse("application/json; charset=utf-8"));

        Request.Builder builder = new Request.Builder();
        headers.forEach((key, value) -> {
            if (value != null && !value.isEmpty()) {
                builder.addHeader(key, String.join(",", value));
            }
        });

        Request request = builder.url(url).post(body).build();
        EventSource.Factory factory = EventSources.createFactory(okHttpClientUtils.getHttpClient());
        SseEmitter sseEmitter = new SseEmitter(timeout);

        CountDownLatch latch = new CountDownLatch(1);
        listener.setLatch(latch);
        listener.setSseEmitter(sseEmitter);

        // 创建事件
        log.info("http stream request, url: {}", url);
        EventSource eventSource = factory.newEventSource(request, listener);
        try {
            latch.await(30, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            log.error("Request agent service timeout.", e);
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        if (listener.getErrorRsp() != null) {
            return listener.getErrorRsp();
        }
        return sseEmitter;
    }

    /**
     * Agent专用流式方法，根据executeType选择LLMAgentListener或ControllerAgentListener处理事件并存储调测数据
     */
    public Object agentStream(String url, HttpHeaders headers, String bodyJson, AgentExecuteParams executeParams) {
        String taskId = agentRuntimeService.queryTaskId(executeParams.getAgentId(), executeParams.getExecutionId());
        if (StringUtils.isEmpty(taskId)) {
            taskId = MDC.get(REQUEST_ID);
        }
        if (StringUtils.isEmpty(taskId)) {
            taskId = headers.getFirst("X-Execution-Id");
        }
        MDC.put(Constant.TASK_ID, taskId);
        headers.set("X-Execution-Id", taskId);
        executeParams.setExecutionId(taskId);

        if (Constant.AppType.CONTROLLER.equals(executeParams.getExecuteType())) {
            ControllerAgentListener listener = new ControllerAgentListener(MDC.get(REQUEST_ID), executeParams, headers);
            return stream(url, headers, bodyJson, 900000L, listener);
        } else if (Constant.AppType.AGENT.equals(executeParams.getExecuteType())) {
            LLMAgentListener listener = new LLMAgentListener(MDC.get(REQUEST_ID), executeParams, headers);
            return stream(url, headers, bodyJson, 900000L, listener);
        } else {
            return stream(url, headers, bodyJson, 900000L, new BaseEventListener(MDC.get(REQUEST_ID), headers));
        }
    }

    /**
     * 工作流专用流式方法，使用WorkflowListener处理事件并存储调测数据
     */
    public Object workflowStream(String url, HttpHeaders headers, String bodyJson, WorkflowRunResult result,
        ExecuteParams executeParams) {
        String taskId = executeParams.getExecutionId();
        if (StringUtils.isEmpty(taskId)) {
            taskId = headers.getFirst("X-Execution-Id");
        }
        if (StringUtils.isEmpty(taskId)) {
            taskId = MDC.get(REQUEST_ID);
        }
        if (StringUtils.isEmpty(taskId)) {
            taskId = UUID.randomUUID().toString();
        }
        MDC.put(Constant.TASK_ID, taskId);
        headers.set("X-Execution-Id", taskId);
        executeParams.setExecutionId(taskId);

        WorkflowListener listener = new WorkflowListener(MDC.get(REQUEST_ID), executeParams, result, headers);
        return stream(url, headers, bodyJson, 900000L, listener);
    }

    @OperationLog(
            operationType = OperationType.EXECUTE,
            resourceType = "agent",
            description = "上传文件"
    )
    public FileUploadRsp uploadAgentFile(MultipartFile file, Integer expiresDays, Boolean isImage) {
        if (file.isEmpty()) {
            log.error("file cannot be empty!");
            throw new AgentStudioException(StudioError.FILE_CANNOT_BE_EMPTY);
        }

        // 文件上传校验
        String safeFileName = checkUploadFile(file, isImage ? CommonConstant.IMAGE : CommonConstant.FILE);
        checkUserCanUpload(file, RequestContextUtils.getRequestUserId());

        return uploadFileToObs(file, expiresDays, safeFileName);
    }

    /**
     * 上传文件到OBS
     *
     * @param file 文件
     * @param expiresDays 过期天数
     * @param safeFileName 安全文件名
     * @return 上传结果
     */
    private FileUploadRsp uploadFileToObs(MultipartFile file, Integer expiresDays, String safeFileName) {
        try {
            InputStream inputStream = file.getInputStream();
            // 设置返回响应体Url和Headers参数
            FileUploadRsp fileUploadRsp = new FileUploadRsp();

            String objectKey = String.format("%s/%s", CommonConstant.FILE, safeFileName);

            String objectName = mgObsService.uploadStreamStagingBucket(objectKey, inputStream, expiresDays);
            String url = mgObsService.getTemporaryGetRsp(true, objectName, (long) expiresDays * 24L * 60* 60);
            fileUploadRsp.setUrl(url);

            return fileUploadRsp;
        } catch (IOException e) {
            log.error("OBS failure", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    private void checkUserCanUpload(MultipartFile file, String userId) {
        checkUploadNum(userId);
        checkUploadTotalSize(file, userId);
    }

    private void checkUploadTotalSize(MultipartFile file, String userId) {
        String key = "uploadFile:new:size:" + userId;
        boolean exist = redisClient.exists(key);
        BigDecimal currentSize = new BigDecimal(file.getSize()).divide(new BigDecimal(KB));
        if (exist) {
            BigDecimal obsSize = new BigDecimal(redisClient.get(key));
            currentSize = currentSize.add(obsSize);
        }

        // 存在 -> 获取已上传的文件大小，与最大值比较
        if (currentSize.compareTo(new BigDecimal(maxUploadTotalSize)) < 0) {
            // 过期时间
            redisClient.setAndKeepTtl(key, String.valueOf(currentSize), Duration.ofSeconds(timeScopeUploadTotalSize));
        } else {
            log.error(
                    "The total size of the upload files exceeds the limit. fileSize:{}, currentSize:{}, maxUploadTotalSize:{}",
                    file.getSize(), currentSize, maxUploadTotalSize);
            throw new AgentStudioException(StudioError.FILE_SIZE_EXCEED_LIMIT);
        }
    }

    private void checkUploadNum(String userId) {
        String key = "uploadFile:num:" + userId;
        long currentCount = redisClient.getAndIncrement(key, timeScopeUploadNum);
        if (currentCount == 0) {
            // 如果是第一次上传，设置过期时间5分钟
            redisClient.expire(key, Duration.ofSeconds(timeScopeUploadNum));
        }
        if (currentCount > maxUploadNum) {
            log.error("The number of the upload files exceeds the limit. currentCount:{}, maxUploadNum:{}",
                    currentCount, maxUploadNum);
            throw new AgentStudioException(StudioError.AGENT_UPLOAD_FILE_NUM);
        }
    }

    /**
     * 上传文件校验
     *
     * @param file 文件
     * @param type 文件类型
     * @return 新生成的文件名
     */
    private String checkUploadFile(MultipartFile file, String type) {
        // 文件为空
        if (file == null || file.isEmpty()) {
            log.error("The uploaded file cannot be empty.");
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        FileCheckWrapper fileCheckWrapper = buildFileCheckWrapper(type);
        // 校验文件大小
        if (file.getSize() > fileCheckWrapper.getSize() * KB) {
            log.error("The avatar file size exceeds the limit: {}KB", iconMaxSize);
            throw new AgentStudioException(StudioError.PICTURE_FILE_SIZE_EXCEED_LIMIT);
        }

        // 校验文件名
        String fileName = file.getOriginalFilename();
        if (org.apache.commons.lang3.StringUtils.isBlank(fileName) || fileName.contains("..") || fileName.contains("\\") || fileName.contains(
                "/")) {
            log.error("The file name is illegal: {}", LogUtils.encodeForLog(fileName));
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_NAME);
        }

        // 校验文件类型
        String fileType = fileName.substring(fileName.lastIndexOf('.'));
        if (org.apache.commons.lang3.StringUtils.isBlank(fileType) || !fileCheckWrapper.getType().contains(fileType.toLowerCase(Locale.ROOT))) {
            log.error("The file type is not supported: {}", LogUtils.encodeForLog(fileType));
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_TYPE);
        }

        // 生成随机名
        return UUID.randomUUID() + fileType;
    }

    /**
     * 根据校验类型获取文件校验包装类
     *
     * @param type 校验类型
     * @return FileCheckWrapper 文件校验包装类
     */
    private FileCheckWrapper buildFileCheckWrapper(String type) {
        FileCheckWrapper.FileCheckWrapperBuilder builder = FileCheckWrapper.builder();
        return switch (type) {
            case CommonConstant.ICON -> builder.size(iconMaxSize).type(allowedIconType).build();
            case CommonConstant.IMAGE -> builder.size(imageMaxSize).type(allowedImgType).build();
            default -> builder.size(fileMaxSize).type(allowedDefaultType).build();
        };
    }
}
