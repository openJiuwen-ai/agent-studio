/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateThirdPartyKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateThirdPartyKnowledgeBaseConnectionResponse;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListThirdPartyKnowledgeBaseConnectionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListThirdPartyKnowledgeBaseConnectionsResponse;
import com.openjiuwen.studio.agent.manager.dto.ListThirdPartyKnowledgeBaseConnectorsQo;
import com.openjiuwen.studio.agent.manager.dto.ListThirdPartyKnowledgeBaseConnectorsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowKnowledgeBaseConnectorAbilitiesQo;
import com.openjiuwen.studio.agent.manager.dto.ShowKnowledgeBaseConnectorAbilitiesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody;
import com.openjiuwen.studio.agent.manager.dto.TestConnectionThirdPartyKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.TestConnectionThirdPartyKnowledgeBaseResponseBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateThirdPartyKnowledgeBaseConnectionRequestBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateThirdPartyKnowledgeBaseConnectionResponse;

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

@Api(value = "ThirdPartyKnowledgeBaseConnectionManagement",
    description = "the ThirdPartyKnowledgeBaseConnectionManagement API")
@Validated

/**
 * ThirdPartyKnowledgeBaseConnectionManagementApi interface
 */ public interface ThirdPartyKnowledgeBaseConnectionManagementApi {
    @ApiOperation(value = "创建第三方知识库连接", nickname = "createThirdPartyKnowledgeBaseConnection",
        notes = "创建第三方知识库连接", response = CreateThirdPartyKnowledgeBaseConnectionResponse.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建第三方知识库连接响应体",
            response = CreateThirdPartyKnowledgeBaseConnectionResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateThirdPartyKnowledgeBaseConnectionResponse> createThirdPartyKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建第三方知识库连接请求体", required = true) @Valid @RequestBody
        CreateThirdPartyKnowledgeBaseConnectionRequestBody body);

    @ApiOperation(value = "删除第三方知识库连接", nickname = "deleteThirdPartyKnowledgeBaseConnection",
        notes = "删除第三方知识库连接", response = CommonDeleteRsp.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除第三方知识库连接响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections/{knowledge_base_connection_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteThirdPartyKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "第三方知识库连接id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_connection_id") String knowledgeBaseConnectionId);

    @ApiOperation(value = "查询第三方知识库连接列表", nickname = "listThirdPartyKnowledgeBaseConnections",
        notes = "查询第三方知识库连接列表", response = ListThirdPartyKnowledgeBaseConnectionsResponse.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "successful operation",
            response = ListThirdPartyKnowledgeBaseConnectionsResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListThirdPartyKnowledgeBaseConnectionsResponse> listThirdPartyKnowledgeBaseConnections(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListThirdPartyKnowledgeBaseConnectionsQo: converted from multi query params") @Valid
        ListThirdPartyKnowledgeBaseConnectionsQo listThirdPartyKnowledgeBaseConnectionsQo);

    @ApiOperation(value = "查询第三方知识库连接器列表", nickname = "listThirdPartyKnowledgeBaseConnectors",
        notes = "查询第三方知识库连接器列表", response = ListThirdPartyKnowledgeBaseConnectorsResponseBody.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库",
            response = ListThirdPartyKnowledgeBaseConnectorsResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connectors",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListThirdPartyKnowledgeBaseConnectorsResponseBody> listThirdPartyKnowledgeBaseConnectors(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListThirdPartyKnowledgeBaseConnectorsQo: converted from multi query params") @Valid
        ListThirdPartyKnowledgeBaseConnectorsQo listThirdPartyKnowledgeBaseConnectorsQo);

    @ApiOperation(value = "查询知识库连接器支持的能力", nickname = "showKnowledgeBaseConnectorAbilities",
        notes = "查询知识库连接器支持的能力", response = ShowKnowledgeBaseConnectorAbilitiesResponseBody.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "检索配置响应体",
            response = ShowKnowledgeBaseConnectorAbilitiesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/connectors/abilities",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShowKnowledgeBaseConnectorAbilitiesResponseBody> showKnowledgeBaseConnectorAbilities(
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ShowKnowledgeBaseConnectorAbilitiesQo: converted from multi query params") @Valid
        ShowKnowledgeBaseConnectorAbilitiesQo showKnowledgeBaseConnectorAbilitiesQo);

    @ApiOperation(value = "查询第三方知识库连接详情", nickname = "showThirdPartyKnowledgeBaseConnection",
        notes = "查询第三方知识库连接详情", response = ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库",
            response = ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections/{knowledge_base_connection_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShowThirdPartyKnowledgeBaseConnectionDetailResponseBody> showThirdPartyKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "第三方知识库连接id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_connection_id") String knowledgeBaseConnectionId);

    @ApiOperation(value = "用于测试第三方知识库连接是否正常",
        nickname = "testConnectionThirdPartyKnowledgeBaseConnection", notes = "用于测试第三方知识库连接是否正常",
        response = TestConnectionThirdPartyKnowledgeBaseResponseBody.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "测试第三方知识库连接响应体",
            response = TestConnectionThirdPartyKnowledgeBaseResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections/test-connection",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TestConnectionThirdPartyKnowledgeBaseResponseBody> testConnectionThirdPartyKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "测试第三方知识库连接请求体", required = true) @Valid @RequestBody
        TestConnectionThirdPartyKnowledgeBaseConnectionRequestBody body);

    @ApiOperation(value = "测试指定第三方知识库连接是否正常",
        nickname = "testConnectionThirdPartyKnowledgeBaseConnectionById", notes = "测试指定第三方知识库连接是否正常",
        response = TestConnectionThirdPartyKnowledgeBaseResponseBody.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "测试连接第三方知识库响应体",
            response = TestConnectionThirdPartyKnowledgeBaseResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections/{knowledge_base_connection_id}/test-connection",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<TestConnectionThirdPartyKnowledgeBaseResponseBody> testConnectionThirdPartyKnowledgeBaseConnectionById(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "知识库连接id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_connection_id") String knowledgeBaseConnectionId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "编辑第三方知识库连接", nickname = "updateThirdPartyKnowledgeBaseConnection",
        notes = "编辑第三方知识库连接（展示名称、描述）", response = UpdateThirdPartyKnowledgeBaseConnectionResponse.class,
        tags = {"ThirdPartyKnowledgeBaseConnectionManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "编辑第三方知识库响应体",
            response = UpdateThirdPartyKnowledgeBaseConnectionResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/third-party/knowledge-bases/connections/{knowledge_base_connection_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<UpdateThirdPartyKnowledgeBaseConnectionResponse> updateThirdPartyKnowledgeBaseConnection(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull
        @Parameter(in = ParameterIn.QUERY, description = "", required = true, schema = @Schema())
        @ApiParam(value = "", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "第三方知识库连接id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_connection_id") String knowledgeBaseConnectionId,
        @NotNull @ApiParam(value = "编辑第三方知识库请求体", required = true) @Valid @RequestBody
        UpdateThirdPartyKnowledgeBaseConnectionRequestBody body);

}
