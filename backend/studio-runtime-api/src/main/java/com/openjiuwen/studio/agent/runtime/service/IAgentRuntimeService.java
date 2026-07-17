/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.service;

import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.dto.ReleaseInfo;

import org.springframework.web.multipart.MultipartFile;


/**
 * AgentRuntime service
 */

public interface IAgentRuntimeService {

    /**
     * additionalQuestions
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param workspaceId workspaceId
     * @param body body
     */
    AutoAddResultJsonObject additionalQuestions(String projectId, String agentId, String conversationId, String workspaceId, AdditionalQuestionsReq body) ;

    /**
     * createReleaseInfo
     *
     * @param projectId projectId
     * @param workspaceId workspaceId
     * @param body body
     */
    String createReleaseInfo(String projectId, String workspaceId, ReleaseInfo body) ;

    /**
     * delegateExchangeToken
     *
     * @param projectId projectId
     * @param authProjectId authProjectId
     * @param authDomainId authDomainId
     */
    String delegateExchangeToken(String projectId, String authProjectId, String authDomainId) ;

    /**
     * deleteReleaseInfo
     *
     * @param projectId projectId
     * @param releaseId releaseId
     * @param channelType channelType
     * @param versionId versionId
     */
    String deleteReleaseInfo(String projectId, String releaseId, String channelType, String versionId) ;

    /**
     * voiceRecognition
     *
     * @param projectId projectId
     * @param body body
     */
    AsrRsp voiceRecognition(String projectId, AsrReq body) ;
}