/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.md;

import static com.openjiuwen.studio.agent.common.enums.StudioError.MD_DATA_NOT_EXIST;
import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_PROJECT_ID;
import static com.openjiuwen.studio.agent.manager.constant.Constants.TEST_WORKSPACE_ID;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.EN_LANGUAGE;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.fail;

import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckReq;
import com.openjiuwen.studio.agent.common.dto.md.ModelServiceCheckRsp;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.ModelInvokeDataListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListQo;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceReq;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.ModelStatusReq;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentBuilderClient;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;
import com.openjiuwen.studio.prompt.engineering.utils.HttpUtil;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;


@Transactional
@TestPropertySource(properties = {"model.sync-model.syncEnabled=true", "model.free-model.enable=true"})
public class ModelServiceMgmtServiceTest extends BaseTest {
    @Autowired
    private ModelServiceMgmtService modelServiceMgmtService;

    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<HttpUtil> mockedStaticHttp;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MgObsService mgObsService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentRuntimeClient runtimeClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentBuilderClient builderClient;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ModelLicenseCtrlService licenseCtrlService;

    @Autowired
    private ProviderAuthService authService;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @BeforeAll
    public static void init() {
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_USER_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(TEST_WORKSPACE_ID);
        mockedStaticHttp = Mockito.mockStatic(HttpUtil.class);
        mockedStaticHttp.when(HttpUtil::getLanguage).thenReturn(EN_LANGUAGE);
    }

    @BeforeEach
    public void beforeEach() {
        ReflectionTestUtils.setField(modelServiceManager, "obsService", mgObsService);
        ReflectionTestUtils.setField(modelServiceManager, "runtimeClient", runtimeClient);
        ReflectionTestUtils.setField(authService, "obsService", mgObsService);
        ReflectionTestUtils.setField(modelServiceMgmtService, "licenseCtrlService", licenseCtrlService);
        ReflectionTestUtils.setField(modelServiceMgmtService, "platformProvider", "model_test_provider");
        ReflectionTestUtils.setField(modelServiceMgmtService,
                "intentModelRecommendation", "test_deployment_id1");
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        mockedStaticHttp.close();
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void createModelServiceTest() {
        ModelServiceReq req = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("agentBuilder-128k")
            .setModelName("deepseek-128k");

        try {
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", false, req);
            fail("服务名重复时应抛出异常");
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MODEL_NAME_REPEATED, e.getErrorCode());
        }

        ModelServiceReq nullPolicyReq = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("test-null-policy")
            .setModelName("valid-model")
            .setApiUrl("open.bigmodel.cn")
            .setInterfaceProtocol("openapi")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true);

        try {
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", false, nullPolicyReq);
            fail("ThrottlingPolicy 为 null 时应抛出异常");
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MD_INVALID_THROTTLING_POLICY, e.getErrorCode());
        }

        ModelServiceReq emptyPolicyReq = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("test-empty-policy")
            .setModelName("valid-model")
            .setApiUrl("")
            .setInterfaceProtocol("openapi")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true)
            .setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum.EMPTY);

        String emptyId = modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", false, emptyPolicyReq);
        Assertions.assertNotNull(emptyId);

        ModelServiceReq nonEmptyPolicyReq = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("test-non-empty-policy")
            .setModelName("valid-model")
            .setApiUrl("")
            .setInterfaceProtocol("openapi")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true)
            .setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100);

        String nonEmptyId = modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", false,
            nonEmptyPolicyReq);
        Assertions.assertNotNull(nonEmptyId);

        ModelServiceReq tagsLimitReq = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("tags_limit_service")
            .setModelName("valid-model")
            .setModelTags("tag1,tag2,tag3,tag4,tag5,tag6") // 6个标签
            .setApiUrl("")
            .setInterfaceProtocol("STANDARD")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true)
            .setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100);

        try {
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", false, tagsLimitReq);
            fail("应抛出MD_MODEL_TAGS_LIMIT异常");
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MD_MODEL_TAGS_LIMIT, e.getErrorCode());
        }

        ModelServiceReq validTagsReq = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("valid_tags_service")
            .setModelName("valid-model")
            .setModelTags("tag1,tag2,tag3,tag4,tag5") // 5个标签
            .setApiUrl("")
            .setInterfaceProtocol("STANDARD")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true)
            .setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100);

        String validId = modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", false, validTagsReq);
        Assertions.assertNotNull(validId);
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void createModelServiceCheckModelTest() {
        ModelServiceReq req = new ModelServiceReq().setProviderId("model_test_provider")
            .setServiceName("agentBuilder-128k")
            .setModelName("deepseek-128k")
            .setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100);

        req.setServiceName("test")
            .setApiUrl("")
            .setInterfaceProtocol("openapi")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true);

        try {
            Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                    Mockito.any(ModelServiceCheckReq.class)))
                .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(false)));
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE, e.getErrorCode());
        }

        try {
            Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                    Mockito.any(ModelServiceCheckReq.class)))
                .thenReturn(ResponseEntity.ok(
                    new ModelServiceCheckRsp().setSuccess(false).setStatusCode(404).setDetail("invalid model")));
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE, e.getErrorCode());
        }

        try {
            Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                    Mockito.any(ModelServiceCheckReq.class)))
                .thenReturn(ResponseEntity.ok(
                    new ModelServiceCheckRsp().setSuccess(false).setStatusCode(401).setDetail("auth not ava.")));
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_PROVIDER_AUTH_DATA_INVALID, e.getErrorCode());
        }

        try {
            Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                    Mockito.any(ModelServiceCheckReq.class)))
                .thenReturn(ResponseEntity.ok(
                    new ModelServiceCheckRsp().setSuccess(false).setStatusCode(401).setDetail("demo")));
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_PROVIDER_AUTH_DATA_INVALID, e.getErrorCode());
        }

        try {
            Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                    Mockito.any(ModelServiceCheckReq.class)))
                .thenReturn(ResponseEntity.ok(
                    new ModelServiceCheckRsp().setSuccess(false).setStatusCode(404).setDetail("demo")));
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_SERVICE_NOT_AVAILABLE, e.getErrorCode());
        }

        Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                Mockito.any(ModelServiceCheckReq.class)))
            .thenReturn(ResponseEntity.ok(new ModelServiceCheckRsp().setSuccess(true)));

        String id = modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        Assertions.assertNotNull(id);

        req.setServiceName("xxxxxxxxxxx");
        modelServiceMgmtService.updateModelService(TEST_PROJECT_ID, "default", true, "m1", req);

        try {
            Mockito.when(builderClient.modelServiceAvailableCheck(Mockito.anyString(), Mockito.anyString(),
                    Mockito.any(ModelServiceCheckReq.class)))
                .thenReturn(ResponseEntity.ok(
                    new ModelServiceCheckRsp().setSuccess(false).setStatusCode(401).setDetail("not have access")));
            modelServiceMgmtService.createModelService(TEST_PROJECT_ID, "default", true, req);
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MODEL_NAME_REPEATED, e.getErrorCode());
        }
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void deleteModelServiceTest() {
        try {
            modelServiceMgmtService.deleteModelService(TEST_PROJECT_ID, "default", "not_exist");
            Assertions.fail();
        } catch (AgentStudioException e) {
            assertEquals(MD_DATA_NOT_EXIST, e.getErrorCode());
        }

        try {
            modelServiceMgmtService.deleteModelService(TEST_PROJECT_ID + "a", "default", "m2");
            Assertions.fail();
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MD_SERVICE_PERMISSION, e.getErrorCode());
        }

        try {
            modelServiceMgmtService.deleteModelService(TEST_PROJECT_ID, "default_not", "m2");
            Assertions.fail();
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MD_SERVICE_PERMISSION, e.getErrorCode());
        }

        try {
            modelServiceMgmtService.deleteModelService(TEST_PROJECT_ID, "default", "m2");
            Assertions.fail();
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MD_MODEL_SERVICE_IS_PUBLISH, e.getErrorCode());
        }

        modelServiceMgmtService.deleteModelService(TEST_PROJECT_ID, "default", "m1");
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void modelServiceDetailTest() {
        ModelServiceRsp rsp = modelServiceMgmtService.modelServiceDetail(TEST_PROJECT_ID, "default", "m1");
        Assertions.assertEquals("m1", rsp.getId());
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void modelServiceListTest() {
        ModelServiceListRsp rsp = modelServiceMgmtService.modelServiceList(TEST_PROJECT_ID,
            new ModelServiceListQo().setWorkspaceId("default"));
        Assertions.assertEquals(4, rsp.getTotal());

        ModelServiceListRsp modelServiceListRsp = modelServiceMgmtService.modelServiceList(TEST_PROJECT_ID,
            new ModelServiceListQo().setProviderId("101").setWorkspaceId("default"));
        Assertions.assertEquals(1, modelServiceListRsp.getTotal());

    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void changeModelServiceStatusTest() {
        modelServiceMgmtService.offlineModelService(TEST_PROJECT_ID, "default", "m2");

        modelServiceMgmtService.onlineModelService(TEST_PROJECT_ID, "default", false, "m2");

        try {
            modelServiceMgmtService.onlineModelService(TEST_PROJECT_ID, "default", false, "m2");
            fail();
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_SERVICE_CANNOT_CHANGE, e.getErrorCode());
        }
    }

    @Test
    public void routerToModelServiceRspTest() {
        RouterStrategyEntity entity = new RouterStrategyEntity().setId("id").setStrategyName("name");
        ModelServiceRsp rsp = modelServiceMgmtService.routerToModelServiceRsp(entity);
        Assertions.assertEquals("LLM", rsp.getModelType());
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void updateModelServiceTest() {
        ModelServiceReq req = new ModelServiceReq();

        req.setServiceName("testservice")
            .setModelName("agentBuilder")
            .setApiUrl("open.bigmodel.cn")
            .setInterfaceProtocol("openapi")
            .setModelType("LLM")
            .setIsSupportFunction(true)
            .setIsSupportStream(true)
            .setThrottlingPolicy(null); // ✅ 显式设置为 null

        try {
            modelServiceMgmtService.updateModelService(TEST_PROJECT_ID, "default", false, "m1", req);
            fail("ThrottlingPolicy 为 null 时应抛出异常");
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_INVALID_THROTTLING_POLICY, e.getErrorCode());
        }

        req.setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100)
            .setModelTags("tag1,tag2,tag3,tag4,tag5,tag6"); // 6个标签

        try {
            modelServiceMgmtService.updateModelService(TEST_PROJECT_ID, "default", false, "m1", req);
            fail("应抛出MD_MODEL_TAGS_LIMIT异常");
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_TAGS_LIMIT, e.getErrorCode());
        }

        req.setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100)
            .setModelTags("tag1,tag2,tag3")
            .setServiceName("agentBuilder-128k2"); // 与 m2 服务名重复

        try {
            modelServiceMgmtService.updateModelService(TEST_PROJECT_ID, "default", false, "m1", req);
            fail("服务名重复时应抛出异常");
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MODEL_NAME_REPEATED, e.getErrorCode());
        }

        req.setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100)
            .setModelTags("tag1,tag2,tag3")
            .setServiceName("testservice")
            .setModelName("agentBuilder");

        try {
            modelServiceMgmtService.updateModelService(TEST_PROJECT_ID, "default", false, "m2", req);
            fail("服务状态为 online 时应抛出异常");
        } catch (AgentStudioException e) {
            Assertions.assertEquals(StudioError.MD_MODEL_SERVICE_CANNOT_CHANGE, e.getErrorCode());
        }

        req.setThrottlingPolicy(ModelServiceReq.ThrottlingPolicyEnum._100)
            .setModelTags("tag1,tag2")
            .setServiceName("testservice")
            .setModelName("agentBuilder").setApiUrl("");

        modelServiceMgmtService.updateModelService(TEST_PROJECT_ID, "default", false, "m1", req);
    }

    @Test
    @Sql(scripts = {"classpath:sql/model_service_test_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void queryModelInvokeDataTest() {
        ModelInvokeDataListRsp rsp = modelServiceMgmtService.queryModelInvokeData(TEST_PROJECT_ID, "m1", "default");
        Assertions.assertEquals("agentBuilder-128k", rsp.getData().get(0).getModelName());
    }

    @Test
    public void updateModelStatusTest() {
        modelServiceMgmtService.updateModelStatus("", "", new ModelStatusReq().setModelId("m").setStatus("success"));
    }
}

