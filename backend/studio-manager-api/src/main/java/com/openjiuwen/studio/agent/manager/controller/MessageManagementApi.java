/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.BatchDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportMessagesParams;
import com.openjiuwen.studio.agent.manager.dto.ListStructuredMessagesQo;
import com.openjiuwen.studio.agent.manager.dto.StructMessage;
import com.openjiuwen.studio.agent.manager.dto.StructMessageListRsp;
import com.openjiuwen.studio.agent.manager.dto.StructuredInfoRequest;
import com.openjiuwen.studio.agent.manager.dto.StructuredInfoRequestDelete;
import com.openjiuwen.studio.agent.manager.dto.StructuredMessagesUploadResult;

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

@Api(value = "MessageManagement", description = "the MessageManagement API")
@Validated

/**
 * MessageManagementApi interface
 */ public interface MessageManagementApi {
    @ApiOperation(value = "添加结构化信息", nickname = "createStructuredMessages", notes = "添加结构化信息",
        response = StructMessage.class, tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "返回的结构化信息", response = StructMessage.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<StructMessage> createStructuredMessages(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "结构化信息参数设置", required = true) @Valid @RequestBody
        StructuredInfoRequest body);

    @ApiOperation(value = "批量删除结构化信息", nickname = "deleteStructuredMessages",
        notes = "根据提供的信息ID列表批量删除结构化信息", response = BatchDeleteRsp.class,
        tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量删除操作结果", response = BatchDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求参数错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 资源不存在", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<BatchDeleteRsp> deleteStructuredMessages(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "结构化信息删除请求参数", required = true) @Valid @RequestBody
        List<StructuredInfoRequestDelete> body);

    @ApiOperation(value = "导出消息模板", nickname = "exportStructuredMessages", notes = "上传消息模板",
        response = Resource.class, tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出文档", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages/export-file",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportStructuredMessages(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "导出参数设置", required = true) @Valid @RequestBody ExportMessagesParams body);

    @ApiOperation(value = "结构化信息模板", nickname = "exportStructuredTemplate", notes = "结构化信息模板获取",
        response = Resource.class, tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出Excel", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages/export-template",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportStructuredTemplate(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询结构化信息列表", nickname = "listStructuredMessages",
        notes = "查询当前项目空间下的所有结构化信息", response = StructMessageListRsp.class,
        tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "结构化信息列表", response = StructMessageListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<StructMessageListRsp> listStructuredMessages(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListStructuredMessagesQo: converted from multi query params") @Valid
        ListStructuredMessagesQo listStructuredMessagesQo);

    @ApiOperation(value = "修改结构化信息", nickname = "updateStructuredMessages", notes = "修改指定ID的结构化信息",
        response = StructMessage.class, tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "更新成功的结构化信息", response = StructMessage.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到指定资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<StructMessage> updateStructuredMessages(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "结构化信息更新参数", required = true) @Valid @RequestBody
        StructuredInfoRequest body);

    @ApiOperation(value = "上传消息模板", nickname = "uploadStructuredMessages", notes = "上传消息模板",
        response = StructuredMessagesUploadResult.class, tags = {"MessageManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "结构化信息列表", response = StructuredMessagesUploadResult.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/structured-messages/upload-file",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<StructuredMessagesUploadResult> uploadStructuredMessages(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file);

}
