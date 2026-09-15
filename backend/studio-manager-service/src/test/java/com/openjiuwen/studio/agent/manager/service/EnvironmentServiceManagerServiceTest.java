/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

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

        Environment result = environmentServiceManagerService.queryEnvironment(TEST_PROJECT_ID, "not_exist_id");

        assertNotNull(result);
    }

    @Test
    void testQueryEnvironmentsList_Success() {
        List<EnvironmentManagerEntity> entities = new ArrayList<>();
        entities.add(testEnvironmentEntity);
        when(environmentManagerMapper.selectAll(TEST_PROJECT_ID, 0, 10))
            .thenReturn(entities);

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(10);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(1, result.getTotal());
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
    }

    @Test
    void testQueryEnvironmentsList_LimitExceedsMax() {
        List<EnvironmentManagerEntity> entities = new ArrayList<>();
        entities.add(testEnvironmentEntity);
        when(environmentManagerMapper.selectAll(TEST_PROJECT_ID, 0, 10))
            .thenReturn(entities);

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(200);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
    }

    @Test
    void testQueryEnvironmentsList_EmptyList() {
        when(environmentManagerMapper.selectAll(TEST_PROJECT_ID, 0, 10))
            .thenReturn(new ArrayList<>());

        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setOffset(0);
        qo.setLimit(10);

        Environments result = environmentServiceManagerService.queryEnvironmentsList(TEST_PROJECT_ID, qo);

        assertNotNull(result);
        assertEquals(0, result.getTotal());
    }

    @Test
    void testQueryEnvironmentsList_NegativeOffset() {
        when(environmentManagerMapper.selectAll(TEST_PROJECT_ID, 0, 10))
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
    }

    @Test
    void testQueryEnvironmentVariablesById_Success() {
        when(environmentManagerMapper.findById("test_env_id"))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn(null);
        when(environmentVariableMapper.findByProjectIdAndWorkspaceIdAndEnvId(
            TEST_PROJECT_ID, TEST_WORKSPACE_ID, "test_env_id"))
            .thenReturn(null);

        String result = environmentServiceManagerService.queryEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertEquals("", result);
    }

    @Test
    void testQueryEnvironmentVariablesById_NotFound() {
        when(environmentManagerMapper.findById("not_exist_id"))
            .thenReturn(null);

        String result = environmentServiceManagerService.queryEnvironmentVariables(
            TEST_PROJECT_ID, "not_exist_id", TEST_WORKSPACE_ID);

        assertEquals("", result);
    }

    @Test
    void testShowEnvironmentVariables_Success() {
        when(environmentManagerMapper.findById("test_env_id"))
            .thenReturn(testEnvironmentEntity);
        when(environmentCacheUtil.getEnvironmentCache("test_env_id", TEST_WORKSPACE_ID))
            .thenReturn("[]");

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "test_env_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
    }

    @Test
    void testShowEnvironmentVariables_NotFound() {
        when(environmentManagerMapper.findById("not_exist_id"))
            .thenReturn(null);

        var result = environmentServiceManagerService.showEnvironmentVariables(
            TEST_PROJECT_ID, "not_exist_id", TEST_WORKSPACE_ID);

        assertNotNull(result);
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

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironmentVariables(
                TEST_PROJECT_ID, "not_exist_id", "var_id", TEST_WORKSPACE_ID);
        });
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
        EnvironmentInfoRequest request = new EnvironmentInfoRequest();
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
        EnvironmentInfoRequest request = new EnvironmentInfoRequest();
        request.setDescription("updated description");

        when(environmentManagerMapper.findByIdAndProjectId("not_exist_id", TEST_PROJECT_ID))
            .thenReturn(null);

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.modifyEnvironmentInfo(
                TEST_PROJECT_ID, "not_exist_id", request);
        });
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

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.isDefaultEnvironments(
                TEST_PROJECT_ID, "not_exist_id");
        });
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
    }

    @Test
    void testValidateEnvironmentId_JsonString() {
        environmentServiceManagerService.validateEnvironmentId("{\"name\":\"test\"}");
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

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.validateEnvironmentId("not_exist_id");
        });
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

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.deleteEnvironment(TEST_PROJECT_ID, "not_exist_id");
        });
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

        assertThrows(AgentStudioException.class, () -> {
            environmentServiceManagerService.uploadEnvironmentVarToObsFileForController(
                TEST_PROJECT_ID, agentId, environmentId, TEST_WORKSPACE_ID, flowVersion);
        });
    }
}