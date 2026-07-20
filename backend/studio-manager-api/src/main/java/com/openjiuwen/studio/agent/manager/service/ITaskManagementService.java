/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.dto.run.CancelTaskRsp;
import com.openjiuwen.studio.agent.common.dto.run.CreateTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ListTaskQo;
import com.openjiuwen.studio.agent.common.dto.run.ModifyTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.ResumeTaskReq;
import com.openjiuwen.studio.agent.common.dto.run.TaskListRsp;
import com.openjiuwen.studio.agent.common.dto.run.TaskRsp;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveTaskQo;

/**
 * TaskManagement service
 */
public interface ITaskManagementService {
    /**
     * cancelTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    CancelTaskRsp cancelTask(String projectId, String workflowId, String taskId, String workspaceId);

    /**
     * createTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param version version
     * @param workspaceId workspaceId
     * @param body body
     */
    TaskRsp createTask(String projectId, String workflowId, String version, String workspaceId, CreateTaskReq body);

    /**
     * deleteTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param taskId taskId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deleteTask(String projectId, String workflowId, String taskId, String workspaceId);

    /**
     * listTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param listTaskQo listTaskQo
     */
    TaskListRsp listTask(String projectId, String workflowId, ListTaskQo listTaskQo);

    /**
     * modifyTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param taskId taskId
     * @param workspaceId workspaceId
     * @param body body
     */
    TaskRsp modifyTask(String projectId, String workflowId, String taskId, String workspaceId, ModifyTaskReq body);

    /**
     * resumeTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param taskId taskId
     * @param workspaceId workspaceId
     * @param body body
     */
    TaskRsp resumeTask(String projectId, String workflowId, String taskId, String workspaceId, ResumeTaskReq body);

    /**
     * retrieveTask
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param taskId taskId
     * @param retrieveTaskQo retrieveTaskQo
     */
    TaskRsp retrieveTask(String projectId, String workflowId, String taskId, RetrieveTaskQo retrieveTaskQo);
}