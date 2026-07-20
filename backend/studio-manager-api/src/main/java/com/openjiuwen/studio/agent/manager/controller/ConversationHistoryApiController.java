/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.controller;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.common.utils.ResponseModel;
import com.openjiuwen.studio.agent.manager.service.IConversationHistoryService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * ConversationHistory controller
 */
@RestController
public class ConversationHistoryApiController implements ConversationHistoryApi {
    private static final Logger log = LoggerFactory.getLogger(ConversationHistoryApiController.class);

    @Autowired
    private IConversationHistoryService conversationHistoryService;

    @Override
    public ResponseEntity<ConversationDeleteResp> deleteConversationHistory(
            String projectId, String agentId, String conversationId,
            String versionId, String workspaceId) {
        return ResponseModel.success(
            conversationHistoryService.deleteConversationHistory(projectId, agentId, conversationId, versionId, workspaceId));
    }

    @Override
    public ResponseEntity<List<Message>> retrieveConversationHistory(
            String projectId, String agentId, String conversationId,
            RetrieveConversationQo retrieveConversationQo, String workspaceId) {
        return ResponseModel.success(
            conversationHistoryService.retrieveConversationHistory(projectId, agentId, conversationId, retrieveConversationQo, workspaceId));
    }
}
