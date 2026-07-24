/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentApplicationListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentVersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.ApplicationListReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.AutoAddStudioResourceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp;
import com.openjiuwen.studio.agent.manager.dto.GetAgentVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.InlineResponse404;
import com.openjiuwen.studio.agent.manager.dto.ListAgentApplicationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsV1Qo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;

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

import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@Api(value = "AgentManagement", description = "the AgentManagement API")
@Validated

/**
 * AgentManagementApi interface
 */ public interface AgentManagementApi {
    @ApiOperation(value = "添加触发器", nickname = "addTrigger", notes = "添加触发器。", response = TriggerConfig.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "触发器信息。", response = TriggerConfig.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/triggers/add",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TriggerConfig> addTrigger(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "配置触发器。", required = true) @Valid @RequestBody TriggerConfig body);

    @ApiOperation(value = "智能一键添加资源。", nickname = "autoAddStudioResource", notes = "智能一键添加资源。",
        response = AutoAddResultJsonObject.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "skill列表。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/resources",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AutoAddResultJsonObject> autoAddStudioResource(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @ApiParam(value = "智能添加资源请求体。", required = true) @Valid @RequestBody
        AutoAddStudioResourceRequestBody body);

    @ApiOperation(value = "复制一个智能体", nickname = "copyAgent", notes = "复制一个智能体。",
        response = AgentInfo.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "已复制的智能体信息。", response = AgentInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/copy", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<AgentInfo> copyAgent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "目标项目空间ID。", required = true) @RequestParam(value = "target_workspace_id", required = true)
    String targetWorkspaceId);

    @ApiOperation(value = "创建智能体", nickname = "createAgent", notes = "创建智能体。", response = AgentInfo.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "已创建的智能体信息。", response = AgentInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AgentInfo> createAgent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "待创建的智能体信息。") @Valid @RequestBody(required = false) CreateAgentReq body);

    @ApiOperation(value = "发布一个智能体版本通道", nickname = "createAgentChannel", notes = "发布一个智能体版本通道。",
        response = VersionChannelInfo.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "发布通道信息。", response = VersionChannelInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/channels",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<VersionChannelInfo> createAgentChannel(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId, @NotNull @ApiParam(value = "创建智能体版本通道请求。", required = true) @Valid @RequestBody
    CreateChannelReq body);

    @ApiOperation(value = "发布智能体版本", nickname = "createAgentVersion", notes = "发布智能体版本。",
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建智能体版本成功"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/versions",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Void> createAgentVersion(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建智能体版本请求。", required = true) @Valid @RequestBody CreateVersionReq body);

    @ApiOperation(value = "发布智能体版本V1", nickname = "createAgentVersionV1", notes = "发布智能体版本。",
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "创建智能体版本成功"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/versions", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Void> createAgentVersionV1(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "创建智能体版本请求。", required = true) @Valid @RequestBody CreateVersionReq body);

    @ApiOperation(value = "删除智能体", nickname = "deleteAgent", notes = "删除智能体。",
        response = CommonDeleteRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除智能体响应。", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteAgent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除一个智能体版本通道", nickname = "deleteAgentChannel", notes = "删除一个智能体版本通道。",
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = ""),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/channels/{channel_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteAgentChannel(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId,
        @Size(max = 128) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("channel_id") String channelId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除指定智能体版本", nickname = "deleteAgentVersion", notes = "删除指定智能体版本。",
        response = CommonDeleteRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "删除智能体版本成功", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteAgentVersion(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @Size(max = 64) @Parameter(in = ParameterIn.PATH, description = "版本ID。", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "删除触发器", nickname = "deleteTrigger", notes = "删除触发器。", tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = ""),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/triggers/{trigger_id}",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<Void> deleteTrigger(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("trigger_id")
    String triggerId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "编辑触发器", nickname = "editTrigger", notes = "编辑触发器。", response = TriggerConfig.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "触发器信息。", response = TriggerConfig.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/triggers/edit",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TriggerConfig> editTrigger(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "配置触发器。", required = true) @Valid @RequestBody TriggerConfig body);

    @ApiOperation(value = "导出智能体", nickname = "exportAgents", notes = "导出智能体。", response = Resource.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出的文件。", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/export",
        produces = {"application/json", "application/octet-stream"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<Resource> exportAgents(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "导出参数设置。", required = true) @Valid @RequestBody ExportParams body);

    @ApiOperation(value = "导出智能体", nickname = "exportResource", notes = "导出智能体。",
        response = ExportResourceRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出的文件。", response = ExportResourceRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/resource/export",
        produces = {"application/json", "application/octet-stream"}, consumes = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<ExportResourceRsp> exportResource(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "application/json 为非流式，text/event-stream 为流式")
        @RequestHeader(value = "Accept", required = false) String accept,
        @NotNull @ApiParam(value = "导出参数设置。", required = true) @Valid @RequestBody ExportResourceParams body);

    @ApiOperation(value = "导出插件", nickname = "exportTools", notes = "导出插件。", response = Resource.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导出文档。", response = Resource.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/export", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<Resource> exportTools(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "导出参数设置。", required = true) @Valid @RequestBody ExportParams body);

    @ApiOperation(value = "生成智能体描述", nickname = "generateAgentDescription", notes = "生成智能体描述。",
        response = AutoAddResultJsonObject.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "智能体描述。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/description",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> generateAgentDescription(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "生成智能体图标", nickname = "generateAgentIcons", notes = "生成智能体图标。",
        response = AutoAddResultJsonObject.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "智能体图标。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/icons", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AutoAddResultJsonObject> generateAgentIcons(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "智能体名称和描述。") @Valid @RequestBody(required = false) CreateAgentReq body);

    @ApiOperation(value = "生成智能体名字", nickname = "generateAgentName", notes = "生成智能体名字。",
        response = AutoAddResultJsonObject.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "智能体名字。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/name", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> generateAgentName(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "生成开场白", nickname = "generateAgentPrologue", notes = "生成开场白。",
        response = AutoAddResultJsonObject.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "开场白。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/prologue",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> generateAgentPrologue(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "查询租户下已发布的智能体列表，支持id列表查询", nickname = "getAgentApplications",
        notes = "查询租户下已发布的智能体列表，支持ID列表查询。", response = AgentApplicationListRsp.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询租户下已发布的智能体列表。", response = AgentApplicationListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/applications", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<AgentApplicationListRsp> getAgentApplications(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
        String projectId,
        @ApiParam(value = "智能体列表查询请求体。") @Valid @RequestBody(required = false) ApplicationListReq body);

    @ApiOperation(value = "获取指定版本智能体详情", nickname = "getAgentVersion", notes = "获取指定版本智能体详情。",
        response = AgentInfo.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "智能体版本详情信息。", response = AgentInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/versions/{version_id}",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AgentInfo> getAgentVersion(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "版本ID。", required = true, schema = @Schema())
        @PathVariable("version_id") String versionId,
        @ApiParam(value = "GetAgentVersionQo: converted from multi query params") @Valid
        GetAgentVersionQo getAgentVersionQo);

    @ApiOperation(value = "获取指定角色的权限列表", nickname = "getPermissionsByRole",
        notes = "根据角色名称返回该角色对应的权限列表。", response = List.class, responseContainer = "Map",
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "成功获取权限列表。", response = List.class, responseContainer = "Map"),
        @ApiResponse(code = 404, message = "角色未找到或没有权限。", response = InlineResponse404.class),
        @ApiResponse(code = 500, message = "服务器内部错误。")
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/permissions", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<Map<String, List<String>>> getPermissionsByRole(
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "导入智能体", nickname = "importAgents", notes = "导入智能体。", response = ImportRsp.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入响应体。", response = ImportRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/import", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ImportRsp> importAgents(@NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_agents", required = false) String importAgents,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_tools", required = false) String importTools,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_workflows", required = false) String importWorkflows,
        @Parameter(in = ParameterIn.DEFAULT, description = "模式:STRICT-严格模式/SPACIOUS-宽松模式", required = false, schema = @Schema())
        @RequestParam(value = "mode", required = false) String mode);

    @ApiOperation(value = "导入插件", nickname = "importTools", notes = "导入插件。", response = ImportRsp.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "导入插件响应体。", response = ImportRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/tools/import", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<ImportRsp> importTools(@NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Parameter(in = ParameterIn.DEFAULT, description = "", required = true, schema = @Schema())
        @RequestParam(value = "import_ids", required = false) String importIds);

    @ApiOperation(value = "查询租户下已发布的智能体列表", nickname = "listAgentApplications",
        notes = "查询租户下已发布的智能体列表。", response = AgentApplicationListRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "查询租户下已发布的智能体列表。", response = AgentApplicationListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/applications", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AgentApplicationListRsp> listAgentApplications(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @ApiParam(value = "ListAgentApplicationsQo: converted from multi query params") @Valid
    ListAgentApplicationsQo listAgentApplicationsQo);

    @ApiOperation(value = "查询智能体版本通道列表", nickname = "listAgentChannels", notes = "查询智能体版本通道列表。",
        response = VersionChannelListRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本通道列表。", response = VersionChannelListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/channels",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<VersionChannelListRsp> listAgentChannels(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
    @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @ApiParam(value = "ListAgentChannelsQo: converted from multi query params") @Valid
    ListAgentChannelsQo listAgentChannelsQo);

    @ApiOperation(value = "Get Agent versions list.", nickname = "listAgentLastVersions",
        notes = "获取已发布智能体列表。", response = AgentVersionListRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "智能体版本列表。", response = AgentVersionListRsp.class),
        @ApiResponse(code = 400, message = "Error response。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/lastversions", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AgentVersionListRsp> listAgentLastVersions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListAgentLastVersionsQo: converted from multi query params") @Valid
        ListAgentLastVersionsQo listAgentLastVersionsQo);

    @ApiOperation(value = "查询智能体版本列表", nickname = "listAgentVersions", notes = "查询智能体版本列表。",
        response = VersionListRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本列表。", response = VersionListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/versions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<VersionListRsp> listAgentVersions(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @ApiParam(value = "ListAgentVersionsQo: converted from multi query params") @Valid
        ListAgentVersionsQo listAgentVersionsQo);

    @ApiOperation(value = "查询智能体版本列表V1", nickname = "listAgentVersionsV1", notes = "查询智能体版本列表。",
        response = VersionListRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "应用版本列表。", response = VersionListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agents/{agent_id}/versions", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<VersionListRsp> listAgentVersionsV1(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @ApiParam(value = "ListAgentVersionsV1Qo: converted from multi query params") @Valid
        ListAgentVersionsV1Qo listAgentVersionsV1Qo);

    @ApiOperation(value = "获取智能体列表", nickname = "listAgents", notes = "获取智能体列表。",
        response = AgentListRsp.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "搜索的智能体列表。", response = AgentListRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AgentListRsp> listAgents(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListAgentsQo: converted from multi query params") @Valid ListAgentsQo listAgentsQo);

    @ApiOperation(value = "解析导入文件", nickname = "listImportFile", notes = "解析导入文件。",
        response = ImportListInfo.class, responseContainer = "List", tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "文件解析内容。", response = ImportListInfo.class,
            responseContainer = "List"),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/list", produces = {"application/json"},
        consumes = {"multipart/form-data"}, method = RequestMethod.POST)
    ResponseEntity<List<ImportListInfo>> listImportFile(
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Parameter(description = "file detail") @Valid @RequestPart(value = "file", required = true) MultipartFile file,
        @Min(0) @Max(10000)
        @ApiParam(value = "分页记录的起始位置偏移量，默认值0。", allowableValues = "10000, 0", defaultValue = "0")
        @RequestParam(value = "offset", required = false, defaultValue = "0") Integer offset,
        @Min(1) @Max(1000) @ApiParam(value = "每一页的数量，默认值10。", allowableValues = "1000, 1", defaultValue = "10")
        @RequestParam(value = "limit", required = false, defaultValue = "10") Integer limit);

    @ApiOperation(value = "修改智能体", nickname = "modifyAgent", notes = "修改智能体。", response = AgentInfo.class,
        tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "修改后的智能体信息。", response = AgentInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<AgentInfo> modifyAgent(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "待修改的智能体应用。") @Valid @RequestBody(required = false) ModifyAgentReq body);

    @ApiOperation(value = "修改一个智能体版本通道", nickname = "modifyAgentChannel", notes = "修改一个智能体版本通道。",
        response = VersionChannelInfo.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "版本通道信息。", response = VersionChannelInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/channels/{channel_id}",
        produces = {"application/json"}, consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<VersionChannelInfo> modifyAgentChannel(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
        String agentId,
        @Size(max = 128) @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("channel_id") String channelId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @ApiParam(value = "修改版本通道请求体。") @Valid @RequestBody(required = false) ModifyChannelReq body);

    @ApiOperation(value = "生成推荐问题", nickname = "recommendedAgentQuestions", notes = "生成推荐问题。",
        response = AutoAddResultJsonObject.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "推荐问列表。", response = AutoAddResultJsonObject.class),
        @ApiResponse(code = 400, message = "Bad Request。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/recommended-questions",
        produces = {"application/json"}, method = RequestMethod.GET)
    ResponseEntity<AutoAddResultJsonObject> recommendedAgentQuestions(
        @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取智能体详情", nickname = "retrieveAgent", notes = "获取智能体详情。",
        response = AgentInfo.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取的智能体信息。", response = AgentInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class),
        @ApiResponse(code = 403, message = "Forbidden 没有操作权限。", response = ErrorRsp.class),
        @ApiResponse(code = 404, message = "Not Found 找不到资源。", response = ErrorRsp.class),
        @ApiResponse(code = 500, message = "Internal Server Error 服务内部错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AgentInfo> retrieveAgent(
        @Parameter(in = ParameterIn.PATH, description = "项目ID。", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
        @Parameter(in = ParameterIn.PATH, description = "资源ID。", required = true, schema = @Schema())
        @PathVariable("agent_id") String agentId,
        @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
        @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "获取一个百宝箱的智能体应用", nickname = "retrieveAgentApp",
        notes = "获取一个百宝箱的智能体应用。", response = AgentInfo.class, tags = {"AgentManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "获取的智能体信息。", response = AgentInfo.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agent-apps/{agent_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<AgentInfo> retrieveAgentApp(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("project_id")
    String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(max = 64)
    @Parameter(in = ParameterIn.PATH, description = "", required = true, schema = @Schema()) @PathVariable("agent_id")
    String agentId, @NotNull @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64)
    @ApiParam(value = "项目空间ID。", required = true) @RequestParam(value = "workspace_id", required = true)
    String workspaceId);

    @ApiOperation(value = "上传一个写作模版", nickname = "uploadDeepResearchTemplate", notes = "上传一个写作模版。", response = FileUploadRsp.class, tags={ "AgentManagement" })
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "上传的写作模板信息。", response = FileUploadRsp.class),
        @ApiResponse(code = 400, message = "Bad Request 请求错误。", response = ErrorRsp.class) })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/agents/{agent_id}/uploadDeepResearchTemplate",
        produces = { "application/json" },
        consumes = { "multipart/form-data" },
        method = RequestMethod.POST)
    ResponseEntity<FileUploadRsp> uploadDeepResearchTemplate(@NotNull @Pattern(regexp="^[a-zA-Z0-9_()\\-]+$") @Size(min=1,max=64) @ApiParam(value = "项目空间ID。", required = true)  @RequestParam(value = "workspace_id", required = true) String workspaceId,@Pattern(regexp="^[a-zA-Z0-9_-]+$") @Size(max=64) @Parameter(in = ParameterIn.PATH, description = "", required=true, schema=@Schema()) @PathVariable("project_id") String projectId,@Pattern(regexp="^[a-zA-Z0-9_-]+$") @Size(max=64) @Parameter(in = ParameterIn.PATH, description = "", required=true, schema=@Schema()) @PathVariable("agent_id") String agentId,@Parameter(description = "file detail") @Valid @RequestPart(value = "file" , required = true) MultipartFile file) ;
}
