/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.TypeReference;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.service.DelegateExchangeTokenService;
import com.openjiuwen.studio.agent.common.utils.JsonUtils;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.common.dto.AgentExecutionInfo;
import com.openjiuwen.studio.agent.common.dto.run.AgentExecutionQueries;
import com.openjiuwen.studio.agent.common.dto.AgentInvokeInfo;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.common.dto.run.ConversationDeleteResp;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;

import com.openjiuwen.studio.agent.common.dto.run.GetAgentExecutionInfoQo;
import com.openjiuwen.studio.agent.common.dto.agent.Feedback;
import com.openjiuwen.studio.agent.runtime.dto.GetMemoryChunksQo;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.runtime.dto.MemoryChunk;
import com.openjiuwen.studio.agent.runtime.dto.MemoryVariable;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationMemoryQo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.runtime.entity.FeedbackEntity;
import com.openjiuwen.studio.agent.runtime.entity.ModelConfig;
import com.openjiuwen.studio.agent.runtime.entity.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.runtime.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.runtime.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.runtime.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.runtime.model.AgentIrMetadata;
import com.openjiuwen.studio.agent.runtime.model.AgentIrWrapper;
import com.openjiuwen.studio.agent.runtime.model.Conversation;
import com.openjiuwen.studio.agent.runtime.model.ConversationParams;
import com.openjiuwen.studio.agent.runtime.model.ExecuteParams;
import com.openjiuwen.studio.agent.runtime.model.WorkflowRunResult;
import com.openjiuwen.studio.agent.runtime.rce.client.JiuWenClient;
import com.openjiuwen.studio.agent.runtime.rce.model.BackflowMessage;
import com.openjiuwen.studio.agent.runtime.rce.model.BackflowModel;
import com.openjiuwen.studio.agent.runtime.rce.model.BackflowSource;
import com.openjiuwen.studio.agent.runtime.rce.model.BackflowVo;
import com.openjiuwen.studio.agent.runtime.rce.model.CreateBackflowReq;
import com.openjiuwen.studio.agent.runtime.rce.model.JiuWenDeleteIrReq;
import com.openjiuwen.studio.agent.runtime.rce.service.DataManagerService;
import com.openjiuwen.studio.agent.runtime.service.debugging.ControllerDebuggingMgmtService;
import com.openjiuwen.studio.agent.runtime.utils.AlarmLogUtil;

import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

/**
 * Assistant运行态服务
 *
 */
@Slf4j
@Service
public class ConversationManagementService implements IConversationManagementService {
    private static final String CHAIN_INVOKE_TYPE = "chain";

    private static final String LLM_INVOKE_TYPE = "llm";

    private static final String PLUGIN_INVOKE_TYPE = "plugin";

    private static final String KNOWLEDGE_INVOKE_TYPE = "knowledge";

    private static final String MCP_INVOKE_TYPE = "mcp";

    private static final String LOCK_STR = "_lock";

    /**
     * RedisKey：用户反馈数据,ei:feedback:{conversation_id}:{message_id}
     */
    private static final String REDIS_KEY_USER_FEEDBACK = "ei:feedback:%s:%s";

    /**
     * RedisKey：用户反馈时间戳排序key，timeStamp:feedback_key
     */
    private static final String REDIS_KEY_FEEDBACK_SORTED = "ei:feedback:sorted";

    private final RedisClient redisClient;

    private final AgentIrCacheService agentIrCacheService;

    private final DataManagerService dataManagerService;

    @Autowired
    private DelegateExchangeTokenService delegateExchangeTokenService;

    @Autowired
    private WorkflowInstanceService workflowInstanceService;

    @Autowired
    private AgentOpsService opsService;

    @Autowired
    private ControllerDebuggingMgmtService controllerDebuggingMgmtService;

    @Autowired
    @Qualifier("traceTaskExecutor")
    private ThreadPoolTaskExecutor traceTaskExecutor;

    @Value("${redis.expire_time}")
    private long expireTime;

    @Value("${redis.user-variables-expire-time}")
    private long userVariablesExpireTime;

    @Value("${redis.conversation-variables-expire-time}")
    private long conVariablesExpireTime;

    @Value("${redis.max_message_num}")
    private int maxMessageNum;

    @Value("${redis.max_message_size:5000000}")
    private long maxMessageSize;

    @Value("${agent.insight-conv-rel:}")
    private String agentInsightConvRel; // conversation 记录

    @Value("${agent.insight-exec:}")
    private String agentInsightExec;

    @Value("${memory.chunk-num}")
    private Integer memoryChunkNum;

    @Value("${memory.conversation-num}")
    private Integer memoryConversationNum;

    @Autowired
    AlarmLogUtil alarmLogUtil;

    @Autowired
    private JiuWenClient jiuWenClient;

    public ConversationManagementService(RedisClient redisClient, AgentIrCacheService agentIrCacheService,
        DataManagerService dataManagerService) {
        this.redisClient = redisClient;
        this.agentIrCacheService = agentIrCacheService;
        this.dataManagerService = dataManagerService;
    }

    public void saveTaskId(String agentId, String conversionId, String taskId) {
        redisClient.set("task_id:" + agentId + ":" + conversionId, taskId, Duration.ofSeconds(expireTime));
    }

    public String queryTaskId(String agentId, String conversionId) {
        try {
            return redisClient.get("task_id:" + agentId + ":" + conversionId);
        } catch (Exception e) {
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "Redis get key failed, key is " + "task_id:" + agentId + ":" + conversionId,
                detail);
            return "";
        }
    }

    public void deleteTaskId(String agentId, String conversionId) {
        try {
            redisClient.delete("task_id:" + agentId + ":" + conversionId);
        } catch (Exception e) {
            log.warn("delete redis key fail. {}", e.getMessage());
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "delete redis key fail, key is " + "task_id:" + agentId + ":" + conversionId,
                    detail);
        }
    }

    public void saveDialogueCun(String agentId, String conversationId) {
        try {
            redisClient.getAndIncrement("dialoge_count:" + agentId + ":" + conversationId, expireTime);
        } catch (Exception e) {
            log.warn("fail save dialogue count to redis. {}", e.getMessage());
        }
    }

    /**
     * 根据projectId，conversationId获取会话信息
     *
     * @param projectId projectId
     * @param conversationId conversationId
     * @return MessageList
     */
    @Override
    public List<Message> retrieveConversation(String projectId, String id, String conversationId,
                                              RetrieveConversationQo retrieveConversationQo) {
        return retrieveConversationCore(projectId, id, conversationId,
                retrieveConversationQo.getVersionId()).getMessageList();
    }

    @Override
    public List<MemoryVariable> retrieveConversationMemory(String projectId, String agentId, String conversationId,
                                                           RetrieveConversationMemoryQo retrieveConversationMemoryQo) {
        String versionId = Optional.ofNullable(retrieveConversationMemoryQo)
                .map(RetrieveConversationMemoryQo::getVersionId)
                .orElse(null);

        // 从Redis获取记忆参数信息（用户级&会话级）
        List<MemoryVariable> memoryVariables = new ArrayList<>();
        List<MemoryVariable> userMemoryVariables = retrieveUserMemoryVariables(agentId,
                RequestContextUtils.getRequestUserId(), versionId);
        if (!CollectionUtils.isEmpty(userMemoryVariables)) {
            memoryVariables.addAll(userMemoryVariables);
        }
        List<MemoryVariable> conMemoryVariables = retrieveConMemoryVariables(agentId, conversationId, versionId);
        if (!CollectionUtils.isEmpty(conMemoryVariables)) {
            memoryVariables.addAll(conMemoryVariables);
        }
        Map<String, MemoryVariable> memoryVariableMap = memoryVariables.stream()
                .collect(
                        Collectors.toMap(item -> item.getLifeCycle() + "-" + item.getName(), memoryVariable -> memoryVariable));

        // 从IR获取记忆参数定义
        List<MemoryVariable> memoryVariableFromIr = getMemoryVariableFromIr(agentId, versionId);

        // 更新IR的记忆参数
        List<MemoryVariable> finalMemoryVariable = new ArrayList<>();
        for (MemoryVariable memoryVariable : memoryVariableFromIr) {
            String key = memoryVariable.getLifeCycle() + "-" + memoryVariable.getName();
            if (memoryVariableMap.containsKey(key)) {
                finalMemoryVariable.add(memoryVariableMap.get(key));
                continue;
            }
            finalMemoryVariable.add(memoryVariable);
        }
        return finalMemoryVariable;
    }

    /**
     * 根据projectId，conversationId获取会话信息
     *
     * @param projectId projectId
     * @param conversationId conversationId
     * @return 返回会话
     */
    public Conversation retrieveConversationCore(String projectId, String id, String conversationId, String versionId) {
        try {
            String conversationKey = getConversationKey(id, conversationId, versionId);
            if (!redisClient.exists(conversationKey)) {
                Conversation conversation = new Conversation();
                conversation.setOld(false);
                return conversation;
            }
            Conversation conversation = JSON.parseObject(redisClient.get(conversationKey), Conversation.class);
            conversation.setOld(true);
            List<Message> messageList = conversation.getMessageList()
                    .stream()
                    .sorted(Comparator.comparing(Message::getCreateTime, Comparator.nullsFirst(Comparator.naturalOrder())))
                    .toList();
            redisClient.expire(conversationKey, Duration.ofSeconds(expireTime));
            log.info("retrieve: projectId={}, conversationId={}, messagesSize={} ", projectId, conversationId,
                    messageList.size());
            return conversation;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed ", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    /**
     * 根据projectId，conversationId删除会话信息
     *
     * @param projectId projectId
     * @param conversationId conversationId
     * @return Void
     */
    @Override
    public ConversationDeleteResp deleteConversation(String projectId, String id, String conversationId,
                                                     String versionId) {
        RedisLock lock = null;
        try {
            String conversationKey = getConversationKey(id, conversationId, versionId);
            redisClient.delete(conversationKey);

            // 删除conversation列表中的记录
            String conversationsKey = String.format(agentInsightConvRel, id, RequestContextUtils.getRequestUserId());
            lock = redisClient.getLock(conversationsKey + LOCK_STR);
            if (lock.tryLock(Duration.ofSeconds(3))) {
                List<ConversationInfo> conversationInfoList = new ArrayList<>();
                if (redisClient.exists(conversationsKey)) {
                    String text = redisClient.get(conversationsKey);
                    if (StringUtils.isNotEmpty(text)) {
                        conversationInfoList = JSON.parseObject(text, new TypeReference<>() { });
                    }
                }
                conversationInfoList.removeIf(
                        conversationInfo -> conversationInfo.getConversationId().equals(conversationId));

                // 设置最后更新时间
                redisClient.set(conversationsKey, JSON.toJSONString(conversationInfoList),
                        Duration.ofSeconds(expireTime));
            } else {
                log.error("failed to get lock, other user is processing same workflow!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }
            return new ConversationDeleteResp().setId(conversationId);
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed ", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    @Override
    public ConversationDeleteResp deleteMemoryChunks(String projectId, String agentId, String conversationId,
                                                     Integer chunkId) {
        try {
            List<MemoryChunk> memoryChunkList = new ArrayList<>();
            String memoryChunkRedisKey = getMemoryChunkRedisKey(RequestContextUtils.getRequestUserId(), agentId,
                    conversationId);
            if (redisClient.exists(memoryChunkRedisKey)) {
                memoryChunkList = JSON.parseObject(redisClient.get(memoryChunkRedisKey), new TypeReference<>() { });
            }
            if (!memoryChunkList.isEmpty()) {
                if (!Objects.isNull(chunkId)) {
                    List<MemoryChunk> collect = memoryChunkList.stream()
                            .filter(memoryChunk -> !chunkId.equals(memoryChunk.getId()))
                            .toList();
                    redisClient.set(memoryChunkRedisKey, JSON.toJSONString(collect), Duration.ofSeconds(expireTime));
                } else {
                    redisClient.set(memoryChunkRedisKey, JSON.toJSONString(new ArrayList<>()),
                            Duration.ofSeconds(expireTime));
                }
            }
        } catch (Exception e) {
            log.error("Failed to get memory-chunk.", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "Failed to get memory-chunk ", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
        return new ConversationDeleteResp().setId(conversationId);
    }

    @Override
    public MemoryChunk generateMemoryChunk(String projectId, String agentId, String conversationId, Long start,
                                           Long end, Integer offset, Integer limit, String versionId, String workspaceId) {
        try {
            List<MemoryChunk> memoryChunkList = new ArrayList<>();
            String memoryChunkRedisKey = getMemoryChunkRedisKey(RequestContextUtils.getRequestUserId(), agentId,
                    conversationId);
            if (redisClient.exists(memoryChunkRedisKey)) {
                memoryChunkList = JSON.parseObject(redisClient.get(memoryChunkRedisKey), new TypeReference<>() { });
            }
            StringBuilder historyMessages = new StringBuilder();
            Conversation conversation = retrieveConversationCore(projectId, agentId, conversationId, versionId);
            if (conversation.getMessageList().isEmpty()) {
                log.info(
                        "No history messages when generating memory-chunk. projectId={}, agentId={}, conversationId={}",
                        projectId, agentId, conversationId);
                return new MemoryChunk();
            }
            MemoryChunk lastMemoryChunk = new MemoryChunk();
            if (!memoryChunkList.isEmpty()) {
                lastMemoryChunk = memoryChunkList.get(memoryChunkList.size() - 1);
                final Long lastMemoryChunkEndTime = lastMemoryChunk.getEnd();
                if (!Objects.isNull(lastMemoryChunkEndTime)) {
                    conversation.getMessageList()
                            .removeIf(message -> message.getCreateTime() <= lastMemoryChunkEndTime);
                }
                if (conversation.getMessageList().isEmpty()) {
                    log.info(
                            "No new messages when generating memory-chunk. projectId={}, agentId={}, conversationId={}",
                            projectId, agentId, conversationId);
                    return new MemoryChunk();
                }
                getRightHistoryMessages(conversation, historyMessages);
            } else {
                getRightHistoryMessages(conversation, historyMessages);
            }
            log.info("History messages startTime: {}",
                    Objects.isNull(conversation.getMessageList().get(0).getCreateTime())
                            ? null
                            : conversation.getMessageList().get(0).getCreateTime().toString());

            // 获取模型信息
            AgentRuntimeService agentRuntimeService = SpringBeanUtils.getBean(AgentRuntimeService.class);
            ModelConfig modelConfig = agentRuntimeService.getModelConfigFromObs(agentId);
            if (modelConfig == null) {
                log.warn("Not found agent model config.");
                return new MemoryChunk();
            }

            // 构造query
            String template = com.openjiuwen.studio.agent.common.utils.CommonUtils.getResourceContent(
                    Constant.MEMORY_CHUNK_PROMPT);
            PromptTemplate promptTemplate = new PromptTemplate(template);
            String query = promptTemplate.format(KV.of(Constant.LAST_MEMORY_CHUNK, lastMemoryChunk.getSummary()),
                    KV.of(Constant.HISTORY_MESSAGES, historyMessages.toString()));

            // 调用模型
            String content = agentRuntimeService.callModel(agentRuntimeService.buildAskModelReq(modelConfig, query),
                    workspaceId, RequestContextUtils.getRequestUserDomainId());

            MemoryChunk newMemoryChunk = new MemoryChunk().setId(
                            Objects.isNull(lastMemoryChunk.getId()) ? 1 : lastMemoryChunk.getId() + 1)
                    .setStart(conversation.getMessageList().get(0).getCreateTime())
                    .setEnd(conversation.getMessageList().get(conversation.getMessageList().size() - 1).getCreateTime())
                    .setSummary(content)
                    .setCreateTime(new Date(System.currentTimeMillis()));
            memoryChunkList.add(newMemoryChunk);
            redisClient.set(memoryChunkRedisKey, JSON.toJSONString(memoryChunkList), Duration.ofSeconds(expireTime));
            return newMemoryChunk;
        } catch (Exception e) {
            log.error("Failed to get memory-chunk.", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "Failed to get memory-chunk ", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    private void getRightHistoryMessages(Conversation conversation, StringBuilder historyMessages) {
        conversation.setMessageList(new ArrayList<>(conversation.getMessageList()
                .subList(0, Math.min(conversation.getMessageList().size(), memoryConversationNum))));
        for (int i = 0; i < conversation.getMessageList().size(); i++) {
            historyMessages.append(conversation.getMessageList().get(i).getContent()).append("\n");
        }
    }

    private String getMemoryChunkRedisKey(String userId, String agentId, String conversationId) {
        return "memory_chunks_" + userId + "_" + agentId + "_" + conversationId;
    }

    @Override
    public List<MemoryVariable> resetConversationMemory(String projectId, String conversationId, String agentId,
                                                        String versionId) {
        // 清理Redis里的记忆参数（会话级&用户级）
        try {
            redisClient.delete(getMemoryRedisKey(agentId, RequestContextUtils.getRequestUserId(), versionId));
            redisClient.delete(getMemoryRedisKey(agentId, conversationId, versionId));
        } catch (Exception exception) {
            log.error("redisson get bucket failed", exception);
            String detail = exception.getMessage();
            if (exception instanceof AgentStudioException) {
                detail = ((AgentStudioException) exception).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed ", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
        return getMemoryVariableFromIr(agentId, versionId);
    }

    /**
     * 根据projectId，conversationId更新会话信息
     *
     * @param executeParams 根据工作流执行参数更新会话
     * @return MessageList
     */
    public List<Message> updateConversation(ExecuteParams executeParams, boolean dialogueEnd) {
        ConversationParams conversationParams = ConversationParams.builder()
                .id(executeParams.getWorkflowId())
                .projectId(executeParams.getProjectId())
                .conversationId(executeParams.getConversationId())
                .versionId(executeParams.getReleasedVersion())
                .executeType(Constant.AppType.WORKFLOW)
                .build();
        List<Message> messages = executeParams.getMessages();
        return updateConversation(conversationParams, messages, dialogueEnd);
    }

    /**
     * 根据projectId，conversationId更新会话信息
     *
     * @param conversationParams 会话参数
     * @param messages message list
     * @return MessageList
     */
    @SuppressWarnings( {"unchecked", "ConstantValue"})
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
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed ", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            Long endTime = System.currentTimeMillis();
            log.info("update conversation cost {}ms, conversation id: {}", endTime - startTime,
                    conversationParams.getConversationId());
        }
    }

    /**
     * 查询记忆参数信息，用户级
     *
     * @param agentId agentId
     * @param userId userId
     * @return List<MemoryVariable>
     */
    public List<MemoryVariable> retrieveUserMemoryVariables(String agentId, String userId, String versionId) {
        return retrieveMemoryVariables(getMemoryRedisKey(agentId, userId, versionId), userVariablesExpireTime);
    }

    /**
     * 查询记忆参数信息，会话级
     *
     * @param agentId agentId
     * @param conversationId conversationId
     * @return List<MemoryVariable>
     */
    public List<MemoryVariable> retrieveConMemoryVariables(String agentId, String conversationId, String versionId) {
        return retrieveMemoryVariables(getMemoryRedisKey(agentId, conversationId, versionId), conVariablesExpireTime);
    }

    private List<MemoryVariable> retrieveMemoryVariables(String memoryVariablesRedisKey, long timeToLive) {
        try {
            List<MemoryVariable> memoryVariables = new ArrayList<>();
            if (redisClient.exists(memoryVariablesRedisKey)) {
                memoryVariables = JSON.parseObject(redisClient.get(memoryVariablesRedisKey), new TypeReference<>() { });
                redisClient.expire(memoryVariablesRedisKey, Duration.ofSeconds(timeToLive));
            }
            return memoryVariables;
        } catch (Exception exception) {
            log.error("Fail to retrieve memory variables because [{}]", exception.getMessage());
            String detail = exception.getMessage();
            if (exception instanceof AgentStudioException) {
                detail = ((AgentStudioException) exception).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "Fail to retrieve memory variables ", detail);
            throw new AgentStudioException(StudioError.RETRIEVE_MEMORY_VARIABLES_FAILED);
        }
    }

    /**
     * 更新记忆参数信息，用户级
     *
     * @param agentId agentId
     * @param userId userId
     * @param versionId 版本id
     * @param newMemoryVariables 待更新的记忆参数列表
     */
    public void updateUserMemoryVariables(String agentId, String userId, String versionId,
                                          List<MemoryVariable> newMemoryVariables) {
        updateMemoryVariables(getMemoryRedisKey(agentId, userId, versionId), newMemoryVariables,
                userVariablesExpireTime);
    }

    /**
     * 更新记忆参数信息，会话级
     *
     * @param agentId agentId
     * @param conversationId conversationId
     * @param versionId 版本id
     * @param newMemoryVariables 待更新的记忆参数列表
     */
    public void updateConMemoryVariables(String agentId, String conversationId, String versionId,
                                         List<MemoryVariable> newMemoryVariables) {
        updateMemoryVariables(getMemoryRedisKey(agentId, conversationId, versionId), newMemoryVariables,
                conVariablesExpireTime);
    }

    private void updateMemoryVariables(String memoryVariablesRedisKey, List<MemoryVariable> newMemoryVariables,
                                       long timeToLive) {
        try {
            redisClient.set(memoryVariablesRedisKey, JSON.toJSONString(newMemoryVariables),
                    Duration.ofSeconds(timeToLive));
        } catch (Exception exception) {
            log.error("Fail to update memory variables because [{}]", exception.getMessage());
            String detail = exception.getMessage();
            if (exception instanceof AgentStudioException) {
                detail = ((AgentStudioException) exception).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "Fail to update memory variables ", detail);
            throw new AgentStudioException(StudioError.UPDATE_MEMORY_VARIABLES_FAILED);
        }
    }

    private List<MemoryVariable> getMemoryVariableFromIr(String agentId, String versionId) {
        AgentIrWrapper irWrapper = StringUtils.isBlank(versionId)
                ? agentIrCacheService.getLatestAgentIr(agentId)
                : agentIrCacheService.getPublishedAgentIr(agentId, versionId);
        AgentIrMetadata metadata = irWrapper.getMetadata();
        return Optional.ofNullable(metadata).map(AgentIrMetadata::getMemoryVariables).orElse(new ArrayList<>());
    }

    private String getMemoryRedisKey(String prefix, String suffix, String versionId) {
        return prefix + "_" + (StringUtils.isBlank(versionId) ? suffix : suffix + "_" + versionId);
    }

    /**
     * 获取不同版本会话缓存的Key值
     *
     * @param id Workflow/Agent id
     * @param conversationId 会话id
     * @param versionId 版本号
     * @return 会话缓存的Key值
     */
    public String getConversationKey(String id, String conversationId, String versionId) {
        String conversationKey = String.format("%s_%s_%s", conversationId, id, RequestContextUtils.getRequestUserId());
        if (StringUtils.isEmpty(versionId)) {
            return conversationKey;
        }
        return conversationKey + "_" + versionId;
    }

    public void saveAgentExecutionToOps(JiuwenAgentEvent eventObj, AgentExecuteParams executeParams) {
        if (!executeParams.isUploadOpsSwitch()) {
            return;
        }

        String executionId = eventObj.getExecutionId();
        executeParams.setExecutionId(executionId);
        try {
            // execution info已存在则更新invoke list
            if (executeParams.getExecutionInfo() == null) {
                executeParams.setExecutionInfo(new AgentExecutionInfo());
            }
            AgentExecutionInfo finalExecutionInfo = executeParams.getExecutionInfo();
            JiuwenAgentEventData data = eventObj.getData();
            convertAgentExecutionInfo(finalExecutionInfo, data, executeParams);

            reportToAgentOps(executeParams, finalExecutionInfo);
        } catch (Exception e) {
            log.error("saveAgentExecutionToOps get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "saveAgentExecutionToOps get bucket failed", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    private void reportToAgentOps(AgentExecuteParams executeParams, AgentExecutionInfo executionInfo) {
        if (!executeParams.isUploadOpsSwitch()) {
            return;
        }
        traceTaskExecutor.execute(() -> {
            opsService.agentTraceHandler(executeParams, executionInfo);
        });
        if (!executeParams.isOldConversation()) {
            traceTaskExecutor.execute(() -> {
                executeParams.setOldConversation(true);
                opsService.agentSessionHandler(executeParams, "AGENT");
            });
        }
    }

    public void reportToAgentOps(AgentExecuteParams executeParams, JiuwenAgentEvent jiuwenAgentEvent) {
        if (!executeParams.isUploadOpsSwitch()) {
            return;
        }

        traceTaskExecutor.execute(() -> {
            opsService.multiAgentTraceHandler(executeParams, jiuwenAgentEvent);
        });
        if (!executeParams.isOldConversation()) {
            traceTaskExecutor.execute(() -> {
                executeParams.setOldConversation(true);
                opsService.agentSessionHandler(executeParams, "CONTROLLER");
            });
        }
    }

    public void reportToAgentOps(AgentExecuteParams executeParams, JiuwenEvent jiuwenEvent) {
        if (!executeParams.isUploadOpsSwitch()) {
            return;
        }
        opsService.multiAgentTraceHandler(executeParams, jiuwenEvent, false);
    }

    /**
     * 异步上报和agent交互的输入输出
     * @param executeParams
     */
    public void processAgentInteraction(AgentExecuteParams executeParams) {
        if (executeParams.isUploadOpsSwitch()) {
            opsService.uploadAgentInteraction(executeParams);
        }
    }

    public void reportTaskEnd(AgentExecuteParams executeParams) {
        if (executeParams.isUploadOpsSwitch()) {
            opsService.multiAgentTraceHandler(executeParams, null, true);
        }
    }

    private AgentExecutionInfo getAgentExecutionInfo(String projectId, String executionId, String agentId,
                                                    GetAgentExecutionInfoQo getAgentExecutionInfoQo) {
        AgentExecutionInfo executionInfo = new AgentExecutionInfo();
        try {
            String userId = RequestContextUtils.getRequestUserId();
            String insightExecKey = String.format(agentInsightExec, userId, executionId);
            if (redisClient.exists(insightExecKey)) {
                String text = redisClient.get(insightExecKey);
                if (StringUtils.isNotEmpty(text)) {
                    executionInfo = JSON.parseObject(text, AgentExecutionInfo.class);
                }
            } else {
                return executionInfo;
            }

            List<AgentInvokeInfo> invokeInfoList = executionInfo.getInvokeList();
            invokeInfoList.stream().sorted(Comparator.comparing(AgentInvokeInfo::getStartTime).reversed()).toList();
            return executionInfo;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    @Override
    public AutoAddResultJsonObject getMemoryChunks(String projectId, String agentId, String conversationId,
                                                   GetMemoryChunksQo getMemoryChunksQo) {
        try {
            List<MemoryChunk> memoryChunkList = new ArrayList<>();
            String memoryChunkRedisKey = getMemoryChunkRedisKey(RequestContextUtils.getRequestUserId(), agentId,
                    conversationId);
            redisClient.expire(memoryChunkRedisKey, Duration.ofSeconds(expireTime));
            if (!redisClient.exists(memoryChunkRedisKey)) {
                return new AutoAddResultJsonObject().setMemoryChunks(memoryChunkList);
            }
            memoryChunkList = JSON.parseObject(redisClient.get(memoryChunkRedisKey), new TypeReference<>() { });
            if (Objects.isNull(getMemoryChunksQo.getLimit())) {
                memoryChunkList = new ArrayList<>(
                        memoryChunkList.subList(Math.max(memoryChunkList.size() - memoryChunkNum, 0),
                                memoryChunkList.size()));
                memoryChunkList = memoryChunkList.stream()
                        .sorted(Comparator.comparing(MemoryChunk::getId).reversed())
                        .toList();
                return new AutoAddResultJsonObject().setMemoryChunks(memoryChunkList);
            }
            memoryChunkList = new ArrayList<>(
                    memoryChunkList.subList(Math.max(memoryChunkList.size() - getMemoryChunksQo.getLimit(), 0),
                            memoryChunkList.size()));
            memoryChunkList = memoryChunkList.stream()
                    .sorted(Comparator.comparing(MemoryChunk::getId).reversed())
                    .toList();
            return new AutoAddResultJsonObject().setMemoryChunks(memoryChunkList);
        } catch (Exception e) {
            log.error("Failed to get memory-chunk.", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "Failed to get memory-chunk.", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    @Override
    public String createUserFeedback(String projectId, String appId, String conversationId, String messageId,
                                     String appType, String versionId, Feedback body) {
        RedisLock lock = null;
        try {
            // 1. 更新用户反馈redis key中对应的数据
            String feedbackKey = String.format(REDIS_KEY_USER_FEEDBACK, conversationId, messageId);
            lock = redisClient.getLock(feedbackKey + LOCK_STR);
            Long feedbackTimeStamp = System.currentTimeMillis();
            FeedbackEntity feedbackEntity = new FeedbackEntity();
            if (lock.tryLock(Duration.ofSeconds(3))) {
                feedbackEntity.setAppId(appId);
                feedbackEntity.setAppType(appType);
                feedbackEntity.setAppName(body.getAppName());
                feedbackEntity.setDomainId(RequestContextUtils.getRequestUserDomainId());
                feedbackEntity.setProjectId(projectId);
                feedbackEntity.setUserId(RequestContextUtils.getRequestUserId());
                feedbackEntity.setVersionId(versionId);
                feedbackEntity.setConversationId(conversationId);
                feedbackEntity.setMessageId(messageId);
                feedbackEntity.setFeedback(body);
                feedbackEntity.setCreateAt(feedbackTimeStamp);

                // 设置feedback key最后更新时间
                redisClient.set(feedbackKey, JSON.toJSONString(feedbackEntity), Duration.ofSeconds(expireTime));
            } else {
                log.error("failed to get lock, other user is processing same feedback redis key!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }

            // 2. 更新feedback时间戳集合数据
            redisClient.scoredSortedSet(REDIS_KEY_FEEDBACK_SORTED, feedbackTimeStamp, feedbackKey);

            // 3. 更新message记录中的反馈数据
            messageFeedbackAction(appId, conversationId, messageId, versionId, body);
            return null;
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    public void creatDataBackflowJob(FeedbackEntity feedback) {
        try {
            // 1. 根据反馈数据中的projectId和domainId信息，通过委托获取用户token
            String opToken = "";
            RequestContextUtils.setRequestAuthTokenAndUserId(
                    delegateExchangeTokenService.delegateExchangeToken(feedback.getProjectId(), feedback.getDomainId(),
                            opToken), feedback.getProjectId(), feedback.getUserId());

            // 2. 查询会话记录信息，找到对应的message块，获取message关联的executor_id
            String executorId = getMessageExecutorId(feedback);

            // 3. 根据查询到的executor_id，获取对应的invoke info，查询model_deployment_id和实际传入模型的message信息
            if (executorId == null) {
                // 非阻塞流程，executorId不存在时直接退出
                log.error("message executor id is null");
                return;
            }
            String modelDeploymentId = null;
            List<BackflowVo> data = new ArrayList<>();
            if (Constant.AppType.AGENT.equals(feedback.getAppType())) {
                AgentExecutionInfo executionInfo = getAgentExecutionInfo(feedback.getProjectId(), executorId,
                        feedback.getAppId(), null);
                for (AgentInvokeInfo invokeInfo : executionInfo.getInvokeList()) {
                    if (LLM_INVOKE_TYPE.equals(invokeInfo.getNodeType())) {
                        modelDeploymentId = invokeInfo.getModelDeploymentId();
                        List<BackflowMessage> actualMessageList = buildAgentBackflowMessage(feedback, invokeInfo);
                        BackflowVo backflowVo = buildBackflowVo(feedback, actualMessageList, modelDeploymentId);
                        data.add(backflowVo);
                        break;
                    }
                }
            } else if (Constant.AppType.WORKFLOW.equals(feedback.getAppType())) {
                WorkflowInstanceEntity workflowInstance = workflowInstanceService.get(executorId, null);
                if (workflowInstance == null) {
                    // 非阻塞流程，workflow insight不存在时直接退出
                    log.error("workflow insight instance is not exist");
                    return;
                }

                // 对每条workflow_node_message debug事件进行转换并倒叙排序
                List<NodeRunInfo> nodeRunInfos = new ArrayList<>();
                for (JiuwenEvent jiuwenEvent : workflowInstance.getEventList()) {
                    if (Strings.CS.equals(jiuwenEvent.getEvent(),
                            JiuwenEventType.WORKFLOW_NODE_MESSAGE.name().toLowerCase(Locale.ROOT))) {
                        nodeRunInfos.add(JiuwenEventProcessor.convertNodeRunInfo(jiuwenEvent.getData()));
                    }
                }
                for (NodeRunInfo nodeRunInfo : nodeRunInfos) {
                    if (LLM_INVOKE_TYPE.equalsIgnoreCase(nodeRunInfo.getNodeType())
                            && NodeRunInfo.NodeStatusEnum.FINISHED.equals(nodeRunInfo.getNodeStatus())) {
                        modelDeploymentId = nodeRunInfo.getOutputs().get("deploymentId").toString();
                        List<BackflowMessage> actualMessageList = buildWorkflowBackflowMessage(feedback, nodeRunInfo);
                        BackflowVo backflowVo = buildBackflowVo(feedback, actualMessageList, modelDeploymentId);
                        data.add(backflowVo);
                    }
                }
            } else {
                // 非阻塞流程，app type不存在时直接退出
                log.error("app type {} is not exist", feedback.getAppType());
                return;
            }

            // 4. 调用回流接口
            dataManagerService.createDataBackflowJob(feedback.getProjectId(), new CreateBackflowReq(data));
        } catch (Exception e) {
            // 数据回流不是强制步骤，异常时容错处理，打印错误日志，不抛出异常
            log.error("create feedback data backflow job failed, {}", e.getMessage());
        }
    }

    private String getMessageExecutorId(FeedbackEntity feedback) {
        String conversationKey = getConversationKey(feedback.getAppId(), feedback.getConversationId(),
                feedback.getVersionId());
        if (!redisClient.exists(conversationKey)) {
            // 非阻塞流程，会话不存在时直接退出
            log.error("conversation is not exist, conversation id: {}", feedback.getConversationId());
            return null;
        }
        Conversation conversation = JSON.parseObject(redisClient.get(conversationKey), Conversation.class);
        List<Message> messageList = conversation.getMessageList()
                .stream()
                .sorted(Comparator.comparing(Message::getCreateTime, Comparator.nullsFirst(Comparator.naturalOrder())))
                .toList();
        String executorId = null;
        for (Message message : messageList) {
            // 根据messageId匹配对应的message记录，获取对应的executorId
            if (message.getCreateTime() != null && Long.parseLong(feedback.getMessageId()) == message.getCreateTime()) {
                executorId = message.getExecutionId();
                break;
            }
        }
        return executorId;
    }

    private List<BackflowMessage> buildAgentBackflowMessage(FeedbackEntity feedback, AgentInvokeInfo invokeInfo) {
        Object inputs = invokeInfo.getInputs();
        List<BackflowMessage> actualMessageList = JSON.parseObject(inputs.toString(), new TypeReference<>() { });

        // 根据数据回流接口要求，每条message带上时间戳
        for (BackflowMessage backflowMessage : actualMessageList) {
            backflowMessage.setTimestamp(invokeInfo.getEndTime());
        }
        BackflowMessage backflowMessage = JSON.parseObject(invokeInfo.getOutputs().toString(), BackflowMessage.class);
        backflowMessage.setTimestamp(Long.parseLong(feedback.getMessageId()));
        backflowMessage.setReview(feedback.getFeedback().getRating());
        backflowMessage.setReason(feedback.getFeedback().getReason());
        actualMessageList.add(backflowMessage);
        return actualMessageList;
    }

    private List<BackflowMessage> buildWorkflowBackflowMessage(FeedbackEntity feedback, NodeRunInfo nodeRunInfo) {
        Map<String, Object> llmInfoMap = JSON.parseObject(nodeRunInfo.getMetadata().get("llm_info").toString(),
                new TypeReference<>() { });
        Map<String, Object> llmInputsMap = JSON.parseObject(llmInfoMap.get("llm_inputs").toString(),
                new TypeReference<>() { });
        List<JSONObject> llmMessages = JSON.parseObject(llmInputsMap.get("messages").toString(),
                new TypeReference<>() { });
        List<BackflowMessage> actualMessageList = new ArrayList<>();
        for (JSONObject message : llmMessages) {
            BackflowMessage inputMessage = new BackflowMessage();
            inputMessage.setRole(message.getString("type"));
            inputMessage.setContent(message.getString("content"));

            // 根据数据回流接口要求，每条message带上时间戳
            inputMessage.setTimestamp(nodeRunInfo.getEndTime());
            actualMessageList.add(inputMessage);
        }
        BackflowMessage outputMessage = new BackflowMessage();
        outputMessage.setRole("assistant");
        outputMessage.setContent(llmInfoMap.get("llm_outputs").toString());
        outputMessage.setTimestamp(Long.parseLong(feedback.getMessageId()));
        outputMessage.setReview(feedback.getFeedback().getRating());
        outputMessage.setReason(feedback.getFeedback().getReason());
        actualMessageList.add(outputMessage);
        return actualMessageList;
    }

    private BackflowVo buildBackflowVo(FeedbackEntity feedback, List<BackflowMessage> actualMessageList,
                                       String modelDeploymentId) {
        BackflowVo backflowVo = new BackflowVo();
        backflowVo.setMessages(actualMessageList);
        backflowVo.setSource(new BackflowSource(feedback.getAppId(), feedback.getAppType(), feedback.getAppName()));
        BackflowModel backflowModel = new BackflowModel();
        backflowModel.setDeploymentId(modelDeploymentId);
        backflowVo.setModel(backflowModel);
        return backflowVo;
    }

    @Override
    public ConversationDeleteResp deleteFeedback(String projectId, String appId, String conversationId,
                                                 String messageId, String versionId) {
        try {
            // 1. 删除用户反馈redis key中对应的数据
            String feedbackKey = String.format(REDIS_KEY_USER_FEEDBACK, conversationId, messageId);
            redisClient.delete(feedbackKey);

            // 2. 删除feedback时间戳集合中对应的数据
            redisClient.scoredSortedRemove(REDIS_KEY_FEEDBACK_SORTED, feedbackKey);

            // 3. 删除message记录中的反馈数据
            messageFeedbackAction(appId, conversationId, messageId, versionId, new Feedback());
            return new ConversationDeleteResp().setId(conversationId);
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
    }

    /**
     * 更新或清空message记录中的feedback数据
     *
     * @param appId appId
     * @param conversationId conversationId
     * @param messageId messageId
     * @param versionId versionId
     * @param body body
     */
    private void messageFeedbackAction(String appId, String conversationId, String messageId, String versionId,
                                       Feedback body) {
        RedisLock lock = null;
        try {
            // 操作message记录中的反馈数据
            String conversationKey = getConversationKey(appId, conversationId, versionId);
            lock = redisClient.getLock(conversationKey + LOCK_STR);
            if (lock.tryLock(Duration.ofSeconds(3))) {
                Conversation conversation = new Conversation();
                List<Message> messageList = new ArrayList<>();
                if (redisClient.exists(conversationKey)) {
                    conversation = JSON.parseObject(redisClient.get(conversationKey), Conversation.class);
                    messageList = conversation.getMessageList();
                    messageList.forEach(message -> {
                        // 根据messageId匹配对应的message记录，更新或清空对应的反馈数据
                        if (message.getCreateTime() != null && Long.parseLong(messageId) == message.getCreateTime()) {
                            message.setRating(body.getRating());
                            message.setReason(body.getReason());
                        }
                    });
                }

                // 设置会话最后更新时间
                conversation.setMessageList(messageList);
                redisClient.set(conversationKey, JSON.toJSONString(conversation), Duration.ofSeconds(expireTime));
            } else {
                log.error("failed to get lock, other user is processing same redis key!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            String detail = e.getMessage();
            if (e instanceof AgentStudioException) {
                detail = ((AgentStudioException) e).getErrorCode().toString();
            }
            alarmLogUtil.logAlarm("REDIS", "redisson get bucket failed", detail);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
    }

    /**
     * event转换为execution info
     */
    public AgentExecutionInfo convertAgentExecutionInfo(AgentExecutionInfo executionInfo,
                                                        JiuwenAgentEventData eventData, AgentExecuteParams executeParams) {
        executionInfo.setConversationId(executeParams.getConversationId());
        executionInfo.setExecutionId(executeParams.getExecutionId());
        executionInfo.setMetaData(eventData.getMetaData());
        executionInfo.setInputs(executeParams.getQuery());
        AgentInvokeInfo invokeInfo = convertAgentInvokeInfo(executionInfo, eventData, executeParams);
        if (executionInfo.getInvokeList() == null) {
            executionInfo.setInvokeList(new ArrayList<>());
        }
        if (invokeInfo != null) {
            executionInfo.getInvokeList().add(invokeInfo);
        }
        return executionInfo;
    }

    /**
     * event转换为invoke info
     */
    public AgentInvokeInfo convertAgentInvokeInfo(AgentExecutionInfo executionInfo, JiuwenAgentEventData eventData,
                                                  AgentExecuteParams executeParams) {
        // event结束时间为空表示invoke未结束，不记录信息
        if (StringUtils.isEmpty(eventData.getEndTime())) {
            return null;
        }
        AgentInvokeInfo agentInvokeInfo = new AgentInvokeInfo();

        // 时间日期转换格式
        long startTime = System.currentTimeMillis();
        if (StringUtils.isNotEmpty(eventData.getStartTime())) {
            LocalDateTime localDateTime = LocalDateTime.parse(eventData.getStartTime());
            startTime = localDateTime.atZone(ZoneOffset.systemDefault()).toInstant().toEpochMilli();
            agentInvokeInfo.setStartTime(startTime);
        }
        long endTime = System.currentTimeMillis();
        if (StringUtils.isNotEmpty(eventData.getEndTime())) {
            LocalDateTime localDateTime = LocalDateTime.parse(eventData.getEndTime());
            endTime = localDateTime.atZone(ZoneOffset.systemDefault()).toInstant().toEpochMilli();
            agentInvokeInfo.setEndTime(endTime);
        }

        // 根据invoke类型进行对应处理
        String invokeType = eventData.getInvokeType();
        if (invokeType.equals(CHAIN_INVOKE_TYPE)) {
            if (eventData.getEndTime() != null) {
                // 当invoke_type为chain，并且是结束event时，标识agent应用对话结束
                executionInfo.setOutputs(Optional.ofNullable(eventData.getOutputs())
                        .map(Object::toString)
                        .map(str -> str.replaceAll("(?i)(九问|jiuwen)", "Runtime"))
                        .orElse(""));
                if (StringUtils.isNotBlank(eventData.getError())) {
                    executionInfo.setErrorInfo(eventData.getError().replaceAll("(?i)(九问|jiuwen)", "Runtime"));
                }
                executionInfo.setStatus(executionInfo.getStatus() == null ? "succeeded" : executionInfo.getStatus());
                executionInfo.setStartTime(startTime);
                executionInfo.setEndTime(endTime);
            }
            return null;
        }
        if (invokeType.equals(PLUGIN_INVOKE_TYPE)) {
            JSONObject instanceAttributes = JSON.parseObject(
                    eventData.getMetaData().get("instance_attributes").toString());
            String nodeName = instanceAttributes.getString("plugin_name");
            if (Objects.equals("retrieval", nodeName)) {
                invokeType = KNOWLEDGE_INVOKE_TYPE;
                nodeName = "知识库";
            } else if (Optional.ofNullable(instanceAttributes.getBoolean("is_mcp")).orElse(false)) {
                invokeType = MCP_INVOKE_TYPE;
                nodeName = instanceAttributes.getString("server_name");
            }
            agentInvokeInfo.setNodeName(nodeName);
        }


        // 如果节点类型为大模型，获取模型信息保存到insight记录中
        if (invokeType.equals(LLM_INVOKE_TYPE)) {
            agentInvokeInfo.setModelDeploymentId(executeParams.getModelDeploymentId());
        }
        agentInvokeInfo.setNodeId(eventData.getInvokeId());
        agentInvokeInfo.setNodeType(invokeType);
        agentInvokeInfo.setInputs(eventData.getInputs());
        agentInvokeInfo.setOutputs(eventData.getOutputs());
        agentInvokeInfo.setMetaData(eventData.getMetaData());

        // 节点状态转换
        if (eventData.getError() != null) {
            agentInvokeInfo.setErrorMessage(eventData.getError());
            agentInvokeInfo.setNodeStatus("failed");
            executionInfo.setStatus("failed");
        } else {
            agentInvokeInfo.setNodeStatus("succeeded");
        }
        return agentInvokeInfo;
    }

    private void clearJiuwenConversaion(String token, String conversationId) {
        try {
            JiuWenDeleteIrReq jiuWenDeleteIrReq = JiuWenDeleteIrReq.builder().conversationId(conversationId).build();

            jiuWenClient.deleteIr(token, jiuWenDeleteIrReq);
        } catch (Exception e) {
            log.warn("Fail clear jiuwen conversation record. conversation:{}", conversationId, e);
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
