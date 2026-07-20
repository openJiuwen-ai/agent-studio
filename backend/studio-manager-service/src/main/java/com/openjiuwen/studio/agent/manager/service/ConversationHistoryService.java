/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constant;
import com.openjiuwen.studio.agent.manager.dto.ConversationParams;
import com.openjiuwen.studio.agent.manager.model.Conversation;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * 会话历史服务，直接操作Redis，从 runtime 迁移而来
 */
@Slf4j
@Service
public class ConversationHistoryService implements IConversationHistoryService {

    private static final String LOCK_STR = ":lock";

    @Autowired
    private RedisClient redisClient;

    @Value("${redis.max_message_num}")
    private int maxMessageNum;

    @Value("${redis.max_message_size:5000000}")
    private long maxMessageSize;

    @Value("${redis.expire_time}")
    private long expireTime;

    @Value("${agent.insight-conv-rel:}")
    private String agentInsightConvRel;

    @Override
    public ConversationDeleteResp deleteConversationHistory(String projectId, String agentId,
            String conversationId, String versionId, String workspaceId) {
        RedisLock lock = null;
        try {
            String conversationKey = getConversationKey(agentId, conversationId, versionId);
            redisClient.delete(conversationKey);

            // 删除conversation列表中的记录
            if (StringUtils.isNotEmpty(agentInsightConvRel)) {
                String conversationsKey = String.format(agentInsightConvRel, agentId, RequestContextUtils.getRequestUserId());
                lock = redisClient.getLock(conversationsKey + LOCK_STR);
                if (lock.tryLock(Duration.ofSeconds(3))) {
                    List<ConversationInfo> conversationInfoList = new ArrayList<>();
                    if (redisClient.exists(conversationsKey)) {
                        String text = redisClient.get(conversationsKey);
                        if (StringUtils.isNotEmpty(text)) {
                            conversationInfoList = JSON.parseObject(text, new TypeReference<List<ConversationInfo>>() {});
                        }
                    }
                    conversationInfoList.removeIf(
                        conversationInfo -> conversationInfo.getConversationId().equals(conversationId));
                    redisClient.set(conversationsKey, JSON.toJSONString(conversationInfoList),
                        Duration.ofSeconds(expireTime));
                } else {
                    log.error("failed to get lock, other user is processing same workflow!");
                    throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
                }
            }
            return new ConversationDeleteResp().setId(conversationId);
        } catch (AgentStudioException e) {
            throw e;
        } catch (Exception e) {
            log.error("delete conversation failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    @Override
    public List<Message> retrieveConversationHistory(String projectId, String agentId,
            String conversationId, RetrieveConversationQo retrieveConversationQo, String workspaceId) {
        try {
            String versionId = retrieveConversationQo != null ? retrieveConversationQo.getVersionId() : null;
            String conversationKey = getConversationKey(agentId, conversationId, versionId);
            if (!redisClient.exists(conversationKey)) {
                return new ArrayList<>();
            }
            String conversationStr = redisClient.get(conversationKey);
            if (StringUtils.isEmpty(conversationStr)) {
                return new ArrayList<>();
            }
            Conversation conversation = JSON.parseObject(conversationStr, Conversation.class);
            List<Message> messageList = conversation.getMessageList()
                .stream()
                .sorted(Comparator.comparing(Message::getCreateTime, Comparator.nullsFirst(Comparator.naturalOrder())))
                .toList();
            redisClient.expire(conversationKey, Duration.ofSeconds(expireTime));
            log.info("retrieve: projectId={}, conversationId={}, messagesSize={} ", projectId, conversationId,
                messageList.size());
            return messageList;
        } catch (Exception e) {
            log.error("retrieve conversation failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    private String getConversationKey(String agentId, String conversationId, String versionId) {
        String key = String.format("%s_%s_%s", conversationId, agentId, RequestContextUtils.getRequestUserId());
        if (StringUtils.isEmpty(versionId)) {
            return key;
        }
        return key + "_" + versionId;
    }

    /**
     * 根据projectId，conversationId更新会话信息
     *
     * @param conversationParams 会话参数
     * @param messages message list
     * @return MessageList
     */
    public List<Message> updateConversation(ConversationParams conversationParams, List<Message> messages, boolean dialogueEnd) {
        Long startTime = System.currentTimeMillis();
        try {
            Conversation conversation;
            List<Message> messageList;
            String conversationKey = getConversationKey(conversationParams.getId(),
                    conversationParams.getConversationId(), conversationParams.getVersionId());
            String conversationStr = redisClient.get(conversationKey);
            if (StringUtils.isEmpty(conversationStr) || Constant.AppType.CONTROLLER.equals(
                    conversationParams.getExecuteType())) {
                // agent接口刷新conversation insight信息，工作流单独刷新逻辑和executions保持一致
                messageList = new ArrayList<>();
                conversation = new Conversation();
                conversation.setMessageList(messageList);
            } else {
                conversation = JSON.parseObject(conversationStr, Conversation.class);
                messageList = conversation.getMessageList();
            }
            messageList.addAll(messages);
            if (messageList.size() >= maxMessageNum) {
                messageList = new ArrayList<>(
                        messageList.subList(messageList.size() - maxMessageNum, messageList.size()));
            }
            long size = 0L;
            int offset = 0;

            for (int i = messageList.size() - 1; i >= 0; i--) {
                Object msg = messageList.get(i);
                if (msg instanceof Message mm) {
                    size += mm.getContent().length();
                } else if (msg instanceof Map) {
                    Map<String, Object> map = (Map<String, Object>) msg;
                    String content = map.getOrDefault("content", "").toString();
                    size += content.length();
                }

                if (size > maxMessageSize) {
                    log.warn("Conversation message size exceed limit. size:{} limit:{}", size, maxMessageSize);
                    break;
                }
                ++offset;
            }
            messageList = getTrimmedMessageList(messageList, offset);

            // 设置会话最后更新时间
            conversation.setMessageList(messageList);
            conversation.setLastUpdateTime(System.currentTimeMillis());
            if (dialogueEnd) {
                conversation.addDialogueCount();
            }
            redisClient.set(conversationKey, JSON.toJSONString(conversation), Duration.ofSeconds(expireTime));
            log.info("update: projectId={}, conversationId={}, messagesSize={} ", conversationParams.getProjectId(),
                    conversationParams.getConversationId(), messageList.size());
            return messageList;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            Long endTime = System.currentTimeMillis();
            log.info("update conversation cost {}ms, conversation id: {}", endTime - startTime,
                    conversationParams.getConversationId());
        }
    }

    private List<Message> getTrimmedMessageList(List<Message> messageList, int offset) {
        if (messageList.isEmpty()) {
            return messageList;
        }
        if (offset > 0) {
            return messageList.subList(messageList.size() - offset, messageList.size());
        }
        return messageList.subList(messageList.size() - 1, messageList.size());
    }
}
