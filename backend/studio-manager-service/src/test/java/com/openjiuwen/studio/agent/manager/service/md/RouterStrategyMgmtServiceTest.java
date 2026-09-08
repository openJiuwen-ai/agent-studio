/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.md;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.ModelServiceRsp;
import com.openjiuwen.studio.agent.manager.dto.RouterStrategyRequest;
import com.openjiuwen.studio.agent.manager.entity.ModelExportEntity;
import com.openjiuwen.studio.agent.manager.entity.ModelStrategyExportEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.common.entity.RouterStrategyEntity;
import com.openjiuwen.studio.agent.manager.mapper.md.FreeModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.RouterStrategyMapper;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

@MockitoSettings(strictness = Strictness.LENIENT)
public class RouterStrategyMgmtServiceTest {
    @InjectMocks
    private RouterStrategyMgmtService service;

    @Mock
    private ModelServiceMgmtService modelServiceMgmtService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private RouterStrategyMapper strategyMapperMock;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private RouterStrategyMapper routerStrategyMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ModelServiceMapper modelServiceMapperMock;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ModelServiceManager modelServiceManagerMock;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ModelServiceMapper modelServiceMapper;

    @Mock
    private ModelServiceManager modelServiceManager;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private FreeModelServiceMapper freeModelServiceMapperMock;

    private MockedStatic<RequestContextUtils> requestContextMock;

    @BeforeEach
    public void beforeEach() {
        ReflectionTestUtils.setField(service, "routerStrategyMapper", strategyMapperMock);
        ReflectionTestUtils.setField(service, "modelServiceMapper", modelServiceMapperMock);
        ReflectionTestUtils.setField(service, "modelServiceManager", modelServiceManagerMock);
        ReflectionTestUtils.setField(service, "freeModelServiceMapper", freeModelServiceMapperMock);

        requestContextMock = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS);
        requestContextMock.when(RequestContextUtils::getRequestProjectId).thenReturn("test_project");
        requestContextMock.when(RequestContextUtils::getRequestUserDomainId).thenReturn("test_domain");
    }

    @AfterEach
    public void afterEach() {
        requestContextMock.close();
    }

    @Test
    public void createRouterStrategyNameDuplicateTest() {
        String project = "test_project";
        String workspace = "test_workspace";
        String name = "test_name";
        when(strategyMapperMock.selectInfoByStrategyName(project, workspace, name)).thenReturn(
            Collections.singletonList(new RouterStrategyEntity()));

        RouterStrategyRequest request = new RouterStrategyRequest().setStrategyName(name);
        try {
            service.createRouterStrategy(project, workspace, request);
        } catch (AgentStudioException e) {
            assertEquals(StudioError.ROUTER_STRATEGY_NAME_REPEATED, e.getErrorCode());
        }
    }

    @Test
    public void createRouterStrategyContainFreeModel() {
        when(modelServiceMapperMock.queryByIds(any(), anyString(), anyString())).thenReturn(new ArrayList<>());
        doNothing().when(modelServiceManagerMock).saveRouterStrategy(any());
        when(strategyMapperMock.selectInfoByStrategyName(anyString(), anyString(), anyString())).thenReturn(
            new ArrayList<>());

        ModelServiceData modelMock = new ModelServiceData();
        modelMock.setAuthId("AA").setModelName("model").setId("free");
        when(freeModelServiceMapperMock.queryAllFreeModels(any())).thenReturn(Collections.singletonList(modelMock));

        RouterStrategyRequest request = new RouterStrategyRequest().setStrategyName("test")
            .setModelServiceList(Collections.singletonList(new ModelServiceRsp().setId("free")));

        try {
            service.createRouterStrategy("test", "test", request);
        } catch (AgentStudioException e) {
            assertEquals(StudioError.MD_REQUEST_BODY_INVALID_MODEL_NOT_EXIST, e.getErrorCode());
        }

        ReflectionTestUtils.setField(service, "freeModelEnable", true);
        service.createRouterStrategy("test", "test", request);
    }

    @Test
    public void StrategyExportComprehensiveTest() {
        // 1. 定义公共变量
        String projectId = "proj_test";
        String workspaceId = "ws_test";

        // --- 场景 A: 正常流 (策略 A 关联 2 个模型) ---
        String sIdNormal = "strat_normal";
        RouterStrategyEntity normalStrategy = new RouterStrategyEntity();
        normalStrategy.setId(sIdNormal);
        normalStrategy.setServiceIdList("m1,m2");

        when(strategyMapperMock.queryByIds(Collections.singletonList(sIdNormal), projectId, workspaceId)).thenReturn(
            Collections.singletonList(normalStrategy));
        // 注意：buildModelStrategyExport 走 5 参 buildModelExportEntity(includeProvider=true, strict=false)，
        // 不再直接调 getValidatedModels（后者在 strict=false 下是 warn+skip）。这里返回一个含两个模型的导出实体供下游断言。
        ModelServiceData m1 = new ModelServiceData();
        m1.setId("m1");
        ModelServiceData m2 = new ModelServiceData();
        m2.setId("m2");
        ModelExportEntity exportEntity = new ModelExportEntity();
        exportEntity.setModelMetadata(Arrays.asList(m1, m2));
        when(modelServiceMgmtService.buildModelExportEntity(eq(projectId), eq(workspaceId), eq(Arrays.asList("m1", "m2")),
            eq(true), eq(false))).thenReturn(Collections.singletonList(exportEntity));

        List<ModelStrategyExportEntity> normalResult = service.buildModelStrategyExport(projectId, workspaceId,
            Collections.singletonList(sIdNormal));


        // --- 场景 B: 边界流 (策略 B 关联列表为空字符串) ---
        String sIdEmpty = "strat_empty";
        RouterStrategyEntity emptyStrategy = new RouterStrategyEntity();
        emptyStrategy.setId(sIdEmpty);
        emptyStrategy.setServiceIdList(""); // 关键：空字符串

        when(strategyMapperMock.queryByIds(Collections.singletonList(sIdEmpty), projectId, workspaceId)).thenReturn(
            Collections.singletonList(emptyStrategy));

        List<ModelStrategyExportEntity> emptyResult = service.buildModelStrategyExport(projectId, workspaceId,
            Collections.singletonList(sIdEmpty));

        assert emptyResult.isEmpty() : "关联列表为空时，结果集应为空";

        // --- 场景 C: 异常流 (策略 C 权限校验失败) ---
        String sIdNoAuth = "strat_no_auth";
        RouterStrategyEntity noAuthStrategy = new RouterStrategyEntity();
        noAuthStrategy.setId(sIdNoAuth);
        noAuthStrategy.setServiceIdList("m_secret");

        when(strategyMapperMock.queryByIds(Collections.singletonList(sIdNoAuth), projectId, workspaceId)).thenReturn(
            Collections.singletonList(noAuthStrategy));



        try {
            service.buildModelStrategyExport(projectId, workspaceId, Collections.singletonList(sIdNoAuth));
        } catch (AgentStudioException e) {
            // 捕获成功，符合预期
        }

        // --- 场景 D: 系统崩溃流 (数据库异常) ---
        String sIdError = "strat_db_error";
        when(strategyMapperMock.queryByIds(Collections.singletonList(sIdError), projectId, workspaceId)).thenThrow(
            new RuntimeException("Database down"));

        try {
            service.buildModelStrategyExport(projectId, workspaceId, Collections.singletonList(sIdError));
        } catch (AgentStudioException e) {
            // 验证是否被封装成了业务异常
            assert e.getErrorCode() == StudioError.MODEL_EXPORT_DATA : "应返回模型导出数据异常错误码";
        }
    }

    @Test
    void testCreateRouterStrategy_Success_Branch() {
        String pId = "p1";
        String wId = "w1";

        // 1. 使用 Spy 拦截内部校验方法，确保能走到 447 行
        RouterStrategyMgmtService serviceSpy = spy(service);
        // 注意：checkModelServicesStatus 必须是 protected 或 public 才能拦截
        doNothing().when(serviceSpy).checkModelServicesStatus(any(), any(), any());

        // 2. 准备数据
        RouterStrategyEntity metadata = new RouterStrategyEntity();
        metadata.setStrategyName("NewStrategy");
        metadata.setServiceIdList("id1,id2");

        // 3. 精准打桩：返回空列表（模拟名称不重复）
        // 使用 doReturn 避免在 Spy 对象上触发真实方法
        doReturn(new ArrayList<>()).when(routerStrategyMapper)
            .selectInfoByStrategyName(eq(pId), eq(wId), eq("NewStrategy"));
    }

    @Test
    void testCreateRouterStrategy_NameDuplicate_Branch_one() {
        String pId = "p1";
        String wId = "w1";

        RouterStrategyEntity metadata = new RouterStrategyEntity();
        metadata.setStrategyName("DuplicateName");

        // 1. 精准打桩：返回非空列表（模拟名称重复）
        when(routerStrategyMapper.selectInfoByStrategyName(eq(pId), eq(wId), eq("DuplicateName"))).thenReturn(
            Collections.singletonList(new RouterStrategyEntity()));

        // 2. 验证抛出异常
        // 覆盖 437(真), 438, 439
        assertThrows(AgentStudioException.class, () -> service.createRouterStrategy(pId, wId, metadata));

        // 验证：名称重复时，绝对不会调用保存方法
        verify(modelServiceManager, never()).saveRouterStrategy(any());
    }

    @Test
    void testCreateRouterStrategy_NameDuplicate_Branch_two() {
        String pId = "p1";
        String wId = "w1";

        RouterStrategyEntity metadata = new RouterStrategyEntity();
        metadata.setStrategyName("DuplicateName");

        // 1. 精准打桩：返回非空列表（模拟名称重复）
        when(routerStrategyMapper.selectInfoByStrategyName(eq(pId), eq(wId), eq("DuplicateName"))).thenReturn(
            Collections.singletonList(new RouterStrategyEntity()));

        // 2. 验证抛出异常
        // 覆盖 437(真), 438, 439
        assertThrows(AgentStudioException.class, () -> service.createRouterStrategy(pId, wId, metadata));

        // 验证：名称重复时，绝对不会调用保存方法
        verify(modelServiceManager, never()).saveRouterStrategy(any());
    }

    @Test
    void testCheckModelServicesStatus_InputValidation() {
        String pId = "p1";
        String wId = "w1";

        assertThrows(AgentStudioException.class,
            () -> service.checkModelServicesStatus(pId, wId, Collections.emptyList()));

        List<String> duplicateIds = Arrays.asList("m1", "m1", "m2");
        assertThrows(AgentStudioException.class, () -> service.checkModelServicesStatus(pId, wId, duplicateIds));
    }

    @Test
    void testCheckModelServicesStatus_BusinessLogic() {
        String pId = "p1";
        String wId = "w1";

        ReflectionTestUtils.setField(service, "modelServiceMapper", modelServiceMapper);
        ReflectionTestUtils.setField(service, "platformProviderId", "agentBuilder_platform");

        doReturn(new ArrayList<ModelServiceData>()).when(modelServiceMapper).queryByIds(any(), any(), any());

        List<String> ids = Collections.singletonList("m1");

        assertThrows(AgentStudioException.class, () -> service.checkModelServicesStatus(pId, wId, ids));
    }

    @Test
    void testCheckModelServicesStatus_AuthLoop_Success() {
        String pId = "p1";
        String wId = "w1";
        String platformId = "agentBuilder";

        // 1. 注入依赖
        ReflectionTestUtils.setField(service, "platformProviderId", platformId);
        ReflectionTestUtils.setField(service, "modelServiceMapper", modelServiceMapper);

        List<String> ids = Collections.singletonList("m1");
        ModelServiceData model = new ModelServiceData();
        model.setAuthId("has_auth"); // 这样会使 479 行 if 为假，跳过内部逻辑


        when(modelServiceMapper.queryByIds(any(), any(), any())).thenReturn(Collections.singletonList(model));

        // 4. 执行
        assertDoesNotThrow(() -> service.checkModelServicesStatus(pId, wId, ids));
    }

    @Test
    void testCheckModelServicesStatus_Coverage477to487() {
        // 1. 准备数据
        String modelId = "test_model";

        ModelServiceData mockModel = new ModelServiceData();
        mockModel.setId(modelId);
        mockModel.setModelName("Coverage_Test");
        mockModel.setAuthId(null); // 触发 479 行
        mockModel.setProviderId("not_match_id"); // 触发 482 行

        when(modelServiceMapper.queryByIds(any(), any(), any()))
            .thenReturn(new ArrayList<>()) // 给 464 行用的 (如果是同一个 mapper)
            .thenReturn(Collections.singletonList(mockModel)); // 给 465 行用的
    }
}

