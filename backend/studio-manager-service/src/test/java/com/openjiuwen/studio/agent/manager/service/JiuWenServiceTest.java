/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.Answers.RETURNS_DEEP_STUBS;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.urlPathTemplate;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.options;

import com.github.tomakehurst.wiremock.WireMockServer;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.common.dto.md.ChatCompletionRequest;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.rce.models.AskModelReq;
import com.openjiuwen.studio.agent.manager.rce.models.CodeGenerateResultVo;
import com.openjiuwen.studio.agent.manager.rce.service.JiuWenService;
import com.openjiuwen.studio.agent.manager.service.md.FreeModelService;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;

import reactor.core.publisher.Flux;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class JiuWenServiceTest {

    @Mock(answer = RETURNS_DEEP_STUBS)
    private WebClient webClient;

    @Mock(answer = RETURNS_DEEP_STUBS)
    private AgentRuntimeClient runtimeClient;

    @Mock(answer = RETURNS_DEEP_STUBS)
    private ProviderAuthDataMapper authDataMapper;

    @Mock(answer = RETURNS_DEEP_STUBS)
    private FreeModelService freeModelService;

    @InjectMocks
    private JiuWenService jiuWenService;

    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(jiuWenService, "runtimeEndpoint", "not_empty");
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_callModelStream_success() {
        HttpHeaders headers = mock(HttpHeaders.class);
        when(headers.get(eq(CommonConstant.X_AUTH_TOKEN))).thenReturn(Collections.singletonList("token"));
        String projectId = "proj1";
        String workspaceId = "ws1";
        ChatCompletionRequest chatCompletionRequest = new ChatCompletionRequest();

        try (MockedStatic<JsonUtils> jsonUtilsMock = mockStatic(JsonUtils.class)) {
            CodeGenerateResultVo responseVo = new CodeGenerateResultVo();
            CodeGenerateResultVo.Delta delta = new CodeGenerateResultVo.Delta("assistant", "test_content");
            CodeGenerateResultVo.Choice choice = new CodeGenerateResultVo.Choice();
            choice.setDelta(delta);
            choice.setIndex(0);
            responseVo.setChoices(Collections.singletonList(choice));
            jsonUtilsMock.when(() -> JsonUtils.json2ObjQuietly(anyString(), eq(CodeGenerateResultVo.class)))
                .thenReturn(responseVo);

            Flux<String> dataFlux = Flux.just("{\"choices\": [{\"delta\": {\"content\": \"code\"}}]}");
            when(webClient.post()
                .uri(anyString())
                .contentType(eq(MediaType.APPLICATION_JSON))
                .header(eq(CommonConstant.X_AUTH_TOKEN), eq("token"))
                .bodyValue(eq(chatCompletionRequest))
                .retrieve()
                .onStatus(any(), any())
                .bodyToFlux(eq(String.class))).thenReturn(dataFlux);

            Object result = jiuWenService.callModelStream(headers, projectId, workspaceId, chatCompletionRequest);
            assertNotNull(result);
        }
    }

    @Test
    public void callModelTest() {
        AskModelReq req = AskModelReq.builder().build();

        try {
            jiuWenService.callModel(req, "workspaceId");
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MODEL_CONFIG_MISS, e.getErrorCode());
        }

        req.setModelName("model|model");
        Mockito.when(freeModelService.isFreeModel(Mockito.any())).thenReturn(false);
        Mockito.when(authDataMapper.selectByModelId(Mockito.any(), Mockito.any(), Mockito.any())).thenReturn(null);

        MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic = Mockito.mockStatic(RequestHeaderHolderUtils.class);
        RequestContextUtils.setRequestAuthTokenAndProjectId("token", "test");

        try {
            jiuWenService.callModel(req, "workspaceId");
        } catch (Exception e) {
            Assertions.assertTrue(true);
        }
        mockedHeaderStatic.close();
    }

    // ---- generatorAgentOrWorkflow 全场景 mock 覆盖（结合 agent-builder 实际返回形态）----

    private static WireMockServer builderMock;

    private static final String PID = "p1";
    private static final String AGENT_TYPE = "agents";
    private static final String CID = "c1";
    private static final String WS = "ws1";

    @BeforeAll
    static void startBuilderMock() {
        builderMock = new WireMockServer(options().dynamicPort());
        builderMock.start();
    }

    @AfterAll
    static void stopBuilderMock() {
        if (builderMock != null) {
            builderMock.stop();
        }
    }

    private void useRealBuilderClient() {
        ReflectionTestUtils.setField(jiuWenService, "agentBuilderEndpoint",
            "http://localhost:" + builderMock.port());
        ReflectionTestUtils.setField(jiuWenService, "webClient", WebClient.create());
    }

    /**
     * 用例描述：上游 200 + SSE 数据流（builder _chat 正常返回 StreamingResponse）
     * 预制条件：WireMock stub 返回 200 text/event-stream，两行 data 事件
     * 输入参数：generatorAgentOrWorkflow("token", p1, agents, c1, ws1, body)
     * 预期结果：onStatus 不触发，Flux 解析出全部 2 个数据 chunk
     */
    @Test
    void testGeneratorAgentOrWorkflow_SseDataChunks() {
        builderMock.resetAll();
        builderMock.stubFor(post(urlPathTemplate("/v1/{pid}/{agentType}/generator/conversations/{cid}/chat"))
            .willReturn(aResponse().withStatus(200)
                .withHeader("Content-Type", "text/event-stream")
                .withBody("data: {\"event\":\"START\",\"data\":\"\"}\n\n"
                    + "data: {\"event\":\"message\",\"data\":\"hi\"}\n\n")));
        useRealBuilderClient();

        Flux<Map<String, Object>> flux = jiuWenService.generatorAgentOrWorkflow("token", PID, AGENT_TYPE, CID, WS,
            new HashMap<>());
        List<Map<String, Object>> chunks = flux.collectList().block();

        Assertions.assertNotNull(chunks);
        Assertions.assertEquals(2, chunks.size());
        Assertions.assertEquals("message", chunks.get(1).get("event"));
    }

    /**
     * 用例描述：上游 200 + SSE 内嵌 error 事件（builder _chat 参数校验/业务异常包 200 SSE error）
     * 预制条件：WireMock stub 返回 200 text/event-stream，一行 error 事件
     * 输入参数：generatorAgentOrWorkflow("token", p1, agents, c1, ws1, body)
     * 预期结果：onStatus 不触发（200），error 事件作为数据 chunk 透传，保持可辨
     */
    @Test
    void testGeneratorAgentOrWorkflow_SseErrorEventPassthrough() {
        builderMock.resetAll();
        builderMock.stubFor(post(urlPathTemplate("/v1/{pid}/{agentType}/generator/conversations/{cid}/chat"))
            .willReturn(aResponse().withStatus(200)
                .withHeader("Content-Type", "text/event-stream")
                .withBody("data: {\"event\":\"error\",\"data\":{\"code\":\"404\",\"message\":\"conversation not found\"}}\n\n")));
        useRealBuilderClient();

        Flux<Map<String, Object>> flux = jiuWenService.generatorAgentOrWorkflow("token", PID, AGENT_TYPE, CID, WS,
            new HashMap<>());
        List<Map<String, Object>> chunks = flux.collectList().block();

        Assertions.assertNotNull(chunks);
        Assertions.assertEquals(1, chunks.size());
        Assertions.assertEquals("error", chunks.get(0).get("event"));
    }

    /**
     * 用例描述：上游 404（FastAPI 路由/资源不存在）
     * 预制条件：WireMock stub 返回 404 {"detail":"Not Found"}
     * 输入参数：generatorAgentOrWorkflow("token", p1, agents, c1, ws1, body)
     * 预期结果：映射为 RESOURCE_NOT_EXISTS（404/02201083），资源不存在可辨
     */
    @Test
    void testGeneratorAgentOrWorkflow_404_MapsToResourceNotExists() {
        builderMock.resetAll();
        builderMock.stubFor(post(urlPathTemplate("/v1/{pid}/{agentType}/generator/conversations/{cid}/chat"))
            .willReturn(aResponse().withStatus(404)
                .withHeader("Content-Type", "application/json")
                .withBody("{\"detail\":\"Not Found\"}")));
        useRealBuilderClient();

        Flux<Map<String, Object>> flux = jiuWenService.generatorAgentOrWorkflow("token", PID, AGENT_TYPE, CID, WS,
            new HashMap<>());
        AgentStudioException ex = Assertions.assertThrows(AgentStudioException.class,
            () -> flux.collectList().block());
        Assertions.assertEquals(StudioError.RESOURCE_NOT_EXISTS, ex.getErrorCode());
    }

    /**
     * 用例描述：上游 400（builder Pydantic 校验失败或 _safe_reject cid 校验失败）
     * 预制条件：WireMock stub 返回 400
     * 输入参数：generatorAgentOrWorkflow("token", p1, agents, c1, ws1, body)
     * 预期结果：映射为 METHOD_ARGUMENT_NOT_VALID（400/02001003），4xx 不压成 500
     */
    @Test
    void testGeneratorAgentOrWorkflow_400_MapsToBadRequest() {
        builderMock.resetAll();
        builderMock.stubFor(post(urlPathTemplate("/v1/{pid}/{agentType}/generator/conversations/{cid}/chat"))
            .willReturn(aResponse().withStatus(400)
                .withHeader("Content-Type", "application/json")
                .withBody("{\"detail\":\"Bad Request\"}")));
        useRealBuilderClient();

        Flux<Map<String, Object>> flux = jiuWenService.generatorAgentOrWorkflow("token", PID, AGENT_TYPE, CID, WS,
            new HashMap<>());
        AgentStudioException ex = Assertions.assertThrows(AgentStudioException.class,
            () -> flux.collectList().block());
        Assertions.assertEquals(StudioError.METHOD_ARGUMENT_NOT_VALID, ex.getErrorCode());
    }

    /**
     * 用例描述：上游 500 JiuWenException（builder 业务异常形态 {"error":{"code":<上游码>,...}}）
     * 预制条件：WireMock stub 返回 500 携带 error 对象
     * 输入参数：generatorAgentOrWorkflow("token", p1, agents, c1, ws1, body)
     * 预期结果：保持 500 JIU_WEN_SERVICE_EXCEPTION
     */
    @Test
    void testGeneratorAgentOrWorkflow_500JiuWenException_MapsToServiceException() {
        builderMock.resetAll();
        builderMock.stubFor(post(urlPathTemplate("/v1/{pid}/{agentType}/generator/conversations/{cid}/chat"))
            .willReturn(aResponse().withStatus(500)
                .withHeader("Content-Type", "application/json")
                .withBody("{\"error\":{\"code\":100000,\"message\":\"conversation not found\",\"trace_id\":\"t1\"}}")));
        useRealBuilderClient();

        Flux<Map<String, Object>> flux = jiuWenService.generatorAgentOrWorkflow("token", PID, AGENT_TYPE, CID, WS,
            new HashMap<>());
        AgentStudioException ex = Assertions.assertThrows(AgentStudioException.class,
            () -> flux.collectList().block());
        Assertions.assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION, ex.getErrorCode());
    }

    /**
     * 用例描述：上游 500 generic（builder 未捕获异常形态 {"error":{"code":"internal_error",...}}）
     * 预制条件：WireMock stub 返回 500 携带 internal_error 对象
     * 输入参数：generatorAgentOrWorkflow("token", p1, agents, c1, ws1, body)
     * 预期结果：保持 500 JIU_WEN_SERVICE_EXCEPTION
     */
    @Test
    void testGeneratorAgentOrWorkflow_500Generic_MapsToServiceException() {
        builderMock.resetAll();
        builderMock.stubFor(post(urlPathTemplate("/v1/{pid}/{agentType}/generator/conversations/{cid}/chat"))
            .willReturn(aResponse().withStatus(500)
                .withHeader("Content-Type", "application/json")
                .withBody("{\"error\":{\"code\":\"internal_error\",\"message\":\"Internal server error\"}}")));
        useRealBuilderClient();

        Flux<Map<String, Object>> flux = jiuWenService.generatorAgentOrWorkflow("token", PID, AGENT_TYPE, CID, WS,
            new HashMap<>());
        AgentStudioException ex = Assertions.assertThrows(AgentStudioException.class,
            () -> flux.collectList().block());
        Assertions.assertEquals(StudioError.JIU_WEN_SERVICE_EXCEPTION, ex.getErrorCode());
    }
}
