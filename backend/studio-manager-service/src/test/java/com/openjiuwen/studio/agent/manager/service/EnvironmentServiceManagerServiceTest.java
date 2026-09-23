/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.*;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentManagerEntity;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentVariableEntity;
import com.openjiuwen.studio.agent.manager.service.environment.GlobalSyncAgentOpsStatus;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentManagerMapper;
import com.openjiuwen.studio.agent.manager.mapper.EnvironmentVariableMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.service.EnvironmentClientService;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentCacheUtil;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentServiceManagerService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * EnvironmentServiceManagerService Test
 * Tests for EnvironmentServiceManagerService class after JPA to MyBatis refactoring
 */
@ExtendWith(MockitoExtension.class)
public class EnvironmentServiceManagerServiceTest {

    private static final String TEST_PROJECT_ID = "test_project_id";
    private static final String TEST_WORKSPACE_ID = "default";
    private static final String TEST_TOKEN = "test_x_auth_token";
    private static final String TEST_DOMAIN_ID = "test_domain_id";
    private static final String TEST_USER_NAME = "test_user_name";
    private static final String TEST_CREATOR_ID = "test_user_id";

    @Mock
    private EnvironmentClientService environmentClientService;

    @Mock
    private EnvironmentManagerMapper environmentManagerMapper;

    @Mock
    private EnvironmentVariableMapper environmentVariableMapper;

    @Mock
    private WorkspaceMapper workspaceMapper;

    @Mock
    private EnvironmentCacheUtil environmentCacheUtil;

    @Mock
    private MgObsService obsService;

    @InjectMocks
    private EnvironmentServiceManagerService environmentServiceManagerService;

    private MockedStatic<RequestContextUtils> requestContextUtilsMockedStatic;

    private EnvironmentManagerEntity testEnvironmentEntity;

    @BeforeEach
    void setUp() {
        requestContextUtilsMockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(TEST_PROJECT_ID);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(TEST_WORKSPACE_ID);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(TEST_TOKEN);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(TEST_DOMAIN_ID);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(TEST_USER_NAME);
        requestContextUtilsMockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(TEST_CREATOR_ID);

        testEnvironmentEntity = createTestEnvironmentEntity();
        ReflectionTestUtils.setField(environmentServiceManagerService, "environmentQuota", 5);
        ReflectionTestUtils.setField(environmentServiceManagerService, "environmentVariablesQuota", 1000);
        ReflectionTestUtils.setField(environmentServiceManagerService, "opsCallSwitch", false);
        ReflectionTestUtils.setField(environmentServiceManagerService, "syncCaeStatusQueue",
            Mockito.mock(GlobalSyncAgentOpsStatus.class));
    }

    @AfterEach
    void tearDown() {
        if (requestContextUtilsMockedStatic != null) {
            requestContextUtilsMockedStatic.close();
        }
    }

    private EnvironmentManagerEntity createTestEnvironmentEntity() {
        EnvironmentManagerEntity entity = new EnvironmentManagerEntity();
        entity.setId("test_env_id");
        entity.setName("test_env_name");
        entity.setProjectId(TEST_PROJECT_ID);
        entity.setStatus("ready");
        entity.setIsDefault(false);
        entity.setCreatorId(TEST_CREATOR_ID);
        entity.setUpdaterId(TEST_CREATOR_ID);
        entity.setDomainId(TEST_DOMAIN_ID);
        entity.setDescription("test description");
        entity.setResources("{}");
        entity.setCreatedOn(new Date());
        entity.setUpdatedOn(new Date());
        return entity;
    }

    @Test
    void testQueryEnvironment_Success() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        Environment result = environmentServiceManagerService.queryEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertNotNull(result);
        assertEquals("test_env_name", result.getName());
    }

    @Test
    void testQueryEnvironment_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.queryEnvironment(TEST_PROJECT_ID, "not_exist_id");
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
        assertEquals("1017", exception.getErrorCode().getCode());
    }

    @Test
    void testQueryEnvironmentsList_Success() {
        List<EnvironmentManagerEntity> entities = new ArrayList<>();
        entities.add(testEnvironmentEntity);
        when(environmentManagerMapper.selectByConditionWithPage(null, TEST_PROJECT_ID, 0, 10))
            .thenReturn(entities);
        when(environmentManagerMapper.countByCondition(null, TEST_PROJECT_ID))
            .thenReturn(1);

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(10);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(1, result.getTotal());
    }

    @Test
    void testQueryEnvironmentsList_WithNameFilter() {
        List<EnvironmentManagerEntity> entities = new ArrayList<>();
        entities.add(testEnvironmentEntity);
        when(environmentManagerMapper.selectByConditionWithPage("test", TEST_PROJECT_ID, 0, 10))
            .thenReturn(entities);
        when(environmentManagerMapper.countByCondition("test", TEST_PROJECT_ID))
            .thenReturn(1);

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(10);
        qo.setName("test");

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(1, result.getTotal());
        verify(environmentManagerMapper).selectByConditionWithPage("test", TEST_PROJECT_ID, 0, 10);
        verify(environmentManagerMapper).countByCondition("test", TEST_PROJECT_ID);
    }

    @Test
    void testQueryEnvironmentsList_FilterDefault() {
        testEnvironmentEntity.setIsDefault(true);
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue(TEST_PROJECT_ID))
            .thenReturn(List.of(testEnvironmentEntity));

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(10);
        qo.setIsDefault(true);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(1, result.getTotal());
        assertEquals(Boolean.TRUE, result.getEnvInfo().get(0).isIsDefault());
        // 过滤路径不走分页查询
        Mockito.verify(environmentManagerMapper, Mockito.never())
            .selectAll(anyString(), anyInt(), anyInt());
        Mockito.verify(environmentManagerMapper, Mockito.never())
            .selectByConditionWithPage(any(), anyString(), anyInt(), anyInt());
    }

    @Test
    void testQueryEnvironmentsList_FilterDefaultEmpty() {
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue(TEST_PROJECT_ID))
            .thenReturn(new ArrayList<>());

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setIsDefault(true);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(0, result.getTotal());
        Mockito.verify(environmentManagerMapper, Mockito.never())
            .selectAll(anyString(), anyInt(), anyInt());
        Mockito.verify(environmentManagerMapper, Mockito.never())
            .selectByConditionWithPage(any(), anyString(), anyInt(), anyInt());
    }

    @Test
    void testQueryEnvironmentsList_LimitExceedsMax() {
        List<EnvironmentManagerEntity> entities = new ArrayList<>();
        entities.add(testEnvironmentEntity);
        when(environmentManagerMapper.selectByConditionWithPage(null, TEST_PROJECT_ID, 0, 10))
            .thenReturn(entities);

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(200);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
    }

    @Test
    void testQueryEnvironmentsList_EmptyList() {
        when(environmentManagerMapper.selectByConditionWithPage(null, TEST_PROJECT_ID, 0, 10))
            .thenReturn(new ArrayList<>());
        when(environmentManagerMapper.countByCondition(null, TEST_PROJECT_ID))
            .thenReturn(0);

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(10);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(0, result.getTotal());
    }

    @Test
    void testQueryEnvironmentsList_NegativeOffset() {
        when(environmentManagerMapper.selectByConditionWithPage(null, TEST_PROJECT_ID, 0, 10))
            .thenReturn(new ArrayList<>());

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(-1);
        qo.setLimit(10);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
    }

    @Test
    void testQueryEnvironmentVariables_Success() {
        List<EnvironmentManagerEntity> entities = new ArrayList<>();
        entities.add(testEnvironmentEntity);
        when(environmentManagerMapper.selectAllByStatus("READY", TEST_PROJECT_ID, 0, 10))
            .thenReturn(entities);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id"))
            .thenReturn(null);

        QueryEnvironmentVariablesQo qo = new QueryEnvironmentVariablesQo();
        qo.setWorkspaceId(TEST_WORKSPACE_ID);
        qo.setOffset(0);
        qo.setLimit(10);

        var result = environmentServiceManagerService.queryEnvironmentVariables(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(1, result.getTotal());
        assertNotNull(result.getVariables());
        assertEquals(1, result.getVariables().size());
        // 环境变量 DB 记录为空时 count 为 0、变量列表为空
        assertEquals(0, result.getVariables().get(0).getCount());
        assertEquals(0, result.getVariables().get(0).getVariables().size());
    }

    @Test
    void testQueryEnvironmentVariables_LimitExceedsMax() {
        when(environmentManagerMapper.selectAllByStatus("READY", TEST_PROJECT_ID, 0, 10))
            .thenReturn(new ArrayList<>());

        QueryEnvironmentVariablesQo qo = new QueryEnvironmentVariablesQo();
        qo.setWorkspaceId(TEST_WORKSPACE_ID);
        qo.setOffset(0);
        qo.setLimit(200);

        var result = environmentServiceManagerService.queryEnvironmentVariables(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        // 单页最大 100 时回退为 10，空结果 total 为 0
        assertEquals(0, result.getTotal());
        assertEquals(0, result.getVariables().size());
    }

    @Test
    void testQueryEnvironmentVariablesById_Success() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn(null);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id"))
            .thenReturn(null);

        String result = environmentServiceManagerService.queryEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertEquals("", result);
        // 越权修复：环境查询走 findByIdAndProjectId 而非 findById
        verify(environmentManagerMapper).findByIdAndProjectId("test_env_id", TEST_PROJECT_ID);
        verify(environmentManagerMapper, Mockito.never()).findById(anyString());
    }

    @Test
    void testQueryEnvironmentVariablesById_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        String result = environmentServiceManagerService.queryEnvironmentVariables(
            TEST_PROJECT_ID, "not_exist_id", TEST_WORKSPACE_ID);

        assertEquals("", result);
        // 越权修复：环境查询走 findByIdAndProjectId 而非 findById
        verify(environmentManagerMapper).findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID);
        verify(environmentManagerMapper, Mockito.never()).findById(anyString());
    }

    @Test
    void testShowEnvironmentVariables_Success() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn("[{\"name\":\"KEY\",\"value\":{\"type\":\"string\",\"content\":\"val\",\"secret\":false}}]");

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
        assertNotNull(result.getVariables());
        assertEquals(1, result.getVariables().size());
        assertEquals("KEY", result.getVariables().get(0).getName());
        // 越权修复：环境查询走 findByIdAndProjectId 而非 findById
        verify(environmentManagerMapper).findByIdAndProjectId("test_env_id", TEST_PROJECT_ID);
        verify(environmentManagerMapper, Mockito.never()).findById(anyString());
        // 缓存命中分支不查询 DB
        verify(environmentVariableMapper, Mockito.never())
            .findByProjectIdAndWorkspaceIdAndEnvId(anyString(), anyString(), anyString());
    }

    @Test
    void testShowEnvironmentVariables_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.showEnvironmentVariables(
                TEST_PROJECT_ID, "not_exist_id", TEST_WORKSPACE_ID);
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
        assertEquals("1017", exception.getErrorCode().getCode());
    }

    @Test
    void testDeleteEnvironmentVariables_Success() {
        com.openjiuwen.studio.agent.manager.entity.EnvironmentVariableEntity variableEntity =
            new com.openjiuwen.studio.agent.manager.entity.EnvironmentVariableEntity();
        variableEntity.setId("var_id");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvIdAndId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id", "var_id"))
            .thenReturn(variableEntity);
        when(environmentVariableMapper.deleteById("var_id"))
            .thenReturn(1);
        doNothing().when(environmentCacheUtil).deleteEnvironmentCache(anyString(), anyString());

        String result = environmentServiceManagerService.deleteEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", "var_id", TEST_WORKSPACE_ID);

        assertEquals("success", result);
    }

    @Test
    void testDeleteEnvironmentVariables_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvIdAndId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id", "not_exist_id"))
            .thenReturn(null);

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironmentVariables(
                TEST_PROJECT_ID, "test_env_id", "not_exist_id", TEST_WORKSPACE_ID);
        });
    }

    @Test
    void testDeleteEnvironmentVariables_EnvironmentNotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironmentVariables(
                TEST_PROJECT_ID, "not_exist_id", "var_id", TEST_WORKSPACE_ID);
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
    }

    @Test
    void testCreateEnvironmentVariables_NullBody() {
        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.createEnvironmentVariables(
                TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID, null);
        });
    }

    @Test
    void testCreateEnvironmentVariables_EmptyBody() {
        EnvironmentVariables body = new EnvironmentVariables();
        body.setVariables(new ArrayList<>());

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        String result = environmentServiceManagerService.createEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID, body);

        assertEquals("success", result);
    }

    @Test
    void testCreateEnvironmentVariables_ExceedQuota() {
        ReflectionTestUtils.setField(environmentServiceManagerService, "environmentVariablesQuota", 1);

        EnvironmentVariables body = new EnvironmentVariables();
        List<com.openjiuwen.studio.agent.manager.dto.EnvironmentVariable> variables = new ArrayList<>();
        for (int i = 0; i < 5; i++) {
            com.openjiuwen.studio.agent.manager.dto.EnvironmentVariable variable =
                new com.openjiuwen.studio.agent.manager.dto.EnvironmentVariable();
            variable.setName("test_var_" + i);
            com.openjiuwen.studio.agent.manager.dto.EnvironmentVariableValue variableValue =
                new com.openjiuwen.studio.agent.manager.dto.EnvironmentVariableValue();
            variableValue.setContent("test_value");
            variableValue.setType(com.openjiuwen.studio.agent.manager.dto.EnvironmentVariableValue.TypeEnum.STRING);
            variableValue.setSecret(false);
            variable.setValue(variableValue);
            variables.add(variable);
        }
        body.setVariables(variables);

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.createEnvironmentVariables(
                TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID, body);
        });
    }

    @Test
    void testModifyEnvironmentInfo_Success() {
        ModifyEnvironmentInfoRequestBody request = new ModifyEnvironmentInfoRequestBody();
        request.setDescription("updated description");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentManagerMapper.updateById(any(EnvironmentManagerEntity.class)))
            .thenReturn(1);

        Boolean result = environmentServiceManagerService.modifyEnvironmentInfo(
            TEST_PROJECT_ID, "test_env_id", request);

        assertTrue(result);
    }

    @Test
    void testModifyEnvironmentInfo_NotFound() {
        ModifyEnvironmentInfoRequestBody request = new ModifyEnvironmentInfoRequestBody();
        request.setDescription("updated description");

        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.modifyEnvironmentInfo(
                TEST_PROJECT_ID, "not_exist_id", request);
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
    }

    @Test
    void testIsDefaultEnvironments_Success() {
        EnvironmentManagerEntity defaultEntity = new EnvironmentManagerEntity();
        defaultEntity.setId("default_env_id");
        defaultEntity.setName("default_env");
        defaultEntity.setProjectId(TEST_PROJECT_ID);
        defaultEntity.setStatus("ready");
        defaultEntity.setIsDefault(true);

        testEnvironmentEntity.setIsDefault(false);
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue(TEST_PROJECT_ID))
            .thenReturn(List.of(defaultEntity));
        when(environmentManagerMapper.batchUpdateIsDefaultByIds(any(), anyBoolean(), anyString()))
            .thenReturn(1);
        when(environmentManagerMapper.updateIsDefaultById("test_env_id", true, TEST_CREATOR_ID))
            .thenReturn(1);

        Boolean result = environmentServiceManagerService.isDefaultEnvironments(
            TEST_PROJECT_ID, "test_env_id");

        assertTrue(result);
    }

    @Test
    void testIsDefaultEnvironments_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.isDefaultEnvironments(
                TEST_PROJECT_ID, "not_exist_id");
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
    }

    @Test
    void testIsDefaultEnvironments_StatusNotReady() {
        testEnvironmentEntity.setStatus("creating");
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.isDefaultEnvironments(
                TEST_PROJECT_ID, "test_env_id");
        });
    }

    @Test
    void testValidateEnvironmentId_BlankEnvironment() {
        environmentServiceManagerService.validateEnvironmentId("");

        // 空环境 ID 提前返回，不触发 DB 越权校验
        verify(environmentManagerMapper, Mockito.never()).findByIdAndProjectId(anyString(), anyString());
    }

    @Test
    void testValidateEnvironmentId_JsonString() {
        environmentServiceManagerService.validateEnvironmentId("{\"name\":\"test\"}");

        // JSON 字符串视为工作流引用，提前返回，不触发 DB 越权校验
        verify(environmentManagerMapper, Mockito.never()).findByIdAndProjectId(anyString(), anyString());
    }

    @Test
    void testValidateEnvironmentId_Success() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        environmentServiceManagerService.validateEnvironmentId("test_env_id");
    }

    @Test
    void testValidateEnvironmentId_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.validateEnvironmentId("not_exist_id");
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
    }

    @Test
    void testCreateEnvironmentInfo_NullBody() {
        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.createEnvironmentInfo(TEST_PROJECT_ID, null);
        });
    }

    @Test
    void testDeleteEnvironment_Success() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentClientService.hasDeleteEnvironment(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(true);
        when(environmentManagerMapper.updateStatusAndIsDefaultById(any(), any(), any(), anyBoolean()))
            .thenReturn(1);
        when(environmentVariableMapper.findByProjectIdAndEnvId(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(new ArrayList<>());

        Boolean result = environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertTrue(result);
    }

    @Test
    void testDeleteEnvironment_NotFound() {
        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "not_exist_id");
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
    }

    @Test
    void testDeleteEnvironment_StatusCreating() {
        testEnvironmentEntity.setStatus("creating");
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "test_env_id");
        });
    }

    @Test
    void testDeleteEnvironment_StatusDeleting() {
        testEnvironmentEntity.setStatus("deleting");
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "test_env_id");
        });
    }

    @Test
    void testDeleteEnvironment_IsDefault() {
        testEnvironmentEntity.setIsDefault(true);

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentClientService.hasDeleteEnvironment(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(true);
        when(environmentManagerMapper.updateStatusAndIsDefaultById(any(), any(), any(), anyBoolean()))
            .thenReturn(1);
        when(environmentVariableMapper.findByProjectIdAndEnvId(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(new ArrayList<>());
        when(environmentManagerMapper.findByProjectIdAndIsDefaultFalseAndStatus(TEST_PROJECT_ID, "READY"))
            .thenReturn(new ArrayList<>());

        Boolean result = environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertTrue(result);
    }

    @Test
    void testDeleteEnvironment_IsDefaultWithFallback() {
        testEnvironmentEntity.setIsDefault(true);

        EnvironmentManagerEntity fallbackEntity = new EnvironmentManagerEntity();
        fallbackEntity.setId("fallback_env_id");
        fallbackEntity.setIsDefault(false);
        fallbackEntity.setStatus("READY");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentClientService.hasDeleteEnvironment(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(true);
        when(environmentManagerMapper.updateStatusAndIsDefaultById(any(), any(), any(), anyBoolean()))
            .thenReturn(1);
        when(environmentVariableMapper.findByProjectIdAndEnvId(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(new ArrayList<>());
        when(environmentManagerMapper.findByProjectIdAndIsDefaultFalseAndStatus(TEST_PROJECT_ID, "READY"))
            .thenReturn(List.of(fallbackEntity));
        when(environmentManagerMapper.updateIsDefaultById("fallback_env_id", true, TEST_CREATOR_ID))
            .thenReturn(1);

        Boolean result = environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertTrue(result);
    }

    @Test
    void testQueryEnvironment_WithOpsInfo() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentClientService.queryEnvironmentInfo(any(), any(), any(), any()))
            .thenReturn(new com.openjiuwen.studio.agent.manager.service.environment.model.OpsEnvironmentInfo());

        Environment result = environmentServiceManagerService.queryEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertNotNull(result);
        assertEquals("test_env_name", result.getName());
    }

    @Test
    void testQueryEnvironment_OpsInfoNull() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentClientService.queryEnvironmentInfo(any(), any(), any(), any()))
            .thenReturn(null);

        Environment result = environmentServiceManagerService.queryEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertNotNull(result);
    }

    @Test
    void testUploadEnvironmentVarToObsFileForController_Success() {
        String agentId = "agent123";
        String environmentId = "test_env_id";
        String flowVersion = "v1";

        when(environmentManagerMapper.findByIdAndProjectId(environmentId, TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        EnvironmentVariableEntity variableEntity = new EnvironmentVariableEntity();
        variableEntity.setId("var_id");
        variableEntity.setEnvVariable("[{\"name\":\"KEY\",\"value\":{\"content\":\"val\"}}]");
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, environmentId))
            .thenReturn(variableEntity);

        boolean result = environmentServiceManagerService.uploadEnvironmentVarToObsFileForController(
            TEST_PROJECT_ID, agentId, environmentId, TEST_WORKSPACE_ID, flowVersion);

        assertTrue(result);
        verify(obsService).uploadObsFile(
            eq(agentId), eq("agent123_v1_env"), eq("agent"), eq("[{\"name\":\"KEY\",\"value\":{\"content\":\"val\"}}]"), anyString());
    }

    @Test
    void testUploadEnvironmentVarToObsFileForController_NullVariableEntity() {
        String agentId = "agent456";
        String environmentId = "test_env_id";
        String flowVersion = "v2";

        when(environmentManagerMapper.findByIdAndProjectId(environmentId, TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, environmentId))
            .thenReturn(null);

        boolean result = environmentServiceManagerService.uploadEnvironmentVarToObsFileForController(
            TEST_PROJECT_ID, agentId, environmentId, TEST_WORKSPACE_ID, flowVersion);

        assertTrue(result);
        verify(obsService).uploadObsFile(
            eq(agentId), eq("agent456_v2_env"), eq("agent"), eq(""), anyString());
    }

    @Test
    void testUploadEnvironmentVarToObsFileForController_EnvironmentNotFound() {
        String agentId = "agent789";
        String environmentId = "not_exist_env";
        String flowVersion = "v3";

        when(environmentManagerMapper.findByIdAndProjectId(environmentId, TEST_PROJECT_ID))
            .thenReturn(null);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.uploadEnvironmentVarToObsFileForController(
                TEST_PROJECT_ID, agentId, environmentId, TEST_WORKSPACE_ID, flowVersion);
        });

        assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        assertEquals(HttpStatus.NOT_FOUND, exception.getErrorCode().getHttpStatus());
    }

    /**
     * 用例描述：showEnvironmentVariables 缓存未命中时回源 DB 查询环境变量并返回
     * 预制条件：环境存在（findByIdAndProjectId 返回实体），缓存为空串
     * 输入参数：projectId、环境 ID、workspaceId
     * 预期结果：返回 DB 中的变量列表，verify 环境查询走 findByIdAndProjectId 且缓存为空时查询 DB
     */
    @Test
    void testShowEnvironmentVariablesShouldReadVariablesFromDbWhenCacheEmpty() {
        EnvironmentVariableEntity variableEntity = new EnvironmentVariableEntity();
        variableEntity.setEnvVariable("[{\"name\":\"KEY\",\"value\":{\"type\":\"string\",\"content\":\"val\",\"secret\":false}}]");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn("");
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id"))
            .thenReturn(variableEntity);

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
        assertNotNull(result.getVariables());
        assertEquals(1, result.getVariables().size());
        assertEquals("KEY", result.getVariables().get(0).getName());
        // 越权修复：环境查询走 findByIdAndProjectId 而非 findById
        verify(environmentManagerMapper).findByIdAndProjectId("test_env_id", TEST_PROJECT_ID);
        verify(environmentManagerMapper, Mockito.never()).findById(anyString());
        // 缓存为空回源 DB
        verify(environmentVariableMapper)
            .findByProjectIdAndWorkspaceIdAndEnvId(TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id");
    }

    /**
     * 用例描述：showEnvironmentVariables 缓存为空且 DB 无记录时返回空变量结果
     * 预制条件：环境存在，缓存为空串，DB 中无环境变量记录
     * 输入参数：projectId、环境 ID、workspaceId
     * 预期结果：返回 EnvironmentVariables 空结果，variables 为 null 不抛异常
     */
    @Test
    void testShowEnvironmentVariablesShouldReturnEmptyResultWhenDbEmpty() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn("");
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id"))
            .thenReturn(null);

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
        assertNull(result.getVariables());
        verify(environmentManagerMapper).findByIdAndProjectId("test_env_id", TEST_PROJECT_ID);
    }

    /**
     * 用例描述：showEnvironmentVariables 返回前对密钥类型变量内容做脱敏处理
     * 预制条件：环境存在，缓存中存在 secret=true 的变量
     * 输入参数：projectId、环境 ID、workspaceId，缓存内容含明文密钥
     * 预期结果：密钥变量 content 被替换为 ******，非密钥变量保持不变
     */
    @Test
    void testShowEnvironmentVariablesShouldMaskSecretValue() {
        String cacheContent = "[{\"name\":\"SECRET_KEY\",\"value\":{\"type\":\"string\",\"content\":\"plain-secret\",\"secret\":true}},"
            + "{\"name\":\"PLAIN_KEY\",\"value\":{\"type\":\"string\",\"content\":\"plain-value\",\"secret\":false}}]";

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn(cacheContent);

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
        assertNotNull(result.getVariables());
        assertEquals(2, result.getVariables().size());
        // 密钥变量脱敏
        assertEquals("******", result.getVariables().get(0).getValue().getContent());
        // 非密钥变量内容保持原样
        assertEquals("plain-value", result.getVariables().get(1).getValue().getContent());
    }

    /**
     * 用例描述：queryEnvironment 环境 resources 为 null 时资源元数据解析为空，不抛异常正常返回
     * 预制条件：环境存在且 resources 字段为 null
     * 输入参数：projectId、环境 ID
     * 预期结果：返回 Environment 对象且基本信息正确
     */
    @Test
    void testQueryEnvironmentShouldNotFailWhenResourcesNull() {
        EnvironmentManagerEntity entityWithoutResources = createTestEnvironmentEntity();
        entityWithoutResources.setResources(null);
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(entityWithoutResources);
        when(environmentClientService.queryEnvironmentInfo(any(), any(), any(), any()))
            .thenReturn(null);

        Environment result = environmentServiceManagerService.queryEnvironment(TEST_PROJECT_ID, "test_env_id");

        assertNotNull(result);
        assertEquals("test_env_name", result.getName());
        assertNull(result.getVpcName());
    }

    /**
     * 用例描述：showEnvironmentVariables 缓存内容为空数组时返回空变量列表且不抛异常
     * 预制条件：环境存在，缓存内容为 "[]"
     * 输入参数：projectId、环境 ID、workspaceId
     * 预期结果：返回 variables 为空列表的 EnvironmentVariables
     */
    @Test
    void testShowEnvironmentVariablesShouldReturnEmptyListWhenCacheEmptyArray() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn("[]");

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
        assertNotNull(result.getVariables());
        assertEquals(0, result.getVariables().size());
        // 缓存命中不查 DB
        verify(environmentVariableMapper, Mockito.never())
            .findByProjectIdAndWorkspaceIdAndEnvId(anyString(), anyString(), anyString());
    }

    /**
     * 用例描述：deleteEnvironment 底层 Mapper 更新异常时转换为 ENVIRONMENT_DELETE_FAIL
     * 预制条件：环境存在且状态为 ready，updateStatusAndIsDefaultById 抛异常
     * 输入参数：projectId、环境 ID
     * 预期结果：抛出 AgentStudioException 且错误码为 ENVIRONMENT_DELETE_FAIL
     */
    @Test
    void testDeleteEnvironmentShouldThrowDeleteFailWhenMapperFails() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentClientService.hasDeleteEnvironment(TEST_PROJECT_ID, "test_env_id"))
            .thenReturn(true);
        when(environmentManagerMapper.updateStatusAndIsDefaultById(any(), any(), any(), anyBoolean()))
            .thenThrow(new RuntimeException("db error"));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "test_env_id");
        });

        assertEquals(StudioError.ENVIRONMENT_DELETE_FAIL, exception.getErrorCode());
    }

    /**
     * 用例描述：modifyEnvironmentInfo 底层 Mapper 更新异常时转换为 ENVIRONMENT_MODIFY_FAIL
     * 预制条件：环境存在且状态为 ready，updateById 抛异常
     * 输入参数：projectId、环境 ID、修改请求体
     * 预期结果：抛出 AgentStudioException 且错误码为 ENVIRONMENT_MODIFY_FAIL
     */
    @Test
    void testModifyEnvironmentInfoShouldThrowModifyFailWhenUpdateFails() {
        ModifyEnvironmentInfoRequestBody request = new ModifyEnvironmentInfoRequestBody();
        request.setDescription("updated description");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentManagerMapper.updateById(any(EnvironmentManagerEntity.class)))
            .thenThrow(new RuntimeException("db error"));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.modifyEnvironmentInfo(
                TEST_PROJECT_ID, "test_env_id", request);
        });

        assertEquals(StudioError.ENVIRONMENT_MODIFY_FAIL, exception.getErrorCode());
    }

    /**
     * 用例描述：isDefaultEnvironments 项目内无其他默认环境时直接设置目标环境为默认
     * 预制条件：环境存在且状态 ready，项目内无现有默认环境
     * 输入参数：projectId、环境 ID
     * 预期结果：返回 true 并同步默认环境缓存
     */
    @Test
    void testIsDefaultEnvironmentsShouldSetDefaultWhenNoExistingDefault() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue(TEST_PROJECT_ID))
            .thenReturn(new ArrayList<>());
        when(environmentManagerMapper.updateIsDefaultById("test_env_id", true, TEST_CREATOR_ID))
            .thenReturn(1);

        Boolean result = environmentServiceManagerService.isDefaultEnvironments(
            TEST_PROJECT_ID, "test_env_id");

        assertTrue(result);
        verify(environmentCacheUtil).updateDefaultEnvironmentCache(TEST_PROJECT_ID, "test_env_id");
    }

    /**
     * 用例描述：isDefaultEnvironments 设置默认环境失败时抛出 ENVIRONMENT_DEFAULT_SET_FAIL
     * 预制条件：环境存在且状态 ready，updateIsDefaultById 返回 0
     * 输入参数：projectId、环境 ID
     * 预期结果：抛出 AgentStudioException 且错误码为 ENVIRONMENT_DEFAULT_SET_FAIL
     */
    @Test
    void testIsDefaultEnvironmentsShouldThrowSetFailWhenUpdateFails() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentManagerMapper.findByProjectIdAndIsDefaultTrue(TEST_PROJECT_ID))
            .thenReturn(new ArrayList<>());
        when(environmentManagerMapper.updateIsDefaultById("test_env_id", true, TEST_CREATOR_ID))
            .thenReturn(0);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.isDefaultEnvironments(
                TEST_PROJECT_ID, "test_env_id");
        });

        assertEquals(StudioError.ENVIRONMENT_DEFAULT_SET_FAIL, exception.getErrorCode());
    }

    /**
     * 用例描述：modifyEnvironmentInfo 环境状态非 READY 时抛出 ENVIRONMENT_DEFAULT_NOT_SUPPORT
     * 预制条件：环境存在但状态为 creating（非 ready）
     * 输入参数：projectId、环境 ID、修改请求体
     * 预期结果：抛出 AgentStudioException 且错误码为 ENVIRONMENT_DEFAULT_NOT_SUPPORT
     */
    @Test
    void testModifyEnvironmentInfoShouldThrowNotSupportWhenStatusNotReady() {
        testEnvironmentEntity.setStatus("creating");
        ModifyEnvironmentInfoRequestBody request = new ModifyEnvironmentInfoRequestBody();
        request.setDescription("updated description");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.modifyEnvironmentInfo(
                TEST_PROJECT_ID, "test_env_id", request);
        });

        assertEquals(StudioError.ENVIRONMENT_DEFAULT_NOT_SUPPORT, exception.getErrorCode());
    }

    /**
     * 用例描述：deleteEnvironmentVariables 底层 Mapper 删除异常时转换为 ENVIRONMENT_VARIABLE_DELETE_FAIL
     * 预制条件：环境存在且变量记录存在，deleteById 抛异常
     * 输入参数：projectId、环境 ID、变量 ID、workspaceId
     * 预期结果：抛出 AgentStudioException 且错误码为 ENVIRONMENT_VARIABLE_DELETE_FAIL
     */
    @Test
    void testDeleteEnvironmentVariablesShouldThrowDeleteFailWhenMapperFails() {
        EnvironmentVariableEntity variableEntity = new EnvironmentVariableEntity();
        variableEntity.setId("var_id");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvIdAndId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id", "var_id"))
            .thenReturn(variableEntity);
        when(environmentVariableMapper.deleteById("var_id"))
            .thenThrow(new RuntimeException("db error"));

        AgentStudioException exception = assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironmentVariables(
                TEST_PROJECT_ID, "test_env_id", "var_id", TEST_WORKSPACE_ID);
        });

        assertEquals(StudioError.ENVIRONMENT_VARIABLE_DELETE_FAIL, exception.getErrorCode());
    }

    /**
     * 用例描述：queryEnvironmentVariables(projectId, environmentId, workspaceId) 缓存命中时直接返回缓存值
     * 预制条件：环境存在（findByIdAndProjectId 返回实体），缓存中存在非空变量串
     * 输入参数：projectId、环境 ID、workspaceId
     * 预期结果：返回缓存中的变量串，不查询 DB
     */
    @Test
    void testQueryEnvironmentVariablesByIdShouldReturnCachedValue() {
        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn("[{\"name\":\"KEY\",\"value\":{\"type\":\"string\",\"content\":\"val\",\"secret\":false}}]");

        String result = environmentServiceManagerService.queryEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertEquals("[{\"name\":\"KEY\",\"value\":{\"type\":\"string\",\"content\":\"val\",\"secret\":false}}]", result);
        // 越权修复：环境查询走 findByIdAndProjectId 而非 findById
        verify(environmentManagerMapper).findByIdAndProjectId("test_env_id", TEST_PROJECT_ID);
        verify(environmentManagerMapper, Mockito.never()).findById(anyString());
        verify(environmentVariableMapper, Mockito.never())
            .findByProjectIdAndWorkspaceIdAndEnvId(anyString(), anyString(), anyString());
    }

    /**
     * 用例描述：queryEnvironmentVariables(projectId, environmentId, workspaceId) 缓存未命中时回源 DB 返回变量串
     * 预制条件：环境存在，缓存为空，DB 中存在变量记录
     * 输入参数：projectId、环境 ID、workspaceId
     * 预期结果：返回 DB 中的变量串
     */
    @Test
    void testQueryEnvironmentVariablesByIdShouldReturnDbValue() {
        EnvironmentVariableEntity variableEntity = new EnvironmentVariableEntity();
        variableEntity.setEnvVariable("db-variable-json");

        when(environmentManagerMapper.findByIdAndProjectId("test_env_id", TEST_PROJECT_ID))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn(null);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id"))
            .thenReturn(variableEntity);

        String result = environmentServiceManagerService.queryEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertEquals("db-variable-json", result);
        // 越权修复：环境查询走 findByIdAndProjectId 而非 findById
        verify(environmentManagerMapper).findByIdAndProjectId("test_env_id", TEST_PROJECT_ID);
        verify(environmentManagerMapper, Mockito.never()).findById(anyString());
    }

    /**
     * 用例描述：validateEnvironmentId 在 envType 为 hc 时提前返回不做越权校验
     * 预制条件：envType 字段为 "hc"
     * 输入参数：普通环境 ID 字符串（非 JSON、非空）
     * 预期结果：方法正常返回不抛异常，不触发 DB 查询
     */
    @Test
    void testValidateEnvironmentIdShouldReturnEarlyWhenEnvTypeIsHc() {
        ReflectionTestUtils.setField(environmentServiceManagerService, "envType", "hc");

        environmentServiceManagerService.validateEnvironmentId("plain_env_id");

        verify(environmentManagerMapper, Mockito.never()).findByIdAndProjectId(anyString(), anyString());
    }

    /**
     * 用例描述：validateEnvironmentId 环境 ID 命中工作流名称引用正则（{name= 前缀）时提前返回
     * 预制条件：无（envType 为默认值 null）
     * 输入参数：以 {name= 前缀开头的工作流引用字符串
     * 预期结果：方法正常返回不抛异常，不触发 DB 查询
     */
    @Test
    void testValidateEnvironmentIdShouldReturnEarlyWhenWorkflowNameRegexMatches() {
        environmentServiceManagerService.validateEnvironmentId("{name=test_env}");

        verify(environmentManagerMapper, Mockito.never()).findByIdAndProjectId(anyString(), anyString());
    }
}