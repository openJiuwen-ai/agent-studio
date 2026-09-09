/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.ApiKeyRequest;
import com.openjiuwen.studio.agent.manager.dto.ApiKeysListResp;
import com.openjiuwen.studio.agent.manager.dto.ApikeyResponse;
import com.openjiuwen.studio.agent.manager.dto.QueryApiKeysQo;

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

@Api(value = "ApiKeyMgmt", description = "the ApiKeyMgmt API")
@Validated

/**
 * ApiKeyMgmtApi interface
 */ public interface ApiKeyMgmtApi {
    @ApiOperation(value = "创建 API Key", nickname = "createApiKey", notes = "租户管理员通过该接口创建 API Key 并返回",
        response = ApikeyResponse.class, tags = {"ApiKeyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建的apikey信息", response = ApikeyResponse.class)
    })
    @RequestMapping(value = "/v1/{project_id}/api-auth/api-keys", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ApikeyResponse> createApiKey(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ApiKeyRequest body);

    @ApiOperation(value = "删除 API Key", nickname = "deleteApiKey",
        notes = "租户管理员通过该接口删除指定的 API Key 信息", tags = {"ApiKeyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除成功")
    })
    @RequestMapping(value = "/v1/{project_id}/api-auth/api-keys/{id}", method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteApiKey(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id, @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询 API Key 列表", nickname = "queryApiKeys",
        notes = "租户管理员通过该接口查询当前租户的 API Key 列表", response = ApiKeysListResp.class,
        tags = {"ApiKeyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询成功", response = ApiKeysListResp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/api-auth/api-keys/list", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ApiKeysListResp> queryApiKeys(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @ApiParam(value = "QueryApiKeysQo: converted from multi query params") @Valid QueryApiKeysQo queryApiKeysQo);

}
