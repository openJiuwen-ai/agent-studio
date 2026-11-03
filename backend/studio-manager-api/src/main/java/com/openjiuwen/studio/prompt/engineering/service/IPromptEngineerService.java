/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service;

import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptTaskRsp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptTaskIterEvalResQo;
import com.openjiuwen.studio.prompt.engineering.dto.ListPromptTasksQo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseInfo;
import com.openjiuwen.studio.prompt.engineering.dto.PromptBaseResp;
import com.openjiuwen.studio.prompt.engineering.dto.PromptTaskCreateReq;

/**
 * PromptEngineer service
 */

public interface IPromptEngineerService {

    /**
     * copyPromptTask
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    CreatePromptTaskRsp copyPromptTask(String projectId, String taskId, String workspaceId);

    /**
     * createPromptTask
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    CreatePromptTaskRsp createPromptTask(String projectId, String taskId, String workspaceId);

    /**
     * createPromptTaskDraft
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    CreatePromptTaskRsp createPromptTaskDraft(String projectId, String workspaceId, PromptTaskCreateReq body);

    /**
     * deletePromptTask
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    PromptBaseInfo deletePromptTask(String projectId, String taskId, String workspaceId);

    /**
     * getPromptTask
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    PromptBaseResp getPromptTask(String projectId, String taskId, String workspaceId);

    /**
     * getPromptTaskIterEvalRes
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param iterNum iterNum
     * @param getPromptTaskIterEvalResQo getPromptTaskIterEvalResQo
     */
    PromptBaseResp getPromptTaskIterEvalRes(String projectId, String taskId, String iterNum, GetPromptTaskIterEvalResQo getPromptTaskIterEvalResQo);

    /**
     * listPromptTasks
     *
     * @param projectId projectId
     * @param listPromptTasksQo listPromptTasksQo
     */
    PromptBaseResp listPromptTasks(String projectId, ListPromptTasksQo listPromptTasksQo);

    /**
     * pausePromptTask
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    PromptBaseInfo pausePromptTask(String projectId, String taskId, String workspaceId);

    /**
     * resumePromptTask
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    PromptBaseInfo resumePromptTask(String projectId, String taskId, String workspaceId);

    /**
     * updatePromptTaskDraft
     *
     * @param projectId projectId
     * @param taskId taskId
     * @param workspaceId workspaceId
     * @param body body
     */
    PromptBaseResp updatePromptTaskDraft(String projectId, String taskId, String workspaceId, PromptTaskCreateReq body);
}
