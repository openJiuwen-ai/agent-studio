/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.ExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.ExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.run.GetExecutionInsightQo;
import com.openjiuwen.studio.agent.common.dto.run.ListConversationQueriesQo;
import com.openjiuwen.studio.agent.common.dto.run.ListExecutionQueriesQo;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.service.IWorkflowRuntimeService;

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
    public ResponseEntity<ExecutionInfo> getExecutionInsight(String projectId, String workflowId, String executionId, GetExecutionInsightQo getExecutionInsightQo) {
        return ResponseModel.success(workflowRuntimeService.getExecutionInsight(projectId, workflowId, executionId, getExecutionInsightQo));
    }

    @Override
    public ResponseEntity<ConversionQueries> listConversationQueries(String projectId, String workflowId, ListConversationQueriesQo listConversationQueriesQo) {
        return ResponseModel.success(workflowRuntimeService.listConversationQueries(projectId, workflowId, listConversationQueriesQo));
    }

    @Override
    public ResponseEntity<ExecutionQueries> listExecutionQueries(String projectId, String workflowId, String conversationId, ListExecutionQueriesQo listExecutionQueriesQo) {
        return ResponseModel.success(workflowRuntimeService.listExecutionQueries(projectId, workflowId, conversationId, listExecutionQueriesQo));
    }
}
