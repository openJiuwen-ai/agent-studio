/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.DeveloperAgentListRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListDeveloperAgentsQo;

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
import jakarta.validation.constraints.Size;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

@Api(value = "TenantOpenApi", description = "the TenantOpenApi API")
@Validated

/**
 * TenantOpenApiApi interface
 */ public interface TenantOpenApiApi {
    @ApiOperation(value = "查询是否存在已发布的agent", nickname = "existPublishedAgent",
        notes = "查询是否存在已发布的agent", response = Boolean.class, tags = {"TenantOpenApi"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "是否存在已发布的agent", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/open/developer/agent-manager/agents/exist/published", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Boolean> existPublishedAgent(
        @NotNull @Size(min = 1, max = 256)
        @Parameter(in = ParameterIn.QUERY, description = "账号id", required = true, schema = @Schema())
        @ApiParam(value = "账号id", required = true)
        @RequestParam(value = "domainId", required = true) String domainId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "发布时间", required = true, schema = @Schema())
        @ApiParam(value = "发布时间", required = true) @RequestParam(value = "publishedDate", required = true)
        Long publishedDate);

    @ApiOperation(value = "获取agent列表", nickname = "listDeveloperAgents", notes = "获取agent列表",
        response = DeveloperAgentListRsp.class, tags = {"TenantOpenApi"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "搜索的agent列表", response = DeveloperAgentListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/open/developer/agent-manager/agents", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<DeveloperAgentListRsp> listDeveloperAgents(
        @NotNull @ApiParam(value = "", required = true) @RequestHeader(value = "X-User-Info", required = true)
        String xUserInfo, @ApiParam(value = "ListDeveloperAgentsQo: converted from multi query params") @Valid
        ListDeveloperAgentsQo listDeveloperAgentsQo);

}
