/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CopyWorkflowQo;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowEnvsQo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowParamsQo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkflowVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionsV1Qo;
import com.openjiuwen.studio.agent.common.dto.agent.ListWorkflowsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.manager.dto.ValidateWorkflowQo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkFlowEnvs;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFrontParamInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.common.dto.run.WorkflowListRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowSceneRsp;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVersionListRsp;

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

/**
 * WorkflowManagement service
 */

public interface IWorkflowManagementService {

    /**
     * addTrigger
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param body body
     */
    TriggerConfig addTrigger(String projectId, String workflowId, String workspaceId, TriggerConfig body);

    /**
     * copyWorkflow
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param copyWorkflowQo copyWorkflowQo
     */
    WorkflowInfo copyWorkflow(String projectId, String workflowId, CopyWorkflowQo copyWorkflowQo);

    /**
     * createWorkflow
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    WorkflowInfo createWorkflow(String projectId, String workspaceId, WorkflowInfo body);

    /**
     * createWorkflowChannel
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param body body
     */
    VersionChannelInfo createWorkflowChannel(String projectId, String workflowId, String workspaceId,
        CreateChannelReq body);

    /**
     * deleteTrigger
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param triggerId triggerId
     * @param workspaceId workspaceId
     */
    Void deleteTrigger(String projectId, String workflowId, String triggerId, String workspaceId);

    /**
     * deleteWorkflow
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deleteWorkflow(String projectId, String workflowId, String workspaceId);

    /**
     * deleteWorkflowChannel
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param channelId channelId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deleteWorkflowChannel(String projectId, String workflowId, String channelId, String workspaceId);

    /**
     * deleteWorkflowVersion
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param versionId versionId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deleteWorkflowVersion(String projectId, String workflowId, String versionId, String workspaceId);

    /**
     * editTrigger
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param body body
     */
    TriggerConfig editTrigger(String projectId, String workflowId, String workspaceId, TriggerConfig body);

    /**
     * exportWorkflows
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Resource exportWorkflows(String projectId, String workspaceId, ExportParams body);

    /**
     * generateWorkflowPrologue
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     */
    AutoAddResultJsonObject generateWorkflowPrologue(String projectId, String workflowId, String workspaceId);

    /**
     * getWorkflow
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     */
    WorkflowInfo getWorkflow(String projectId, String workflowId, String workspaceId);

    /**
     * getWorkflowEnvs
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param getWorkflowEnvsQo getWorkflowEnvsQo
     */
    WorkFlowEnvs getWorkflowEnvs(String projectId, String workflowId, GetWorkflowEnvsQo getWorkflowEnvsQo);

    /**
     * getWorkflowParams
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param getWorkflowParamsQo getWorkflowParamsQo
     */
    WorkflowFrontParamInfo getWorkflowParams(String projectId, String workflowId,
        GetWorkflowParamsQo getWorkflowParamsQo);

    /**
     * getWorkflowScene
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     */
    WorkflowSceneRsp getWorkflowScene(String projectId, String workflowId, String workspaceId);

    /**
     * getWorkflowVersion
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param versionId versionId
     * @param nestedCheck nestedCheck
     * @param getWorkflowVersionQo getWorkflowVersionQo
     */
    WorkflowInfo getWorkflowVersion(String projectId, String workflowId, String versionId, Boolean nestedCheck,
        GetWorkflowVersionQo getWorkflowVersionQo);

    /**
     * importWorkflows
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     * @param importWorkflows importWorkflows
     * @param importTools importTools
     * @param mode mode
     */
    ImportRsp importWorkflows(String workspaceId, String projectId, MultipartFile file, String importWorkflows,
        String importTools, String mode);

    /**
     * listWorkflowChannels
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param listWorkflowChannelsQo listWorkflowChannelsQo
     */
    VersionChannelListRsp listWorkflowChannels(String projectId, String workflowId,
        ListWorkflowChannelsQo listWorkflowChannelsQo);

    /**
     * listWorkflowLastVersions
     *
     * @param projectId projectId
     * @param listWorkflowLastVersionsQo listWorkflowLastVersionsQo
     */
    WorkflowVersionListRsp listWorkflowLastVersions(String projectId,
        ListWorkflowLastVersionsQo listWorkflowLastVersionsQo);

    /**
     * listWorkflowVersions
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param listWorkflowVersionsQo listWorkflowVersionsQo
     */
    VersionListRsp listWorkflowVersions(String projectId, String workflowId,
        ListWorkflowVersionsQo listWorkflowVersionsQo);

    /**
     * listWorkflowVersionsV1
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param listWorkflowVersionsV1Qo listWorkflowVersionsV1Qo
     */
    VersionListRsp listWorkflowVersionsV1(String projectId, String workflowId,
        ListWorkflowVersionsV1Qo listWorkflowVersionsV1Qo);

    /**
     * listWorkflows
     *
     * @param projectId projectId
     * @param listWorkflowsQo listWorkflowsQo
     */
    WorkflowListRsp listWorkflows(String projectId, ListWorkflowsQo listWorkflowsQo);

    /**
     * modifyWorkflowChannel
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param channelId channelId
     * @param workspaceId workspaceId
     * @param body body
     */
    VersionChannelInfo modifyWorkflowChannel(String projectId, String workflowId, String channelId, String workspaceId,
        ModifyChannelReq body);

    /**
     * parseThirdpartyWorkflowFile
     *
     * @param type type
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     */
    WorkflowInfo parseThirdpartyWorkflowFile(String type, String workspaceId, String projectId, MultipartFile file);

    /**
     * recommendedWorkflowQuestions
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     */
    AutoAddResultJsonObject recommendedWorkflowQuestions(String projectId, String workflowId, String workspaceId);

    /**
     * releaseWorkflowVersion
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param body body
     */
    String releaseWorkflowVersion(String projectId, String workflowId, String workspaceId, CreateVersionReq body);

    /**
     * releaseWorkflowVersionV1
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param body body
     */
    String releaseWorkflowVersionV1(String projectId, String workflowId, String workspaceId, CreateVersionReq body);

    /**
     * setWorkflowTestStatus
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param success success
     */
    WorkflowInfo setWorkflowTestStatus(String projectId, String workflowId, String workspaceId, Boolean success);

    /**
     * updateWorkflow
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param workspaceId workspaceId
     * @param body body
     */
    WorkflowInfo updateWorkflow(String projectId, String workflowId, String workspaceId, WorkflowInfo body);

    /**
     * validateWorkflow
     *
     * @param projectId projectId
     * @param workflowId workflowId
     * @param validateWorkflowQo validateWorkflowQo
     */
    WorkflowValidationVO validateWorkflow(String projectId, String workflowId, ValidateWorkflowQo validateWorkflowQo);
}