/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;

import java.util.List;

/**
 * ConversationHistory service
 */
public interface IConversationHistoryService {

    ConversationDeleteResp deleteConversationHistory(String projectId, String agentId,
        String conversationId, String versionId, String workspaceId);

    List<Message> retrieveConversationHistory(String projectId, String agentId,
        String conversationId, RetrieveConversationQo retrieveConversationQo, String workspaceId);
}
