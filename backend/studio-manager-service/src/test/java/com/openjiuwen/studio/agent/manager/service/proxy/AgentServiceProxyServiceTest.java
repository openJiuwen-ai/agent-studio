/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.dto.ErrorRsp;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.AgentRunReq;
import com.openjiuwen.studio.agent.manager.dto.runtime.EmbeddingRequest;
import com.openjiuwen.studio.agent.manager.dto.runtime.RankDocumentsRequest;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentManagerEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseChannel;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentManagerMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseChannelMapper;
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
import org.mockito.ArgumentCaptor;
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
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.verify;
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
    private EnvironmentManagerMapper environmentManagerMapper;

    @Mock
    private ReleaseChannelMapper releaseChannelMapper;

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
            modelServiceMapper, okHttpClientUtils, routerStrategyMapper, freeModelServiceMapper, toolMapper,
            environmentManagerMapper, releaseChannelMapper, agentRuntimeService, controllerDebuggingMgmtService, mgObsService);
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
            when(builderClient.textEmbeddings(anyString(), isNull(), anyString(), anyString(),
                any(EmbeddingRequest.class), any(), any())).thenReturn(expectedResult);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            Object result = proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1", null);

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
                () -> proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1", null));
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
            when(builderClient.textEmbeddings(anyString(), isNull(), anyString(), anyString(),
                any(EmbeddingRequest.class), any(), any())).thenThrow(feignException);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            Object result = proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1", null);

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
            when(builderClient.textEmbeddings(anyString(), isNull(), anyString(), anyString(),
                any(EmbeddingRequest.class), any(), any())).thenThrow(feignException);

            EmbeddingRequest request = new EmbeddingRequest();
            request.setModel("model-1");
            request.setInput("hello");

            Object result = proxyService.textEmbeddings(new HttpHeaders(), "ws-1", request, true, "proj-1", null);

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
            when(builderClient.rerank(anyString(), isNull(), anyString(), anyString(),
                any(RankDocumentsRequest.class), any(), any())).thenReturn(expectedResult);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1", "doc2"));
            request.setTopN(2);

            Object result = proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1", null);

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
                () -> proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1", null));
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
            when(builderClient.rerank(anyString(), isNull(), anyString(), anyString(),
                any(RankDocumentsRequest.class), any(), any())).thenThrow(feignException);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1"));
            request.setTopN(1);

            Object result = proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1", null);

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
            when(builderClient.rerank(anyString(), isNull(), anyString(), anyString(),
                any(RankDocumentsRequest.class), any(), any())).thenThrow(feignException);

            RankDocumentsRequest request = new RankDocumentsRequest();
            request.setModel("model-1");
            request.setQuery("query text");
            request.setDocs(List.of("doc1"));
            request.setTopN(1);

            Object result = proxyService.rerank(new HttpHeaders(), "ws-1", request, true, "proj-1", null);

            assertNotNull(result);
            assertTrue(result instanceof ResponseEntity);
            ResponseEntity<?> responseEntity = (ResponseEntity<?>) result;
            assertEquals(503, responseEntity.getStatusCode().value());
            ErrorRsp errorRsp = (ErrorRsp) responseEntity.getBody();
            assertNotNull(errorRsp);
            assertEquals(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE.getFullCode(), errorRsp.getErrorCode());
        }
    }

    // ==================== 单智能体默认环境兜底测试 ====================

    /**
     * resolveEnvironmentId — 入参非空原样透传，不触发默认环境查询
     */
    @Test
    void testResolveEnvironmentId_NonBlankPassthrough() {
        assertEquals("env-explicit", proxyService.resolveEnvironmentId("proj-1", "env-explicit"));

        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * resolveEnvironmentId — 入参为空且默认环境存在，返回默认环境 id
     */
    @Test
    void testResolveEnvironmentId_BlankWithDefaultEnv() {
        EnvironmentManagerEntity env = new EnvironmentManagerEntity();
        env.setId("env-default");
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-1")).thenReturn(List.of(env));

        assertEquals("env-default", proxyService.resolveEnvironmentId("proj-1", null));
    }

    /**
     * resolveEnvironmentId — 入参为空（含空白串）且无默认环境，返回 null
     */
    @Test
    void testResolveEnvironmentId_BlankNoDefaultEnv() {
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-1")).thenReturn(Collections.emptyList());

        assertNull(proxyService.resolveEnvironmentId("proj-1", " "));
    }

    /**
     * resolveEnvironmentId — mapper 查询异常时兜底返回 null，不上抛
     */
    @Test
    void testResolveEnvironmentId_MapperThrows() {
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-1"))
            .thenThrow(new RuntimeException("db down"));

        assertNull(proxyService.resolveEnvironmentId("proj-1", null));
    }

    /**
     * resolveEnvironmentIdForSingleAgent — 入参非空原样透传，不查智能体也不查默认环境
     */
    @Test
    void testResolveEnvironmentIdForSingleAgent_NonBlankPassthrough() {
        assertEquals("env-explicit", proxyService.resolveEnvironmentIdForSingleAgent("proj-1", "agent-1", "env-explicit"));

        verify(agentMapper, never()).selectById(anyString());
        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * resolveEnvironmentIdForSingleAgent — 单智能体（type=agent）且默认环境存在：返回默认环境 id
     */
    @Test
    void testResolveEnvironmentIdForSingleAgent_SingleAgentWithDefaultEnv() {
        Agent agent = new Agent();
        agent.setType(CommonConstant.AGENT_TYPE);
        agent.setProjectId("proj-1");
        when(agentMapper.selectById("agent-1")).thenReturn(agent);
        EnvironmentManagerEntity env = new EnvironmentManagerEntity();
        env.setId("env-default");
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-1")).thenReturn(List.of(env));

        assertEquals("env-default", proxyService.resolveEnvironmentIdForSingleAgent("proj-1", "agent-1", null));
    }

    /**
     * resolveEnvironmentIdForSingleAgent — 共享智能体（归属项目≠请求项目，opSvc 发布态
     * 跨项目调用可达）：不兜底返回 null，不查默认环境——调用方项目默认环境变量不能
     * 注入归属其它项目的智能体（runtime 按请求 workspace 加载变量，会把发布方
     * 占位符 api_url 解析到调用方环境配置的端点）
     */
    @Test
    void testResolveEnvironmentIdForSingleAgent_SharedAgentCrossProject_NoFallback() {
        Agent agent = new Agent();
        agent.setType(CommonConstant.AGENT_TYPE);
        agent.setProjectId("op-svc-project");
        when(agentMapper.selectById("agent-1")).thenReturn(agent);

        assertNull(proxyService.resolveEnvironmentIdForSingleAgent("proj-1", "agent-1", null));

        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * resolveEnvironmentIdForSingleAgent — 多智能体（type=controller）：不兜底返回 null，
     * 不触发默认环境查询（runtime 会话路由同时服务单智能体与多智能体）
     */
    @Test
    void testResolveEnvironmentIdForSingleAgent_ControllerType_NoFallback() {
        Agent agent = new Agent();
        agent.setType("controller");
        when(agentMapper.selectById("agent-1")).thenReturn(agent);

        assertNull(proxyService.resolveEnvironmentIdForSingleAgent("proj-1", "agent-1", null));

        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * resolveEnvironmentIdForSingleAgent — 智能体不存在：fail-closed 返回 null，不查默认环境
     */
    @Test
    void testResolveEnvironmentIdForSingleAgent_AgentNotFound_NoFallback() {
        when(agentMapper.selectById("agent-x")).thenReturn(null);

        assertNull(proxyService.resolveEnvironmentIdForSingleAgent("proj-1", "agent-x", null));

        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * resolveEnvironmentIdForSingleAgent — 智能体查询异常：fail-closed 返回 null，不上抛
     */
    @Test
    void testResolveEnvironmentIdForSingleAgent_AgentMapperThrows() {
        when(agentMapper.selectById("agent-1")).thenThrow(new RuntimeException("db down"));

        assertNull(proxyService.resolveEnvironmentIdForSingleAgent("proj-1", "agent-1", null));
    }

    /** 构造网页发布通道 stub：short_code=code-1，所属项目可指定；appType 默认单智能体 */
    private ReleaseChannel webChannel(String projectId) {
        return webChannel(projectId, CommonConstant.AGENT_TYPE);
    }

    /** 构造网页发布通道 stub：short_code=code-1，所属项目与发布应用类型可指定 */
    private ReleaseChannel webChannel(String projectId, String appType) {
        ReleaseChannel channel = new ReleaseChannel();
        channel.setShortCode("code-1");
        channel.setProjectId(projectId);
        channel.setAppType(appType);
        channel.setWorkspaceId("ws-owner");
        return channel;
    }

    /**
     * runWebAgent 流式 — 通道存在且有默认环境：转发 URL 追加 environment_id，
     * 默认环境按通道所属项目解析、workspace 取发布通道 workspace（通道项目与路径
     * project_id 故意不同，断言路径 project_id 与请求 workspace_id 均不参与
     * 解析 —— 短链入口无鉴权的信任边界；环境变量按 (env, workspace) 维度存储，
     * 请求 workspace 可换成发布项目其它空间选取不同变量值）
     */
    @Test
    void testRunWebAgent_StreamWithDefaultEnv() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(webChannel("proj-owner"));
        EnvironmentManagerEntity env = new EnvironmentManagerEntity();
        env.setId("env-default");
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-owner")).thenReturn(List.of(env));

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-owner&environment_id=env-default",
            urlCaptor.getValue());
        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue("proj-1");
    }

    /**
     * runWebAgent 流式（stream 缺省按 true）— 通道存在但项目无默认环境：
     * 转发 URL 不带 environment_id，行为同现状
     */
    @Test
    void testRunWebAgent_StreamNoDefaultEnv() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(webChannel("proj-owner"));
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-owner")).thenReturn(Collections.emptyList());

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", null, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-1", urlCaptor.getValue());
    }

    /**
     * runWebAgent 非流式 — 通道存在且有默认环境：Feign 调用携带默认环境 id
     */
    @Test
    void testRunWebAgent_NonStreamWithDefaultEnv() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
                eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(webChannel("proj-owner"));
            EnvironmentManagerEntity env = new EnvironmentManagerEntity();
            env.setId("env-default");
            when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-owner")).thenReturn(List.of(env));

            AgentRunReq body = new AgentRunReq().setQuery("hello");
            ResponseEntity<Object> expected = ResponseEntity.ok("ok");
            when(runtimeClient.runWebAgent("token", "code-1", "ws-owner", false, "env-default", body))
                .thenReturn(expected);

            Object result = proxyService.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", false, body);

            assertEquals("ok", result);
        }
    }

    /**
     * runWebAgent 非流式 — 通道存在但项目无默认环境：Feign 调用 environment_id 为 null，行为同现状
     */
    @Test
    void testRunWebAgent_NonStreamNoDefaultEnv() {
        try (MockedStatic<RequestContextUtils> mockedStatic = mockStatic(RequestContextUtils.class)) {
            mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
            when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
                eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(webChannel("proj-owner"));
            when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-owner")).thenReturn(Collections.emptyList());

            AgentRunReq body = new AgentRunReq().setQuery("hello");
            ResponseEntity<Object> expected = ResponseEntity.ok("ok");
            when(runtimeClient.runWebAgent("token", "code-1", "ws-1", false, null, body))
                .thenReturn(expected);

            Object result = proxyService.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", false, body);

            assertEquals("ok", result);
        }
    }

    /**
     * runWebAgent — 两类网页渠道均查不到通道（short_code 无效）：不带 environment_id，
     * 也不触发默认环境查询（不能借用路径 project_id 的环境）
     */
    @Test
    void testRunWebAgent_ChannelNotFound_NoEnv() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(null);
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.CLOUD_STORE_CHANNEL))).thenReturn(null);

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-1", urlCaptor.getValue());
        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * runWebAgent — WEB_PAGE 渠道查不到时回退 CLOUD_STORE 渠道：按云商店通道所属项目解析默认环境
     */
    @Test
    void testRunWebAgent_CloudStoreChannelFallback() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(null);
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.CLOUD_STORE_CHANNEL))).thenReturn(webChannel("proj-cloud"));
        EnvironmentManagerEntity env = new EnvironmentManagerEntity();
        env.setId("env-cloud");
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue("proj-cloud")).thenReturn(List.of(env));

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-owner&environment_id=env-cloud",
            urlCaptor.getValue());
    }

    /**
     * runWebAgent — 通道查表异常：兜底不带 environment_id，不上抛
     */
    @Test
    void testRunWebAgent_ChannelLookupThrows_NoEnv() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenThrow(new RuntimeException("db down"));

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-1", urlCaptor.getValue());
    }

    /**
     * runWebAgent — 通道存在但所属项目为空白：视为无法解析，不带 environment_id
     */
    @Test
    void testRunWebAgent_ChannelProjectBlank_NoEnv() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(webChannel(" "));

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-1", urlCaptor.getValue());
        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * runWebAgent — 通道存在但发布应用非单智能体（appType=controller）：
     * 不兜底默认环境，转发 URL 不带 environment_id（多智能体发布不走本兜底）
     */
    @Test
    void testRunWebAgent_ChannelAppTypeNotAgent_NoEnv() {
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(webChannel("proj-owner", "controller"));

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-1", urlCaptor.getValue());
        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
    }

    /**
     * runWebAgent — 通道存在且为单智能体但通道 workspace 缺失：fail-closed 不注入
     * 默认环境（不回退到请求 workspace 加载，请求 workspace 无鉴权不可信），
     * 转发 URL 保持请求 workspace、不带 environment_id
     */
    @Test
    void testRunWebAgent_ChannelWorkspaceBlank_NoEnv() {
        ReleaseChannel channel = new ReleaseChannel();
        channel.setShortCode("code-1");
        channel.setProjectId("proj-owner");
        channel.setAppType(CommonConstant.AGENT_TYPE);
        channel.setWorkspaceId(" ");
        when(releaseChannelMapper.selectByChannelIdOrShortCode(isNull(), isNull(), eq("code-1"),
            eq(CommonConstant.WEB_PAGE_CHANNEL))).thenReturn(channel);

        AgentServiceProxyService spied = spy(proxyService);
        doReturn(new Object()).when(spied).stream(anyString(), any(HttpHeaders.class), anyString());

        spied.runWebAgent("code-1", "proj-1", new HttpHeaders(), "ws-1", true, new AgentRunReq());

        ArgumentCaptor<String> urlCaptor = ArgumentCaptor.forClass(String.class);
        verify(spied).stream(urlCaptor.capture(), any(HttpHeaders.class), anyString());
        assertEquals("http://runtime:8080/v1/agents/chat/code-1?workspace_id=ws-1", urlCaptor.getValue());
        verify(environmentManagerMapper, never()).findByProjectIdAndIsDefaultTrue(anyString());
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
