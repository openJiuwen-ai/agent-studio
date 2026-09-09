/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ResourceUsageDetails;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

@Api(value = "ResourceManagement", description = "the ResourceManagement API")
@Validated

/**
 * ResourceManagementApi interface
 */ public interface ResourceManagementApi {
    @ApiOperation(value = "获取当前资源使用情况及是否超限", nickname = "resourceUsageDetails",
        notes = "获取当前资源使用情况及是否超限", response = ResourceUsageDetails.class, tags = {"ResourceManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = ResourceUsageDetails.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/resource-management", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ResourceUsageDetails> resourceUsageDetails(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @NotNull @Size(max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
    @ApiParam(value = "", required = true)
    @RequestParam(value = "resourceType", required = true) String resourceType);

}
