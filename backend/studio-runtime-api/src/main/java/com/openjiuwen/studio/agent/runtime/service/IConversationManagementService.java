/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */


package com.openjiuwen.studio.agent.runtime.service;

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

import java.util.List;


/**
 * ConversationManagement service
 */

public interface IConversationManagementService {

    /**
     * createUserFeedback
     *
     * @param projectId projectId
     * @param appId appId
     * @param conversationId conversationId
     * @param messageId messageId
     * @param appType appType
     * @param versionId versionId
     * @param body body
     */
    String createUserFeedback(String projectId, String appId, String conversationId, String messageId, String appType, String versionId, Feedback body) ;

    /**
     * deleteConversation
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param versionId versionId
     */
    ConversationDeleteResp deleteConversation(String projectId, String agentId, String conversationId, String versionId) ;

    /**
     * deleteFeedback
     *
     * @param projectId projectId
     * @param appId appId
     * @param conversationId conversationId
     * @param messageId messageId
     * @param versionId versionId
     */
    ConversationDeleteResp deleteFeedback(String projectId, String appId, String conversationId, String messageId, String versionId) ;

    /**
     * deleteMemoryChunks
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param chunkId chunkId
     */
    ConversationDeleteResp deleteMemoryChunks(String projectId, String agentId, String conversationId, Integer chunkId) ;

    /**
     * generateMemoryChunk
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param start start
     * @param end end
     * @param offset offset
     * @param limit limit
     * @param versionId versionId
     * @param workspaceId workspaceId
     */
    MemoryChunk generateMemoryChunk(String projectId, String agentId, String conversationId, Long start, Long end, Integer offset, Integer limit, String versionId, String workspaceId) ;

    /**
     * getMemoryChunks
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param getMemoryChunksQo getMemoryChunksQo
     */
    AutoAddResultJsonObject getMemoryChunks(String projectId, String agentId, String conversationId, GetMemoryChunksQo getMemoryChunksQo) ;

    /**
     * resetConversationMemory
     *
     * @param projectId projectId
     * @param conversationId conversationId
     * @param agentId agentId
     * @param versionId versionId
     */
    List<MemoryVariable> resetConversationMemory(String projectId, String conversationId, String agentId, String versionId) ;

    /**
     * retrieveConversation
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param retrieveConversationQo retrieveConversationQo
     */
    List<Message> retrieveConversation(String projectId, String agentId, String conversationId, RetrieveConversationQo retrieveConversationQo) ;

    /**
     * retrieveConversationMemory
     *
     * @param projectId projectId
     * @param agentId agentId
     * @param conversationId conversationId
     * @param retrieveConversationMemoryQo retrieveConversationMemoryQo
     */
    List<MemoryVariable> retrieveConversationMemory(String projectId, String agentId, String conversationId, RetrieveConversationMemoryQo retrieveConversationMemoryQo) ;
}