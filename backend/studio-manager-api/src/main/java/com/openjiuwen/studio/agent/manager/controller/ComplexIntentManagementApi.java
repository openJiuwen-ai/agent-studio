/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchListRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentExportParams;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentListRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListComplexIntentBranchQo;
import com.openjiuwen.studio.agent.manager.dto.ListComplexIntentQo;

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

@Api(value = "ComplexIntentManagement", description = "the ComplexIntentManagement API")
@Validated

/**
 * ComplexIntentManagementApi interface
 */ public interface ComplexIntentManagementApi {
    @ApiOperation(value = "创建一个意图包", nickname = "createComplexIntent", notes = "创建一个意图包",
        response = ComplexIntentBriefRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建意图包响应体", response = ComplexIntentBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ComplexIntentBriefRsp> createComplexIntent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "意图包信息请求体", required = true) @Valid @RequestBody ComplexIntentInfoReq body);

    @ApiOperation(value = "创建一个意图包分支", nickname = "createComplexIntentBranch", notes = "创建一个意图包分支",
        response = ComplexIntentBranchBriefRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建意图包响应体", response = ComplexIntentBranchBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}/branch",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ComplexIntentBranchBriefRsp> createComplexIntentBranch(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "模型id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "意图包信息请求体", required = true) @Valid @RequestBody
        ComplexIntentBranchInfoReq body);

    @ApiOperation(value = "删除一个意图包", nickname = "deleteComplexIntent", notes = "删除一个意图包，不做解绑",
        response = ComplexIntentBriefRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除意图包响应体", response = ComplexIntentBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<ComplexIntentBriefRsp> deleteComplexIntent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "模型id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除一个意图包分支", nickname = "deleteComplexIntentBranch",
        notes = "删除一个意图包分支，不做解绑", response = ComplexIntentBranchBriefRsp.class,
        tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除分支响应体", response = ComplexIntentBranchBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}/branch/{branch_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<ComplexIntentBranchBriefRsp> deleteComplexIntentBranch(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "模型id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "意图包分支id", required = true, schema = @Schema())
        @PathVariable("branch_id") String branchId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "导出高级意图包", nickname = "exportIntent", notes = "导出高级意图包",
        response = Resource.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出Excel", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/export", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportIntent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "导出参数设置", required = true) @Valid @RequestBody ComplexIntentExportParams body);

    @ApiOperation(value = "导出高级意图配置模板", nickname = "exportIntentTemplate", notes = "导出高级意图配置模板",
        response = Resource.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出Excel", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/export-template",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportIntentTemplate(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "导入意图分支", nickname = "importIntent", notes = "导入图分支",
        response = ComplexIntentImportRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入响应体", response = ComplexIntentImportRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/import", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ComplexIntentImportRsp> importIntent(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Pattern(regexp = "^[\\u4e00-\\u9fa5a-zA-Z0-9\\-_]+$") @Size(min = 1, max = 64) @Parameter(in = ParameterIn.QUERY, description = "意图包名称", required = false, schema = @Schema()) @ApiParam(value = "意图包名称")
        @RequestParam(value = "intent_name", required = false) String intentName);

    @ApiOperation(value = "导入意图分支", nickname = "importIntentBranch", notes = "导入图分支",
        response = ComplexIntentImportRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入响应体", response = ComplexIntentImportRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}/branch/import",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ComplexIntentImportRsp> importIntentBranch(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file);

    @ApiOperation(value = "获取意图包列表", nickname = "listComplexIntent", notes = "获取意图包列表",
        response = ComplexIntentListRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = ComplexIntentListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ComplexIntentListRsp> listComplexIntent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListComplexIntentQo: converted from multi query params") @Valid
        ListComplexIntentQo listComplexIntentQo);

    @ApiOperation(value = "获取意图包列表", nickname = "listComplexIntentBranch", notes = "获取意图包列表",
        response = ComplexIntentBranchListRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工具", response = ComplexIntentBranchListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}/branch",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ComplexIntentBranchListRsp> listComplexIntentBranch(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "意图id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId,
        @ApiParam(value = "ListComplexIntentBranchQo: converted from multi query params") @Valid
        ListComplexIntentBranchQo listComplexIntentBranchQo);

    @ApiOperation(value = "修改一个意图包", nickname = "modifyComplexIntent", notes = "修改一个意图包",
        response = ComplexIntentBriefRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改意图包响应体", response = ComplexIntentBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ComplexIntentBriefRsp> modifyComplexIntent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "意图包id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "修改意图包请求体", required = true) @Valid @RequestBody ComplexIntentInfoReq body);

    @ApiOperation(value = "修改一个意图分支", nickname = "modifyComplexIntentBranch", notes = "修改一个意图分支",
        response = ComplexIntentBranchBriefRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改意图包响应体", response = ComplexIntentBranchBriefRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}/branch/{branch_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ComplexIntentBranchBriefRsp> modifyComplexIntentBranch(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "意图包id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "意图包分支id", required = true, schema = @Schema())
        @PathVariable("branch_id") String branchId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "修改意图包请求体", required = true) @Valid @RequestBody
        ComplexIntentBranchInfoReq body);

    @ApiOperation(value = "获取一个意图包", nickname = "retrieveComplexIntent", notes = "获取一个意图包",
        response = ComplexIntentRsp.class, tags = {"ComplexIntentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "意图包信息", response = ComplexIntentRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/complex-intent/{intent_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ComplexIntentRsp> retrieveComplexIntent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "意图包id", required = true, schema = @Schema())
        @PathVariable("intent_id") String intentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

}
