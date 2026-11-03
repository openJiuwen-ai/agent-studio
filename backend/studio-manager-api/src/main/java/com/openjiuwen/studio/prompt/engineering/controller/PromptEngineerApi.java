/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.prompt.engineering.controller;

import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptTaskRsp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptTaskIterEvalResQo;
import com.openjiuwen.studio.prompt.engineering.dto.ListPromptTasksQo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseResp;
import com.openjiuwen.studio.prompt.engineering.dto.PromptErrorInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptTaskCreateReq;

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

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * PromptEngineerApi interface
 */

@Api(value = "PromptEngineer", description = "the PromptEngineer API")
@Validated
public interface PromptEngineerApi {

    @ApiOperation(value = "创建副本", nickname = "copyPromptTask", notes = "Create a copy the prompt optimization task",
        response = CreatePromptTaskRsp.class, tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = CreatePromptTaskRsp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}/copy", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<CreatePromptTaskRsp> copyPromptTask(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "创建提示词优化任务", nickname = "createPromptTask",
        notes = "Create a new prompt optimization task", response = CreatePromptTaskRsp.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = CreatePromptTaskRsp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<CreatePromptTaskRsp> createPromptTask(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "创建提示词优化任务草稿", nickname = "createPromptTaskDraft",
        notes = "Create a new prompt optimization task", response = CreatePromptTaskRsp.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = CreatePromptTaskRsp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/draft", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.POST)
    ResponseEntity<CreatePromptTaskRsp> createPromptTaskDraft(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody PromptTaskCreateReq body);

    @ApiOperation(value = "删除提示词优化任务", nickname = "deletePromptTask",
        notes = "Delete a prompt optimization task", response = PromptBaseInfo.class, tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = PromptBaseInfo.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 404, message = "任务不存在", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}", produces = {"application/json"},
        method = RequestMethod.DELETE)
    ResponseEntity<PromptBaseInfo> deletePromptTask(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "查询提示词优化任务详情", nickname = "getPromptTask",
        notes = "Get details of a specific prompt optimization task", response = PromptBaseResp.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = PromptBaseResp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 404, message = "任务不存在", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<PromptBaseResp> getPromptTask(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @ApiParam(value = "空间id") @RequestParam(value = "workspace_id", required = false) String workspaceId);

    @ApiOperation(value = "查询提示词优化任务某一轮迭代评估数据集预测结果", nickname = "getPromptTaskIterEvalRes",
        notes = "Get eval details of a specific iter prompt optimization task", response = PromptBaseResp.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = PromptBaseResp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 404, message = "任务不存在", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}/eval/{iter_num}", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<PromptBaseResp> getPromptTaskIterEvalRes(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @Parameter(in = ParameterIn.PATH, description = "迭代轮次", required = true, schema = @Schema())
        @PathVariable("iter_num") String iterNum,
        @ApiParam(value = "GetPromptTaskIterEvalResQo: converted from multi query params") @Valid
        GetPromptTaskIterEvalResQo getPromptTaskIterEvalResQo);

    @ApiOperation(value = "查询提示词优化任务列表", nickname = "listPromptTasks",
        notes = "获取指定项目下的提示词优化任务列表，支持分页和多种筛选条件", response = PromptBaseResp.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = PromptBaseResp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks", produces = {"application/json"},
        method = RequestMethod.GET)
    ResponseEntity<PromptBaseResp> listPromptTasks(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @ApiParam(value = "ListPromptTasksQo: converted from multi query params") @Valid
        ListPromptTasksQo listPromptTasksQo);

    @ApiOperation(value = "暂停提示词优化任务", nickname = "pausePromptTask",
        notes = "将执行中(2)的任务暂停，状态变更为等待执行(1)", response = PromptBaseInfo.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "暂停成功", response = PromptBaseInfo.class),
        @ApiResponse(code = 400, message = "暂停失败（如当前状态不允许暂停）", response = PromptErrorInfo.class),
        @ApiResponse(code = 404, message = "任务不存在", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "服务器错误", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}/pause", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<PromptBaseInfo> pausePromptTask(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "继续提示词优化任务", nickname = "resumePromptTask",
        notes = "将暂停状态(1)的任务恢复为执行中(2)", response = PromptBaseInfo.class, tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "继续成功", response = PromptBaseInfo.class),
        @ApiResponse(code = 400, message = "继续失败（如当前状态不允许继续）", response = PromptErrorInfo.class),
        @ApiResponse(code = 404, message = "任务不存在", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "服务器错误", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}/resume", produces = {"application/json"},
        method = RequestMethod.POST)
    ResponseEntity<PromptBaseInfo> resumePromptTask(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId);

    @ApiOperation(value = "全量更新提示词优化任务（只能更新草稿）", nickname = "updatePromptTaskDraft",
        notes = "Fully update a prompt optimization task (all fields required)", response = PromptBaseResp.class,
        tags = {"Prompt Engineer"})
    @ApiResponses(value = {
        @ApiResponse(code = 200, message = "操作成功", response = PromptBaseResp.class),
        @ApiResponse(code = 400, message = "操作失败,返回错误信息", response = PromptErrorInfo.class),
        @ApiResponse(code = 404, message = "任务不存在", response = PromptErrorInfo.class),
        @ApiResponse(code = 500, message = "操作失败,返回错误信息", response = PromptErrorInfo.class)
    })
    @RequestMapping(value = "/v2/{project_id}/prompt/tasks/{task_id}", produces = {"application/json"},
        consumes = {"application/json"}, method = RequestMethod.PUT)
    ResponseEntity<PromptBaseResp> updatePromptTaskDraft(
        @Parameter(in = ParameterIn.PATH, description = "项目ID", required = true, schema = @Schema())
        @PathVariable("project_id") String projectId,
        @Pattern(regexp = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
        @Parameter(in = ParameterIn.PATH, description = "任务ID", required = true, schema = @Schema())
        @PathVariable("task_id") String taskId,
        @NotNull @ApiParam(value = "空间ID", required = true) @RequestParam(value = "workspace_id", required = true)
        String workspaceId,
        @NotNull @ApiParam(value = "", required = true) @Valid @RequestBody PromptTaskCreateReq body);
}
