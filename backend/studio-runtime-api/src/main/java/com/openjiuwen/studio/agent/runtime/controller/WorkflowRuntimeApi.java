/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
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

@Api(value = "WorkflowRuntime", description = "the WorkflowRuntime API")
@Validated

/**
 * WorkflowRuntimeApi interface
 */
public interface WorkflowRuntimeApi {
    @ApiOperation(value = "停止对话生成并清空会话", nickname = "abortConversation", notes = "", response = Status.class,
        tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = Status.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/abort",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Status> abortConversation(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
    @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "会话流id", required = true, schema = @Schema())
    @PathVariable("conversation_id") String conversationId);

    @ApiOperation(value = "自动生成追问", nickname = "additionalQuestionsWorkflow", notes = "自动生成追问",
        response = AutoAddResultJsonObject.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "追问列表", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/additional-questions",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AutoAddResultJsonObject> additionalQuestionsWorkflow(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @NotNull @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "追问请求体", required = true) @Valid @RequestBody
        AdditionalQuestionsWorkflowReq body);

}
