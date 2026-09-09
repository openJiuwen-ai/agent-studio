/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeBaseObsConfigReq;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeBaseObsConfigResp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseObsConfigExecuteRecordsQo;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseObsConfigExecuteRecordsResp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseObsConfigExecuteReq;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseObsConfigExecuteResp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseObsConfigResp;
import com.openjiuwen.studio.agent.manager.dto.ObsBucketObjectsReq;

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

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@Api(value = "KnowledgeBaseObsConfigManagement", description = "the KnowledgeBaseObsConfigManagement API")
@Validated

/**
 * KnowledgeBaseObsConfigManagementApi interface
 */ public interface KnowledgeBaseObsConfigManagementApi {
    @ApiOperation(value = "创建知识库obs配置", nickname = "createKnowledgeBaseObsConfig", notes = "创建知识库obs配置。",
        response = CreateKnowledgeBaseObsConfigResp.class, tags = {"KnowledgeBaseObsConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = CreateKnowledgeBaseObsConfigResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/obs-configs",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateKnowledgeBaseObsConfigResp> createKnowledgeBaseObsConfig(
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "项目空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "项目空间ID。", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.PATH, description = "知识库ID。", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @ApiParam(value = "") @Valid @RequestBody(required = false) CreateKnowledgeBaseObsConfigReq body);

    @ApiOperation(value = "根据obs配置执行动作", nickname = "knowledgeBaseObsConfigExecute",
        notes = "根据obs配置执行动作。", response = KnowledgeBaseObsConfigExecuteResp.class,
        tags = {"KnowledgeBaseObsConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = KnowledgeBaseObsConfigExecuteResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/obs-configs/{obs_config_id}/execute",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<KnowledgeBaseObsConfigExecuteResp> knowledgeBaseObsConfigExecute(
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "项目空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "项目空间ID。", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.PATH, description = "知识库ID。", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @Parameter(in = ParameterIn.PATH, description = "OBS配置ID。", required = true, schema = @Schema())
        @PathVariable("obs_config_id") String obsConfigId,
        @ApiParam(value = "") @Valid @RequestBody(required = false) KnowledgeBaseObsConfigExecuteReq body);

    @ApiOperation(value = "查询obs执行记录列表", nickname = "knowledgeBaseObsConfigExecuteRecords",
        notes = "查询obs执行记录列表。", response = KnowledgeBaseObsConfigExecuteRecordsResp.class,
        tags = {"KnowledgeBaseObsConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "obs同步日志列表",
            response = KnowledgeBaseObsConfigExecuteRecordsResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/obs-configs/{obs_config_id}/execute-records",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<KnowledgeBaseObsConfigExecuteRecordsResp> knowledgeBaseObsConfigExecuteRecords(
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "知识库ID。", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @Parameter(in = ParameterIn.PATH, description = "OBS配置ID。", required = true, schema = @Schema())
        @PathVariable("obs_config_id") String obsConfigId,
        @ApiParam(value = "KnowledgeBaseObsConfigExecuteRecordsQo: converted from multi query params") @Valid
        KnowledgeBaseObsConfigExecuteRecordsQo knowledgeBaseObsConfigExecuteRecordsQo);

    @ApiOperation(value = "展示用户obs桶名", nickname = "listObsBucketNames", notes = "", response = String.class,
        responseContainer = "List", tags = {"KnowledgeBaseObsConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = String.class, responseContainer = "List")
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/obs-bucket-names",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<List<String>> listObsBucketNames(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @NotNull
    @Parameter(in = ParameterIn.QUERY, description = "项目空间ID。", required = true, schema = @Schema())
    @ApiParam(value = "项目空间ID。", required = true)
    @RequestParam(value = "workspace_id", required = true) String workspaceId);

    @ApiOperation(value = "展示用户obs指定路径下的文件对象名集合", nickname = "listObsBucketObjects", notes = "",
        response = String.class, responseContainer = "List", tags = {"KnowledgeBaseObsConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = String.class, responseContainer = "List")
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/obs-bucket-objects",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<List<String>> listObsBucketObjects(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "项目空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "项目空间ID。", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @ApiParam(value = "") @Valid @RequestBody(required = false) ObsBucketObjectsReq body);

    @ApiOperation(value = "查看知识库obs配置", nickname = "showKnowledgeBaseObsConfig", notes = "查看知识库obs配置。",
        response = KnowledgeBaseObsConfigResp.class, tags = {"KnowledgeBaseObsConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库obs配置详情", response = KnowledgeBaseObsConfigResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/obs-configs",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<KnowledgeBaseObsConfigResp> showKnowledgeBaseObsConfig(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "项目空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "项目空间ID。", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.PATH, description = "知识库ID。", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId);

}
