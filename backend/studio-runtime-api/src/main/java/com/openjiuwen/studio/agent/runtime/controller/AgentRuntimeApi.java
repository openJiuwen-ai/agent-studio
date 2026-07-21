/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.dto.ReleaseInfo;

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
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

@Api(value = "AgentRuntime", description = "the AgentRuntime API")
@Validated

/**
 * AgentRuntimeApi interface
 */
public interface AgentRuntimeApi {
    @ApiOperation(value = "自动生成追问", nickname = "additionalQuestions", notes = "自动生成追问", response = AutoAddResultJsonObject.class, tags={ "AgentRuntime" })
    @ApiResponses(value = { 
        @ApiResponse(code = 200, message = "追问列表", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/additional-questions",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AutoAddResultJsonObject> additionalQuestions(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("conversation_id") String conversationId,
        @NotNull @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "追问请求体", required = true) @Valid @RequestBody AdditionalQuestionsReq body);

    @ApiOperation(value = "", nickname = "createReleaseInfo", notes = "同步应用发布信息", response = String.class,
        tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = String.class)
    })
    @RequestMapping(value = "/v1/{project_id}/releases", produces = {"*/*"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<String> createReleaseInfo(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "") @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @ApiParam(value = "应用发布信息") @Valid @RequestBody(required = false) ReleaseInfo body);

    @ApiOperation(value = "", nickname = "delegateExchangeToken", notes = "委托换取token", response = String.class,
        tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "success", response = String.class),
        @ApiResponse(code = 400, message = "Bad request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/token", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<String> delegateExchangeToken(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "需要换取的token的project id") @RequestParam(value = "auth_project_id", required = false)
        String authProjectId,
        @ApiParam(value = "需要换取的token的domain id") @RequestParam(value = "auth_domain_id", required = false)
        String authDomainId);

    @ApiOperation(value = "", nickname = "deleteReleaseInfo", notes = "删除应用发布信息", response = String.class,
        tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = String.class)
    })
    @RequestMapping(value = "/v1/{project_id}/releases/{release_id}", produces = {"*/*"}, method = RequestMethod.DELETE)
    ResponseEntity<String> deleteReleaseInfo(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("release_id") String releaseId, @NotNull @ApiParam(value = "发布通道类型", required = true)
        @RequestParam(value = "channel_type", required = true) String channelType,
        @ApiParam(value = "版本ID") @RequestParam(value = "version_id", required = false) String versionId);

    @ApiOperation(value = "", nickname = "voiceRecognition", notes = "一句话语音识别", response = AsrRsp.class,
        tags = {"AgentRuntime"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "语音识别返回数据", response = AsrRsp.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/asr/short-audio", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AsrRsp> voiceRecognition(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "接口请求体", required = true) @Valid @RequestBody AsrReq body);

}
