/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderReq;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceProviderRsp;
import com.openjiuwen.studio.agent.manager.dto.ProviderAuthInfoReq;
import com.openjiuwen.studio.agent.manager.dto.QueryPlatformProvidersQo;
import com.openjiuwen.studio.agent.manager.dto.QueryUserProvidersQo;

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

@Api(value = "ProviderMgmt", description = "the ProviderMgmt API")
@Validated

/**
 * ProviderMgmtApi interface
 */ public interface ProviderMgmtApi {
    @ApiOperation(value = "", nickname = "createModelServiceProviders", notes = "用户接入模型服务供应商列",
        response = String.class, tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型服务供应商列表", response = String.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/integration/providers", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createModelServiceProviders(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ModelServiceProviderReq body);

    @ApiOperation(value = "", nickname = "deleteModelServiceProvider", notes = "删除供应商信息",
        tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/integration/providers/{id}", method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteModelServiceProvider(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "integrationModelServiceProviderDetail", notes = "查询供应商详情",
        response = ModelServiceProviderRsp.class, tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型服务供应商列表", response = ModelServiceProviderRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/integration/providers/{id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ModelServiceProviderRsp> integrationModelServiceProviderDetail(
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "platformModelServiceProviderDetail", notes = "查询平台预置模型服务供应详情",
        response = ModelServiceProviderRsp.class, tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型服务供应商", response = ModelServiceProviderRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/platform/providers/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ModelServiceProviderRsp> platformModelServiceProviderDetail(
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$") @Size(max = 80)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId);

    @ApiOperation(value = "", nickname = "queryPlatformProviders", notes = "查询平台预置模型服务供应商列表",
        response = ModelServiceProviderListRsp.class, tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型服务供应商列表", response = ModelServiceProviderListRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/platform/providers", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ModelServiceProviderListRsp> queryPlatformProviders(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "QueryPlatformProvidersQo: converted from multi query params") @Valid
    QueryPlatformProvidersQo queryPlatformProvidersQo);

    @ApiOperation(value = "", nickname = "queryUserProviders", notes = "查询用户接入模型服务供应商列表",
        response = ModelServiceProviderListRsp.class, tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型服务供应商列表", response = ModelServiceProviderListRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/integration/providers", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ModelServiceProviderListRsp> queryUserProviders(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "QueryUserProvidersQo: converted from multi query params") @Valid
    QueryUserProvidersQo queryUserProvidersQo);

    @ApiOperation(value = "", nickname = "updateModelServiceProvider", notes = "更新供应商信息",
        tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/integration/providers/{id}",
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Void> updateModelServiceProvider(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id,
        @Parameter(in = ParameterIn.QUERY, description = "", required = false, schema = @Schema()) @ApiParam(value = "") @RequestParam(value = "available_check", required = false) Boolean availableCheck,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ModelServiceProviderReq body);

    @ApiOperation(value = "", nickname = "updateModelServiceProviderAuthInfo", notes = "更新供应商权鉴信息",
        tags = {"ProviderMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/integration/providers/auth-info/{id}",
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Void> updateModelServiceProviderAuthInfo(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id,
        @Parameter(in = ParameterIn.QUERY, description = "", required = false, schema = @Schema()) @ApiParam(value = "") @RequestParam(value = "available_check", required = false) Boolean availableCheck,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ProviderAuthInfoReq body);

}
