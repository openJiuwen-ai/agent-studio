/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.environment;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.Environment;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentInfoRequest;
import com.openjiuwen.studio.agent.manager.dto.ModifyEnvironmentInfoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentInstances;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariable;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariableValue;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariables;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariablesExport;
import com.openjiuwen.studio.agent.manager.dto.EnvironmentVariablesResp;
import com.openjiuwen.studio.agent.manager.dto.Environments;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentInstancesQo;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentVariablesQo;
import com.openjiuwen.studio.agent.manager.dto.QueryEnvironmentsListQo;
import com.openjiuwen.studio.agent.manager.dto.ValidationVariablesImport;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentManagerEntity;
import com.openjiuwen.studio.agent.manager.entity.EnvironmentVariableEntity;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.VpcClient;
import com.openjiuwen.studio.agent.manager.rce.models.IamUserInfo2;
import com.openjiuwen.studio.agent.manager.rce.models.IamUserInfoResp;
import com.openjiuwen.studio.agent.manager.rce.service.ClientService;
import com.openjiuwen.studio.agent.manager.rce.service.EnvironmentClientService;
import com.openjiuwen.studio.agent.manager.service.environment.model.EnvironmentVariablesExportAndImportDetail;
import com.openjiuwen.studio.agent.manager.service.environment.model.OpsEnvironmentInstance;
import com.openjiuwen.studio.agent.manager.service.environment.model.OpsEnvironmentInstances;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;

import com.openjiuwen.studio.prompt.engineering.service.PromptObsService;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * 功能描述
 *
 */
@Transactional
public class EnvironmentServiceManagerServiceTest extends BaseTest {
    @Autowired
    private EnvironmentClientService environmentClientService;

    @MockitoBean
    private ClientService clientService;

    @MockitoBean(name = "vpcClient")
    private VpcClient vpcClient;

    @MockitoBean(name = "mgObsService")
    private MgObsService mgObsService;

    @MockitoBean(name = "promptObsService")
    private PromptObsService promptObsService;

    @Autowired
    private EnvironmentServiceManagerService environmentServiceManagerService;

    private static MockedStatic<RequestContextUtils> mockedStatic;

    private AutoCloseable mockitoCloseable;

    @BeforeAll
    public static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = Mockito.mockStatic(RequestContextUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestProjectId).thenReturn(Constants.TEST_PROJECT_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(Constants.TEST_WORKSPACE_ID);
        mockedStatic.when(RequestContextUtils::getRequestAuthToken).thenReturn(Constants.TEST_TOKEN);
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_PROJECT_ID2);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_USER_NAME);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn("test_copy_user_id");
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testDeleteEnvironment() {
        IamUserInfoResp iamUserInfoResp = new IamUserInfoResp();
        IamUserInfo2 iamUserInfo = new IamUserInfo2();
        iamUserInfo.setDomainOwner(true);
        iamUserInfoResp.setUser(iamUserInfo);
        when(clientService.queryIamUserDetail(anyString(), anyString())).thenReturn(ResponseEntity.ofNullable(JSONObject.from(iamUserInfoResp)));
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.deleteEnvironment(Constants.TEST_PROJECT_ID, "test_env_not_exist"));
        boolean result = environmentServiceManagerService.deleteEnvironment(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d");
        Assertions.assertTrue(result);

        boolean result2 = environmentServiceManagerService.deleteEnvironment(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c28");
        Assertions.assertTrue(result2);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testDeleteEnvironment2() {
        IamUserInfoResp iamUserInfoResp = new IamUserInfoResp();
        IamUserInfo2 iamUserInfo = new IamUserInfo2();
        iamUserInfo.setDomainOwner(true);
        iamUserInfoResp.setUser(iamUserInfo);
        when(clientService.queryIamUserDetail(anyString(), anyString())).thenReturn(ResponseEntity.ofNullable(JSONObject.from(iamUserInfoResp)));
        boolean result2 = environmentServiceManagerService.deleteEnvironment(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c28");
        Assertions.assertTrue(result2);

        boolean result3 = environmentServiceManagerService.deleteEnvironment(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c26");
        Assertions.assertTrue(result3);
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.deleteEnvironment(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c21"));
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testIsDefaultEnvironments() {
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.isDefaultEnvironments(Constants.TEST_PROJECT_ID, "test_env_not_exist"));

        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.isDefaultEnvironments(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c21"));
        boolean result = environmentServiceManagerService.isDefaultEnvironments(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d");
        Assertions.assertTrue(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testModifyEnvironmentInfo() {
        ModifyEnvironmentInfoRequestBody request = new ModifyEnvironmentInfoRequestBody();
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.modifyEnvironmentInfo(Constants.TEST_PROJECT_ID, "test_env_not_exist", request));
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.modifyEnvironmentInfo(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c21", request));
        request.setDescription("test");
        boolean result = environmentServiceManagerService.modifyEnvironmentInfo(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d", request);
        Assertions.assertTrue(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testQueryEnvironment() {
        // 越权修复：环境查询走 findByIdAndProjectId，环境不存在时抛 ENVIRONMENT_NOT_EXIST
        AgentStudioException exception = Assertions.assertThrows(AgentStudioException.class,
            () -> environmentServiceManagerService.queryEnvironment(Constants.TEST_PROJECT_ID, "test_env_not_exist"));
        Assertions.assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        Environment result3 = environmentServiceManagerService.queryEnvironment(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d");
        Assertions.assertNotNull(result3);
        Assertions.assertEquals("test_environment", result3.getName());
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testQueryEnvironmentsList() {
        QueryEnvironmentsListQo queryEnvironmentsListQo = new QueryEnvironmentsListQo();
        queryEnvironmentsListQo.setLimit(200);
        queryEnvironmentsListQo.setOffset(-1);
        Environments result = environmentServiceManagerService.queryEnvironmentsList(Constants.TEST_PROJECT_ID, queryEnvironmentsListQo);
        Assertions.assertNotNull(result);
        // 夹具共 10 条环境，total 应为真实总数而非当前页条数
        Assertions.assertEquals(10, result.getTotal());
        Assertions.assertEquals(10, result.getEnvInfo().size());
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testQueryEnvironmentsListWithNameFilter() {
        // 精确前缀过滤：3 条 test_environment2
        QueryEnvironmentsListQo qo = new QueryEnvironmentsListQo();
        qo.setLimit(10);
        qo.setOffset(0);
        qo.setName("test_environment2");
        Environments result = environmentServiceManagerService.queryEnvironmentsList(Constants.TEST_PROJECT_ID, qo);
        Assertions.assertEquals(3, result.getTotal());
        Assertions.assertEquals(3, result.getEnvInfo().size());
        result.getEnvInfo().forEach(env -> Assertions.assertEquals("test_environment2", env.getName()));

        // 模糊匹配：片段 "environment2" 同样命中 3 条
        qo.setName("environment2");
        Environments fuzzyResult = environmentServiceManagerService.queryEnvironmentsList(Constants.TEST_PROJECT_ID, qo);
        Assertions.assertEquals(3, fuzzyResult.getTotal());

        // 无匹配：空列表 + total 0
        qo.setName("no-such-env");
        Environments emptyResult = environmentServiceManagerService.queryEnvironmentsList(Constants.TEST_PROJECT_ID, qo);
        Assertions.assertEquals(0, emptyResult.getTotal());
        Assertions.assertTrue(emptyResult.getEnvInfo() == null || emptyResult.getEnvInfo().isEmpty());
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testQueryEnvironmentInstances() {
        QueryEnvironmentInstancesQo queryEnvironmentInstancesQo = new QueryEnvironmentInstancesQo();
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.queryEnvironmentInstances(Constants.TEST_PROJECT_ID, "test_env_not_exist", queryEnvironmentInstancesQo));

        OpsEnvironmentInstance opsEnvironmentInstance = new OpsEnvironmentInstance();
        opsEnvironmentInstance.setDeployName("test_deploy_name");
        opsEnvironmentInstance.setAgentName("test_agent_name");
        OpsEnvironmentInstances opsEnvironmentInstances = new OpsEnvironmentInstances();
        opsEnvironmentInstances.setItems(List.of(opsEnvironmentInstance));
        EnvironmentInstances result = environmentServiceManagerService.queryEnvironmentInstances(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d", queryEnvironmentInstancesQo);
        Assertions.assertNotNull(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testQueryEnvironmentVariables() {
        QueryEnvironmentVariablesQo qo = new QueryEnvironmentVariablesQo();
        qo.setWorkspaceId(Constants.TEST_WORKSPACE_ID);
        qo.setLimit(1000);
        qo.setOffset(2000);
        EnvironmentVariablesResp result = environmentServiceManagerService.queryEnvironmentVariables(Constants.TEST_PROJECT_ID, qo);

        String result2 = environmentServiceManagerService.queryEnvironmentVariables(Constants.TEST_PROJECT_ID, "test_env_not_exist", Constants.TEST_WORKSPACE_ID);
        Assertions.assertEquals(result2, "");
        String result3 = environmentServiceManagerService.queryEnvironmentVariables(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d", Constants.TEST_WORKSPACE_ID);
        Assertions.assertEquals(result3, "");

    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testCreateEnvironmentVariables() {
        EnvironmentVariables body = new EnvironmentVariables();
        EnvironmentVariable variable = new EnvironmentVariable();
        variable.setName("test");
        EnvironmentVariableValue variableValue = new EnvironmentVariableValue();
        variableValue.setContent("123");
        variableValue.setType(EnvironmentVariableValue.TypeEnum.STRING);
        variableValue.setSecret(false);
        variable.setValue(variableValue);
        body.setVariables(List.of(variable));
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.createEnvironmentVariables(Constants.TEST_PROJECT_ID, "test_env_not_exist", Constants.TEST_WORKSPACE_ID, body));
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.createEnvironmentVariables(Constants.TEST_PROJECT_ID, "test_env_not_exist", Constants.TEST_WORKSPACE_ID, null));

        String result = environmentServiceManagerService.createEnvironmentVariables(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666918c2d", Constants.TEST_WORKSPACE_ID, body);
        Assertions.assertEquals(result, "success");

        EnvironmentVariables body2 = new EnvironmentVariables();
        EnvironmentVariable variable2 = new EnvironmentVariable();
        variable2.setName("test");
        EnvironmentVariableValue variableValue2 = new EnvironmentVariableValue();
        variableValue2.setContent("123");
        variableValue2.setType(EnvironmentVariableValue.TypeEnum.STRING);
        variableValue2.setSecret(false);
        variable2.setValue(variableValue);
        body2.setVariables(List.of(variable));
        String result2 = environmentServiceManagerService.createEnvironmentVariables(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c23", Constants.TEST_WORKSPACE_ID, body2);
        Assertions.assertEquals(result2, "success");
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    public void testDeleteEnvironmentVariables() {
        Assertions.assertThrows(AgentStudioException.class, () -> environmentServiceManagerService.deleteEnvironmentVariables(Constants.TEST_PROJECT_ID, "test_env_not_exist",
            "var_id", Constants.TEST_WORKSPACE_ID));
        String result = environmentServiceManagerService.deleteEnvironmentVariables(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c23",
            "e20e0bbe-42bb-48ef-861b-341cf81e5e58", Constants.TEST_WORKSPACE_ID);
        Assertions.assertEquals(result, "success");
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testUploadEnvironmentVarToObsFile() {
        EnvironmentManagerEntity entity = new EnvironmentManagerEntity();
        EnvironmentVariableEntity variableEntity = new EnvironmentVariableEntity();
        variableEntity.setEnvVariable("{}");
        when(mgObsService.uploadObsFile(anyString(), anyString(), anyString(), anyString(), any())).thenReturn("path");
        boolean result = this.environmentServiceManagerService.uploadEnvironmentVarToObsFile(Constants.TEST_PROJECT_ID, "flow_id", "9c7d551a-0644-4ac2-be48-6d5666928c25", Constants.TEST_WORKSPACE_ID, "version");
        Assertions.assertTrue(result);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testShowEnvironmentVariables() {
        // 越权修复：环境查询走 findByIdAndProjectId，环境不存在时抛 ENVIRONMENT_NOT_EXIST
        AgentStudioException exception = Assertions.assertThrows(AgentStudioException.class,
            () -> this.environmentServiceManagerService.showEnvironmentVariables(Constants.TEST_PROJECT_ID, "test_env_not_exist", Constants.TEST_WORKSPACE_ID));
        Assertions.assertEquals(StudioError.ENVIRONMENT_NOT_EXIST, exception.getErrorCode());
        EnvironmentVariables result2 = this.environmentServiceManagerService.showEnvironmentVariables(Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c25", Constants.TEST_WORKSPACE_ID);
        Assertions.assertNotNull(result2);
        Assertions.assertNotNull(result2.getVariables());
        Assertions.assertEquals(2, result2.getVariables().size());
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testValidateEnvironmentId() {
        Assertions.assertDoesNotThrow(() -> this.environmentServiceManagerService.validateEnvironmentId(""));
        Assertions.assertDoesNotThrow(
            () -> this.environmentServiceManagerService.validateEnvironmentId("9c7d551a-0644-4ac2-be48-6d5666928c27"));
        Assertions.assertDoesNotThrow(
            () -> this.environmentServiceManagerService.validateEnvironmentId("{\"name\":\"\"}"));
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testExportEnvironmentVariable() {
        Assertions.assertThrows(AgentStudioException.class, () -> this.environmentServiceManagerService.exportEnvironmentVariable(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, new EnvironmentVariablesExport()));
        EnvironmentVariablesExport environmentVariablesExport = new EnvironmentVariablesExport();
        environmentVariablesExport.setEnvironmentId(List.of("123"));
        Assertions.assertThrows(AgentStudioException.class, () -> this.environmentServiceManagerService.exportEnvironmentVariable("test_project_id_not_exist", Constants.TEST_WORKSPACE_ID, environmentVariablesExport));
        Assertions.assertThrows(AgentStudioException.class, () -> this.environmentServiceManagerService.exportEnvironmentVariable(Constants.TEST_PROJECT_ID, Constants.TEST_WORKSPACE_ID, environmentVariablesExport));
        environmentVariablesExport.setEnvironmentId(List.of("9c7d551a-0644-4ac2-be48-6d5666928c22"));
        Resource resource = this.environmentServiceManagerService.exportEnvironmentVariable(Constants.TEST_PROJECT_ID,
            Constants.TEST_WORKSPACE_ID, environmentVariablesExport);
        Assertions.assertNotNull(resource);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testImportEnvironmentVariable() {
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_ENVIRONMENT_EXPORT.getBytes()  // 文件内容
        );
        boolean importRsp = this.environmentServiceManagerService.importEnvironmentVariable(
            Constants.TEST_WORKSPACE_ID, Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c28",
            List.of("test_a", "test_a"), file);
        Assertions.assertTrue(importRsp);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testEnvironmentVariableImportFileValidation() {
        MockMultipartFile file = new MockMultipartFile("file",  // 参数名
            "test.jsonl",  // 原始文件名
            "text/plain",  // MIME类型
            Constants.TEST_ENVIRONMENT_EXPORT.getBytes()  // 文件内容
        );
        ValidationVariablesImport importRsp = this.environmentServiceManagerService.environmentVariableImportFileValidation(
            Constants.TEST_WORKSPACE_ID, Constants.TEST_PROJECT_ID, "9c7d551a-0644-4ac2-be48-6d5666928c28", file);
        Assertions.assertNotNull(importRsp);
    }

    @Test
    @Sql(scripts = {"classpath:sql/environment_manager_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void testResolveEnvironmentVariables() {
        EnvironmentVariablesExportAndImportDetail importDetail = new EnvironmentVariablesExportAndImportDetail();
        importDetail.setEnvironmentId("test-env-id");
        Assertions.assertThrows(AgentStudioException.class, () -> this.environmentServiceManagerService.resolveEnvironmentVariables(Constants.TEST_PROJECT_ID, importDetail, "test-env-id"));

        // 测试导入的环境变量为空的场景
        Assertions.assertThrows(AgentStudioException.class, () -> this.environmentServiceManagerService.resolveEnvironmentVariables(Constants.TEST_PROJECT_ID, new EnvironmentVariablesExportAndImportDetail(), "9c7d551a-0644-4ac2-be48-6d5666928c22"));

        EnvironmentVariableValue variableValue = new EnvironmentVariableValue();
        variableValue.setType(EnvironmentVariableValue.TypeEnum.STRING);
        variableValue.setContent("test-vari-a");
        variableValue.setSecret(false);
        EnvironmentVariable variable = new EnvironmentVariable();
        variable.setName("a");
        variable.setValue(variableValue);

        // 测试当前导入的环境下没有环境变量的场景
        importDetail.setEnvironmentId("9c7d551a-0644-4ac2-be48-6d5666928c22");
        importDetail.setEnvironmentVariables(List.of(variable));
        ValidationVariablesImport result3 = this.environmentServiceManagerService.resolveEnvironmentVariables(Constants.TEST_PROJECT_ID, importDetail, "9c7d551a-0644-4ac2-be48-6d5666928c22");
        Assertions.assertTrue(result3.isResult());

        // 测试当前环境下环境变量存在且为空的场景
        EnvironmentVariablesExportAndImportDetail importDetail3 = new EnvironmentVariablesExportAndImportDetail();
        importDetail3.setEnvironmentId("9c7d551a-0644-4ac2-be48-6d5666928c29");
        importDetail3.setEnvironmentVariables(List.of(variable));
        ValidationVariablesImport result4 = this.environmentServiceManagerService.resolveEnvironmentVariables(Constants.TEST_PROJECT_ID, importDetail3, "9c7d551a-0644-4ac2-be48-6d5666928c29");
        Assertions.assertTrue(result4.isResult());

        // 测试当前环境下环境变量存在且不为空的场景
        EnvironmentVariablesExportAndImportDetail importDetail4 = new EnvironmentVariablesExportAndImportDetail();
        importDetail4.setEnvironmentId("9c7d551a-0644-4ac2-be48-6d5666928c28");
        importDetail4.setEnvironmentVariables(List.of(variable));
        ValidationVariablesImport result5 = this.environmentServiceManagerService.resolveEnvironmentVariables(Constants.TEST_PROJECT_ID, importDetail4, "9c7d551a-0644-4ac2-be48-6d5666928c28");
        Assertions.assertTrue(result5.isResult());
    }
}

