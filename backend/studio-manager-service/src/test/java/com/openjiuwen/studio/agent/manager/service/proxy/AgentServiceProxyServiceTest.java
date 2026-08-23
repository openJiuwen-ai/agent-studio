/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentBuilderClient;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;

import com.openjiuwen.studio.agent.manager.service.AgentRuntimeService;
import com.openjiuwen.studio.agent.manager.service.debugging.ControllerDebuggingMgmtService;
import feign.FeignException;
import feign.Request;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AgentServiceProxyServiceTest {

    @Mock
    private AgentRuntimeClient runtimeClient;

    @Mock
    private AgentBuilderClient builderClient;

    @Mock
    private RedisClient redisClient;

    @Mock
    private AgentMapper agentMapper;

    @Mock
    private WorkflowMapper workflowMapper;

    @Mock
    private ModelServiceMapper modelServiceMapper;

    @Mock
    private OkHttpClientUtils okHttpClientUtils;

    @Mock
    private RouterStrategyMapper routerStrategyMapper;

    @Mock
    private FreeModelServiceMapper freeModelServiceMapper;

    @Mock
    private ToolMapper toolMapper;

    @Mock
    private AgentRuntimeService agentRuntimeService;

    @Mock
    private ControllerDebuggingMgmtService controllerDebuggingMgmtService;

    @Mock
    private MgObsService mgObsService;

    private AgentServiceProxyService proxyService;

    @BeforeEach
    void setUp() {
        proxyService = new AgentServiceProxyService(runtimeClient, builderClient, redisClient, agentMapper, workflowMapper,
            modelServiceMapper, okHttpClientUtils, routerStrategyMapper, freeModelServiceMapper, toolMapper, agentRuntimeService, controllerDebuggingMgmtService, mgObsService);
        ReflectionTestUtils.setField(proxyService, "runtimeEndpoint", "http://runtime:8080");
        ReflectionTestUtils.setField(proxyService, "envType", "hc");
        ReflectionTestUtils.setField(proxyService, "opSvcProjectId", "op-svc-project");
    }

    @Test
    void testCheckToolsPermission_ToolNull() {
        assertThrows(AgentStudioException.class,
            () -> proxyService.checkToolsPermission(null, "proj-1", "ws-1"));
    }

    @Test
    void testCheckToolsPermission_SameProjectAndWorkspace() {
        ToolEntity tool = new ToolEntity();
        tool.setProjectId("proj-1");
        tool.setWorkspaceId("ws-1");
        tool.setPublished(1);

        assertDoesNotThrow(() -> proxyService.checkToolsPermission(tool, "proj-1", "ws-1"));
    }

    @Test
    void testCheckToolsPermission_OpSvcProjectPublished() {
        ToolEntity tool = new ToolEntity();
        tool.setProjectId("op-svc-project");
        tool.setWorkspaceId("other-ws");
        tool.setPublished(1);

        assertDoesNotThrow(() -> proxyService.checkToolsPermission(tool, "proj-1", "ws-1"));
    }

    @Test
    void testCheckToolsPermission_OpSvcProjectNotPublished() {
        ToolEntity tool = new ToolEntity();
        tool.setProjectId("op-svc-project");
        tool.setWorkspaceId("other-ws");
        tool.setPublished(0);

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkToolsPermission(tool, "proj-1", "ws-1"));
    }

    @Test
    void testCheckToolsPermission_DifferentProjectNotOpSvc() {
        ToolEntity tool = new ToolEntity();
        tool.setProjectId("other-proj");
        tool.setWorkspaceId("other-ws");
        tool.setPublished(1);

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkToolsPermission(tool, "proj-1", "ws-1"));
    }

    @Test
    void testCheckToolsPermission_NullPublished() {
        ToolEntity tool = new ToolEntity();
        tool.setProjectId("proj-1");
        tool.setWorkspaceId("ws-1");
        tool.setPublished(null);

        assertDoesNotThrow(() -> proxyService.checkToolsPermission(tool, "proj-1", "ws-1"));
        assertEquals(0, tool.getPublished());
    }

    @Test
    void testCheckModelBasePermission_PublicModel() {
        ModelServiceBase model = new ModelServiceBase();
        model.setPublic(true);

        assertDoesNotThrow(() -> proxyService.checkModelBasePermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckModelBasePermission_SystemProject() {
        ModelServiceBase model = new ModelServiceBase();
        model.setPublic(false);
        model.setProjectId("SYSTEM");
        model.setWorkspaceId("ws-1");

        assertDoesNotThrow(() -> proxyService.checkModelBasePermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckModelBasePermission_MatchingProjectAndWorkspace() {
        ModelServiceBase model = new ModelServiceBase();
        model.setPublic(false);
        model.setProjectId("proj-1");
        model.setWorkspaceId("ws-1");

        assertDoesNotThrow(() -> proxyService.checkModelBasePermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckModelBasePermission_DifferentProject() {
        ModelServiceBase model = new ModelServiceBase();
        model.setPublic(false);
        model.setProjectId("other-proj");
        model.setWorkspaceId("ws-1");

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkModelBasePermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckModelBasePermission_DifferentWorkspace() {
        ModelServiceBase model = new ModelServiceBase();
        model.setPublic(false);
        model.setProjectId("proj-1");
        model.setWorkspaceId("other-ws");

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkModelBasePermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckRouterStrategyEntity_SystemProjectAndWorkspace() {
        RouterStrategyEntity router = new RouterStrategyEntity();
        router.setProjectId("SYSTEM");
        router.setWorkspaceId("SYSTEM");

        assertDoesNotThrow(() -> proxyService.checkRouterStrategyEntity(router, "proj-1", "ws-1"));
    }

    @Test
    void testCheckRouterStrategyEntity_MatchingProjectAndWorkspace() {
        RouterStrategyEntity router = new RouterStrategyEntity();
        router.setProjectId("proj-1");
        router.setWorkspaceId("ws-1");

        assertDoesNotThrow(() -> proxyService.checkRouterStrategyEntity(router, "proj-1", "ws-1"));
    }

    @Test
    void testCheckRouterStrategyEntity_DifferentProject() {
        RouterStrategyEntity router = new RouterStrategyEntity();
        router.setProjectId("other-proj");
        router.setWorkspaceId("ws-1");

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkRouterStrategyEntity(router, "proj-1", "ws-1"));
    }

    @Test
    void testCheckFreeModelPermission_MatchingProject() {
        ModelServiceBase model = new ModelServiceBase();
        model.setProjectId("proj-1");
        model.setWorkspaceId("ws-1");

        assertDoesNotThrow(() -> proxyService.checkFreeModelPermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckFreeModelPermission_DifferentProject() {
        ModelServiceBase model = new ModelServiceBase();
        model.setProjectId("other-proj");
        model.setWorkspaceId("ws-1");

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkFreeModelPermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckFreeModelPermission_DifferentWorkspace() {
        ModelServiceBase model = new ModelServiceBase();
        model.setProjectId("proj-1");
        model.setWorkspaceId("other-ws");

        assertThrows(AgentStudioException.class,
            () -> proxyService.checkFreeModelPermission(model, "proj-1", "ws-1"));
    }

    @Test
    void testCheckModelPermission_ModelFound() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            assertDoesNotThrow(() -> proxyService.checkModelPermission("proj-1", "ws-1", "model-1"));
        }
    }

    @Test
    void testCheckModelPermission_FreeModelFound() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(modelServiceMapper.queryById("model-1")).thenReturn(null);
            ModelServiceBase freeModel = new ModelServiceBase();
            freeModel.setProjectId("SYSTEM");
            freeModel.setWorkspaceId("SYSTEM");
            when(freeModelServiceMapper.queryById("model-1")).thenReturn(freeModel);

            assertDoesNotThrow(() -> proxyService.checkModelPermission("proj-1", "ws-1", "model-1"));
        }
    }

    @Test
    void testCheckModelPermission_RouterFound() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(modelServiceMapper.queryById("model-1")).thenReturn(null);
            when(freeModelServiceMapper.queryById("model-1")).thenReturn(null);
            RouterStrategyEntity router = new RouterStrategyEntity();
            router.setProjectId("SYSTEM");
            router.setWorkspaceId("SYSTEM");
            when(routerStrategyMapper.selectInfoById("model-1")).thenReturn(router);

            assertDoesNotThrow(() -> proxyService.checkModelPermission("proj-1", "ws-1", "model-1"));
        }
    }

    @Test
    void testCheckModelPermission_NoneFound() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(modelServiceMapper.queryById("model-1")).thenReturn(null);
            when(freeModelServiceMapper.queryById("model-1")).thenReturn(null);
            when(routerStrategyMapper.selectInfoById("model-1")).thenReturn(null);

            assertThrows(AgentStudioException.class,
                () -> proxyService.checkModelPermission("proj-1", "ws-1", "model-1"));
        }
    }

    @Test
    void testCreateUserFeedback_Success() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ResponseEntity<String> expected = ResponseEntity.ok("ok");
            when(runtimeClient.createUserFeedback("token", "proj-1", "app-1", "conv-1", "msg-1", "agent",
                "v1", null)).thenReturn(expected);

            ResponseEntity<String> result = proxyService.createUserFeedback("proj-1", "app-1", "conv-1",
                "msg-1", "agent", "v1", null);

            assertEquals(expected, result);
        }
    }

    @Test
    void testTextToSpeech_Success() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(runtimeClient.textToSpeech(anyString(), anyString(), anyString(), any()))
                .thenReturn(new com.alibaba.fastjson.JSONObject());

            var result = proxyService.textToSpeech("proj-1", "ws-1", null);

            assertNotNull(result);
        }
    }

    // ==================== 文本向量化调测连通性测试 ====================

    /**
     * 文本向量化调测 — 正常调用：权限校验通过 + Feign 返回结果
     */
    @Test
    void testTextEmbeddings_Success() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            com.alibaba.fastjson.JSONObject expectedResult = new com.alibaba.fastjson.JSONObject();
            expectedResult.put("data", "embedding-result");
            when(builderClient.textEmbeddings(anyString(), anyString(), anyString(),
                any(EmbeddingRequest.class), any())).thenReturn(expectedResult);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            Object result = proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1");

            assertNotNull(result);
            assertEquals(expectedResult, result);
        }
    }

    /**
     * 文本向量化调测 — 权限校验失败：模型不存在，抛出 AgentStudioException
     */
    @Test
    void testTextEmbeddings_PermissionDenied() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(modelServiceMapper.queryById("model-1")).thenReturn(null);
            when(freeModelServiceMapper.queryById("model-1")).thenReturn(null);
            when(routerStrategyMapper.selectInfoById("model-1")).thenReturn(null);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            assertThrows(AgentStudioException.class,
                () -> proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1"));
        }
    }

    /**
     * 文本向量化调测 — Feign 异常且可解析错误体：返回 ErrorRsp
     */
    @Test
    void testTextEmbeddings_FeignException_ParsableError() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            String errorBody = "{\"error_code\":\"openjiuwen.02501049\",\"error_msg\":\"model invoke failed\","
                + "\"error_reason\":\"upstream error\",\"error_suggestion\":\"check model config\","
                + "\"details\":[{\"error_msg\":\"upstream 500\"}]}";
            FeignException feignException = new FeignException.InternalServerError(
                "internal error", mockFeignRequest(), errorBody.getBytes(StandardCharsets.UTF_8),
                Collections.emptyMap());
            when(builderClient.textEmbeddings(anyString(), anyString(), anyString(),
                any(EmbeddingRequest.class), any())).thenThrow(feignException);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            Object result = proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1");

            assertNotNull(result);
            assertTrue(result instanceof ResponseEntity);
            ResponseEntity<?> responseEntity = (ResponseEntity<?>) result;
            assertEquals(500, responseEntity.getStatusCode().value());
            ErrorRsp errorRsp = (ErrorRsp) responseEntity.getBody();
            assertNotNull(errorRsp);
            assertEquals("openjiuwen.02501049", errorRsp.getErrorCode());
            assertEquals("model invoke failed", errorRsp.getErrorMsg());
            assertNotNull(errorRsp.getDetails());
            assertEquals(1, errorRsp.getDetails().size());
            assertEquals("upstream 500", errorRsp.getDetails().get(0).getErrorMsg());
        }
    }

    /**
     * 文本向量化调测 — Feign 异常但错误体不可解析：退回通用错误码
     */
    @Test
    void testTextEmbeddings_FeignException_UnparsableError() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            // 注入 i18nUtil mock（构造函数不包含，需通过反射注入）
            com.openjiuwen.studio.agent.common.utils.I18nUtil i18nUtilMock =
                org.mockito.Mockito.mock(com.openjiuwen.studio.agent.common.utils.I18nUtil.class);
            com.openjiuwen.studio.agent.common.utils.ErrorInfo errorInfo =
                new com.openjiuwen.studio.agent.common.utils.ErrorInfo("unavailable", "reason", "suggestion");
            when(i18nUtilMock.getMessage(any(com.openjiuwen.studio.agent.common.exception.AgentStudioException.class)))
                .thenReturn(errorInfo);
            ReflectionTestUtils.setField(proxyService, "i18nUtil", i18nUtilMock);

            String badBody = "not-a-json";
            FeignException feignException = new FeignException.BadGateway(
                "bad gateway", mockFeignRequest(), badBody.getBytes(StandardCharsets.UTF_8),
                Collections.emptyMap());
            when(builderClient.textEmbeddings(anyString(), anyString(), anyString(),
                any(EmbeddingRequest.class), any())).thenThrow(feignException);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            Object result = proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1");

            assertNotNull(result);
            assertTrue(result instanceof ResponseEntity);
            ResponseEntity<?> responseEntity = (ResponseEntity<?>) result;
            assertEquals(502, responseEntity.getStatusCode().value());
            ErrorRsp errorRsp = (ErrorRsp) responseEntity.getBody();
            assertNotNull(errorRsp);
            assertEquals(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE.getFullCode(), errorRsp.getErrorCode());
        }
    }

    // ==================== 文本排序调测连通性测试 ====================

    /**
     * 文本排序调测 — 正常调用：权限校验通过 + Feign 返回结果
     */
    @Test
    void testRerank_Success() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            com.alibaba.fastjson.JSONObject expectedResult = new com.alibaba.fastjson.JSONObject();
            expectedResult.put("results", "rerank-result");
            when(builderClient.rerank(anyString(), anyString(), anyString(),
                any(RankDocumentsRequest.class), any())).thenReturn(expectedResult);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1", "doc2"));
            request.setTopN(2);

            Object result = proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1");

            assertNotNull(result);
            assertEquals(expectedResult, result);
        }
    }

    /**
     * 文本排序调测 — 权限校验失败：模型不存在，抛出 AgentStudioException
     */
    @Test
    void testRerank_PermissionDenied() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(modelServiceMapper.queryById("model-1")).thenReturn(null);
            when(freeModelServiceMapper.queryById("model-1")).thenReturn(null);
            when(routerStrategyMapper.selectInfoById("model-1")).thenReturn(null);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1"));
            request.setTopN(1);

            assertThrows(AgentStudioException.class,
                () -> proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1"));
        }
    }

    /**
     * 文本排序调测 — Feign 异常且可解析错误体：返回 ErrorRsp
     */
    @Test
    void testRerank_FeignException_ParsableError() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            String errorBody = "{\"error_code\":\"openjiuwen.02501049\",\"error_msg\":\"model invoke failed\","
                + "\"error_reason\":\"upstream error\",\"error_suggestion\":\"check model config\","
                + "\"details\":[{\"error_msg\":\"upstream 500\"}]}";
            FeignException feignException = new FeignException.InternalServerError(
                "internal error", mockFeignRequest(), errorBody.getBytes(StandardCharsets.UTF_8),
                Collections.emptyMap());
            when(builderClient.rerank(anyString(), anyString(), anyString(),
                any(RankDocumentsRequest.class), any())).thenThrow(feignException);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1"));
            request.setTopN(1);

            Object result = proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1");

            assertNotNull(result);
            assertTrue(result instanceof ResponseEntity);
            ResponseEntity<?> responseEntity = (ResponseEntity<?>) result;
            assertEquals(500, responseEntity.getStatusCode().value());
            ErrorRsp errorRsp = (ErrorRsp) responseEntity.getBody();
            assertNotNull(errorRsp);
            assertEquals("openjiuwen.02501049", errorRsp.getErrorCode());
            assertEquals("model invoke failed", errorRsp.getErrorMsg());
            assertNotNull(errorRsp.getDetails());
            assertEquals(1, errorRsp.getDetails().size());
            assertEquals("upstream 500", errorRsp.getDetails().get(0).getErrorMsg());
        }
    }

    /**
     * 文本排序调测 — Feign 异常但错误体不可解析：退回通用错误码
     */
    @Test
    void testRerank_FeignException_UnparsableError() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            ModelServiceBase model = new ModelServiceBase();
            model.setPublic(true);
            when(modelServiceMapper.queryById("model-1")).thenReturn(model);

            // 注入 i18nUtil mock（构造函数不包含，需通过反射注入）
            com.openjiuwen.studio.agent.common.utils.I18nUtil i18nUtilMock =
                org.mockito.Mockito.mock(com.openjiuwen.studio.agent.common.utils.I18nUtil.class);
            com.openjiuwen.studio.agent.common.utils.ErrorInfo errorInfo =
                new com.openjiuwen.studio.agent.common.utils.ErrorInfo("unavailable", "reason", "suggestion");
            when(i18nUtilMock.getMessage(any(com.openjiuwen.studio.agent.common.exception.AgentStudioException.class)))
                .thenReturn(errorInfo);
            ReflectionTestUtils.setField(proxyService, "i18nUtil", i18nUtilMock);

            String badBody = "not-a-json";
            FeignException feignException = new FeignException.ServiceUnavailable(
                "service unavailable", mockFeignRequest(), badBody.getBytes(StandardCharsets.UTF_8),
                Collections.emptyMap());
            when(builderClient.rerank(anyString(), anyString(), anyString(),
                any(RankDocumentsRequest.class), any())).thenThrow(feignException);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1"));
            request.setTopN(1);

            Object result = proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1");

            assertNotNull(result);
            assertTrue(result instanceof ResponseEntity);
            ResponseEntity<?> responseEntity = (ResponseEntity<?>) result;
            assertEquals(503, responseEntity.getStatusCode().value());
            ErrorRsp errorRsp = (ErrorRsp) responseEntity.getBody();
            assertNotNull(errorRsp);
            assertEquals(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE.getFullCode(), errorRsp.getErrorCode());
        }
    }

    /**
     * 构造最小的 feign.Request 用于 FeignException
     */
    private feign.Request mockFeignRequest() {
        return feign.Request.create(
            feign.Request.HttpMethod.POST,
            "http://localhost/v1/agent-builder/embeddings",
            Collections.emptyMap(),
            (byte[]) null,
            StandardCharsets.UTF_8,
            null
        );
    }
}
