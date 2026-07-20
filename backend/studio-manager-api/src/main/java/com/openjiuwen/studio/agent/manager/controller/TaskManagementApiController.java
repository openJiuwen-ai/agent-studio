/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.CreateTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ListTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.ModifyTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ResumeTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.TaskListRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskRsp;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveTaskQo;
import com.openjiuwen.studio.agent.manager.service.ITaskManagementService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

/**
 * TaskManagement controller
 */
@RestController

public class TaskManagementApiController implements TaskManagementApi {
    private static final Logger log = LoggerFactory.getLogger(TaskManagementApiController.class);

    @Autowired
    private ITaskManagementService taskManagementService;

    @Override
    public ResponseEntity<CancelTaskRsp> cancelTask(String projectId, String workflowId, String taskId, String workspaceId) {
        return ResponseModel.success(taskManagementService.cancelTask(projectId, workflowId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<TaskRsp> createTask(String projectId, String workflowId, String version, String workspaceId, CreateTaskReq body) {
        return ResponseModel.success(taskManagementService.createTask(projectId, workflowId, version, workspaceId, body));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deleteTask(String projectId, String workflowId, String taskId, String workspaceId) {
        return ResponseModel.success(taskManagementService.deleteTask(projectId, workflowId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<TaskListRsp> listTask(String projectId, String workflowId, ListTaskQo listTaskQo) {
        return ResponseModel.success(taskManagementService.listTask(projectId, workflowId, listTaskQo));
    }

    @Override
    public ResponseEntity<TaskRsp> modifyTask(String projectId, String workflowId, String taskId, String workspaceId, ModifyTaskReq body) {
        return ResponseModel.success(taskManagementService.modifyTask(projectId, workflowId, taskId, workspaceId, body));
    }

    @Override
    public ResponseEntity<TaskRsp> resumeTask(String projectId, String workflowId, String taskId, String workspaceId, ResumeTaskReq body) {
        return ResponseModel.success(taskManagementService.resumeTask(projectId, workflowId, taskId, workspaceId, body));
    }

    @Override
    public ResponseEntity<TaskRsp> retrieveTask(String projectId, String workflowId, String taskId, RetrieveTaskQo retrieveTaskQo) {
        return ResponseModel.success(taskManagementService.retrieveTask(projectId, workflowId, taskId, retrieveTaskQo));
    }
}