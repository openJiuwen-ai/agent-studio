/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.QueryShareResourceInfoByResourceIdQo;
import com.openjiuwen.studio.agent.manager.dto.QueryShareResourceListQo;
import com.openjiuwen.studio.agent.manager.dto.QuerySharedResourceListQo;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceRequestInfo;
import com.openjiuwen.studio.agent.manager.dto.ShareResourceResp;

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

@Api(value = "ShareResourceManager", description = "the ShareResourceManager API")
@Validated

/**
 * ShareResourceManagerApi interface
 */ public interface ShareResourceManagerApi {
    @ApiOperation(value = "", nickname = "cancelShareResource", notes = "取消资源跨空间共享", response = Boolean.class,
        tags = {"ShareResourceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "取消资源跨空间共享是否成功", response = Boolean.class),
        @ApiResponse(code = 400, message = "取消资源跨空间共享失败", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/share/{resource_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Boolean> cancelShareResource(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源id", required = true, schema = @Schema())
        @PathVariable("resource_id") String resourceId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "资源类型，controller-多智能体、workflow-工作流、plugin-插件", required = false, schema = @Schema())
        @ApiParam(value = "资源类型，controller-多智能体、workflow-工作流、plugin-插件",
            allowableValues = "controller, workflow, plugin") @RequestParam(value = "resource_type", required = false)
        String resourceType);

    @ApiOperation(value = "", nickname = "createOrUpdateShareResource",
        notes = "资源（智能体、工作流、插件等）共享到其他空间", response = Boolean.class, tags = {"ShareResourceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "是否共享成功", response = Boolean.class),
        @ApiResponse(code = 400, message = "共享资源失败", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/share", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Boolean> createOrUpdateShareResource(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "创建资源共享请求体", required = true) @Valid @RequestBody
        ShareResourceRequestInfo body);

    @ApiOperation(value = "", nickname = "queryShareResourceInfoByResourceId",
        notes = "查询跨空间共享对象记录信息，更新发布跨空间共享时，需要先加载已有的共享信息",
        response = ShareResourceResp.class, tags = {"ShareResourceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "资源共享记录详情", response = ShareResourceResp.class),
        @ApiResponse(code = 400, message = "查询资源共享记录详情失败", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/share/{resource_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShareResourceResp> queryShareResourceInfoByResourceId(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源id", required = true, schema = @Schema())
        @PathVariable("resource_id") String resourceId,
        @ApiParam(value = "QueryShareResourceInfoByResourceIdQo: converted from multi query params") @Valid
        QueryShareResourceInfoByResourceIdQo queryShareResourceInfoByResourceIdQo);

    @ApiOperation(value = "", nickname = "queryShareResourceList", notes = "获取共享给当前空间的资源",
        response = ShareResourceListRsp.class, tags = {"ShareResourceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "跨空间共享对象对应的资源详情", response = ShareResourceListRsp.class),
        @ApiResponse(code = 400, message = "获取函数列表失败", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/share", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ShareResourceListRsp> queryShareResourceList(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "QueryShareResourceListQo: converted from multi query params") @Valid
        QueryShareResourceListQo queryShareResourceListQo);

    @ApiOperation(value = "", nickname = "querySharedResourceList", notes = "获取共享给当前空间的资源",
        response = ShareResourceListRsp.class, tags = {"ShareResourceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "跨空间共享对象对应的资源详情", response = ShareResourceListRsp.class),
        @ApiResponse(code = 400, message = "获取函数列表失败", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource/shared", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ShareResourceListRsp> querySharedResourceList(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "QuerySharedResourceListQo: converted from multi query params") @Valid
        QuerySharedResourceListQo querySharedResourceListQo);

}
