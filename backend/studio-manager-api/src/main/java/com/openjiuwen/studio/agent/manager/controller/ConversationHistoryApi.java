/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
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
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@Api(value = "ConversationHistory", description = "the ConversationHistory API")
@Validated
public interface ConversationHistoryApi {

    @ApiOperation(value = "根据conversation_id删除会话", nickname = "deleteConversationHistory",
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
    ResponseEntity<ConversationDeleteResp> deleteConversationHistory(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow/agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @Size(max = 32) @ApiParam(value = "版本号") @RequestParam(value = "version_id", required = false)
        String versionId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @ApiOperation(value = "根据conversation_id查询会话", nickname = "retrieveConversationHistory",
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
    ResponseEntity<List<Message>> retrieveConversationHistory(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "workflow/agent id", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "conversation_id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "RetrieveConversationQo: converted from multi query params") @Valid
        RetrieveConversationQo retrieveConversationQo,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId);
}
