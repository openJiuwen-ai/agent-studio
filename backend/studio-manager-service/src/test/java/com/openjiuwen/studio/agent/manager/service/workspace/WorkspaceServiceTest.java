/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.workspace;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.CreateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.GetWorkspaceListRsp;
import com.openjiuwen.studio.agent.manager.dto.MemberRole;
import com.openjiuwen.studio.agent.manager.dto.QueryWorkspaceQo;
import com.openjiuwen.studio.agent.manager.dto.UpdateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberInfo;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.service.AgentManagementService;
import com.openjiuwen.studio.agent.manager.service.SkuManageService;
import com.openjiuwen.studio.agent.manager.service.WorkflowManagementService;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class WorkspaceServiceTest {

    @Mock
    private WorkspaceMapper workspaceMapper;
    @Mock
    private WorkspaceMappingService workspaceMappingService;
    @Mock
    private WorkspaceMemberService workspaceMemberService;
    @Mock
    private SkuManageService skuManageService;
    @Mock
    private AgentManagementService agentManagementService;
    @Mock
    private WorkflowManagementService workflowManagementService;

    @InjectMocks
    private WorkspaceService workspaceService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(workspaceService, "workSpaceDefaultIcon", "default-icon");
        ReflectionTestUtils.setField(workspaceService, "iconMaxSize", "1048576");
        ReflectionTestUtils.setField(workspaceService, "allowedIconTypeStr", "png,jpg,jpeg");
        ReflectionTestUtils.setField(workspaceService, "agentInitTemplateEnable", false);
        ReflectionTestUtils.setField(workspaceService, "agentInitTemplatePath", "");
        workspaceService.init();
    }

    @Test
    void testCreateWorkspace_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            when(workspaceMapper.countWorkspaceByDomainId(anyString(), anyString())).thenReturn(0);
            when(workspaceMapper.countWorkspaceEntityByName(anyString(), anyString())).thenReturn(0);

            CreateWorkspaceReq req = new CreateWorkspaceReq();
            req.setName("Test Workspace");
            req.setDescription("desc");

            String result = workspaceService.createWorkspace("p1", req);

            assertNotNull(result);
            verify(workspaceMapper).insert(any(WorkspaceEntity.class));
            verify(workspaceMemberService).addWorkspaceMember(anyString(), eq("uid-1"), eq(MemberRole.OWNER.getValue()));
        }
    }

    @Test
    void testCreateWorkspace_DuplicateName() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            when(workspaceMapper.countWorkspaceByDomainId(anyString(), anyString())).thenReturn(0);
            when(workspaceMapper.countWorkspaceEntityByName(anyString(), anyString())).thenReturn(1);

            CreateWorkspaceReq req = new CreateWorkspaceReq();
            req.setName("Existing Workspace");

            assertThrows(AgentStudioException.class, () ->
                workspaceService.createWorkspace("p1", req));
        }
    }

    @Test
    void testUpdateWorkspace_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");
            ctx.when(RequestContextUtils::getRequestUserName).thenReturn("user1");

            WorkspaceEntity existing = new WorkspaceEntity();
            existing.setId("ws-1");
            existing.setName("Old Name");
            when(workspaceMapper.selectWorkspaceEntityById("p1", "ws-1")).thenReturn(existing);

            WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
            memberInfo.setRole(MemberRole.OWNER.getValue());
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(memberInfo);
            when(workspaceMapper.countWorkspaceEntityByName(anyString(), anyString())).thenReturn(0);

            UpdateWorkspaceReq req = new UpdateWorkspaceReq();
            req.setId("ws-1");
            req.setName("New Name");
            req.setDescription("new desc");

            WorkspaceInfo result = workspaceService.updateWorkspace("p1", req);

            assertNotNull(result);
            verify(workspaceMapper).updateByPrimaryKeySelective(any(WorkspaceEntity.class));
        }
    }

    @Test
    void testUpdateWorkspace_NotFound() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            when(workspaceMapper.selectWorkspaceEntityById("p1", "ws-1")).thenReturn(null);

            UpdateWorkspaceReq req = new UpdateWorkspaceReq();
            req.setId("ws-1");
            req.setName("New Name");

            AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
                workspaceService.updateWorkspace("p1", req));
            assertEquals(StudioError.WORKSPACE_NOT_EXISTED, ex.getErrorCode());
        }
    }

    @Test
    void testUpdateWorkspace_NoPermission() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            WorkspaceEntity existing = new WorkspaceEntity();
            existing.setId("ws-1");
            existing.setName("Old Name");
            when(workspaceMapper.selectWorkspaceEntityById("p1", "ws-1")).thenReturn(existing);
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(null);

            UpdateWorkspaceReq req = new UpdateWorkspaceReq();
            req.setId("ws-1");
            req.setName("New Name");

            assertThrows(AgentStudioException.class, () ->
                workspaceService.updateWorkspace("p1", req));
        }
    }

    @Test
    void testDeleteWorkspace_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
            memberInfo.setRole(MemberRole.OWNER.getValue());
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(memberInfo);

            WorkspaceInfo wsInfo = new WorkspaceInfo();
            wsInfo.setType("team");
            when(workspaceMapper.selectById("p1", "ws-1")).thenReturn(wsInfo);

            DeleteWorkspaceReq req = new DeleteWorkspaceReq();
            req.setId("ws-1");

            String result = workspaceService.deleteWorkspace("p1", req);

            assertEquals("ws-1", result);
            verify(workspaceMapper).updateByPrimaryKeySelective(any(WorkspaceEntity.class));
        }
    }

    @Test
    void testDeleteWorkspace_NoPermission() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            WorkspaceInfo wsInfo = new WorkspaceInfo();
            wsInfo.setType("team");
            when(workspaceMapper.selectById("p1", "ws-1")).thenReturn(wsInfo);
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(null);

            DeleteWorkspaceReq req = new DeleteWorkspaceReq();
            req.setId("ws-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
                workspaceService.deleteWorkspace("p1", req));
            assertEquals(StudioError.USER_NO_PERMISSION_DO_THIS, ex.getErrorCode());
        }
    }

    @Test
    void testDeleteWorkspace_NotFound() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            when(workspaceMapper.selectById("p1", "ws-1")).thenReturn(null);

            DeleteWorkspaceReq req = new DeleteWorkspaceReq();
            req.setId("ws-1");

            AgentStudioException ex = assertThrows(AgentStudioException.class, () ->
                workspaceService.deleteWorkspace("p1", req));
            assertEquals(StudioError.WORKSPACE_NOT_EXISTED, ex.getErrorCode());
        }
    }

    @Test
    void testDeleteWorkspace_PersonalType() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
            memberInfo.setRole(MemberRole.OWNER.getValue());
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(memberInfo);

            WorkspaceInfo wsInfo = new WorkspaceInfo();
            wsInfo.setType("PERSON");
            when(workspaceMapper.selectById("p1", "ws-1")).thenReturn(wsInfo);

            DeleteWorkspaceReq req = new DeleteWorkspaceReq();
            req.setId("ws-1");

            assertThrows(AgentStudioException.class, () ->
                workspaceService.deleteWorkspace("p1", req));
        }
    }

    @Test
    void testQueryWorkspace_ProjectScope() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            QueryWorkspaceQo qo = new QueryWorkspaceQo();
            qo.setScope("project");

            when(workspaceMapper.selectWorkspaceWithMappingInfo(eq("p1"), any()))
                .thenReturn(Collections.emptyList());

            GetWorkspaceListRsp result = workspaceService.queryWorkspace("p1", qo);

            assertNotNull(result);
            assertEquals(0, result.getCount());
        }
    }

    @Test
    void testValidateIcon_NullIcon() {
        assertDoesNotThrow(() -> workspaceService.validateIcon(null));
    }

    @Test
    void testValidateIcon_EmptyIcon() {
        assertDoesNotThrow(() -> workspaceService.validateIcon(""));
    }

    /**
     * 用例描述：查询工作空间详情时工作空间不存在，应抛出 WORKSPACE_NOT_EXISTED 异常（404）
     * 预制条件：workspaceMemberService 返回有效成员信息，workspaceMapper.getWorkspaceByWorkspaceId 返回 null
     * 输入参数：projectId=p1, workspaceId=ws-1
     * 预期结果：抛出 AgentStudioException，错误码为 WORKSPACE_NOT_EXISTED
     */
    @Test
    void testQueryWorkspaceById_WorkspaceNotFound_ThrowsException() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
            memberInfo.setRole(MemberRole.OWNER.getValue());
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(memberInfo);
            when(workspaceMapper.getWorkspaceByWorkspaceId("p1", "ws-1")).thenReturn(null);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> workspaceService.queryWorkspaceById("p1", "ws-1"));
            assertEquals(StudioError.WORKSPACE_NOT_EXISTED, ex.getErrorCode());
        }
    }

    /**
     * 用例描述：查询工作空间详情时用户无权限（memberInfo 为 null），应抛出 USER_NO_PERMISSION_DO_THIS 异常
     * 预制条件：workspaceMemberService.queryWorkspaceMemberDetail 返回 null
     * 输入参数：projectId=p1, workspaceId=ws-1
     * 预期结果：抛出 AgentStudioException，错误码为 USER_NO_PERMISSION_DO_THIS
     */
    @Test
    void testQueryWorkspaceById_NoPermission_ThrowsException() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(null);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> workspaceService.queryWorkspaceById("p1", "ws-1"));
            assertEquals(StudioError.USER_NO_PERMISSION_DO_THIS, ex.getErrorCode());
        }
    }

    /**
     * 用例描述：查询工作空间详情时工作空间存在，应正常返回 WorkspaceInfo
     * 预制条件：workspaceMemberService 返回有效成员信息，workspaceMapper 返回有效实体
     * 输入参数：projectId=p1, workspaceId=ws-1
     * 预期结果：返回非空 WorkspaceInfo，role 被正确设置
     */
    @Test
    void testQueryWorkspaceById_Success() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestUserId).thenReturn("uid-1");

            WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
            memberInfo.setRole(MemberRole.OWNER.getValue());
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq("p1"), eq("uid-1"), eq("ws-1")))
                .thenReturn(memberInfo);

            WorkspaceEntity workspaceEntity = new WorkspaceEntity();
            workspaceEntity.setId("ws-1");
            workspaceEntity.setName("Test Workspace");
            when(workspaceMapper.getWorkspaceByWorkspaceId("p1", "ws-1")).thenReturn(workspaceEntity);
            when(workspaceMappingService.queryWorkspaceMappingInfoByWorkspaceId("ws-1"))
                .thenReturn(Collections.emptyList());

            WorkspaceInfo result = workspaceService.queryWorkspaceById("p1", "ws-1");

            assertNotNull(result);
            assertEquals("ws-1", result.getId());
            assertEquals(MemberRole.OWNER.getValue(), result.getRole());
        }
    }
}
