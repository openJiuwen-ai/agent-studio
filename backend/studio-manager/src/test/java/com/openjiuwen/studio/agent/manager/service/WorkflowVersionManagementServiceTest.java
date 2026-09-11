/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mockStatic;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.RequestHeaderHolderUtils;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteVersionFailedInfo;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteVersionsRequestBody;
import com.openjiuwen.studio.agent.manager.dto.BatchDeleteVersionsResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListWorkflowVersionReferencesQo;
import com.openjiuwen.studio.agent.manager.dto.VersionReference;
import com.openjiuwen.studio.agent.manager.dto.VersionReferenceListRsp;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 工作流版本引用查询与批量删除测试
 */
@Transactional
class WorkflowVersionManagementServiceTest extends BaseTest {
    private static MockedStatic<RequestContextUtils> mockedStatic;

    private static MockedStatic<RequestHeaderHolderUtils> mockedHeaderStatic;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MgObsService mgObsService;

    @Autowired
    private WorkflowManagementService workflowManagementService;

    @BeforeAll
    static void init() {
        RequestContextUtils.setRequestAuthTokenAndProjectId(Constants.TEST_TOKEN, Constants.TEST_PROJECT_ID);
        mockedStatic = mockStatic(RequestContextUtils.class);
        mockedHeaderStatic = mockStatic(RequestHeaderHolderUtils.class);
        mockedStatic.when(RequestContextUtils::getRequestUserName).thenReturn(Constants.TEST_CREATOR);
        mockedStatic.when(RequestContextUtils::getRequestUserId).thenReturn(Constants.TEST_CREATOR_ID);
        mockedStatic.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("default");
        mockedStatic.when(RequestContextUtils::getRequestUserDomainId).thenReturn(Constants.TEST_DOMAIN_ID);
        mockedHeaderStatic.when(RequestHeaderHolderUtils::getRequestLanguage).thenReturn("zh-cn");
    }

    @AfterAll
    static void end() {
        mockedStatic.close();
        mockedHeaderStatic.close();
    }

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(workflowManagementService, "obsService", mgObsService);
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/workflow_setup_db.sql",
        "classpath:sql/version_setup_db.sql", "classpath:sql/version_reference_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_list_workflow_version_references() {
        // 未指定版本号：返回该工作流全部版本及各自引用数量
        VersionReferenceListRsp referenceListRsp = workflowManagementService.listWorkflowVersionReferences(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID,
            new ListWorkflowVersionReferencesQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID));
        assertNotNull(referenceListRsp);
        Map<String, VersionReference> referenceMap = referenceListRsp.getVersionReferences().stream()
            .collect(Collectors.toMap(VersionReference::getVersionId, Function.identity()));
        assertEquals(2, referenceMap.size());
        // test_version_id2：被本空间agent引用1条
        VersionReference firstReference = referenceMap.get("test_version_id2");
        assertEquals(1L, firstReference.getReferenceCount());
        assertFalse(firstReference.getIsShared());
        assertFalse(firstReference.getIsLatest());
        // test_version_id3：被本空间workflow引用1条，为最新版本且已共享到资产广场
        VersionReference secondReference = referenceMap.get("test_version_id3");
        assertEquals(1L, secondReference.getReferenceCount());
        assertTrue(secondReference.getIsShared());
        assertTrue(secondReference.getIsLatest());

        // 指定版本号：仅返回该版本
        VersionReferenceListRsp filteredRsp = workflowManagementService.listWorkflowVersionReferences(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID,
            new ListWorkflowVersionReferencesQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID)
                .setVersionId("test_version_id2"));
        assertEquals(1, filteredRsp.getVersionReferences().size());
        assertEquals("test_version_id2", filteredRsp.getVersionReferences().get(0).getVersionId());
        assertEquals(1L, filteredRsp.getVersionReferences().get(0).getReferenceCount());

        // workspace下不存在该工作流时抛出异常，防止横向越权
        assertThrows(AgentStudioException.class, () -> workflowManagementService.listWorkflowVersionReferences(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID,
            new ListWorkflowVersionReferencesQo().setWorkspaceId("other_workspace")));

        // 无版本的工作流：返回空列表
        VersionReferenceListRsp emptyRsp = workflowManagementService.listWorkflowVersionReferences(
            Constants.TEST_PROJECT_ID, "test_code_interpreter_workflow_id",
            new ListWorkflowVersionReferencesQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID));
        assertTrue(emptyRsp.getVersionReferences().isEmpty());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/workflow_setup_db.sql",
        "classpath:sql/version_setup_db.sql", "classpath:sql/version_reference_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_batch_delete_workflow_versions_partial_success() {
        BatchDeleteVersionsRequestBody body = new BatchDeleteVersionsRequestBody()
            .setVersionIds(List.of("test_version_id2", "test_version_id3", "not_exist_version_id"));
        BatchDeleteVersionsResponseBody responseBody = workflowManagementService.batchDeleteWorkflowVersions(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID, Constants.TEST_WORKSPACE_ID, body);

        // 部分成功：正常版本删除成功，已共享版本与不存在版本进failed
        assertEquals(3, responseBody.getTotalCount());
        assertEquals(1, responseBody.getDeletedCount());
        assertEquals(List.of("test_version_id2"), responseBody.getSuccess());
        Map<String, BatchDeleteVersionFailedInfo> failedMap = responseBody.getFailed().stream()
            .collect(Collectors.toMap(BatchDeleteVersionFailedInfo::getVersionId, Function.identity()));
        assertEquals(2, failedMap.size());
        assertEquals(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY.name(),
            failedMap.get("test_version_id3").getErrorCode());
        assertNotNull(failedMap.get("not_exist_version_id").getErrorCode());

        // 删除成功的版本已从版本引用查询中移除，共享版本保留
        VersionReferenceListRsp referenceListRsp = workflowManagementService.listWorkflowVersionReferences(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID,
            new ListWorkflowVersionReferencesQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID));
        assertEquals(1, referenceListRsp.getVersionReferences().size());
        assertEquals("test_version_id3", referenceListRsp.getVersionReferences().get(0).getVersionId());
    }

    @Test
    @Sql(scripts = {"classpath:sql/agent_setup_db.sql", "classpath:sql/workflow_setup_db.sql",
        "classpath:sql/version_setup_db.sql", "classpath:sql/version_reference_setup_db.sql"},
        executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
    void test_batch_delete_workflow_versions_shared_only() {
        // 仅删除已共享版本：全部进failed，版本列表不变
        BatchDeleteVersionsRequestBody body = new BatchDeleteVersionsRequestBody()
            .setVersionIds(List.of("test_version_id3"));
        BatchDeleteVersionsResponseBody responseBody = workflowManagementService.batchDeleteWorkflowVersions(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID, Constants.TEST_WORKSPACE_ID, body);

        assertEquals(1, responseBody.getTotalCount());
        assertEquals(0, responseBody.getDeletedCount());
        assertTrue(responseBody.getSuccess().isEmpty());
        assertEquals(1, responseBody.getFailed().size());
        assertEquals(StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY.name(),
            responseBody.getFailed().get(0).getErrorCode());

        VersionReferenceListRsp referenceListRsp = workflowManagementService.listWorkflowVersionReferences(
            Constants.TEST_PROJECT_ID, Constants.TEST_WORKFLOW_ID,
            new ListWorkflowVersionReferencesQo().setWorkspaceId(Constants.TEST_WORKSPACE_ID));
        assertEquals(2, referenceListRsp.getVersionReferences().size());
    }
}
