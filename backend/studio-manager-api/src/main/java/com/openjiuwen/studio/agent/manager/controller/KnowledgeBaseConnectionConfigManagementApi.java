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
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
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
        @ApiResponse(responseCode = "200", description = "创建默认知识库连接响应体",
            content = @Content(schema = @Schema(implementation = CreateDefaultKnowledgeBaseConnectionResponse.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request 请求错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized 鉴权失败",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden 没有操作权限",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "404", description = "Not Found 找不到资源",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "500", description = "Internal Server Error 服务内部错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class)))
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
        @ApiResponse(responseCode = "200", description = "知识库",
            content = @Content(schema = @Schema(implementation = ListDefaultKnowledgeBaseConnectorsResponseBody.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request 请求错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized 鉴权失败",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden 没有操作权限",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "404", description = "Not Found 找不到资源",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "500", description = "Internal Server Error 服务内部错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class)))
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
        notes = "查询当前环境配置的默认知识库连接：kb_connection_id 为固定占位值（default_lakesearch_inside_connection_id），"
            + "返回环境支持（按连接器类型配置）的第一个已配置默认连接；未配置时 knowledge_base_connection_detail 为 null，表示默认连接未配置",
        response = ShowDefaultKnowledgeBaseConnectionDetailResponseBody.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "知识库",
            content = @Content(schema = @Schema(implementation = ShowDefaultKnowledgeBaseConnectionDetailResponseBody.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request 请求错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized 鉴权失败",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden 没有操作权限",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "404", description = "Not Found 找不到资源",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "500", description = "Internal Server Error 服务内部错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class)))
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/configurations/default-connections/{kb_connection_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShowDefaultKnowledgeBaseConnectionDetailResponseBody> showDefaultKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,         @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库连接id（固定占位值：default_lakesearch_inside_connection_id）", required = true, schema = @Schema())
        @PathVariable("kb_connection_id") String kbConnectionId);

    @ApiOperation(value = "用于测试默认知识库连接是否正常", nickname = "testDefaultKnowledgeBaseConnection",
        notes = "用于测试默认知识库连接是否正常", response = TestDefaultKnowledgeBaseResponseBody.class,
        tags = {"KnowledgeBaseConnectionConfigManagement"})
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "测试默认知识库连接响应体",
            content = @Content(schema = @Schema(implementation = TestDefaultKnowledgeBaseResponseBody.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request 请求错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized 鉴权失败",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden 没有操作权限",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "404", description = "Not Found 找不到资源",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "500", description = "Internal Server Error 服务内部错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class)))
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
        @ApiResponse(responseCode = "200", description = "测试默认知识库连接响应体",
            content = @Content(schema = @Schema(implementation = TestDefaultKnowledgeBaseResponseBody.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request 请求错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized 鉴权失败",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden 没有操作权限",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "404", description = "Not Found 找不到资源",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "500", description = "Internal Server Error 服务内部错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class)))
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
        @ApiResponse(responseCode = "200", description = "编辑第三方知识库响应体",
            content = @Content(schema = @Schema(implementation = UpdateDefaultKnowledgeBaseConnectionResponse.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request 请求错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized 鉴权失败",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden 没有操作权限",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "404", description = "Not Found 找不到资源",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class))),
        @ApiResponse(responseCode = "500", description = "Internal Server Error 服务内部错误",
            content = @Content(schema = @Schema(implementation = ErrorRsp.class)))
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
