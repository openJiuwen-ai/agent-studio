/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesRequestBody;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.DownloadFileByAccessKeyQo;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkListRsp;
import com.openjiuwen.studio.agent.manager.dto.FileChunkReq;
import com.openjiuwen.studio.agent.manager.dto.FileInfo;
import com.openjiuwen.studio.agent.manager.dto.ListFileChunksQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeFilesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.RetrieveFileContentQo;
import com.openjiuwen.studio.agent.manager.dto.ShowKnowledgeFileQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileChunkRsp;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileMetaInfoReq;
import com.openjiuwen.studio.agent.manager.dto.UpdateFileMetaInfoRsp;
import com.openjiuwen.studio.agent.manager.dto.UploadKnowledgeFileResponseBody;

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

import org.hibernate.validator.constraints.Length;
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

import java.util.List;

@Api(value = "KnowledgeFileManagement", description = "the KnowledgeFileManagement API")
@Validated

/**
 * KnowledgeFileManagementApi interface
 */ public interface KnowledgeFileManagementApi {
    @ApiOperation(value = "从知识库中批量删除文档", nickname = "batchDeleteKnowledgeFiles",
        notes = "从知识库中批量删除文档", response = BatchDeleteKnowledgeFilesResponseBody.class,
        tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "批量删除文件响应体",
            response = BatchDeleteKnowledgeFilesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/batch-delete",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<BatchDeleteKnowledgeFilesResponseBody> batchDeleteKnowledgeFiles(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "批量删除文件请求体", required = true) @Valid @RequestBody
        BatchDeleteKnowledgeFilesRequestBody body);

    @ApiOperation(value = "新增知识文件的切片", nickname = "createFileChunk", notes = "新增知识文件的切片",
        response = CreateFileChunkRsp.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建知识文档切片响应体", response = CreateFileChunkRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}/chunks",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateFileChunkRsp> createFileChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建知识库切片请求体", required = true) @Valid @RequestBody FileChunkReq body);

    @ApiOperation(value = "从知识库中删除一个文档", nickname = "deleteFile", notes = "从知识库中删除一个文档",
        response = CommonDeleteRsp.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除知识文档响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteFile(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识文档id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除知识文件的切片", nickname = "deleteFileChunk", notes = "删除知识文件的切片",
        response = CommonDeleteRsp.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除知识文档切片响应体", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}/chunks/{chunk_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteFileChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "切片id", required = true, schema = @Schema())
        @PathVariable("chunk_id") String chunkId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "根据AccessKey下载文档", nickname = "downloadFileByAccessKey",
        notes = "根据AccessKey下载文档", response = Resource.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "下载的文档", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/files/{file_id}/content",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Resource> downloadFileByAccessKey(@Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文档id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @ApiParam(value = "DownloadFileByAccessKeyQo: converted from multi query params") @Valid
        DownloadFileByAccessKeyQo downloadFileByAccessKeyQo);

    @ApiOperation(value = "下载的图片", nickname = "downloadKnowledgeImage",
        notes = "下载下载知识库切片和命中测试中的图片", response = Resource.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "下载的图片", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_base_id}/image/{image_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Resource> downloadKnowledgeImage(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "图片id", required = true, schema = @Schema())
        @PathVariable("image_id") String imageId);

    @ApiOperation(value = "通过图片id（accessKey）下载图片", nickname = "downloadKnowledgeImageByAccessKey",
        notes = "通过图片id（accessKey）下载图片", response = Resource.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "图片详情", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/images/{image_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Resource> downloadKnowledgeImageByAccessKey(@Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 100)
        @Parameter(in = ParameterIn.PATH, description = "图片id（accessKey）", required = true, schema = @Schema())
        @PathVariable("image_id") String imageId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = false, schema = @Schema()) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @ApiOperation(value = "获知识文件的切片列表", nickname = "listFileChunks", notes = "获取知识文档的切片列表",
        response = FileChunkListRsp.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文件切片列表", response = FileChunkListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}/chunks",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<FileChunkListRsp> listFileChunks(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId,
        @ApiParam(value = "ListFileChunksQo: converted from multi query params") @Valid
        ListFileChunksQo listFileChunksQo);

    @ApiOperation(value = "获取知识库中的文件列表", nickname = "listKnowledgeFiles", notes = "获取知识库中的文件列表",
        response = ListKnowledgeFilesResponseBody.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库中的文件列表", response = ListKnowledgeFilesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeFilesResponseBody> listKnowledgeFiles(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ListKnowledgeFilesQo: converted from multi query params") @Valid
        ListKnowledgeFilesQo listKnowledgeFilesQo);

    @ApiOperation(value = "从知识库中下载一个文档", nickname = "retrieveFileContent", notes = "从知识库中下载一个文档",
        response = Resource.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "下载的文档", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}/content",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<Resource> retrieveFileContent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文档id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "RetrieveFileContentQo: converted from multi query params") @Valid
        RetrieveFileContentQo retrieveFileContentQo);

    @ApiOperation(value = "获取知识库中的一个文档信息", nickname = "showKnowledgeFile",
        notes = "获取知识库中的一个文档信息", response = FileInfo.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文件信息", response = FileInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<FileInfo> showKnowledgeFile(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识文档id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ShowKnowledgeFileQo: converted from multi query params") @Valid
        ShowKnowledgeFileQo showKnowledgeFileQo);

    @ApiOperation(value = "修改知识文件的切片", nickname = "updateFileChunk", notes = "修改知识文件的切片",
        response = UpdateFileChunkRsp.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改知识库切片响应体", response = UpdateFileChunkRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(
        value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}/chunks/{chunk_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<UpdateFileChunkRsp> updateFileChunk(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "切片id", required = true, schema = @Schema())
        @PathVariable("chunk_id") String chunkId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "修改知识库切片请求体", required = true) @Valid @RequestBody FileChunkReq body);

    @ApiOperation(value = "更新知识库文档的元信息", nickname = "updateFileMetaInfo", notes = "更新知识库文档的元信息",
        response = UpdateFileMetaInfoRsp.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改知识库文档元信息响应体", response = UpdateFileMetaInfoRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files/{file_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<UpdateFileMetaInfoRsp> updateFileMetaInfo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "文件id", required = true, schema = @Schema())
        @PathVariable("file_id") String fileId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "更新文档元信息的请求体", required = true) @Valid @RequestBody
        UpdateFileMetaInfoReq body);

    @ApiOperation(value = "在知识库中上传一个文档", nickname = "uploadKnowledgeFile", notes = "在知识库中上传一个文档",
        response = UploadKnowledgeFileResponseBody.class, tags = {"KnowledgeFileManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文档上传响应体", response = UploadKnowledgeFileResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/files",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<UploadKnowledgeFileResponseBody> uploadKnowledgeFile(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Size(max = 20) @Parameter(in = ParameterIn.QUERY, description = "文档标签列表", required = false, schema = @Schema()) @ApiParam(value = "文档标签列表") @Valid @RequestParam(value = "tags", required = false)
        List<@Length(min = 0, max = 100) String> tags);

}
