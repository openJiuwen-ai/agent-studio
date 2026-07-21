/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.controller;

import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.agent.ConversionQueries;
import com.openjiuwen.studio.agent.common.dto.agent.Feedback;
import com.openjiuwen.studio.agent.runtime.dto.GetMemoryChunksQo;
import com.openjiuwen.studio.agent.runtime.dto.MemoryChunk;
import com.openjiuwen.studio.agent.runtime.dto.MemoryVariable;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationMemoryQo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.runtime.service.IConversationManagementService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;


/**
 * ConversationManagement controller
 */
@RestController

public class ConversationManagementApiController implements ConversationManagementApi {
    private static final Logger log = LoggerFactory.getLogger(ConversationManagementApiController.class);

    @Autowired
    private IConversationManagementService conversationManagementService;

    @Override
    public ResponseEntity<String> createUserFeedback(String projectId, String appId, String conversationId, String messageId, String appType, String versionId, Feedback body) {
        return ResponseModel.success(conversationManagementService.createUserFeedback(projectId, appId, conversationId, messageId, appType, versionId, body));
    }

    @Override
    public ResponseEntity<ConversationDeleteResp> deleteConversation(String projectId, String agentId, String conversationId, String versionId) {
        return ResponseModel.success(conversationManagementService.deleteConversation(projectId, agentId, conversationId, versionId));
    }

    @Override
    public ResponseEntity<ConversationDeleteResp> deleteFeedback(String projectId, String appId, String conversationId, String messageId, String versionId) {
        return ResponseModel.success(conversationManagementService.deleteFeedback(projectId, appId, conversationId, messageId, versionId));
    }

    @Override
    public ResponseEntity<ConversationDeleteResp> deleteMemoryChunks(String projectId, String agentId, String conversationId, Integer chunkId) {
        return ResponseModel.success(conversationManagementService.deleteMemoryChunks(projectId, agentId, conversationId, chunkId));
    }

    @Override
    public ResponseEntity<MemoryChunk> generateMemoryChunk(String projectId, String agentId, String conversationId, Long start, Long end, Integer offset, Integer limit, String versionId, String workspaceId) {
        return ResponseModel.success(conversationManagementService.generateMemoryChunk(projectId, agentId, conversationId, start, end, offset, limit, versionId, workspaceId));
    }

    @Override
    public ResponseEntity<AutoAddResultJsonObject> getMemoryChunks(String projectId, String agentId, String conversationId, GetMemoryChunksQo getMemoryChunksQo) {
        return ResponseModel.success(conversationManagementService.getMemoryChunks(projectId, agentId, conversationId, getMemoryChunksQo));
    }

    @Override
    public ResponseEntity<List<MemoryVariable>> resetConversationMemory(String projectId, String conversationId, String agentId, String versionId) {
        return ResponseModel.success(conversationManagementService.resetConversationMemory(projectId, conversationId, agentId, versionId));
    }

    @Override
    public ResponseEntity<List<Message>> retrieveConversation(String projectId, String agentId, String conversationId, RetrieveConversationQo retrieveConversationQo) {
        return ResponseModel.success(conversationManagementService.retrieveConversation(projectId, agentId, conversationId, retrieveConversationQo));
    }

    @Override
    public ResponseEntity<List<MemoryVariable>> retrieveConversationMemory(String projectId, String agentId, String conversationId, RetrieveConversationMemoryQo retrieveConversationMemoryQo) {
        return ResponseModel.success(conversationManagementService.retrieveConversationMemory(projectId, agentId, conversationId, retrieveConversationMemoryQo));
    }
}