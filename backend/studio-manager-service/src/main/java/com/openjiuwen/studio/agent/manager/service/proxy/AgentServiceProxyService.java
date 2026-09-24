/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.obs.services.model.TemporarySignatureResponse;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventReq;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationReq;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationResp;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.common.dto.run.*;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.common.entity.Text2AudioReq;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorDetail;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.ErrorInfo;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;

import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFailure;
import com.openjiuwen.studio.agent.manager.exception.downstream.DownstreamFailureException;
import feign.FeignException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.*;
import com.openjiuwen.studio.agent.manager.bo.FileCheckWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.observability.ExecutionIdSelector;
import com.openjiuwen.studio.agent.manager.observability.MdcKeys;
import com.openjiuwen.studio.agent.manager.observability.MdcScope;
import com.openjiuwen.studio.agent.manager.observability.OkHttpCorrelationHeaderApplier;
import com.openjiuwen.studio.agent.manager.observability.OutboundCorrelationPolicy;
import com.openjiuwen.studio.agent.manager.dto.*;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationReq;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.common.dto.run.RunToolRequestBody;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.manager.dto.ControllerExecutionDetail;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.Audio2TextReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.StsTextResp;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentManagerEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.insight.WorkflowRunResult;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentManagerMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
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
import com.openjiuwen.studio.agent.manager.rce.client.AgentBuilderClient;
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
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
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
    /** MDC key for request-id，权威来源为 {@link MdcKeys}（COM-02 白名单）。 */
    private static final String REQUEST_ID = MdcKeys.REQUEST_ID;

    private final AgentRuntimeClient runtimeClient;

    private final AgentBuilderClient builderClient;

    private final RedisClient redisClient;

    private final ExecutionIdSelector executionIdSelector = new ExecutionIdSelector();

    private final AgentMapper agentMapper;

    private final WorkflowMapper workflowMapper;

    private final ModelServiceMapper modelServiceMapper;

    private final OkHttpClientUtils okHttpClientUtils;

    private final RouterStrategyMapper routerStrategyMapper;

    private final FreeModelServiceMapper freeModelServiceMapper;

    private final ToolMapper toolMapper;

    private final EnvironmentManagerMapper environmentManagerMapper;

    private final ReleaseChannelMapper releaseChannelMapper;

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

    @Value("${workflow.sse-timeout-milliseconds}")
    private long workflowSseTimeoutMilliSec;

    @Value("${manager.stream-open-await-timeout-seconds:30}")
    private long streamOpenAwaitTimeoutSeconds;

    @Value("${manager.http-failed-publish-await-seconds:10}")
    private long httpFailedPublishAwaitSeconds;

    private Set<String> allowedIconType = new HashSet<>();

    private Set<String> allowedImgType = new HashSet<>();

    private Set<String> allowedDefaultType = new HashSet<>();

    @Autowired
    private IPlugin iPlugin;

    @Autowired
    private I18nUtil i18nUtil;

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

    public AgentServiceProxyService(AgentRuntimeClient runtimeClient, AgentBuilderClient agentBuilderClient, RedisClient redisClient, AgentMapper agentMapper,
        WorkflowMapper workflowMapper, ModelServiceMapper modelServiceMapper, OkHttpClientUtils okHttpClientUtils,
        RouterStrategyMapper routerStrategyMapper, FreeModelServiceMapper freeModelServiceMapper,
        ToolMapper toolMapper, EnvironmentManagerMapper environmentManagerMapper,
        ReleaseChannelMapper releaseChannelMapper,
        AgentRuntimeService agentRuntimeService,
        ControllerDebuggingMgmtService controllerDebuggingMgmtService, MgObsService mgObsService) {
        this.runtimeClient = runtimeClient;
        this.builderClient = agentBuilderClient;
        this.redisClient = redisClient;
        this.agentMapper = agentMapper;
        this.workflowMapper = workflowMapper;
        this.modelServiceMapper = modelServiceMapper;
        this.okHttpClientUtils = okHttpClientUtils;
        this.routerStrategyMapper = routerStrategyMapper;
        this.freeModelServiceMapper = freeModelServiceMapper;
        this.toolMapper = toolMapper;
        this.environmentManagerMapper = environmentManagerMapper;
        this.releaseChannelMapper = releaseChannelMapper;
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
        return streamWithExecutionContext(url, httpHeaders, JsonUtils.encode(body));
    }








    public ResponseEntity<McpValidationResp> testServer(String projectId, McpValidationReq body, String workspaceId) {

        return runtimeClient.testServer(getToken(), projectId, body, workspaceId);
    }

    public Object rerank(HttpHeaders headers, String workspaceId, RankDocumentsRequest request, Boolean refresh,
        String projectId, String apiUrlEnvVars) {
        String modelId = request.getModel();
        checkModelPermission(projectId, workspaceId, modelId);
        String environmentId = headers.getFirst("X-Environment-Id");
        try {
            return builderClient.rerank(getToken(), environmentId, projectId, workspaceId, request, refresh, apiUrlEnvVars);
        } catch (FeignException e) {
            ResponseEntity<Object> errorResponse = parseModelServiceFeignError(e);
            if (errorResponse != null) {
                return errorResponse;
            }
            throw e;
        } catch (DownstreamFailureException e) {
            return parseDownstreamFailureError(e);
        }
    }

    public Object textEmbeddings(HttpHeaders headers, String workspaceId, EmbeddingRequest request, Boolean refresh,
        String projectId, String apiUrlEnvVars) {

        String modelId = request.getModel();
        checkModelPermission(projectId, workspaceId, modelId);
        String environmentId = headers.getFirst("X-Environment-Id");
        try {
            return builderClient.textEmbeddings(getToken(), environmentId, projectId, workspaceId, request, refresh, apiUrlEnvVars);
        } catch (FeignException e) {
            ResponseEntity<Object> errorResponse = parseModelServiceFeignError(e);
            if (errorResponse != null) {
                return errorResponse;
            }
            throw e;
        } catch (DownstreamFailureException e) {
            return parseDownstreamFailureError(e);
        }
    }

    /**
     * 解析模型服务 Feign 调用的错误响应体，提取错误信息及上游 details。
     * 解析失败时退回通用错误码（MD_MODEL_SERVICE_NOT_AVAILABLE），透传上游 HTTP 状态码。
     */
    private ResponseEntity<Object> parseModelServiceFeignError(FeignException e) {
        log.error("Model service call failed via Feign client.", e);
        try {
            String body = e.contentUTF8();
            if (body != null) {
                JSONObject errObj = JSONObject.parseObject(body);
                if (errObj != null && errObj.containsKey("error_code")) {
                    ErrorRsp errorRsp = new ErrorRsp()
                        .setErrorCode(errObj.getString("error_code"))
                        .setErrorMsg(errObj.getString("error_msg"))
                        .setErrorReason(errObj.getString("error_reason"))
                        .setErrorSuggestion(errObj.getString("error_suggestion"));
                    if (errObj.containsKey("details")) {
                        JSONArray detailsArr = errObj.getJSONArray("details");
                        if (detailsArr != null) {
                            List<ErrorDetail> details = new ArrayList<>();
                            for (int i = 0; i < detailsArr.size(); i++) {
                                JSONObject d = detailsArr.getJSONObject(i);
                                if (d != null) {
                                    details.add(new ErrorDetail()
                                        .setErrorMsg(d.getString("error_msg")));
                                }
                            }
                            errorRsp.setDetails(details);
                        }
                    }
                    return ResponseEntity.status(e.status() > 0 ? e.status() : 500).body(errorRsp);
                }
            }
        } catch (Exception parseEx) {
            log.warn("Failed to parse Feign error body.", parseEx);
        }
        // 无法从 Feign 异常解析出 builder 的 error body 时，退回通用错误码（不带构造的 details，
        // 避免透出对用户无意义的异常堆栈信息）
        ErrorInfo errorInfo = i18nUtil.getMessage(
            new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE));
        ErrorRsp errorRsp = new ErrorRsp()
            .setErrorCode(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE.getFullCode())
            .setErrorMsg(errorInfo.getMessage())
            .setErrorReason(errorInfo.getReason())
            .setErrorSuggestion(errorInfo.getSuggestion());
        int status = e.status() > 0 ? e.status() : 500;
        return ResponseEntity.status(status).body(errorRsp);
    }

    /**
     * COM-04 DownstreamFailureException 透传：BuilderFeignConfig 的 DownstreamFeignErrorDecoder
     * 把非 2xx 转 DownstreamFailureException（非 FeignException 子类），catch(FeignException) 不命中。
     * 此方法用 DownstreamFailure.trustedCode 透传 error_code，保留原映射语义（不丢失上游码）。
     */
    private ResponseEntity<Object> parseDownstreamFailureError(DownstreamFailureException e) {
        DownstreamFailure failure = e.getFailure();
        String requestId = MDC.get(MdcKeys.REQUEST_ID);
        ErrorInfo errorInfo = i18nUtil.getMessage(
            new AgentStudioException(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE));
        ErrorRsp errorRsp = new ErrorRsp()
            .setRequestId(requestId)
            .setErrorMsg(errorInfo.getMessage())
            .setErrorReason(errorInfo.getReason())
            .setErrorSuggestion(errorInfo.getSuggestion());
        if (failure.hasTrustedErrorCode()) {
            errorRsp.setErrorCode(failure.getDownstreamErrorCode());
        } else {
            errorRsp.setErrorCode(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE.getFullCode());
            log.warn("DownstreamFailure without trusted code: {}", failure);
        }
        Integer dsStatus = failure.getDownstreamHttpStatus();
        return ResponseEntity.status(dsStatus != null && dsStatus > 0 ? dsStatus : 500).body(errorRsp);
    }

    public Object chatCompletions(HttpHeaders headers, String workspaceId, ChatCompletionRequest request,
        Boolean refresh, String projectId, String apiUrlEnvVars) {

        String modelId = request.getModel();
        checkModelPermission(projectId, workspaceId, modelId);
        if (request.getStream() == null || request.getStream()) {
            String url = agentBuilderEndpoint + "/v1/agent-builder/chat/completions?project_id=" + projectId + "&workspace_id="
                + workspaceId + "&refresh=" + (Boolean.FALSE.equals(refresh) ? "false" : "true");
            if (apiUrlEnvVars != null && !apiUrlEnvVars.isEmpty()) {
                url += "&api_url_env_vars=" + URLEncoder.encode(apiUrlEnvVars, StandardCharsets.UTF_8);
            }

            return streamForBuilder(url, headers, JsonUtils.encode(request));
        }
        String environmentId = headers.getFirst("X-Environment-Id");
        try {
            return builderClient.chatCompletions(getToken(), environmentId, projectId, workspaceId, request, refresh, apiUrlEnvVars);
        } catch (FeignException e) {
            return parseModelServiceFeignError(e);
        } catch (DownstreamFailureException e) {
            return parseDownstreamFailureError(e);
        }
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

    public ResponseEntity<ListControllerExecutionsResp> listControllerExecutions(String projectId, String agentId,
        String conversationId, ListControllerExecutionsQo listControllerExecutionsQo, String workspaceId) {
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

    public ResponseEntity<ControllerExecutionDetail> getControllerExecutionDetail(String projectId, String agentId,
        String executionId, GetControllerExecutionDetailQo body, String workspaceId) {

        ControllerExecutionDetailModel detailModel = controllerDebuggingMgmtService.queryCtrlExecutionDetail(
            agentId, executionId);
        if (detailModel == null || detailModel.getExecutionId() == null) {
            return ResponseEntity.ok(new ControllerExecutionDetail());
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
            return ResponseEntity.ok(new ControllerExecutionDetail());
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
        // 网页短链入口无鉴权：默认环境按 short_code 所属发布通道的 project 解析，
        // 环境变量按 (environment_id, workspace_id) 维度存储，加载 workspace 同样取
        // 发布通道 workspace（对齐 runWebAgent，保证占位符 URL 解析到发布方预期的变量值）
        ReleaseChannel channel = lookupWebReleaseChannel(shortCode);
        String environmentId = resolveChannelDefaultEnvironment(channel, shortCode);
        String forwardWorkspaceId = workspaceId;
        if (StringUtils.hasText(environmentId)) {
            forwardWorkspaceId = channel.getWorkspaceId();
        }
        if (stream == null || stream) {
            String url = runtimeEndpoint + "/v1/workflows/chat/" + shortCode + "/conversations/" + conversationId
                + "?workspace_id=" + forwardWorkspaceId;
            if (StringUtils.hasText(environmentId)) {
                url = url + "&environment_id=" + environmentId;
            }
            try (MdcScope scope = establishExecutionScope(httpHeaders)) {
                return stream(url, httpHeaders, JsonUtils.encode(body));
            }
        }
        try (MdcScope scope = establishExecutionScope(httpHeaders)) {
            return runtimeClient.runWebWorkflow(getToken(), shortCode, conversationId, forwardWorkspaceId,
                environmentId, body, false).getBody();
        }
    }

    /**
     * 智能体运行 environment_id 兜底：入参非空原样返回；
     * 为空时回填项目默认环境 id（单智能体无环境选择，模型 api_url 占位符按默认环境解析）。
     * 查不到默认环境或查询异常返回 null，转发 URL 不带参，行为与不兜底时一致。
     *
     * @param projectId 项目 id
     * @param environmentId 请求携带的 environment_id，可为空
     * @return 实际使用的 environment_id，可能为 null
     */
    public String resolveEnvironmentId(String projectId, String environmentId) {
        if (StringUtils.hasText(environmentId)) {
            return environmentId;
        }
        try {
            List<EnvironmentManagerEntity> defaults = environmentManagerMapper
                .findByProjectIdAndIsDefaultTrue(projectId);
            if (defaults == null || defaults.isEmpty()) {
                return null;
            }
            return defaults.get(0).getId();
        } catch (Exception e) {
            log.error("resolve default environment failed, projectId: {}", projectId, e);
            return null;
        }
    }

    /**
     * 单智能体运行的 environment_id 兜底：入参非空原样返回；为空且目标智能体为
     * 归属请求项目的单智能体（t_agent.type = agent 且 project_id 一致）时回填项目
     * 默认环境 id。多智能体（controller）/高代码（agent_new）/智能体不存在/跨项目
     * 共享智能体（opSvc 归属，checkAgentPermission 允许跨项目调用发布态）/查询
     * 异常一律返回 null，转发不带 environment_id，保持既有运行行为——runtime 会话
     * 路由同时服务单智能体与多智能体（百宝箱试用也复用），默认环境兜底只应作用于
     * 无环境选择的单智能体链路，不向其他类型/归属其它项目的应用注入项目默认环境变量。
     *
     * @param projectId 项目 id
     * @param agentId 智能体 id
     * @param environmentId 请求携带的 environment_id，可为空
     * @return 实际使用的 environment_id，可能为 null
     */
    public String resolveEnvironmentIdForSingleAgent(String projectId, String agentId, String environmentId) {
        if (StringUtils.hasText(environmentId)) {
            return environmentId;
        }
        try {
            Agent agent = agentMapper.selectById(agentId);
            if (agent == null || !CommonConstant.AGENT_TYPE.equals(agent.getType())) {
                return null;
            }
            // 共享智能体（归属项目与请求项目不一致，仅 opSvc 发布态可达）不做兜底：
            // runtime 按 environment:{envId}:workspaceId:{请求workspace} 加载变量，
            // 回填调用方项目默认环境会把发布方占位符 api_url 解析到调用方环境配置的
            // 端点（模型请求重定向、调用方变量值外流）
            if (!Objects.equals(projectId, agent.getProjectId())) {
                log.warn("agent {} belongs to project {}, not request project {}, skip default environment",
                    agentId, agent.getProjectId(), projectId);
                return null;
            }
            return resolveEnvironmentId(projectId, null);
        } catch (Exception e) {
            log.error("resolve single agent default environment failed, projectId: {}, agentId: {}",
                projectId, agentId, e);
            return null;
        }
    }

    public Object runWebAgent(String shortCode, String projectId, HttpHeaders httpHeaders, String workspaceId,
        Boolean stream, AgentRunReq body) {
        // 网页短链入口无鉴权：路径 project_id 与请求 workspace_id 均不可信
        // - 默认环境按 short_code 所属发布通道的 project 解析，与 runtime 侧按 Redis
        //   release_web_rel_{short_code} 中的 project_id 构造执行上下文的做法一致
        // - 环境变量按 (environment_id, workspace_id) 维度存储，加载 workspace 同样
        //   取发布通道 workspace：请求 workspace_id 可被换成发布项目下其它 workspace，
        //   选取该项目其它空间写入的变量值，使占位符 api_url 解析到非发布方预期端点
        // - workspace_id 在本执行链仅用于环境变量加载：未解析到默认环境时
        //   environment_id 缺省、runtime 不加载变量，请求 workspace 原样转发
        ReleaseChannel channel = lookupWebReleaseChannel(shortCode);
        String environmentId = resolveChannelDefaultEnvironment(channel, shortCode);
        String forwardWorkspaceId = workspaceId;
        if (StringUtils.hasText(environmentId)) {
            forwardWorkspaceId = channel.getWorkspaceId();
        }
        if (stream == null || stream) {
            String url = runtimeEndpoint + "/v1/agents/chat/" + shortCode + "?workspace_id=" + forwardWorkspaceId;
            if (StringUtils.hasText(environmentId)) {
                url = url + "&environment_id=" + environmentId;
            }
            try (MdcScope scope = establishExecutionScope(httpHeaders)) {
                return stream(url, httpHeaders, JsonUtils.encode(body));
            }
        }
        try (MdcScope scope = establishExecutionScope(httpHeaders)) {
            return runtimeClient.runWebAgent(getToken(), shortCode, forwardWorkspaceId, false, environmentId,
                body).getBody();
        }
    }

    /**
     * 以 short_code 反查网页发布通道：WEB_PAGE / CLOUD_STORE 两类网页渠道均生成
     * short_code，逐类反查（channelType 是 SQL 硬等值，不能传 null；projectId/id
     * 传 null 走 if 跳过）。通道不存在或查表异常返回 null。
     *
     * @param shortCode 网页短链码
     * @return 发布通道，可能为 null
     */
    private ReleaseChannel lookupWebReleaseChannel(String shortCode) {
        try {
            ReleaseChannel channel = releaseChannelMapper.selectByChannelIdOrShortCode(
                null, null, shortCode, CommonConstant.WEB_PAGE_CHANNEL);
            if (channel == null) {
                channel = releaseChannelMapper.selectByChannelIdOrShortCode(
                    null, null, shortCode, CommonConstant.CLOUD_STORE_CHANNEL);
            }
            return channel;
        } catch (Exception e) {
            log.error("lookup web release channel failed, shortCode: {}", shortCode, e);
            return null;
        }
    }

    /**
     * 按网页发布通道解析默认环境：以通道所属 project 为准（不信任请求路径
     * project_id）。通道不存在、发布应用非单智能体/工作流（appType 不属于
     * agent / workflow，如多智能体发布，不走本兜底）、通道 workspace 缺失
     * （无法安全确定环境变量加载维度，宁可不放行也不回退到请求 workspace）或
     * 项目无默认环境时返回 null，转发不带 environment_id，行为与项目未配置
     * 默认环境一致（占位符 URL 报错，不会借用其它项目/其它空间的环境变量）。
     *
     * @param channel 网页发布通道，可为 null
     * @param shortCode 网页短链码（仅用于日志）
     * @return 默认环境 id，可能为 null
     */
    private String resolveChannelDefaultEnvironment(ReleaseChannel channel, String shortCode) {
        if (channel == null || !StringUtils.hasText(channel.getProjectId())) {
            log.warn("web release channel not found or missing project, skip default environment, shortCode: {}",
                shortCode);
            return null;
        }
        if (!CommonConstant.AGENT_TYPE.equals(channel.getAppType())
            && !CommonConstant.WORKFLOW_TYPE.equals(channel.getAppType())) {
            log.warn("web release channel app is not single agent or workflow, skip default environment, shortCode: {}, "
                + "appType: {}", shortCode, channel.getAppType());
            return null;
        }
        if (!StringUtils.hasText(channel.getWorkspaceId())) {
            log.warn("web release channel missing workspace, skip default environment, shortCode: {}", shortCode);
            return null;
        }
        return resolveEnvironmentId(channel.getProjectId(), null);
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
        return stream(url, headers, bodyJson, workflowSseTimeoutMilliSec);
    }

    public Object stream(String url, HttpHeaders headers, String bodyJson, Long timeout) {
        return streamNoListener(url, headers, bodyJson, timeout,
            OutboundCorrelationPolicy.RUNTIME_EXECUTION, runtimeEndpoint);
    }

    public Object stream(String url, HttpHeaders headers, String bodyJson, Long timeout, BaseEventListener listener) {
        Request request = buildStreamRequest(url, headers, bodyJson,
            OutboundCorrelationPolicy.RUNTIME_EXECUTION, runtimeEndpoint);
        EventSource.Factory factory =
            EventSources.createFactory(OkHttpCorrelationHeaderApplier.withoutRedirects(okHttpClientUtils.getHttpClient()));
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
     * COM-04 §6.2：构建出站 SSE 请求——先排除三个关联 Header（防调用方伪造重复变体），
     * 再由 {@link OkHttpCorrelationHeaderApplier} 按策略从当前线程 MDC 读取权威值先删后写。
     */
    private okhttp3.Request buildStreamRequest(String url, HttpHeaders headers, String bodyJson,
        OutboundCorrelationPolicy policy, String allowedOrigin) {
        RequestBody body = RequestBody.create(bodyJson, MediaType.parse("application/json; charset=utf-8"));
        Request.Builder builder = new Request.Builder();
        headers.forEach((key, value) -> {
            if (value != null && !value.isEmpty() && !OkHttpCorrelationHeaderApplier.isCorrelationHeader(key)) {
                builder.addHeader(key, String.join(",", value));
            }
        });
        builder.url(url).post(body);
        OkHttpCorrelationHeaderApplier.apply(policy, allowedOrigin, url, builder);
        return builder.build();
    }

    /**
     * COM-04 §6.2：无自定义 listener 的流式调用——5-arg {@link ProxyEventSourceListener}，
     * 禁用重定向的客户端变体（防关联 Header 被携带到新 origin），COM-03 awaitStreamOpen 协议。
     */
    private Object streamNoListener(String url, HttpHeaders headers, String bodyJson, Long timeout,
        OutboundCorrelationPolicy policy, String allowedOrigin) {
        Request request = buildStreamRequest(url, headers, bodyJson, policy, allowedOrigin);
        EventSource.Factory factory =
            EventSources.createFactory(OkHttpCorrelationHeaderApplier.withoutRedirects(okHttpClientUtils.getHttpClient()));
        SseEmitter sseEmitter = new SseEmitter(timeout);

        CountDownLatch latch = new CountDownLatch(1);
        // COM-03 §5.1: 入口 locale 快照——从请求 Header 捕获,不用线程默认 locale
        String langHeader = org.apache.commons.lang3.StringUtils.defaultIfEmpty(
            org.springframework.web.context.request.RequestContextHolder.getRequestAttributes() != null
                ? ((org.springframework.web.context.request.ServletRequestAttributes)
                    org.springframework.web.context.request.RequestContextHolder.getRequestAttributes())
                    .getRequest().getHeader("x-language")
                : null,
            "zh-CN");
        java.util.Locale localeSnapshot = java.util.Locale.forLanguageTag(langHeader);
        ProxyEventSourceListener listener = new ProxyEventSourceListener(
            MDC.get(MdcKeys.REQUEST_ID), latch, sseEmitter,
            (key, loc) -> i18nUtil.getMessage(key, loc), localeSnapshot);

        log.info("http stream request, url: {}", url);
        EventSource eventSource = factory.newEventSource(request, listener);
        // COM-03 复审8 §4.2: SseEmitter 生命周期回调——客户端断开/超时/完成时
        // 幂等取消上游 EventSource，防止下游继续占用连接与生成资源
        listener.bindEmitterLifecycle(sseEmitter, eventSource);
        return awaitStreamOpen(latch, listener, sseEmitter, eventSource);
    }

    /**
     * COM-03 复审10 §3.2: 统一流式等待协议——OPENED→emitter / HTTP_FAILED→errorRsp /
     * CANCELLED / WAIT_TIMEOUT / INTERRUPTED，含二次 await + guard 竞争处理。
     */
    Object awaitStreamOpen(CountDownLatch latch, ProxyEventSourceListener listener,
            SseEmitter sseEmitter, EventSource eventSource) {
        boolean opened;
        try {
            opened = latch.await(streamOpenAwaitTimeoutSeconds, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Stream open wait interrupted.", e);
            listener.tryCancelTerminal();
            cleanupStreamResources(listener, sseEmitter, eventSource);
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        if (listener.getErrorRsp() != null) {
            return listener.getErrorRsp();
        }
        if (opened && !listener.isCancelled()) {
            return sseEmitter;
        }
        if (listener.tryAbortBeforeOpen()) {
            log.error("Stream open wait timed out; abort before open.");
            cleanupStreamResources(listener, sseEmitter, eventSource);
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        if (listener.isCancelled()) {
            log.error("Stream cancelled before open.");
            cleanupStreamResources(listener, sseEmitter, eventSource);
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        if (listener.isHttpFailed()) {
            log.warn("Stream open wait timed out while HTTP failure result pending publish.");
            boolean published;
            try {
                published = latch.await(httpFailedPublishAwaitSeconds, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.error("HTTP failure publish wait interrupted.", e);
                cleanupStreamResources(listener, sseEmitter, eventSource);
                throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
            }
            if (published && listener.getErrorRsp() != null) {
                return listener.getErrorRsp();
            }
            cleanupStreamResources(listener, sseEmitter, eventSource);
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        cleanupStreamResources(listener, sseEmitter, eventSource);
        throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
    }

    private void cleanupStreamResources(ProxyEventSourceListener listener,
            SseEmitter sseEmitter, EventSource eventSource) {
        listener.cancelUpstream(eventSource);
        try {
            sseEmitter.complete();
        } catch (Throwable ignored) {
            // already closing — complete 异常不替换主异常
        }
    }

    /**
     * COM-04 §6.3：Builder 流式调用——固定 BUILDER 策略，注入 request/trace、删除 execution，
     * origin 校验与 {@code agentBuilderEndpoint} 一致。
     */
    public Object streamForBuilder(String url, HttpHeaders headers, String bodyJson) {
        return streamNoListener(url, headers, bodyJson, workflowSseTimeoutMilliSec,
            OutboundCorrelationPolicy.BUILDER, agentBuilderEndpoint);
    }

    /**
     * DEF-02 §4.1：为无 executeParams 的执行入口（如 node_execute）选定 execution ID，
     * 在当前线程建立 EXECUTION_ID 的 partial-override scope（close 恢复）。
     */
    public Object streamWithExecutionContext(String url, HttpHeaders headers, String bodyJson) {
        return streamWithExecutionContext(url, headers, bodyJson, workflowSseTimeoutMilliSec);
    }

    public Object streamWithExecutionContext(String url, HttpHeaders headers, String bodyJson, Long timeout) {
        ExecutionIdSelector.Result selection = executionIdSelector.select(
            null, MDC.get(MdcKeys.EXECUTION_ID), headers.getFirst("X-Execution-Id"));
        if (selection.isRestoreIllegal()) {
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        String executionId = selection.getValue();
        try (MdcScope scope = MdcScope.open(Map.of(MdcKeys.EXECUTION_ID, executionId))) {
            return stream(url, headers, bodyJson, timeout);
        }
    }

    /**
     * DEF-02 §4.1：从当前线程 MDC 读取 execution-id 候选，建立 EXECUTION_ID scope 供 runWeb* 路径包装。
     */
    public MdcScope establishExecutionScope(HttpHeaders headers) {
        ExecutionIdSelector.Result selection = executionIdSelector.select(
            null, MDC.get(MdcKeys.EXECUTION_ID), headers.getFirst("X-Execution-Id"));
        if (selection.isRestoreIllegal()) {
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        return MdcScope.open(Map.of(MdcKeys.EXECUTION_ID, selection.getValue()));
    }

    /**
     * Agent专用流式方法，根据executeType选择LLMAgentListener或ControllerAgentListener处理事件并存储调测数据
     */
    public Object agentStream(String url, HttpHeaders headers, String bodyJson, AgentExecuteParams executeParams) {
        // DEF-02 §4.1：四级优先级选值——恢复值(Redis) > 内部 executeParams.executionId > 入站 X-Execution-Id > 生成
        String restored = "";
        if (!StringUtils.isEmpty(executeParams.getConversationId())) {
            restored = agentRuntimeService.queryResumeExecutionId(
                executeParams.getAgentId(), executeParams.getConversationId());
        }
        ExecutionIdSelector.Result selection = executionIdSelector.select(
            restored, executeParams.getExecutionId(), headers.getFirst("X-Execution-Id"));
        if (selection.isRestoreIllegal()) {
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        String executionId = selection.getValue();
        executeParams.setExecutionId(executionId);

        try (MdcScope scope = MdcScope.open(Map.of(MdcKeys.EXECUTION_ID, executionId))) {
            if (Constant.AppType.CONTROLLER.equals(executeParams.getExecuteType())) {
                ControllerAgentListener listener =
                    new ControllerAgentListener(MDC.get(MdcKeys.REQUEST_ID), executeParams, headers);
                return stream(url, headers, bodyJson, workflowSseTimeoutMilliSec, listener);
            } else if (Constant.AppType.AGENT.equals(executeParams.getExecuteType())) {
                LLMAgentListener listener =
                    new LLMAgentListener(MDC.get(MdcKeys.REQUEST_ID), executeParams, headers);
                return stream(url, headers, bodyJson, workflowSseTimeoutMilliSec, listener);
            } else {
                return stream(url, headers, bodyJson, workflowSseTimeoutMilliSec,
                    new BaseEventListener(MDC.get(MdcKeys.REQUEST_ID), headers));
            }
        }
    }

    /**
     * 工作流专用流式方法，使用WorkflowListener处理事件并存储调测数据
     */
    public Object workflowStream(String url, HttpHeaders headers, String bodyJson, WorkflowRunResult result,
        ExecuteParams executeParams) {
        // 恢复场景：从 Redis 查询上一次中断时保存的 resume executionId，保持 execution_id 一致
        String restored = agentRuntimeService.queryResumeExecutionId(
            executeParams.getWorkflowId(), executeParams.getConversationId());
        ExecutionIdSelector.Result selection = executionIdSelector.select(
            restored, executeParams.getExecutionId(), headers.getFirst("X-Execution-Id"));
        if (selection.isRestoreIllegal()) {
            throw new AgentStudioException(StudioError.CALL_RUNTIME_ERROR);
        }
        String executionId = selection.getValue();
        executeParams.setExecutionId(executionId);

        try (MdcScope scope = MdcScope.open(Map.of(MdcKeys.EXECUTION_ID, executionId))) {
            WorkflowListener listener =
                new WorkflowListener(MDC.get(MdcKeys.REQUEST_ID), executeParams, result, headers);
            return stream(url, headers, bodyJson, workflowSseTimeoutMilliSec, listener);
        }
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
            String maxSizeReadable = String.valueOf(maxUploadTotalSize / KB);
            long hours = timeScopeUploadTotalSize / 3600;
            String timeWindowReadable = String.valueOf(hours > 0 ? hours : timeScopeUploadTotalSize);
            throw new AgentStudioException(StudioError.FILE_SIZE_EXCEED_LIMIT, maxSizeReadable, timeWindowReadable);
        }
    }

    private void checkUploadNum(String userId) {
        String key = "uploadFile:num:" + userId;
        long currentCount = redisClient.getAndIncrement(key, timeScopeUploadNum);
        if (currentCount == 0) {
            // 如果是第一次上传，设置过期时间5分钟
            redisClient.expire(key, Duration.ofSeconds(timeScopeUploadNum));
        }
        // 用自增前的值判断：第 1~maxUploadNum 次返回 0~maxUploadNum-1，均放行；
        // 第 maxUploadNum+1 次返回 maxUploadNum，>= 判定拒绝，与文案"最多上传N个"严格一致
        if (currentCount >= maxUploadNum) {
            log.error("The number of the upload files exceeds the limit. currentCount:{}, maxUploadNum:{}",
                    currentCount, maxUploadNum);
            long minutes = timeScopeUploadNum / 60;
            String timeWindowReadable = String.valueOf(minutes > 0 ? minutes : timeScopeUploadNum);
            throw new AgentStudioException(StudioError.AGENT_UPLOAD_FILE_NUM,
                    String.valueOf(maxUploadNum), timeWindowReadable);
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
            log.error("The file size exceeds the limit: {}KB", fileCheckWrapper.getSize());
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
