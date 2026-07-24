/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

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
import com.openjiuwen.studio.agent.manager.service.IWorkflowManagementService;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * WorkflowManagement controller
 */
@RestController

public class WorkflowManagementApiController implements WorkflowManagementApi {
    private static final Logger log = LoggerFactory.getLogger(WorkflowManagementApiController.class);

    @Autowired
    private IWorkflowManagementService workflowManagementService;

    @Override
    public ResponseEntity<TriggerConfig> addTrigger(String projectId, String workflowId, String workspaceId,
        TriggerConfig body) {
        return ResponseModel.success(workflowManagementService.addTrigger(projectId, workflowId, workspaceId, body));
    }

    @Override
    public ResponseEntity<WorkflowInfo> copyWorkflow(String projectId, String workflowId,
        CopyWorkflowQo copyWorkflowQo) {
        return ResponseModel.success(workflowManagementService.copyWorkflow(projectId, workflowId, copyWorkflowQo));
    }

    @Override
    public ResponseEntity<WorkflowInfo> createWorkflow(String projectId, String workspaceId, WorkflowInfo body) {
        return ResponseModel.success(workflowManagementService.createWorkflow(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<VersionChannelInfo> createWorkflowChannel(String projectId, String workflowId,
        String workspaceId, CreateChannelReq body) {
        return ResponseModel.success(
            workflowManagementService.createWorkflowChannel(projectId, workflowId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Void> deleteTrigger(String projectId, String workflowId, String triggerId,
        String workspaceId) {
        return ResponseModel.success(
            workflowManagementService.deleteTrigger(projectId, workflowId, triggerId, workspaceId));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deleteWorkflow(String projectId, String workflowId, String workspaceId) {
        return ResponseModel.success(workflowManagementService.deleteWorkflow(projectId, workflowId, workspaceId));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deleteWorkflowChannel(String projectId, String workflowId, String channelId,
        String workspaceId) {
        return ResponseModel.success(
            workflowManagementService.deleteWorkflowChannel(projectId, workflowId, channelId, workspaceId));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deleteWorkflowVersion(String projectId, String workflowId, String versionId,
        String workspaceId) {
        return ResponseModel.success(
            workflowManagementService.deleteWorkflowVersion(projectId, workflowId, versionId, workspaceId));
    }

    @Override
    public ResponseEntity<TriggerConfig> editTrigger(String projectId, String workflowId, String workspaceId,
        TriggerConfig body) {
        return ResponseModel.success(workflowManagementService.editTrigger(projectId, workflowId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Resource> exportWorkflows(String projectId, String workspaceId, ExportParams body) {
        return ResponseModel.successDownload(workflowManagementService.exportWorkflows(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> generateWorkflowPrologue(String projectId, String workflowId,
        String workspaceId) {
        return ResponseModel.success(
            workflowManagementService.generateWorkflowPrologue(projectId, workflowId, workspaceId));
    }

    @Override
    public ResponseEntity<WorkflowInfo> getWorkflow(String projectId, String workflowId, String workspaceId) {
        return ResponseModel.success(workflowManagementService.getWorkflow(projectId, workflowId, workspaceId));
    }

    @Override
    public ResponseEntity<WorkFlowEnvs> getWorkflowEnvs(String projectId, String workflowId,
        GetWorkflowEnvsQo getWorkflowEnvsQo) {
        return ResponseModel.success(
            workflowManagementService.getWorkflowEnvs(projectId, workflowId, getWorkflowEnvsQo));
    }

    @Override
    public ResponseEntity<WorkflowFrontParamInfo> getWorkflowParams(String projectId, String workflowId,
        GetWorkflowParamsQo getWorkflowParamsQo) {
        return ResponseModel.success(
            workflowManagementService.getWorkflowParams(projectId, workflowId, getWorkflowParamsQo));
    }

    @Override
    public ResponseEntity<WorkflowSceneRsp> getWorkflowScene(String projectId, String workflowId, String workspaceId) {
        return ResponseModel.success(workflowManagementService.getWorkflowScene(projectId, workflowId, workspaceId));
    }

    @Override
    public ResponseEntity<WorkflowInfo> getWorkflowVersion(String projectId, String workflowId, String versionId,
        Boolean nestedCheck, GetWorkflowVersionQo getWorkflowVersionQo) {
        return ResponseModel.success(
            workflowManagementService.getWorkflowVersion(projectId, workflowId, versionId, nestedCheck,
                getWorkflowVersionQo));
    }

    @Override
    public ResponseEntity<ImportRsp> importWorkflows(String workspaceId, String projectId, MultipartFile file,
        String importWorkflows, String importTools, String mode) {
        return ResponseModel.success(
            workflowManagementService.importWorkflows(workspaceId, projectId, file, importWorkflows, importTools,
                mode));
    }

    @Override
    public ResponseEntity<VersionChannelListRsp> listWorkflowChannels(String projectId, String workflowId,
        ListWorkflowChannelsQo listWorkflowChannelsQo) {
        return ResponseModel.success(
            workflowManagementService.listWorkflowChannels(projectId, workflowId, listWorkflowChannelsQo));
    }

    @Override
    public ResponseEntity<WorkflowVersionListRsp> listWorkflowLastVersions(String projectId,
        ListWorkflowLastVersionsQo listWorkflowLastVersionsQo) {
        return ResponseModel.success(
            workflowManagementService.listWorkflowLastVersions(projectId, listWorkflowLastVersionsQo));
    }

    @Override
    public ResponseEntity<VersionListRsp> listWorkflowVersions(String projectId, String workflowId,
        ListWorkflowVersionsQo listWorkflowVersionsQo) {
        return ResponseModel.success(
            workflowManagementService.listWorkflowVersions(projectId, workflowId, listWorkflowVersionsQo));
    }

    @Override
    public ResponseEntity<VersionListRsp> listWorkflowVersionsV1(String projectId, String workflowId,
        ListWorkflowVersionsV1Qo listWorkflowVersionsV1Qo) {
        return ResponseModel.success(
            workflowManagementService.listWorkflowVersionsV1(projectId, workflowId, listWorkflowVersionsV1Qo));
    }

    @Override
    public ResponseEntity<WorkflowListRsp> listWorkflows(String projectId, ListWorkflowsQo listWorkflowsQo) {
        return ResponseModel.success(workflowManagementService.listWorkflows(projectId, listWorkflowsQo));
    }

    @Override
    public ResponseEntity<VersionChannelInfo> modifyWorkflowChannel(String projectId, String workflowId,
        String channelId, String workspaceId, ModifyChannelReq body) {
        return ResponseModel.success(
            workflowManagementService.modifyWorkflowChannel(projectId, workflowId, channelId, workspaceId, body));
    }

    @Override
    public ResponseEntity<WorkflowInfo> parseThirdpartyWorkflowFile(String type, String workspaceId, String projectId,
        MultipartFile file) {
        return ResponseModel.success(
            workflowManagementService.parseThirdpartyWorkflowFile(type, workspaceId, projectId, file));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> recommendedWorkflowQuestions(String projectId, String workflowId,
        String workspaceId) {
        return ResponseModel.success(
            workflowManagementService.recommendedWorkflowQuestions(projectId, workflowId, workspaceId));
    }

    @Override
    public ResponseEntity<String> releaseWorkflowVersion(String projectId, String workflowId, String workspaceId,
        CreateVersionReq body) {
        return ResponseModel.success(
            workflowManagementService.releaseWorkflowVersion(projectId, workflowId, workspaceId, body));
    }

    @Override
    public ResponseEntity<String> releaseWorkflowVersionV1(String projectId, String workflowId, String workspaceId,
        CreateVersionReq body) {
        return ResponseModel.success(
            workflowManagementService.releaseWorkflowVersionV1(projectId, workflowId, workspaceId, body));
    }

    @Override
    public ResponseEntity<WorkflowInfo> setWorkflowTestStatus(String projectId, String workflowId, String workspaceId,
        Boolean success) {
        return ResponseModel.success(
            workflowManagementService.setWorkflowTestStatus(projectId, workflowId, workspaceId, success));
    }

    @Override
    public ResponseEntity<WorkflowInfo> updateWorkflow(String projectId, String workflowId, String workspaceId,
        WorkflowInfo body) {
        return ResponseModel.success(
            workflowManagementService.updateWorkflow(projectId, workflowId, workspaceId, body));
    }

    @Override
    public ResponseEntity<WorkflowValidationVO> validateWorkflow(String projectId, String workflowId,
        ValidateWorkflowQo validateWorkflowQo) {
        return ResponseModel.success(
            workflowManagementService.validateWorkflow(projectId, workflowId, validateWorkflowQo));
    }
}