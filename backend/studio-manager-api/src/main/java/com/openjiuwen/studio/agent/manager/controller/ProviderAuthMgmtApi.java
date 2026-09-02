/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.AuthConfigListQo;
import com.openjiuwen.studio.agent.manager.dto.CreateAuthConfigReq;
import com.openjiuwen.studio.agent.manager.dto.ProviderAuthCfgList;

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

@Api(value = "ProviderAuthMgmt", description = "the ProviderAuthMgmt API")
@Validated

/**
 * ProviderAuthMgmtApi interface
 */ public interface ProviderAuthMgmtApi {
    @ApiOperation(value = "", nickname = "authConfigList", notes = "查询供应商认证配置",
        response = ProviderAuthCfgList.class, tags = {"ProviderAuthMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = ProviderAuthCfgList.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/provider/auths", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ProviderAuthCfgList> authConfigList(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "AuthConfigListQo: converted from multi query params") @Valid
    AuthConfigListQo authConfigListQo);

    @ApiOperation(value = "", nickname = "createAuthConfig", notes = "认证配置设置", tags = {"ProviderAuthMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/provider/auths", consumes = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<Void> createAuthConfig(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "", required = false, schema = @Schema())
        @ApiParam(value = "") @RequestParam(value = "available_check", required = false) Boolean availableCheck,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody CreateAuthConfigReq body);

    @ApiOperation(value = "", nickname = "removeAuthConfig", notes = "移除供应商认证配置", tags = {"ProviderAuthMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/provider/auths/{id}", method = RequestMethod.DELETE)
    ResponseEntity<Void> removeAuthConfig(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "removeProviderAuthCfg", notes = "移除供应商认证配置",
        tags = {"ProviderAuthMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/provider/auths", method = RequestMethod.DELETE)
    ResponseEntity<Void> removeProviderAuthCfg(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = false, schema = @Schema())
        @ApiParam(value = "")
        @RequestParam(value = "provider_id", required = false) String providerId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = false, schema = @Schema())
        @ApiParam(value = "")
        @RequestParam(value = "auth_id", required = false) String authId);

}
