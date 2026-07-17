/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.service;

import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;


/**
 * WorkflowRuntime service
 */

public interface IWorkflowRuntimeService {

    /**
     * abortConversation
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param conversationId conversationId
     */
    Status abortConversation(String projectId, String workflowId, String conversationId) ;

    /**
     * additionalQuestionsWorkflow
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param conversationId conversationId
     * @param workspaceId workspaceId
     * @param body body
     */
    AutoAddResultJsonObject additionalQuestionsWorkflow(String projectId, String workflowId, String conversationId, String workspaceId, AdditionalQuestionsWorkflowReq body) ;
}