/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.ListRouterStrategyQo;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyBaseInfo;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyListResponse;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyRequest;

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

@Api(value = "RouterStrategyMgmt", description = "the RouterStrategyMgmt API")
@Validated

/**
 * RouterStrategyMgmtApi interface
 */ public interface RouterStrategyMgmtApi {
    @ApiOperation(value = "", nickname = "createRouterStrategy", notes = "创建模型路由策略",
        response = RouterStrategyBaseInfo.class, tags = {"RouterStrategyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建的路由策略信息", response = RouterStrategyBaseInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-router-strategies", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<RouterStrategyBaseInfo> createRouterStrategy(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody RouterStrategyRequest body);

    @ApiOperation(value = "", nickname = "deleteRouterStrategy", notes = "删除模型路由策略",
        tags = {"RouterStrategyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-router-strategies/{strategy_id}", method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteRouterStrategy(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("strategy_id") String strategyId);

    @ApiOperation(value = "", nickname = "listRouterStrategy", notes = "查看我的模型路由策略列表",
        response = RouterStrategyListResponse.class, tags = {"RouterStrategyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型路由策略列表", response = RouterStrategyListResponse.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-router-strategies", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<RouterStrategyListResponse> listRouterStrategy(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "ListRouterStrategyQo: converted from multi query params") @Valid
    ListRouterStrategyQo listRouterStrategyQo);

    @ApiOperation(value = "", nickname = "strategyDetail", notes = "查询模型路由策略详情",
        response = RouterStrategyBaseInfo.class, tags = {"RouterStrategyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "模型路由策略详情", response = RouterStrategyBaseInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-router-strategies/{strategy_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<RouterStrategyBaseInfo> strategyDetail(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("strategy_id") String strategyId);

    @ApiOperation(value = "", nickname = "updateRouterStrategy", notes = "修改模型路由策略",
        tags = {"RouterStrategyMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-router-strategies/{strategy_id}", consumes = {"application/json"},
        method = RequestMethod.PUT)
    ResponseEntity<Void> updateRouterStrategy(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$")
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("strategy_id") String strategyId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody RouterStrategyRequest body);

}
