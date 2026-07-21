/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.md;

import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_DOMAIN_ID;
import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_PROJECT_ID;
import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_WORKSPACE_ID;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckRsp;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ProviderAuthDataMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentBuilderClient;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.agent.common.utils.CryptoUtils;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * @since: 2025-08-13 10:16:22
 */
@Transactional
@TestPropertySource(properties = {"model.free-model.enable=true"})
public class ModelServiceManagerTest extends BaseTest {
    private static final String MOCK_MODEL_ID = "TestModelId";

    private static final String MOCK_SERVICE_NAME = "TestServiceName";

    private static final String MOCK_SERVICE_KEY = "TestServiceKey";

    private static final String MOCK_MODEL_NAME = "TestModelName";

    private static final String MOCK_MODEL_VERSION = "TestModelVersion";

    private static final String MOCK_MODEL_TYPE = "TestModelType";

    private static final String MOCK_MODEL_DEPLOY_TYPE = "TestModelDeployType";

    private static final String MOCK_API_URL = "TestApiUrl";

    private static final String MOCK_INTERFACE_PROTOCOL = "TestInterfaceProtocol";

    private static final String MOCK_PUBLISH_STATUS = "offline";

    private static final boolean MOCK_IS_SUPPORT_FUNCTION = true;

    private static final boolean MOCK_IS_SUPPORT_STREAM = false;

    @InjectMocks
    private ModelServiceManager modelServiceManager;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ModelServiceMapper modelServiceMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private RouterStrategyMapper routerStrategyMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MgObsService obsService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentRuntimeClient runtimeClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentBuilderClient builderClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private RedisClient redisClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ProviderAuthDataMapper authDataMapper;

    private static MockedStatic<RequestContextUtils> mockedStatic;

    @BeforeAll
    public static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(TEST_WORKSPACE_ID);
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(modelServiceManager,
                "intentModelRecommendation", "test_deployment_id1");
        ReflectionTestUtils.setField(modelServiceManager, "obsService", obsService);
        ReflectionTestUtils.setField(modelServiceManager, "runtimeClient", runtimeClient);
        ReflectionTestUtils.setField(modelServiceManager, "redisClient", redisClient);
    }

    @Test
    public void testCreateModelService() {
        ModelServiceBase model = new ModelServiceBase();
        model.setId(MOCK_MODEL_ID);
        model.setServiceName(MOCK_SERVICE_NAME);
        model.setServiceKey(MOCK_SERVICE_KEY);
        model.setModelName(MOCK_MODEL_NAME);
        model.setModelVersion(MOCK_MODEL_VERSION);
        model.setModelType(MOCK_MODEL_TYPE);
        model.setDomainId(TEST_DOMAIN_ID);
        model.setProjectId(TEST_PROJECT_ID);
        model.setWorkspaceId(TEST_WORKSPACE_ID);
        model.setModelDeployType(MOCK_MODEL_DEPLOY_TYPE);
        model.setApiUrl(MOCK_API_URL);
        model.setInterfaceProtocol(MOCK_INTERFACE_PROTOCOL);
        model.setPublishStatus(MOCK_PUBLISH_STATUS);
        model.setIsSupportFunction(MOCK_IS_SUPPORT_FUNCTION);
        model.setIsSupportStream(MOCK_IS_SUPPORT_STREAM);

        modelServiceManager.createModelService(model);

        verify(modelServiceMapper).insert(model);
        verify(obsService).putObject(anyString(), anyString());
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_manager_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testUpdateModelService() {
        ModelServiceBase model = new ModelServiceBase();
        model.setId(MOCK_MODEL_ID);
        model.setServiceName(MOCK_SERVICE_NAME);
        model.setServiceKey(MOCK_SERVICE_KEY);
        model.setModelName(MOCK_MODEL_NAME);
        model.setModelVersion(MOCK_MODEL_VERSION);
        model.setModelType(MOCK_MODEL_TYPE);
        model.setDomainId(TEST_DOMAIN_ID);
        model.setProjectId(TEST_PROJECT_ID);
        model.setWorkspaceId(TEST_WORKSPACE_ID);
        model.setModelDeployType(MOCK_MODEL_DEPLOY_TYPE);
        model.setApiUrl(MOCK_API_URL);
        model.setInterfaceProtocol(MOCK_INTERFACE_PROTOCOL);
        model.setPublishStatus(MOCK_PUBLISH_STATUS);
        model.setIsSupportFunction(MOCK_IS_SUPPORT_FUNCTION);
        model.setIsSupportStream(MOCK_IS_SUPPORT_STREAM);

        modelServiceManager.updateModelService(model);

        verify(modelServiceMapper).updateModelService(model);
        verify(obsService).putObject(anyString(), anyString());
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_manager_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testDeleteModelService() {
        modelServiceManager.deleteModelService(MOCK_MODEL_ID);

        verify(modelServiceMapper).deleteById(MOCK_MODEL_ID);
        verify(obsService).deleteObject(anyString());
    }

    @Test
    public void testQueryAllAvailableServiceIds() {
        ModelServiceData modelServiceData = new ModelServiceData();
        modelServiceData.setId("test_deployment_id1");
        when(modelServiceMapper.queryAvailableServices(any())).thenReturn(
            Collections.singletonList(modelServiceData));
        when(modelServiceMapper.queryPublicAvailableServices(any())).thenReturn(new ArrayList<>());

        Set<String> result = modelServiceManager.queryAllAvailableServiceIds(TEST_PROJECT_ID, TEST_WORKSPACE_ID);

        assertEquals(1, result.size());
    }

    @Test
    public void testQueryAvailableServices() {
        ModelServiceData modelServiceData = new ModelServiceData();
        modelServiceData.setId("test_deployment_id1");
        when(modelServiceMapper.queryAvailableServices(any())).thenReturn(
            Collections.singletonList(modelServiceData));
        when(modelServiceMapper.queryPublicAvailableServices(any())).thenReturn(new ArrayList<>());

        List<ModelServiceData> result = modelServiceManager.queryAvailableServices(TEST_PROJECT_ID, TEST_WORKSPACE_ID,
            null, true);

        assertEquals(1, result.size());
    }

    @Test
    public void testParseModelExtension() {
        ModelServiceBase model = new ModelServiceBase();
        model.setId(MOCK_MODEL_ID);
        model.setServiceName(MOCK_SERVICE_NAME);
        model.setServiceKey(MOCK_SERVICE_KEY);
        model.setModelName(MOCK_MODEL_NAME);
        model.setModelVersion(MOCK_MODEL_VERSION);
        model.setModelType(MOCK_MODEL_TYPE);
        model.setDomainId(TEST_DOMAIN_ID);
        model.setProjectId(TEST_PROJECT_ID);
        model.setWorkspaceId(TEST_WORKSPACE_ID);
        model.setModelDeployType(MOCK_MODEL_DEPLOY_TYPE);
        model.setApiUrl(MOCK_API_URL);
        model.setInterfaceProtocol(MOCK_INTERFACE_PROTOCOL);
        model.setPublishStatus(MOCK_PUBLISH_STATUS);
        model.setIsSupportFunction(MOCK_IS_SUPPORT_FUNCTION);
        model.setIsSupportStream(MOCK_IS_SUPPORT_STREAM);
        model.setSystemPrompt("test-prompt");

        when(modelServiceMapper.queryById(MOCK_MODEL_ID)).thenReturn(model);

        Map<String, Object> result = modelServiceManager.parseModelExtension(MOCK_MODEL_ID, TEST_PROJECT_ID,
            TEST_WORKSPACE_ID, false);

        assertNotNull(result);
        assertEquals(MOCK_MODEL_ID, result.get("deploymentId"));
        assertEquals("test-prompt", result.get("systemPrompt"));

        when(modelServiceMapper.queryById(MOCK_MODEL_ID)).thenReturn(null);
        result = modelServiceManager.parseModelExtension(MOCK_MODEL_ID, TEST_PROJECT_ID, TEST_WORKSPACE_ID, false);
        Assertions.assertNotNull(result);

        model = new ModelServiceBase();
        model.setProjectId("test");
        when(modelServiceMapper.queryById(MOCK_MODEL_ID)).thenReturn(model);
        result = modelServiceManager.parseModelExtension(MOCK_MODEL_ID, TEST_PROJECT_ID, TEST_WORKSPACE_ID, false);
        Assertions.assertNotNull(result);

        model = new ModelServiceBase();
        model.setProjectId(TEST_PROJECT_ID);
        model.setWorkspaceId("test");
        when(modelServiceMapper.queryById(MOCK_MODEL_ID)).thenReturn(model);
        result = modelServiceManager.parseModelExtension(MOCK_MODEL_ID, TEST_PROJECT_ID, TEST_WORKSPACE_ID, false);
        Assertions.assertNotNull(result);
    }

    @Test
    public void testSaveRouterStrategy() {
        RouterStrategyEntity entity = new RouterStrategyEntity();
        entity.setId(MOCK_MODEL_ID);

        modelServiceManager.saveRouterStrategy(entity);

        verify(routerStrategyMapper).insert(entity);
        verify(obsService).putObject(anyString(), anyString());
    }

    @Test
    @Sql(scripts = {"classpath:sql/router_strategy_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testDeleteRouterStrategy() {
        modelServiceManager.deleteRouterStrategy(MOCK_MODEL_ID);

        verify(routerStrategyMapper).deleteById(MOCK_MODEL_ID);
        verify(obsService).deleteObject(anyString());
    }

    @Test
    @Sql(scripts = {"classpath:sql/router_strategy_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testUpdateRouterStrategy() {
        RouterStrategyEntity entity = new RouterStrategyEntity();
        entity.setId(MOCK_MODEL_ID);

        modelServiceManager.updateRouterStrategy(entity);

        verify(routerStrategyMapper).update(entity);
        verify(obsService).putObject(anyString(), anyString());
    }

    @Test
    public void checkProviderAuthTest() {
        Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                Mockito.any(ModelServiceCheckReq.class)))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(true)));

        modelServiceManager.checkProviderAuth("test_project_id", "default", "NO_AUTH", "{}", "100", true);
        modelServiceManager.checkProviderAuth("test_project_id", "default", "NO_AUTH", "{}", "nn", false);

        Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                Mockito.any(ModelServiceCheckReq.class)))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(false).setReason("ModelArts.81004")));
        modelServiceManager.checkProviderAuth("test_project_id", "default", "NO_AUTH", "{}", "100", true);

        ModelServiceManager service = new ModelServiceManager();
        ModelServiceMapper mapper = Mockito.mock(ModelServiceMapper.class);
        AgentRuntimeClient client = Mockito.mock(AgentRuntimeClient.class);
        ReflectionTestUtils.setField(service, "modelServiceMapper", mapper);
        ReflectionTestUtils.setField(service, "runtimeClient", client);

        ModelServiceBase base = new ModelServiceBase().setId("123").setModelName("");
        Mockito.when(mapper.queryByProviders(Mockito.anyString(), Mockito.anyString(), Mockito.anyString()))
            .thenReturn(Collections.singletonList(base));
    }

    @Test
    public void checkProviderAuthTest2() {
        ModelServiceManager service = new ModelServiceManager();
        ModelServiceMapper mapper = Mockito.mock(ModelServiceMapper.class);
        AgentBuilderClient client = Mockito.mock(AgentBuilderClient.class);
        ReflectionTestUtils.setField(service, "modelServiceMapper", mapper);
        ReflectionTestUtils.setField(service, "runtimeClient", client);

        ModelServiceBase base = new ModelServiceBase().setId("123").setModelName("");
        Mockito.when(mapper.queryByProviders(Mockito.any(), Mockito.anyString(), Mockito.anyString()))
            .thenReturn(Collections.singletonList(base));

        Mockito.when(client.modelServiceAvailableCheck(Mockito.any(), Mockito.anyString(),
                Mockito.any(ModelServiceCheckReq.class)))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(false).setReason("81004")));

        try {
            service.checkProviderAuth("test_project_id", "default", "NO_AUTH", "{}", "100", true);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_PROVIDER_AUTH_DATA_INVALID, e.getErrorCode());
        }

        Mockito.when(client.modelServiceAvailableCheck(Mockito.any(), Mockito.anyString(),
                Mockito.any(ModelServiceCheckReq.class)))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(false).setReason("81004")));
        try {
            service.checkProviderAuth("test_project_id", "default", "NO_AUTH", "{}", "100", false);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_OR_AUTH_NOT_INVALID, e.getErrorCode());
        }
    }

    @Test
    void testCheckModelAvailableWithValidAuthInfoString() {
        // 准备参数
        String projectId = "123";
        String workspaceId = "default";
        String modelName = "testModel";
        String modelType = "type";
        String modelApiUrl = "http://api.com";
        String interfaceProtocol = "http";
        String authType = "basic";
        String authInfoJson = "{\"username\":\"user123\",\"password\":\"pass123\"}";

        // 模拟runtimeClient返回成功响应
        Mockito.when(builderClient.modelServiceAvailableCheck(any(), any(), any()))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(true)));


        try (MockedStatic<CryptoUtils> mockedSccCryptoUtils = Mockito.mockStatic(CryptoUtils.class)) {
            mockedSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("test");
            mockedSccCryptoUtils.when(() -> CryptoUtils.encrypt(anyString())).thenReturn("test");

            // 调用方法
            modelServiceManager.checkModelAvailable(projectId, modelName, modelType, modelApiUrl, interfaceProtocol,
                authType, authInfoJson, false);

            // 验证请求是否正确构建
            verify(builderClient).modelServiceAvailableCheck(any(), any(), any());
        }
    }

    @Test
    void testCheckModelAvailableWithValidAuthInfoMap() {
        // 准备参数
        String projectId = "123";
        String workspaceId = "default";
        String modelName = "testModel";
        String modelType = "type";
        String modelApiUrl = "http://api.com";
        String interfaceProtocol = "http";
        String authType = "basic";
        Map<String, String> authInfoMap = new HashMap<>();
        authInfoMap.put("username", "user123");
        authInfoMap.put("password", "pass123");

        // 模拟成功响应
        ModelServiceCheckRsp mockRsp = new ModelServiceCheckRsp();
        mockRsp.setSuccess(true);
        Mockito.when(builderClient.modelServiceAvailableCheck(any(), any(), any()))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(true)));

        try (MockedStatic<CryptoUtils> mockedSccCryptoUtils = Mockito.mockStatic(CryptoUtils.class)) {
            mockedSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("test");
            mockedSccCryptoUtils.when(() -> CryptoUtils.encrypt(anyString())).thenReturn("test");

            // 调用方法
            modelServiceManager.checkModelAvailable(projectId, modelName, modelType, modelApiUrl, interfaceProtocol,
                authType, authInfoMap, false);

            // 验证请求构建
            verify(builderClient).modelServiceAvailableCheck(any(), any(), any());
        }
    }

    @Test
    void testCheckModelAvailableWithInvalidAuthInfoType() {
        // 准备参数
        String projectId = "123";
        String workspaceId = "default";
        String modelName = "testModel";
        String modelType = "type";
        String modelApiUrl = "http://api.com";
        String interfaceProtocol = "http";
        String authType = "basic";
        Map<String, String> authInfoMap = new HashMap<>();
        authInfoMap.put("username", "user123");
        authInfoMap.put("password", "pass123");

        // 模拟成功响应
        Mockito.when(builderClient.modelServiceAvailableCheck(any(), any(), any()))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(true)));

        try (MockedStatic<CryptoUtils> mockedSccCryptoUtils = Mockito.mockStatic(CryptoUtils.class)) {
            mockedSccCryptoUtils.when(() -> CryptoUtils.decrypt(anyString())).thenReturn("test");
            mockedSccCryptoUtils.when(() -> CryptoUtils.encrypt(anyString())).thenReturn("test");

            // 调用方法，预期不处理authInfo
            modelServiceManager.checkModelAvailable(projectId, modelName, modelType, modelApiUrl, interfaceProtocol,
                authType, authInfoMap, false);

            // 验证请求构建，authInfo未设置
            verify(builderClient).modelServiceAvailableCheck(any(), any(), any());
        }
    }

    @Test
    void testCheckModelAvailableWithServiceUnavailable() {
        // 准备参数
        String projectId = "123";
        String workspaceId = "default";
        String modelName = "testModel";
        String modelType = "type";
        String modelApiUrl = "http://api.com";
        String interfaceProtocol = "http";
        String authType = "basic";
        String authInfo = "{}";

        // 模拟失败响应
        Mockito.when(builderClient.modelServiceAvailableCheck(any(), any(), any()))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(false)));

        // 预期抛出异常
        ModelServiceCheckRsp rsp = modelServiceManager.checkModelAvailable(projectId, modelName, modelType, modelApiUrl,
            interfaceProtocol, authType, authInfo, false);

        Assertions.assertFalse(rsp.isSuccess());
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_manager_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void syncUpgradeModelsTest() {
        modelServiceManager.syncUpgradeModels();
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_manager_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void syncSysPlatformModelsTest(){
        modelServiceManager.syncSysPlatformModels(Collections.singletonList(new ModelServiceData()));
    }
}

