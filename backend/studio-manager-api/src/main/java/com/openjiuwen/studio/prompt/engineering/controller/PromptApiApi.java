/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.controller;

import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptResp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptListsQo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptNewListVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateNewVo;

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

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * PromptApiApi interface
 */

@Api(value = "PromptApi", description = "the PromptApi API")
@Validated
public interface PromptApiApi {

    @ApiOperation(value = "创建一个提示词", nickname = "createCustomPromptApiAction",
        notes = "Create CustomPromptApi Action", response = String.class, tags = {"PromptApi"})
    @ApiResponses(value = {@ApiResponse(code = 200, message = "操作成功", response = String.class)})
    @RequestMapping(value = "/v2/{project_id}/agent-builder/prompt", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createCustomPromptApiAction(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "工作空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建或者更新候选模板请求体", required = true) @Valid @RequestBody
        PePromptTemplateNewVo body);

    @ApiOperation(value = "查询单个自定义连接器的单个执行动作详细信息", nickname = "getPromptLists",
        notes = "Get prompt list", response = PePromptNewListVo.class, tags = {"PromptApi"})
    @ApiResponses(value = {@ApiResponse(code = 200, message = "", response = PePromptNewListVo.class)})
    @RequestMapping(value = "/v2/{project_id}/agent-builder/prompt/list", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<PePromptNewListVo> getPromptLists(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "GetPromptListsQo: converted from multi query params") @Valid
        GetPromptListsQo getPromptListsQo);

    @ApiOperation(value = "保存模板", nickname = "savePromptTemplate", notes = "Save Prompt Template",
        response = CreatePromptResp.class, tags = {"PromptApi"})
    @ApiResponses(value = {@ApiResponse(code = 200, message = "启动成功", response = CreatePromptResp.class)})
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/prompt/save", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreatePromptResp> savePromptTemplate(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "工作空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建模板请求体", required = true) @Valid @RequestBody PePromptTemplateNewVo body);

    @ApiOperation(value = "更新提示词", nickname = "updateCustomPromptApiAction",
        notes = "Update CustomPromptApi Action", response = CreatePromptResp.class, tags = {"PromptApi"})
    @ApiResponses(value = {@ApiResponse(code = 200, message = "操作成功", response = CreatePromptResp.class)})
    @RequestMapping(value = "/v2/{project_id}/agent-builder/prompt", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<CreatePromptResp> updateCustomPromptApiAction(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "工作空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody PePromptTemplateNewVo body);
}
