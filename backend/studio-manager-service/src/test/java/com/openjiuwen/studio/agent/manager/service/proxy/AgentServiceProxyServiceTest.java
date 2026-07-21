/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
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
}
