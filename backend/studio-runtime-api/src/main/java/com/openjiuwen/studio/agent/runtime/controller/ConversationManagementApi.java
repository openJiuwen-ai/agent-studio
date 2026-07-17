/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.Feedback;
import com.openjiuwen.studio.agent.runtime.dto.GetMemoryChunksQo;
import com.openjiuwen.studio.agent.runtime.dto.MemoryChunk;
import com.openjiuwen.studio.agent.runtime.dto.MemoryVariable;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationMemoryQo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;

import io.swagger.annotations.Api;
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

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@Api(value = "ConversationManagement", description = "the ConversationManagement API")
@Validated

/**
 * ConversationManagementApi interface
 */
public interface ConversationManagementApi {
    @ApiOperation(value = "指定message创建用户反馈", nickname = "createUserFeedback", notes = "指定message创建用户反馈",
        response = String.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = String.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/apps/{app_id}/conversions/{conversation_id}/messages/{message_id}/feedback",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createUserFeedback(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
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
        String versionId, @ApiParam(value = "用户反馈请求体") @Valid @RequestBody(required = false) Feedback body);

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
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/history",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<ConversationDeleteResp> deleteConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow/agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Size(max = 32) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId);

    @ApiOperation(value = "删除指定message用户反馈", nickname = "deleteFeedback", notes = "删除指定message用户反馈",
        response = ConversationDeleteResp.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversationDeleteResp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/apps/{app_id}/conversions/{conversation_id}/messages/{message_id}/feedback",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<ConversationDeleteResp> deleteFeedback(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("app_id") String appId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("message_id") String messageId,
        @Size(max = 64) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId);

    @ApiOperation(value = "", nickname = "deleteMemoryChunks", notes = "删除记忆片段",
        response = ConversationDeleteResp.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversationDeleteResp.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-chunks",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<ConversationDeleteResp> deleteMemoryChunks(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "chunk id") @RequestParam(value = "chunk_id", required = false) Integer chunkId);

    @ApiOperation(value = "", nickname = "generateMemoryChunk", notes = "生成记忆片段", response = MemoryChunk.class,
        tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "记忆片段", response = MemoryChunk.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-chunks",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<MemoryChunk> generateMemoryChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "") @RequestParam(value = "start", required = false) Long start,
        @ApiParam(value = "") @RequestParam(value = "end", required = false) Long end,
        @Min(0) @Max(100000) @ApiParam(value = "", allowableValues = "0, 100000", defaultValue = "0")
        @RequestParam(value = "offset", required = false, defaultValue = "0") Integer offset,
        @Min(1) @Max(1000) @ApiParam(value = "", allowableValues = "1, 1000", defaultValue = "10")
        @RequestParam(value = "limit", required = false, defaultValue = "10") Integer limit,
        @Size(max = 64) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId,
        @NotNull @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "", nickname = "getMemoryChunks", notes = "获取记忆片段",
        response = AutoAddResultJsonObject.class, tags = {"ConversationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "记忆片段列表", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-chunks",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> getMemoryChunks(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "GetMemoryChunksQo: converted from multi query params") @Valid
        GetMemoryChunksQo getMemoryChunksQo);

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
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-variables/reset",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<List<MemoryVariable>> resetConversationMemory(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "应用id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Size(max = 32) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId);

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
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/history",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<List<Message>> retrieveConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow/agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "RetrieveConversationQo: converted from multi query params") @Valid
        RetrieveConversationQo retrieveConversationQo);

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
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/memory-variables",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<List<MemoryVariable>> retrieveConversationMemory(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "agent_id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "RetrieveConversationMemoryQo: converted from multi query params") @Valid
        RetrieveConversationMemoryQo retrieveConversationMemoryQo);

}
