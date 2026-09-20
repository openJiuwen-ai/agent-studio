/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.Environment;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentInfoRequest;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentInstances;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariables;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariablesExport;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariablesResp;
import com.openjiuwen.studio.agent.manager.dto.Environments;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListSubnets;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentInstancesQo;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentVariablesQo;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentsListQo;
import com.openjiuwen.studio.agent.manager.dto.ValidationVariablesImport;
import com.openjiuwen.studio.agent.manager.dto.VpcInfo;

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

import java.util.List;

@Api(value = "EnvironmentServiceManager", description = "the EnvironmentServiceManager API")
@Validated

/**
 * EnvironmentServiceManagerApi interface
 */ public interface EnvironmentServiceManagerApi {
    @ApiOperation(value = "创建环境", nickname = "createEnvironmentInfo", notes = "创建环境", response = String.class,
        tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createEnvironmentInfo(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody EnvironmentInfoRequest body);

    @ApiOperation(value = "创建环境变量", nickname = "createEnvironmentVariables", notes = "创建环境变量",
        response = String.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "更新环境变量响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}/variables",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> createEnvironmentVariables(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "环境ID", required = true, schema = @Schema())
        @PathVariable("environment_id") String environmentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody EnvironmentVariables body);

    @ApiOperation(value = "删除环境信息", nickname = "deleteEnvironment", notes = "删除环境信息",
        response = Boolean.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Boolean> deleteEnvironment(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "环境id", required = true, schema = @Schema())
    @PathVariable("environment_id") String environmentId);

    @ApiOperation(value = "删除环境变量", nickname = "deleteEnvironmentVariables", notes = "删除环境变量",
        response = String.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "更新环境变量响应体", response = String.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}/variables/{env_variable_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<String> deleteEnvironmentVariables(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "环境ID", required = true, schema = @Schema())
        @PathVariable("environment_id") String environmentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "环境变量ID", required = true, schema = @Schema())
        @PathVariable("env_variable_id") String envVariableId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "环境变量导入前验证", nickname = "environmentVariableImportFileValidation",
        notes = "环境变量导入前验证", response = ValidationVariablesImport.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入环境文件", response = ValidationVariablesImport.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments-variables/import-validation",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ValidationVariablesImport> environmentVariableImportFileValidation(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "environment_id", required = true) String environmentId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = false)
        MultipartFile file);

    @ApiOperation(value = "环境变量导出", nickname = "exportEnvironmentVariable", notes = "环境变量导出",
        response = Resource.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出环境文件", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments-variables/export",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportEnvironmentVariable(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "导出参数设置", required = true) @Valid @RequestBody
        EnvironmentVariablesExport body);

    @ApiOperation(value = "环境变量导入", nickname = "importEnvironmentVariable", notes = "环境变量导入",
        response = Boolean.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入环境文件", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments-variables/import",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<Boolean> importEnvironmentVariable(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "environment_id", required = true) String environmentId,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema()) @Valid
        @RequestPart(value = "cover_variables", required = true) List<String> coverVariables,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = false)
        MultipartFile file);

    @ApiOperation(value = "设置为默认环境", nickname = "isDefaultEnvironments", notes = "设置为默认环境",
        response = Boolean.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}/is_default",
        produces = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Boolean> isDefaultEnvironments(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "环境id", required = true, schema = @Schema())
    @PathVariable("environment_id") String environmentId);

    @ApiOperation(value = "修改环境", nickname = "modifyEnvironmentInfo", notes = "修改环境", response = Boolean.class,
        tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Boolean.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Boolean> modifyEnvironmentInfo(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "环境第", required = true, schema = @Schema())
        @PathVariable("environment_id") String environmentId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody EnvironmentInfoRequest body);

    @ApiOperation(value = "查询环境详情", nickname = "queryEnvironment", notes = "查询环境详情",
        response = Environment.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Environment.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Environment> queryEnvironment(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "环境id", required = true, schema = @Schema())
    @PathVariable("environment_id") String environmentId);

    @ApiOperation(value = "查询环境中关联的实例信息", nickname = "queryEnvironmentInstances",
        notes = "查询环境中关联的实例信息", response = EnvironmentInstances.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = EnvironmentInstances.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}/instance",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<EnvironmentInstances> queryEnvironmentInstances(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "环境id", required = true, schema = @Schema())
        @PathVariable("environment_id") String environmentId,
        @ApiParam(value = "QueryEnvironmentInstancesQo: converted from multi query params") @Valid
        QueryEnvironmentInstancesQo queryEnvironmentInstancesQo);

    @ApiOperation(value = "查询环境变量列表", nickname = "queryEnvironmentVariables", notes = "查询环境变量列表",
        response = EnvironmentVariablesResp.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询环境变量列表响应体", response = EnvironmentVariablesResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments-variables", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<EnvironmentVariablesResp> queryEnvironmentVariables(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "QueryEnvironmentVariablesQo: converted from multi query params") @Valid
        QueryEnvironmentVariablesQo queryEnvironmentVariablesQo);

    @ApiOperation(value = "查询环境列表", nickname = "queryEnvironmentsList", notes = "查询环境列表",
        response = Environments.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = Environments.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Environments> queryEnvironmentsList(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "QueryEnvironmentsListQo: converted from multi query params") @Valid
        QueryEnvironmentsListQo queryEnvironmentsListQo);

    @ApiOperation(value = "查询vpc列表", nickname = "queryVpcs", notes = "查询vpc列表", response = VpcInfo.class,
        responseContainer = "List", tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = VpcInfo.class, responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/vpc/vpcs", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<List<VpcInfo>> queryVpcs(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId);

    @ApiOperation(value = "查询vpc中的子网列表", nickname = "queryVpcsSubnets", notes = "查询vpc中的子网列表",
        response = ListSubnets.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "服务响应体", response = ListSubnets.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/vpc/subnets", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListSubnets> queryVpcsSubnets(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "vpc id", required = true, schema = @Schema())
        @ApiParam(value = "vpc id", required = true) @RequestParam(value = "vpc_id", required = true) String vpcId);

    @ApiOperation(value = "查询环境变量", nickname = "showEnvironmentVariables", notes = "查询环境变量",
        response = EnvironmentVariables.class, tags = {"EnvironmentServiceManager"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "更新环境变量响应体", response = EnvironmentVariables.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = String.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/environments/{environment_id}/variables",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<EnvironmentVariables> showEnvironmentVariables(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "环境ID", required = true, schema = @Schema())
        @PathVariable("environment_id") String environmentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

}
