/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.openjiuwen.studio.agent.common.annotation.OperationLog;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Feedback;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventReq;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.ListUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationResp;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.common.dto.run.AgentExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
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
import com.openjiuwen.studio.agent.common.dto.run.ResumeTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.TaskListRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskRsp;
import com.openjiuwen.studio.agent.common.dto.tool.RunToolResponseBody;
import com.openjiuwen.studio.agent.common.entity.Text2AudioReq;
import com.openjiuwen.studio.agent.common.enums.OperationType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
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
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationMemoryQo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.manager.dto.runtime.StsTextResp;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;

import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
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
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

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

    @Value("${agent_runtime_endpoint:}")
    private String runtimeEndpoint;

    @Value("${env.type}")
    private String envType;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Autowired
    private IPlugin iPlugin;

    private String getToken() {
        return RequestContextUtils.getRequestAuthToken();
    }

    public AgentServiceProxyService(AgentRuntimeClient runtimeClient, RedisClient redisClient, AgentMapper agentMapper,
        WorkflowMapper workflowMapper, ModelServiceMapper modelServiceMapper, OkHttpClientUtils okHttpClientUtils,
        RouterStrategyMapper routerStrategyMapper, FreeModelServiceMapper freeModelServiceMapper,
        ToolMapper toolMapper) {
        this.runtimeClient = runtimeClient;
        this.redisClient = redisClient;
        this.agentMapper = agentMapper;
        this.workflowMapper = workflowMapper;
        this.modelServiceMapper = modelServiceMapper;
        this.okHttpClientUtils = okHttpClientUtils;
        this.routerStrategyMapper = routerStrategyMapper;
        this.freeModelServiceMapper = freeModelServiceMapper;
        this.toolMapper = toolMapper;
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

    public ResponseEntity<ConversionQueries> listConversationQueries(String projectId, String workflowId,
        ListConversationQueriesQo listConversationQueriesQo, String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.listConversationQueries(getToken(), projectId, workflowId, listConversationQueriesQo,
            workspaceId);
    }

    public ResponseEntity<ExecutionQueries> listExecutionQueries(String projectId, String workflowId,
        String conversationId, ListExecutionQueriesQo listExecutionQueriesQo, String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.listExecutionQueries(getToken(), projectId, workflowId, conversationId,
            listExecutionQueriesQo, workspaceId);
    }

    public ResponseEntity<ExecutionInfo> getExecutionInsight(String projectId, String workflowId, String executionId,
        GetExecutionInsightQo getExecutionInsightQo, String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.getExecutionInsight(getToken(), projectId, workflowId, executionId, getExecutionInsightQo,
            workspaceId);
    }

    public ResponseEntity<List<Message>> retrieveConversation(String projectId, String agentId, String conversationId,
        RetrieveConversationQo retrieveConversationQo, String workspaceId) {

        // agentId可能是workflowId
        try {
            checkWorkflowPermission(projectId, workspaceId, agentId);
        } catch (AgentStudioException e) {
            if (StudioError.WORKFLOW_NOT_EXIST == e.getErrorCode()) {
                checkAgentPermission(projectId, workspaceId, agentId);
            } else {
                throw e;
            }
        }
        return runtimeClient.retrieveConversation(getToken(), projectId, agentId, conversationId,
            retrieveConversationQo, workspaceId);
    }

    public ResponseEntity<ConversationDeleteResp> deleteConversation(String projectId, String agentId,
        String conversationId, String versionId, String workspaceId) {
        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.deleteConversation(getToken(), projectId, agentId, conversationId, versionId, workspaceId);
    }

    public ResponseEntity<TaskRsp> createTask(String projectId, String workflowId, String version, String workspaceId,
        CreateTaskReq body) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.createTask(getToken(), projectId, workflowId, version, workspaceId, body);
    }

    public ResponseEntity<TaskListRsp> listTask(String projectId, String workflowId, ListTaskQo listTaskQo,
        String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.listTask(getToken(), projectId, workflowId, listTaskQo.getStatus(), listTaskQo.getType(), listTaskQo.getSort(), listTaskQo.getOrder(), workspaceId);
    }

    public ResponseEntity<TaskRsp> retrieveTask(String projectId, String workflowId, String taskId, String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.retrieveTask(getToken(), projectId, workflowId, taskId, workspaceId);
    }

    public ResponseEntity<TaskRsp> resumeTask(String projectId, String workflowId, String taskId, String workspaceId,
        ResumeTaskReq body) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.resumeTask(getToken(), projectId, workflowId, taskId, workspaceId, body);
    }

    public ResponseEntity<TaskRsp> modifyTask(String projectId, String workflowId, String taskId, String workspaceId,
        ModifyTaskReq body) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.modifyTask(getToken(), projectId, workflowId, taskId, workspaceId, body);
    }

    public ResponseEntity<CommonDeleteRsp> deleteTask(String projectId, String workflowId, String taskId,
        String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.deleteTask(getToken(), projectId, workflowId, taskId, workspaceId);
    }

    public ResponseEntity<CancelTaskRsp> cancelTask(String projectId, String workflowId, String taskId,
        String workspaceId) {

        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.cancelTask(getToken(), projectId, workflowId, taskId, workspaceId);
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
            String url = runtimeEndpoint + "/v1/agent-builder/chat/completions?project_id=" + projectId + "&workspace_id="
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

    public ResponseEntity<AgentExecutionQueries> listAgentExecutionQueries(String projectId, String agentId,
        String conversationId, ListAgentExecutionQueriesQo listAgentExecutionQueriesQo, String workspaceId) {

        return runtimeClient.listAgentExecutionQueries(getToken(), projectId, agentId, conversationId,
            listAgentExecutionQueriesQo, workspaceId);
    }

    public ResponseEntity<AgentExecutionInfo> getAgentExecutionInfo(String projectId, String executionId,
        String agentId, GetAgentExecutionInfoQo getAgentExecutionInfoQo, String workspaceId) {

        return runtimeClient.getAgentExecutionInfo(getToken(), projectId, executionId, agentId, getAgentExecutionInfoQo,
            workspaceId);
    }

    public ResponseEntity<AsrRsp> voiceRecognition(String projectId, AsrReq body, String workspaceId) {

        return runtimeClient.voiceRecognition(getToken(), projectId, body, workspaceId);
    }

    public ResponseEntity<ConversionQueries> listAgentConversations(String projectId, String agentId,
        ListAgentConversationsQo listAgentConversationsQo, String workspaceId, String type) {

        checkAgentPermission(projectId, workspaceId, agentId);
        return runtimeClient.listAgentConversations(getToken(), projectId, agentId, listAgentConversationsQo,
            workspaceId);
    }

    public ResponseEntity<Status> abortConversation(String projectId, String workflowId, String conversationId,
        String workspaceId) {
        checkWorkflowPermission(projectId, workspaceId, workflowId);
        return runtimeClient.abortConversation(getToken(), projectId, workflowId, conversationId, workspaceId);
    }
    //  MCP\rerank\Embedding 待确认鉴权方式

    public ResponseEntity<Object> listControllerExecutions(String projectId, String agentId, String conversationId,
        ListControllerExecutionsQo listControllerExecutionsQo, String workspaceId) {
        return runtimeClient.listControllerExecutions(getToken(), projectId, agentId, conversationId, workspaceId,
            listControllerExecutionsQo);
    }

    public ResponseEntity<Object> getControllerExecutionDetail(String projectId, String agentId, String executionId,
        GetControllerExecutionDetailQo body, String workspaceId) {

        ResponseEntity<Object> getControllerExecutionDetailResp = runtimeClient.getControllerExecutionDetail(getToken(),
            projectId, agentId, executionId, workspaceId, body);
        Object respBody = getControllerExecutionDetailResp.getBody();
        if (respBody == null) {
            return getControllerExecutionDetailResp;
        }

        try {
            JSONObject controllerExecutionDetail = JSONObject.parseObject(JSONObject.toJSONString(respBody));

            JSONArray nestedWorkflowArr = controllerExecutionDetail.getJSONArray("nestedWorkflows");
            if (nestedWorkflowArr != null && !nestedWorkflowArr.isEmpty()) {
                List<String> nestedWorkflowIds = nestedWorkflowArr.stream()
                    .map(workflow -> ((JSONObject) workflow).getString("workflow_id"))
                    .toList();

                List<WorkflowEntity> workflowEntities = workflowMapper.selectByWorkflowIds(projectId, workspaceId,
                    nestedWorkflowIds);
                List<JSONObject> workflowBaseDataList = workflowEntities.stream().map(workflowEntity -> {
                    JSONObject workflowBaseData = new JSONObject();
                    workflowBaseData.put("workflow_id", workflowEntity.getId());
                    workflowBaseData.put("workflow_name", workflowEntity.getName());

                    return workflowBaseData;
                }).toList();

                controllerExecutionDetail.put("nestedWorkflows", workflowBaseDataList);
            }

            return ResponseEntity.ok(controllerExecutionDetail);
        } catch (Exception e) {
            return getControllerExecutionDetailResp;
        }
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
        EventSource.Factory factory = factory = EventSources.createFactory(okHttpClientUtils.getHttpClient());
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
}
