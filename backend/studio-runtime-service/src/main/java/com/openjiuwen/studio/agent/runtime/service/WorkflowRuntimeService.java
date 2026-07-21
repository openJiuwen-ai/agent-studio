/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import static com.openjiuwen.studio.agent.runtime.constant.Constant.REQUEST_ID;
import static com.openjiuwen.studio.agent.runtime.constant.Constant.TASK_ID;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.serializer.SerializerFeature;
import com.fasterxml.jackson.core.type.TypeReference;
import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.dto.agent.ConversationInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.dto.agent.NodeRunInfo;
import com.openjiuwen.studio.agent.common.dto.agent.Status;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsWorkflowReq;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.common.utils.PublishUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.dto.ContextDTO;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenEvent;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenEventData;
import com.openjiuwen.studio.agent.runtime.dto.ParamExtractionIndex;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.runtime.dto.RoundDTO;
import com.openjiuwen.studio.agent.runtime.dto.TaskTypeEnum;
import com.openjiuwen.studio.agent.runtime.dto.WorkFlowDTO;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunInfo;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunRsp;
import com.openjiuwen.studio.agent.runtime.entity.ModelConfig;
import com.openjiuwen.studio.agent.runtime.entity.WorkflowInstanceEntity;
import com.openjiuwen.studio.agent.runtime.enums.JiuwenEventType;
import com.openjiuwen.studio.agent.runtime.enums.MessageRole;
import com.openjiuwen.studio.agent.runtime.enums.ParamExtractionType;
import com.openjiuwen.studio.agent.runtime.enums.WorkflowRunStatus;
import com.openjiuwen.studio.agent.runtime.model.Conversation;
import com.openjiuwen.studio.agent.runtime.model.ExecuteParams;
import com.openjiuwen.studio.agent.runtime.model.ModelApiLog;
import com.openjiuwen.studio.agent.runtime.model.WorkflowIrMetadata;
import com.openjiuwen.studio.agent.runtime.model.WorkflowIrWrapper;
import com.openjiuwen.studio.agent.runtime.model.WorkflowRunResult;
import com.openjiuwen.studio.agent.runtime.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.runtime.sensitive.SensitiveTrieUtils;
import com.openjiuwen.studio.agent.runtime.thread.ModelApiLogThreadLocal;
import com.openjiuwen.studio.agent.runtime.utils.CommonUtils;
import com.openjiuwen.studio.agent.runtime.utils.JsonUtils;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

import javax.annotation.Resource;

/**
 * workflow运行面service
 *
 */
@Slf4j
@Service
public class WorkflowRuntimeService implements IWorkflowRuntimeService {
    private static final String HC_ENV = "hc";

    private static final int THREAD_POOL_SIZE = 100;

    private static final String PARAM_EXTRACTION = "ParamExtraction";

    private static final String COMPOSITE = "composite";

    private static final String JIUWEN_EXCEPTION_NODE_ID = "jiuwen_exception_node_id";

    private final ExecutorService fixedThreadPool = Executors.newFixedThreadPool(THREAD_POOL_SIZE);

    @Resource(name = "JiuwenWorkflowRunCoreService")
    private IWorkflowRunCoreService workflowRunService;

    @Autowired
    private WorkflowIrCacheService workflowIrCacheService;

    @Autowired
    private ConversationManagementService conversationManagementService;

    @Autowired
    private WorkflowInstanceService workflowInstanceService;

    @Autowired
    private JiuWenService jiuWenService;

    @Value("${workflow.max-query-length}")
    private int workflowMaxQueryLength;

    @Value("${workflow.sse-timeout-milliseconds}")
    private long workflowSseTimeoutMilliSec;

    @Value("${workflow.max-execution-size:}")
    private Integer maxExecutionSize;

    @Value("${env.type}")
    private String envType;

    @Autowired
    private PublishUtils publishUtils;

    @Autowired
    private ObsService obsService;

    @Autowired
    private AgentRuntimeService agentRuntimeService;

    /**
     * 工作流运行非流式接口
     *
     * @param executeParams 执行参数
     * @return 返回流式接口对象
     */
    public WorkflowRunRsp runWorkflow(ExecuteParams executeParams) {
        log.info("runWorkflow begin, conversationId:{}, workflowId:{}, version:{}, debug:{}, trace:{}.",
                executeParams.getConversationId(), executeParams.getWorkflowId(), executeParams.getVersion(),
                executeParams.isDebug(), executeParams.isTrace());

        // 运行前检查
        checkBeforeRun(executeParams);

        WorkflowRunRsp resp = runWorkflowCore(executeParams);
        log.info("runWorkflow end, resp:{}.", resp.toString());
        return resp;
    }

    /**
     * 工作流运行核心逻辑
     * 要考虑流式和非流式的不同处理方式
     *
     * @param executeParam 执行参数
     * @return 返回流式接口对象
     */
    private WorkflowRunRsp runWorkflowCore(ExecuteParams executeParam) {
        String conversationId = executeParam.getConversationId();

        // 1.会话管理，查询历史会话 -- 迭代一当次用户query也放到历史会话
        Conversation conversation;
        if (executeParam.getConversation() != null) {
            conversation = executeParam.getConversation();
        } else {
            conversation = getConversation(executeParam);
        }
        if (conversation.isOld()) {
            executeParam.setOldConversation(true);
        }
        // ir变化时清理九问会话实例
        clearJiuwenConversation(conversationId, conversation, executeParam);

        // 2.会话管理，创建会话记录用户query,(请求参数中带有query字段 && (非单节点调测模式 || 单节点调测模式包含query字段))时更新会话
        if (executeParam.getInputs().containsKey(Constant.Jiuwen.USER_MSG_FIELD) && (!executeParam.isNodeExecute()
            || executeParam.getInputs().get(Constant.Jiuwen.USER_MSG_FIELD) != null)
            && executeParam.isEnableHistory()) {
            // 初始化对话消息列表
            executeParam.getMessages()
                .add(new Message().setRole(MessageRole.USER.name().toLowerCase(Locale.ROOT))
                    .setContent(executeParam.getInputs().get(Constant.Jiuwen.USER_MSG_FIELD).toString())
                    .setCreateTime(System.currentTimeMillis()));
        }

        // 3.工作流运行
        WorkflowRunResult result = workflowRunService.runWorkflow(executeParam, conversation);

        Long endTime = System.currentTimeMillis();
        WorkflowRunInfo workflowRunInfo = result.getWorkflowRunInfo();
        return WorkflowRunRsp.builder()
            .outputs(workflowRunInfo == null ? null : result.getWorkflowRunInfo().getOutputs())
            .nodeInfo(result.getNodeRunInfoList())
            .startTime(executeParam.getStartTime())
            .endTime(endTime)
            .conversationId(executeParam.getConversationId())
            .metadata(workflowRunInfo == null ? null : result.getWorkflowRunInfo().getMetadata())
            .status(workflowRunInfo == null
                ? WorkflowRunStatus.FAILED.getStatus()
                : result.getWorkflowRunInfo().getStatus())
            .errorCode(workflowRunInfo == null ? null : workflowRunInfo.getErrorCode())
            .errorMessage(workflowRunInfo == null ? null : result.getWorkflowRunInfo().getErrorMessage())
            .messages(result.getMessageList())
            .knowledgeBaseFileInfoList(result.getKnowledgeBaseFileInfoList())
            .build();
    }

    private void clearJiuwenConversation(String conversationId, Conversation conversation,
        ExecuteParams executeParams) {
        String workflowId = executeParams.getWorkflowId();
        String releasedVersion = executeParams.getReleasedVersion();

        // 发布版本不用清理
        if (!StringUtils.isEmpty(releasedVersion)) {
            return;
        }
        try {
            long wfUpdateTime = workflowIrCacheService.getIrMetadata(workflowId, releasedVersion).getUpdatedAt();

            // 如果会话最后修改时间小于ir更新时间，则先调用九问接口清除九文会话
            if (conversation.getLastUpdateTime() > 0 && conversation.getLastUpdateTime() < wfUpdateTime) {
                log.info("Conversation time less ir update time. {}  {} flowId:{}", conversation.getLastUpdateTime(),
                    wfUpdateTime, workflowId);
                jiuWenService.deleteConversationIr(conversationId, workflowIrCacheService.getIrPath(workflowId));
            }
        } catch (Exception e) {
            log.error("clear jiuwen conversation failed.", e);
        }
    }

    @Override
    public Status abortConversation(String projectId, String workflowId, String conversationId) {
        jiuWenService.deleteConversationIr(conversationId);

        return new Status().setCode(0).setDesc("succeeded");
    }

    @Override
    public AutoAddResultJsonObject additionalQuestionsWorkflow(String projectId, String workflowId,
        String conversationId, String workspaceId, AdditionalQuestionsWorkflowReq body) {
        if (StringUtils.isBlank(body.getName())) {
            log.error("Agent name is null. projectId = {}, workflowId = {}", projectId, workflowId);
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED);
        }
        if (!body.isEnable()) {
            log.error("Abnormal interface calling. projectId = {}, workflowId = {}", projectId, workflowId);
            throw new AgentStudioException(StudioError.INTERFACE_CALL_EXCEPTION);
        }

        // 获取历史会话消息
        List<Message> messageList;
        try {
            RetrieveConversationQo retrieveConversationQo = new RetrieveConversationQo().setVersionId(
                body.getVersionId());
            messageList = conversationManagementService.retrieveConversation(projectId, workflowId, conversationId,
                retrieveConversationQo);
        } catch (AgentStudioException e) {
            log.error("Retrieve history messages failed. projectId = {}, workflowId = {}, conversationId = {}",
                projectId, workflowId, conversationId);
            throw new AgentStudioException(StudioError.REDISSON_GET_BUCKET_FAILED);
        }
        if (CollectionUtils.isNotEmpty(messageList)) {
            log.info("Conversation [{}]: successfully retrieved {} historical messages.", conversationId,
                messageList.size());
            for (int i = 0; i < messageList.size(); i++) {
                Message msg = messageList.get(i);
                log.debug("Message index [{}]: role={}, content={}", i, msg.getRole(), msg.getContent());
            }
        } else {
            log.warn("Conversation [{}]: no messages found.", conversationId);
        }
        if (messageList.size() < 2) {
            log.error("History messages are incorrect. projectId = {}, workflowId = {}, conversationId = {}", projectId,
                workflowId, conversationId);
            return new AutoAddResultJsonObject().setQuestions(new ArrayList<>());
        }
        StringBuilder historyMessages = new StringBuilder();
        for (int index = messageList.size() - 2; index < messageList.size(); index++) {
            historyMessages.append(messageList.get(index).getContent()).append("\n");
        }

        // 获取模型信息
        ModelConfig modelConfig = ModelConfig.builder()
            .modelName(body.getModelId())
            .modelType(body.getModelType())
            .build();

        // 构造query
        boolean isChinese = LanguageUtils.isChinese();
        String template = com.openjiuwen.studio.agent.common.utils.CommonUtils.getResourceContent(
            isChinese ? Constant.ADDITIONAL_QUESTIONS_PROMPT : Constant.ADDITIONAL_QUESTIONS_PROMPT_EN);
        PromptTemplate promptTemplate = new PromptTemplate(template);
        String query = promptTemplate.format(KV.of(Constant.NAME, body.getName()),
            KV.of(Constant.HISTORY_MESSAGES, historyMessages.toString()),
            KV.of(Constant.USER_PROMPT, StringUtils.defaultIfEmpty(body.getPrompt(), "")));

        // 调用模型并解析返回结果
        List<String> questionList = new ArrayList<>();
        for (int callCounts = 0; callCounts < Constant.MODEL_CALLS; callCounts++) {
            questionList = JsonUtils.json2Obj(
                agentRuntimeService.callModel(agentRuntimeService.buildAskModelReq(modelConfig, query), workspaceId,
                    RequestContextUtils.getRequestUserDomainId()), new TypeReference<List<String>>() {
                });
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

    private Conversation getConversation(ExecuteParams executeParams) {
        Conversation conversation;
        if (!StringUtils.isEmpty(executeParams.getConversationId())) {
            try {
                conversation = conversationManagementService.retrieveConversationCore(executeParams.getProjectId(),
                    executeParams.getWorkflowId(), executeParams.getConversationId(),
                    executeParams.getReleasedVersion());
            } catch (Exception e) {
                log.info("new conversationId:{}", executeParams.getConversationId());
                conversation = new Conversation();
            }
        } else {
            conversation = new Conversation();
            String conversationId = UUID.randomUUID().toString();
            executeParams.setConversationId(conversationId);
        }

        if (conversation == null) {
            conversation = new Conversation();
        }

        return conversation;
    }

    private void checkBeforeRun(ExecuteParams executeParams) {
        log.info("checkBeforeRun begin.");

        Object queryParams = executeParams.getInputs().get(Constant.Jiuwen.USER_MSG_FIELD);

        // 对工作流进行query字段输入进行长度校验
        if (queryParams instanceof String && queryParams.toString().length() > workflowMaxQueryLength) {
            log.error("workflow query param exceed max length {}", workflowMaxQueryLength);
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID);
        }

        AgentMetadata agentMetadata = getWorkflowMetadata(executeParams);
        // 会话型工作流校验 query 非空
        if (!executeParams.isNodeExecute()
            && Strings.CI.equals(agentMetadata.getAppType(), TaskTypeEnum.CHAT.getValue())
            && (queryParams == null || StringUtils.isBlank(queryParams.toString()))) {
            log.error("query param is empty: {}", queryParams);
            throw new AgentStudioException(StudioError.METHOD_ARGUMENT_NOT_VALID, List.of("parameter query is needed"));
        }

        // 非网页发布在此处校验租户
        if (!executeParams.isWebPage() && !executeParams.getProjectId().equals(agentMetadata.getProjectId())
            && !executeParams.isTreasure()) {
            throw new AgentStudioException(StudioError.INSUFFICIENT_WORKFLOW_RUN_PRIVILEGES);
        }
        if (!HC_ENV.equals(envType) && executeParams.getReleasedVersion() == null && executeParams.getVersion() != null
                && executeParams.getVersion() != agentMetadata.getUpdatedAt()) {
            log.error("Workflow is not last workflow version.  execute version:{} updateAt:{}",
                    executeParams.getVersion(), agentMetadata.getUpdatedAt());
            throw new AgentStudioException(StudioError.NOT_LATEST_WORKFLOW);
        }

        // 初始化敏感词树
        executeParams.setSensitiveTrieUtils(new SensitiveTrieUtils(Constant.AppType.WORKFLOW, agentMetadata));

        log.info("checkBeforeRun end.");
    }

    private AgentMetadata getWorkflowMetadata(ExecuteParams executeParams) {
        AgentMetadata agentMetadata;

        // 百宝箱或最新版本，从redis读取版本信息，优先运行百宝箱
        if (executeParams.isLatestPublish() || executeParams.isTreasure()) {
            // 发布版本(最新版本)，读redis
            agentMetadata = publishUtils.getPublish(executeParams.getWorkflowId(),
                executeParams.isTreasure() ? Constants.TREASURE_PUBLISH_VERSION : Constants.LATEST_PUBLISH_VERSION,
                obsService);
            if (agentMetadata != null) {
                // 从metadata解析实际执行版本
                executeParams.setReleasedVersion(agentMetadata.getVersionId());

                // 最新版本或百宝箱，刷新对应版本缓存
                workflowIrCacheService.refreshWorkflowIr(executeParams, agentMetadata.getVersionId());
            }
        } else {
            // 非最新版本或编辑态，刷新缓存，编辑态、发布版本(带version)旧逻辑不变，内存缓存+OBS一次读
            WorkflowIrWrapper irWrapper = workflowIrCacheService.refreshWorkflowIr(executeParams,
                executeParams.getReleasedVersion());
            WorkflowIrMetadata metadata = irWrapper.getMetadata();
            if (StringUtils.isEmpty(executeParams.getOwnerWorkspaceId())) {
                executeParams.setOwnerWorkspaceId(metadata.getWorkspaceId());
            }

            agentMetadata = AgentMetadata.builder()
                .projectId(metadata.getProjectId())
                .updatedAt(metadata.getUpdatedAt())
                .isContentReviewEnable(irWrapper.isContentReviewEnabled())
                .safetyBarrier(irWrapper.isSafetyBarrier())
                .agentId(executeParams.getWorkflowId())
                .versionId(executeParams.getReleasedVersion())
                .appType(metadata.getType())
                .build();
        }

        if (agentMetadata == null) {
            log.error("get agent metadata failed");
            if (executeParams.isLatestPublish()) {
                throw new AgentStudioException(StudioError.WORKFLOW_NOT_EXIST,
                    "use latest publish version need republish first");
            }
            throw new AgentStudioException(StudioError.AGENT_NOT_EXIST);
        }

        return agentMetadata;
    }

    /**
     * 工作流运行流式接口
     *
     * @param executeParams 执行参数
     * @return 返回流式接口对象
     */
    public SseEmitter runWorkflowStream(ExecuteParams executeParams) {
        log.info("runWorkflowStream begin, conversationId:{}, workflowId:{}, debug:{}, trace:{}.", executeParams.getConversationId(),
            executeParams.getWorkflowId(), executeParams.isDebug(), executeParams.isTrace());
        SseEmitter sseEmitters = new SseEmitter(workflowSseTimeoutMilliSec);
        executeParams.setSseEmitter(sseEmitters);
        String authToken = RequestContextUtils.getRequestAuthToken();
        Map<String, String> curHeaders = RequestContextUtils.getHeaders();
        String language = RequestHeaderHolderUtils.getRequestLanguage();
        try {
            // 执行前检查
            checkBeforeRun(executeParams);
            String requestId = MDC.get(REQUEST_ID);
            String taskId = MDC.get(TASK_ID);
            ModelApiLog apiLog = ModelApiLogThreadLocal.getApiLog();
            fixedThreadPool.submit(() -> {
                try {
                    MDC.put(REQUEST_ID, requestId);
                    MDC.put(TASK_ID, taskId);
                    RequestContextUtils.setRequestAuthTokenAndUserId(authToken, executeParams.getProjectId(),
                        executeParams.getUserId());
                    RequestContextUtils.setHeaders(curHeaders);
                    RequestHeaderHolderUtils.setRequestLanguage(language);
                    ModelApiLogThreadLocal.setApiLog(apiLog);
                    runWorkflowCore(executeParams);
                } catch (Exception e) {
                    String error = String.format("stream interface failed,workflowId:%s, conversationId:%s",
                        executeParams.getWorkflowId(), executeParams.getConversationId());
                    log.error(error, e);
                    sseEmitters.completeWithError(e);
                } finally {
                    RequestHeaderHolderUtils.clear();
                }
            });
        } catch (AgentStudioException e) {
            log.error("Run workflow failed.", e);
            throw e;
        } catch (Exception e) {
            log.error("Run workflow failed.", e);
            throw new AgentStudioException(StudioError.WORKFLOW_RUN_FAILED);
        }
        log.info("runWorkflowStream end.");
        return sseEmitters;
    }

    /**
     * 处理参数提取节点的内循环
     *
     * @param nodeRunInfos    所有事件
     * @param cycleBeginIndex 内循环开始的标志位
     */
    private RoundDTO paramExtractionInCirculation(List<NodeRunInfo> nodeRunInfos, int cycleBeginIndex) {
        RoundDTO round = new RoundDTO();
        round.setWorkflowList(new ArrayList<>());
        round.setContextList(new ArrayList<>());
        round.setIndex(-1);
        for (int i = cycleBeginIndex + 2; i < nodeRunInfos.size(); i++) {
            NodeRunInfo nowNode = nodeRunInfos.get(i);
            // 执行遇见错误
            if (nowNode.getErrorMessage() != null) {
                round.setErrorNode(nowNode);
                return round;
            }
            // finish事件错误
            if (i + 1 < nodeRunInfos.size() && nodeRunInfos.get(i + 1).getErrorMessage() != null) {
                round.setErrorNode(nodeRunInfos.get(i + 1));
                return round;
            }
            // 异常事件
            if (isEndExceptionNode(nowNode)) {
                NodeRunInfo endNode = nodeRunInfos.get(i + 1);
                round.setErrorNode(endNode);
                round.setIndex(i + 1);
                break;
            }
            // 结束事件
            if (isEndNode(nowNode)) {
                round.setIndex(i + 1);
                break;
            }
            // domain_objects子工作流
            if (isDomainObjectsNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode, ParamExtractionType.DOMAIN_OBJECTS);
                continue;
            }
            // extension_after_extraction子工作流
            if (isExtensionAfterExtractionNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode, ParamExtractionType.EXTENSION_AFTER_EXTRACTION);
                continue;
            }
            // extension_before_judge_quit子工作流
            if (isExtensionBeforeJudgeQuitNode(nowNode)) {
                i = processSubWorkflow(round, nodeRunInfos, i, nowNode,
                    ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT);
                continue;
            }
            // 大模型节点
            if (isLlmNode(nowNode)) {
                round.setModuleInput(nowNode.getInputs());
                round.setModuleOutput(nowNode.getOutputs());
            }
        }

        // 交互节点是否中断判定
        if (round.getIndex() == -1) {
            round.setIndex(nodeRunInfos.size() - 1);
        }
        return round;
    }

    private int processSubWorkflow(RoundDTO round, List<NodeRunInfo> nodeRunInfos, int currentIndex,
        NodeRunInfo currentNode, ParamExtractionType workflowType) {
        int newIndex = currentIndex + 2;// 直接跳到扩展子工作流的开始节点
        WorkFlowDTO workflow = instructWorkFlow(nodeRunInfos, newIndex, currentNode.getNodeId(),
            workflowType.name().toLowerCase(Locale.ROOT));

        if (ParamExtractionType.DOMAIN_OBJECTS.equals(workflowType)) {
            workflow.setDomainObjectName(getTrueObjectNames(currentNode.getNodeName()));
        }
        setContextList(nodeRunInfos, newIndex - 2, workflow);

        round.getWorkflowList().add(workflow);

        if (isErrorEventWorkflow(workflow, round, currentNode)) {
            return nodeRunInfos.size(); // 遇到异常，直接终止最外层循环
        }

        return workflow.getIndex();
    }

    private String getTrueObjectNames(String oriObjectName) {
        if (oriObjectName == null || oriObjectName.isEmpty()) {
            return "";
        }
        int index = oriObjectName.indexOf("domain_objects_");
        if (index == -1) {
            return "";
        }
        int startIndex = index + "domain_objects_".length();
        if (startIndex < oriObjectName.length()) {
            return oriObjectName.substring(startIndex);
        }
        return "";
    }

    private Boolean isErrorEventWorkflow(WorkFlowDTO workflow, RoundDTO round, NodeRunInfo nowNode) {
        if (workflow.getErrorMessage() != null) {
            nowNode.setErrorMessage(workflow.getErrorMessage());
            nowNode.setStatus(workflow.getStatus());
            round.setErrorNode(nowNode);
            return true;
        }
        return false;
    }

    /**
     * 处理参数提取节点的外循环
     *
     * @param nodeRunInfos      所有事件
     * @param startProcessIndex 外循环开始的标志位
     * @param sumName           提取节点的名字
     * @param inputs            提取节点的原始输入
     */
    private ParamExtractionIndex paramExtractionOutCirculation(List<NodeRunInfo> nodeRunInfos, int startProcessIndex,
        String sumName, Map<String, Object> inputs) {
        ParamExtractionIndex paramExtractionIndex = new ParamExtractionIndex();
        paramExtractionIndex.setIndex(-1);
        NodeRunInfo sumNode = createSumNode(nodeRunInfos, startProcessIndex, sumName,
            NodeRunInfo.NodeStatusEnum.FINISHED);

        // 处理extension_before_entry类型
        List<WorkFlowDTO> beforeWorkflowList = new ArrayList<>();
        int cycleBegin = processBeforeEntryEvents(beforeWorkflowList, nodeRunInfos, startProcessIndex, inputs, sumNode,
            paramExtractionIndex);
        // before事件异常
        if (cycleBegin == -1) {
            return paramExtractionIndex;
        }
        // 验证循环开始事件
        if (!isCycleBeginEvent(nodeRunInfos.get(cycleBegin))) {
            log.warn("before event next event is not cycle begin event !");
            finalizeResult(sumNode, inputs, nodeRunInfos, new ArrayList<>(), beforeWorkflowList, paramExtractionIndex);
            return paramExtractionIndex;
        }
        // 内循环处理
        List<RoundDTO> roundList = new ArrayList<>();
        int cycleEnd = processCirculationEvents(roundList, nodeRunInfos, cycleBegin, inputs, beforeWorkflowList,
            sumNode, paramExtractionIndex);
        if (cycleEnd == -1) {
            return paramExtractionIndex;
        }
        // 处理最终结果
        finalizeResult(sumNode, inputs, nodeRunInfos, roundList, beforeWorkflowList, paramExtractionIndex);
        return paramExtractionIndex;
    }

    private NodeRunInfo createSumNode(List<NodeRunInfo> nodeRunInfos, int startProcessIndex, String sumName,
        NodeRunInfo.NodeStatusEnum type) {
        NodeRunInfo sumNode = new NodeRunInfo();
        NodeRunInfo nowNode = nodeRunInfos.get(startProcessIndex);
        // 总节点设置名字和id
        String[] nameParts = nowNode.getNodeId().split("_");
        String nodeId = "";
        if (nameParts.length < 2) {
            log.warn("event node is illegal, nodeName: {}, oriNodeId: {}", sumName, nowNode.getNodeId());
        }
        nodeId = nameParts[1] + '_' + nameParts[2];
        sumNode.setMetadata(new HashMap<>());
        sumNode.setNodeId(nodeId);
        sumNode.setNodeStatus(type);
        sumNode.setNodeType(PARAM_EXTRACTION);
        sumNode.setNodeName(sumName);

        Status status = new Status();
        status.setCode(0);
        status.setDesc("succeeded");
        sumNode.setStatus(status);

        return sumNode;
    }

    private int processBeforeEntryEvents(List<WorkFlowDTO> beforeWorkflowList, List<NodeRunInfo> nodeRunInfos,
        int startProcessIndex, Map<String, Object> inputs, NodeRunInfo sumNode,
        ParamExtractionIndex paramExtractionIndex) {
        log.info("process before entry events start.");
        for (int beforeIndex = startProcessIndex; beforeIndex < nodeRunInfos.size(); beforeIndex++) {
            NodeRunInfo currentNode = nodeRunInfos.get(beforeIndex);

            if (!isBeforeEntryEvent(currentNode)) {
                // before_entry事件结束，循环事件开始
                startProcessIndex = beforeIndex;
                break;
            }
            // before事件直接报错
            if (hasErrorInBeforeEvent(nodeRunInfos, beforeIndex)) {
                setErrorNodeInfo(sumNode, nodeRunInfos, beforeIndex + 1, inputs, beforeWorkflowList, new ArrayList<>());
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                log.info("process before entry events finish : before event error.");
                return -1;
            }

            WorkFlowDTO newWork = paramExtractionBeforeEvent(nodeRunInfos, beforeIndex);
            beforeWorkflowList.add(newWork);
            // 如果遇见异常，直接返回总结点的结束
            if (newWork.getErrorMessage() != null) {
                setErrorNodeInfo(sumNode, nodeRunInfos, startProcessIndex - 1, inputs, beforeWorkflowList,
                    new ArrayList<>());
                sumNode.setErrorMessage(newWork.getErrorMessage());
                sumNode.setStatus(newWork.getStatus());
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                log.info("process before entry events finish : other event error.");
                return -1;
            }

            beforeIndex = newWork.getIndex();
            startProcessIndex = beforeIndex;
        }
        log.info("process before entry events finish : success.");
        return startProcessIndex;
    }

    private boolean hasErrorInBeforeEvent(List<NodeRunInfo> nodeRunInfos, int beforeIndex) {
        return beforeIndex + 1 < nodeRunInfos.size() && nodeRunInfos.get(beforeIndex + 1).getErrorMessage() != null
            && beforeIndex + 2 >= nodeRunInfos.size();
    }

    private int processCirculationEvents(List<RoundDTO> roundList, List<NodeRunInfo> nodeRunInfos,
        int startProcessIndex, Map<String, Object> inputs, List<WorkFlowDTO> beforeWorkflowList, NodeRunInfo sumNode,
        ParamExtractionIndex paramExtractionIndex) {
        for (int circulationIndex = startProcessIndex; circulationIndex < nodeRunInfos.size(); circulationIndex++) {
            NodeRunInfo currentNode = nodeRunInfos.get(circulationIndex);
            log.info("param extraction in cycle begin, event index is {}", circulationIndex);
            if (!isCycleBeginEvent(currentNode)) {
                // 一轮循环事件结束，新事件开始
                paramExtractionIndex.setIndex(circulationIndex - 1);
                break;
            }
            // cycle事件直接报错
            if (hasErrorInCycleEvent(nodeRunInfos, circulationIndex)) {
                setErrorNodeInfo(sumNode, nodeRunInfos, circulationIndex + 1, inputs, beforeWorkflowList, roundList);
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                return -1;
            }
            // 一轮循环
            RoundDTO round = paramExtractionInCirculation(nodeRunInfos, circulationIndex);
            processRoundContextList(round);
            roundList.add(round);

            if (round.getErrorNode() != null) {
                setErrorNodeInfo(sumNode, nodeRunInfos, startProcessIndex - 1, inputs, beforeWorkflowList, roundList);
                sumNode.setErrorMessage(round.getErrorNode().getErrorMessage());
                sumNode.setStatus(round.getErrorNode().getStatus());
                paramExtractionIndex.setParamFinishNode(sumNode);
                paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
                return -1;
            }
            circulationIndex = round.getIndex();
        }
        return nodeRunInfos.size();
    }

    private boolean hasErrorInCycleEvent(List<NodeRunInfo> nodeRunInfos, int circulationIndex) {
        return circulationIndex + 1 < nodeRunInfos.size()
            && nodeRunInfos.get(circulationIndex + 1).getErrorMessage() != null;
    }

    private void setErrorNodeInfo(NodeRunInfo sumNode, List<NodeRunInfo> nodeRunInfos, int errorIndex,
        Map<String, Object> inputs, List<WorkFlowDTO> beforeWorkflowList, List<RoundDTO> roundList) {
        sumNode.setInputs(inputs);
        sumNode.setErrorMessage(nodeRunInfos.get(errorIndex).getErrorMessage());
        sumNode.setStartTime(nodeRunInfos.get(errorIndex).getStartTime());
        sumNode.setEndTime(nodeRunInfos.get(errorIndex).getEndTime());
        sumNode.setStatus(nodeRunInfos.get(errorIndex).getStatus());
        sumNode.getMetadata().put("workflow_list", beforeWorkflowList);
        sumNode.getMetadata().put("round_list", roundList);
    }

    private void finalizeResult(NodeRunInfo sumNode, Map<String, Object> inputs, List<NodeRunInfo> nodeRunInfos,
        List<RoundDTO> roundList, List<WorkFlowDTO> beforeWorkflowList, ParamExtractionIndex paramExtractionIndex) {
        // 是否有返回带错误的error事件
        if (!roundList.isEmpty() && roundList.get(roundList.size() - 1).getErrorNode() != null) {
            RoundDTO errorRound = roundList.get(roundList.size() - 1);
            sumNode.setErrorMessage(errorRound.getErrorNode().getErrorMessage());
            sumNode.setStatus(errorRound.getErrorNode().getStatus());
        }
        // 交互节点中断情况
        if (paramExtractionIndex.getIndex() == -1) {
            paramExtractionIndex.setIndex(nodeRunInfos.size() - 1);
        }
        // 模型输出作为round的输出
        if (!roundList.isEmpty()) {
            sumNode.setInputs(inputs);
            sumNode.setOutputs(roundList.get(roundList.size() - 1).getModuleOutput());
            sumNode.setStartTime(nodeRunInfos.get(paramExtractionIndex.getIndex()).getStartTime());
            sumNode.setEndTime(nodeRunInfos.get(paramExtractionIndex.getIndex()).getEndTime());
        }
        // 拼装workflowList和roundList到sumNode里面的metadata
        sumNode.getMetadata().put("workflow_list", beforeWorkflowList);
        sumNode.getMetadata().put("round_list", roundList);
        paramExtractionIndex.setParamFinishNode(sumNode);
    }

    private void processRoundContextList(RoundDTO round) {
        Map<String, ContextDTO> contextDTOMap = new HashMap<>();
        for (WorkFlowDTO workflow : round.getWorkflowList()) {
            if (workflow.getContextList() == null) {
                continue;
            }
            workflow.getContextList().forEach((key, value) -> contextDTOMap.merge(key, value, (existing, newValue) -> {
                existing.setValueAfter(newValue.getValueAfter());
                return existing;
            }));
        }
        List<ContextDTO> contextList = new ArrayList<>(contextDTOMap.values());
        round.setContextList(contextList);
    }

    private WorkFlowDTO instructWorkFlow(List<NodeRunInfo> nodeRunInfos, int startIndex, String nodeIdFlag,
        String paramEventType) {
        WorkFlowDTO work = new WorkFlowDTO();
        work.setTiming(paramEventType);
        work.setEventList(new ArrayList<>());
        work.setContextList(new HashMap<>());
        work.setIndex(-1);
        int returnIndex;
        for (int index = startIndex; index < nodeRunInfos.size(); index++) {
            NodeRunInfo nowNode = nodeRunInfos.get(index);

            // 如果遇到异常，立刻终止循环，返回异常信息
            if (nowNode.getErrorMessage() != null) {
                work.getEventList().add(nowNode);
                work.setErrorMessage(nowNode.getErrorMessage());
                work.setStatus(nowNode.getStatus());
                return work;
            }

            // 结束循环
            if (nowNode.getParentNodeId() == null || !nowNode.getParentNodeId().equals(nodeIdFlag)) {
                // 工作流构建完毕，设定下一个世事件的开始index，外层循环会+1，这里设置为-1
                returnIndex = index - 1;
                work.setIndex(returnIndex);
                break;
            }
            work.setId(nowNode.getAgentId());
            work.getEventList().add(nowNode);

        }
        // 交互节点中断的情况
        if (work.getIndex() == -1) {
            work.setIndex(nodeRunInfos.size() - 1);
        }
        return work;
    }

    private WorkFlowDTO paramExtractionBeforeEvent(List<NodeRunInfo> nodeRunInfos, int beforeBeginIndex) {
        // 处理before事件，直到非before事件结束
        NodeRunInfo nowNode = nodeRunInfos.get(beforeBeginIndex);
        int instructIndex = beforeBeginIndex + 2;
        WorkFlowDTO workFlowDetail = instructWorkFlow(nodeRunInfos, instructIndex, nowNode.getNodeId(),
            ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT));

        setContextList(nodeRunInfos, beforeBeginIndex, workFlowDetail);
        return workFlowDetail;
    }

    private void setContextList(List<NodeRunInfo> nodeRunInfos, int startIndex, WorkFlowDTO workflow) {
        workflow.setContextList(new HashMap<>());

        Map<String, Object> inputMemory = Optional.ofNullable(nodeRunInfos.get(startIndex).getMemory())
            .orElse(new HashMap<>());
        Map<String, Object> outputMemory = Optional.ofNullable(
                startIndex + 1 < nodeRunInfos.size() ? nodeRunInfos.get(startIndex + 1).getMemory() : null)
            .orElse(new HashMap<>());

        for (Map.Entry<String, Object> input : inputMemory.entrySet()) {
            ContextDTO contextDTO = new ContextDTO();
            String valueKey = input.getKey();
            Object valueBefore = input.getValue();
            valueBefore = replaceNoneWithEmpty(valueBefore);
            contextDTO.setName(valueKey);
            contextDTO.setValueBefor(JSON.toJSONString(valueBefore, SerializerFeature.WriteMapNullValue));
            workflow.getContextList().put(valueKey, contextDTO);
        }

        for (Map.Entry<String, Object> output : outputMemory.entrySet()) {
            String valueKey = output.getKey();
            Object valueAfter = output.getValue();
            valueAfter = replaceNoneWithEmpty(valueAfter);
            if (workflow.getContextList().get(valueKey) != null) {
                workflow.getContextList()
                    .get(valueKey)
                    .setValueAfter(JSON.toJSONString(valueAfter, SerializerFeature.WriteMapNullValue));
            }
        }
    }

    private Object replaceNoneWithEmpty(Object input) {
        if (input instanceof String) {
            return ((String) input).equals("None") ? "" : input;
        } else if (input instanceof Map) {
            @SuppressWarnings("unchecked") Map<String, Object> map = (Map<String, Object>) input;
            Map<String, Object> newMap = new HashMap<>();
            for (Map.Entry<String, Object> entry : map.entrySet()) {
                Object val = entry.getValue();
                if (val instanceof String && ((String) val).equals("None")) {
                    newMap.put(entry.getKey(), "");
                } else {
                    newMap.put(entry.getKey(), replaceNoneWithEmpty(val));
                }
            }
            return newMap;
        } else if (input instanceof List) {
            List<Object> list = new ArrayList<>();
            for (Object item : (List<?>) input) {
                list.add(replaceNoneWithEmpty(item));
            }
            return list;
        }
        return input;
    }

    private boolean isEndExceptionNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.END_EXCEPTION.name().toLowerCase(Locale.ROOT));
    }

    private boolean isEndNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.END.name().toLowerCase(Locale.ROOT)) && node.getNodeId()
            .contains(COMPOSITE);
    }

    private boolean isDomainObjectsNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.DOMAIN_OBJECTS.name().toLowerCase(Locale.ROOT));
    }

    private boolean isExtensionAfterExtractionNode(NodeRunInfo node) {
        return node.getNodeId()
            .contains(ParamExtractionType.EXTENSION_AFTER_EXTRACTION.name().toLowerCase(Locale.ROOT));
    }

    private boolean isExtensionBeforeJudgeQuitNode(NodeRunInfo node) {
        return node.getNodeId()
            .contains(ParamExtractionType.EXTENSION_BEFORE_JUDGE_QUIT.name().toLowerCase(Locale.ROOT));
    }

    private boolean isLlmNode(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.LLM.name().toLowerCase(Locale.ROOT));
    }

    private boolean isBeforeEntryEvent(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.EXTENSION_BEFORE_ENTRY.name().toLowerCase(Locale.ROOT));
    }

    private boolean isCycleBeginEvent(NodeRunInfo node) {
        return node.getNodeId().contains(ParamExtractionType.CYCLE_BEGIN.name().toLowerCase(Locale.ROOT));
    }

    private boolean isStartCompositeEvent(NodeRunInfo node) {
        return node.getNodeId() != null && node.getNodeId()
            .contains(ParamExtractionType.START.name().toLowerCase(Locale.ROOT)) && node.getNodeId()
            .contains(COMPOSITE);
    }
}
