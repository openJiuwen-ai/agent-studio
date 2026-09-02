/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.DownloadFaqFileByAccessKeyQo;
import com.openjiuwen.studio.agent.manager.dto.DownloadFaqFileQo;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FaqFileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FaqFileInfoListRsp;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFileChunksQo;
import com.openjiuwen.studio.agent.manager.dto.ListFaqFilesQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.UploadFaqFileRsp;

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

@Api(value = "KnowledgeFaqFileManagement", description = "the KnowledgeFaqFileManagement API")
@Validated

/**
 * KnowledgeFaqFileManagementApi interface
 */ public interface KnowledgeFaqFileManagementApi {
    @ApiOperation(value = "新增知识FAQ文件的切片", nickname = "createFaqFileChunk", notes = "新增知识FAQ文件的切片",
        response = CreateFileChunkRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建文件切片响应体", response = CreateFileChunkRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files/{file_id}/chunks",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateFileChunkRsp> createFaqFileChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
    @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
    @PathVariable("file_id") String fileId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
    @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId, @NotNull @ApiParam(value = "创建知识库FAQ切片请求体", required = true) @Valid @RequestBody
    FaqFileChunkReq body);

    @ApiOperation(value = "删除知识FAQ文件", nickname = "deleteFaqFile", notes = "删除知识FAQ文件",
        response = CommonDeleteRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除FAQ文档响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files/{file_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteFaqFile(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
    @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
    @PathVariable("file_id") String fileId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
    @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "删除知识FAQ文件的切片", nickname = "deleteFaqFileChunk", notes = "删除知识文件的切片",
        response = CommonDeleteRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除FAQ切片响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files/{file_id}/chunks/{chunk_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteFaqFileChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "切片id", required = true, schema = @Schema())
        @PathVariable("chunk_id") String chunkId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "从知识库中下载一个faq文档", nickname = "downloadFaqFile",
        notes = "从知识库中下载一个faq文档", response = Resource.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "下载的文档", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files/{file_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Resource> downloadFaqFile(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文档id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId,
        @ApiParam(value = "DownloadFaqFileQo: converted from multi query params") @Valid
        DownloadFaqFileQo downloadFaqFileQo);

    @ApiOperation(value = "根据AccessKey下载faq文档", nickname = "downloadFaqFileByAccessKey",
        notes = "根据AccessKey下载faq文档", response = Resource.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "下载的文档", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/faq-files/{file_id}/content",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Resource> downloadFaqFileByAccessKey(@Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文档id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @ApiParam(value = "DownloadFaqFileByAccessKeyQo: converted from multi query params") @Valid
        DownloadFaqFileByAccessKeyQo downloadFaqFileByAccessKeyQo);

    @ApiOperation(value = "获知识FAQ文件的切片列表", nickname = "listFaqFileChunks", notes = "获知识FAQ文件的切片列表",
        response = FaqFileChunkListRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文件切片列表", response = FaqFileChunkListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files/{file_id}/chunks",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<FaqFileChunkListRsp> listFaqFileChunks(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId,
        @ApiParam(value = "ListFaqFileChunksQo: converted from multi query params") @Valid
        ListFaqFileChunksQo listFaqFileChunksQo);

    @ApiOperation(value = "获取知识库中的faq文件列表", nickname = "listFaqFiles", notes = "获取知识库中的faq文件列表",
        response = FaqFileInfoListRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库中的Faq文件列表", response = FaqFileInfoListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<FaqFileInfoListRsp> listFaqFiles(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ListFaqFilesQo: converted from multi query params") @Valid ListFaqFilesQo listFaqFilesQo);

    @ApiOperation(value = "修改知识FAQ文件的切片", nickname = "updateFaqFileChunk", notes = "修改知识FAQ文件的切片",
        response = UpdateFileChunkRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改知识库切片响应体", response = UpdateFileChunkRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files/{file_id}/chunks/{chunk_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<UpdateFileChunkRsp> updateFaqFileChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "切片id", required = true, schema = @Schema())
        @PathVariable("chunk_id") String chunkId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "修改知识库切片请求体", required = true) @Valid @RequestBody FaqFileChunkReq body);

    @ApiOperation(value = "在知识库中上传一个faq文档", nickname = "uploadFaqFile", notes = "在知识库中上传一个faq文档",
        response = UploadFaqFileRsp.class, tags = {"KnowledgeFaqFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文档上传响应体", response = UploadFaqFileRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/faq-files",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<UploadFaqFileRsp> uploadFaqFile(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema())
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file);

}
