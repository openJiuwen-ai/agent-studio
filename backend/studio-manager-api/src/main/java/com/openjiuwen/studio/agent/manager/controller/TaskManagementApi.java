/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.CreateTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ListTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.ModifyTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ResumeTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.TaskListRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveTaskQo;

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

@Api(value = "TaskManagement", description = "the TaskManagement API")
@Validated

/**
 * TaskManagementApi interface
 */
public interface TaskManagementApi {
    @ApiOperation(value = "取消异步任务详情", nickname = "cancelTask", notes = "", response = CancelTaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = CancelTaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}/cancel",
        produces = {"application/json"}, method = RequestMethod.DELETE)
    ResponseEntity<CancelTaskRsp> cancelTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @ApiOperation(value = "提交异步工作流任务", nickname = "createTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TaskRsp> createTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @Size(max = 64) @ApiParam(value = "版本号") @RequestParam(value = "version", required = false) String version,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "创建文件请求体", required = true) @Valid @RequestBody CreateTaskReq body);

    @ApiOperation(value = "取消异步任务详情", nickname = "deleteTask", notes = "", response = CommonDeleteRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = CommonDeleteRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<CommonDeleteRsp> deleteTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @ApiOperation(value = "查看任务列表", nickname = "listTask", notes = "", response = TaskListRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskListRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<TaskListRsp> listTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId,
        @ApiParam(value = "ListTaskQo: converted from multi query params") @Valid ListTaskQo listTaskQo);

    @ApiOperation(value = "修改任务信息", nickname = "modifyTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<TaskRsp> modifyTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "创建文件请求体", required = true) @Valid @RequestBody ModifyTaskReq body);

    @ApiOperation(value = "继续执行任务", nickname = "resumeTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<TaskRsp> resumeTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Pattern(regexp = "^[a-zA-Z0-9_()\\-]+$") @Size(min = 1, max = 64) @ApiParam(value = "项目空间id")
        @RequestParam(value = "workspace_id", required = false) String workspaceId,
        @NotNull @ApiParam(value = "创建文件请求体", required = true) @Valid @RequestBody ResumeTaskReq body);

    @ApiOperation(value = "获取异步任务详情", nickname = "retrieveTask", notes = "", response = TaskRsp.class,
        tags = {"TaskManagement"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "", response = TaskRsp.class),
        @ApiResponse(code = 400, message = "", response = ErrorRsp.class)
    })
    @RequestMapping(value = "/v1/{project_id}/agent-manager/workflows/{workflow_id}/tasks/{task_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<TaskRsp> retrieveTask(@Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "租户项目id", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "工作流id", required = true, schema = @Schema())
        @PathVariable("workflow_id") String workflowId, @Pattern(regexp = "^[a-zA-Z0-9_-]+$") @Size(min = 1, max = 64)
        @Parameter(in = ParameterIn.PATH, description = "异步任务id", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @ApiParam(value = "RetrieveTaskQo: converted from multi query params") @Valid RetrieveTaskQo retrieveTaskQo);

}
