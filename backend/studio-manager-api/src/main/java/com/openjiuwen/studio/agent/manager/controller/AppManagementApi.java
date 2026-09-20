/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.AppInfo;
import com.openjiuwen.studio.agent.manager.dto.AppListRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListAppsQo;
import com.openjiuwen.studio.agent.manager.dto.SearchCriteria;

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

@Api(value = "AppManagement", description = "the AppManagement API")
@Validated

/**
 * AppManagementApi interface
 */ public interface AppManagementApi {
    @ApiOperation(value = "复制百宝箱应用", nickname = "copyApp", notes = "复制百宝箱应用。", response = AppInfo.class,
        tags = {"AppManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用信息。", response = AppInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/apps/{app_id}/copy", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AppInfo> copyApp(@Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("app_id") String appId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "目标项目空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "目标项目空间ID。", required = true)
        @RequestParam(value = "target_workspace_id", required = true) String targetWorkspaceId,
        @ApiParam(value = "搜索条件。") @Valid @RequestBody(required = false) SearchCriteria body);

    @ApiOperation(value = "获取应用百宝箱列表", nickname = "listApps", notes = "获取应用百宝箱列表。",
        response = AppListRsp.class, tags = {"AppManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "搜索的应用列表。", response = AppListRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/apps", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AppListRsp> listApps(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListAppsQo: converted from multi query params") @Valid ListAppsQo listAppsQo);

}
