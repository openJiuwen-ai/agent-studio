/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonResponse;
import com.openjiuwen.studio.agent.manager.dto.DeleteWorkspaceMemberReq;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.GetWorkspaceMemberListRsp;
import com.openjiuwen.studio.agent.manager.dto.GetWorkspaceMemberRoleRsp;
import com.openjiuwen.studio.agent.manager.dto.MemberOwnershipBody;
import com.openjiuwen.studio.agent.manager.dto.QueryWorkspaceMemberListQo;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberBody;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberBody1;

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

@Api(value = "WorkSpaceMember", description = "the WorkSpaceMember API")
@Validated

/**
 * WorkSpaceMemberApi interface
 */ public interface WorkSpaceMemberApi {
    @ApiOperation(value = "", nickname = "batchAddWorkspaceMember", notes = "批量添加团队空间成员。",
        response = Integer.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量添加团队空间成员成功。", response = Integer.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Integer> batchAddWorkspaceMember(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody WorkspaceMemberBody body);

    @ApiOperation(value = "", nickname = "batchDeleteWorkspaceMember", notes = "批量移除团队空间成员。",
        response = Integer.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量移除成员成功。", response = Integer.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "无权限移除成员（如移除所有者）。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Integer> batchDeleteWorkspaceMember(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "批量删除空间成员请求体。", required = true) @Valid @RequestBody
        DeleteWorkspaceMemberReq body);

    @ApiOperation(value = "", nickname = "batchUpdateWorkspaceMemberRole", notes = "修改团队空间成员角色。",
        response = Integer.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成员角色修改成功。", response = Integer.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "无权限修改该成员角色。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PATCH)
    ResponseEntity<Integer> batchUpdateWorkspaceMemberRole(
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody WorkspaceMemberBody1 body);

    @ApiOperation(value = "", nickname = "exitWorkspace", notes = "当前用户退出指定空间",
        response = CommonResponse.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "退出空间成功。", response = CommonResponse.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member/me", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonResponse> exitWorkspace(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "要退出的空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "要退出的空间ID。", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId);

    @ApiOperation(value = "", nickname = "queryIamUserList", notes = "获取IAM用户列表。",
        response = GetWorkspaceMemberListRsp.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取当前租户下面的用户列表。", response = GetWorkspaceMemberListRsp.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/users", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<GetWorkspaceMemberListRsp> queryIamUserList(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
            String workspaceId);

    @ApiOperation(value = "", nickname = "queryRoleList", notes = "获取团队空间下的角色列表。",
        response = GetWorkspaceMemberRoleRsp.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取当前租户下面的用户列表。", response = GetWorkspaceMemberRoleRsp.class),
        @ApiResponse(code = 400, message = "请求参数错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member/role", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<GetWorkspaceMemberRoleRsp> queryRoleList(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
            String workspaceId);


    @ApiOperation(value = "", nickname = "queryWorkspaceMemberList", notes = "查询团队空间成员列表",
        response = GetWorkspaceMemberListRsp.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取团队空间成员列表响应体。", response = GetWorkspaceMemberListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<GetWorkspaceMemberListRsp> queryWorkspaceMemberList(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "QueryWorkspaceMemberListQo: converted from multi query params") @Valid
        QueryWorkspaceMemberListQo queryWorkspaceMemberListQo);

    @ApiOperation(value = "", nickname = "transferWorkspaceOwnership", notes = "转让空间所有权给指定用户。",
        response = CommonResponse.class, tags = {"WorkSpaceMember"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作完成。", response = CommonResponse.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workspace/member/ownership",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<CommonResponse> transferWorkspaceOwnership(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody MemberOwnershipBody body);

}
