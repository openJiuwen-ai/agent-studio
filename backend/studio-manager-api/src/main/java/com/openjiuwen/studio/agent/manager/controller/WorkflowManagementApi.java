/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CopyWorkflowQo;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowEnvsQo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowParamsQo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionsV1Qo;
import com.openjiuwen.studio.agent.common.dto.agent.ListWorkflowsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.manager.dto.ValidateWorkflowQo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkFlowEnvs;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFrontParamInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.common.dto.run.WorkflowListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowSceneRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVersionListRsp;

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
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

@Api(value = "WorkflowManagement", description = "the WorkflowManagement API")
@Validated

/**
 * WorkflowManagementApi interface
 */ public interface WorkflowManagementApi {
    @ApiOperation(value = "工作流添加触发器", nickname = "addTrigger", notes = "工作流添加触发器。",
        response = TriggerConfig.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "触发器信息。", response = TriggerConfig.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/triggers/add",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TriggerConfig> addTrigger(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "配置触发器。", required = true) @Valid @RequestBody TriggerConfig body);

    @ApiOperation(value = "复制工作流", nickname = "copyWorkflow", notes = "复制工作流。", response = WorkflowInfo.class,
        tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/copy",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<WorkflowInfo> copyWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "CopyWorkflowQo: converted from multi query params") @Valid CopyWorkflowQo copyWorkflowQo);

    @ApiOperation(value = "创建工作流", nickname = "createWorkflow", notes = "创建工作流。",
        response = WorkflowInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<WorkflowInfo> createWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "工作流请求信息。", required = true) @Valid @RequestBody WorkflowInfo body);

    @ApiOperation(value = "发布一个Workflow版本通道", nickname = "createWorkflowChannel",
        notes = "发布一个Workflow版本通道。", response = VersionChannelInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "发布通道信息。", response = VersionChannelInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<VersionChannelInfo> createWorkflowChannel(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @NotNull @ApiParam(value = "创建workflow版本通道请求。", required = true) @Valid @RequestBody
        CreateChannelReq body);

    @ApiOperation(value = "工作流删除触发器", nickname = "deleteTrigger", notes = "工作流删除触发器。",
        tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。"),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/triggers/{trigger_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteTrigger(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
    @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("trigger_id")
    String triggerId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "刪除工作流", nickname = "deleteWorkflow", notes = "刪除工作流。",
        response = CommonDeleteRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除一个workflow版本通道", nickname = "deleteWorkflowChannel",
        notes = "删除一个workflow版本通道。", response = CommonDeleteRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels/{channel_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteWorkflowChannel(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("channel_id") String channelId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除一个workflow版本快照", nickname = "deleteWorkflowVersion",
        notes = "删除一个workflow版本快照。", response = CommonDeleteRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteWorkflowVersion(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "工作流编辑触发器", nickname = "editTrigger", notes = "工作流编辑触发器。",
        response = TriggerConfig.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "触发器信息。", response = TriggerConfig.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/triggers/edit",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TriggerConfig> editTrigger(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "配置触发器。", required = true) @Valid @RequestBody TriggerConfig body);

    @ApiOperation(value = "导出工作流", nickname = "exportWorkflows", notes = "导出工作流。", response = Resource.class,
        tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出的文件。", response = Resource.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/export", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportWorkflows(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "导出参数设置。", required = true) @Valid @RequestBody ExportParams body);

    @ApiOperation(value = "对话型工作流生成开场白", nickname = "generateWorkflowPrologue",
        notes = "对话型工作流生成开场白。", response = AutoAddResultJsonObject.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "开场白。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/prologue",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> generateWorkflowPrologue(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取工作流详情", nickname = "getWorkflow", notes = "获取工作流详情。",
        response = WorkflowInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<WorkflowInfo> getWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取一个workflow中的渠道变量", nickname = "getWorkflowEnvs",
        notes = "获取一个workflow版本中的渠道变量。", response = WorkFlowEnvs.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "workflow中的渠道变量。", response = WorkFlowEnvs.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions/envs",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<WorkFlowEnvs> getWorkflowEnvs(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "GetWorkflowEnvsQo: converted from multi query params") @Valid
        GetWorkflowEnvsQo getWorkflowEnvsQo);

    @ApiOperation(value = "获取工作流输入输出参数", nickname = "getWorkflowParams", notes = "获取工作流输入输出参数。",
        response = WorkflowFrontParamInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowFrontParamInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/front-params",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<WorkflowFrontParamInfo> getWorkflowParams(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "GetWorkflowParamsQo: converted from multi query params") @Valid
        GetWorkflowParamsQo getWorkflowParamsQo);

    @ApiOperation(value = "Get workflow application details.", nickname = "getWorkflowScene",
        notes = "查询场景化应用接口。", response = WorkflowSceneRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowSceneRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/scene/{workflow_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<WorkflowSceneRsp> getWorkflowScene(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Size(max = 128)
        @Parameter(in = ParameterIn.PATH, description = "workflow ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取一个workflow版本定义", nickname = "getWorkflowVersion",
        notes = "获取一个workflow版本定义。", response = WorkflowInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "workflow指定版本定义。", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<WorkflowInfo> getWorkflowVersion(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @ApiParam(value = "是否检查嵌套层级。") @RequestHeader(value = "nested-check", required = false)
        Boolean nestedCheck, @ApiParam(value = "GetWorkflowVersionQo: converted from multi query params") @Valid
        GetWorkflowVersionQo getWorkflowVersionQo);

    @ApiOperation(value = "导入工作流", nickname = "importWorkflows", notes = "导入工作流。", response = ImportRsp.class,
        tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入响应体。", response = ImportRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/import", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ImportRsp> importWorkflows(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_workflows", required = false) String importWorkflows,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_tools", required = false) String importTools,
        @Parameter(in = ParameterIn.DEFAULT, description = "模式:STRICT-严格模式/SPACIOUS-宽松模式", required = false, schema = @Schema())
        @RequestParam(value = "mode", required = false) String mode);

    @ApiOperation(value = "查询workflow版本通道列表", nickname = "listWorkflowChannels",
        notes = "查询workflow版本通道列表。", response = VersionChannelListRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "工作流版本通道列表。", response = VersionChannelListRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<VersionChannelListRsp> listWorkflowChannels(
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListWorkflowChannelsQo: converted from multi query params") @Valid
        ListWorkflowChannelsQo listWorkflowChannelsQo);

    @ApiOperation(value = "Get workflow versions list.", nickname = "listWorkflowLastVersions",
        notes = "获取已发布工作流列表。", response = WorkflowVersionListRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowVersionListRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/lastversions", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<WorkflowVersionListRsp> listWorkflowLastVersions(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListWorkflowLastVersionsQo: converted from multi query params") @Valid
        ListWorkflowLastVersionsQo listWorkflowLastVersionsQo);

    @ApiOperation(value = "查询工作流版本列表", nickname = "listWorkflowVersions", notes = "查询工作流版本列表。",
        response = VersionListRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本列表。", response = VersionListRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<VersionListRsp> listWorkflowVersions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListWorkflowVersionsQo: converted from multi query params") @Valid
        ListWorkflowVersionsQo listWorkflowVersionsQo);

    @ApiOperation(value = "查询工作流版本列表V1", nickname = "listWorkflowVersionsV1", notes = "查询工作流版本列表。",
        response = VersionListRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本列表。", response = VersionListRsp.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/workflows/{workflow_id}/versions", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<VersionListRsp> listWorkflowVersionsV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListWorkflowVersionsV1Qo: converted from multi query params") @Valid
        ListWorkflowVersionsV1Qo listWorkflowVersionsV1Qo);

    @ApiOperation(value = "获取工作流列表", nickname = "listWorkflows", notes = "获取工作流列。",
        response = WorkflowListRsp.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowListRsp.class),
        @ApiResponse(code = 400, message = "错误响应。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<WorkflowListRsp> listWorkflows(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListWorkflowsQo: converted from multi query params") @Valid ListWorkflowsQo listWorkflowsQo);

    @ApiOperation(value = "修改一个workflow版本通道", nickname = "modifyWorkflowChannel",
        notes = "修改一个workflow版本通道。", response = VersionChannelInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "版本通道信息。", response = VersionChannelInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/channels/{channel_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<VersionChannelInfo> modifyWorkflowChannel(
        @Size(max = 128) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Size(max = 128) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Size(max = 128) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("channel_id") String channelId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "修改版本通道请求体。") @Valid @RequestBody(required = false) ModifyChannelReq body);

    @ApiOperation(value = "解析并转换第三方的工作流文件", nickname = "parseThirdpartyWorkflowFile",
        notes = "解析并转换第三方的工作流文件", response = WorkflowInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "解析成功响应体", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/import/parse", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<WorkflowInfo> parseThirdpartyWorkflowFile(@NotNull @Size(min = 1, max = 64)
        @ApiParam(value = "第三方工作流类型", required = true, allowableValues = "Dify")
        @RequestParam(value = "type", required = true) String type,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间id", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true)
        MultipartFile file);

    @ApiOperation(value = "对话型工作流生成推荐问", nickname = "recommendedWorkflowQuestions",
        notes = "对话型工作流生成推荐问。", response = AutoAddResultJsonObject.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "推荐问列表。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/recommended-questions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> recommendedWorkflowQuestions(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "发布工作流版本", nickname = "releaseWorkflowVersion", notes = "发布工作流版本。",
        response = String.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "发布版本号。", response = String.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/versions",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> releaseWorkflowVersion(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @ApiParam(value = "") @Valid @RequestBody(required = false) CreateVersionReq body);

    @ApiOperation(value = "发布工作流版本V1", nickname = "releaseWorkflowVersionV1", notes = "发布工作流版本。",
        response = String.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "发布版本号。", response = String.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/workflows/{workflow_id}/versions", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<String> releaseWorkflowVersionV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @ApiParam(value = "") @Valid @RequestBody(required = false) CreateVersionReq body);

    @ApiOperation(value = "设置工作流试运行状态", nickname = "setWorkflowTestStatus", notes = "设置工作流试运行状态。",
        response = WorkflowInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "错误响应。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/test-status",
        produces = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<WorkflowInfo> setWorkflowTestStatus(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "是否试运行成功。", required = true) @RequestParam(value = "success", required = true)
        Boolean success);

    @ApiOperation(value = "修改工作流", nickname = "updateWorkflow", notes = "修改工作流。",
        response = WorkflowInfo.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowInfo.class),
        @ApiResponse(code = 400, message = "请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 401, message = "鉴权失败。", response = String.class),
        @ApiResponse(code = 403, message = "没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<WorkflowInfo> updateWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "团队空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "工作流请求信息。", required = true) @Valid @RequestBody WorkflowInfo body);

    @ApiOperation(value = "验证工作流信息", nickname = "validateWorkflow", notes = "验证工作流信息。",
        response = WorkflowValidationVO.class, tags = {"WorkflowManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功响应。", response = WorkflowValidationVO.class),
        @ApiResponse(code = 400, message = "错误响应。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/validate",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<WorkflowValidationVO> validateWorkflow(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流ID。", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ValidateWorkflowQo: converted from multi query params") @Valid
        ValidateWorkflowQo validateWorkflowQo);

}
