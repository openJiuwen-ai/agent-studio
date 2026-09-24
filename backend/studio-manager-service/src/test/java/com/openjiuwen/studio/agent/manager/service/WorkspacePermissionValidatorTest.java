/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * WorkspacePermissionValidator 语义方法 + fail-closed + 管理租户跳过 单测。
 * validateModifyPrivilege 内部依赖 RequestContextHolder(静态)，难纯测；
 * 语义方法 validateByAction(未知 action 抛 IllegalArgumentException)可测。
 */
@ExtendWith(MockitoExtension.class)
class WorkspacePermissionValidatorTest {

    @InjectMocks
    private WorkspacePermissionValidator validator;

    @Mock
    private WorkspaceMemberMapper workspaceMemberMapper;

    @Mock
    private PermissionService permissionService;

    private static final String OP_SVC_PROJECT_ID = "op-tenant-project-id";
    private static final String PROJECT_ID = "biz-project-id";
    private static final String WORKSPACE_ID = "ws-id";
    private static final String CREATOR_USER_ID = "creator-user-id";

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(validator, "opSvcProjectId", OP_SVC_PROJECT_ID);
    }

    @Test
    void validateByAction_UnknownAction_ThrowsIllegalArgument_FailClosed() {
        // 未知 action 应 fail-closed 抛异常，不静默放行
        assertThrows(IllegalArgumentException.class,
            () -> validator.validateAgent(PROJECT_ID, WORKSPACE_ID, CREATOR_USER_ID, "unknown-action", false));
        // 不应调用 validateModifyPrivilege 内部的 permissionService
        verify(permissionService, never()).isCreatorCheckRequired(anyString(), anyString(), anyString());
    }

    @Test
    void validateAgent_KnownAction_DelegatesToValidateModifyPrivilege() {
        // 管理租户直接放行，不进入创建人校验
        validator.validateAgent(OP_SVC_PROJECT_ID, WORKSPACE_ID, CREATOR_USER_ID, "delete", false);
        verify(permissionService, never()).isCreatorCheckRequired(anyString(), anyString(), anyString());
    }

    @Test
    void validateWorkflow_KnownAction_DelegatesToValidateModifyPrivilege() {
        validator.validateWorkflow(OP_SVC_PROJECT_ID, WORKSPACE_ID, CREATOR_USER_ID, "delete", false);
        verify(permissionService, never()).isCreatorCheckRequired(anyString(), anyString(), anyString());
    }

    @Test
    void validateProvider_KnownAction_DelegatesToValidateModifyPrivilege() {
        validator.validateProvider(OP_SVC_PROJECT_ID, WORKSPACE_ID, "creator-user-name", "delete", false);
        verify(permissionService, never()).isCreatorCheckRequired(anyString(), anyString(), anyString());
    }

    @Test
    void validateModelService_KnownAction_DelegatesToValidateModifyPrivilege() {
        validator.validateModelService(OP_SVC_PROJECT_ID, WORKSPACE_ID, "creator-user-name", "delete", false);
        verify(permissionService, never()).isCreatorCheckRequired(anyString(), anyString(), anyString());
    }

    @Test
    void validateModifyPrivilege_OpTenantSkip_AllRolesPass() {
        // 管理租户:任何 action 都放行
        assertDoesNotThrow(() -> validator.validateAgent(OP_SVC_PROJECT_ID, WORKSPACE_ID, "any-creator", "delete", false));
        assertDoesNotThrow(() -> validator.validateAgent(OP_SVC_PROJECT_ID, WORKSPACE_ID, "any-creator", "edit", false));
        assertDoesNotThrow(() -> validator.validateAgent(OP_SVC_PROJECT_ID, WORKSPACE_ID, "any-creator",
            "channel-create", false));
    }

    @Test
    void validateModifyPrivilege_OpTenantSkip_EvenForNonCreator() {
        // 管理租户:非创建者也放行(设计如此)
        assertDoesNotThrow(() -> validator.validateAgent(OP_SVC_PROJECT_ID, WORKSPACE_ID, "other-creator", "delete", false));
    }
}
