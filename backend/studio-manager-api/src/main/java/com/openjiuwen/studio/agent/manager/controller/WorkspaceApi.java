/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CreateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteWorkspaceReq;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.GetWorkspaceListRsp;
import com.openjiuwen.studio.agent.manager.dto.QueryWorkspaceQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceInfo;

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

@Api(value = "Workspace", description = "the Workspace API")
@Validated

/**
 * WorkspaceApi interface
 */ public interface WorkspaceApi {
    @ApiOperation(value = "", nickname = "createWorkspace", notes = "创建团队空间。", response = String.class,
        tags = {"Workspace"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "是否创建成功。", response = String.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createWorkspace(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "创建团队空间请求体。", required = true) @Valid @RequestBody CreateWorkspaceReq body);

    @ApiOperation(value = "", nickname = "deleteWorkspace", notes = "删除团队空间。", response = String.class,
        tags = {"Workspace"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除成功。", response = String.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<String> deleteWorkspace(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "删除团队空间请求体。", required = true) @Valid @RequestBody DeleteWorkspaceReq body);

    @ApiOperation(value = "", nickname = "initWorkspace",
        notes = "用户空间初始化，如果用户没有个人空间，给用户创建个人空间，初始化后返回用户所在的空间列表。",
        response = GetWorkspaceListRsp.class, tags = {"Workspace"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取团队空间列表响应体。", response = GetWorkspaceListRsp.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/init", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<GetWorkspaceListRsp> initWorkspace(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.QUERY, description = "user-查询用户下有哪些空间，project-查询当前project下有哪些空间。", required = false, schema = @Schema())
        @ApiParam(value = "user-查询用户下有哪些空间，project-查询当前project下有哪些空间。",
            allowableValues = "user, project", defaultValue = "user")
        @RequestParam(value = "scope", required = false, defaultValue = "user") String scope);

    @ApiOperation(value = "", nickname = "queryWorkspace", notes = "查询团队空间列表。",
        response = GetWorkspaceListRsp.class, tags = {"Workspace"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取团队空间列表响应体。", response = GetWorkspaceListRsp.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<GetWorkspaceListRsp> queryWorkspace(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "QueryWorkspaceQo: converted from multi query params") @Valid
        QueryWorkspaceQo queryWorkspaceQo);

    @ApiOperation(value = "", nickname = "queryWorkspaceById", notes = "查询指定ID的空间信息。",
        response = WorkspaceInfo.class, tags = {"Workspace"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取团队空间详情。", response = WorkspaceInfo.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/{workspace_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<WorkspaceInfo> queryWorkspaceById(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "空间ID。", required = true, schema = @Schema())
        @PathVariable("workspace_id") String workspaceId);

    @ApiOperation(value = "", nickname = "updateWorkspace", notes = "修改工作空间。", response = WorkspaceInfo.class,
        tags = {"Workspace"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "是否更新成功。", response = WorkspaceInfo.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<WorkspaceInfo> updateWorkspace(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "更新团队空间请求体。", required = true) @Valid @RequestBody UpdateWorkspaceReq body);

}
