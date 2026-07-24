/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.dto.AgentApplicationListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentInfo;
import com.openjiuwen.studio.agent.manager.dto.AgentListRsp;
import com.openjiuwen.studio.agent.manager.dto.AgentVersionListRsp;
import com.openjiuwen.studio.agent.manager.dto.ApplicationListReq;
import com.openjiuwen.studio.agent.manager.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.manager.dto.AutoAddStudioResourceRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CommonDeleteRsp;
import com.openjiuwen.studio.agent.manager.dto.CreateAgentReq;
import com.openjiuwen.studio.agent.manager.dto.CreateChannelReq;
import com.openjiuwen.studio.agent.manager.dto.CreateVersionReq;
import com.openjiuwen.studio.agent.manager.dto.ExportParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceParams;
import com.openjiuwen.studio.agent.manager.dto.ExportResourceRsp;
import com.openjiuwen.studio.agent.manager.dto.GetAgentVersionQo;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.ListAgentApplicationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentChannelsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentLastVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsQo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentVersionsV1Qo;
import com.openjiuwen.studio.agent.manager.dto.ListAgentsQo;
import com.openjiuwen.studio.agent.manager.dto.ModifyAgentReq;
import com.openjiuwen.studio.agent.manager.dto.ModifyChannelReq;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelInfo;
import com.openjiuwen.studio.agent.manager.dto.VersionChannelListRsp;
import com.openjiuwen.studio.agent.manager.dto.VersionListRsp;
import com.openjiuwen.studio.agent.manager.service.IAgentManagementService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * AgentManagement controller
 */
@RestController
public class AgentManagementApiController implements AgentManagementApi {
    private static final Logger log = LoggerFactory.getLogger(AgentManagementApiController.class);

    @Autowired
    private IAgentManagementService agentManagementService;

    @Override
    public ResponseEntity<TriggerConfig> addTrigger(String projectId, String agentId, String workspaceId,
        TriggerConfig body) {
        return ResponseModel.success(agentManagementService.addTrigger(projectId, agentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> autoAddStudioResource(String projectId, String workspaceId,
        String agentId, AutoAddStudioResourceRequestBody body) {
        return ResponseModel.success(
            agentManagementService.autoAddStudioResource(projectId, workspaceId, agentId, body));
    }

    @Override
    public ResponseEntity<AgentInfo> copyAgent(String projectId, String agentId, String workspaceId,
        String targetWorkspaceId) {
        return ResponseModel.success(
            agentManagementService.copyAgent(projectId, agentId, workspaceId, targetWorkspaceId));
    }

    @Override
    public ResponseEntity<AgentInfo> createAgent(String projectId, String workspaceId, CreateAgentReq body) {
        return ResponseModel.success(agentManagementService.createAgent(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<VersionChannelInfo> createAgentChannel(String projectId, String agentId, String workspaceId,
        CreateChannelReq body) {
        return ResponseModel.success(agentManagementService.createAgentChannel(projectId, agentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Void> createAgentVersion(String projectId, String agentId, String workspaceId,
        CreateVersionReq body) {
        return ResponseModel.success(agentManagementService.createAgentVersion(projectId, agentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Void> createAgentVersionV1(String projectId, String agentId, String workspaceId,
        CreateVersionReq body) {
        return ResponseModel.success(
            agentManagementService.createAgentVersionV1(projectId, agentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deleteAgent(String projectId, String agentId, String workspaceId) {
        return ResponseModel.success(agentManagementService.deleteAgent(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<Void> deleteAgentChannel(String projectId, String agentId, String channelId,
        String workspaceId) {
        return ResponseModel.success(
            agentManagementService.deleteAgentChannel(projectId, agentId, channelId, workspaceId));
    }

    @Override
    public ResponseEntity<CommonDeleteRsp> deleteAgentVersion(String projectId, String agentId, String versionId,
        String workspaceId) {
        return ResponseModel.success(
            agentManagementService.deleteAgentVersion(projectId, agentId, versionId, workspaceId));
    }

    @Override
    public ResponseEntity<Void> deleteTrigger(String projectId, String agentId, String triggerId, String workspaceId) {
        return ResponseModel.success(agentManagementService.deleteTrigger(projectId, agentId, triggerId, workspaceId));
    }

    @Override
    public ResponseEntity<TriggerConfig> editTrigger(String projectId, String agentId, String workspaceId,
        TriggerConfig body) {
        return ResponseModel.success(agentManagementService.editTrigger(projectId, agentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<Resource> exportAgents(String projectId, String workspaceId, ExportParams body) {
        return ResponseModel.successDownload(agentManagementService.exportAgents(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<ExportResourceRsp> exportResource(String projectId, String workspaceId, String accept,
        ExportResourceParams body) {
        return ResponseModel.success(agentManagementService.exportResource(projectId, workspaceId, accept, body));
    }

    @Override
    public ResponseEntity<Resource> exportTools(String projectId, String workspaceId, ExportParams body) {
        return ResponseModel.successDownload(agentManagementService.exportTools(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> generateAgentDescription(String projectId, String agentId,
        String workspaceId) {
        return ResponseModel.success(agentManagementService.generateAgentDescription(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> generateAgentIcons(String projectId, String workspaceId,
        CreateAgentReq body) {
        return ResponseModel.success(agentManagementService.generateAgentIcons(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> generateAgentName(String projectId, String agentId,
        String workspaceId) {
        return ResponseModel.success(agentManagementService.generateAgentName(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> generateAgentPrologue(String projectId, String agentId,
        String workspaceId) {
        return ResponseModel.success(agentManagementService.generateAgentPrologue(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<AgentApplicationListRsp> getAgentApplications(String projectId, ApplicationListReq body) {
        return ResponseModel.success(agentManagementService.getAgentApplications(projectId, body));
    }

    @Override
    public ResponseEntity<AgentInfo> getAgentVersion(String projectId, String agentId, String versionId,
        GetAgentVersionQo getAgentVersionQo) {
        return ResponseModel.success(
            agentManagementService.getAgentVersion(projectId, agentId, versionId, getAgentVersionQo));
    }

    @Override
    public ResponseEntity<Map<String, List<String>>> getPermissionsByRole(String projectId, String workspaceId) {
        return ResponseModel.success(agentManagementService.getPermissionsByRole(projectId, workspaceId));
    }

    @Override
    public ResponseEntity<ImportRsp> importAgents(String workspaceId, String projectId, MultipartFile file,
        String importAgents, String importTools, String importWorkflows, String mode) {
        return ResponseModel.success(
            agentManagementService.importAgents(workspaceId, projectId, file, importAgents, importTools,
                importWorkflows, mode));
    }

    @Override
    public ResponseEntity<ImportRsp> importTools(String workspaceId, String projectId, MultipartFile file,
        String importIds) {
        return ResponseModel.success(agentManagementService.importTools(workspaceId, projectId, file, importIds));
    }

    @Override
    public ResponseEntity<AgentApplicationListRsp> listAgentApplications(String projectId,
        ListAgentApplicationsQo listAgentApplicationsQo) {
        return ResponseModel.success(agentManagementService.listAgentApplications(projectId, listAgentApplicationsQo));
    }

    @Override
    public ResponseEntity<VersionChannelListRsp> listAgentChannels(String projectId, String agentId,
        ListAgentChannelsQo listAgentChannelsQo) {
        return ResponseModel.success(agentManagementService.listAgentChannels(projectId, agentId, listAgentChannelsQo));
    }

    @Override
    public ResponseEntity<AgentVersionListRsp> listAgentLastVersions(String projectId,
        ListAgentLastVersionsQo listAgentLastVersionsQo) {
        return ResponseModel.success(agentManagementService.listAgentLastVersions(projectId, listAgentLastVersionsQo));
    }

    @Override
    public ResponseEntity<VersionListRsp> listAgentVersions(String projectId, String agentId,
        ListAgentVersionsQo listAgentVersionsQo) {
        return ResponseModel.success(agentManagementService.listAgentVersions(projectId, agentId, listAgentVersionsQo));
    }

    @Override
    public ResponseEntity<VersionListRsp> listAgentVersionsV1(String projectId, String agentId,
        ListAgentVersionsV1Qo listAgentVersionsV1Qo) {
        return ResponseModel.success(
            agentManagementService.listAgentVersionsV1(projectId, agentId, listAgentVersionsV1Qo));
    }

    @Override
    public ResponseEntity<AgentListRsp> listAgents(String projectId, ListAgentsQo listAgentsQo) {
        return ResponseModel.success(agentManagementService.listAgents(projectId, listAgentsQo));
    }

    @Override
    public ResponseEntity<List<ImportListInfo>> listImportFile(String workspaceId, String projectId, MultipartFile file,
        Integer offset, Integer limit) {
        return ResponseModel.success(
            agentManagementService.listImportFile(workspaceId, projectId, file, offset, limit));
    }

    @Override
    public ResponseEntity<AgentInfo> modifyAgent(String projectId, String agentId, String workspaceId,
        ModifyAgentReq body) {
        return ResponseModel.success(agentManagementService.modifyAgent(projectId, agentId, workspaceId, body));
    }

    @Override
    public ResponseEntity<VersionChannelInfo> modifyAgentChannel(String projectId, String agentId, String channelId,
        String workspaceId, ModifyChannelReq body) {
        return ResponseModel.success(
            agentManagementService.modifyAgentChannel(projectId, agentId, channelId, workspaceId, body));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> recommendedAgentQuestions(String projectId, String agentId,
        String workspaceId) {
        return ResponseModel.success(agentManagementService.recommendedAgentQuestions(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<AgentInfo> retrieveAgent(String projectId, String agentId, String workspaceId) {
        return ResponseModel.success(agentManagementService.retrieveAgent(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<AgentInfo> retrieveAgentApp(String projectId, String agentId, String workspaceId) {
        return ResponseModel.success(agentManagementService.retrieveAgentApp(projectId, agentId, workspaceId));
    }

    @Override
    public ResponseEntity<FileUploadRsp> uploadDeepResearchTemplate(String workspaceId, String projectId, String agentId, MultipartFile file) {
        return ResponseModel.success(agentManagementService.uploadDeepResearchTemplate(workspaceId, projectId, agentId, file));
    }
}