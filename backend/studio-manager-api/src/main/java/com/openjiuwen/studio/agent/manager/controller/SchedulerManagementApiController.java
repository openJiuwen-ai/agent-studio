/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledExecutionListRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskListRsp;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskReq;
import com.openjiuwen.studio.agent.manager.dto.scheduler.ScheduledTaskRsp;
import com.openjiuwen.studio.agent.manager.service.ISchedulerTaskService;

import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;

import jakarta.validation.Valid;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 自动化（定时任务）管理接口。
 */
@Api(value = "SchedulerManagement", description = "the SchedulerManagement API")
@Validated
@RestController
@RequestMapping("/v1/{project_id}/agent-manager/scheduler")
public class SchedulerManagementApiController {
    @Autowired
    private ISchedulerTaskService schedulerTaskService;

    @ApiOperation(value = "创建自动化任务", nickname = "createScheduledTask")
    @PostMapping(produces = {"application/json"}, consumes = {"application/json"})
    public ResponseEntity<ScheduledTaskRsp> createTask(@PathVariable("project_id") String projectId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Valid @RequestBody ScheduledTaskReq body) {
        return ResponseModel.success(schedulerTaskService.createTask(projectId, workspaceId, body));
    }

    @ApiOperation(value = "更新自动化任务", nickname = "updateScheduledTask")
    @PutMapping(value = "/{task_id}", produces = {"application/json"}, consumes = {"application/json"})
    public ResponseEntity<ScheduledTaskRsp> updateTask(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @Valid @RequestBody ScheduledTaskReq body) {
        return ResponseModel.success(schedulerTaskService.updateTask(projectId, workspaceId, taskId, body));
    }

    @ApiOperation(value = "删除自动化任务", nickname = "deleteScheduledTask")
    @DeleteMapping(value = "/{task_id}", produces = {"application/json"})
    public ResponseEntity<Void> deleteTask(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId) {
        schedulerTaskService.deleteTask(projectId, workspaceId, taskId);
        return ResponseModel.success(null);
    }

    @ApiOperation(value = "查询自动化任务详情", nickname = "getScheduledTask")
    @GetMapping(value = "/{task_id}", produces = {"application/json"})
    public ResponseEntity<ScheduledTaskRsp> getTask(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId) {
        return ResponseModel.success(schedulerTaskService.getTask(projectId, workspaceId, taskId));
    }

    @ApiOperation(value = "分页查询自动化任务列表", nickname = "listScheduledTasks")
    @GetMapping(produces = {"application/json"})
    public ResponseEntity<ScheduledTaskListRsp> listTasks(@PathVariable("project_id") String projectId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @RequestParam(value = "page", required = false, defaultValue = "1") int page,
        @RequestParam(value = "page_size", required = false, defaultValue = "20") int pageSize,
        @RequestParam(value = "status", required = false) String status,
        @RequestParam(value = "search", required = false) String search) {
        return ResponseModel.success(
            schedulerTaskService.listTasks(projectId, workspaceId, status, search, page, pageSize));
    }

    @ApiOperation(value = "启用自动化任务", nickname = "enableScheduledTask")
    @PostMapping(value = "/{task_id}/enable", produces = {"application/json"})
    public ResponseEntity<ScheduledTaskRsp> enableTask(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId) {
        return ResponseModel.success(schedulerTaskService.enableTask(projectId, workspaceId, taskId));
    }

    @ApiOperation(value = "禁用自动化任务", nickname = "disableScheduledTask")
    @PostMapping(value = "/{task_id}/disable", produces = {"application/json"})
    public ResponseEntity<ScheduledTaskRsp> disableTask(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId) {
        return ResponseModel.success(schedulerTaskService.disableTask(projectId, workspaceId, taskId));
    }

    @ApiOperation(value = "手动触发自动化任务", nickname = "triggerScheduledTask")
    @PostMapping(value = "/{task_id}/trigger", produces = {"application/json"})
    public ResponseEntity<Void> triggerTask(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId) {
        schedulerTaskService.triggerTask(projectId, workspaceId, taskId);
        return ResponseModel.success(null);
    }

    @ApiOperation(value = "分页查询自动化任务执行日志", nickname = "listScheduledTaskExecutions")
    @GetMapping(value = "/{task_id}/executions", produces = {"application/json"})
    public ResponseEntity<ScheduledExecutionListRsp> listExecutions(@PathVariable("project_id") String projectId,
        @PathVariable("task_id") String taskId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @RequestParam(value = "page", required = false, defaultValue = "1") int page,
        @RequestParam(value = "page_size", required = false, defaultValue = "10") int pageSize,
        @RequestParam(value = "status", required = false) String status) {
        return ResponseModel.success(
            schedulerTaskService.listExecutions(projectId, workspaceId, taskId, status, page, pageSize));
    }

    @ApiOperation(value = "预览调度执行时间", nickname = "previewSchedule")
    @PostMapping(value = "/preview", produces = {"application/json"}, consumes = {"application/json"})
    public ResponseEntity<Map<String, Object>> preview(@PathVariable("project_id") String projectId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId,
        @RequestBody ScheduledTaskReq.ScheduleInfo body) {
        return ResponseModel.success(schedulerTaskService.preview(body));
    }

    @ApiOperation(value = "查询支持的执行方式", nickname = "getExecutorTypes")
    @GetMapping(value = "/executor-types", produces = {"application/json"})
    public ResponseEntity<List<Map<String, Object>>> executorTypes(@PathVariable("project_id") String projectId,
        @RequestParam(value = "workspace_id", required = true) String workspaceId) {
        return ResponseModel.success(schedulerTaskService.executorTypes());
    }
}
