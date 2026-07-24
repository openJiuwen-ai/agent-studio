/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListDependencyQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourceRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourcesRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.RelationList;
import com.openjiuwen.studio.agent.manager.dto.ResourceDependencyResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ResourceMappingList;
import com.openjiuwen.studio.agent.manager.dto.ResourceVersionResponseBody;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

@Api(value = "RelationManagement", description = "the RelationManagement API")
@Validated

/**
 * RelationManagementApi interface
 */ public interface RelationManagementApi {
    @ApiOperation(value = "查询应用引用了哪些资源", nickname = "listAppRelations", notes = "查询应用引用了哪些资源。",
        response = RelationList.class, tags = {"RelationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "关联关系列表。", response = RelationList.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/relation/apps/{app_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<RelationList> listAppRelations(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("app_id") String appId,
        @ApiParam(value = "ListAppRelationsQo: converted from multi query params") @Valid
        ListAppRelationsQo listAppRelationsQo);

    @ApiOperation(value = "查询资源被哪些应用引用", nickname = "listResourceRelations",
        notes = "查询资源被哪些应用引用。", response = RelationList.class, tags = {"RelationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "关联关系列表。", response = RelationList.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/relation/resources/{resource_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<RelationList> listResourceRelations(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("resource_id") String resourceId,
        @ApiParam(value = "ListResourceRelationsQo: converted from multi query params") @Valid
        ListResourceRelationsQo listResourceRelationsQo);

    @ApiOperation(value = "批量获取指定资源绑定的应用列表", nickname = "listResourcesRelations",
        notes = "批量获取指定资源绑定的应用列表。", response = ResourceMappingList.class, tags = {"RelationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "资源绑定信息。", response = ResourceMappingList.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/relation/resources", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ResourceMappingList> listResourcesRelations(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListResourcesRelationsQo: converted from multi query params") @Valid
        ListResourcesRelationsQo listResourcesRelationsQo);

    @ApiOperation(value = "查询资源依赖的子资源", nickname = "listDependency", notes = "查询资源依赖的子资源。",
        response = ResourceDependencyResponseBody.class, tags = {"RelationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "agent依赖资源rsp。", response = ResourceDependencyResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/{app_id}/dependency",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ResourceDependencyResponseBody> listDependency(@Pattern(regexp = "^[a-zA-Z0-9_-]+$")
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("app_id") String appId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @ApiParam(value = "版本id。") @RequestParam(value = "version_id", required = false) String versionId);

    @ApiOperation(value = "查询资源可用的版本", nickname = "listVersions", notes = "查询资源可用的版本。",
        response = ResourceVersionResponseBody.class, tags = {"RelationManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "版本信息。", response = ResourceVersionResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/{app_id}/versions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ResourceVersionResponseBody> listVersions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$")
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("app_id") String appId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotBlank @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @ApiParam(value = "资源类型：workflow/agent/controller。", required = true)
        @RequestParam(value = "resource_type", required = true) String resourceType);

}
