/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.manager.dto.CesMetricDataResp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.IdListRequest;
import com.openjiuwen.studio.agent.manager.dto.ListServersQo;
import com.openjiuwen.studio.agent.manager.dto.McpDataProcessBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServerDetailReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerRatingReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBaseInfoListResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceBatchDeployResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDataResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDeployReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceDetailInfoDto;
import com.openjiuwen.studio.agent.manager.dto.McpServiceModifyReq;
import com.openjiuwen.studio.agent.manager.dto.McpServiceSkinnyEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceStatisticResp;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsEntity;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolsTestReq;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.McpServicesCesSuccessRateLineChartQo;
import com.openjiuwen.studio.agent.manager.dto.PageInfoV2;

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

import java.util.List;
import java.util.Map;

@Api(value = "McpServiceManager", description = "the McpServiceManager API")
@Validated

/**
 * McpServiceManagerApi interface
 */ public interface McpServiceManagerApi {
    @ApiOperation(value = "批量部署MCP服务", nickname = "batchDeployServices", notes = "一次性部署多个MCP服务",
        response = McpServiceBatchDeployResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量部署任务已接受", response = McpServiceBatchDeployResp.class),
        @ApiResponse(code = 400, message = "请求参数错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 409, message = "资源冲突（如服务已存在）", response = ErrorRsp.class),
        @ApiResponse(code = 429, message = "请求过于频繁", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/deploy/batch", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServiceBatchDeployResp> batchDeployServices(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间ID", required = true, schema = @Schema()) @ApiParam(value = "项目空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @Parameter(in = ParameterIn.QUERY, description = "MCP来源", required = true, schema = @Schema()) @ApiParam(value = "MCP来源", required = true) @RequestParam(value = "resource", required = true)
        String resource, @NotNull @ApiParam(value = "批量部署请求参数", required = true) @Valid @RequestBody
        McpServiceBatchDeployReq body);

    @ApiOperation(value = "创建MCP服务", nickname = "createServer", notes = "创建MCP服务", response = String.class,
        tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/server/create", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建服务参数", required = true) @Valid @RequestBody McpServerDetailReq body);

    @ApiOperation(value = "查询数据加工列表", nickname = "dataProcessList", notes = "查询数据加工列表",
        response = McpDataProcessBaseInfoListResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 数据处理 服务响应体", response = McpDataProcessBaseInfoListResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/dataProcess/list", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpDataProcessBaseInfoListResp> dataProcessList(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "检索语言", required = false, schema = @Schema()) @ApiParam(value = "检索语言") @RequestParam(value = "language", required = false) String language,
        @Pattern(regexp = "[\\u4e00-\\u9fa5a-zA-Z0-9][\\u4e00-\\u9fa5_a-zA-Z0-9\\-\\(\\)]*") @Size(max = 255)
        @Parameter(in = ParameterIn.QUERY, description = "数据节点名称", required = false, schema = @Schema()) @ApiParam(value = "数据节点名称") @RequestParam(value = "name", required = false) String name,
        @NotNull @ApiParam(value = "page_info", required = true) @Valid @RequestBody PageInfoV2 body);

    @ApiOperation(value = "删除MCP服务", nickname = "deleteService", notes = "删除MCP服务", response = String.class,
        tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/delete/{id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<String> deleteService(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目空间id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "部署MCP服务", nickname = "deploy", notes = "部署MCP服务", response = String.class,
        tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/deploy/{id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> deploy(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "服务id", required = true, schema = @Schema())
        @PathVariable("id") String id,
        @NotNull @ApiParam(value = "创建服务参数", required = true) @Valid @RequestBody McpServiceDeployReq body);

    @ApiOperation(value = "查询MCP服务列表", nickname = "listServers", notes = "查询MCP服务列表",
        response = McpServerBaseInfoListResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerBaseInfoListResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/server/list", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServerBaseInfoListResp> listServers(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListServersQo: converted from multi query params") @Valid ListServersQo listServersQo);

    @ApiOperation(value = "查询MCP服务列表", nickname = "listServices", notes = "查询MCP服务列表",
        response = McpServiceBaseInfoListResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceBaseInfoListResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/list", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServiceBaseInfoListResp> listServices(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "检索语言", required = false, schema = @Schema()) @ApiParam(value = "检索语言") @RequestParam(value = "language", required = false) String language,
        @Size(max = 255) @Parameter(in = ParameterIn.QUERY, description = "服务名称", required = false, schema = @Schema()) @ApiParam(value = "服务名称") @RequestParam(value = "name", required = false) String name,
        @Parameter(in = ParameterIn.QUERY, description = "部署状态", required = false, schema = @Schema()) @ApiParam(value = "部署状态") @RequestParam(value = "fc_instance_status", required = false)
        String fcInstanceStatus, @Parameter(in = ParameterIn.QUERY, description = "MCP节点类型", required = false, schema = @Schema()) @ApiParam(value = "MCP节点类型", allowableValues = "DataAcquisition, DataProcess")
        @RequestParam(value = "node_type", required = false) String nodeType,
        @Parameter(in = ParameterIn.QUERY, description = "MCP节点可见性", required = false, schema = @Schema()) @ApiParam(value = "MCP节点可见性", allowableValues = "global, workspace")
        @RequestParam(value = "visibility", required = false) String visibility,
        @NotNull @ApiParam(value = "page_info", required = true) @Valid @RequestBody PageInfoV2 body);

    @ApiOperation(value = "查询MCP服务汇总", nickname = "listServicesSummary", notes = "查询MCP服务汇总",
        response = Integer.class, responseContainer = "Map", tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Map.class, responseContainer = "Map"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/list/summary", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Map<String, Integer>> listServicesSummary(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询MCP服务列表", nickname = "listServicesWithRuntimeInfo", notes = "查询MCP服务列表",
        response = McpServiceBaseInfoListResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceBaseInfoListResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/list-run", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServiceBaseInfoListResp> listServicesWithRuntimeInfo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Parameter(in = ParameterIn.QUERY, description = "检索语言", required = false, schema = @Schema()) @ApiParam(value = "检索语言") @RequestParam(value = "language", required = false) String language,
        @Pattern(regexp = "[\\u4e00-\\u9fa5a-zA-Z0-9][\\u4e00-\\u9fa5_a-zA-Z0-9\\-\\(\\)]*") @Size(max = 255)
        @Parameter(in = ParameterIn.QUERY, description = "服务名称", required = false, schema = @Schema()) @ApiParam(value = "服务名称") @RequestParam(value = "name", required = false) String name,
        @NotNull @ApiParam(value = "page_info", required = true) @Valid @RequestBody PageInfoV2 body);

    @ApiOperation(value = "MCP服务评分", nickname = "mcpServerRating", notes = "MCP服务评分", response = Boolean.class,
        tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/server/rating", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Boolean> mcpServerRating(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "mcpServerRatingReq", required = true) @Valid @RequestBody McpServerRatingReq body);

    @ApiOperation(value = "MCP服务推荐", nickname = "mcpServerRecommendation", notes = "MCP服务推荐",
        response = McpServerBaseInfoDto.class, responseContainer = "List", tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = McpServerBaseInfoDto.class,
            responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/server/recommendation", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<List<McpServerBaseInfoDto>> mcpServerRecommendation(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询MCP服务调用量折线图", nickname = "mcpServicesCesLineChart",
        notes = "查询MCP服务调用量折线图", response = CesMetricDataResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = CesMetricDataResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/metric/data/ces/count/chart/{id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<CesMetricDataResp> mcpServicesCesLineChart(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "id", required = true, schema = @Schema()) @PathVariable("id")
    String id, @ApiParam(value = "McpServicesCesLineChartQo: converted from multi query params") @Valid
    McpServicesCesLineChartQo mcpServicesCesLineChartQo);

    @ApiOperation(value = "查询MCP服务调用数据", nickname = "mcpServicesCesStatistic", notes = "查询MCP服务调用数据",
        response = McpServiceStatisticResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = McpServiceStatisticResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/service/metric/data/ces/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServiceStatisticResp> mcpServicesCesStatistic(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "服务id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "查询MCP服务重调用量", nickname = "mcpServicesCesStatisticListMcp",
        notes = "查询MCP服务重调用量", response = Long.class, responseContainer = "Map", tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Map.class, responseContainer = "Map"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/service/metric/data/ces/count/ids", produces = {"application/json"},
        consumes = {"*/*"}, method = RequestMethod.GET)
    ResponseEntity<Map<String, Long>> mcpServicesCesStatisticListMcp(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody IdListRequest body);

    @ApiOperation(value = "查询MCP服务成功率折线图", nickname = "mcpServicesCesSuccessRateLineChart",
        notes = "查询MCP服务成功率折线图", response = CesMetricDataResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = CesMetricDataResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/metric/data/ces/success_rate/chart/{id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<CesMetricDataResp> mcpServicesCesSuccessRateLineChart(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "id", required = true, schema = @Schema()) @PathVariable("id")
        String id, @ApiParam(value = "McpServicesCesSuccessRateLineChartQo: converted from multi query params") @Valid
        McpServicesCesSuccessRateLineChartQo mcpServicesCesSuccessRateLineChartQo);

    @ApiOperation(value = "查询MCP服务工具列表", nickname = "mcpServicesToolsList", notes = "查询MCP服务工具列表",
        response = String.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/tools/list/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<String> mcpServicesToolsList(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "服务id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "查询MCP服务工具列表-流中引用", nickname = "mcpServicesToolsListWithFlow",
        notes = "查询MCP服务工具列表-流中引用", response = McpServiceToolsEntity.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceToolsEntity.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/tools/info/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServiceToolsEntity> mcpServicesToolsListWithFlow(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "服务id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "修改mcp服务信息", nickname = "modifyService", notes = "修改mcp服务信息",
        response = Boolean.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/modify", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Boolean> modifyService(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "mcpServiceModifyReq", required = true) @Valid @RequestBody
        McpServiceModifyReq body);

    @ApiOperation(value = "根据ids查询mcp列表", nickname = "queryMcpListByIds", notes = "根据ids查询mcp列表",
        response = McpServiceSkinnyEntity.class, responseContainer = "List", tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceSkinnyEntity.class,
            responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/list/ids", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<List<McpServiceSkinnyEntity>> queryMcpListByIds(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema()) @ApiParam(value = "", required = true) @Valid @RequestParam(value = "ids", required = true)
        List<String> ids);

    @ApiOperation(value = "查询MCP服务详情", nickname = "queryServerDetail", notes = "查询MCP服务详情",
        response = McpServerDetailInfoDto.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerDetailInfoDto.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/server/detail/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServerDetailInfoDto> queryServerDetail(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "服务id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "查询MCP服务详情", nickname = "queryServiceDetail", notes = "查询MCP服务详情",
        response = McpServiceDetailInfoDto.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceDetailInfoDto.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/detail/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServiceDetailInfoDto> queryServiceDetail(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目空间id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "查询MCP服务详情", nickname = "queryServiceDetailForRuntime", notes = "查询MCP服务详情",
        response = McpServiceDetailInfoDto.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceDetailInfoDto.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/detail-run/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServiceDetailInfoDto> queryServiceDetailForRuntime(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目空间id", required = true, schema = @Schema())
        @PathVariable("id") String id);

    @ApiOperation(value = "执行MCP服务工具", nickname = "testServicesTools", notes = "执行MCP服务工具",
        response = McpServiceDataResp.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServiceDataResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/tools/test", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServiceDataResp> testServicesTools(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody McpServiceToolsTestReq body);

    @ApiOperation(value = "修改mcp服务信息", nickname = "updateMcpAuthInfo", notes = "修改mcp服务信息",
        response = Boolean.class, tags = {"McpServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/mcp/service/auth-info/{id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Boolean> updateMcpAuthInfo(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("id") String id, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "工具鉴权方式，分为用户级、服务级和IAM方式", required = true) @Valid @RequestBody
        AuthInfo body);

}
