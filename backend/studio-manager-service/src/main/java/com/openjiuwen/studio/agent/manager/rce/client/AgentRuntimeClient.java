/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.rce.client;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.dto.BatchDeleteUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Feedback;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventReq;
import com.openjiuwen.studio.agent.common.dto.analytics.AnalyticsEventResp;
import com.openjiuwen.studio.agent.common.dto.knowledge.ListUserVariableMemoryResponseBody;
import com.openjiuwen.studio.agent.common.dto.mcp.McpCallToolResp;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationReq;
import com.openjiuwen.studio.agent.common.dto.mcp.McpValidationResp;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckRsp;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.run.CreateTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.GetControllerExecutionDetailQo;
import com.openjiuwen.studio.agent.common.dto.run.GetExecutionInsightQo;
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
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteUserVariableMemoryRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.McpServerReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerTools;
import com.openjiuwen.studio.agent.manager.dto.MemoryVariable;
import com.openjiuwen.studio.agent.manager.dto.ReleaseInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowRunReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.Audio2TextReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.StsTextResp;
import com.openjiuwen.studio.agent.manager.rce.models.AskModelReq;
import com.openjiuwen.studio.agent.manager.rce.models.McpCallToolRequest;
import com.openjiuwen.studio.prompt.engineering.dto.IndustryVo;

import io.swagger.annotations.ApiParam;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import reactor.core.publisher.Flux;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.cloud.openfeign.SpringQueryMap;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * agent runtime服务client
 *
 */
@FeignClient(name = "agentRuntime", url = "${feign.client.config.agentRuntime.url:}")
public interface AgentRuntimeClient {
    /**
     * 同步应用发布信息接口
     *
     * @param authToken 认证token
     * @param projectId projectId信息
     * @return String
     */
    @PostMapping("/v1/{project_id}/releases")
    ResponseEntity<String> createReleaseInfo(@RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @RequestBody ReleaseInfo body);

    /**
     * 删除应用发布信息接口
     *
     * @param authToken 认证token
     * @param projectId projectId信息
     */
    @DeleteMapping("/v1/{project_id}/releases/{release_id}")
    ResponseEntity<String> deleteReleaseInfo(@RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("release_id") String releaseId,
        @NotNull @ApiParam(value = "发布通道类型", required = true)
        @RequestParam(value = "channel_type", required = true) String channelType,
        @ApiParam(value = "版本ID") @RequestParam(value = "version_id", required = false) String versionId);

    /**
     * 查询 mcp 服务工具列表
     *
     * @param authToken 认证 token
     * @param projectId project id
     * @param body      mcp 服务信息
     * @return mcp 服务工具列表
     */
    @PostMapping("/v1/{project_id}/mcp-servers/tools")
    ResponseEntity<McpServerTools> queryMcpServerTools(@RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @RequestBody McpServerReq body);

    /**
     * 运行模型调用接口
     *
     * @param authToken   String
     * @param askModelReq AskModelReq
     * @return 响应体
     */
    @PostMapping(path = "/v1/agent-builder/chat/completions", consumes = MediaType.APPLICATION_JSON_VALUE,
        produces = MediaType.APPLICATION_JSON_VALUE)
    ResponseEntity<JSONObject> askModel(@RequestHeader("X-Auth-Token") String authToken,
        @RequestHeader(value = "X-Auth-Id", required = false) String authId, @RequestBody AskModelReq askModelReq);

    /**
     * 运行 mcp 服务指定工具
     *
     * @param authToken 认证 token
     * @param projectId project id
     * @param body      工具运行信息
     * @return mcp 工具运行结果
     */
    @PostMapping("/v1/{project_id}/mcp-servers/tools/run")
    ResponseEntity<McpCallToolResp> callMcpServerTool(@RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @RequestBody McpCallToolRequest body);

    @PostMapping("/v1/{project_id}/model-service/status/check")
    ResponseEntity<ModelServiceCheckRsp> modelServiceAvailableCheck(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @RequestBody ModelServiceCheckReq request);

    /**
     * 运行 agent，带会话 id
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping("/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}")
    ResponseEntity<Object> runAgentWithConversation(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestHeader(value = CommonConstant.AUTHORIZATION, required = false) String authorization,
        @PathVariable(value = "project_id") String projectId, @PathVariable(value = "agent_id") String agentId,
        @PathVariable(value = "conversation_id") String conversationId,
        @RequestParam(value = "workspace_id") String workspaceId, @RequestParam(value = "agent_type") String agentType,
        @RequestParam(value = "version") String version, @RequestParam(value = "type") String type,
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @RequestBody Object request);

    /**
     * 运行 agent，带会话 id, 流式
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping("/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}")
    Flux<Object> runAgentWithConversationStream(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestHeader(value = CommonConstant.AUTHORIZATION, required = false) String authorization,
        @PathVariable(value = "project_id") String projectId, @PathVariable(value = "agent_id") String agentId,
        @PathVariable(value = "conversation_id") String conversationId,
        @RequestParam(value = "workspace_id") String workspaceId, @RequestParam(value = "agent_type") String agentType,
        @RequestParam(value = "version") String version, @RequestParam(value = "type") String type,
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @RequestBody Object request);

    /**
     * 运行 agent
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping("/v1/{project_id}/agents/{agent_id}/conversations")
    ResponseEntity<Object> runAgent(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @PathVariable(value = "agent_id") String agentId,
        @RequestParam(value = "workspace_id") String workspaceId, @RequestParam(value = "agent_type") String agentType,
        @RequestParam(value = "version") String version,
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @RequestBody Object request);

    /**
     * 运行 agent，流式
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping("/v1/{project_id}/agents/{agent_id}/conversations")
    Flux<Object> runAgentStream(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestHeader(value = CommonConstant.AUTHORIZATION, required = false) String authorization,
        @PathVariable(value = "project_id") String projectId, @PathVariable(value = "agent_id") String agentId,
        @RequestParam(value = "workspace_id") String workspaceId, @RequestParam(value = "agent_type") String agentType,
        @RequestParam(value = "version") String version,
        @RequestParam(value = "environment_id", required = false) String environmentId,
        @RequestBody Object request);

    /**
     * 运行工作流
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping("/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}")
    ResponseEntity<Object> runWorkflowWithConversation(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @PathVariable(value = "workflow_id") String workflowId,
        @PathVariable(value = "conversation_id") String conversationId,
        @RequestParam(value = "workspace_id") String workspaceId,
        @RequestParam(value = "environment_id") String environmentId, @RequestParam(value = "version") String version,
        @RequestBody Object request);

    /**
     * 运行工作流，流式
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping("/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}")
    Flux<Object> runWorkflowWithConversationStream(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestHeader(value = CommonConstant.AUTHORIZATION, required = false) String authorization,
        @PathVariable(value = "project_id") String projectId, @PathVariable(value = "workflow_id") String workflowId,
        @PathVariable(value = "conversation_id") String conversationId,
        @RequestParam(value = "workspace_id") String workspaceId,
        @RequestParam(value = "environment_id") String environmentId, @RequestParam(value = "version") String version,
        @RequestBody Object request);

    /**
     * 上传文件
     */
    @SuppressWarnings("checkstyle: all")
    @PostMapping(value = "/v1/{project_id}/agent-runtime/upload-file", consumes = {MediaType.MULTIPART_FORM_DATA_VALUE})
    ResponseEntity<Object> uploadAgentFile(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId, @RequestParam(value = "workspace_id") String workspaceId,
        @RequestParam(CommonConstant.X_EXPIRES) Integer expires,
        @RequestParam(CommonConstant.X_IS_IMAGE) Boolean isImage, @RequestPart(value = "file") MultipartFile file);

    /**
     * 根据conversation_id重置会话记忆
     */
    @PostMapping("/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-variables/reset")
    ResponseEntity<List<MemoryVariable>> resetConversationMemory(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId,
        @PathVariable(value = "conversation_id") String conversationId,
        @PathVariable(value = "agent_id") String agentId, @RequestParam(value = "version_id") String versionId);

    /**
     * 根据conversation_id查询会话记忆
     */
    @GetMapping("/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-variables")
    ResponseEntity<List<MemoryVariable>> retrieveConversationMemory(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId,
        @PathVariable(value = "conversation_id") String conversationId,
        @PathVariable(value = "agent_id") String agentId,
        @SpringQueryMap RetrieveConversationMemoryQo retrieveConversationMemoryQo);

    @PostMapping("/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/node_execute/{node_id}")
    Flux<Object> runWorkflowNodeExecute(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable(value = "project_id") String projectId,
        @RequestParam(value = "workspace_id") String workspaceId,
        @RequestParam(value = "environment_id") String environmentId,
        @PathVariable(value = "workflow_id") String workflowId,
        @PathVariable(value = "conversation_id") String conversationId, @PathVariable(value = "node_id") String nodeId,
        @RequestBody WorkflowRunReq body);

    @PostMapping("/v1/{project_id}/apps/{app_id}/conversions/{conversation_id}/messages/{message_id}/feedback")
    ResponseEntity<String> createUserFeedback(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("app_id") String appId, @PathVariable("conversation_id") String conversationId,
        @PathVariable("message_id") String messageId, @RequestParam("app_type") String appType,
        @RequestParam("version_id") String versionId, @RequestBody @Valid Feedback body);

    @DeleteMapping("/v1/{project_id}/apps/{app_id}/conversions/{conversation_id}/messages/{message_id}/feedback")
    ResponseEntity<ConversationDeleteResp> deleteFeedback(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("app_id") String appId,
        @PathVariable("conversation_id") String conversationId, @PathVariable("message_id") String messageId,
        @RequestParam("version_id") String version_id);

    @GetMapping("/v1/{project_id}/agent-builder/prompt/industry/list")
    ResponseEntity<List<IndustryVo>> listIndustry(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @RequestParam("workspace_id") String workspaceId);

    @PostMapping(value = "/v2/{project_id}/agent-runtime/agents/{agent_id}/memories/variables/batch-delete")
    ResponseEntity<BatchDeleteUserVariableMemoryResponseBody> batchDeleteUserVariableMemory(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @RequestParam("workspace_id") String workspaceId,
        @RequestBody @NotNull @Valid BatchDeleteUserVariableMemoryRequestBody body);

    @GetMapping(value = "/v2/{project_id}/agent-runtime/agents/{agent_id}/memories/variables")
    ResponseEntity<ListUserVariableMemoryResponseBody> listUserVariableMemory(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @RequestParam("workspace_id") String workspaceId);

    @PostMapping(value = "/v2/{project_id}/agent-runtime/agents/{agent_id}/memories/variables/reset")
    ResponseEntity<ResetUserVariableMemoryResponseBody> resetUserVariableMemory(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @RequestParam("workspace_id") String workspaceId);

    @GetMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/history")
    ResponseEntity<List<Message>> retrieveConversation(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @PathVariable("conversation_id") String conversationId,
        @SpringQueryMap RetrieveConversationQo retrieveConversationQo,
        @RequestParam("workspace_id") String workspaceId);

    @DeleteMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/history")
    ResponseEntity<ConversationDeleteResp> deleteConversation(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @PathVariable("conversation_id") String conversationId, @RequestParam("version_id") String versionId,
        @RequestParam("workspace_id") String workspaceId);

    @PostMapping(value = "/v1/{project_id}/workflows/{workflow_id}/tasks")
    ResponseEntity<TaskRsp> createTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @RequestParam(value = "version", required = false) String version,
        @RequestParam(value = "workspace_id", required = false) String workspaceId, @RequestBody @NotNull @Valid CreateTaskReq body);

    @GetMapping("/v1/{project_id}/workflows/{workflow_id}/tasks")
    ResponseEntity<TaskListRsp> listTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "type", required = false) String type,
        @RequestParam(value = "sort", required = false) String sort,
        @RequestParam(value = "order", required = false) String order,
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @GetMapping("/v1/{project_id}/workflows/{workflow_id}/tasks/{task_id}")
    ResponseEntity<TaskRsp> retrieveTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @PostMapping("/v1/{project_id}/workflows/{workflow_id}/tasks/{task_id}")
    ResponseEntity<TaskRsp> resumeTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = false) String workspaceId, @RequestBody @Valid @NotNull ResumeTaskReq bpdy);

    @PutMapping("/v1/{project_id}/workflows/{workflow_id}/tasks/{task_id}")
    ResponseEntity<TaskRsp> modifyTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = false) String workspaceId, @RequestBody @NotNull @Valid ModifyTaskReq body);

    @DeleteMapping("/v1/{project_id}/workflows/{workflow_id}/tasks/{task_id}")
    ResponseEntity<CommonDeleteRsp> deleteTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @DeleteMapping("/v1/{project_id}/workflows/{workflow_id}/tasks/{task_id}/cancel")
    ResponseEntity<CancelTaskRsp> cancelTask(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @PostMapping("/v1/{project_id}/mcp-servers/test")
    ResponseEntity<McpValidationResp> testServer(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @RequestBody @NotNull @Valid McpValidationReq body, @RequestParam("workspqce_id") String workspaceId);

    @PostMapping("/v1/agent-builder/rerank")
    Object rerank(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestParam("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId, @RequestBody @Valid RankDocumentsRequest request,
        @RequestParam("refresh") Boolean refresh);

    @PostMapping("/v1/agent-builder/embeddings")
    Object textEmbeddings(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestParam("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId, @RequestBody @Valid EmbeddingRequest request,
        @RequestParam("refresh") Boolean refresh);

    @PostMapping("/v1/agent-builder/chat/completions")
    Object chatCompletions(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestParam("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId, @RequestBody ChatCompletionRequest request,
        @RequestParam("refresh") boolean refresh);

    @PostMapping("/v1/agent-builder/chat/completions")
    Flux<Object> chatCompletionsStream(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestParam("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId, @RequestBody ChatCompletionRequest request,
        @RequestParam("refresh") boolean refresh);

    @PostMapping("/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/additional-questions")
    ResponseEntity<AutoAddResultJsonObject> additionalQuestions(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @PathVariable("conversation_id") String conversationId, @RequestParam("workspace_id") String workspaceId,
        @RequestBody AdditionalQuestionsReq body);

    @PostMapping("/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/additional-questions")
    ResponseEntity<AutoAddResultJsonObject> additionalQuestionsWorkflow(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("workflow_id") String workflowId,
        @PathVariable("conversation_id") String conversationId, @RequestParam("workspace_id") String workspaceId,
        @RequestBody AdditionalQuestionsWorkflowReq body);

    @PostMapping("/v1/{project_id}/tools/{tool_id}")
    ResponseEntity<RunToolResponseBody> runTool(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @RequestParam("workspace_id") String workspaceId, @PathVariable("project_id") String projectId,
        @RequestBody RunToolRequestBody body, @PathVariable("tool_id") String toolId);

    @PostMapping("/v1/{project_id}/agents/audio/tts")
    com.alibaba.fastjson.JSONObject textToSpeech(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @RequestParam("workspace_id") String workspaceId, @RequestBody Text2AudioReq req);

    @PostMapping("/v1/{project_id}/agents/audio/transcriptions")
    ResponseEntity<StsTextResp> audioTranscriptions(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @RequestParam("workspace_id") String workspaceId, @RequestBody Audio2TextReq req);

    @PostMapping("/v1/{project_id}/agents/{agent_id}/analytics/event")
    ResponseEntity<AnalyticsEventResp> analyticsEvent(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @RequestBody AnalyticsEventReq body, @RequestHeader("workspace_id") String workspaceId);

    @PostMapping("/v1/{project_id}/asr/short-audio")
    ResponseEntity<AsrRsp> voiceRecognition(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @RequestBody AsrReq body, @RequestParam("workspace_id") String workspaceId);

    @PostMapping("/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/abort")
    ResponseEntity<Status> abortConversation(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId,
        @PathVariable("workflow_id") String workflowId, @PathVariable("conversation_id") String conversationId,
        @RequestParam("workspace_id") String workspaceId);

    @GetMapping("/v1/{project_id}/controller/{agent_id}/conversations/{conversation_id}/executions")
    ResponseEntity<Object> listControllerExecutions(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @PathVariable("conversation_id") String conversationId,
        @RequestParam("workspace_id") String workspaceId,
        @SpringQueryMap ListControllerExecutionsQo body);

    @GetMapping("/v1/{project_id}/controller/{agent_id}/executions/{execution_id}")
    ResponseEntity<Object> getControllerExecutionDetail(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("agent_id") String agentId,
        @PathVariable("execution_id") String executionId,
        @RequestParam("workspace_id") String workspaceId,
        @SpringQueryMap GetControllerExecutionDetailQo body);

    @PostMapping("/v1/workflows/chat/{short_code}/conversations/{conversation_id}")
    ResponseEntity<Object> runWebWorkflow(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("short_code") String shortCode,
        @PathVariable("conversation_id") String conversationId, @RequestParam("workspace_id") String workspaceId,
        @RequestBody WorkflowRunReq body, @RequestHeader("stream") Boolean stream);

    @PostMapping("/v1/agents/chat/{short_code}")
    ResponseEntity<Object> runWebAgent(
        @RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("short_code") String shortCode,
        @RequestParam("workspace_id") String workspaceId, @RequestHeader("stream") Boolean stream,
        @RequestBody AgentRunReq body);

    @DeleteMapping(value = "/v1/{project_id}/agent-runtime/resource/{resource_id}/clear")
    ResponseEntity<Object> clearResourceCache(@RequestHeader(CommonConstant.X_AUTH_TOKEN) String authToken,
        @PathVariable("project_id") String projectId, @PathVariable("resource_id") String resourceId,
        @RequestParam(value = "type") String type);

    /**
     * Delete memory data in agent-runtime for a memory repo.
     * Called when a memory repo is deleted to clean up OpenSearch/Redis data.
     */
    @DeleteMapping(value = "/internal/v1/memory-repos/{memory_repo_id}")
    ResponseEntity<Object> deleteMemoryRepoData(
        @PathVariable("memory_repo_id") String memoryRepoId);

    /**
     * List memories for a user within a memory repo scope.
     * Calls runtime internal API which queries OpenSearch.
     */
    @GetMapping(value = "/internal/v1/memory-repos/{memory_repo_id}/users/{user_id}/memories")
    ResponseEntity<Object> listMemories(
        @PathVariable("memory_repo_id") String memoryRepoId,
        @PathVariable("user_id") String userId,
        @RequestParam(value = "page_size", defaultValue = "10") Integer pageSize,
        @RequestParam(value = "page_num", defaultValue = "1") Integer pageNum);

    /**
     * Batch-delete memories by ID list for a user within a memory repo scope.
     * Calls runtime internal API which deletes from OpenSearch.
     */
    @PostMapping(value = "/internal/v1/memory-repos/{memory_repo_id}/users/{user_id}/memories/batch-delete")
    ResponseEntity<Object> batchDeleteMemories(
        @PathVariable("memory_repo_id") String memoryRepoId,
        @PathVariable("user_id") String userId,
        @RequestBody java.util.Map<String, List<String>> body);

    /**
     * Semantic search for memories within a memory repo scope.
     * Calls runtime internal API which searches OpenSearch.
     */
    @PostMapping(value = "/internal/v1/memory-repos/{memory_repo_id}/users/{user_id}/memories/search")
    ResponseEntity<Object> searchMemories(
        @PathVariable("memory_repo_id") String memoryRepoId,
        @PathVariable("user_id") String userId,
        @RequestBody java.util.Map<String, Object> body);
}
