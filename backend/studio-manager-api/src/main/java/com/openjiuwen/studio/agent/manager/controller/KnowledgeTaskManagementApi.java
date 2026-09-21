/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonBatchDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeTaskRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeTaskResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeTaskReq;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeTasksQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeTasksResponseBody;

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

@Api(value = "KnowledgeTaskManagement", description = "the KnowledgeTaskManagement API")
@Validated

/**
 * KnowledgeTaskManagementApi interface
 */ public interface KnowledgeTaskManagementApi {
    @ApiOperation(value = "创建知识库任务", nickname = "createKnowledgeTask",
        notes = "创建知识库任务，包括知识文件重新解析、QA生成", response = CreateKnowledgeTaskResponseBody.class,
        tags = {"KnowledgeTaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建知识库任务响应体", response = CreateKnowledgeTaskResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/tasks",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateKnowledgeTaskResponseBody> createKnowledgeTask(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @ApiParam(value = "创建知识库任务请求体", required = true) @Valid @RequestBody
        CreateKnowledgeTaskRequestBody body);

    @ApiOperation(value = "删除知识库任务", nickname = "deleteKnowledgeTask", notes = "删除知识库任务（单个、批量）",
        response = CommonBatchDeleteRsp.class, tags = {"KnowledgeTaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量删除知识库任务响应体", response = CommonBatchDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/tasks/batch-delete",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CommonBatchDeleteRsp> deleteKnowledgeTask(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @ApiParam(value = "") @Valid @RequestBody(required = false) DeleteKnowledgeTaskReq body);

    @ApiOperation(value = "查询知识库任务", nickname = "listKnowledgeTasks", notes = "查询知识库任务列表",
        response = ListKnowledgeTasksResponseBody.class, tags = {"KnowledgeTaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询知识库任务响应体", response = ListKnowledgeTasksResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/tasks",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeTasksResponseBody> listKnowledgeTasks(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ListKnowledgeTasksQo: converted from multi query params") @Valid
        ListKnowledgeTasksQo listKnowledgeTasksQo);

}
