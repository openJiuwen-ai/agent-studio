/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.dto.ReleaseInfo;
import com.openjiuwen.studio.agent.runtime.service.IAgentRuntimeService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;


/**
 * AgentRuntime controller
 */
@RestController

public class AgentRuntimeApiController implements AgentRuntimeApi {
    private static final Logger log = LoggerFactory.getLogger(AgentRuntimeApiController.class);

    @Autowired
    private IAgentRuntimeService agentRuntimeService;

    @Override
    public ResponseEntity<AutoAddResultJsonObject> additionalQuestions(String projectId, String agentId, String conversationId, String workspaceId, AdditionalQuestionsReq body) {
        return ResponseModel.success(agentRuntimeService.additionalQuestions(projectId, agentId, conversationId, workspaceId, body));
    }

    @Override
    public ResponseEntity<String> createReleaseInfo(String projectId, String workspaceId, ReleaseInfo body) {
        return ResponseModel.success(agentRuntimeService.createReleaseInfo(projectId, workspaceId, body));
    }

    @Override
    public ResponseEntity<String> delegateExchangeToken(String projectId, String authProjectId, String authDomainId) {
        return ResponseModel.success(agentRuntimeService.delegateExchangeToken(projectId, authProjectId, authDomainId));
    }

    @Override
    public ResponseEntity<String> deleteReleaseInfo(String projectId, String releaseId, String channelType, String versionId) {
        return ResponseModel.success(agentRuntimeService.deleteReleaseInfo(projectId, releaseId, channelType, versionId));
    }

    @Override
    public ResponseEntity<AsrRsp> voiceRecognition(String projectId, AsrReq body) {
        return ResponseModel.success(agentRuntimeService.voiceRecognition(projectId, body));
    }
}