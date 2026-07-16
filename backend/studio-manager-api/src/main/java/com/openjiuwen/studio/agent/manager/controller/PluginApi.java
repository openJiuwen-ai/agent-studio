/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.BatchCreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolReq;
import com.openjiuwen.studio.agent.manager.dto.CreatePluginToolRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ErrorInfo;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.GetPluginVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ListPluginsQo;
import com.openjiuwen.studio.agent.manager.dto.ListToolsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyPluginRsp;
import com.openjiuwen.studio.agent.manager.dto.ParsePluginReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateReq;
import com.openjiuwen.studio.agent.manager.dto.PluginAuthUpdateRsp;
import com.openjiuwen.studio.agent.manager.dto.PluginListRsp;
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

import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

@Api(value = "Plugin", description = "the Plugin API")
@Validated

/**
 * PluginApi interface
 */ public interface PluginApi {
    @ApiOperation(value = "创建多个工具", nickname = "batchCreateTool", notes = "创建多个工具",
        response = BatchCreatePluginToolRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建工具响应体", response = BatchCreatePluginToolRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/batchtools", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BatchCreatePluginToolRsp> batchCreateTool(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "创建工具请求体", required = true) @Valid @RequestBody
        BatchCreatePluginToolReq body);

    @ApiOperation(value = "创建一个插件", nickname = "createPlugin", notes = "创建一个插件",
        response = CreatePluginToolRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建插件响应体", response = CreatePluginToolRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreatePluginToolRsp> createPlugin(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建插件请求体", required = true) @Valid @RequestBody CreatePluginToolReq body);

    @ApiOperation(value = "创建一个工具", nickname = "createTool", notes = "创建一个工具",
        response = CreatePluginToolRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建工具响应体", response = CreatePluginToolRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/tools", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreatePluginToolRsp> createTool(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建工具请求体", required = true) @Valid @RequestBody CreatePluginToolReq body);

    @ApiOperation(value = "根据工具id创建工具OpenAPI定义", nickname = "createToolOpenAPIById",
        notes = "根据工具id创建工具OpenAPI定义", response = BaseResp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建工具OpenAPI定义响应体。", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/openapi/{plugin_id}",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BaseResp> createToolOpenAPIById(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "插件ID。", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @ApiParam(value = "工具ID。", required = true) @RequestParam(value = "tool_id", required = true)
        String toolId);

    @ApiOperation(value = "删除一个插件", nickname = "deletePlugin",
        notes = "删除一个插件，如果assistant引用了该工具，必须先进行解绑，否则删除报错", response = CommonDeleteRsp.class,
        tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除工具响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deletePlugin(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "根据工具id和版本id进行版本还原", nickname = "updatePluginVersionByVersionId",
        notes = "根据工具id和版本id进行版本还原", response = BaseResp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "插件版本响应体", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BaseResp> updatePluginVersionByVersionId(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "插件ID", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "插件版本id", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除一个工具版本定义", nickname = "deletePluginVersion", notes = "删除一个工具版本定义",
        response = CommonDeleteRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除工具版本定义响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deletePluginVersion(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除一个工具", nickname = "deleteTool",
        notes = "删除一个工具，如果assistant引用了该工具，必须先进行解绑，否则删除报错", response = BaseResp.class,
        tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除工具响应体", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/tools/{tool_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<BaseResp> deleteTool(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "插件id", required = true) @RequestParam(value = "plugin_id", required = true)
        String pluginId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "导出插件", nickname = "exportplugins", notes = "导出插件", response = Resource.class,
        tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出文档", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/export", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportplugins(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "导出参数设置", required = true) @Valid @RequestBody ExportParams body);

    @ApiOperation(value = "获取一个工具版本定义", nickname = "getPluginVersion", notes = "获取一个工具版本定义",
        response = BaseResp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "workflow指定版本定义", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<BaseResp> getPluginVersion(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @ApiParam(value = "GetPluginVersionQo: converted from multi query params") @Valid
        GetPluginVersionQo getPluginVersionQo);

    @ApiOperation(value = "导入插件", nickname = "importplugins", notes = "导入插件", response = ImportRsp.class,
        tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入插件响应体", response = ImportRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/import", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ImportRsp> importplugins(@NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_ids", required = false) String importIds);

    @ApiOperation(value = "更新预置插件免费配额", nickname = "incrementPluginFreeTrialUsageQuota",
        notes = "实时更新预置插件免费配额", response = BaseResp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "额度更新成功", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = ErrorInfo.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{domain_id}/freetrialincrement",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BaseResp> incrementPluginFreeTrialUsageQuota(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("domain_id") String domainId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "预置插件ID", required = true) @RequestParam(value = "plugin_id", required = true)
        String pluginId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询工具版本列表", nickname = "listPluginVersions", notes = "查询工具版本列表",
        response = VersionListRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本列表", response = VersionListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}/versions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<VersionListRsp> listPluginVersions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取插件列表", nickname = "listPlugins", notes = "获取插件列表",
        response = PluginListRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = PluginListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<PluginListRsp> listPlugins(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListPluginsQo: converted from multi query params") @Valid ListPluginsQo listPluginsQo);

    @ApiOperation(value = "获取工具列表", nickname = "listTools", notes = "获取工具列表", response = BaseResp.class,
        tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/tools", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<BaseResp> listTools(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListToolsQo: converted from multi query params") @Valid ListToolsQo listToolsQo);

    @ApiOperation(value = "修改一个插件", nickname = "modifyPlugin", notes = "修改一个插件",
        response = ModifyPluginRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改工具响应体", response = ModifyPluginRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ModifyPluginRsp> modifyPlugin(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @ApiParam(value = "修改工具请求体", required = true) @Valid @RequestBody ModifyPluginReq body);

    @ApiOperation(value = "修改一个工具", nickname = "modifyTool", notes = "修改一个工具", response = BaseResp.class,
        tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改工具响应体", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/tools/{tool_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<BaseResp> modifyTool(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
        @PathVariable("tool_id") String toolId,
        @NotNull @ApiParam(value = "修改工具请求体", required = true) @Valid @RequestBody CreatePluginToolReq body);

    @ApiOperation(value = "将openapi定义解析为平台的插件结构", nickname = "parsePlugin",
        notes = "将openapi定义解析为平台的插件结构", response = BaseResp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "插件解析成功", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/parse-plugin", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BaseResp> parsePlugin(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ParsePluginReq body);

    @ApiOperation(value = "发布一个工具版本", nickname = "releasePluginVersion", notes = "发布一个工具版本",
        response = VersionInfo.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "发布的工具信息", response = VersionInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}/versions",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<VersionInfo> releasePluginVersion(
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "版本创建信息") @Valid @RequestBody(required = false) CreateVersionReq body);

    @ApiOperation(value = "获取一个插件", nickname = "retrievePlugin", notes = "获取一个插件",
        response = BaseResp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<BaseResp> retrievePlugin(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工具id", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "更新插件鉴权信息", nickname = "updatePluginAuthInfo",
        notes = "更新插件鉴权信息。若插件已发布则仅更新鉴权（不改变版本）；若未发布，则更新鉴权并自动发布初始版本。",
        response = PluginAuthUpdateRsp.class, tags = {"Plugin"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "更新成功", response = PluginAuthUpdateRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorInfo.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorInfo.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorInfo.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorInfo.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/plugins/{plugin_id}/auth-info",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<PluginAuthUpdateRsp> updatePluginAuthInfo(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "插件id", required = true, schema = @Schema())
        @PathVariable("plugin_id") String pluginId,
        @NotNull @ApiParam(value = "更新插件鉴权信息请求体", required = true) @Valid @RequestBody
        PluginAuthUpdateReq body);

}
