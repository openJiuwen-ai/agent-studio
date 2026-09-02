/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeSegmentRuleRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeSegmentRuleResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteOneResponseBody;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeSegmentRulesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeSegmentRuleRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeSegmentRuleResponseBody;

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

@Api(value = "KnowledgeRuleManagement", description = "the KnowledgeRuleManagement API")
@Validated

/**
 * KnowledgeRuleManagementApi interface
 */ public interface KnowledgeRuleManagementApi {
    @ApiOperation(value = "创建一个知识库分层规则", nickname = "createKnowledgeSegmentRule",
        notes = "创建一个知识库分层规则", response = CreateKnowledgeSegmentRuleResponseBody.class,
        tags = {"KnowledgeRuleManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建知识库分层规则响应体",
            response = CreateKnowledgeSegmentRuleResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/rule-regex", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateKnowledgeSegmentRuleResponseBody> createKnowledgeSegmentRule(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "创建知识库分层规则请求体", required = true) @Valid @RequestBody
        CreateKnowledgeSegmentRuleRequestBody body);

    @ApiOperation(value = "删除知识库分层规则", nickname = "deleteKnowledgeSegmentRule", notes = "删除知识库分层规则",
        response = DeleteOneResponseBody.class, tags = {"KnowledgeRuleManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除知识分层规则响应体", response = DeleteOneResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/rule-regex/{id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<DeleteOneResponseBody> deleteKnowledgeSegmentRule(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识分层规则id", required = true, schema = @Schema())
        @PathVariable("id") String id, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询知识库分层规则列表", nickname = "listKnowledgeSegmentRules",
        notes = "查询知识库分层规则列表", response = ListKnowledgeSegmentRulesResponseBody.class,
        tags = {"KnowledgeRuleManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库分层规则列表响应体",
            response = ListKnowledgeSegmentRulesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/rule-regex", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeSegmentRulesResponseBody> listKnowledgeSegmentRules(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Size(min = 1, max = 100)
        @Parameter(in = ParameterIn.QUERY, description = "知识库id", required = false, schema = @Schema())
        @ApiParam(value = "知识库id") @RequestParam(value = "repo_id", required = false)
        String repoId);

    @ApiOperation(value = "修改一个知识库分层规则", nickname = "modifyKnowledgeSegmentRule",
        notes = "修改一个知识库分层规则", response = ModifyKnowledgeSegmentRuleResponseBody.class,
        tags = {"KnowledgeRuleManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改知识库分层规则响应体",
            response = ModifyKnowledgeSegmentRuleResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/rule-regex/{id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ModifyKnowledgeSegmentRuleResponseBody> modifyKnowledgeSegmentRule(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "分层规则id", required = true, schema = @Schema())
        @PathVariable("id") String id,
        @NotNull @ApiParam(value = "修改知识库分层规则请求体", required = true) @Valid @RequestBody
        ModifyKnowledgeSegmentRuleRequestBody body);

}
