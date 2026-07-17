/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import static com.openjiuwen.studio.agent.runtime.constant.Constant.Agent.INVOKE_HEADER_KEY;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.REQUEST_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.TASK_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.X_REQUEST_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.X_TASK_ID;

import com.alibaba.fastjson.JSONException;
import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.AgentInvokeInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.knowledge.FileUploadRsp;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrReq;
import com.openjiuwen.studio.agent.common.dto.run.AsrRsp;
import com.openjiuwen.studio.agent.common.dto.run.ChatMessage;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.common.enums.KnowledgeSourceEnum;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.service.DelegateExchangeTokenService;
import com.openjiuwen.studio.agent.common.utils.CommonUtils;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.runtime.bo.FileCheckWrapper;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.runtime.controller.RuntimeModelServiceController;
import com.openjiuwen.studio.agent.runtime.dto.AgentEvent;
import com.openjiuwen.studio.agent.runtime.dto.AgentRunRsp;
import com.openjiuwen.studio.agent.runtime.dto.AgentWorkflowContent;
import com.openjiuwen.studio.agent.runtime.dto.ApiExecDataEventAnswer;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.dto.ConversationHistory;
import com.openjiuwen.studio.agent.runtime.dto.ErrorEvent;
import com.openjiuwen.studio.agent.runtime.dto.FunctionCallEventAnswer;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenDeepResearchEvent;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenExecutionRequest;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenParams;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenParamsSysOperationCard;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenParamsSysOperationCardWorkConfig;
import com.openjiuwen.studio.agent.runtime.dto.Latency;
import com.openjiuwen.studio.agent.runtime.dto.LongTermMemoryRuntime;
import com.openjiuwen.studio.agent.runtime.dto.MemoryVariable;
import com.openjiuwen.studio.agent.runtime.dto.MessageEvent;
import com.openjiuwen.studio.agent.runtime.dto.NodeMessage;
import com.openjiuwen.studio.agent.runtime.dto.Plugin;
import com.openjiuwen.studio.agent.runtime.dto.ReleaseInfo;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunInfo;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunRsp;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunStreamRsp;
import com.openjiuwen.studio.agent.runtime.entity.AskModelReq;
import com.openjiuwen.studio.agent.runtime.entity.MessageEntity;
import com.openjiuwen.studio.agent.runtime.entity.ModelConfig;
import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsChannel;
import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsEventEntity;
import com.openjiuwen.studio.agent.runtime.entity.analytics.AnalyticsEventType;
import com.openjiuwen.studio.agent.runtime.enums.EventType;
import com.openjiuwen.studio.agent.runtime.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.runtime.enums.MessageRole;
import com.openjiuwen.studio.agent.runtime.enums.WorkflowStreamEventEnum;
import com.openjiuwen.studio.agent.runtime.event.SensitiveMessageEvent;
import com.openjiuwen.studio.agent.runtime.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.runtime.model.AgentIrMetadata;
import com.openjiuwen.studio.agent.runtime.model.AgentIrWrapper;
import com.openjiuwen.studio.agent.runtime.model.Conversation;
import com.openjiuwen.studio.agent.runtime.model.ConversationParams;
import com.openjiuwen.studio.agent.runtime.model.ImageInfo;
import com.openjiuwen.studio.agent.runtime.model.MediaUrl;
import com.openjiuwen.studio.agent.runtime.model.MessageChunkCache;
import com.openjiuwen.studio.agent.runtime.model.ModelApiLog;
import com.openjiuwen.studio.agent.runtime.model.VideoInfo;
import com.openjiuwen.studio.agent.runtime.model.WorkflowRunResult;
import com.openjiuwen.studio.agent.runtime.model.debugging.AgentCtrlTraceData;
import com.openjiuwen.studio.agent.runtime.model.debugging.WorkflowInvokeData;
import com.openjiuwen.studio.agent.runtime.model.memory.LongTermMemoryRefreshEvent;
import com.openjiuwen.studio.agent.runtime.model.memory.UserCachedChatTurn;
import com.openjiuwen.studio.agent.runtime.rce.client.SISClient;
import com.openjiuwen.studio.agent.runtime.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.runtime.sensitive.SensitiveTrie;
import com.openjiuwen.studio.agent.runtime.sensitive.SensitiveTrieUtils;
import com.openjiuwen.studio.agent.runtime.service.debugging.ControllerDebuggingMgmtService;
import com.openjiuwen.studio.agent.runtime.service.md.RuntimeModelApiLogService;
import com.openjiuwen.studio.agent.runtime.service.memory.UserMemoryCacheMgmtService;
import com.openjiuwen.studio.agent.runtime.thread.ModelApiLogThreadLocal;
import com.openjiuwen.studio.agent.runtime.utils.DatetimeUtils;
import com.openjiuwen.studio.agent.runtime.utils.EnvVariablesUtils;
import com.openjiuwen.studio.agent.runtime.utils.JsonUtils;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;
import com.openjiuwen.studio.agent.runtime.utils.PerformUtils;
import com.openjiuwen.studio.agent.runtime.utils.SseEmitterUtils;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import okhttp3.sse.EventSourceListener;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.apache.commons.lang3.tuple.Pair;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.MessageSource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

/**
 * Agent运行Service
 *
 */
@Slf4j
@Service
public class AgentRuntimeService implements IAgentRuntimeService {
    private static final String LOCK_STR = "_lock";

    private static final int KB = 1024;

    private static final List<String> SYSTEM_INPUTS = Arrays.asList(Constant.Jiuwen.USER_MSG_FIELD,
            Constant.Jiuwen.WORKFLOW_SEQUENCE_FIELD, Constant.Jiuwen.ACTIVE_WORKFLOWS_FIELD, Constant.Jiuwen.INTENT_FIELD);

    private final AgentIrCacheService agentIrCacheService;

    private final ConversationManagementService conversationManagementService;

    private final JiuWenService jiuWenService;

    private final OkHttpUtils okHttpUtils;

    private final RedisClient redisClient;

    private final EnvVariablesUtils envVariablesUtils;

    @Autowired
    private ObsService obsService;

    @Autowired
    private JiuwenEventProcessor eventProcessor;

    @Autowired
    private AgentOpsService opsService;

    @Setter
    @Resource
    private ControllerDebuggingMgmtService controllerDebuggingMgmtService;

    @Value("${jiuwen.base-url}")
    private String jiuwenBaseUrl;

    @Value("${jiuwen.deep-research-url}")
    private String jiuwenDeepResearchUrl;

    @Value("${agent.ir-obs-path}")
    private String irObsPath;

    @Value("${agent.skill-enabled}")
    private boolean skillEnabled;

    @Value("${jiuwen.run-api:/v1/orchestration/ir/execute}")
    private String runApi;

    @Value("${agent.sse-timeout-milliseconds}")
    private long agentSseTimeoutMilliSec;

    @Value("${agent.jiuwen-timeout-milliseconds}")
    private long agentJiuwenTimeoutMilliSec;

    @Value("${agent.deep-research-sse-timeout-milliseconds}")
    private long deepResearchSseTimeoutMilliSec;

    @Value("${redis.expire_time}")
    private long expireTime;

    @Value("${release.web-rel}")
    private String releaseWebRel;

    @Value("${release.app-rel}")
    private String releaseAppRel;

    @Value("${release.cloud-rel}")
    private String releaseCloudRel;

    @Value("${env.type}")
    private String envType;

    @Value("${agent.max-query-length}")
    private int agentMaxQueryLength;

    @Value("${agent.max-deep-research-message-length}")
    private int deepResearchMaxMsgLength;

    @Value("${op.svc.project-id}")
    private String opProjectId;

    @Value("${file.access.expiration-minutes:10080}")
    private int fileExpirationMinutes;

    @Value("${icon.max-size}")
    private long iconMaxSize;

    @Value("${agent.max-upload-file-size}")
    private long fileMaxSize;

    @Value("${agent.max-upload-image-size}")
    private long imageMaxSize;

    @Value("${file.default-type}")
    private String allowedDefaultTypeStr;

    @Value("${file.icon-type}")
    private String allowedIconTypeStr;

    @Value("${file.img-type}")
    private String allowedImgTypeStr;

    @Value("${file.max-upload-num}")
    private int maxUploadNum;

    @Value("${file.time-scope-upload-num}")
    private int timeScopeUploadNum;

    @Value("${file.max-upload-total-size}")
    private int maxUploadTotalSize;

    @Value("${file.time-scope-upload-total-size}")
    private int timeScopeUploadTotalSize;

    @Value("${storage.bucket-storage-limit:100}")
    private long bucketStorageLimit;

    @Value("${file.video-type}")
    private String allowedVideoTypeStr;

    @Value("${file.readonly.enable:false}")
    private boolean fileReadOnly;

    @Value("${agent.conversion_file_max_num}")
    private int conversionFileMaxNum;

    @Value("${knowledge.source}")
    private String knowledgeSource;

    @Value("${jiuwen.exclude-headers:Content-Type,Content-Length,Host,User-Agent,Accept,Accept-Encoding,Connection,X-Auth-Token,X-Workspace-Id,X-Owner-Domain-Id,X-Owner-Project-Id}")
    private String excludeHeaders;

    @Value("${lite.api-code.enabled:false}")
    private boolean isApiKeyCheckEnabled;

    @Value("${heartbeat.interval-seconds:50}")
    private long heartbeatInterval;

    @Value("${agent.finish-keep-text:false}")
    private boolean finishKeepText;

    @Autowired
    private AnalyticsEventService analyticsEventService;

    @Autowired
    private DelegateExchangeTokenService delegateExchangeTokenService;

    @Autowired
    private PublishUtils publishUtils;

    @Autowired
    private SISClient sisClient;

    @Autowired
    private MessageSource messageSource;

    @Autowired
    private RuntimeModelApiLogService apiLogService;

    @Autowired
    private KnowledgeBaseFileInfoService knowledgeBaseFileInfoService;

    @Resource
    private UserMemoryCacheMgmtService userMemoryCacheMgmtService;

    private Set<String> allowedIconType = new HashSet<>();

    private Set<String> allowedImgType = new HashSet<>();

    private Set<String> allowedVideoType = new HashSet<>();

    private Set<String> allowedDefaultType = new HashSet<>();

    @Autowired
    private RuntimeModelServiceController modelController;

    @Autowired
    private RuntimeI18nService runtimeI18nService;

    private Set<String> excludeHeaderSet;

    /**
     * 构造方法
     *
     * @param agentIrCacheService agentIrCacheService
     * @param conversationManagementService conversationManagementService
     * @param jiuWenService jiuWenService
     * @param okHttpUtils okHttpUtils
     * @param redisClient redisClient
     */
    public AgentRuntimeService(AgentIrCacheService agentIrCacheService,
                               ConversationManagementService conversationManagementService, JiuWenService jiuWenService,
                               OkHttpUtils okHttpUtils, RedisClient redisClient, EnvVariablesUtils envVariablesUtils) {
        this.agentIrCacheService = agentIrCacheService;
        this.conversationManagementService = conversationManagementService;
        this.jiuWenService = jiuWenService;
        this.okHttpUtils = okHttpUtils;
        this.redisClient = redisClient;
        this.envVariablesUtils = envVariablesUtils;
    }

    /**
     * 初始化
     */
    @PostConstruct
    public void init() {
        allowedIconType = Arrays.stream(allowedIconTypeStr.split(Constant.SEPARATOR)).collect(Collectors.toSet());
        allowedImgType = Arrays.stream(allowedImgTypeStr.split(Constant.SEPARATOR)).collect(Collectors.toSet());
        allowedVideoType = Arrays.stream(allowedVideoTypeStr.split(Constant.SEPARATOR)).collect(Collectors.toSet());
        allowedDefaultType = Arrays.stream(allowedDefaultTypeStr.split(Constant.SEPARATOR)).collect(Collectors.toSet());

        if (!StringUtils.isEmpty(excludeHeaders)) {
            excludeHeaderSet = Arrays.stream(excludeHeaders.split(","))
                    .map(String::toLowerCase)
                    .collect(Collectors.toSet());
        } else {
            excludeHeaderSet = new HashSet<>();
        }
        if (isApiKeyCheckEnabled) {
            excludeHeaderSet.add("authorization");
        }
    }

    /**
     * 执行知识型Agent，非流式
     *
     * @param executeParams Agent运行参数
     * @return WorkflowRunRsp 保持与工作流返回结构一致
     */
    public Object runAgent(AgentExecuteParams executeParams) {
        if (Constant.AppType.PLAN_EXECUTE.equals(executeParams.getExecuteType())) {
            log.error("Plan execute not support stream=false");
            throw new AgentStudioException(StudioError.NOT_SUPPORT_UN_STREAM_INVOKE);
        }
        checkNonStreamExecuteParams(executeParams);
        checkAndInitExecuteParams(executeParams);

        // 复用工作流运行结果定义，用于非流式信息存储汇总
        WorkflowRunInfo workflowRunInfo = new WorkflowRunInfo();
        workflowRunInfo.setStartTime(executeParams.getStartTime());
        WorkflowRunResult result = new WorkflowRunResult();
        result.setWorkflowRunInfo(workflowRunInfo);

        try {
            Conversation conversation = getConversation(executeParams);
            if (conversation.isOld()) {
                executeParams.setOldConversation(true);
            }

            // 发送请求并等待流式处理完成
            CountDownLatch latch = new CountDownLatch(1);
            invokeJiuWenStreamInterface(executeParams, conversation, null, result, latch);
            try {
                latch.await(agentJiuwenTimeoutMilliSec, TimeUnit.MILLISECONDS);
            } catch (InterruptedException e) {
                throw new AgentStudioException(StudioError.AGENT_RUN_TIMEOUT);
            }
        } catch (AgentStudioException exception) {
            handleRunAgentFailure(executeParams, exception);
            throw exception;
        } catch (Exception exception) {
            handleRunAgentFailure(executeParams, exception);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
        if (Constant.AppType.AGENT.equals(executeParams.getExecuteType())) {
            List<AgentInvokeInfo> invokeList = result.getInvokeList();
            invokeList.sort((o1, o2) -> (int) (o1.getStartTime() - o2.getStartTime()));
            return AgentRunRsp.builder()
                    .startTime(executeParams.getStartTime())
                    .endTime(System.currentTimeMillis())
                    .conversationId(executeParams.getConversationId())
                    .errorCode(workflowRunInfo.getErrorCode())
                    .errorMessage(result.getWorkflowRunInfo().getErrorMessage())
                    .messages(result.getAgentMessageList())
                    .events(invokeList)
                    .filesInfo(result.getKnowledgeBaseFileInfoList())
                    .build();
        }
        return WorkflowRunRsp.builder()
                .nodeInfo(result.getNodeRunInfoList())
                .startTime(executeParams.getStartTime())
                .endTime(System.currentTimeMillis())
                .conversationId(executeParams.getConversationId())
                .errorCode(workflowRunInfo.getErrorCode())
                .errorMessage(result.getWorkflowRunInfo().getErrorMessage())
                .messages(result.getMessageList())
                .knowledgeBaseFileInfoList(result.getKnowledgeBaseFileInfoList())
                .events(result.getEventList())
                .build();
    }

    /**
     * 执行知识型Agent，流式
     *
     * @param executeParams Agent运行参数
     * @return SseEmitter
     */
    public SseEmitter runAgentStream(AgentExecuteParams executeParams) {
        checkAndInitExecuteParams(executeParams);

        SseEmitter sseEmitter = buildSseEmitter(executeParams);
        try {
            Conversation conversation = getConversation(executeParams);
            if (conversation.isOld()) {
                executeParams.setOldConversation(true);
            }

            invokeJiuWenStreamInterface(executeParams, conversation, sseEmitter, null, null);
        } catch (AgentStudioException exception) {
            handleRunAgentFailure(executeParams, exception);
            if (StudioError.OBS_FAILED.equals(exception.getErrorCode())) {
                throw new AgentStudioException(StudioError.AGENT_OR_VERSION_NOT_EXIST);
            }
            ErrorEvent errorEvent = runtimeI18nService.createErrorEvent(exception, null);
            eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                    WorkflowStreamEventFactory.error(errorEvent));
            sseEmitter.complete();
        } catch (Exception exception) {
            handleRunAgentFailure(executeParams, exception);
            ErrorEvent errorEvent = runtimeI18nService.createErrorEvent(exception, null);
            eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                    WorkflowStreamEventFactory.error(errorEvent));
            sseEmitter.complete();
        }
        return sseEmitter;
    }

    private void handleRunAgentFailure(AgentExecuteParams executeParams, Exception exception) {
        log.error("Fail to run agent because [{}]", exception.getMessage(), exception);

        // 出现异常时，需要清理九问会话IR实例，保证下次对话九问service使用最新的IR
        jiuWenService.deleteConversationIr(executeParams.getConversationId());

        // 记录事件
        addAgentExecEvent(AnalyticsEventType.FAIL, executeParams);
    }

    private Conversation getConversation(AgentExecuteParams executeParams) {
        // 1、参数&权限校验
        checkExecuteParams(executeParams);
        AgentMetadata agentMetadata = getAgentMetadata(executeParams);
        if (!executeParams.isWebPage() && !Constant.Agent.TREASURE_BOX_AGENT.equals(executeParams.getType())
                && !executeParams.getProjectId().equals(agentMetadata.getProjectId())) {
            throw new AgentStudioException(StudioError.INSUFFICIENT_AGENT_RUN_PRIVILEGES);
        }

        // 记忆变量能力屏蔽
        executeParams.setMemoryVariables(new ArrayList<>());
        // 更新versionId（latest场景）
        if (StringUtils.isNotEmpty(agentMetadata.getVersionId())) {
            executeParams.setVersionId(agentMetadata.getVersionId());
        }
        executeParams.setUserId(getAgentExecuteUserId());

        // 2、查询历史会话
        Conversation conversation = conversationManagementService.retrieveConversationCore(executeParams.getProjectId(),
                executeParams.getAgentId(), executeParams.getConversationId(), executeParams.getVersionId());
        // 调用方传入历史会话场景下, 使用传入的历史会话覆盖执行参数的历史会话
        if (CollectionUtils.isNotEmpty(executeParams.getHistories())) {
            conversation.setOld(true);
            conversation.setMessageList(executeParams.getHistories());
        }

        log.info("conversation is {}, id {}", conversation, executeParams.getConversationId());

        // 如果会话过程中IR有变更，则需要及时清理九问会话的IR实例,已发布ir不会变无需清理
        if (conversation.getLastUpdateTime() > 0 && conversation.getLastUpdateTime() <= agentMetadata.getUpdatedAt()
                && StringUtils.isEmpty(executeParams.getVersionId())) {
            log.info("conversation lastUpdateTime:{} agentMetadata updateAt:{} version:{} agentId:{}",
                    conversation.getLastUpdateTime(), agentMetadata.getUpdatedAt(), executeParams.getVersionId(),
                    agentMetadata.getAgentId());
            jiuWenService.deleteConversationIr(executeParams.getConversationId(), getAgentIrObsPath(executeParams));
        }
        return conversation;
    }

    private void checkAndInitExecuteParams(AgentExecuteParams executeParams) {
        // 对执行类型进行校验，必须为agent或controller
        String executeType = executeParams.getExecuteType();
        if (!executeType.equals(Constant.AppType.AGENT) && !executeType.equals(Constant.AppType.CONTROLLER)
            && !executeType.equals(Constant.AppType.DEEP_RESEARCH) && !executeType.equals(Constant.AppType.PLAN_EXECUTE)) {
            log.error("agent execute type must be agent, controller or deepresearch! agent execute type is {}",
                executeType);
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }
        if (!CollectionUtils.isEmpty(executeParams.getFileUrls())
                && executeParams.getFileUrls().size() > conversionFileMaxNum) {
            throw new AgentStudioException(StudioError.AGENT_CONVERSATION_FILE_NUM, conversionFileMaxNum);
        }

        if (Strings.CI.equals(executeType, Constant.AppType.CONTROLLER)) {
            if (executeParams.getInputs() != null) {
                Object queryParams = executeParams.getInputs().get(Constant.Jiuwen.USER_MSG_FIELD);
                if (queryParams == null || StringUtils.isBlank(queryParams.toString())) {
                    log.error("query param is empty: {}", queryParams);
                    throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                            List.of("parameter query is needed"));
                }
            } else {
                log.error("inputs param is empty");
                throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID,
                        List.of("parameter inputs.query is needed"));
            }
        }

        executeParams.setToken(RequestContextUtils.getRequestAuthToken());
    }

    private void checkNonStreamExecuteParams(AgentExecuteParams executeParams) {
        if (Constant.AppType.DEEP_RESEARCH.equals(executeParams.getExecuteType())) {
            log.error("deep research is only supported for SSE!");
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }
    }

    private SseEmitter buildSseEmitter(AgentExecuteParams executeParams) {
        SseEmitter sseEmitter = Constant.AppType.DEEP_RESEARCH.equals(executeParams.getExecuteType())
            ? new SseEmitter(deepResearchSseTimeoutMilliSec) : new SseEmitter(agentSseTimeoutMilliSec);

        // SSE响应超时的处理：构造结构化错误事件发送到前端
        sseEmitter.onTimeout(() -> {
            log.error("SSE connection timed out, conversationId [{}]", executeParams.getConversationId());
            try {
                // 根据执行类型推断超时原因，构造结构化错误事件
                String errorType = classifySseTimeoutError(executeParams);
                String errorCode = "SSE_TIMEOUT_" + errorType.toUpperCase(Locale.ROOT);
                String userMessage = getSseTimeoutUserMessage(errorType);

                ErrorEvent timeoutError = new ErrorEvent()
                        .setErrorMsg(userMessage)
                        .setErrorReason(errorType)
                        .setErrorCode(errorCode);
                eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                        WorkflowStreamEventFactory.error(timeoutError));
                sendDoneAndComplete(sseEmitter, executeParams);
            } catch (Exception e) {
                log.error("Failed to send SSE timeout error event, conversationId [{}], reason [{}]",
                        executeParams.getConversationId(), e.getMessage());
            }
        });

        // SSE结束后的处理
        sseEmitter.onCompletion(() -> {
        });
        return sseEmitter;
    }

    /**
     * 根据执行上下文推断SSE超时原因
     */
    private String classifySseTimeoutError(AgentExecuteParams executeParams) {
        // 默认分类为模型响应超时
        return "model_timeout";
    }

    /**
     * 根据超时类型获取用户友好的错误提示文案
     */
    private String getSseTimeoutUserMessage(String errorType) {
        switch (errorType) {
            case "model_timeout":
                return "模型响应超时，请稍后重试";
            case "gateway_timeout":
                return "网关响应超时，请检查网络连接";
            case "network_error":
                return "网络连接异常，请检查网络状态";
            case "iteration_exceeded":
                return "执行迭代超限，任务已终止";
            default:
                return "响应超时，请稍后重试";
        }
    }

    private Map<String, String> initHeaders() {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest httpServletRequest = Optional.ofNullable(attrs)
                .map(ServletRequestAttributes::getRequest)
                .orElse(null);
        if (httpServletRequest == null) {
            return new HashMap<>();
        }
        Enumeration<String> names = httpServletRequest.getHeaderNames();
        Map<String, String> headers = new HashMap<>();
        while (names.hasMoreElements()) {
            String name = names.nextElement().toLowerCase(Locale.ROOT);
            String value = httpServletRequest.getHeader(name);
            if (!excludeHeaderSet.contains(name) && !StringUtils.isEmpty(value)) {
                headers.put(name, value);
            }
        }
        return headers;
    }

    // 构造请求信息，调用九问执行IR的流式接口
    private void invokeJiuWenStreamInterface(AgentExecuteParams executeParams, Conversation conversation,
                                             SseEmitter sseEmitter, WorkflowRunResult result, CountDownLatch latch) {
        MDC.put(REQUEST_ID, executeParams.getRequestId());
        MDC.put(TASK_ID, executeParams.getTaskId());
        RequestContextUtils.setRequestAuthTokenAndProjectId(executeParams.getToken(), executeParams.getProjectId());

        // 初始化敏感词匹配辅助类
        AgentMetadata agentMetadata = getAgentMetadata(executeParams);
        executeParams.setTrieUtils(new SensitiveTrieUtils(Constant.AppType.AGENT, agentMetadata));

        // 输入敏感词匹配
        if (handleInputSensitiveMatch(executeParams, sseEmitter)) {
            if (latch != null) {
                latch.countDown();
            }
            return;
        }

        // 构造请求体
        JiuwenExecutionRequest request = buildJiuWenRequestBody(executeParams, conversation);
        request.setDialogueCount(Math.max(1L, conversation.getDialogueCount()));

        // 添加ir路径 用于trace使用
        executeParams.setIrPath(request.getIrPath());
        String body = com.alibaba.fastjson2.JSON.toJSONString(request);
        log.info("Request jiuwen body is :{}", body);

        // 构造请求头
        Map<String, String> headerMap = initHeaders();
        headerMap.put("Content-Type", "application/json");
        headerMap.put(X_REQUEST_ID, MDC.get(REQUEST_ID));
        headerMap.put(X_TASK_ID, MDC.get(TASK_ID));
        headerMap.put("X-Auth-Token", executeParams.getToken());
        headerMap.put("X-Workspace-Id", StringUtils.isNotEmpty(executeParams.getOwnerWorkspaceId())
                ? executeParams.getOwnerWorkspaceId()
                : opsService.handlerWorkspaceId(true, executeParams.getAgentId(), executeParams.getVersionId()));
        headerMap.put(Constant.OWNER_PROJECT_ID,
                executeParams.getOwnerProjectId() == null ? "" : executeParams.getOwnerProjectId());
        headerMap.put("X-Owner-Domain-Id",
                executeParams.getOwnerDomainId() == null ? "" : executeParams.getOwnerDomainId());
        headerMap.put(Constants.Header.X_LANGUAGE.toLowerCase(Locale.ROOT), RequestHeaderHolderUtils.getRequestLanguage());

        if (headerMap.keySet().stream().noneMatch(key -> key.equalsIgnoreCase("x-call-type"))) {
            headerMap.put("x-call-type", executeParams.getTraceMode());
        }
        // 银行定制场景
        if (KnowledgeSourceEnum.CUSTOM.toString().equalsIgnoreCase(knowledgeSource)) {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            HttpServletRequest httpServletRequest = attrs.getRequest();
            headerMap.put(Constants.CustomModel.CUSTOM_TOKEN,
                    httpServletRequest.getHeader(Constants.CustomModel.CUSTOM_TOKEN));
            headerMap.put(Constants.CustomModel.CUSTOM_USER_ID,
                    httpServletRequest.getHeader(Constants.CustomModel.CUSTOM_USER_ID));
        }
        // 上报OpsAgent数据需要在调用engine时，使能debug
        if (executeParams.isUploadOpsSwitch() || executeParams.isDebug()) {
            headerMap.put(INVOKE_HEADER_KEY.toLowerCase(Locale.ROOT), Constant.Common.INVOKE_MOD_DEBUG);
        }

        // 初始化对话消息列表
        List<Message> messageList = new ArrayList<>();
        if (executeParams.isHistoryEnabled()) {
            Message message = new Message().setRole(MessageRole.USER.name().toLowerCase(Locale.ROOT))
                    .setContent(executeParams.getQuery())
                    .setCreateTime(System.currentTimeMillis())
                    .setEnableHistory(executeParams.isHistoryEnabled());
            if (!CollectionUtils.isEmpty(executeParams.getFiles())) {
                message.setFiles(executeParams.getFiles());
            }
            messageList.add(message);
        }
        executeParams.setMessages(messageList);

        // 根据IR文件判断是否调用DeepResearch运行时
        String baseUrl =  Constant.AppType.DEEP_RESEARCH.equals(executeParams.getExecuteType())
                ? jiuwenDeepResearchUrl
                : jiuwenBaseUrl;

        // 调用九问执行IR的流式接口
        PerformUtils.recordAgent(executeParams, Constant.Performance.ENGINE_START, System.currentTimeMillis());
        executeParams.setExecutionId(headerMap.get(X_TASK_ID));
        okHttpUtils.stream(baseUrl + runApi, headerMap, body, getEventListener(executeParams, sseEmitter, result, latch));
    }

    private EventSourceListener getEventListener(AgentExecuteParams executeParams, SseEmitter sseEmitter,
                                                 WorkflowRunResult result, CountDownLatch latch) {
        Map<String, String> curHeaders = RequestContextUtils.getHeaders();
        String language = RequestHeaderHolderUtils.getRequestLanguage();
        return new EventSourceListener() {
            final AgentCtrlTraceData traceData = new AgentCtrlTraceData();

            @Override
            public void onOpen(@NotNull EventSource eventSource, @NotNull Response response) {
                long start = System.currentTimeMillis();
                traceData.setStartTime(start);
                MDC.put(REQUEST_ID, executeParams.getRequestId());
                MDC.put(TASK_ID, executeParams.getTaskId());
                RequestContextUtils.setRequestAuthTokenAndUserId(executeParams.getToken(), executeParams.getProjectId(),
                        executeParams.getUserId());
                RequestContextUtils.setHeaders(curHeaders);
                RequestHeaderHolderUtils.setRequestLanguage(language);
                PerformUtils.accumulationAgent(executeParams, Constant.Performance.MANAGER,
                        System.currentTimeMillis() - start);

                sendMemoryRefreshEvent(executeParams, sseEmitter);

                // 发送心跳
                if (sseEmitter != null) {
                    executeParams.setHeartbeatFuture(CompletableFuture.runAsync(() -> {
                        try {
                            while (System.currentTimeMillis() - start < agentSseTimeoutMilliSec) {
                                Thread.sleep(heartbeatInterval * 1000L);
                                WorkflowRunStreamRsp heartBeatEvent = new WorkflowRunStreamRsp().setEvent(
                                                WorkflowStreamEventEnum.HEARTBEAT.name().toLowerCase(Locale.ROOT))
                                        .setCreatedTime(System.currentTimeMillis());
                                SseEmitterUtils.sendEvent(sseEmitter, heartBeatEvent);
                            }
                        } catch (Throwable e) {
                            log.info("heartbeat end: {}.", e.getMessage());
                        }
                    }));
                }
            }

            @Override
            public void onEvent(@NotNull EventSource eventSource, @Nullable String id, @Nullable String type,
                                @NotNull String data) {
                try {
                    long start = System.currentTimeMillis();
                    PerformUtils.recordFirstAgentEvent(executeParams, Constant.Performance.FIRST_EVENT, start);
                    if (Constant.AppType.DEEP_RESEARCH.equals(executeParams.getExecuteType())) {
                        processOnDeepResearchEvent(data, executeParams, sseEmitter);
                    } else {
                        processOnEvent(data, executeParams, sseEmitter, result, eventSource, traceData);
                    }
                    PerformUtils.accumulationAgent(executeParams, Constant.Performance.MANAGER,
                            System.currentTimeMillis() - start);
                } catch (Exception e) {
                    log.error("processEvent {} exception: ", data, e);
                }
            }

            private void cancelFuture() {
                try {
                    if (executeParams.getHeartbeatFuture() != null) {
                        executeParams.getHeartbeatFuture().cancel(true);
                    }
                } catch (Throwable e) {
                    log.warn("Close fail. {}", e.getMessage());
                }
            }

            @Override
            public void onFailure(@NotNull EventSource eventSource, @Nullable Throwable throwable,
                                  @Nullable Response response) {
                if (executeParams.isCanceled()) {
                    traceData.setStatus("canceled");
                    onClosed(eventSource);
                    return;
                }
                cancelFuture();

                ErrorEvent errorEvent = runtimeI18nService.createErrorEvent(throwable, response);
                String errMsg = errorEvent.getErrorMsg();

                // 非流式，记录错误信息
                if (result != null) {
                    WorkflowRunInfo workflowRunInfo = result.getWorkflowRunInfo();
                    workflowRunInfo.setErrorMessage(errMsg);
                    workflowRunInfo.setErrorCode(StudioError.UNEXPECTED_ERROR.getFullCode());
                }
                countDown(latch);

                long start = System.currentTimeMillis();
                executeParams.setSuccess(-1);
                PerformUtils.recordFirstAgentEvent(executeParams, Constant.Performance.FIRST_EVENT, start);
                log.error("An error occurred when receiving sse message: [{}].", errMsg);

                // 九问服务报错时，需要清理九问会话IR实例，保证下次对话九问service使用最新的IR
                RequestContextUtils.setRequestAuthTokenAndProjectId(executeParams.getToken(),
                        executeParams.getProjectId());
                jiuWenService.deleteConversationIr(executeParams.getConversationId());


                log.warn("get agent failure event, sent default error event");
                eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                        WorkflowStreamEventFactory.error(errorEvent));

                // 记录事件
                addAgentExecEvent(AnalyticsEventType.FAIL, executeParams);

                MDC.put(REQUEST_ID, executeParams.getRequestId());
                MDC.put(TASK_ID, executeParams.getTaskId());
                long end = System.currentTimeMillis();
                PerformUtils.accumulationAgent(executeParams, Constant.Performance.MANAGER, end - start);
                PerformUtils.recordAgent(executeParams, Constant.Performance.ENGINE_END, end);
                PerformUtils.recordAgent(executeParams, Constant.Performance.END, end);
                PerformUtils.agentLog(executeParams);
                MDC.put(REQUEST_ID, null);

                ModelApiLog apiLog = executeParams.getApiLog();
                apiLog.setReason(errMsg).setStatus("failed").setInput(executeParams.getQuery());
                apiLogService.saveSecurityCenterLog(apiLog);
                RequestHeaderHolderUtils.clear();
            }

            @Override
            public void onClosed(@NotNull EventSource eventSource) {
                cancelFuture();

                log.info("End to receive sse message.");

                long start = System.currentTimeMillis();
                PerformUtils.recordFirstAgentEvent(executeParams, Constant.Performance.FIRST_EVENT, start);

                sendMemoryRefreshEvent(executeParams, sseEmitter);

                processOnClosed(sseEmitter, executeParams, traceData.isBlock());

                countDown(latch);

                // 记录事件
                addAgentExecEvent(AnalyticsEventType.COMPLETE, executeParams);

                MDC.put(REQUEST_ID, executeParams.getRequestId());
                MDC.put(TASK_ID, executeParams.getTaskId());
                long end = System.currentTimeMillis();
                PerformUtils.accumulationAgent(executeParams, Constant.Performance.MANAGER, end - start);
                PerformUtils.recordAgent(executeParams, Constant.Performance.ENGINE_END, end);
                PerformUtils.recordAgent(executeParams, Constant.Performance.END, end);
                PerformUtils.agentLog(executeParams);
                MDC.put(REQUEST_ID, null);

                ModelApiLog apiLog = executeParams.getApiLog();
                apiLog.setReason(executeParams.isCanceled() ? "canceled by content review" : "")
                        .setStatus(executeParams.isCanceled() ? "failed" : "success")
                        .setInput(executeParams.getQuery());
                apiLogService.saveSecurityCenterLog(apiLog);

                conversationManagementService.processAgentInteraction(executeParams);
                RequestHeaderHolderUtils.clear();
            }

            private void countDown(CountDownLatch latch) {
                if (latch != null) {
                    latch.countDown();
                }
            }
        };
    }

    /**
     * 发送记忆更新事件
     *
     * @param executeParams
     * @param sseEmitter
     */
    private void sendMemoryRefreshEvent(AgentExecuteParams executeParams, SseEmitter sseEmitter) {
        try {
            String userId = executeParams.getUserId();
            String memoryRepoId = executeParams.getMemoryRepoId();
            String conversationId = executeParams.getConversationId();

            LongTermMemoryRefreshEvent longTermMemoryRefreshEvent
                    = userMemoryCacheMgmtService.getStoredLongTermMemoryRefreshEvent(userId, memoryRepoId, conversationId);

            if (longTermMemoryRefreshEvent != null) {
                log.info("Exists stored memory refresh event. Send it.");
                sseEmitter.send(longTermMemoryRefreshEvent);
                userMemoryCacheMgmtService.deleteStoredLongTermMemoryRefreshEvent(userId, memoryRepoId, conversationId);
            }
        } catch (IOException e) {
            log.error("Send stored memory refresh event failed.", e);
        }
    }

    private boolean handleInputSensitiveMatch(AgentExecuteParams executeParams, SseEmitter sseEmitter) {
        String executeType = executeParams.getExecuteType();
        if (Constant.AppType.CONTROLLER.equals(executeType) || Constant.AppType.PLAN_EXECUTE.equals(executeType)) {
            return false;
        }
        SensitiveTrieUtils trieUtils = executeParams.getTrieUtils();
        String query = executeParams.getQuery();
        if (!trieUtils.isInputMatchEnabled() || StringUtils.isBlank(query)) {
            return false;
        }
        Pair<Integer, String> matchResult = trieUtils.handleSensitiveMatch(query, true);
        if (matchResult.getLeft() == 0) {
            return false;
        }
        if (sseEmitter == null) {
            return false;
        }
        AgentEvent agentEvent = new AgentEvent();
        agentEvent.setEvent(EventType.MESSAGE.toString())
                .setContent(matchResult.getRight())
                .setCreatedTime(System.currentTimeMillis());
        sendSseData(sseEmitter, agentEvent);
        sendDoneAndComplete(sseEmitter, executeParams);
        return true;
    }

    public void processOnEvent(String sseData, AgentExecuteParams executeParams, SseEmitter sseEmitter,
                               WorkflowRunResult result, EventSource eventSource, AgentCtrlTraceData traceData) {
        JiuwenAgentEvent eventObj = parseJiuWenEventFromSseData(sseData);
        if (Objects.isNull(eventObj)) {
            return;
        }
        String event = eventObj.getEvent();
        JiuwenEventType eventType;
        try {
            eventType = JiuwenEventType.valueOf(event.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException exception) {
            log.warn("Event is not support: [{}]", event);
            return;
        }
        switch (executeParams.getExecuteType()) {
            case Constant.AppType.AGENT: {
                processOnAgentEvent(sseData, executeParams, sseEmitter, result, eventSource, eventType, eventObj,
                        event);
                break;
            }
            case Constant.AppType.CONTROLLER: {
                if (eventType != JiuwenEventType.TASK_END) {
                    traceData.setPreEventType(eventType);
                }
                processOnControllerEvent(sseData, executeParams, sseEmitter, result, eventType, eventObj, traceData);
                break;
            }
            case Constant.AppType.PLAN_EXECUTE: {
                processOnPlanAgentEvent(sseData, executeParams, sseEmitter, result, eventSource, eventType, eventObj,
                        event);
                break;
            }
        }
    }

    void processOnControllerEvent(String sseData, AgentExecuteParams executeParams, SseEmitter sseEmitter,
                                  WorkflowRunResult result, JiuwenEventType eventType, JiuwenAgentEvent eventObj, AgentCtrlTraceData traceData) {
        // 流式
        if (sseEmitter != null) {
            switch (eventType) {
                case MESSAGE -> processOnControllerMessage(sseEmitter, eventObj, executeParams);
                case MESSAGE_END -> processOnControllerMessageEnd(sseEmitter, eventObj, executeParams);
                case INTERMEDIATE_MESSAGE ->
                        processOnControllerIntermediateMessage(eventObj, executeParams, sseEmitter);
                case ERROR -> processOnError(sseEmitter, eventObj, executeParams, traceData);
                case AGENT_INTERRUPTED -> blockHandler(executeParams, traceData);
                case WORKFLOW_BLOCKED -> passBlockThrough(sseData, sseEmitter, executeParams, traceData);
                case WORKFLOW_RESUME -> passResumeThrough(sseData, sseEmitter, executeParams, traceData);
                case WORKFLOW_START, WORKFLOW_END, TASK_TERMINATED -> passThrough(sseData, sseEmitter, executeParams);
                case WORKFLOW_NODE_MESSAGE ->
                        processOnControllerWorkflowNodeMessage(sseData, result, executeParams, traceData, sseEmitter);
                case AGENT_NODE_MESSAGE -> processOnCtrlAgentNodeMessage(sseData, eventObj, executeParams, traceData, sseEmitter);
                case TASK_END -> processTaskEnd(sseEmitter, executeParams, traceData);
                case SCENE_MATCH, PLAN_START, PLAN_END, STEP_START, STEP_END, TASK_COMPLETE, TASK_START ->
                        agentEventPassThrough(sseData, sseEmitter, executeParams);
                case FUNCTION_CALL -> processOnFunctionCall(sseEmitter, eventObj, executeParams);
                case FUNCTION_CALL_END -> processOnFunctionCallEnd(sseEmitter, eventObj, executeParams);
                case API_EXEC_DATA -> processOnApiExecData(sseEmitter, eventObj, executeParams);
                case STATISTIC_DATA -> processOnStaticData(sseEmitter, eventObj, executeParams);
                case SUMMARY_RESPONSE -> processOnSummaryResponse(sseEmitter, eventObj, executeParams);
                case INTENT -> agentEventPassThrough(sseData, sseEmitter, executeParams);
                case DONE -> processOnControllerDoneMessage(eventObj, executeParams);
                default -> log.warn("not process event: [{}]", eventType);
            }
            return;
        }
        // 非流式
        if (result != null) {
            switch (eventType) {
                case MESSAGE_END -> processOnControllerMessageEnd(eventObj, result, executeParams);
                case INTERMEDIATE_MESSAGE -> processOnControllerIntermediateMessage(eventObj, executeParams, null);
                case WORKFLOW_NODE_MESSAGE ->
                        processOnControllerWorkflowNodeMessage(sseData, result, executeParams, traceData,sseEmitter);
                case ERROR -> processOnError(eventObj, result, executeParams, traceData);
                case AGENT_INTERRUPTED -> blockHandler(executeParams, traceData);
                case WORKFLOW_BLOCKED -> passBlockThrough(sseData, result, executeParams, traceData);
                case WORKFLOW_RESUME -> passResumeThrough(sseData, result, executeParams, traceData);
                case WORKFLOW_START, WORKFLOW_END, TASK_TERMINATED -> passThrough(sseData, result, executeParams);
                case AGENT_NODE_MESSAGE -> processOnCtrlAgentNodeMessage(sseData, eventObj, executeParams, traceData, sseEmitter);
                case TASK_END -> processTaskEnd(null, executeParams, traceData);
                case DONE -> processOnControllerDoneMessage(eventObj, executeParams);
                default -> log.debug("not process event: [{}]", eventType);
            }
        }
    }

    private void processOnAgentEvent(String sseData, AgentExecuteParams executeParams, SseEmitter sseEmitter, WorkflowRunResult result,
                                     EventSource eventSource, JiuwenEventType eventType, JiuwenAgentEvent eventObj, String event) {
        // 流式
        if (sseEmitter != null) {
            switch (eventType) {
                case START -> processOnStart(sseEmitter, eventObj);
                case MESSAGE -> {
                    processOnMessage(sseEmitter, eventObj, executeParams);
                    SensitiveTrieUtils.MatchResultWrapper resultWrapper = processOnSensitiveMessage(executeParams,
                            sseEmitter, eventObj, false);
                    // 存在兜底回复匹配，结束流
                    if (resultWrapper != null
                            && (resultWrapper.getOp() & SensitiveTrie.SensitiveOp.REPLY.getCode()) > 0) {
                        log.info("Fallback response matched, stream ended. : {}", eventObj);
                        executeParams.setCanceled(true);
                        eventSource.cancel();
                    }
                }
                case MESSAGE_END -> processOnControllerMessageEnd(sseEmitter, eventObj, executeParams);
                case FUNCTION_CALL -> processOnFunctionCall(sseEmitter, eventObj, executeParams);
                case FUNCTION_CALL_END -> processOnFunctionCallEnd(sseEmitter, eventObj, executeParams);
                case API_EXEC_DATA -> processOnApiExecData(sseEmitter, eventObj, executeParams);
                case AGENT_NODE_MESSAGE -> {
                    processOnAgentNodeMessage(eventObj, executeParams, null);
                    if (executeParams.isDebug()) {
                        agentEventPassThrough(sseData, sseEmitter, executeParams);
                    }
                }
                case INTERMEDIATE_MESSAGE -> processOnIntermediateMessage(sseEmitter, eventObj, executeParams);
                case STATISTIC_DATA -> processOnStaticData(sseEmitter, eventObj, executeParams);
                case SUMMARY_RESPONSE -> processOnSummaryResponse(sseEmitter, eventObj, executeParams);
                case AGENT_INTERRUPTED, SCENE_MATCH, PLAN_START, PLAN_END, STEP_START, STEP_END, TASK_COMPLETE, TASK_START, TASK_END, WORKFLOW_BLOCKED, WORKFLOW_END, WORKFLOW_RESUME, WORKFLOW_START ->
                        agentEventPassThrough(sseData, sseEmitter, executeParams);
                case DONE -> processOnControllerDoneMessage(eventObj, executeParams);
                case ERROR -> processOnError(sseEmitter, eventObj, executeParams, new AgentCtrlTraceData());
                default -> log.warn("not process event: [{}]", event);
            }
        }

        // 非流式
        if (result != null) {
            switch (eventType) {
                case AGENT_NODE_MESSAGE -> processOnAgentNodeMessage(eventObj, executeParams, result);
                case INTERMEDIATE_MESSAGE -> processOnIntermediateMessage(null, eventObj, executeParams);
                case SUMMARY_RESPONSE -> processOnSummaryResponse(eventObj, result, executeParams);
                case ERROR -> processOnError(eventObj, result, executeParams, new AgentCtrlTraceData());
                case API_EXEC_DATA -> processOnKnowledgeBaseMessage(eventObj, result);
                default -> log.warn("not process event: [{}]", event);
            }
        }
    }

    private void processOnPlanAgentEvent(String sseData, AgentExecuteParams executeParams, SseEmitter sseEmitter, WorkflowRunResult result,
                                         EventSource eventSource, JiuwenEventType eventType, JiuwenAgentEvent eventObj, String event) {
        // 流式
        if (sseEmitter != null) {
            switch (eventType) {
                case START -> processOnStart(sseEmitter, eventObj);
                case MESSAGE -> {
                    processOnControllerMessage(sseEmitter, eventObj, executeParams);
                    SensitiveTrieUtils.MatchResultWrapper resultWrapper = processOnSensitiveMessage(executeParams,
                            sseEmitter, eventObj, false);
                    // 存在兜底回复匹配，结束流
                    if (resultWrapper != null
                            && (resultWrapper.getOp() & SensitiveTrie.SensitiveOp.REPLY.getCode()) > 0) {
                        log.info("Fallback response matched, stream ended. : {}", eventObj);
                        executeParams.setCanceled(true);
                        eventSource.cancel();
                    }
                }
                case MESSAGE_END -> processOnControllerMessageEnd(sseEmitter, eventObj, executeParams);
                case FUNCTION_CALL -> processOnFunctionCall(sseEmitter, eventObj, executeParams);
                case FUNCTION_CALL_END -> processOnFunctionCallEnd(sseEmitter, eventObj, executeParams);
                case API_EXEC_DATA -> processOnApiExecData(sseEmitter, eventObj, executeParams);
                case AGENT_NODE_MESSAGE -> processOnAgentNodeMessage(eventObj, executeParams, null);
                case INTERMEDIATE_MESSAGE -> processOnIntermediateMessage(sseEmitter, eventObj, executeParams);
                case STATISTIC_DATA -> processOnStaticData(sseEmitter, eventObj, executeParams);
                case SUMMARY_RESPONSE -> processOnSummaryResponse(sseEmitter, eventObj, executeParams);
                case AGENT_INTERRUPTED, SCENE_MATCH, PLAN_START, PLAN_END, STEP_START, STEP_END, TASK_COMPLETE, TASK_START, TASK_END, WORKFLOW_BLOCKED, WORKFLOW_END, WORKFLOW_RESUME, WORKFLOW_START ->
                        agentEventPassThrough(sseData, sseEmitter, executeParams);
                case DONE -> processOnControllerDoneMessage(eventObj, executeParams);
                case ERROR -> processOnError(sseEmitter, eventObj, executeParams, new AgentCtrlTraceData());
                default -> log.warn("not process event: [{}]", event);
            }
        }
    }

    private void blockHandler(AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        if (executeParams.isDebug() || executeParams.isUploadOpsSwitch()) {
            log.info("Agent task is block. recive task block message.");
        }
        traceData.setBlock(true);
        conversationManagementService.saveTaskId(executeParams.getAgentId(), executeParams.getConversationId(),
                MDC.get(TASK_ID));
    }

    private void processOnDeepResearchEvent(String sseData, AgentExecuteParams executeParams, SseEmitter sseEmitter) {
        JiuwenDeepResearchEvent eventObj = parseJiuWenEventFromSseData(sseData, JiuwenDeepResearchEvent.class);
        if (Objects.isNull(eventObj)) {
            return;
        }
        String event = eventObj.getEvent();
        JiuwenEventType eventType;
        try {
            eventType = JiuwenEventType.valueOf(event.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException exception) {
            log.warn("Event is not support: [{}]", event);
            return;
        }

        // Deep Research only supports streaming
        if (sseEmitter == null) {
            log.error("Deep Research only support stream.");
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }
        switch (eventType) {
            case START, MESSAGE, DONE -> processOnDRStream(sseEmitter, eventObj, executeParams, eventType);
            case SUMMARY_RESPONSE, ERROR, WAITING_USER_INPUT, HEARTBEAT -> sendDeepResearchData(sseEmitter, eventObj);
            default -> log.warn("not process event: [{}]", event);
        }
    }

    private void processOnDRStream(SseEmitter sseEmitter, JiuwenDeepResearchEvent eventObj,
        AgentExecuteParams executeParams, JiuwenEventType eventType) {
        if (StringUtils.isBlank(eventObj.getMessageId())) {
            log.warn("Message id is null, ignore this event: {}", eventObj);
            return;
        }

        int chunkCount = executeParams.getMessageChunkCount().incrementAndGet();
        if (chunkCount >= 300 && executeParams.getMessageChunkCount().compareAndSet(chunkCount, 0)) {
            // 防止组装超时
            sendDeepResearchHeartBeat(sseEmitter, eventObj);
        }

        MessageChunkCache messageChunkCache = getMessageChunkCache(executeParams, eventObj.getMessageId());
        messageChunkCache.addChunk(eventObj.getContent());

        if (eventType == JiuwenEventType.DONE && messageChunkCache.containsStartChunk()) {
            // 完整数据，直接发送
            sendAggregatedMessage(sseEmitter, eventObj, messageChunkCache);
        } else if (Constant.DeepResearch.SUB_REPORTER_NODE.equals(eventObj.getAgent())) {
            processOnDRSubReporter(sseEmitter, eventObj, messageChunkCache, eventType);
        }

        if (eventType == JiuwenEventType.DONE) {
            // 消息结束，移除缓存
            executeParams.getMessageChunkMap().remove(eventObj.getMessageId());
        }
    }

    private void sendDeepResearchHeartBeat(SseEmitter sseEmitter, JiuwenDeepResearchEvent eventObj) {
        String heartbeat = JiuwenEventType.HEARTBEAT.name().toLowerCase(Locale.ROOT);
        sendDeepResearchData(
                sseEmitter,
                new JiuwenDeepResearchEvent()
                        .setConversationId(eventObj.getConversationId())
                        .setAgent(heartbeat)
                        .setMessageId(heartbeat)
                        .setContent("")
                        .setMessageType("message_chunk")
                        .setEvent(heartbeat)
                        .setCreatedTime(eventObj.getCreatedTime())
        );
    }

    private MessageChunkCache getMessageChunkCache(AgentExecuteParams executeParams, String messageId) {
        Map<String, MessageChunkCache> messageMap = executeParams.getMessageChunkMap();
        messageMap.computeIfAbsent(messageId, k -> new MessageChunkCache());
        return messageMap.get(messageId);
    }

    private void sendAggregatedMessage(SseEmitter sseEmitter, JiuwenDeepResearchEvent eventObj,
        MessageChunkCache messageChunkCache) {
        eventObj.setContent(messageChunkCache.drain()).setEvent(EventType.SUMMARY_RESPONSE.toString());
        sendDeepResearchData(sseEmitter, eventObj);
    }

    private void processOnDRSubReporter(SseEmitter sseEmitter, JiuwenDeepResearchEvent eventObj,
        MessageChunkCache messageChunkCache, JiuwenEventType eventType) {
        if (!messageChunkCache.isFull() && eventType != JiuwenEventType.DONE) {
            // sub_reporter节点数据需要组装拼接
            return;
        }

        if (messageChunkCache.containsStartChunk()) {
            sendDeepResearchStreamFlag(sseEmitter, eventObj, EventType.START);
        }

        eventObj.setContent(messageChunkCache.drain()).setEvent(EventType.MESSAGE.toString());
        sendDeepResearchData(sseEmitter, eventObj);

        if (eventType == JiuwenEventType.DONE) {
            sendDeepResearchStreamFlag(sseEmitter, eventObj, EventType.DONE);
        }
    }

    private void sendDeepResearchStreamFlag(SseEmitter sseEmitter, JiuwenDeepResearchEvent eventObj,
        EventType eventType) {
        sendDeepResearchData(
                sseEmitter,
                new JiuwenDeepResearchEvent()
                        .setConversationId(eventObj.getConversationId())
                        .setAgent(eventObj.getAgent())
                        .setMessageId(eventObj.getMessageId())
                        .setRole(eventObj.getRole())
                        .setContent("")
                        .setMessageType(eventObj.getMessageType())
                        .setEvent(eventType.toString())
                        .setCreatedTime(eventObj.getCreatedTime())
                        .setSectionIdx(eventObj.getSectionIdx())
        );
    }

    private void passResumeThrough(String sseData, WorkflowRunResult result, AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        traceData.setResume(true);
        passThrough(sseData, result, executeParams);
    }

    private void passBlockThrough(String sseData, WorkflowRunResult result, AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        blockHandler(executeParams, traceData);
        passThrough(sseData, result, executeParams);
    }

    private void processOnKnowledgeBaseMessage(JiuwenAgentEvent eventObj, WorkflowRunResult result) {
        JiuwenAgentEventData eventData = eventObj.getData();
        ApiExecDataEventAnswer pluginRsp = parseEventDataAnswer(eventData.getAnswer(), ApiExecDataEventAnswer.class);
        if (Objects.isNull(pluginRsp)) {
            log.error("pluginRsp can not be null, eventData [{}].", eventData);
            return;
        }
        if (!Constant.KnowledgeRetrievalNode.RETRIEVAL.equals(pluginRsp.getName())) {
            return;
        }
        result.setKnowledgeBaseFileInfoList(
                knowledgeBaseFileInfoService.getKnowledgeBaseFileInfosFromPlugin(pluginRsp));
    }

    private void passThrough(String sseData, WorkflowRunResult result, AgentExecuteParams executeParams) {
        if (!executeParams.isDebug()) {
            return;
        }
        WorkflowRunStreamRsp workflowRunStreamRsp = WorkflowStreamEventFactory.workflowPassThrough(sseData,
                executeParams.getConversationId());
        if (workflowRunStreamRsp != null) {
            result.getEventList().add(workflowRunStreamRsp);
        }
    }

    private void passResumeThrough(String sseData, SseEmitter sseEmitter, AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        traceData.setResume(true);
        passThrough(sseData, sseEmitter, executeParams);
    }

    private void passBlockThrough(String sseData, SseEmitter sseEmitter, AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        blockHandler(executeParams, traceData);
        passThrough(sseData, sseEmitter, executeParams);
    }

    private void passThrough(String sseData, SseEmitter sseEmitter, AgentExecuteParams executeParams) {
        if (!executeParams.isDebug()) {
            return;
        }
        agentEventPassThrough(sseData, sseEmitter, executeParams);
    }

    private void agentEventPassThrough(String sseData, SseEmitter sseEmitter, AgentExecuteParams executeParams) {
        WorkflowRunStreamRsp workflowRunStreamRsp = WorkflowStreamEventFactory.workflowPassThrough(sseData,
                executeParams.getConversationId());
        if (workflowRunStreamRsp == null) {
            log.error("pass throught event is empty.");
            return;
        }
        eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter, workflowRunStreamRsp);
    }

    // agent开始执行
    private void processOnStart(SseEmitter sseEmitter, JiuwenAgentEvent eventObj) {
        AgentEvent agentEvent = new AgentEvent();
        agentEvent.setEvent(EventType.START.toString()).setCreatedTime(eventObj.getCreatedTime());
        sendSseData(sseEmitter, agentEvent);
    }

    // agent执行的消息
    private void processOnMessage(SseEmitter sseEmitter, JiuwenAgentEvent eventObj, AgentExecuteParams executeParams) {
        Object answerObj = eventObj.getData().getAnswer();
        String answer = answerObj != null ? answerObj.toString() : null;// answer无内容，说明是模型思考内容，不传值
        
        // 兜底敏感词过滤：确保发送给前端的message事件内容已过滤敏感词
        SensitiveTrieUtils trieUtils = executeParams.getTrieUtils();
        if (trieUtils != null && trieUtils.isOutputMatchEnabled() && StringUtils.isNotEmpty(answer)) {
            answer = trieUtils.handleSensitiveMatch(answer, false).getRight();
        }
        
        AgentEvent agentEvent = new AgentEvent();
        agentEvent.setEvent(EventType.MESSAGE.toString())
                .setContent(answer).setReasoningContent(eventObj.getData().getThink())
                .setCreatedTime(eventObj.getCreatedTime());
        sendSseData(sseEmitter, agentEvent);

        executeParams.getApiLog()
                .getOutputMap()
                .computeIfAbsent("agent", k -> new StringBuilder())
                .append(answer);
    }

    public SensitiveTrieUtils.MatchResultWrapper processOnSensitiveMessage(AgentExecuteParams executeParams,
                                                                           SseEmitter sseEmitter, JiuwenAgentEvent eventObj, boolean isFinished) {
        SensitiveTrieUtils trieUtils = executeParams.getTrieUtils();
        if (!trieUtils.isOutputMatchEnabled()) {
            return null;
        }
        Object answer = eventObj.getData().getAnswer();
        String text = isFinished || answer == null ? "" : answer.toString();
        SensitiveTrieUtils.MatchResultWrapper resultWrapper = trieUtils.handleOutputSensitiveMatch(text, "agent",
                isFinished);

        if (resultWrapper.getOp() > 0) {
            SensitiveMessageEvent sensitiveMessageEvent = new SensitiveMessageEvent();
            sensitiveMessageEvent.setText(resultWrapper.getText());
            sensitiveMessageEvent.setOffset(resultWrapper.getOffset());
            sensitiveMessageEvent.setCreatedTime(eventObj.getCreatedTime());
            eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                    WorkflowStreamEventFactory.sensitive(sensitiveMessageEvent));
        }
        return resultWrapper;
    }

    // 处理控制器执行消息块
    private void processOnControllerMessage(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
                                            AgentExecuteParams executeParams) {
        MessageEvent messageEvent = new MessageEvent();
        JiuwenAgentEventData jiuwenAgentEventData = eventObj.getData();
        String answer = Optional.ofNullable(jiuwenAgentEventData.getAnswer())
                .map(Object::toString)
                .orElse(StringUtils.EMPTY);
        NodeType nodeType = NodeType.fromJiuwen(jiuwenAgentEventData.getNodeType());
        
        // 兜底敏感词过滤：确保发送给前端的message事件内容已过滤敏感词
        SensitiveTrieUtils trieUtils = executeParams.getTrieUtils();
        if (trieUtils != null && trieUtils.isOutputMatchEnabled() && StringUtils.isNotEmpty(answer)) {
            answer = trieUtils.handleSensitiveMatch(answer, false).getRight();
        }
        
        messageEvent.setText(answer);
        messageEvent.setIndex(eventObj.getIndex());
        messageEvent.setNodeId(jiuwenAgentEventData.getNodeId());
        messageEvent.setNodeName(jiuwenAgentEventData.getNodeName());
        messageEvent.setNodeType(nodeType.getEiType());
        messageEvent.setWorkflowId(jiuwenAgentEventData.getWorkflowId());
        messageEvent.setWorkflowName(jiuwenAgentEventData.getWorkflowName());
        messageEvent.setReasoningContent(jiuwenAgentEventData.getThink());
        eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                WorkflowStreamEventFactory.message(messageEvent));

        executeParams.getApiLog()
                .getOutputMap()
                .computeIfAbsent("agent", k -> new StringBuilder())
                .append(answer);
    }

    // 处理控制器执行结束消息块
    private void processOnControllerMessageEnd(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
                                               AgentExecuteParams executeParams) {
        // 九问message end event也返回message事件，状态为finished
        MessageEvent messageEvent = new MessageEvent();
        JiuwenAgentEventData jiuwenAgentEventData = eventObj.getData();

        String summary = jiuwenAgentEventData.getAnswer().toString();
        // 兜底敏感词过滤：确保发送给前端的message事件内容已过滤敏感词
        SensitiveTrieUtils trieUtils = executeParams.getTrieUtils();
        if (trieUtils != null && trieUtils.isOutputMatchEnabled() && StringUtils.isNotEmpty(summary)) {
            summary = trieUtils.handleSensitiveMatch(summary, false).getRight();
        }
        
        messageEvent.setSummary(summary);
        messageEvent.setText(finishKeepText ? summary : "");
        if (jiuwenAgentEventData.getOriginAnswer() != null) {
            messageEvent.setOrigin(jiuwenAgentEventData.getOriginAnswer().toString());
        }

        messageEvent.setNodeId(jiuwenAgentEventData.getNodeId());
        messageEvent.setNodeName(jiuwenAgentEventData.getNodeName());
        messageEvent.setNodeType(NodeType.fromJiuwen(jiuwenAgentEventData.getNodeType()).getEiType());
        messageEvent.setIsFinished(true);
        messageEvent.setWorkflowId(jiuwenAgentEventData.getWorkflowId());
        messageEvent.setWorkflowName(jiuwenAgentEventData.getWorkflowName());
        handleMessageEnd(eventObj,executeParams);
        eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter, WorkflowStreamEventFactory.message(messageEvent));
    }

    private void handleMessageEnd(JiuwenAgentEvent eventObj,AgentExecuteParams executeParams){
        List<Message> controllerMessages = executeParams.getControllerMessages();
        if(controllerMessages==null){
            controllerMessages = new ArrayList<>();
        }
        Message message = new Message();
        message.setContent(eventObj.getData().getAnswer().toString());
        message.setRole(MessageRole.ASSISTANT.name().toLowerCase(Locale.ROOT));
        message.setCreateTime(eventObj.getCreatedTime());
        controllerMessages.add(message);
        executeParams.setControllerMessages(controllerMessages);
    }

    private void processOnControllerMessageEnd(JiuwenAgentEvent eventObj, WorkflowRunResult result,
                                               AgentExecuteParams executeParams) {
        JiuwenAgentEventData eventData = eventObj.getData();
        NodeMessage nodeMessage = new NodeMessage();
        nodeMessage.setRole(MessageRole.ASSISTANT.name().toLowerCase(Locale.ROOT));
        nodeMessage.setNodeId(eventData.getNodeId());
        nodeMessage.setNodeName(eventData.getNodeName());
        nodeMessage.setNodeType(NodeType.fromJiuwen(eventData.getNodeType()).getEiType());
        nodeMessage.setContent(eventData.getAnswer().toString());
        result.getMessageList().add(nodeMessage);

        executeParams.getApiLog()
                .getOutputMap()
                .computeIfAbsent("agent", k -> new StringBuilder())
                .append(eventData.getAnswer().toString());
    }

    // 调用插件的请求信息
    private void processOnFunctionCall(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
        AgentExecuteParams executeParams) {
        FunctionCallEventAnswer pluginReq = parseEventDataAnswer(eventObj.getData().getAnswer(),
            FunctionCallEventAnswer.class);
        if (Objects.isNull(pluginReq)) {
            log.warn("The format of function_call eventData.answer is incorrect, eventData [{}].", eventObj.getData());
            return;
        }
        // 从九问响应块中解析插件名和参数信息
        String name = pluginReq.getFunctionCall().getName();
        String arguments = pluginReq.getFunctionCall().getArguments();
        if (StringUtils.isNoneBlank(name) && StringUtils.isNoneBlank(arguments)) {
            executeParams.getPluginInputMap().put(name, arguments);
        }
        log.info("Start run plugin, name: [{}], input: [{}], latency: [{}]", name, arguments,
            com.alibaba.fastjson2.JSON.toJSONString(pluginReq.getTimeConsumption()));

        // 插件信息，包括插件名、参数信息、记忆参数提取信息
        Plugin plugin = new Plugin().setName(name).setArguments(arguments);
        Map<String, String> memoryVariablesMap = extractMemoryVariables(executeParams.getMemoryVariables(), arguments);
        if (MapUtils.isNotEmpty(memoryVariablesMap)) {
            plugin.setMemoryVariables(memoryVariablesMap);
        }

        // 当前插件调用是否是workflow
        executeParams.setWorkflow(Boolean.TRUE.equals(pluginReq.isIsWorkflow()));

        AgentEvent agentEvent = new AgentEvent().setEvent(EventType.PLUGIN_START.toString())
            .setPlugin(plugin)
            .setLatency(new Latency().setModel(pluginReq.getTimeConsumption().getModelLatency())
                .setOverall(getOverAllLatency(executeParams)))
            .setType(executeParams.isWorkflow() ? AgentEvent.TypeEnum.WORKFLOW : AgentEvent.TypeEnum.PLUGIN)
            .setCreatedTime(eventObj.getCreatedTime());

        // 当前调用是MCP服务时特殊处理
        if (pluginReq.getFunctionCall().isIsMcp()) {
            agentEvent.setType(AgentEvent.TypeEnum.MCP);
            plugin.setName(pluginReq.getFunctionCall().getServerName());
            plugin.setToolName(name);
        }
        sendSseData(sseEmitter, agentEvent);
    }

    // 处理function_call_end事件：将工具调用结束转换为plugin_end/step_end事件发送到前端
    private void processOnFunctionCallEnd(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
                                          AgentExecuteParams executeParams) {
        JiuwenAgentEventData eventData = eventObj.getData();
        log.info("Function call end received, conversationId [{}]", executeParams.getConversationId());

        // 构造plugin_end事件发送到前端
        AgentEvent agentEvent = new AgentEvent().setEvent(EventType.PLUGIN_END.toString())
                .setCreatedTime(eventObj.getCreatedTime())
                .setLatency(new Latency().setOverall(getOverAllLatency(executeParams)));

        // 如果是workflow类型，设置type为WORKFLOW
        if (Boolean.TRUE.equals(executeParams.isWorkflow())) {
            agentEvent.setType(AgentEvent.TypeEnum.WORKFLOW);
            executeParams.setWorkflow(false);
        } else {
            agentEvent.setType(AgentEvent.TypeEnum.PLUGIN);
        }

        // 从事件数据中提取结果信息
        if (eventData != null && eventData.getAnswer() != null) {
            Object answerData = eventData.getAnswer();
            agentEvent.setContent(answerData);
        }

        sendSseData(sseEmitter, agentEvent);
    }

    // 调用插件的响应信息
    private void processOnApiExecData(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
                                      AgentExecuteParams executeParams) {
        JiuwenAgentEventData eventData = eventObj.getData();
        ApiExecDataEventAnswer pluginRsp = parseEventDataAnswer(eventData.getAnswer(), ApiExecDataEventAnswer.class);
        if (Objects.isNull(pluginRsp)) {
            log.warn("The format of api_exec_data eventData.answer is incorrect, eventData [{}].", eventData);
            return;
        }
        log.info("End run plugin, name: [{}], output: [{}], latency: [{}]", pluginRsp.getName(),
                com.alibaba.fastjson2.JSON.toJSONString(pluginRsp.getContent()),
                com.alibaba.fastjson2.JSON.toJSONString(pluginRsp.getTimeConsumption()));

        AgentEvent agentEvent = new AgentEvent().setEvent(EventType.PLUGIN_END.toString())
                .setRole(pluginRsp.getRole())
                .setContent(pluginRsp.getContent())
                .setCreatedTime(eventObj.getCreatedTime())
                .setLatency(new Latency().setPlugin(pluginRsp.getTimeConsumption().getPluginLatency())
                        .setOverall(getOverAllLatency(executeParams)));

        // 对应agent绑定workflow，执行workflow需要返回对应的结果和状态
        if (executeParams.isWorkflow()) {
            AgentWorkflowContent agentWorkflowContent = parseEventDataAnswer(pluginRsp.getContent(),
                    AgentWorkflowContent.class);
            if (agentWorkflowContent.getErrMessage() == null) {
                agentEvent.setContent(agentWorkflowContent.getAnswer());
                agentEvent.setStatus(AgentEvent.StatusEnum.fromValue(agentWorkflowContent.getWorkflowState()));
            }
            // 调用workflow执行结束，将workflow状态设置为false，下次再调用插件的时候再做判断
            executeParams.setWorkflow(false);
        }
        sendSseData(sseEmitter, agentEvent);
        if (Constant.KnowledgeRetrievalNode.RETRIEVAL.equals(pluginRsp.getName())) {
            knowledgeBaseFileInfoService.processRetrievalPlugin(pluginRsp, sseEmitter);
        }
    }

    /**
     * 处理agent对话insight信息
     *
     * @param eventObj eventObj
     * @param executeParams executeParams
     */
    private void processOnAgentNodeMessage(JiuwenAgentEvent eventObj, AgentExecuteParams executeParams,
                                           WorkflowRunResult result) {
        if (!executeParams.isDebug()) {
            conversationManagementService.saveAgentExecutionToOps(eventObj, executeParams);
        }
        // debug 模式下：设置 executionId，确保转发给 manager 后能正确保存调试记录
        if (executeParams.isDebug()) {
            eventObj.setExecutionId(executeParams.getExecutionId());
        }
    }

    /**
     * 处理agent工具调用信息
     *
     * @param eventObj eventObj
     * @param executeParams executeParams
     */
    private void processOnIntermediateMessage(SseEmitter sseEmitter, JiuwenAgentEvent eventObj, AgentExecuteParams executeParams) {
        if (sseEmitter != null) {
            try {
                sseEmitter.send(eventObj, MediaType.APPLICATION_JSON);
            } catch (Throwable e) {
                log.warn("Send intermediate message fail. {}", e.getMessage());
            }
        }
        List<Message> messages = JsonUtils.objectToClass(eventObj.getData().getAnswer());
        executeParams.getMessages().addAll(messages);

        UserCachedChatTurn chatTurn = executeParams.getChatTurn();
        if (chatTurn == null) {
            chatTurn = new UserCachedChatTurn(messages);
        } else {
            chatTurn.addMessages(messages);
        }
        executeParams.setChatTurn(chatTurn);
    }

    /**
     * 处理控制器中间调用信息，将事件answer作为对话message列表记录，包含intent信息
     *
     * @param eventObj eventObj
     * @param executeParams executeParams
     * @param sseEmitter sseEmitter
     */
    private void processOnControllerIntermediateMessage(JiuwenAgentEvent eventObj, AgentExecuteParams executeParams,
                                                        SseEmitter sseEmitter) {
        log.info("origin controller intermediate message is {}", eventObj.getData().getAnswer());
        List<Object> msgList = JsonUtils.objectToClass(eventObj.getData().getAnswer());
        ObjectMapper objectMapper = new ObjectMapper();
        List<Message> messages = new ArrayList<>();
        for (Object msg : msgList) {
            Message convertMsg = objectMapper.convertValue(msg, Message.class);
            messages.add(convertMsg);
        }
        executeParams.setMessages(messages);

        UserCachedChatTurn chatTurn = executeParams.getChatTurn();
        if (chatTurn == null) {
            chatTurn = new UserCachedChatTurn(messages);
        } else {
            chatTurn.addMessages(messages);
        }
        executeParams.setChatTurn(chatTurn);
    }

    // 会话静态信息
    private void processOnStaticData(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
                                     AgentExecuteParams executeParams) {
        AgentEvent agentEvent = new AgentEvent().setEvent(EventType.STATIC_DATA.toString())
                .setCreatedTime(eventObj.getCreatedTime())
                .setLatency(new Latency().setOverall(getOverAllLatency(executeParams)));
        sendSseData(sseEmitter, agentEvent);
        executeParams.setDone(true);
    }

    @SuppressWarnings( {"unchecked", "ConstantValue"})
    private boolean isNeedAppendMessage(List<Message> messages, Message message) {
        if (CollectionUtils.isEmpty(messages)) {
            return true;
        }
        Object lastMsg = messages.get(messages.size() - 1);
        boolean roleChanged = false;
        boolean contentChanged = false;
        if (lastMsg instanceof Message msg) {
            roleChanged = !Strings.CS.equals(msg.getRole(), message.getRole());
            contentChanged = !Strings.CS.equals(msg.getContent(), message.getContent());
        } else if (lastMsg instanceof Map) {
            Map<String, Object> msg = (Map<String, Object>) lastMsg;
            roleChanged = !Objects.equals(msg.get("role"), message.getRole());
            contentChanged = !Objects.equals(msg.get("content"), message.getContent());
        } else {
            return true;
        }
        return roleChanged || contentChanged;
    }

    // 会话总结
    private void processOnSummaryResponse(SseEmitter sseEmitter, JiuwenAgentEvent eventObj,
                                          AgentExecuteParams executeParams) {
        processOnSensitiveMessage(executeParams, sseEmitter, eventObj, true);
        JiuwenAgentEventData eventData = eventObj.getData();
        Message message = parseEventDataAnswer(eventData.getAnswer(), Message.class);
        if (Objects.isNull(message)) {
            log.warn("The format of summary_response eventData.answer is incorrect, eventData [{}].", eventData);
            return;
        }
        UserCachedChatTurn chatTurn = executeParams.getChatTurn();
        if (isNeedAppendMessage(executeParams.getMessages(), message)) {
            message.setCreateTime(eventObj.getCreatedTime());
            message.setExecutionId(executeParams.getExecutionId());
            executeParams.getMessages().add(message);

            if (chatTurn == null) {
                List<Message> messages = new ArrayList<>();
                messages.add(message);
                chatTurn = new UserCachedChatTurn(messages);
            } else {
                chatTurn.addMessage(message);
            }
            executeParams.setChatTurn(chatTurn);
        } else if (chatTurn == null) {
            chatTurn = new UserCachedChatTurn(new ArrayList<>());
            executeParams.setChatTurn(chatTurn);
        }

        String answer = message.getContent();
        log.info("Final total answer is: [{}]", answer);
        // 对 summary_response 做全量匹配，作为流式匹配的兜底
        if (executeParams.getTrieUtils().isOutputMatchEnabled()) {
            log.info("[Sensitive]: start to match agent summary response");
            answer = executeParams.getTrieUtils().handleSensitiveMatch(answer, false).getRight();
        }
        if (StringUtils.isNotBlank(answer)){
            answer = answer.replaceAll("(?i)(九问|jiuwen)", "Runtime");
        }
        AgentEvent agentEvent = new AgentEvent().setEvent(EventType.SUMMARY_RESPONSE.toString())
                .setRole(message.getRole())
                .setCreatedTime(eventObj.getCreatedTime())
                .setContent(answer)
                .setExecutionId(executeParams.getExecutionId());
        sendSseData(sseEmitter, agentEvent);
    }

    /**
     * 处理最终响应
     *
     * @param eventObj eventObj
     * @param result result
     * @param executeParams executeParams
     */
    private void processOnSummaryResponse(JiuwenAgentEvent eventObj, WorkflowRunResult result,
                                          AgentExecuteParams executeParams) {
        JiuwenAgentEventData eventData = eventObj.getData();
        Message message = parseEventDataAnswer(eventData.getAnswer(), Message.class);

        UserCachedChatTurn chatTurn = executeParams.getChatTurn();
        if (isNeedAppendMessage(result.getAgentMessageList(), message)) {
            result.getAgentMessageList().add(message);

            if (chatTurn == null) {
                List<Message> messages = new ArrayList<>();
                messages.add(message);
                chatTurn = new UserCachedChatTurn(messages);
            } else {
                chatTurn.addMessage(message);
            }
        } else if (chatTurn == null) {
            chatTurn = new UserCachedChatTurn(new ArrayList<>());
        }

        executeParams.setChatTurn(chatTurn);

        executeParams.getApiLog()
                .getOutputMap()
                .computeIfAbsent("agent", k -> new StringBuilder())
                .append(message.getContent());
    }

    private void processOnError(SseEmitter sseEmitter, JiuwenAgentEvent eventObj, AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        JiuwenAgentEventData eventData = eventObj.getData();
        sendErrorEvent(sseEmitter, executeParams, eventData);

        ModelApiLog apiLog = executeParams.getApiLog();
        apiLog.setReason(eventData.getMessage()).setStatus("failed").setInput(executeParams.getQuery());
        apiLogService.saveSecurityCenterLog(apiLog);
        traceData.setStatus("failed");
    }

    private void processOnError(JiuwenAgentEvent eventObj, WorkflowRunResult result, AgentExecuteParams executeParams, AgentCtrlTraceData traceData) {
        JiuwenAgentEventData eventData = eventObj.getData();
        WorkflowRunInfo workflowRunInfo = result.getWorkflowRunInfo();
        workflowRunInfo.setErrorCode(String.valueOf(eventData.getCode()));
        workflowRunInfo.setErrorMessage(eventData.getMessage());

        ModelApiLog apiLog = executeParams.getApiLog();
        apiLog.setReason(eventData.getMessage()).setStatus("failed").setInput(executeParams.getQuery());
        apiLogService.saveSecurityCenterLog(apiLog);
        traceData.setStatus("failed");
    }

    private double getOverAllLatency(AgentExecuteParams executeParams) {
        double overallLatency = (double) (System.currentTimeMillis() - executeParams.getStartTime()) / 1000;
        return Double.parseDouble(String.format(Locale.ROOT, "%.2f", overallLatency));
    }

    private void sendSseData(SseEmitter sseEmitter, AgentEvent sseData) {
        try {
            if (sseData.getCreatedTime() == null) {
                sseData.setCreatedTime(System.currentTimeMillis());
            }
            sseEmitter.send(sseData, MediaType.APPLICATION_JSON);
        } catch (IllegalStateException | IOException exception) {
            log.error("Fail to send sse, data [{}], reason [{}]", sseData, exception.getMessage());
            throw new AgentStudioException(StudioError.AGENT_INFO_SEND_FAILED, exception.getMessage());
        }
    }

    private void sendDeepResearchData(SseEmitter sseEmitter, JiuwenDeepResearchEvent sseData) {
        try {
            sseEmitter.send(sseData, MediaType.APPLICATION_JSON);
        } catch (IllegalStateException | IOException exception) {
            log.error("Fail to send sse, data [{}], reason [{}]", sseData, exception.getMessage());
            throw new AgentStudioException(StudioError.AGENT_INFO_SEND_FAILED, exception.getMessage());
        }
    }

    JiuwenAgentEvent parseJiuWenEventFromSseData(String sseData) {
        return parseJiuWenEventFromSseData(sseData, JiuwenAgentEvent.class);
    }

    private <T> T parseJiuWenEventFromSseData(String sseData, Class<T> clazz) {
        try {
            return com.alibaba.fastjson2.JSON.parseObject(sseData, clazz);
        } catch (JSONException e) {
            log.error("Fail to parse sse data: [{}]", sseData);
            return null;
        }
    }

    private void processOnClosed(SseEmitter sseEmitter, AgentExecuteParams executeParams, Boolean isBlock) {
        // 1、保存会话信息
        log.info("Start to update conversation.");
        updateConversation(executeParams, !isBlock);

        // 2、保存记忆参数信息
        Map<String, String> pluginInputMap = executeParams.getPluginInputMap();
        if (MapUtils.isEmpty(pluginInputMap)) {
            // 直接发送done事件
            sendDoneEvent(sseEmitter, executeParams);
            return;
        }
        log.info("Start to update memory variables.");
        pluginInputMap.forEach((pluginName, arguments) -> saveMemoryVariablesInfo(arguments, executeParams));
        sendDoneEvent(sseEmitter, executeParams);
    }

    private void sendDoneEvent(SseEmitter sseEmitter, AgentExecuteParams executeParams) {
        // 运行结束，返回done消息块
        try {
            sendDoneAndComplete(sseEmitter, executeParams);
        } catch (Throwable e) {
            log.info("Send done event on close failed.", e);
        }
    }

    private <T> T parseEventDataAnswer(Object answer, Class<T> clazz) {
        try {
            return com.alibaba.fastjson2.JSON.parseObject(com.alibaba.fastjson2.JSON.toJSONString(answer), clazz);
        } catch (JSONException exception) {
            log.error("Fail to parse event data answer [{}]", com.alibaba.fastjson2.JSON.toJSONString(answer));
            throw new AgentStudioException(StudioError.FAIL_TO_PARSE_DATA);
        }
    }

    private void sendErrorEvent(SseEmitter sseEmitter, AgentExecuteParams executeParams, JiuwenAgentEventData eventData) {
        if (sseEmitter == null) {
            return;
        }
        ErrorEvent errorEvent = runtimeI18nService.createErrorEvent(eventData);
        String errorMsg = errorEvent.getErrorMsg();
        try {
            // 发送error消息块
            eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter,
                    WorkflowStreamEventFactory.error(errorEvent));
            // 如果没有发送过statistic_data消息，需要再主动发送一次，用于统计耗时
            if (!executeParams.isDone() && (executeParams.getExecuteType().equals(Constant.AppType.AGENT) || executeParams.getExecuteType().equals(Constant.AppType.PLAN_EXECUTE))) {
                AgentEvent agentEvent = new AgentEvent().setEvent(EventType.STATIC_DATA.toString())
                        .setCreatedTime(System.currentTimeMillis())
                        .setLatency(new Latency().setOverall(getOverAllLatency(executeParams)));
                sendSseData(sseEmitter, agentEvent);
            }

            SseEmitterUtils.setFailureOnSseEmitter(sseEmitter, new Throwable(errorMsg));

            // 发送结束消息块
            sendDoneAndComplete(sseEmitter, executeParams);
        } catch (AgentStudioException exception) {
            log.error("Fail to send error message [{}], because [{}]", errorMsg, exception.getMessage());
        }
    }

    private void sendDoneAndComplete(SseEmitter sseEmitter, AgentExecuteParams executeParams) {
        if (sseEmitter == null) {
            return;
        }
        switch (executeParams.getExecuteType()) {
            case Constant.AppType.DEEP_RESEARCH: {
                sendDeepResearchStatisticData(sseEmitter, executeParams);
                sendDeepResearchDone(sseEmitter);
                break;
            }
            case Constant.AppType.AGENT:
            case Constant.AppType.PLAN_EXECUTE: {
                sendAgentDone(sseEmitter);
                break;
            }
            case Constant.AppType.CONTROLLER: {
                sendControllerDone(sseEmitter, executeParams);
            }
        }
    }

    private void sendDeepResearchStatisticData(SseEmitter sseEmitter, AgentExecuteParams executeParams) {
        JiuwenDeepResearchEvent event = new JiuwenDeepResearchEvent().setEvent(EventType.STATIC_DATA.toString())
                .setCreatedTime(System.currentTimeMillis())
                .setLatency(new Latency().setOverall(getOverAllLatency(executeParams)));
        sendDeepResearchData(sseEmitter, event);
        executeParams.setDone(true);
    }

    // DeepResearch运行结束，返回done消息块
    private void sendDeepResearchDone(SseEmitter sseEmitter) {
        sendDeepResearchData(sseEmitter,
            new JiuwenDeepResearchEvent().setEvent(EventType.DONE.toString()).setCreatedTime(System.currentTimeMillis()));
        sseEmitter.complete();
    }

    // Agent运行结束，返回done消息块
    private void sendAgentDone(SseEmitter sseEmitter) {
        sendSseData(sseEmitter,
                new AgentEvent().setEvent(EventType.DONE.toString()).setCreatedTime(System.currentTimeMillis()));
        sseEmitter.complete();
    }

    // 控制器运行结束，返回end消息块
    private void sendControllerDone(SseEmitter sseEmitter, AgentExecuteParams executeParams) {
        eventProcessor.sendEvent(executeParams.getAgentId(), sseEmitter, WorkflowStreamEventFactory.end());
        sseEmitter.complete();
    }

    private AgentMetadata getAgentMetadata(AgentExecuteParams executeParams) {
        long start = System.currentTimeMillis();

        AgentMetadata agentMetadata;
        if (executeParams.isLatestPublish()) {
            // 发布版本(最新版本)，读redis
            agentMetadata = publishUtils.getPublish(executeParams.getAgentId(), Constants.LATEST_PUBLISH_VERSION,
                    obsService);
        } else if (StringUtils.isNoneBlank(executeParams.getVersionId()) || Constant.Agent.TREASURE_BOX_AGENT.equals(
                executeParams.getType())) {
            // 百宝箱、发布版本(带version)旧逻辑不变，内存缓存+OBS一次读
            AgentIrWrapper irWrapper = agentIrCacheService.getPublishedAgentIr(executeParams.getAgentId(),
                    executeParams.getVersionId());
            AgentIrMetadata agentIrMetadata = irWrapper.getMetadata();
            agentMetadata = AgentMetadata.builder()
                    .projectId(agentIrMetadata.getProjectId())
                    .updatedAt(agentIrMetadata.getUpdatedAt().getTime())
                    .isContentReviewEnable(irWrapper.isContentReviewEnabled())
                    .safetyBarrier(irWrapper.isSafetyBarrier())
                    .agentId(executeParams.getAgentId())
                    .versionId(
                            StringUtils.isBlank(executeParams.getVersionId()) ? "published" : executeParams.getVersionId())
                    .build();
        } else {
            // 草稿，旧逻辑不变，内存缓存+OBS每次读(检查MD5)
            AgentIrWrapper irWrapper = agentIrCacheService.getLatestAgentIr(executeParams.getAgentId());
            AgentIrMetadata agentIrMetadata = irWrapper.getMetadata();
            agentMetadata = AgentMetadata.builder()
                    .projectId(agentIrMetadata.getProjectId())
                    .updatedAt(agentIrMetadata.getUpdatedAt().getTime())
                    .isContentReviewEnable(irWrapper.isContentReviewEnabled())
                    .safetyBarrier(irWrapper.isSafetyBarrier())
                    .agentId(executeParams.getAgentId())
                    .build();
        }

        PerformUtils.accumulationAgent(executeParams, Constant.Performance.LOAD_IR, System.currentTimeMillis() - start);

        if (agentMetadata == null) {
            log.error("get agent metadata failed");
            if (executeParams.isLatestPublish()) {
                throw new AgentStudioException(StudioError.AGENT_HAS_BEEN_UPDATED);
            }
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        return agentMetadata;
    }

    private void checkExecuteParams(AgentExecuteParams executeParams) {
        // 对query字段输入进行长度校验
        String query = null;
        if (executeParams.getExecuteType().equals(Constant.AppType.CONTROLLER)) {
            if (executeParams.getInputs() == null) {
                // 如果为控制器，inputs不能为null
                log.error("controller execute inputs must not be null!");
                throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
            }
            query = executeParams.getInputs().get(Constant.Jiuwen.USER_MSG_FIELD).toString();
            executeParams.setQuery(query);
        } else if (executeParams.getExecuteType().equals(Constant.AppType.AGENT) || executeParams.getExecuteType().equals(Constant.AppType.PLAN_EXECUTE)) {
            Map<String, Object> inputs = executeParams.getInputs();
            // 单智能体支持inputs字段，兼容query字段
            if (ObjectUtils.isNotEmpty(inputs) && inputs.containsKey(Constant.Jiuwen.USER_MSG_FIELD)) {
                query = inputs.get(Constant.Jiuwen.USER_MSG_FIELD).toString();
                executeParams.setQuery(query);
            } else {
                query = executeParams.getQuery();
            }
        } else if (Constant.AppType.DEEP_RESEARCH.equals(executeParams.getExecuteType())
                && isInvalidDRInputs(executeParams.getInputs())) {
            log.error("invalid inputs for deep research!");
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }
        if (query != null && query.length() > agentMaxQueryLength) {
            log.error("query param exceed max length {}", agentMaxQueryLength);
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }
    }

    private boolean isInvalidDRInputs(Map<String, Object> inputs) {
        if (ObjectUtils.isEmpty(inputs)) {
            return true;
        }
        if (ObjectUtils.isEmpty(inputs.get(Constant.DeepResearch.MESSAGE_FIELD))) {
            return true;
        }
        if (String.valueOf(inputs.get(Constant.DeepResearch.MESSAGE_FIELD)).length() > deepResearchMaxMsgLength) {
            return true;
        }
        if (inputs.containsKey(Constant.DeepResearch.FEEDBACK_FIELD)) {
            return !Constant.DeepResearch.FEEDBACK_ACCEPTED.equals(inputs.get(Constant.DeepResearch.FEEDBACK_FIELD));
        }
        if (!inputs.containsKey(Constant.DeepResearch.TEMPLATE_FIELD)) {
            return false;
        }
        Object templateField = inputs.get(Constant.DeepResearch.TEMPLATE_FIELD);
        if (!(templateField instanceof Map<?, ?>)) {
            return true;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> templateMap = (Map<String, Object>) templateField;
        if (ObjectUtils.isEmpty(templateMap.get(Constant.DeepResearch.FILE_NAME_FIELD))
                || ObjectUtils.isEmpty(templateMap.get(Constant.DeepResearch.FILE_PATH_FIELD))) {
            return true;
        }
        return !(templateMap.get(Constant.DeepResearch.IS_TEMPLATE_FIELD) instanceof Boolean);
    }

    private JiuwenExecutionRequest buildJiuWenRequestBody(AgentExecuteParams executeParams, Conversation conversation) {
        List<Message> historyMessageList = Optional.ofNullable(conversation)
                .map(Conversation::getMessageList)
                .orElse(new ArrayList<>());

        JiuwenParams jiuwenParams = buildJiuwenParams(executeParams, historyMessageList);
        configureMemorySettings(executeParams, jiuwenParams);
        configureSysOperationCard(executeParams, jiuwenParams);

        return new JiuwenExecutionRequest().setConversationId(executeParams.getConversationId())
                .setQuery(executeParams.getQuery())
                .setUserId(executeParams.getUserId())
                .setAgentId(executeParams.getAgentId())
                .setParams(jiuwenParams)
                .setIrPath(getAgentIrObsPath(executeParams))
                .setResponseMode(Constant.Jiuwen.RESPONSE_MODE_STREAMING);
    }

    private JiuwenParams buildJiuwenParams(AgentExecuteParams executeParams, List<Message> historyMessageList) {
        Map<String, Object> globalVariables = extractGlobalVariables(executeParams);
        JiuwenParams jiuwenParams = new JiuwenParams();
        jiuwenParams.setGlobalVariables(globalVariables);
        setEnvironmentVariables(executeParams, jiuwenParams);
        configureControllerParams(executeParams, jiuwenParams);
        processFileUrls(executeParams, jiuwenParams);
        configureAgentTypeParams(executeParams, jiuwenParams, historyMessageList);
        return jiuwenParams;
    }

    private void setEnvironmentVariables(AgentExecuteParams executeParams, JiuwenParams jiuwenParams) {
        if (StringUtils.isBlank(executeParams.getEnvironmentId())) {
            return;
        }
        Map<String, Object> envVars = envVariablesUtils.getEnvironmentVariables(executeParams);
        Object secretKeys = envVars.remove("_secretEnvKeys");
        jiuwenParams.setEnvironmentVariables(new HashMap<>(envVars));
        if (secretKeys instanceof List) {
            @SuppressWarnings("unchecked")
            List<String> keys = (List<String>) secretKeys;
            jiuwenParams.setSecretEnvKeys(keys);
        }
    }

    private Map<String, Object> extractGlobalVariables(AgentExecuteParams executeParams) {
        Map<String, Object> globalVariables = new HashMap<>();
        if (executeParams.getInputs() != null) {
            executeParams.getInputs().forEach((k, v) -> {
                if (!SYSTEM_INPUTS.contains(k)) {
                    globalVariables.put(k, v);
                }
            });
        }
        return globalVariables;
    }

    private void configureControllerParams(AgentExecuteParams executeParams, JiuwenParams jiuwenParams) {
        if (!executeParams.getExecuteType().equals(Constant.AppType.CONTROLLER)) {
            return;
        }
        Object workflowSequenceObj = executeParams.getInputs().get(Constant.Jiuwen.WORKFLOW_SEQUENCE_FIELD);
        List<String> workflowSequences = workflowSequenceObj != null ? JsonUtils.objectToClass(workflowSequenceObj) : new ArrayList<>();
        Object activeWorkflowsObj = executeParams.getInputs().get(Constant.Jiuwen.ACTIVE_WORKFLOWS_FIELD);
        List<String> activeWorkflows = activeWorkflowsObj != null ? JsonUtils.objectToClass(activeWorkflowsObj) : new ArrayList<>();
        jiuwenParams.setWorkflowSequence(workflowSequences).setActiveWorkflows(activeWorkflows);
        Object intent = executeParams.getInputs().get(Constant.Jiuwen.INTENT_FIELD);
        if (intent != null) {
            jiuwenParams.setIntent(intent.toString());
        }
    }

    private void processFileUrls(AgentExecuteParams executeParams, JiuwenParams jiuwenParams) {
        if (CollectionUtils.isEmpty(executeParams.getFileUrls())) {
            return;
        }
        List<Object> mediaUrls = extractUrlFromQuery(executeParams.getFileUrls());
        if (!CollectionUtils.isEmpty(mediaUrls)) {
            jiuwenParams.setFiles(mediaUrls);
            executeParams.setFiles(mediaUrls);
        }
    }

    private void configureAgentTypeParams(AgentExecuteParams executeParams, JiuwenParams jiuwenParams, List<Message> historyMessageList) {
        if (Constant.AppType.DEEP_RESEARCH.equals(executeParams.getExecuteType())) {
            configureDeepResearchParams(executeParams, jiuwenParams);
        } else {
            configureRegularAgentParams(executeParams, jiuwenParams, historyMessageList);
        }
    }

    private void configureMemorySettings(AgentExecuteParams executeParams, JiuwenParams jiuwenParams) {
        jiuwenParams.setAppId(executeParams.getAgentId());
        jiuwenParams.setEnableMemoryRetrieve(
                Optional.ofNullable(executeParams.getLongTermMemoryRuntime()).map(LongTermMemoryRuntime::isEnableRetrieve).orElse(false));
        jiuwenParams.setEnableMemoryExtract(
                Optional.ofNullable(executeParams.getLongTermMemoryRuntime()).map(LongTermMemoryRuntime::isEnableExtract).orElse(false));
    }

    private void configureSysOperationCard(AgentExecuteParams executeParams, JiuwenParams jiuwenParams) {
        if (!skillEnabled) {
            return;
        }
        JiuwenParamsSysOperationCardWorkConfig workConfig = new JiuwenParamsSysOperationCardWorkConfig();
        workConfig.setWorkDir("/opt/tmp/agent");
        workConfig.setShellAllowlist(Arrays.asList(
                "echo", "rg", "ls", "dir", "cd", "pwd", "python", "python3", "pip", "pip3",
                "npm", "node", "git", "cat", "type", "mkdir", "md", "rm", "rd", "cp", "copy",
                "mv", "move", "grep", "find", "curl", "wget", "ps", "df", "ping"
        ));
        JiuwenParamsSysOperationCard sysOperationCard = new JiuwenParamsSysOperationCard();
        sysOperationCard.setId(executeParams.getAgentId());
        sysOperationCard.setMode("local");
        sysOperationCard.setWorkConfig(workConfig);
        jiuwenParams.setSysOperationCard(sysOperationCard);
    }

    public List<Object> extractUrlFromQuery(List<String> fileUrls) {
        List<Object> mediaObjs = new ArrayList<>();
        // 上传附件，解析url，过滤出图片和视频的url，拼接成files
        fileUrls.forEach(url -> {
            String cleanUrl = url.split("[?]")[0];
            if (checkImage(cleanUrl)) {
                MediaUrl mediaUrl = new MediaUrl();
                mediaUrl.setUrl(url);
                ImageInfo imageInfo = new ImageInfo();
                imageInfo.setImageUrl(mediaUrl);
                imageInfo.setType(Constant.Jiuwen.IMAGE_TYPE);
                mediaObjs.add(imageInfo);
            } else if (checkVideo(cleanUrl)) {
                MediaUrl mediaUrl = new MediaUrl();
                mediaUrl.setUrl(url);
                VideoInfo videoInfo = new VideoInfo();
                videoInfo.setVideoUrl(mediaUrl);
                videoInfo.setType(Constant.Jiuwen.VIDEO_TYPE);
                mediaObjs.add(videoInfo);
            }
        });
        return mediaObjs;
    }

    List<ConversationHistory> convertMessages(List<Message> messageList) {
        List<ConversationHistory> conversationHistoryList = new ArrayList<>();
        for (Message msg : messageList) {
            ConversationHistory conversationHistory = new ConversationHistory();
            conversationHistory.setRole(msg.getRole());
            conversationHistory.setContent(msg.getContent());
            conversationHistory.setIntent(msg.getIntent());
            conversationHistory.setFunctionCall(msg.getFunctionCall());
            conversationHistory.setName(msg.getName());
            conversationHistory.setFiles(msg.getFiles());
            conversationHistory.setToolCalls(msg.getToolCalls());
            conversationHistory.setToolCallId(msg.getToolCallId());
            conversationHistory.setEnableHistory(msg.isEnableHistory());
            conversationHistory.setAgentId(msg.getAgentId());
            conversationHistoryList.add(conversationHistory);
        }
        return conversationHistoryList;
    }

    private void updateConversation(AgentExecuteParams executeParams, boolean dialogueEnd) {
        ConversationParams conversationParams = ConversationParams.builder()
                .id(executeParams.getAgentId())
                .projectId(executeParams.getProjectId())
                .conversationId(executeParams.getConversationId())
                .versionId(executeParams.getVersionId())
                .executeType(executeParams.getExecuteType())
                .build();
        conversationManagementService.updateConversation(conversationParams, executeParams.getMessages(), dialogueEnd);
    }

    // 提取并保存记忆参数信息
    private void saveMemoryVariablesInfo(String arguments, AgentExecuteParams executeParams) {
        // 租户配置的记忆参数列表(IR)
        List<MemoryVariable> memoryVariables = executeParams.getMemoryVariables();
        if (CollectionUtils.isEmpty(memoryVariables)) {
            return;
        }
        // 用户级记忆参数更新
        List<MemoryVariable> irUserMemoryVariables = memoryVariables.stream()
                .filter(item -> Constant.Agent.MEMORY_VAR_LIFE_CYCLE_USER.equals(item.getLifeCycle()))
                .toList();
        if (!CollectionUtils.isEmpty(irUserMemoryVariables)) {
            Map<String, MemoryVariable> userMemoryVariableMap
                    = conversationManagementService.retrieveUserMemoryVariables(executeParams.getAgentId(),
                            executeParams.getUserId(), executeParams.getVersionId())
                    .stream()
                    .collect(Collectors.toMap(MemoryVariable::getName, memoryVariable -> memoryVariable));

            updateIrMemoryVariables(irUserMemoryVariables, userMemoryVariableMap, arguments);
            conversationManagementService.updateUserMemoryVariables(executeParams.getAgentId(),
                    executeParams.getUserId(), executeParams.getVersionId(), irUserMemoryVariables);
        }
        // 会话级记忆参数更新
        List<MemoryVariable> irConMemoryVariables = memoryVariables.stream()
                .filter(item -> Constant.Agent.MEMORY_VAR_LIFE_CYCLE_CONVERSATION.equals(item.getLifeCycle()))
                .toList();
        if (CollectionUtils.isEmpty(irConMemoryVariables)) {
            return;
        }
        Map<String, MemoryVariable> conMemoryVariableMap = conversationManagementService.retrieveConMemoryVariables(
                        executeParams.getAgentId(), executeParams.getConversationId(), executeParams.getVersionId())
                .stream()
                .collect(Collectors.toMap(MemoryVariable::getName, memoryVariable -> memoryVariable));

        updateIrMemoryVariables(irConMemoryVariables, conMemoryVariableMap, arguments);
        conversationManagementService.updateConMemoryVariables(executeParams.getAgentId(),
                executeParams.getConversationId(), executeParams.getVersionId(), irConMemoryVariables);
    }

    /**
     * 根据plugin传参和Redis历史记录，更新IR记忆参数的值
     *
     * @param irMemoryVariables ir metadata中的记忆参数信息
     * @param memoryVariableMap 记忆参数在Redis中的信息，key参数名，value参数信息
     * @param arguments plugin调用入参信息
     */
    private void updateIrMemoryVariables(List<MemoryVariable> irMemoryVariables,
                                         Map<String, MemoryVariable> memoryVariableMap, String arguments) {
        // plugin入参对象
        com.alibaba.fastjson2.JSONObject jsonObject = Optional.ofNullable(
                com.alibaba.fastjson2.JSON.parseObject(arguments)).orElse(new com.alibaba.fastjson2.JSONObject());

        // 优先取plugin入参，没有再取Redis历史记录
        for (MemoryVariable memoryVariable : irMemoryVariables) {
            String name = memoryVariable.getName();
            String value = jsonObject.getString(name);
            if (StringUtils.isNoneBlank(value)) {
                memoryVariable.setValue(value);
                memoryVariable.setUpdateTime(System.currentTimeMillis());
                continue;
            }
            log.warn("Not found keyword [{}] in plugin inputs", name);
            if (memoryVariableMap.containsKey(memoryVariable.getName())) {
                memoryVariable.setValue(memoryVariableMap.get(memoryVariable.getName()).getValue());
                memoryVariable.setUpdateTime(memoryVariableMap.get(memoryVariable.getName()).getUpdateTime());
            }
        }
    }

    private Map<String, String> extractMemoryVariables(List<MemoryVariable> irMemoryVariables, String arguments) {
        Map<String, String> memoryVariableMap = new HashMap<>();
        if (CollectionUtils.isEmpty(irMemoryVariables)) {
            return memoryVariableMap;
        }
        // plugin入参对象
        com.alibaba.fastjson2.JSONObject jsonObject = com.alibaba.fastjson2.JSON.parseObject(arguments);
        if (Objects.isNull(jsonObject)) {
            return memoryVariableMap;
        }
        for (MemoryVariable variable : irMemoryVariables) {
            String name = variable.getName();
            String value = jsonObject.getString(name);
            if (StringUtils.isBlank(value)) {
                continue;
            }
            memoryVariableMap.put(name, value);
        }
        return memoryVariableMap;
    }

    private String getAgentIrObsPath(AgentExecuteParams executeParams) {
        return String.format("%s/%s/%s.json", irObsPath, executeParams.getAgentId(), getIrObjectKey(executeParams));
    }

    private String getIrObjectKey(AgentExecuteParams executeParams) {
        if (StringUtils.isNoneBlank(executeParams.getVersionId())) {
            // 发布版本
            return executeParams.getAgentId() + "_" + executeParams.getVersionId();
        } else if (Constant.Agent.TREASURE_BOX_AGENT.equals(executeParams.getType())) {
            // 百宝箱
            return executeParams.getAgentId() + "_published";
        } else {
            // 调试版本
            return executeParams.getAgentId();
        }
    }


    @Override
    public AutoAddResultJsonObject additionalQuestions(String projectId, String agentId, String conversationId,
                                                       String workspaceId, AdditionalQuestionsReq body) {
        if (StringUtils.isBlank(body.getName())) {
            log.error("Agent name is null. projectId = {}, agentId = {}", projectId, agentId);
            throw new AgentStudioException(StudioError.CHECK_AGENT_INFO_FAILED);
        }
        if (!body.isEnable()) {
            log.error("Abnormal interface calling. projectId = {}, agentId = {}", projectId, agentId);
            throw new AgentStudioException(StudioError.INTERFACE_CALL_EXCEPTION);
        }

        // 获取历史会话消息
        List<Message> messageList;
        try {
            RetrieveConversationQo retrieveConversationQo = new RetrieveConversationQo().setVersionId(
                    body.getVersionId());
            messageList = conversationManagementService.retrieveConversation(projectId, agentId, conversationId,
                    retrieveConversationQo);
        } catch (AgentStudioException e) {
            log.error("Retrieve history messages failed. projectId = {}, agentId = {}, conversationId = {}", projectId,
                    agentId, conversationId);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
        if (messageList.size() < 2) {
            log.error("History messages are incorrect. projectId = {}, agentId = {}, conversationId = {}", projectId,
                    agentId, conversationId);
            return new AutoAddResultJsonObject().setQuestions(new ArrayList<>());
        }
        StringBuilder historyMessages = new StringBuilder();
        for (int index = messageList.size() - 2; index < messageList.size(); index++) {
            historyMessages.append(messageList.get(index).getContent()).append("\n");
        }

        // 获取模型信息
        ModelConfig modelConfig = getModelConfigFromObs(agentId);

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = CommonUtils.getResourceContent(
                isChinese ? Constant.ADDITIONAL_QUESTIONS_PROMPT : Constant.ADDITIONAL_QUESTIONS_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(Constant.NAME, body.getName()),
                KV.of(Constant.HISTORY_MESSAGES, historyMessages.toString()),
                KV.of(Constant.USER_PROMPT, StringUtils.defaultIfEmpty(body.getPrompt(), "")));

        // 调用模型并解析返回结果
        List<String> questionList = new ArrayList<>();
        for (int callCounts = 0; callCounts < Constant.MODEL_CALLS; callCounts++) {
            questionList = JsonUtils.json2Obj(callModel(buildAskModelReq(modelConfig, query), workspaceId,
                    RequestContextUtils.getRequestUserDomainId()), new TypeReference<List<String>>() {});
            if (!CollectionUtils.isEmpty(questionList)) {
                break;
            }
        }

        if (CollectionUtils.isEmpty(questionList)) {
            return new AutoAddResultJsonObject().setQuestions(new ArrayList<>());
        }
        if (questionList.size() > Constant.MAX_QUESTION_NUMS) {
            questionList = questionList.subList(0, Constant.MAX_QUESTION_NUMS);
        }
        return new AutoAddResultJsonObject().setQuestions(questionList);
    }

    @Override
    public String createReleaseInfo(String projectId, String workspaceId, ReleaseInfo body) {
        String releaseInfoKey = null;
        if (body.getChannelType().equals(Constant.WEB_PAGE_CHANNEL)) {
            releaseInfoKey = String.format(releaseWebRel, body.getShortCode());
        } else if (body.getChannelType().equals(Constant.APP_STORE_CHANNEL)) {
            releaseInfoKey = String.format(releaseAppRel, body.getAppId(), body.getVersionId());
        } else if (body.getChannelType().equals(Constant.CLOUD_STORE_CHANNEL)) {
            releaseInfoKey = String.format(releaseCloudRel, body.getShortCode());
        }
        log.info("releaseInfo is {}", body);
        log.info("create release info redis key: {}", releaseInfoKey);
        body.setProjectId(projectId);
        body.setWorkspaceId(workspaceId);
        body.setDomainId(RequestContextUtils.getRequestUserDomainId());
        body.setAlreadyBeenCalled(0);
        body.setUpdateTime(System.currentTimeMillis());
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(releaseInfoKey + LOCK_STR);

            // 获取redis分布式锁，如果锁不可用，则等待3秒，如果还是无法获取，则抛出异常
            if (lock.tryLock(Duration.ofSeconds(3))) {
                // 设置最后更新时间
                redisClient.set(releaseInfoKey, com.alibaba.fastjson2.JSON.toJSONString(body));
            } else {
                log.error("failed to get lock");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED,
                        "other user is processing same redis key!");
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed, other user is processing same redis key!", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
        return null;
    }

    @Override
    public String delegateExchangeToken(String projectId, String authProjectId, String authDomainId) {
        String authToken;
        String opToken = "";
        try {
            authToken = delegateExchangeTokenService.delegateExchangeToken(authProjectId, authDomainId, opToken);
        } catch (Exception e) {
            log.error("Call get-agency-token api exception.", e);
            throw new AgentStudioException(StudioError.CALL_GET_AGENCY_TOKEN_API_EXCEPTION);
        }
        log.info("DomainId: {}, projectId: {} has exchanged the tok of domainId: {}, projectId: {}",
                RequestContextUtils.getRequestUserDomainId(), RequestContextUtils.getRequestProjectId(), authProjectId,
                authDomainId);
        HttpServletResponse response;
        if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes) {
            if (!Objects.isNull(RequestContextHolder.getRequestAttributes())) {
                response = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getResponse();
                if (!Objects.isNull(response)) {
                    response.setHeader(Constant.Common.X_AUTH_TOKEN, authToken);
                    return "success";
                }
            }
        }
        log.error("Get HttpServletResponse failed, set header failed.");
        return "fail";
    }

    @Override
    public String deleteReleaseInfo(String projectId, String releaseId, String channelType, String versionId) {
        String releaseInfoKey = null;
        if (Constant.WEB_PAGE_CHANNEL.equals(channelType)) {
            releaseInfoKey = String.format(releaseWebRel, releaseId);
        } else if (Constant.APP_STORE_CHANNEL.equals(channelType)) {
            releaseInfoKey = String.format(releaseAppRel, releaseId, versionId);
        } else if (Constant.CLOUD_STORE_CHANNEL.equals(channelType)) {
            releaseInfoKey = String.format(releaseCloudRel, releaseId);
        }
        log.info("delete release info redis key: {}", releaseInfoKey);
        RedisLock lock = null;
        try {
            lock = redisClient.getLock(releaseInfoKey + LOCK_STR);

            // 获取redis分布式锁，如果锁不可用，则等待3秒，如果还是无法获取，则抛出异常
            if (lock.tryLock(Duration.ofSeconds(3))) {
                redisClient.delete(releaseInfoKey);
            } else {
                log.error("failed to get lock, other user is processing same redis key!");
                throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
            }
        } catch (Exception e) {
            log.error("redisson get bucket failed", e);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        } finally {
            if (lock != null) {
                lock.unlock();
            }
        }
        return null;
    }

    @Override
    public AsrRsp voiceRecognition(String projectId, AsrReq body) {
        try {
            return sisClient.shortAudioRecognition("", opProjectId, body);
        } catch (Exception e) {
            log.error("Asr API service exception.", e);
            throw new AgentStudioException(StudioError.INTERFACE_CALL_EXCEPTION);
        }
    }

    /**
     * 从obs获取模型信息
     *
     * @param agentId String
     * @return modelConfig
     */
    public ModelConfig getModelConfigFromObs(String agentId) {
        try {
            AgentIrWrapper agentIrWrapper = agentIrCacheService.getLatestAgentIr(agentId);
            return agentIrWrapper.getModelConfig();
        } catch (Exception e) {
            log.error("Failed to access obs service. agentId = {}", agentId, e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    /**
     * 构造模型调用请求体
     *
     * @param modelConfig ModelConfig
     * @param query String
     * @return askModelReq
     */
    public AskModelReq buildAskModelReq(ModelConfig modelConfig, String query) {
        return AskModelReq.builder()
                .model(modelConfig)
                .messages(new ArrayList<>(
                        Collections.singletonList(MessageEntity.builder().role(Constant.USER).content(query).build())))
                .build();
    }

    /**
     * 调用模型
     *
     * @param askModelReq AskModelReq
     * @return content
     */
    public String callModel(AskModelReq askModelReq, String workspaceId, String ownerDomainId) {
        Map<String, String> headers = new HashMap<>();
        headers.put("x-owner-domain-id", ownerDomainId);
        String modelId = askModelReq.getModel().getModelName().contains("|") ? askModelReq.getModel()
                .getModelName()
                .split("\\|")[0] : askModelReq.getModel().getModelName();

        ModelApiLogThreadLocal.clear();
        ModelApiLog apiLog = new ModelApiLog().setModelName(modelId)
                .setDomainId(RequestContextUtils.getRequestUserDomainId())
                .setProjectId(RequestContextUtils.getRequestProjectId())
                .setModelId(modelId)
                .setApi("")
                .setStartTime(System.currentTimeMillis());
        ModelApiLogThreadLocal.setApiLog(apiLog);

        try {
            ChatCompletionRequest request = createModelInvokeBase(askModelReq, modelId);

            Object object = modelController.chatCompletions(workspaceId, workspaceId, headers, request, false, "", "");
            JSONObject response;
            if (object instanceof JSONObject) {
                response = (JSONObject) object;
            } else {
                response = JSONObject.parseObject(JSONObject.toJSONString(object));
            }
            String content = response.getJSONArray(Constant.CHOICES)
                    .getJSONObject(0)
                    .getJSONObject(Constant.MESSAGE)
                    .getString(Constant.CONTENT);
            return Strings.CS.removeEnd(Strings.CS.removeStart(content, "```json"), "```");
        } finally {
            ModelApiLogThreadLocal.clear();
        }
    }

    private ChatCompletionRequest createModelInvokeBase(AskModelReq askModelReq, String modeId) {
        ChatCompletionRequest chatCompletionRequest = new ChatCompletionRequest();
        chatCompletionRequest.setModel(modeId);
        chatCompletionRequest.setStream(false);
        if (askModelReq.getModel().getHyperParameters() != null) {
            chatCompletionRequest.setTemperature(askModelReq.getModel().getHyperParameters().getTemperature());
            chatCompletionRequest.setTopP(askModelReq.getModel().getHyperParameters().getTopP());
        }

        List<ChatMessage> messages = new ArrayList<>();
        for (MessageEntity entity : askModelReq.getMessages()) {
            messages.add(new ChatMessage().setRole(entity.getRole()).setContent(entity.getContent()));
        }

        chatCompletionRequest.setMessages(messages);
        return chatCompletionRequest;
    }

    private void addAgentExecEvent(AnalyticsEventType eventType, AgentExecuteParams executeParams) {
        analyticsEventService.addEvent(AnalyticsEventEntity.builder()
                .eventType(eventType.toString())
                .appType(Constant.AppType.AGENT)
                .appId(executeParams.getAgentId())
                .projectId(executeParams.getProjectId())
                .userId(executeParams.getUserId())
                .channel(AnalyticsChannel.API.getText())
                .build());
    }

    @Override
    public FileUploadRsp uploadAgentFile(String workspaceId, String projectId, MultipartFile file, Integer expiresDays,
                                         Boolean isImage) {
        if (file.isEmpty()) {
            log.error("file cannot be empty!");
            throw new AgentStudioException(StudioError.FILE_CANNOT_BE_EMPTY);
        }

        // 文件上传校验
        String fileName = file.getOriginalFilename();
        boolean isImageFile = checkImage(fileName);
        String safeFileName = checkUploadFile(file, isImageFile ? Constant.IMAGE : Constant.FILE);
        checkUserCanUpload(file, RequestContextUtils.getRequestUserId());

        return uploadFileToObs(file, fileExpirationMinutes, safeFileName);
    }

    @NotNull FileUploadRsp uploadFileToObs(MultipartFile file, Integer expiresMinutes, String safeFileName) {
        try {
            InputStream inputStream = file.getInputStream();
            // 设置返回响应体Url和Headers参数
            FileUploadRsp fileUploadRsp = new FileUploadRsp();

            int fileExpireDays = DatetimeUtils.calculateCeilingDaysFromMinutes(expiresMinutes);

            if (fileReadOnly) {
                String url = obsService.uploadToStagingWithPublicRead(inputStream, safeFileName, fileExpireDays);
                fileUploadRsp.setUrl(url);
            } else {
                String objectName = obsService.uploadToStagingWithExpires(inputStream, safeFileName, fileExpireDays);
                String downloadUrl = obsService.getStagingDownloadUrl(objectName, (long) expiresMinutes * 60);
                fileUploadRsp.setUrl(downloadUrl);
            }

            return fileUploadRsp;
        } catch (IOException e) {
            log.error("OBS failure", e);
            throw new AgentStudioException(StudioError.OBS_FAILED);
        }
    }

    private Boolean checkImage(String fileName) {
        String fileType = fileName.substring(fileName.lastIndexOf('.'));
        return StringUtils.isNotBlank(fileType) && allowedImgType.contains(fileType.toLowerCase(Locale.ROOT));
    }

    private Boolean checkVideo(String fileName) {
        String fileType = fileName.substring(fileName.lastIndexOf('.'));
        return StringUtils.isNotBlank(fileType) && allowedVideoType.contains(fileType.toLowerCase(Locale.ROOT));
    }

    private void checkUserCanUpload(MultipartFile file, String userId) {
        checkUploadNum(userId);
        checkUploadTotalSize(file, userId);
    }

    private void checkUploadTotalSize(MultipartFile file, String userId) {
        String key = "uploadFile:new:size:" + userId;
        boolean exist = redisClient.exists(key);
        BigDecimal currentSize = new BigDecimal(file.getSize()).divide(new BigDecimal(KB));
        if (exist) {
            BigDecimal obsSize = new BigDecimal(redisClient.get(key));
            currentSize = currentSize.add(obsSize);
        }

        // 存在 -> 获取已上传的文件大小，与最大值比较
        if (currentSize.compareTo(new BigDecimal(maxUploadTotalSize)) < 0) {
            // 过期时间
            redisClient.setAndKeepTtl(key, String.valueOf(currentSize), Duration.ofSeconds(timeScopeUploadTotalSize));
        } else {
            log.error(
                    "The total size of the upload files exceeds the limit. fileSize:{}, currentSize:{}, maxUploadTotalSize:{}",
                    file.getSize(), currentSize, maxUploadTotalSize);
            throw new AgentStudioException(StudioError.FILE_SIZE_EXCEED_LIMIT);
        }
    }

    private void checkUploadNum(String userId) {
        String key = "uploadFile:num:" + userId;
        long currentCount = redisClient.getAndIncrement(key, timeScopeUploadNum);
        if (currentCount == 0) {
            // 如果是第一次上传，设置过期时间5分钟
            redisClient.expire(key, Duration.ofSeconds(timeScopeUploadNum));
        }
        if (currentCount > maxUploadNum) {
            log.error("The number of the upload files exceeds the limit. currentCount:{}, maxUploadNum:{}",
                    currentCount, maxUploadNum);
            throw new AgentStudioException(StudioError.AGENT_UPLOAD_FILE_NUM);
        }
    }

    /**
     * 上传文件校验
     *
     * @param file 文件
     * @param type 文件类型
     * @return 新生成的文件名
     */
    private String checkUploadFile(MultipartFile file, String type) {
        // 文件为空
        if (file == null || file.isEmpty()) {
            log.error("The uploaded file cannot be empty.");
            throw new AgentStudioException(StudioError.ILLEGAL_FILE);
        }

        FileCheckWrapper fileCheckWrapper = buildFileCheckWrapper(type);

        // 校验文件大小 file.getSize()字节
        if (file.getSize() > fileCheckWrapper.getSize() * KB) {
            log.error("The avatar file size exceeds the limit, IMAGE: {}KB, OTHERS:{}KB", imageMaxSize, fileMaxSize);
            throw new AgentStudioException(StudioError.FILE_SIZE_EXCEED_LIMIT);
        }

        // 校验文件名
        String fileName = file.getOriginalFilename();
        if (StringUtils.isBlank(fileName) || fileName.contains("..") || fileName.contains("\\") || fileName.contains(
                "/")) {
            log.error("The file name is illegal: {}", fileName);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_NAME);
        }

        // 校验文件类型
        String fileType = fileName.substring(fileName.lastIndexOf('.'));
        if (StringUtils.isBlank(fileType) || !fileCheckWrapper.getType().contains(fileType.toLowerCase(Locale.ROOT))) {
            log.error("The file type is not supported: {}", fileType);
            throw new AgentStudioException(StudioError.ILLEGAL_FILE_TYPE);
        }
        // 生成随机名
        return UUID.randomUUID() + fileType;
    }

    /**
     * 根据校验类型获取文件校验包装类
     *
     * @param type 校验类型
     * @return FileCheckWrapper 文件校验包装类
     */
    private FileCheckWrapper buildFileCheckWrapper(String type) {
        FileCheckWrapper.FileCheckWrapperBuilder builder = FileCheckWrapper.builder();
        return switch (type) {
            case Constant.ICON -> builder.size(iconMaxSize).type(allowedIconType).build();
            case Constant.IMAGE -> builder.size(imageMaxSize).type(allowedImgType).build();
            default -> builder.size(fileMaxSize).type(allowedDefaultType).build();
        };
    }

    /**
     * 处理agent对话insight信息
     *
     * @param eventObj eventObj
     * @param executeParams executeParams
     */
    private void processOnCtrlAgentNodeMessage(String sseData, JiuwenAgentEvent eventObj, AgentExecuteParams executeParams, AgentCtrlTraceData traceData, SseEmitter sseEmitter) {
        eventObj.setExecutionId(executeParams.getExecutionId());
        conversationManagementService.reportToAgentOps(executeParams, eventObj);
        if (executeParams.isDebug()) {
            traceData.appendAgentNode(eventObj);
            if (sseEmitter != null) {
                agentEventPassThrough(sseData, sseEmitter, executeParams);
            }
        }
    }

    private void processOnControllerWorkflowNodeMessage(String sseData, WorkflowRunResult result,
                                                        AgentExecuteParams executeParams, AgentCtrlTraceData traceData,SseEmitter sseEmitter) {
        JiuwenEvent eventObj = com.alibaba.fastjson2.JSONObject.parseObject(sseData, JiuwenEvent.class);
        if (eventObj == null) {
            log.error("Got null parsed jiuwen event. Do nothing with this workflow node message: {}.", sseData);
            return;
        }

        NodeRunInfo nodeRunInfo = JiuwenEventProcessor.convertNodeRunInfo(eventObj.getData());
        if (executeParams.isDebug()) {
            String workflowId = nodeRunInfo.getAgentId();
            WorkflowInvokeData invokeData = traceData.getWorkflows()
                    .computeIfAbsent(workflowId, id -> new WorkflowInvokeData(workflowId));
            invokeData.updateProperties(nodeRunInfo, eventObj.getData());

            if (result != null) {
                result.getNodeRunInfoList().add(nodeRunInfo);
            }
            if (sseEmitter != null) {
                agentEventPassThrough(sseData, sseEmitter, executeParams);
            }
        }
        if (Constant.KnowledgeRetrievalNode.PLUGIN.equals(nodeRunInfo.getNodeType())) {
            knowledgeBaseFileInfoService.processRetrievalNode(nodeRunInfo, result, sseEmitter);
        }
        eventObj.setExecutionId(executeParams.getExecutionId());
        conversationManagementService.reportToAgentOps(executeParams, eventObj);
    }

    private void processTaskEnd(SseEmitter sseEmitter, AgentExecuteParams agentExecuteParams,
                                AgentCtrlTraceData traceData) {
        if (agentExecuteParams.isDebug() || agentExecuteParams.isUploadOpsSwitch()) {
            log.info("Agent task is finish. recive task end message.");
        }
        WorkflowRunStreamRsp workflowRunStreamRsp = new WorkflowRunStreamRsp();
        workflowRunStreamRsp.setEvent(EventType.TASK_END.toString());
        workflowRunStreamRsp.setConversationId(agentExecuteParams.getConversationId());
        workflowRunStreamRsp.setCreatedTime(System.currentTimeMillis());

        AgentEvent agentEvent = new AgentEvent();
        // 未识别到意图且无默认工作流，不向前端返回executionId，触发前端的提示信息
        if (traceData.getPreEventType() != JiuwenEventType.TASK_START) {
            String executionId = StringUtils.defaultIfEmpty(
                    traceData.getExecutionId(),
                    StringUtils.defaultIfEmpty(
                            agentExecuteParams.getExecutionId(),
                            UUID.randomUUID().toString()
                    )
            );
            agentEvent.setExecutionId(executionId);
        }

        workflowRunStreamRsp.setData(agentEvent);
        if (sseEmitter != null) {
            eventProcessor.sendEvent(agentExecuteParams.getAgentId(), sseEmitter, workflowRunStreamRsp);
        }
        conversationManagementService.reportTaskEnd(agentExecuteParams);
    }

    private void processOnControllerDoneMessage(JiuwenAgentEvent eventObj, AgentExecuteParams executeParams) {
        if (executeParams.isChatTurnAdded()) {
            return;
        }

        JiuwenAgentEventData eventData = eventObj.getData();
        if (eventData == null || eventData.getAnswer() == null) {
            return;
        }
        Message message = new Message();
        message.setContent(eventData.getAnswer().toString());
        message.setRole(MessageRole.ASSISTANT.name().toLowerCase(Locale.ROOT));
        message.setCreateTime(eventObj.getCreatedTime());

        List<Message> existMessages = executeParams.getMessages();
        if (existMessages == null) {
            existMessages = new ArrayList<>();
        }
        existMessages.add(message);
        executeParams.setMessages(existMessages);
    }

    private void configureDeepResearchParams(AgentExecuteParams executeParams, JiuwenParams jiuwenParams) {
        Map<String, Object> inputs = executeParams.getInputs();
        String message = inputs.get(Constant.DeepResearch.MESSAGE_FIELD).toString();
        executeParams.setQuery(message);
        jiuwenParams.setMessage(message);
        if (inputs.containsKey(Constant.DeepResearch.FEEDBACK_FIELD)) {
            jiuwenParams.setInterruptFeedback(inputs.get(Constant.DeepResearch.FEEDBACK_FIELD).toString());
        }
        if (!inputs.containsKey(Constant.DeepResearch.TEMPLATE_FIELD)) {
            return;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> template = (Map<String, Object>) inputs.get(Constant.DeepResearch.TEMPLATE_FIELD);
        if (template.containsKey(Constant.DeepResearch.FILE_PATH_FIELD)) {
            jiuwenParams.setFileUrl(String.valueOf(template.get(Constant.DeepResearch.FILE_PATH_FIELD)))
                    .setFileName(String.valueOf(template.get(Constant.DeepResearch.FILE_NAME_FIELD)))
                    .setIsTemplate((Boolean) template.get(Constant.DeepResearch.IS_TEMPLATE_FIELD));
        }
    }

    private void configureRegularAgentParams(AgentExecuteParams executeParams, JiuwenParams jiuwenParams,
                                             List<Message> historyMessageList) {
        jiuwenParams.setConversationHistory(convertMessages(historyMessageList))
                .setToolSwitchDict(Optional.ofNullable(executeParams.getToolSwitchDict()).orElse(new HashMap<>()))
                .setEnableHistory(executeParams.isHistoryEnabled());
    }

    /**
     * 处理agent执行时，传给九问的executeParam中的用户ID
     *
     * @return
     */
    private String getAgentExecuteUserId() {
        if (Constant.ENV_SIMPLE.equals(envType)) {
            return RequestContextUtils.getRequestUserIdCompatibleCustom();
        } else {
            return RequestContextUtils.getRequestUserId();
        }
    }
}
