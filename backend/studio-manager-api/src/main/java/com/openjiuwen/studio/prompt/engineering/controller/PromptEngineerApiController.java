/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptTaskRsp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptTaskIterEvalResQo;
import com.openjiuwen.studio.prompt.engineering.dto.ListPromptTasksQo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseResp;
import com.openjiuwen.studio.prompt.engineering.dto.PromptTaskCreateReq;
import com.openjiuwen.studio.prompt.engineering.service.IPromptEngineerService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

/**
 * PromptEngineer controller
 */
@RestController

public class PromptEngineerApiController implements PromptEngineerApi {

    private static final Logger log = LoggerFactory.getLogger(PromptEngineerApiController.class);

    @Autowired
    private IPromptEngineerService promptEngineerService;

    @Override
    public ResponseEntity<CreatePromptTaskRsp> copyPromptTask(String projectId, String taskId, String workspaceId) {
        return ResponseModel.success(promptEngineerService.copyPromptTask(projectId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<CreatePromptTaskRsp> createPromptTask(String projectId, String taskId, String workspaceId) {
        return ResponseModel.success(promptEngineerService.createPromptTask(projectId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<CreatePromptTaskRsp> createPromptTaskDraft(String projectId, String workspaceId, PromptTaskCreateReq body) {
        return ResponseModel.success(promptEngineerService.createPromptTaskDraft(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<PromptBaseInfo> deletePromptTask(String projectId, String taskId, String workspaceId) {
        return ResponseModel.success(promptEngineerService.deletePromptTask(projectId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<PromptBaseResp> getPromptTask(String projectId, String taskId, String workspaceId) {
        return ResponseModel.success(promptEngineerService.getPromptTask(projectId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<PromptBaseResp> getPromptTaskIterEvalRes(String projectId, String taskId, String iterNum, GetPromptTaskIterEvalResQo getPromptTaskIterEvalResQo) {
        return ResponseModel.success(promptEngineerService.getPromptTaskIterEvalRes(projectId, taskId, iterNum, getPromptTaskIterEvalResQo));
    }

    @Override
    public ResponseEntity<PromptBaseResp> listPromptTasks(String projectId, ListPromptTasksQo listPromptTasksQo) {
        return ResponseModel.success(promptEngineerService.listPromptTasks(projectId, listPromptTasksQo));
    }

    @Override
    public ResponseEntity<PromptBaseInfo> pausePromptTask(String projectId, String taskId, String workspaceId) {
        return ResponseModel.success(promptEngineerService.pausePromptTask(projectId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<PromptBaseInfo> resumePromptTask(String projectId, String taskId, String workspaceId) {
        return ResponseModel.success(promptEngineerService.resumePromptTask(projectId, taskId, workspaceId));
    }

    @Override
    public ResponseEntity<PromptBaseResp> updatePromptTaskDraft(String projectId, String taskId, String workspaceId, PromptTaskCreateReq body) {
        return ResponseModel.success(promptEngineerService.updatePromptTaskDraft(projectId, taskId, workspaceId, body));
    }
}
