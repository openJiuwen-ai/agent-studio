/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteMemoryItemRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryItemResponseBody;
import com.openjiuwen.studio.agent.manager.dto.SearchMemoryItemRequestBody;

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

@Api(value = "MemoryItemManagement", description = "the MemoryItemManagement API")
@Validated
public interface MemoryItemManagementApi {

    @ApiOperation(value = "查询记忆条目列表", nickname = "listMemoryItems",
        notes = "查询指定记忆库下的记忆条目列表", response = ListMemoryItemResponseBody.class,
        tags = {"MemoryItemManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "记忆条目列表", response = ListMemoryItemResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-repositories/{memory_repo_id}/memories",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListMemoryItemResponseBody> listMemoryItems(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "记忆库id", required = true, schema = @Schema())
        @PathVariable("memory_repo_id") String memoryRepoId,
        @Parameter(in = ParameterIn.QUERY, description = "页码", required = false, schema = @Schema())
        @ApiParam(value = "页码") @RequestParam(value = "page_num", defaultValue = "1") Integer pageNum,
        @Parameter(in = ParameterIn.QUERY, description = "每页条数", required = false, schema = @Schema())
        @ApiParam(value = "每页条数") @RequestParam(value = "page_size", defaultValue = "10") Integer pageSize);

    @ApiOperation(value = "删除单条记忆", nickname = "deleteMemoryItem",
        notes = "删除指定记忆库下的单条记忆条目", tags = {"MemoryItemManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-repositories/{memory_repo_id}/memories/{memory_id}",
        method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteMemoryItem(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "记忆库id", required = true, schema = @Schema())
        @PathVariable("memory_repo_id") String memoryRepoId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "记忆条目id", required = true, schema = @Schema())
        @PathVariable("memory_id") String memoryId);

    @ApiOperation(value = "批量删除记忆条目", nickname = "batchDeleteMemoryItems",
        notes = "批量删除指定记忆库下的记忆条目", tags = {"MemoryItemManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-repositories/{memory_repo_id}/memories/batch-delete",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Void> batchDeleteMemoryItems(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "记忆库id", required = true, schema = @Schema())
        @PathVariable("memory_repo_id") String memoryRepoId,
        @NotNull @ApiParam(value = "批量删除请求体", required = true) @Valid @RequestBody
        BatchDeleteMemoryItemRequestBody body);

    @ApiOperation(value = "搜索记忆条目", nickname = "searchMemoryItems",
        notes = "在指定记忆库下语义搜索记忆条目", tags = {"MemoryItemManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "搜索结果"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/memory-repositories/{memory_repo_id}/memories/search",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<ListMemoryItemResponseBody> searchMemoryItems(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "记忆库id", required = true, schema = @Schema())
        @PathVariable("memory_repo_id") String memoryRepoId,
        @NotNull @ApiParam(value = "搜索请求体", required = true) @Valid @RequestBody
        SearchMemoryItemRequestBody body);
}
