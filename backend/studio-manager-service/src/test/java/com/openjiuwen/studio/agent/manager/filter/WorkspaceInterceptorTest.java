/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.filter;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.web.servlet.HandlerMapping;

import java.util.HashMap;
import java.util.Map;

/**
 * WorkspaceInterceptor 系统用户免校验测试
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class WorkspaceInterceptorTest {

    @InjectMocks
    private WorkspaceInterceptor interceptor;

    @Mock
    private WorkspaceMapper workspaceMapper;

    @Mock
    private WorkspaceMemberMapper workSpaceMemberMapper;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    private static final String PROJECT_ID = "proj-001";
    private static final String WORKSPACE_ID = "ws-001";

    @BeforeEach
    void setUp() {
        Map<String, String> pathVariables = new HashMap<>();
        pathVariables.put("project_id", PROJECT_ID);
        when(request.getAttribute(HandlerMapping.URI_TEMPLATE_VARIABLES_ATTRIBUTE)).thenReturn(pathVariables);
        when(request.getParameter("workspace_id")).thenReturn(WORKSPACE_ID);
        when(request.getRequestURI()).thenReturn("/v1/proj-001/agent-manager/agents/import");
        when(request.getMethod()).thenReturn("POST");

        WorkspaceEntity workspaceEntity = new WorkspaceEntity();
        workspaceEntity.setName("test-workspace");
        when(workspaceMapper.getWorkspaceByWorkspaceId(PROJECT_ID, WORKSPACE_ID)).thenReturn(workspaceEntity);
    }

    // 场景：系统用户标记存在时，跳过成员校验和权限校验
    @Test
    void preHandle_systemUserSkip_shouldBypassMemberCheck() throws Exception {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(Boolean.TRUE);

        boolean result = interceptor.preHandle(request, response, null);

        assertTrue(result);
        verify(workSpaceMemberMapper, never()).selectByMemberIdAndWorkspaceId(anyString(), anyString());
    }

    // 场景：无系统用户标记时，执行成员校验，非成员被拒绝
    @Test
    void preHandle_noSystemUserSkip_shouldExecuteMemberCheck() {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(null);
        when(workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(anyString(), anyString())).thenReturn(null);

        assertThrows(Exception.class, () -> interceptor.preHandle(request, response, null));
    }

    // 场景：系统用户标记为 false 时，不跳过校验
    @Test
    void preHandle_systemUserSkipFalse_shouldExecuteMemberCheck() {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(Boolean.FALSE);
        when(workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(anyString(), anyString())).thenReturn(null);

        assertThrows(Exception.class, () -> interceptor.preHandle(request, response, null));
    }

    // 场景：workspaceId 格式校验不因系统用户标记而跳过
    @Test
    void preHandle_invalidWorkspaceId_shouldFailEvenWithSystemUserSkip() {
        when(request.getParameter("workspace_id")).thenReturn("invalid!!!");
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(Boolean.TRUE);

        assertThrows(Exception.class, () -> interceptor.preHandle(request, response, null));
    }

    // 场景：空间不存在时不因系统用户标记而跳过
    @Test
    void preHandle_workspaceNotExist_shouldFailEvenWithSystemUserSkip() {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(Boolean.TRUE);
        when(workspaceMapper.getWorkspaceByWorkspaceId(PROJECT_ID, WORKSPACE_ID)).thenReturn(null);

        assertThrows(Exception.class, () -> interceptor.preHandle(request, response, null));
    }
}
