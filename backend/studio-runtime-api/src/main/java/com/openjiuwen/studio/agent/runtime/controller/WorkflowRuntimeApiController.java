/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.service.IWorkflowRuntimeService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;


/**
 * WorkflowRuntime controller
 */
@RestController

public class WorkflowRuntimeApiController implements WorkflowRuntimeApi {
    private static final Logger log = LoggerFactory.getLogger(WorkflowRuntimeApiController.class);

    @Autowired
    private IWorkflowRuntimeService workflowRuntimeService;

    @Override
    public ResponseEntity<Status> abortConversation(String projectId, String workflowId, String conversationId) {
        return ResponseModel.success(workflowRuntimeService.abortConversation(projectId, workflowId, conversationId));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> additionalQuestionsWorkflow(String projectId, String workflowId, String conversationId, String workspaceId, AdditionalQuestionsWorkflowReq body) {
        return ResponseModel.success(workflowRuntimeService.additionalQuestionsWorkflow(projectId, workflowId, conversationId, workspaceId, body));
    }
}