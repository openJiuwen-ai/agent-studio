/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.dto.TriggerConfig;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
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

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * AgentManagement service
 */

public interface IAgentManagementService {

    /**
     * addTrigger
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param body body
     */
    TriggerConfig addTrigger(String projectId, String agentId, String workspaceId, TriggerConfig body);

    /**
     * autoAddStudioResource
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param agentId agentId
     * @param body body
     */
    AutoAddResultJsonObject autoAddStudioResource(String projectId, String workspaceId, String agentId,
        AutoAddStudioResourceRequestBody body);

    /**
     * copyAgent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param targetWorkspaceId targetWorkspaceId
     */
    AgentInfo copyAgent(String projectId, String agentId, String workspaceId, String targetWorkspaceId);

    /**
     * createAgent
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    AgentInfo createAgent(String projectId, String workspaceId, CreateAgentReq body);

    /**
     * createAgentChannel
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param body body
     */
    VersionChannelInfo createAgentChannel(String projectId, String agentId, String workspaceId, CreateChannelReq body);

    /**
     * createAgentVersion
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param body body
     */
    Void createAgentVersion(String projectId, String agentId, String workspaceId, CreateVersionReq body);

    /**
     * createAgentVersionV1
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param body body
     */
    Void createAgentVersionV1(String projectId, String agentId, String workspaceId, CreateVersionReq body);

    /**
     * deleteAgent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deleteAgent(String projectId, String agentId, String workspaceId);

    /**
     * deleteAgentChannel
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param channelId channelId
     * @param workspaceId workspaceId
     */
    Void deleteAgentChannel(String projectId, String agentId, String channelId, String workspaceId);

    /**
     * deleteAgentVersion
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param versionId versionId
     * @param workspaceId workspaceId
     */
    CommonDeleteRsp deleteAgentVersion(String projectId, String agentId, String versionId, String workspaceId);

    /**
     * deleteTrigger
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param triggerId triggerId
     * @param workspaceId workspaceId
     */
    Void deleteTrigger(String projectId, String agentId, String triggerId, String workspaceId);

    /**
     * editTrigger
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param body body
     */
    TriggerConfig editTrigger(String projectId, String agentId, String workspaceId, TriggerConfig body);

    /**
     * exportAgents
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Resource exportAgents(String projectId, String workspaceId, ExportParams body);

    /**
     * exportResource
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param accept accept
     * @param body body
     */
    ExportResourceRsp exportResource(String projectId, String workspaceId, String accept, ExportResourceParams body);

    /**
     * exportTools
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    Resource exportTools(String projectId, String workspaceId, ExportParams body);

    /**
     * generateAgentDescription
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    AutoAddResultJsonObject generateAgentDescription(String projectId, String agentId, String workspaceId);

    /**
     * generateAgentIcons
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    AutoAddResultJsonObject generateAgentIcons(String projectId, String workspaceId, CreateAgentReq body);

    /**
     * generateAgentName
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    AutoAddResultJsonObject generateAgentName(String projectId, String agentId, String workspaceId);

    /**
     * generateAgentPrologue
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    AutoAddResultJsonObject generateAgentPrologue(String projectId, String agentId, String workspaceId);

    /**
     * getAgentApplications
     *
     * @param projectId projectId
     * @param body body
     */
    AgentApplicationListRsp getAgentApplications(String projectId, ApplicationListReq body);

    /**
     * getAgentVersion
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param versionId versionId
     * @param getAgentVersionQo getAgentVersionQo
     */
    AgentInfo getAgentVersion(String projectId, String agentId, String versionId, GetAgentVersionQo getAgentVersionQo);

    /**
     * getPermissionsByRole
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     */
    Map<String, List<String>> getPermissionsByRole(String projectId, String workspaceId);

    /**
     * importAgents
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     * @param importAgents importAgents
     * @param importTools importTools
     * @param importWorkflows importWorkflows
     * @param mode mode
     */
    ImportRsp importAgents(String workspaceId, String projectId, MultipartFile file, String importAgents,
        String importTools, String importWorkflows, String mode);

    /**
     * importTools
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     * @param importIds importIds
     */
    ImportRsp importTools(String workspaceId, String projectId, MultipartFile file, String importIds);

    /**
     * listAgentApplications
     *
     * @param projectId projectId
     * @param listAgentApplicationsQo listAgentApplicationsQo
     */
    AgentApplicationListRsp listAgentApplications(String projectId, ListAgentApplicationsQo listAgentApplicationsQo);

    /**
     * listAgentChannels
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param listAgentChannelsQo listAgentChannelsQo
     */
    VersionChannelListRsp listAgentChannels(String projectId, String agentId, ListAgentChannelsQo listAgentChannelsQo);

    /**
     * listAgentLastVersions
     *
     * @param projectId projectId
     * @param listAgentLastVersionsQo listAgentLastVersionsQo
     */
    AgentVersionListRsp listAgentLastVersions(String projectId, ListAgentLastVersionsQo listAgentLastVersionsQo);

    /**
     * listAgentVersions
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param listAgentVersionsQo listAgentVersionsQo
     */
    VersionListRsp listAgentVersions(String projectId, String agentId, ListAgentVersionsQo listAgentVersionsQo);

    /**
     * listAgentVersionsV1
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param listAgentVersionsV1Qo listAgentVersionsV1Qo
     */
    VersionListRsp listAgentVersionsV1(String projectId, String agentId, ListAgentVersionsV1Qo listAgentVersionsV1Qo);

    /**
     * listAgents
     *
     * @param projectId projectId
     * @param listAgentsQo listAgentsQo
     */
    AgentListRsp listAgents(String projectId, ListAgentsQo listAgentsQo);

    /**
     * listImportFile
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param file file
     * @param offset offset
     * @param limit limit
     */
    List<ImportListInfo> listImportFile(String workspaceId, String projectId, MultipartFile file, Integer offset,
        Integer limit);

    /**
     * modifyAgent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     * @param body body
     */
    AgentInfo modifyAgent(String projectId, String agentId, String workspaceId, ModifyAgentReq body);

    /**
     * modifyAgentChannel
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param channelId channelId
     * @param workspaceId workspaceId
     * @param body body
     */
    VersionChannelInfo modifyAgentChannel(String projectId, String agentId, String channelId, String workspaceId,
        ModifyChannelReq body);

    /**
     * recommendedAgentQuestions
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    AutoAddResultJsonObject recommendedAgentQuestions(String projectId, String agentId, String workspaceId);

    /**
     * retrieveAgent
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    AgentInfo retrieveAgent(String projectId, String agentId, String workspaceId);

    /**
     * retrieveAgentApp
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param workspaceId workspaceId
     */
    AgentInfo retrieveAgentApp(String projectId, String agentId, String workspaceId);

    /**
     * uploadDeepResearchTemplate
     *
     * @param workspaceId workspaceId
     * @param projectId projectId
     * @param agentId agentId
     * @param file file
     */
    FileUploadRsp uploadDeepResearchTemplate(String workspaceId, String projectId, String agentId, MultipartFile file) ;
}