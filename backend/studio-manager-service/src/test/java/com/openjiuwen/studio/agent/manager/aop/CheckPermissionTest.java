/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.aop;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;
import com.openjiuwen.studio.agent.manager.service.PermissionService;

import org.aspectj.lang.JoinPoint;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import jakarta.servlet.http.HttpServletRequest;

/**
 * CheckPermission 系统用户免校验测试
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class CheckPermissionTest {

    @InjectMocks
    private CheckPermission checkPermission;

    @Mock
    private WorkspaceMemberMapper workSpaceMemberMapper;

    @Mock
    private PermissionService permissionService;

    @Mock
    private JoinPoint joinPoint;

    @Mock
    private HttpServletRequest request;

    private ServletRequestAttributes requestAttributes;

    @BeforeEach
    void setUp() {
        requestAttributes = new ServletRequestAttributes(request);
        RequestContextHolder.setRequestAttributes(requestAttributes);
    }

    @AfterEach
    void tearDown() {
        RequestContextHolder.resetRequestAttributes();
    }

    // 场景：系统用户标记存在时，跳过权限校验
    @Test
    void checkPermission_systemUserSkip_shouldBypassCheck() {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(Boolean.TRUE);

        assertDoesNotThrow(() -> checkPermission.checkPermission(joinPoint));

        verify(workSpaceMemberMapper, never()).selectByMemberIdAndWorkspaceId(
            org.mockito.ArgumentMatchers.anyString(), org.mockito.ArgumentMatchers.anyString());
    }

    // 场景：无系统用户标记时，执行权限校验，非成员被拒绝
    @Test
    void checkPermission_noSystemUserSkip_shouldExecuteCheck() {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(null);

        // RequestContextUtils.getRequestUserId() 会返回 null，导致后续查询返回 null
        when(workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(
            org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.any())).thenReturn(null);

        assertThrows(Exception.class, () -> checkPermission.checkPermission(joinPoint));
    }

    // 场景：系统用户标记为 false 时，不跳过校验
    @Test
    void checkPermission_systemUserSkipFalse_shouldExecuteCheck() {
        when(request.getAttribute(Constants.SYSTEM_USER_SKIP_ATTR)).thenReturn(Boolean.FALSE);

        when(workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(
            org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.any())).thenReturn(null);

        assertThrows(Exception.class, () -> checkPermission.checkPermission(joinPoint));
    }

    // 场景：RequestContextHolder 为空时（异步场景），不跳过校验
    @Test
    void checkPermission_nullRequestAttributes_shouldExecuteCheck() {
        RequestContextHolder.resetRequestAttributes();

        when(workSpaceMemberMapper.selectByMemberIdAndWorkspaceId(
            org.mockito.ArgumentMatchers.any(), org.mockito.ArgumentMatchers.any())).thenReturn(null);

        assertThrows(Exception.class, () -> checkPermission.checkPermission(joinPoint));
    }
}
