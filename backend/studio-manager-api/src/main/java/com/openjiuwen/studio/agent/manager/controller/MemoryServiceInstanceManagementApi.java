/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryServiceInstanceResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryServiceInstancesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryServiceInstanceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ShowMemoryServiceInstanceResponseBody;

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

@Api(value = "MemoryServiceInstanceManagement", description = "the MemoryServiceInstanceManagement API")
@Validated
public interface MemoryServiceInstanceManagementApi {

    @ApiOperation(value = "创建外部记忆服务实例", nickname = "createMemoryServiceInstance",
        notes = "创建外部记忆服务实例", response = CreateMemoryServiceInstanceResponseBody.class,
        tags = {"MemoryServiceInstanceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建实例响应体",
            response = CreateMemoryServiceInstanceResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-service-instances",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateMemoryServiceInstanceResponseBody> createMemoryServiceInstance(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建实例请求体", required = true) @Valid @RequestBody
        CreateMemoryServiceInstanceRequestBody body);

    @ApiOperation(value = "删除外部记忆服务实例", nickname = "deleteMemoryServiceInstance",
        notes = "删除外部记忆服务实例", tags = {"MemoryServiceInstanceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除成功"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-service-instances/{instance_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteMemoryServiceInstance(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "实例id", required = true, schema = @Schema())
        @PathVariable("instance_id") String instanceId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "修改外部记忆服务实例", nickname = "modifyMemoryServiceInstance",
        notes = "修改外部记忆服务实例", tags = {"MemoryServiceInstanceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改成功"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-service-instances/{instance_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Void> modifyMemoryServiceInstance(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "实例id", required = true, schema = @Schema())
        @PathVariable("instance_id") String instanceId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "修改实例请求体", required = true) @Valid @RequestBody
        ModifyMemoryServiceInstanceRequestBody body);

    @ApiOperation(value = "获取外部记忆服务实例列表", nickname = "listMemoryServiceInstances",
        notes = "获取外部记忆服务实例列表", response = ListMemoryServiceInstancesResponseBody.class,
        tags = {"MemoryServiceInstanceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "实例列表",
            response = ListMemoryServiceInstancesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-service-instances",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListMemoryServiceInstancesResponseBody> listMemoryServiceInstances(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "实例名称（模糊搜索）") @RequestParam(value = "name", required = false)
        String name);

    @ApiOperation(value = "查询外部记忆服务实例详情", nickname = "showMemoryServiceInstance",
        notes = "查询外部记忆服务实例详情", response = ShowMemoryServiceInstanceResponseBody.class,
        tags = {"MemoryServiceInstanceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "实例详情",
            response = ShowMemoryServiceInstanceResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-service-instances/{instance_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShowMemoryServiceInstanceResponseBody> showMemoryServiceInstance(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "实例id", required = true, schema = @Schema())
        @PathVariable("instance_id") String instanceId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "健康检查外部记忆服务实例", nickname = "healthCheckMemoryServiceInstance",
        notes = "调 agent-memory GET /health 检查实例可达性", response = ShowMemoryServiceInstanceResponseBody.class,
        tags = {"MemoryServiceInstanceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "健康检查结果",
            response = ShowMemoryServiceInstanceResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-service-instances/{instance_id}/health",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ShowMemoryServiceInstanceResponseBody> healthCheckMemoryServiceInstance(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "实例id", required = true, schema = @Schema())
        @PathVariable("instance_id") String instanceId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);
}
