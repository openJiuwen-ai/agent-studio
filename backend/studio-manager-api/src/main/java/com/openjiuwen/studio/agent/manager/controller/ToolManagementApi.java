/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateToolOpenAPIResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreateToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.GetToolVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ListToolsV1Qo;
import com.openjiuwen.studio.agent.manager.dto.ModifyToolReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyToolRsp;
import com.openjiuwen.studio.agent.manager.dto.Tool;
import com.openjiuwen.studio.agent.manager.dto.ToolCredential;
import com.openjiuwen.studio.agent.manager.dto.ToolListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;

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

@Api(value = "ToolManagement", description = "the ToolManagement API")
@Validated

/**
 * ToolManagementApi interface
 */ public interface ToolManagementApi {
    @ApiOperation(value = "创建一个插件鉴权凭证", nickname = "addToolCredential", notes = "创建一个插件鉴权凭证",
        response = ToolCredential.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "添加插件鉴权凭证响应体", response = ToolCredential.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/credentials",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ToolCredential> addToolCredential(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "插件id", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Parameter(in = ParameterIn.QUERY, description = "是否需要校验鉴权", required = false, schema = @Schema()) @ApiParam(value = "是否需要校验鉴权") @RequestParam(value = "need_validate", required = false)
        Boolean needValidate,
        @NotNull @ApiParam(value = "创建插件鉴权凭证请求体", required = true) @Valid @RequestBody ToolCredential body);

    @ApiOperation(value = "检查当前工具是否已经被使用", nickname = "checkToolIsUsed",
        notes = "检查当前工具是否已经被使用", response = Boolean.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "是否被使用", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/check", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Boolean> checkToolIsUsed(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "创建一个工具OpenAPI定义", nickname = "createToolOpenAPI", notes = "创建一个工具OpenAPI定义",
        response = CreateToolOpenAPIResponseBody.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建工具OpenAPI定义响应体", response = CreateToolOpenAPIResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/openapi", produces = {"application/json"},
        consumes = {"application/json;charset=utf-8"}, method = RequestMethod.POST)
    ResponseEntity<CreateToolOpenAPIResponseBody> createToolOpenAPI(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建工具请求体", required = true) @Valid @RequestBody CreateToolReq body);

    @ApiOperation(value = "根据工具id创建工具OpenAPI定义", nickname = "createToolOpenAPIByIdV1",
        notes = "根据工具id创建工具OpenAPI定义", response = CreateToolOpenAPIResponseBody.class,
        tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建工具OpenAPI定义响应体", response = CreateToolOpenAPIResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/openapi/{tool_id}", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<CreateToolOpenAPIResponseBody> createToolOpenAPIByIdV1(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "插件ID。", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id。", required = true, schema = @Schema()) @ApiParam(value = "项目空间id。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "创建一个工具", nickname = "createToolV1", notes = "创建一个工具",
        response = CreateToolRsp.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建工具响应体", response = CreateToolRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateToolRsp> createToolV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建工具请求体", required = true) @Valid @RequestBody CreateToolReq body);

    @ApiOperation(value = "删除一个插件鉴权凭证", nickname = "deleteToolCredential",
        notes = "删除一个插件鉴权凭证，如果该工具被引用，必须先进行解绑，否则删除报错", response = CommonDeleteRsp.class,
        tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除插件鉴权凭证响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/credentials",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteToolCredential(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
    @PathVariable("tool_id") String toolId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "删除一个工具", nickname = "deleteToolV1",
        notes = "删除一个工具，如果assistant引用了该工具，必须先进行解绑，否则删除报错", response = CommonDeleteRsp.class,
        tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除工具响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteToolV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
    @PathVariable("tool_id") String toolId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "删除一个工具版本定义", nickname = "deleteToolVersion", notes = "删除一个工具版本定义",
        response = CommonDeleteRsp.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除工具版本定义响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteToolVersion(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取一个工具版本定义", nickname = "getToolVersion", notes = "获取一个工具版本定义",
        response = Tool.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "workflow指定版本定义", response = Tool.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Tool> getToolVersion(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @ApiParam(value = "GetToolVersionQo: converted from multi query params") @Valid
        GetToolVersionQo getToolVersionQo);

    @ApiOperation(value = "查询工具版本列表", nickname = "listToolVersions", notes = "查询工具版本列表",
        response = VersionListRsp.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本列表", response = VersionListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/versions", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<VersionListRsp> listToolVersions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取工具列表", nickname = "listToolsV1", notes = "获取工具列表",
        response = ToolListRsp.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = ToolListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ToolListRsp> listToolsV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListToolsV1Qo: converted from multi query params") @Valid ListToolsV1Qo listToolsV1Qo);

    @ApiOperation(value = "修改一个工具", nickname = "modifyToolV1", notes = "修改一个工具",
        response = ModifyToolRsp.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改工具响应体", response = ModifyToolRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ModifyToolRsp> modifyToolV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @ApiParam(value = "修改工具请求体", required = true) @Valid @RequestBody ModifyToolReq body);

    @ApiOperation(value = "发布一个工具版本", nickname = "releaseToolVersion", notes = "发布一个工具版本",
        response = VersionInfo.class, tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "发布的工具信息", response = VersionInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}/versions", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<VersionInfo> releaseToolVersion(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "版本创建信息") @Valid @RequestBody(required = false) CreateVersionReq body);

    @ApiOperation(value = "获取一个工具", nickname = "retrieveToolV1", notes = "获取一个工具", response = Tool.class,
        tags = {"ToolManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = Tool.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/{tool_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Tool> retrieveToolV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
    @PathVariable("tool_id") String toolId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

}
