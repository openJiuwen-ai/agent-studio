/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.AvailableModelServicesQo;
import com.openjiuwen.studio.agent.manager.dto.BaseResp;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.MaasServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelInvokeDataListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelNameResp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListQo;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceReq;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelStatusReq;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelExportReq;
import com.openjiuwen.studio.agent.manager.dto.ModelImportPreviewRsp;
import com.openjiuwen.studio.agent.manager.enums.ModelImportConflictStrategy;

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
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

@Api(value = "ModelServiceMgmt", description = "the ModelServiceMgmt API")
@Validated

/**
 * ModelServiceMgmtApi interface
 */ public interface ModelServiceMgmtApi {
    @ApiOperation(value = "", nickname = "availableModelServices", notes = "查询可用的模型服务",
        response = Object.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = Object.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/available/model-services", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Object> availableModelServices(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "AvailableModelServicesQo: converted from multi query params") @Valid
    AvailableModelServicesQo availableModelServicesQo);

    @ApiOperation(value = "", nickname = "createModelService", notes = "新增模型服务", response = Object.class,
        tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = Object.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Object> createModelService(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @ApiParam(value = "", defaultValue = "false")
        @RequestParam(value = "available_check", required = false, defaultValue = "false") Boolean availableCheck,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ModelServiceReq body);

    @ApiOperation(value = "", nickname = "deleteModelService", notes = "删除模型服务", tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/{id}", method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteModelService(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "existsModelName", notes = "查询模型名称是否存在",
        response = ModelNameResp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "是否存在该模型名称", response = ModelNameResp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/model-name/check",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<ModelNameResp> existsModelName(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @Size(min = 2, max = 64) @ApiParam(value = "", required = true)
        @RequestParam(value = "model_name", required = true) String modelName);

    @ApiOperation(value = "", nickname = "maasModelServiceList", notes = "查询模型服务",
        response = MaasServiceRsp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = MaasServiceRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/maas-model-services", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<MaasServiceRsp> maasModelServiceList(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId);

    @ApiOperation(value = "", nickname = "modelServiceDetail", notes = "查询模型服务详情",
        response = ModelServiceRsp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = ModelServiceRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/{id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ModelServiceRsp> modelServiceDetail(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "modelServiceList", notes = "查询模型服务",
        response = ModelServiceListRsp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = ModelServiceListRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ModelServiceListRsp> modelServiceList(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "ModelServiceListQo: converted from multi query params") @Valid
    ModelServiceListQo modelServiceListQo);

    @ApiOperation(value = "", nickname = "offlineModelService", notes = "取消发布模型服务", tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/{id}/offline", method = RequestMethod.POST)
    ResponseEntity<Void> offlineModelService(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "onlineModelService", notes = "发布模型服务", tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/{id}/online", method = RequestMethod.POST)
    ResponseEntity<Void> onlineModelService(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @ApiParam(value = "", defaultValue = "false")
        @RequestParam(value = "available_check", required = false, defaultValue = "false") Boolean availableCheck,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id);

    @ApiOperation(value = "", nickname = "queryModelInvokeData", notes = "查询模型调用数据",
        response = ModelInvokeDataListRsp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = ModelInvokeDataListRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/query/model-invoke/data", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<ModelInvokeDataListRsp> queryModelInvokeData(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @Size(max = 80) @ApiParam(value = "") @RequestParam(value = "model_id", required = false) String modelId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId);

    @ApiOperation(value = "", nickname = "syncModelService", notes = "同步第三方模型服务", response = BaseResp.class,
        tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "同步第三方服务列表成功", response = BaseResp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "Unauthorized 鉴权失败", response = String.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/sync", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<BaseResp> syncModelService(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "provider_id", required = true) String providerId);

    @ApiOperation(value = "", nickname = "updateModelService", notes = "更新模型服务", response = Object.class,
        tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = Object.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/{id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<Object> updateModelService(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @ApiParam(value = "", defaultValue = "false")
        @RequestParam(value = "available_check", required = false, defaultValue = "false") Boolean availableCheck,
        @Pattern(regexp = "^[a-zA-Z0-9_-]{1,80}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("id")
        String id, @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ModelServiceReq body);

    @ApiOperation(value = "", nickname = "updateModelStatus", notes = "更新模型调测状态", tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功")
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-test/status", consumes = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<Void> updateModelStatus(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ModelStatusReq body);

    @ApiOperation(value = "", nickname = "exportModelServices", notes = "批量导出模型服务为 JSONL 文件",
        response = Resource.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = Resource.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/export",
        produces = {"application/octet-stream"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportModelServices(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody ModelExportReq body);

    @ApiOperation(value = "", nickname = "previewImportModelServices", notes = "模型导入预检（解析+冲突检测+URL校验，不落库）",
        response = ModelImportPreviewRsp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = ModelImportPreviewRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/import/preview",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ModelImportPreviewRsp> previewImportModelServices(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file,
        @ApiParam(value = "目标供应商id（详情页只导模型导入用，模型重定向挂到该供应商）", required = false)
        @RequestParam(value = "target_provider_id", required = false) String targetProviderId);

    @ApiOperation(value = "", nickname = "importModelServices", notes = "批量导入模型服务（落库，保留跨环境id）",
        response = ImportRsp.class, tags = {"ModelServiceMgmt"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功", response = ImportRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/model-manager/model-services/import",
        produces = {"application/json"}, consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ImportRsp> importModelServices(@Pattern(regexp = "^[a-zA-Z0-9_-]{1,40}$")
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]{1,40}$") @ApiParam(value = "", required = true)
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file,
        @ApiParam(value = "冲突策略: SKIP-同名跳过 / COVER-同名覆盖", required = false, defaultValue = "SKIP")
        @RequestParam(value = "conflict_strategy", required = false, defaultValue = "SKIP")
        String conflictStrategy,
        @ApiParam(value = "目标供应商id（详情页只导模型导入用，模型重定向挂到该供应商）", required = false)
        @RequestParam(value = "target_provider_id", required = false) String targetProviderId);

}
