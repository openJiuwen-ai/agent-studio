/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBaseConfigsResponse;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.annotations.ApiResponse;
import io.swagger.annotations.ApiResponses;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

@Api(value = "KnowledgeBaseConfigManagement", description = "the KnowledgeBaseConfigManagement API")
@Validated

/**
 * KnowledgeBaseConfigManagementApi interface
 */ public interface KnowledgeBaseConfigManagementApi {
    @ApiOperation(value = "查询知识库配置", nickname = "listKnowledgeBaseConfigs", notes = "查询知识库配置",
        response = ListKnowledgeBaseConfigsResponse.class, tags = {"KnowledgeBaseConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询知识库配置响应体", response = ListKnowledgeBaseConfigsResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/configs", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeBaseConfigsResponse> listKnowledgeBaseConfigs(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "知识库id", required = false, schema = @Schema())
        @ApiParam(value = "知识库id")
        @RequestParam(value = "knowledge_base_id", required = false) String knowledgeBaseId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "空间id", required = false, schema = @Schema())
        @ApiParam(value = "空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

}
