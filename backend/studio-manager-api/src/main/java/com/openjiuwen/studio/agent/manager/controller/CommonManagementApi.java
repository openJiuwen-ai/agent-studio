/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.manager.dto.TagInfo;

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
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@Api(value = "CommonManagement", description = "the CommonManagement API")
@Validated

/**
 * CommonManagementApi interface
 */ public interface CommonManagementApi {
    @ApiOperation(value = "获取标签列表", nickname = "listTags", notes = "获取标签列表。", response = TagInfo.class,
        responseContainer = "List", tags = {"CommonManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "搜索的标签列表。", response = TagInfo.class, responseContainer = "List"),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tags", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<List<TagInfo>> listTags(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间ID。", required = true, schema = @Schema())
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取系统参数", nickname = "systemSettings", notes = "获取系统参数。", response = Object.class,
        tags = {"CommonManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "系统配置。", response = Object.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/system/settings", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Object> systemSettings(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @NotNull @Size(max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "服务名。", required = true, schema = @Schema())
    @ApiParam(value = "服务名。", required = true)
    @RequestParam(value = "service", required = true) String service);

    @ApiOperation(value = "上传头像", nickname = "uploadAvatar",
        notes = "创建应用/工作流/插件/MCP/知识库前，上传对应资源的头像。", response = FileUploadRsp.class,
        tags = {"CommonManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "agent文件上传响应体。", response = FileUploadRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/upload-avatar", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<FileUploadRsp> uploadAvatar(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file);

}
