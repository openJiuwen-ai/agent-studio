/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.BatchDeleteFaqReq;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteFaqResp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateFaqReq;
import com.openjiuwen.studio.agent.manager.dto.CreateFaqResp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListFaqQo;
import com.openjiuwen.studio.agent.manager.dto.ListFaqResp;
import com.openjiuwen.studio.agent.manager.dto.ModifyFaqReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyFaqResp;

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

@Api(value = "KnowledgeFaqManagement", description = "the KnowledgeFaqManagement API")
@Validated

/**
 * KnowledgeFaqManagementApi interface
 */ public interface KnowledgeFaqManagementApi {
    @ApiOperation(value = "批量删除FAQ问答对", nickname = "batchDeleteFaq", notes = "批量删除FAQ问答对",
        response = BatchDeleteFaqResp.class, tags = {"KnowledgeFaqManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量删除Faq响应体", response = BatchDeleteFaqResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq/batch-delete",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BatchDeleteFaqResp> batchDeleteFaq(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "批量删除Faq请求体", required = true) @Valid @RequestBody BatchDeleteFaqReq body);

    @ApiOperation(value = "创建一个FAQ问答对", nickname = "createFaq", notes = "创建一个FAQ问答对",
        response = CreateFaqResp.class, tags = {"KnowledgeFaqManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建FAQ问答对响应体", response = CreateFaqResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateFaqResp> createFaq(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @ApiParam(value = "创建FAQ问答对请求体", required = true) @Valid @RequestBody CreateFaqReq body);

    @ApiOperation(value = "删除一个FAQ问答对", nickname = "deleteFaq", notes = "删除一个FAQ问答对",
        response = CommonDeleteRsp.class, tags = {"KnowledgeFaqManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除FAQ响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq/{faq_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteFaq(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "FAQ id", required = true, schema = @Schema())
        @PathVariable("faq_id") String faqId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询FAQ问答对列表", nickname = "listFaq", notes = "查询FAQ问答对列表",
        response = ListFaqResp.class, tags = {"KnowledgeFaqManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询FAQ问答对列表响应体", response = ListFaqResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListFaqResp> listFaq(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ListFaqQo: converted from multi query params") @Valid ListFaqQo listFaqQo);

    @ApiOperation(value = "修改一个FAQ问答对", nickname = "modifyFaq", notes = "修改一个FAQ问答对",
        response = ModifyFaqResp.class, tags = {"KnowledgeFaqManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改FAQ问答对响应体", response = ModifyFaqResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq/{faq_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ModifyFaqResp> modifyFaq(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "FAQ id", required = true, schema = @Schema())
        @PathVariable("faq_id") String faqId,
        @NotNull @ApiParam(value = "修改FAQ问答对请求体", required = true) @Valid @RequestBody ModifyFaqReq body);

}
