/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListMcpServersQo;
import com.openjiuwen.studio.agent.manager.dto.McpCallToolReq;
import com.openjiuwen.studio.agent.common.dto.mcp.McpCallToolResp;
import com.openjiuwen.studio.agent.manager.dto.McpServerConfig;
import com.openjiuwen.studio.agent.manager.dto.McpServerInfo;
import com.openjiuwen.studio.agent.manager.dto.McpServerInfoList;
import com.openjiuwen.studio.agent.manager.dto.McpServerReq;
import com.openjiuwen.studio.agent.manager.dto.McpServerTools;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
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

@Api(value = "McpServerManager", description = "the McpServerManager API")
@Validated

/**
 * McpServerManagerApi interface
 */ public interface McpServerManagerApi {
    @ApiOperation(value = "添加一个mcp服务", nickname = "addMcpServer", notes = "添加一个mcp服务",
        response = McpServerInfo.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServerInfo> addMcpServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "添加 mcp 服务请求体", required = true) @Valid @RequestBody McpServerReq body);

    @ApiOperation(value = "运行 mcp 服务指定工具", nickname = "callTool", notes = "运行 mcp 服务指定工具",
        response = McpCallToolResp.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "mcp 工具运行结果", response = McpCallToolResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}/tools/run",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpCallToolResp> callTool(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("server_id") String serverId,
        @NotNull @ApiParam(value = "请求参数", required = true) @Valid @RequestBody McpCallToolReq body);

    @ApiOperation(value = "配置 mcp 服务", nickname = "configMcpServer", notes = "配置 mcp 服务",
        response = McpServerConfig.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerConfig.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}/configs",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServerConfig> configMcpServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "mcp 服务 id", required = true, schema = @Schema())
        @PathVariable("server_id") String serverId,
        @NotNull @ApiParam(value = "配置信息", required = true) @Valid @RequestBody McpServerConfig body);

    @ApiOperation(value = "删除 mcp 服务", nickname = "deleteMcpServer", notes = "删除 mcp 服务",
        response = CommonDeleteRsp.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除MCP服务响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteMcpServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "mcp 服务id", required = true, schema = @Schema())
    @PathVariable("server_id") String serverId);

    @ApiOperation(value = "删除 mcp 服务配置", nickname = "deleteMcpServerConfig", notes = "删除 mcp 服务配置",
        response = CommonDeleteRsp.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除MCP服务配置响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}/configs",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteMcpServerConfig(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "mcp 服务 id", required = true, schema = @Schema())
    @PathVariable("server_id") String serverId);

    @ApiOperation(value = "获取 mcp 服务详情", nickname = "getMcpServer", notes = "获取 mcp 服务详情",
        response = McpServerInfo.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取 mcp 服务响应体", response = McpServerInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServerInfo> getMcpServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "mcp 服务id", required = true, schema = @Schema())
    @PathVariable("server_id") String serverId);

    @ApiOperation(value = "获取 mcp 服务工具列表", nickname = "listMcpServerTools", notes = "获取 mcp 服务工具列表",
        response = McpServerTools.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerTools.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/tools", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<McpServerTools> listMcpServerTools(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Min(0) @Max(10000)
        @Parameter(in = ParameterIn.QUERY, description = "分页起始页，默认 0", required = false, schema = @Schema())
        @ApiParam(value = "分页起始页，默认 0", allowableValues = "10000, 0", defaultValue = "0")
        @RequestParam(value = "offset", required = false, defaultValue = "0") Integer offset,
        @Min(0) @Max(100)
        @Parameter(in = ParameterIn.QUERY, description = "分页大小，默认 10", required = false, schema = @Schema())
        @ApiParam(value = "分页大小，默认 10", allowableValues = "100, 0", defaultValue = "10")
        @RequestParam(value = "limit", required = false, defaultValue = "10") Integer limit,
        @NotNull @ApiParam(value = "过滤条件", required = true) @Valid @RequestBody McpServerReq body);

    @ApiOperation(value = "获取 mcp 服务列表", nickname = "listMcpServers", notes = "获取 mcp 服务列表",
        response = McpServerInfoList.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerInfoList.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<McpServerInfoList> listMcpServers(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListMcpServersQo: converted from multi query params") @Valid
        ListMcpServersQo listMcpServersQo);

    @ApiOperation(value = "更新 mcp 服务", nickname = "updateMcpServer", notes = "更新 mcp 服务",
        response = McpServerInfo.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "更新 mcp 服务响应体", response = McpServerInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<McpServerInfo> updateMcpServer(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "mcp 服务id", required = true, schema = @Schema())
        @PathVariable("server_id") String serverId,
        @NotNull @ApiParam(value = "更新 mcp 服务请求体", required = true) @Valid @RequestBody McpServerReq body);

    @ApiOperation(value = "配置 mcp 服务", nickname = "updateMcpServerConfig", notes = "配置 mcp 服务",
        response = McpServerConfig.class, tags = {"McpServerManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加 mcp 服务响应体", response = McpServerConfig.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/mcp-servers/{server_id}/configs",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<McpServerConfig> updateMcpServerConfig(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "mcp 服务 id", required = true, schema = @Schema())
        @PathVariable("server_id") String serverId,
        @NotNull @ApiParam(value = "配置信息", required = true) @Valid @RequestBody McpServerConfig body);

}
