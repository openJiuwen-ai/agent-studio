/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateExternalKnowledgeBaseRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateExternalKnowledgeBaseResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.CreateKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteKnowledgeRepoTagsRsp;
import com.openjiuwen.studio.agent.manager.dto.DeleteOneResponseBody;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeSearchRecordRsp;
import com.openjiuwen.studio.agent.manager.dto.ListExternalKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListExternalKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeModelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeModelsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeRepoTagsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeSearchRecordsQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeTagsResp;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.PermissionsRequestBody;
import com.openjiuwen.studio.agent.manager.dto.SearchKnowledgeRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.SearchKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.StartKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.StopKnowledgeRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.UpdateKnowledgeVisibilityResponse;

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

@Api(value = "KnowledgeRepoManagement", description = "the KnowledgeRepoManagement API")
@Validated

/**
 * KnowledgeRepoManagementApi interface
 */ public interface KnowledgeRepoManagementApi {
    @ApiOperation(value = "新增第三方知识库", nickname = "createExternalKnowledgeBase",
        notes = "从第三方知识库中接入知识库到agent-base中，支持一次接入多个第三方知识库",
        response = CreateExternalKnowledgeBaseResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询第三方知识库列表响应体",
            response = CreateExternalKnowledgeBaseResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/external", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateExternalKnowledgeBaseResponseBody> createExternalKnowledgeBase(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Size(max = 100) @Parameter(in = ParameterIn.QUERY, description = "空间ID", required = true, schema = @Schema()) @ApiParam(value = "空间ID", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody
        CreateExternalKnowledgeBaseRequestBody body);

    @ApiOperation(value = "创建一个知识库", nickname = "createKnowledgeRepo", notes = "创建一个知识库",
        response = CreateKnowledgeRepoResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建知识库响应体", response = CreateKnowledgeRepoResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateKnowledgeRepoResponseBody> createKnowledgeRepo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "创建知识库请求体", required = true) @Valid @RequestBody
        CreateKnowledgeRepoRequestBody body);

    @ApiOperation(value = "在知识库创建文档标签", nickname = "createKnowledgeRepoTags", notes = "在知识库创建文档标签",
        response = CreateKnowledgeRepoTagsRsp.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建知识库文档标签成功", response = CreateKnowledgeRepoTagsRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/tags",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreateKnowledgeRepoTagsRsp> createKnowledgeRepoTags(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @ApiParam(value = "知识库创建文档标签请求体", required = true) @Valid @RequestBody
        CreateKnowledgeRepoTagsReq body);

    @ApiOperation(value = "删除一个知识库", nickname = "deleteKnowledgeRepo",
        notes = "删除一个知识库（需要知识库是停用状态）", response = DeleteOneResponseBody.class,
        tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除知识库响应体", response = DeleteOneResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<DeleteOneResponseBody> deleteKnowledgeRepo(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除知识库下的文档标签", nickname = "deleteKnowledgeRepoTags",
        notes = "删除知识库下的文档标签", response = DeleteKnowledgeRepoTagsRsp.class,
        tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库文档标签列表", response = DeleteKnowledgeRepoTagsRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/tags/{tag_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<DeleteKnowledgeRepoTagsRsp> deleteKnowledgeRepoTags(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "标签id", required = true, schema = @Schema())
        @PathVariable("tag_id") String tagId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody DeleteKnowledgeRepoTagsReq body);

    @ApiOperation(value = "删除知识库测试记录", nickname = "deleteKnowledgeSearchRecord", notes = "删除知识库测试记录",
        response = CommonDeleteRsp.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/search-records/{record_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteKnowledgeSearchRecord(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "命中测试记录id", required = true, schema = @Schema())
        @PathVariable("record_id") String recordId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询第三方知识库列表", nickname = "listExternalKnowledgeBases",
        notes = "根据接入知识库查询第三方知识库列表", response = ListExternalKnowledgeBasesResponseBody.class,
        tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询第三方知识库列表响应体",
            response = ListExternalKnowledgeBasesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/external", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListExternalKnowledgeBasesResponseBody> listExternalKnowledgeBases(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListExternalKnowledgeBasesQo: converted from multi query params") @Valid
        ListExternalKnowledgeBasesQo listExternalKnowledgeBasesQo);

    @ApiOperation(value = "获取知识库列表", nickname = "listKnowledgeBases", notes = "获取知识库列表",
        response = ListKnowledgeBasesResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库列表", response = ListKnowledgeBasesResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeBasesResponseBody> listKnowledgeBases(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListKnowledgeBasesQo: converted from multi query params") @Valid
        ListKnowledgeBasesQo listKnowledgeBasesQo);

    @ApiOperation(value = "查询知识库使用的模型列表", nickname = "listKnowledgeModels",
        notes = "查询知识库使用的模型列表", response = ListKnowledgeModelsResponseBody.class,
        tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询模型列表响应体", response = ListKnowledgeModelsResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/models", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeModelsResponseBody> listKnowledgeModels(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListKnowledgeModelsQo: converted from multi query params") @Valid
        ListKnowledgeModelsQo listKnowledgeModelsQo);

    @ApiOperation(value = "获取知识库标签列表", nickname = "listKnowledgeRepoTags", notes = "获取知识库标签列表",
        response = ListKnowledgeTagsResp.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库标签列表", response = ListKnowledgeTagsResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/tags",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ListKnowledgeTagsResp> listKnowledgeRepoTags(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ListKnowledgeRepoTagsQo: converted from multi query params") @Valid
        ListKnowledgeRepoTagsQo listKnowledgeRepoTagsQo);

    @ApiOperation(value = "查询知识检索测试记录", nickname = "listKnowledgeSearchRecords",
        notes = "查询知识检索测试记录", response = KnowledgeSearchRecordRsp.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识检索测试记录", response = KnowledgeSearchRecordRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/search-records",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<KnowledgeSearchRecordRsp> listKnowledgeSearchRecords(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @ApiParam(value = "ListKnowledgeSearchRecordsQo: converted from multi query params") @Valid
        ListKnowledgeSearchRecordsQo listKnowledgeSearchRecordsQo);

    @ApiOperation(value = "修改知识库可见性", nickname = "modifyKnowledgeBaseVisibility",
        notes = "修改知识库可见性（共享范围：GLOBAL：全空间; SELF：本空间）",
        response = UpdateKnowledgeVisibilityResponse.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改知识库可见性响应", response = UpdateKnowledgeVisibilityResponse.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v2/{project_id}/agent-manager/knowledge-bases/{knowledge_base_id}/permissions",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<UpdateKnowledgeVisibilityResponse> modifyKnowledgeBaseVisibility(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_base_id") String knowledgeBaseId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = false, schema = @Schema()) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "可见范围", required = true) @Valid @RequestBody PermissionsRequestBody body);

    @ApiOperation(value = "修改一个知识库", nickname = "modifyKnowledgeRepo",
        notes = "修改一个知识库，包括：展示名称、描述、高级设置", response = ModifyKnowledgeRepoResponseBody.class,
        tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改知识库响应体", response = ModifyKnowledgeRepoResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<ModifyKnowledgeRepoResponseBody> modifyKnowledgeRepo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "修改知识库请求体", required = true) @Valid @RequestBody
        ModifyKnowledgeRepoRequestBody body);

    @ApiOperation(value = "检索知识库，命中测试", nickname = "searchKnowledgeRepo", notes = "检索知识库，命中测试",
        response = SearchKnowledgeRepoResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库检索响应体", response = SearchKnowledgeRepoResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/search-text", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<SearchKnowledgeRepoResponseBody> searchKnowledgeRepo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @Min(0) @Max(10000) @Parameter(in = ParameterIn.QUERY, description = "分页记录的起始位置偏移量，默认值0", required = false, schema = @Schema()) @ApiParam(value = "分页记录的起始位置偏移量，默认值0", allowableValues = "10000, 0")
        @RequestParam(value = "offset", required = false) Integer offset,
        @Min(1) @Max(1000) @Parameter(in = ParameterIn.QUERY, description = "每一页的数量，默认值10", required = false, schema = @Schema()) @ApiParam(value = "每一页的数量，默认值10", allowableValues = "1000, 1", defaultValue = "10")
        @RequestParam(value = "limit", required = false, defaultValue = "10") Integer limit,
        @NotNull @ApiParam(value = "知识库检索请求体", required = true) @Valid @RequestBody
        SearchKnowledgeRepoRequestBody body);

    @ApiOperation(value = "查询一个知识库详情", nickname = "showKnowledgeRepo", notes = "查询一个知识库详情",
        response = ShowKnowledgeRepoResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "知识库", response = ShowKnowledgeRepoResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ShowKnowledgeRepoResponseBody> showKnowledgeRepo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "开启一个知识库", nickname = "startKnowledgeRepo", notes = "开启一个知识库",
        response = StartKnowledgeRepoResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "启用知识库响应体", response = StartKnowledgeRepoResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/start",
        produces = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<StartKnowledgeRepoResponseBody> startKnowledgeRepo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "停用一个知识库", nickname = "stopKnowledgeRepo",
        notes = "停用一个知识库，停用后的知识库无法再被智能体关联，已关联的检索结果为空",
        response = StopKnowledgeRepoResponseBody.class, tags = {"KnowledgeRepoManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "停用知识库响应体", response = StopKnowledgeRepoResponseBody.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/knowledges/{knowledge_repo_id}/stop",
        produces = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<StopKnowledgeRepoResponseBody> stopKnowledgeRepo(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "知识库id", required = true, schema = @Schema())
        @PathVariable("knowledge_repo_id") String knowledgeRepoId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.QUERY, description = "项目空间id", required = true, schema = @Schema()) @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

}
