/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CreateDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateDefaultKnowledgeBaseConnectionResponse;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListDefaultKnowledgeBaseConnectorsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowDefaultKnowledgeBaseConnectionDetailResponseBody;
import com.openjiuwen.studio.agent.manager.dto.TestDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.TestDefaultKnowledgeBaseResponseBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateDefaultKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateDefaultKnowledgeBaseConnectionResponse;

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

@Api(value = "KnowledgeBaseConnectionConfigManagement", description = "the KnowledgeBaseConnectionConfigManagement API")
@Validated

/**
 * KnowledgeBaseConnectionConfigManagementApi interface
 */ public interface KnowledgeBaseConnectionConfigManagementApi {
    @ApiOperation(value = "创建默认知识库配置", nickname = "createDefaultKbConnection", notes = "创建默认知识库配置",
        response = CreateDefaultKnowledgeBaseConnectionResponse.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建默认知识库连接响应体",
            response = CreateDefaultKnowledgeBaseConnectionResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connections",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateDefaultKnowledgeBaseConnectionResponse> createDefaultKbConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "创建默认知识库连接请求体", required = true) @Valid @RequestBody
        CreateDefaultKnowledgeBaseConnectionRequestBody body);

    @ApiOperation(value = "查询默认知识库连接器列表", nickname = "listDefaultKnowledgeBaseConnectors",
        notes = "查询默认知识库连接器", response = ListDefaultKnowledgeBaseConnectorsResponseBody.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库", response = ListDefaultKnowledgeBaseConnectorsResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connectors",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListDefaultKnowledgeBaseConnectorsResponseBody> listDefaultKnowledgeBaseConnectors(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Min(0) @Max(10000)
        @Parameter(in = ParameterIn.QUERY, description = "分页记录的起始位置偏移量,默认值0", required = false, schema = @Schema())
        @ApiParam(value = "分页记录的起始位置偏移量,默认值0", allowableValues = "0, 10000", defaultValue = "0")
        @RequestParam(value = "offset", required = false, defaultValue = "0") Integer offset,
        @Min(1) @Max(1000)
        @Parameter(in = ParameterIn.QUERY, description = "每一页的数量,默认10", required = false, schema = @Schema())
        @ApiParam(value = "每一页的数量,默认10", allowableValues = "1, 1000", defaultValue = "10")
        @RequestParam(value = "limit", required = false, defaultValue = "10") Integer limit);

    @ApiOperation(value = "查询默认知识库连接详情", nickname = "showDefaultKnowledgeBaseConnection",
        notes = "查询默认知识库连接详情", response = ShowDefaultKnowledgeBaseConnectionDetailResponseBody.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库",
            response = ShowDefaultKnowledgeBaseConnectionDetailResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connections/{kb_connection_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShowDefaultKnowledgeBaseConnectionDetailResponseBody> showDefaultKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库连接id", required = true, schema = @Schema())
        @PathVariable("kb_connection_id") String kbConnectionId);

    @ApiOperation(value = "用于测试默认知识库连接是否正常", nickname = "testDefaultKnowledgeBaseConnection",
        notes = "用于测试默认知识库连接是否正常", response = TestDefaultKnowledgeBaseResponseBody.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "测试默认知识库连接响应体",
            response = TestDefaultKnowledgeBaseResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connections/test-connection",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TestDefaultKnowledgeBaseResponseBody> testDefaultKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "测试默认知识库连接请求体", required = true) @Valid @RequestBody
        TestDefaultKnowledgeBaseConnectionRequestBody body);

    @ApiOperation(value = "用于测试默认知识库连接是否正常", nickname = "testDefaultKnowledgeBaseConnectionId",
        notes = "用于测试默认知识库连接是否正常", response = TestDefaultKnowledgeBaseResponseBody.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "测试默认知识库连接响应体",
            response = TestDefaultKnowledgeBaseResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connections/{connection_id}/test-connection",
        produces = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TestDefaultKnowledgeBaseResponseBody> testDefaultKnowledgeBaseConnectionId(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "测试默认知识库连接Id", required = true, schema = @Schema())
        @PathVariable("connection_id") String connectionId);

    @ApiOperation(value = "编辑默认知识库连接", nickname = "updateDefaultKnowledgeBaseConnection",
        notes = "编辑默认知识库连接", response = UpdateDefaultKnowledgeBaseConnectionResponse.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "编辑第三方知识库响应体",
            response = UpdateDefaultKnowledgeBaseConnectionResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connections/{kb_connection_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<UpdateDefaultKnowledgeBaseConnectionResponse> updateDefaultKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "默认知识库连接id", required = true, schema = @Schema())
        @PathVariable("kb_connection_id") String kbConnectionId,
        @NotNull @ApiParam(value = "编辑默认知识库请求体", required = true) @Valid @RequestBody
        UpdateDefaultKnowledgeBaseConnectionRequestBody body);

}
