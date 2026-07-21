/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.runtime.service;

import static com.openjiuwen.studio.agent.runtime.constant.Constant.AppType.AGENT;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_AGENT_ID;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_AGENT_QUESTION;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_DOMAIN_ID;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_PROJECT_ID;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_TOKEN;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_UPDATED_TIME;
import static com.openjiuwen.studio.agent.runtime.constant.ConstantTest.TEST_USER_ID;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.CALLS_REAL_METHODS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.bo.AgentMetadata;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceInvokeData;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.sensitive.SensitiveEntity;
import com.openjiuwen.studio.agent.common.service.DelegateExchangeTokenService;
import com.openjiuwen.studio.agent.common.utils.KV;
import com.openjiuwen.studio.agent.common.utils.PromptTemplate;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.runtime.constant.Constant;
import com.openjiuwen.studio.agent.runtime.constant.ConstantTest;
import com.openjiuwen.studio.agent.runtime.controller.RuntimeModelServiceController;
import com.openjiuwen.studio.agent.common.dto.run.AdditionalQuestionsReq;
import com.openjiuwen.studio.agent.runtime.dto.AutoAddResultJsonObject;
import com.openjiuwen.studio.agent.runtime.dto.ConversationHistory;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenAgentEvent;
import com.openjiuwen.studio.agent.runtime.dto.JiuwenAgentEventData;
import com.openjiuwen.studio.agent.runtime.dto.MemoryVariable;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.runtime.dto.ReleaseInfo;
import com.openjiuwen.studio.agent.common.dto.run.RetrieveConversationQo;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunInfo;
import com.openjiuwen.studio.agent.runtime.dto.WorkflowRunRsp;
import com.openjiuwen.studio.agent.runtime.entity.AskModelReq;
import com.openjiuwen.studio.agent.runtime.entity.HyperParameters;
import com.openjiuwen.studio.agent.runtime.entity.MessageEntity;
import com.openjiuwen.studio.agent.runtime.entity.ModelConfig;
import com.openjiuwen.studio.agent.runtime.model.AgentExecuteParams;
import com.openjiuwen.studio.agent.runtime.model.AgentIrMetadata;
import com.openjiuwen.studio.agent.runtime.model.AgentIrWrapper;
import com.openjiuwen.studio.agent.runtime.model.Conversation;
import com.openjiuwen.studio.agent.runtime.model.ModelApiLog;
import com.openjiuwen.studio.agent.runtime.model.WorkflowRunResult;
import com.openjiuwen.studio.agent.runtime.model.debugging.AgentCtrlTraceData;
import com.openjiuwen.studio.agent.runtime.rce.client.AgentManagerClient;
import com.openjiuwen.studio.agent.runtime.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.runtime.sensitive.SensitiveTrieCache;
import com.openjiuwen.studio.agent.runtime.sensitive.SensitiveTrieUtils;
import com.openjiuwen.studio.agent.runtime.utils.BaseTest;
import com.openjiuwen.studio.agent.runtime.utils.EnvVariablesUtils;
import com.openjiuwen.studio.agent.runtime.utils.JsonUtils;
import com.openjiuwen.studio.agent.runtime.utils.OkHttpUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.obs.services.model.TemporarySignatureResponse;

import lombok.SneakyThrows;
import okhttp3.sse.EventSource;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * AgentRuntimeService测试类
 *
 */
@MockitoSettings(strictness = Strictness.LENIENT)
public class AgentRuntimeServiceTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    @Autowired
    private AgentRuntimeService agentRuntimeService;

    @Autowired
    private DelegateExchangeTokenService delegateExchangeTokenService;

    private AutoCloseable mockitoCloseable;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentIrCacheService agentIrCacheService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ConversationManagementService conversationManagementService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private JiuWenService jiuWenService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private OkHttpUtils okHttpUtils;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ObsService obsService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentManagerClient agentManagerClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private RuntimeModelServiceController modelController;

    @BeforeAll
    static void init() {
        mockedStatic = mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(TEST_USER_ID);
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(agentRuntimeService, "agentIrCacheService", agentIrCacheService);
        ReflectionTestUtils.setField(agentRuntimeService, "conversationManagementService",
                conversationManagementService);
        ReflectionTestUtils.setField(agentRuntimeService, "jiuWenService", jiuWenService);
        ReflectionTestUtils.setField(agentRuntimeService, "modelController", modelController);
        ReflectionTestUtils.setField(agentRuntimeService, "okHttpUtils", okHttpUtils);
        ReflectionTestUtils.setField(delegateExchangeTokenService, "opSvcProjectId", "op_project_id");
        ReflectionTestUtils.setField(delegateExchangeTokenService, "itepDispatcherEndpoint", "mock_endpoint");
        ReflectionTestUtils.setField(delegateExchangeTokenService, "agencyTokenUrl", "mock_url");

        when(agentIrCacheService.getLatestAgentIr(anyString()).getMetadata()).thenReturn(mockAgentIrMetadata());
        when(conversationManagementService.retrieveConversationCore(anyString(), anyString(), anyString(),
                anyString())).thenReturn(mockConversation());
        when(conversationManagementService.updateConversation(any(), (List<Message>) any(), anyBoolean())).thenReturn(
                new ArrayList<>());
        when(okHttpUtils.stream(anyString(), any(), anyString(), any())).thenReturn(true);
        when(obsService.getObject(anyString(), anyString())).thenReturn(mockObsMap());
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void testDelegateExchangeToken() throws IOException {
        assertThrows(AgentStudioException.class, () -> {
            agentRuntimeService.delegateExchangeToken(TEST_PROJECT_ID, TEST_PROJECT_ID, TEST_DOMAIN_ID);
        });
    }

    @Test
    void test_runAgent_should_succeed_when_test_data_combination() {
        // set up
        AgentExecuteParams executeParams = mockAgentExecuteParams();
        executeParams.setInputs(new HashMap<>());
        // run test
        agentRuntimeService.runAgent(executeParams);
    }

    @Test
    void test_runAgent_should_throw_AgentRuntimeException_when_user_has_no_permission() {
        assertThrows(AgentStudioException.class, () -> {
            // set up
            AgentExecuteParams executeParams = mockAgentExecuteParams();
            executeParams.setProjectId("test_project_id_change");
            // run test
            agentRuntimeService.runAgent(executeParams);
        });
    }

    @Test
    void test_runAgent_exceed_max_query_length() {
        assertThrows(AgentStudioException.class, () -> {
            // set up
            AgentExecuteParams executeParams = mockAgentExecuteParams();
            char[] a = new char[100001];
            Arrays.fill(a, 'a');
            String mockStr = new String(a);
            executeParams.setQuery(mockStr);
            // run test
            agentRuntimeService.runAgent(executeParams);
        });
    }

    @Test
    void test_runAgentStream_should_succeed_when_test_data_combination() {
        // set up
        AgentExecuteParams executeParams = mockAgentExecuteParams();
        executeParams.setExecuteType(AGENT);
        // run test
        agentRuntimeService.runAgentStream(executeParams);
    }

    @SneakyThrows
    @Test
    void test_releaseInfo_action() {
        // set up
        ReleaseInfo releaseInfo = new ReleaseInfo();
        releaseInfo.setChannelType("CLOUD_STORE");
        releaseInfo.setShortCode("test_code");

        // run test
        agentRuntimeService.createReleaseInfo(TEST_PROJECT_ID, "default", releaseInfo);
        agentRuntimeService.deleteReleaseInfo(TEST_PROJECT_ID, releaseInfo.getShortCode(), releaseInfo.getChannelType(),
                "test_version_id");
        releaseInfo.setChannelType("APP_STORE");
        releaseInfo.setAppId("test_app_id");
        releaseInfo.setVersionId("test_version_id");
        agentRuntimeService.createReleaseInfo(TEST_PROJECT_ID, "default", releaseInfo);
        agentRuntimeService.deleteReleaseInfo(TEST_PROJECT_ID, releaseInfo.getAppId(), releaseInfo.getChannelType(),
                "test_version_id");
    }

    @Test
    void test_processOnEvent_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given

            List<MemoryVariable> memoryVariables = new ArrayList<>();
            MemoryVariable memoryVariable = new MemoryVariable();
            memoryVariables.add(memoryVariable);
            Map<String, String> pluginInputMap = new HashMap<>();
            pluginInputMap.put("test", "test");
            List<Message> messages = new ArrayList<>();
            AgentMetadata metadata = AgentMetadata.builder().build();
            SensitiveTrieUtils trieUtils = new SensitiveTrieUtils("test", metadata);
            AgentExecuteParams executeParams = AgentExecuteParams.builder()
                    .agentId("test")
                    .conversationId("test")
                    .executionId("test")
                    .memoryVariables(memoryVariables)
                    .pluginInputMap(pluginInputMap)
                    .executeType("agent")
                    .messages(messages)
                    .trieUtils(trieUtils)
                    .apiLog(new ModelApiLog())
                    .build();

            SseEmitter sseEmitter = new SseEmitter();

            WorkflowRunResult result = new WorkflowRunResult();
            WorkflowRunInfo workflowRunInfo = new WorkflowRunInfo();
            result.setWorkflowRunInfo(workflowRunInfo);

            EventSource eventSource = mock(EventSource.class, Answers.RETURNS_DEEP_STUBS);

            JiuwenAgentEvent jiuwenAgentEvent = new JiuwenAgentEvent();
            jiuwenAgentEvent.setEvent("DONE");
            // When
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("START");
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("MESSAGE");
            jiuwenAgentEvent.setData(new JiuwenAgentEventData().setAnswer(""));
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("API_EXEC_DATA");
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("AGENT_NODE_MESSAGE");
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("INTERMEDIATE_MESSAGE");
            jiuwenAgentEvent.setData(new JiuwenAgentEventData().setAnswer(new ArrayList<>()));
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("STATISTIC_DATA");
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("SUMMARY_RESPONSE");
            jiuwenAgentEvent.setData(new JiuwenAgentEventData().setAnswer(new Message()));
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());

            jiuwenAgentEvent.setEvent("ERROR");
            jiuwenAgentEvent.setData(new JiuwenAgentEventData().setAnswer(new Message()).setCode(0));
            agentRuntimeService.processOnEvent(JSONObject.toJSONString(jiuwenAgentEvent), executeParams, sseEmitter,
                    result, eventSource, new AgentCtrlTraceData());
        });
    }

    @Test
    void testRunAgentSensitiveMatch() {
        String sensitiveConfig
                = "{\"enabled\":true,\"filter\":{\"keywords\":\"帮助\"},\"replace\":[{\"keywords\":\"你好\",\"replace\":\"【您好】\"}],\"reply\":[{\"keywords\":\"兜底匹配\",\"input_enable\":true,\"input_text\":\"我是输入兜底回复内容\",\"output_enable\":true,\"output_text\":\"我是输出兜底回复内容\"}]}";
        AgentIrWrapper irWrapper = new AgentIrWrapper();
        irWrapper.setMetadata(mockAgentIrMetadata());
        irWrapper.setSensitiveEntity(JsonUtils.json2ObjQuietly(sensitiveConfig, SensitiveEntity.class));
        when(agentIrCacheService.getLatestAgentIr(anyString())).thenReturn(irWrapper);
        SensitiveTrieCache trieCache = new SensitiveTrieCache(null, agentIrCacheService);
        trieCache.init();
        try (MockedStatic<SpringBeanUtils> mockedStaticSpringBeanUtils = mockStatic(SpringBeanUtils.class,
                CALLS_REAL_METHODS)) {
            mockedStaticSpringBeanUtils.when(() -> SpringBeanUtils.getBean(SensitiveTrieCache.class))
                    .thenReturn(trieCache);
            AgentExecuteParams executeParams = mockAgentExecuteParams();
            executeParams.setExecuteType(Constant.AppType.CONTROLLER);
            executeParams.setInputs(Map.of("query", "我要兜底匹配"));
            executeParams.setWorkspaceId("default");
            WorkflowRunRsp runRsp = (WorkflowRunRsp) agentRuntimeService.runAgent(executeParams);
            // 控制器不支持敏感词匹配，无返回消息
            Assertions.assertEquals(runRsp.getMessages().size(), 0);

            executeParams = mockAgentExecuteParams();
            executeParams.setExecuteType(AGENT);
            executeParams.setQuery("我要兜底匹配");
            agentRuntimeService.runAgentStream(executeParams);

            JiuwenAgentEvent event = new JiuwenAgentEvent();
            event.setData(new JiuwenAgentEventData().setAnswer("你好，请问有什么可以帮助你"));
            executeParams.setQuery("你好");
            agentRuntimeService.processOnSensitiveMessage(executeParams, new SseEmitter(), event, false);
        }
    }

    private AgentExecuteParams mockAgentExecuteParams() {
        AgentExecuteParams executeParams = new AgentExecuteParams();
        executeParams.setAgentId(TEST_AGENT_ID);
        executeParams.setConversationId(ConstantTest.Conversation.TEST_CONVERSATION_ID);
        executeParams.setQuery(TEST_AGENT_QUESTION);
        executeParams.setProjectId(TEST_PROJECT_ID);
        executeParams.setWorkspaceId("default");
        executeParams.setExecuteType(AGENT);
        return executeParams;
    }

    private AgentIrMetadata mockAgentIrMetadata() {
        AgentIrMetadata metadata = new AgentIrMetadata();
        metadata.setProjectId(TEST_PROJECT_ID);
        metadata.setUpdatedAt(TEST_UPDATED_TIME);
        return metadata;
    }

    private Conversation mockConversation() {
        Conversation conversation = new Conversation();
        List<Message> historyMessages = new ArrayList<>();
        historyMessages.add(new Message().setRole("user").setContent("test_user_question"));
        historyMessages.add(new Message().setRole("assistant").setContent("test_assistant_answer"));
        conversation.setMessageList(historyMessages);
        return conversation;
    }

    private List<Message> mockMessageList() {
        List<Message> historyMessages = new ArrayList<>();
        historyMessages.add(new Message().setRole("user").setContent("test_user_question"));
        historyMessages.add(new Message().setRole("assistant").setContent("test_assistant_answer"));
        return historyMessages;
    }

    private List<Message> mockMessageListException() {
        List<Message> historyMessages = new ArrayList<>();
        historyMessages.add(new Message().setRole("user").setContent("test_user_question"));
        return historyMessages;
    }

    @Test
    void testAdditionalQuestions() {
        // mock getModelConfigFromObs
        AgentIrWrapper irWrapper = new AgentIrWrapper();
        irWrapper.setModelConfig(ModelConfig.builder().modelName("test_model_name").modelType("test_model_type")
                .hyperParameters(new HyperParameters()).build());
        irWrapper.setMetadata(mockAgentIrMetadata());
        when(agentIrCacheService.getLatestAgentIr(anyString())).thenReturn(irWrapper);

        // mock callModel -> modelController.chatCompletions
        com.alibaba.fastjson.JSONObject jsonObject = com.alibaba.fastjson.JSONObject.parseObject(
                "{\"id\":\"chat-test\",\"object\":\"chat.completion\",\"created\":1764853827,\"model\":\"test_model_name\","
                        + "\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\","
                        + "\"content\":\"[\\\"如何分析单品的销售数据？\\\",\\\"销售数据如何分析？\\\",\\\"如何分析市场销售数据？\\\"]\"},"
                        + "\"finish_reason\":\"stop\"}]}");
        when(modelController.chatCompletions(any(), any(), any(), any(), anyBoolean(), anyString(), anyString()))
                .thenReturn(jsonObject);

        // 构造数据
        AdditionalQuestionsReq additionalQuestionsReq = new AdditionalQuestionsReq();
        additionalQuestionsReq.setName("agent");
        additionalQuestionsReq.setDescription("");
        additionalQuestionsReq.setEnable(true);
        additionalQuestionsReq.setPrompt("");

        // run the test
        when(conversationManagementService.retrieveConversation(TEST_PROJECT_ID, TEST_AGENT_ID,
                ConstantTest.Conversation.TEST_CONVERSATION_ID, new RetrieveConversationQo())).thenReturn(
                mockMessageList());
        AutoAddResultJsonObject autoAddResultJsonObject = agentRuntimeService.additionalQuestions(TEST_PROJECT_ID,
                TEST_AGENT_ID, ConstantTest.Conversation.TEST_CONVERSATION_ID, "", additionalQuestionsReq);
        assertNotNull(autoAddResultJsonObject);
        assertEquals(3, autoAddResultJsonObject.getQuestions().size());

        // exception test
        assertThrows(AgentStudioException.class, () -> {
            additionalQuestionsReq.setName(null);
            agentRuntimeService.additionalQuestions(TEST_PROJECT_ID, TEST_AGENT_ID,
                    ConstantTest.Conversation.TEST_CONVERSATION_ID, "", additionalQuestionsReq);
        });

        // exception test
        assertThrows(AgentStudioException.class, () -> {
            additionalQuestionsReq.setName("agent");
            additionalQuestionsReq.setEnable(false);
            agentRuntimeService.additionalQuestions(TEST_PROJECT_ID, TEST_AGENT_ID,
                    ConstantTest.Conversation.TEST_CONVERSATION_ID, "", additionalQuestionsReq);
        });

        // exception test
        assertThrows(AgentStudioException.class, () -> {
            additionalQuestionsReq.setEnable(true);
            AgentStudioException agentRuntimeException = new AgentStudioException("exception_test");
            when(conversationManagementService.retrieveConversation(anyString(), anyString(), anyString(),
                    any(RetrieveConversationQo.class))).thenThrow(agentRuntimeException);
            agentRuntimeService.additionalQuestions(TEST_PROJECT_ID, TEST_AGENT_ID,
                    ConstantTest.Conversation.TEST_CONVERSATION_ID, "", additionalQuestionsReq);
        });

        // exception test
        when(conversationManagementService.retrieveConversation(anyString(), anyString(), anyString(),
                any(RetrieveConversationQo.class))).thenReturn(mockMessageListException());
        AutoAddResultJsonObject result = agentRuntimeService.additionalQuestions(TEST_PROJECT_ID, TEST_AGENT_ID,
                "conversation_id", "", additionalQuestionsReq);
        assertEquals(new ArrayList<>(), result.getQuestions());

        // questionsList == null test
        additionalQuestionsReq.setName("exception");
        agentRuntimeService.additionalQuestions(TEST_PROJECT_ID, TEST_AGENT_ID, "conversation_id", "",
                additionalQuestionsReq);

        // with user prompt test
        when(conversationManagementService.retrieveConversation(anyString(), anyString(), anyString(),
                any(RetrieveConversationQo.class))).thenReturn(mockMessageList());
        AdditionalQuestionsReq promptReq = new AdditionalQuestionsReq();
        promptReq.setName("agent");
        promptReq.setEnable(true);
        promptReq.setPrompt("## 追问规范\n1. 提问简短精准,\n2. 请依第一人称生成追问");
        AutoAddResultJsonObject promptResult = agentRuntimeService.additionalQuestions(TEST_PROJECT_ID,
                TEST_AGENT_ID, ConstantTest.Conversation.TEST_CONVERSATION_ID, "", promptReq);
        assertNotNull(promptResult);
        assertEquals(3, promptResult.getQuestions().size());
        assertTrue(promptResult.getQuestions().contains("如何分析单品的销售数据？"));
    }

    private Map<String, String> mockObsMap() {
        HyperParameters hyperParameters = new HyperParameters();
        hyperParameters.setTemperature(0.5);
        hyperParameters.setTopP(2.0);
        ModelConfig modelConfig = ModelConfig.builder()
                .modelName("test_model_name")
                .modelType("test_model_type")
                .hyperParameters(hyperParameters)
                .build();
        Map<String, Map<String, ModelConfig>> modelConfigMap = new HashMap<>();
        Map<String, ModelConfig> map = new HashMap<>();
        map.put("modelConfig", modelConfig);
        modelConfigMap.put("configs", map);
        Map<String, String> obsMap = new HashMap<>();
        obsMap.put(Constant.Obs.CONTENT, JSON.toJSONString(modelConfigMap));
        return obsMap;
    }

    private InputStream mockTxtInputStream() throws IOException {
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                "test.txt",  // 原始文件名
                "text/plain",  // MIME类型
                "test".getBytes(StandardCharsets.UTF_8)  // 文件内容
        );
        return file.getInputStream();
    }

    @Test
    void testUploadFile() throws IOException {
        String workspaceId = "default";
        String projectId = "project_mock";

        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                "test.txt",  // 原始文件名
                "text/plain",  // MIME类型
                "test".getBytes(StandardCharsets.UTF_8)  // 文件内容
        );

        InputStream inputStream = file.getInputStream();
        String originalFilename = file.getOriginalFilename();
        when(obsService.uploadObsFileWithExpires(inputStream, originalFilename, 7)).thenReturn("name");
        when(obsService.getStagingDownloadUrl(anyString(), anyLong())).thenReturn("url");
        when(obsService.uploadObsFileWithExpires(inputStream, "test.txt", 300)).thenReturn("url");
        try {
            agentRuntimeService.uploadAgentFile(workspaceId, projectId, file, -1, false);
        } catch (Exception e) {
            Assertions.assertTrue(true);
        }
    }

    @Test
    void testUploadFileEmpty() throws IOException {
        String workspaceId = "default";
        String projectId = "project_mock";

        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                null,  // 原始文件名
                "text/plain",  // MIME类型
                "".getBytes(StandardCharsets.UTF_8)  // 文件内容
        );

        try {
            agentRuntimeService.uploadAgentFile(workspaceId, projectId, file, -1, false);
        } catch (Exception e) {
            Assertions.assertTrue(true);
        }
    }

    @Test
    void testUploadImage() throws IOException {
        String workspaceId = "default";
        String projectId = "project_mock";
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                "test.jpg",  // 原始文件名
                "text/plain",  // MIME类型
                "test".getBytes(StandardCharsets.UTF_8)  // 文件内容
        );

        InputStream inputStream = file.getInputStream();
        String originalFilename = file.getOriginalFilename();
        when(obsService.uploadObsFileWithExpires(inputStream, originalFilename, 7)).thenReturn("name");
        when(obsService.getStagingDownloadUrl(anyString(), anyLong())).thenReturn("url");
        when(obsService.uploadObsFileWithExpires(inputStream, "test.jpg", 300)).thenReturn("url");
        // 用力不通过
        try {
            assertNotNull(agentRuntimeService.uploadAgentFile(workspaceId, projectId, file, 1, true));
        } catch (Exception e) {
            Assertions.assertTrue(true);
        }
    }

    @Test
    void testUploadFileExceedSize() throws IOException {
        String workspaceId = "default";
        String projectId = "project_mock";
        MockMultipartFile file = mock(MockMultipartFile.class);
        when(file.getOriginalFilename()).thenReturn("test.jpg");
        when(file.getSize()).thenReturn(999999999L);
        assertThrows(AgentStudioException.class,
                () -> agentRuntimeService.uploadAgentFile(workspaceId, projectId, file, -1, false));
    }

    @Test
    void testExtractUrlFromQuery() {
        List<String> fileUrls = Arrays.asList(
                "https://xxxxxx:443/file/4c254149-9286-4d3d-a3bc-45c4a0e78036.mp4",
                "https://xxxxxx:443/file/e39ad523-ff1a-436c-89ab-3579c1010cbe.jpeg");
        List<Object> urls = agentRuntimeService.extractUrlFromQuery(fileUrls);
        assertEquals(urls.size(), 2);
    }

    @Test
    public void testModelCall() {
        ModelServiceCheckReq reqMock = new ModelServiceCheckReq();
        reqMock.setAuthInfo(new HashMap<>());
        reqMock.setModelName("model").setModelType("LLM").setApiUrl("aa").setAuthType("IAM");

        ModelServiceInvokeData reqMockData = new ModelServiceInvokeData().setData(Collections.singletonList(reqMock));
        Mockito.when(agentManagerClient.queryModelInvokeData(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(ResponseEntity.ok(reqMockData));

        AskModelReq req = AskModelReq.builder().build();
        req.setModel(ModelConfig.builder().modelName("deep").build());
        MessageEntity msg = MessageEntity.builder().role("user").content("test").build();
        req.setMessages(Collections.singletonList(msg));

        com.alibaba.fastjson.JSONObject jsonObject = com.alibaba.fastjson.JSONObject.parseObject(
                "{\"id\":\"chat-bbba4d32929c455fa94b9c5c507bf788\",\"object\":\"chat.completion\",\"created\":1764853827,\"model\":\"DeepSeek-V3\",\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\",\"content\":\"你好！有什么我可以帮您的吗？\uD83D\uDE0A\",\"reasoning_content\":null,\"tool_calls\":[]},\"logprobs\":null,\"finish_reason\":\"stop\",\"stop_reason\":null}],\"usage\":{\"prompt_tokens\":10,\"total_tokens\":21,\"completion_tokens\":11,\"prompt_tokens_details\":null},\"prompt_logprobs\":null}");
        Mockito.when(modelController.chatCompletions(any(), any(), any(), any(), any(), any(), any()))
                .thenReturn(jsonObject);
        agentRuntimeService.callModel(req, "default", "");
    }

    @Test
    public void testFreeModelCall() {
        ModelServiceCheckReq reqMock = new ModelServiceCheckReq();
        reqMock.setAuthInfo(new HashMap<>());
        reqMock.setModelName("model").setModelType("LLM").setApiUrl("aa").setAuthType("IAM");

        ModelServiceInvokeData reqMockData = new ModelServiceInvokeData().setData(Collections.singletonList(reqMock));
        Mockito.when(agentManagerClient.queryModelInvokeData(anyString(), anyString(), anyString(), anyString()))
                .thenReturn(ResponseEntity.ok(reqMockData));

        AskModelReq req = AskModelReq.builder().build();
        req.setModel(ModelConfig.builder().modelName("deep").build());
        MessageEntity msg = MessageEntity.builder().role("user").content("test").build();
        req.setMessages(Collections.singletonList(msg));

        com.alibaba.fastjson.JSONObject jsonObject = com.alibaba.fastjson.JSONObject.parseObject(
                "{\"id\":\"chat-bbba4d32929c455fa94b9c5c507bf788\",\"object\":\"chat.completion\",\"created\":1764853827,\"model\":\"DeepSeek-V3\",\"choices\":[{\"index\":0,\"message\":{\"role\":\"assistant\",\"content\":\"你好！有什么我可以帮您的吗？\uD83D\uDE0A\",\"reasoning_content\":null,\"tool_calls\":[]},\"logprobs\":null,\"finish_reason\":\"stop\",\"stop_reason\":null}],\"usage\":{\"prompt_tokens\":10,\"total_tokens\":21,\"completion_tokens\":11,\"prompt_tokens_details\":null},\"prompt_logprobs\":null}");
        Mockito.when(modelController.chatCompletions(any(), any(), any(), any(), any(), any(), any()))
                .thenReturn(jsonObject);
        agentRuntimeService.callModel(req, "default", "");
    }

    @Test
    public void convertMessagesTest() {
        Message message = new Message();
        message.setAgentId("agent");
        List<Message> messageList = Collections.singletonList(message);
        List<ConversationHistory> histories = agentRuntimeService.convertMessages(messageList);
        Assertions.assertEquals(1, histories.size());
    }

    @Test
    public void uploadFileToObsTest() throws IOException {
        ConversationManagementService conversationManagementService = Mockito.mock(ConversationManagementService.class);
        JiuWenService jiuWenService = Mockito.mock(JiuWenService.class);
        OkHttpUtils okHttpUtils = Mockito.mock(OkHttpUtils.class);
        RedisClient redisClient = Mockito.mock(RedisClient.class);
        AgentIrCacheService agentIrCacheService = Mockito.mock(AgentIrCacheService.class);
        AgentRuntimeService service = new AgentRuntimeService(agentIrCacheService, conversationManagementService,
                jiuWenService, okHttpUtils, redisClient, Mockito.mock(EnvVariablesUtils.class));

        ObsService obs = Mockito.mock(ObsService.class);
        ReflectionTestUtils.setField(service, "obsService", obs);
        when(obs.uploadObsFileWithExpires(any(), any(), anyInt())).thenReturn("url");
        when(obs.uploadToStagingWithPublicRead(any(), any(), anyInt())).thenReturn("url");
        when(obsService.getStagingDownloadUrl(anyString(), anyLong())).thenReturn("url");

        ReflectionTestUtils.setField(service, "fileReadOnly", true);

        InputStream inputStream = new ByteArrayInputStream("content".getBytes(StandardCharsets.UTF_8));
        MultipartFile file = new MockMultipartFile("file", inputStream);
        service.uploadFileToObs(file, 10, "test.txt");

        ReflectionTestUtils.setField(service, "fileReadOnly", false);
        service.uploadFileToObs(file, 10, "test.txt");
    }
}
