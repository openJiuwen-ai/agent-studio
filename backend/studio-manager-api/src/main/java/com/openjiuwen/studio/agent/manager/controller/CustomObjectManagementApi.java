/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListCustomObjectQo;
import com.openjiuwen.studio.agent.manager.dto.ObjectBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ObjectInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ObjectListRsp;
import com.openjiuwen.studio.agent.manager.dto.ObjectRsp;

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

@Api(value = "CustomObjectManagement", description = "the CustomObjectManagement API")
@Validated

/**
 * CustomObjectManagementApi interface
 */ public interface CustomObjectManagementApi {
    @ApiOperation(value = "创建自定义对象", nickname = "createCustomObject", notes = "创建自定义对象",
        response = ObjectBriefRsp.class, tags = {"CustomObjectManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建对象响应体", response = ObjectBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/objects", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ObjectBriefRsp> createCustomObject(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "对象信息请求体", required = true) @Valid @RequestBody ObjectInfoReq body);

    @ApiOperation(value = "删除自定义对象", nickname = "deleteCustomObject", notes = "删除自定义对象",
        response = ObjectBriefRsp.class, tags = {"CustomObjectManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除对象响应体", response = ObjectBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/objects/{id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<ObjectBriefRsp> deleteCustomObject(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "对象id", required = true, schema = @Schema()) @PathVariable("id")
    String id, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
    @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "获取自定义对象列表", nickname = "listCustomObject", notes = "获取自定义对象列表",
        response = ObjectListRsp.class, tags = {"CustomObjectManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "对象列表", response = ObjectListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/objects", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ObjectListRsp> listCustomObject(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListCustomObjectQo: converted from multi query params") @Valid
        ListCustomObjectQo listCustomObjectQo);

    @ApiOperation(value = "修改自定义对象", nickname = "modifyCustomObject", notes = "修改自定义对象",
        response = ObjectBriefRsp.class, tags = {"CustomObjectManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改对象响应体", response = ObjectBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/objects/{id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ObjectBriefRsp> modifyCustomObject(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "对象id", required = true, schema = @Schema()) @PathVariable("id")
        String id, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "修改对象请求体", required = true) @Valid @RequestBody ObjectInfoReq body);

    @ApiOperation(value = "获取自定义对象", nickname = "retrieveCustomObject", notes = "获取自定义对象",
        response = ObjectRsp.class, tags = {"CustomObjectManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "对象信息", response = ObjectRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/objects/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ObjectRsp> retrieveCustomObject(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "对象id", required = true, schema = @Schema()) @PathVariable("id")
    String id, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
    @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

}
