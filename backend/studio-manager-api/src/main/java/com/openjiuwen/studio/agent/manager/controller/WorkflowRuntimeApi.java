/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.run.GetExecutionInsightQo;
import com.openjiuwen.studio.agent.common.dto.run.ListConversationQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListExecutionQueriesQo;

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

@Api(value = "WorkflowRuntime", description = "the WorkflowRuntime API")
@Validated

/**
 * WorkflowRuntimeApi interface
 */
public interface WorkflowRuntimeApi {
    @ApiOperation(value = "", nickname = "getExecutionInsight", notes = "", response = ExecutionInfo.class,
        tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ExecutionInfo.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/workflows/{workflow_id}/executions/{execution_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ExecutionInfo> getExecutionInsight(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "执行id", required = true, schema = @Schema())
        @PathVariable("execution_id") String executionId,
        @ApiParam(value = "GetExecutionInsightQo: converted from multi query params") @Valid
        GetExecutionInsightQo getExecutionInsightQo);

    @ApiOperation(value = "查询当前对话中用户输入内容的列表", nickname = "listConversationQueries", notes = "",
        response = ConversionQueries.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ConversionQueries.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/workflows/{workflow_id}/conversations", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ConversionQueries> listConversationQueries(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListConversationQueriesQo: converted from multi query params") @Valid
        ListConversationQueriesQo listConversationQueriesQo);

    @ApiOperation(value = "查询当前对话中用户输入内容的列表", nickname = "listExecutionQueries", notes = "",
        response = ExecutionQueries.class, tags = {"WorkflowRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = ExecutionQueries.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/executions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ExecutionQueries> listExecutionQueries(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "会话id", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @ApiParam(value = "ListExecutionQueriesQo: converted from multi query params") @Valid
        ListExecutionQueriesQo listExecutionQueriesQo);

}
