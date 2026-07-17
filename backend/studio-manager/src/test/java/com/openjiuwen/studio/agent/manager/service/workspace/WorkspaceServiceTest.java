/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.workspace;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.FileCommonUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UuidUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.constant.Constants;
import com.openjiuwen.studio.agent.manager.dto.CreateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.DeleteWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.Extension;
import com.openjiuwen.studio.agent.manager.dto.ExternalMappingInfo;
import com.openjiuwen.studio.agent.manager.dto.GetWorkspaceListRsp;
import com.openjiuwen.studio.agent.manager.dto.ImportListInfo;
import com.openjiuwen.studio.agent.manager.dto.ImportRsp;
import com.openjiuwen.studio.agent.manager.dto.MemberRole;
import com.openjiuwen.studio.agent.manager.dto.QueryWorkspaceQo;
import com.openjiuwen.studio.agent.manager.dto.SecretLevel;
import com.openjiuwen.studio.agent.manager.dto.UpdateWorkspaceReq;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceInfo;
import com.openjiuwen.studio.agent.manager.dto.WorkspaceMemberInfo;
import com.openjiuwen.studio.agent.manager.entity.WorkSpaceMemberEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMappingMapper;
import com.openjiuwen.studio.agent.manager.service.AgentManagementService;
import com.openjiuwen.studio.agent.manager.service.SkuManageService;
import com.openjiuwen.studio.agent.manager.service.WorkflowManagementService;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.ResourcePatternResolver;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@MockitoSettings(strictness = Strictness.LENIENT)
class WorkspaceServiceTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private WorkspaceMapper workspaceMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private WorkspaceMemberService workspaceMemberService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private WorkspaceMappingService workspaceMappingService;

    @Mock()
    private WorkspaceMappingMapper workspaceMappingMapper;

    @InjectMocks
    private WorkspaceService workspaceService;

    @Mock
    private SkuManageService skuManageService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private AgentManagementService agentManagementService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private WorkflowManagementService workflowManagementService;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ResourcePatternResolver resourcePatternResolver;

    private AutoCloseable mockitoCloseable;

    public static final String projectId = "project_mock";

    public static final String domainId = "domain_mock";

    public static final String userId = "user_id_mock";

    public static final String userName = "user_name_mock";

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(workspaceService, "workSpaceDefaultIcon", "not_empty");

        Set<String> allowedIconType = new HashSet<>();
        allowedIconType.add(".jpg");
        allowedIconType.add(".jpeg");
        allowedIconType.add(".png");
        allowedIconType.add(".gif");
        ReflectionTestUtils.setField(workspaceService, "allowedIconType", allowedIconType);

        ReflectionTestUtils.setField(workspaceService, "iconMaxSize", "20");

        ReflectionTestUtils.setField(workspaceService, "agentInitTemplatePath", "classpath:template/app/**.jsonl");
        ReflectionTestUtils.setField(workspaceService, "agentInitTemplateEnable", false);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    public void test_createWorkspace_success() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS);
            MockedStatic<UuidUtils> mockedStaticUuidUtils = mockStatic(UuidUtils.class, RETURNS_DEEP_STUBS)) {

            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticUuidUtils.when(UuidUtils::getUUID).thenReturn("not_empty");

            CreateWorkspaceReq createWorkspaceReq = buildCreateWorkspaceReq();
            when(workspaceMapper.countWorkspaceEntityByName(projectId, createWorkspaceReq.getName())).thenReturn(0);
            when(workspaceMapper.getWorkspaceByProjectId(projectId)).thenReturn(Collections.emptyList());

            String result = workspaceService.createWorkspace(projectId, createWorkspaceReq);

            assertEquals(createWorkspaceReq.getId(), result);
        }
    }

    @Test
    public void test_createWorkspace_name_already_exists() throws Exception {
        assertThrows((AgentStudioException.class), () -> {
            CreateWorkspaceReq createWorkspaceReq = buildCreateWorkspaceReq();
            when(workspaceMapper.countWorkspaceEntityByName(projectId, createWorkspaceReq.getName())).thenReturn(1);
            workspaceService.createWorkspace(projectId, createWorkspaceReq);
        });
    }

    @Test
    public void test_updateWorkspace_when_workspace_not_exited() {
        assertThrows((AgentStudioException.class), () -> {
            UpdateWorkspaceReq updateWorkspaceReq = buildUpdateWorkspaceReq();
            when(workspaceMapper.selectWorkspaceEntityById(projectId, updateWorkspaceReq.getId())).thenReturn(null);
            workspaceService.updateWorkspace(projectId, updateWorkspaceReq);
        });
    }

    @Test
    public void test_updateWorkspace_success() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS)) {
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn(userName);
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn(userId);
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn(domainId);

            UpdateWorkspaceReq updateWorkspaceReq = buildUpdateWorkspaceReq();

            WorkspaceEntity existedWorkspaceEntity = buildWorkspaceEntity();

            when(workspaceMapper.selectWorkspaceEntityById(projectId, updateWorkspaceReq.getId())).thenReturn(
                existedWorkspaceEntity);

            WorkspaceMemberInfo workspaceMemberInfo = buildWorkspaceMemberInfo();
            when(workspaceMemberService.queryWorkspaceMemberDetail(projectId, userId,
                updateWorkspaceReq.getId())).thenReturn(workspaceMemberInfo);

            WorkspaceInfo workspaceInfo = workspaceService.updateWorkspace(projectId, updateWorkspaceReq);

            assertNotNull(workspaceInfo);
        }
    }

    @Test
    void test_deleteWorkspace_success() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS);) {
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn(userName);
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn(userId);
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn(domainId);

            DeleteWorkspaceReq deleteWorkspaceReq = buildDeleteWorkspaceReq();

            WorkspaceMemberInfo memberInfo = buildWorkspaceMemberInfo();
            when(workspaceMemberService.queryWorkspaceMemberDetail(any(), any(), any())).thenReturn(memberInfo);

            WorkspaceInfo workspaceInfo = new WorkspaceInfo();
            workspaceInfo.setType(CommonConstant.WORKSPACE.TYPE.TEAM_TYPE);
            when(workspaceMemberService.queryWorkspaceMemberDetail(any(), any(), any())).thenReturn(memberInfo);
            when(workspaceMapper.selectById(anyString(), anyString())).thenReturn(workspaceInfo);

            when(workspaceMapper.getWorkspaceByProjectIdAndUserId(anyString(), anyString()).size()).thenReturn(1);
            when(workspaceMapper.updateByPrimaryKeySelective(any())).thenReturn(1);

            String result = workspaceService.deleteWorkspace(projectId, deleteWorkspaceReq);

            assertEquals(deleteWorkspaceReq.getId(), result);
        }
    }

    private CreateWorkspaceReq buildCreateWorkspaceReq() {
        CreateWorkspaceReq createWorkspaceReq = new CreateWorkspaceReq();
        createWorkspaceReq.setId("workspace_123");
        createWorkspaceReq.setDescription("description");
        createWorkspaceReq.setName("workspace_name");
        createWorkspaceReq.setIcon("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA");

        ExternalMappingInfo externalMappingInfo = new ExternalMappingInfo();
        externalMappingInfo.setMappingId("mapping_123");
        externalMappingInfo.setWorkspaceId("workspace_123");
        externalMappingInfo.setSource("MA");

        ArrayList<Extension> extensionList = new ArrayList<>();
        Extension extensionOne = new Extension();
        extensionOne.setKey("key1");
        extensionOne.setValue("value1");
        extensionOne.setSecretLevel(SecretLevel.NONE);

        Extension extensionTwo = new Extension();
        extensionTwo.setKey("key1");
        extensionTwo.setValue("value1");
        extensionTwo.setSecretLevel(SecretLevel.NONE);

        extensionList.add(extensionOne);
        extensionList.add(extensionTwo);

        externalMappingInfo.setExtensionContent(extensionList);
        createWorkspaceReq.setExternalMappingInfo(externalMappingInfo);
        return createWorkspaceReq;
    }

    private UpdateWorkspaceReq buildUpdateWorkspaceReq() {
        UpdateWorkspaceReq updateWorkspaceReq = new UpdateWorkspaceReq();

        updateWorkspaceReq.setId("workspace_123");
        updateWorkspaceReq.setDescription("description");
        updateWorkspaceReq.setName("workspace_name");
        updateWorkspaceReq.setIcon("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA");

        return updateWorkspaceReq;
    }

    private DeleteWorkspaceReq buildDeleteWorkspaceReq() {
        DeleteWorkspaceReq deleteWorkspaceReq = new DeleteWorkspaceReq();
        deleteWorkspaceReq.setId("workspace_123");
        return deleteWorkspaceReq;
    }

    private WorkspaceEntity buildWorkspaceEntity() {
        return new WorkspaceEntity().setId("workspace_123")
            .setProjectId(projectId)
            .setName("workspace_name")
            .setDescription("description")
            .setIcon("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA")
            .setTenantId(domainId)
            .setStatus(CommonConstant.WORKSPACE.STATUS.ENABLE)
            .setType(CommonConstant.WORKSPACE.TYPE.TEAM_TYPE);
    }

    private WorkspaceMemberInfo buildWorkspaceMemberInfo() {
        WorkspaceMemberInfo workspaceMemberInfo = new WorkspaceMemberInfo();
        workspaceMemberInfo.setRole(MemberRole.OWNER.getValue());
        return workspaceMemberInfo;
    }

    @Test
    void test_deleteWorkspace_user_no_permission() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS);
            MockedStatic<UuidUtils> mockedStaticUuidUtils = mockStatic(UuidUtils.class, RETURNS_DEEP_STUBS)) {
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticUuidUtils.when(UuidUtils::getUUID).thenReturn("ws1");

            when(workspaceMapper.selectById(any(), any())).thenReturn(null);
            when(workspaceMemberService.queryWorkspaceMemberDetail(any(), any(), any())).thenReturn(null);
            assertThrows(AgentStudioException.class,
                () -> workspaceService.deleteWorkspace(projectId, buildDeleteWorkspaceReq()));
        }
    }

    @Test
    void test_deleteWorkspace_failure() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS);
            MockedStatic<UuidUtils> mockedStaticUuidUtils = mockStatic(UuidUtils.class, RETURNS_DEEP_STUBS)) {
            // Given
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticUuidUtils.when(UuidUtils::getUUID).thenReturn("ws1");
            DeleteWorkspaceReq body = mock(DeleteWorkspaceReq.class);
            when(body.getId()).thenReturn("ws1");
            WorkspaceMemberInfo memberInfo = mock(WorkspaceMemberInfo.class);
            when(memberInfo.getRole()).thenReturn(MemberRole.OWNER.getValue());
            when(workspaceMemberService.queryWorkspaceMemberDetail(any(), any(), any())).thenReturn(memberInfo);
            when(workspaceMapper.getWorkspaceByProjectIdAndUserId(anyString(), anyString()).size()).thenReturn(1);
            when(workspaceMapper.updateByPrimaryKeySelective(any())).thenReturn(0);

            DeleteWorkspaceReq deleteWorkspaceReq = buildDeleteWorkspaceReq();
            String result = workspaceService.deleteWorkspace(projectId, deleteWorkspaceReq);

            assertEquals(deleteWorkspaceReq.getId(), result);
        }

    }

    @Test
    void test_deleteWorkspace_throw_exception() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS);
            MockedStatic<UuidUtils> mockedStaticUuidUtils = mockStatic(UuidUtils.class, RETURNS_DEEP_STUBS)) {
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticUuidUtils.when(UuidUtils::getUUID).thenReturn("ws1");
            WorkspaceMemberInfo memberInfo = new WorkspaceMemberInfo();
            memberInfo.setRole(MemberRole.OWNER.getValue());

            WorkspaceInfo workspaceInfo = new WorkspaceInfo();
            workspaceInfo.setType(CommonConstant.WORKSPACE.TYPE.PERSON_TYPE);
            when(workspaceMemberService.queryWorkspaceMemberDetail(any(), any(), any())).thenReturn(memberInfo);
            when(workspaceMapper.selectById(anyString(), anyString())).thenReturn(workspaceInfo);
            assertThrows(AgentStudioException.class,
                () -> workspaceService.deleteWorkspace(projectId, buildDeleteWorkspaceReq()));
        }
    }

    @Test
    @DisplayName("test deleteWorkspace")
    void test_deleteWorkspace_should_return_true() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS)) {
            // Given
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");

            WorkspaceMemberInfo workspaceMemberInfo = new WorkspaceMemberInfo();
            when(workspaceMemberService.queryWorkspaceMemberDetail(anyString(), anyString(), anyString())).thenReturn(
                workspaceMemberInfo);

            when(workspaceMapper.getWorkspaceByProjectIdAndUserId(anyString(), anyString()).size()).thenReturn(0);
            when(workspaceMapper.updateByPrimaryKeySelective(any(WorkspaceEntity.class))).thenReturn(0);
            when(workspaceMapper.getWorkspaceByProjectIdAndUserId(anyString(), anyString()).size()).thenReturn(1);

            DeleteWorkspaceReq body = new DeleteWorkspaceReq();

            // Then
            assertThrows(AgentStudioException.class, () -> workspaceService.deleteWorkspace("not_empty", body));
        }
    }

    @Test
    public void test_getWorkspace_workspaces_but_empty() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS);
            MockedStatic<UuidUtils> mockedStaticUuidUtils = mockStatic(UuidUtils.class, RETURNS_DEEP_STUBS)) {
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticUuidUtils.when(UuidUtils::getUUID).thenReturn("ws1");

            List<WorkspaceEntity> workspaces = new ArrayList<>();
            WorkspaceEntity workspaceEntity = new WorkspaceEntity();
            workspaceEntity.setId("1");
            workspaceEntity.setRole("PERSON");
            workspaces.add(workspaceEntity);

            List<WorkSpaceMemberEntity> workSpaceMemberEntitys = new ArrayList<>();
            WorkSpaceMemberEntity workSpaceMemberEntity = new WorkSpaceMemberEntity().setId("1")
                .setRole("OWNER")
                .setWorkspaceId("1");
            workSpaceMemberEntitys.add(workSpaceMemberEntity);

            when(workspaceMemberService.queryAllWorkSpaceInfoByIamUserId(anyString())).thenReturn(
                workSpaceMemberEntitys);
            when(workspaceMapper.getWorkspaceByProjectIdAndWorkspaceIds(eq(projectId), anyList(), any())).thenReturn(
                workspaces);
            when(workspaceMapper.getWorkspaceByProjectIdAndUserId(eq(projectId), anyString())).thenReturn(
                Collections.emptyList());
            when(workspaceMapper.getPersonalWorkspaceByProjectIdAndUserId(eq(projectId), anyString())).thenReturn(null);

            QueryWorkspaceQo queryWorkspaceQo = new QueryWorkspaceQo();
            queryWorkspaceQo.setScope("user");
            queryWorkspaceQo.setType("TEAM");
            GetWorkspaceListRsp response = workspaceService.queryWorkspace(projectId, queryWorkspaceQo);

            assertNotNull(response);
            assertEquals(1, response.getCount());
            assertNotNull(response.getWorkspaceList());
            assertEquals(1, response.getWorkspaceList().size());
        }

    }

    @Test
    @DisplayName("test getWorkspace")
    void test_getWorkspace_should_return_not_null() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS)) {
            // Given
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");

            List<WorkSpaceMemberEntity> workSpaceMemberEntitys = new ArrayList<>();
            WorkSpaceMemberEntity workSpaceMemberEntity1 = new WorkSpaceMemberEntity().setId("1")
                .setWorkspaceId("1")
                .setRole("ADMIN");
            WorkSpaceMemberEntity workSpaceMemberEntity2 = new WorkSpaceMemberEntity().setId("2")
                .setWorkspaceId("2")
                .setRole("ADMIN");
            workSpaceMemberEntitys.add(workSpaceMemberEntity1);
            workSpaceMemberEntitys.add(workSpaceMemberEntity2);

            List<WorkspaceEntity> workspaces = new ArrayList<>();
            WorkspaceEntity workspace1 = new WorkspaceEntity().setId("1").setProjectId("proj1").setName("ws1");
            WorkspaceEntity workspace2 = new WorkspaceEntity().setId("2").setProjectId("proj1").setName("ws2");
            workspaces.add(workspace1);
            workspaces.add(workspace2);
            when(workspaceMemberService.queryAllWorkSpaceInfoByIamUserId(anyString())).thenReturn(
                workSpaceMemberEntitys);
            when(workspaceMapper.getWorkspaceByProjectIdAndWorkspaceIds(anyString(), anyList(), any())).thenReturn(
                workspaces);

            QueryWorkspaceQo queryWorkspaceQo = new QueryWorkspaceQo();
            queryWorkspaceQo.setType("TEAM");
            queryWorkspaceQo.setScope("user");
            GetWorkspaceListRsp response = workspaceService.queryWorkspace(projectId, queryWorkspaceQo);

            assertNotNull(response);
            assertEquals(workspaces.size(), response.getCount());
            assertNotNull(response.getWorkspaceList());
            assertEquals(workspaces.size(), response.getWorkspaceList().size());
        }
    }

    @Test
    public void test_getWorkspaceById_user_has_no_permission() throws Exception {
        String workspaceId = "ws1";
        try (MockedStatic<RequestContextUtils> mockedRequestContextUtils = mockStatic(RequestContextUtils.class)) {
            mockedRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn(userId);
            when(workspaceMemberService.queryWorkspaceMemberDetail(eq(projectId), eq(userId),
                eq(workspaceId))).thenReturn(null);

            // When & Then
            assertThrows(AgentStudioException.class, () -> {
                workspaceService.queryWorkspaceById(projectId, workspaceId);
            });
        }
    }

    @Test
    @DisplayName("test getWorkspaceById")
    void test_getWorkspaceById_should_return_not_null() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS)) {
            String workspaceId = "workspace_001";

            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");

            WorkspaceMemberInfo workspaceMemberInfo = new WorkspaceMemberInfo();
            when(workspaceMemberService.queryWorkspaceMemberDetail(anyString(), anyString(), anyString())).thenReturn(
                workspaceMemberInfo);

            when(workspaceMappingService.queryMappingWorkspaceExtensionInfo(workspaceId, "MAS")).thenReturn(null);

            WorkspaceEntity workspace = new WorkspaceEntity();
            when(workspaceMapper.getWorkspaceByWorkspaceId(anyString(), anyString())).thenReturn(workspace);
            when(workspaceMappingMapper.selectWorkspaceMappingEntityByWorkspaceId(workspaceId)).thenReturn(null);

            WorkspaceInfo result = workspaceService.queryWorkspaceById("not_empty", "not_empty");

            assertNotNull(result, "message");
        }
    }

    @Test
    void test_InitWorkspaceById_should_return_not_null() throws Exception {
        try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS)) {
            // Given
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("not_empty");
            mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("not_empty");
            List<WorkSpaceMemberEntity> workSpaceMemberEntitys = new ArrayList<>();
            WorkSpaceMemberEntity workSpaceMemberEntity1 = new WorkSpaceMemberEntity().setId("1")
                .setWorkspaceId("1")
                .setRole("ADMIN");
            workSpaceMemberEntitys.add(workSpaceMemberEntity1);

            List<WorkspaceEntity> workspaces = new ArrayList<>();
            WorkspaceEntity workspace1 = new WorkspaceEntity().setId("1").setProjectId("proj1").setName("ws1");
            workspaces.add(workspace1);

            when(workspaceMemberService.queryAllWorkSpaceInfoByIamUserId(anyString())).thenReturn(
                workSpaceMemberEntitys);
            when(workspaceMapper.getWorkspaceByProjectIdAndWorkspaceIds(anyString(), anyList(), any())).thenReturn(
                workspaces);
            when(workspaceMapper.getPersonalWorkspaceByProjectIdAndUserId(eq(projectId), anyString())).thenReturn(null);

            GetWorkspaceListRsp response = workspaceService.initWorkspace(projectId, "user");

            assertNotNull(response);
            assertEquals(workspaces.size(), response.getCount());
            assertNotNull(response.getWorkspaceList());
            assertEquals(workspaces.size(), response.getWorkspaceList().size());

            when(workspaceMapper.getPersonalWorkspaceByProjectIdAndUserId(eq(projectId), anyString())).thenReturn(
                new WorkspaceEntity().setIsPresetAgent(0));
            ReflectionTestUtils.setField(workspaceService, "agentInitTemplateEnable", true);
            workspaceService.initWorkspace(projectId, "user");
        }
    }

    @Test
    void test_createAgentTemplate_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<FileCommonUtils> mockedStaticFileCommonUtils = mockStatic(FileCommonUtils.class,
                RETURNS_DEEP_STUBS)) {
                // Given
                ImportRsp importRsp = new ImportRsp();
                when(
                    agentManagementService.importAgents(anyString(), anyString(), any(MultipartFile.class), anyString(),
                        anyString(), anyString(), anyString())).thenReturn(importRsp);
                List<ImportListInfo> importResultList = new ArrayList<>();
                when(agentManagementService.listImportFile(anyString(), anyString(), any(MultipartFile.class), eq(0),
                    eq(10))).thenReturn(importResultList);
                ImportRsp importRsp1 = new ImportRsp();
                when(workflowManagementService.importWorkflows(anyString(), anyString(), any(MultipartFile.class),
                    anyString(), anyString(), anyString())).thenReturn(importRsp1);

                Resource[] resourceArray = new Resource[1];

                when(resourcePatternResolver.getResources(anyString())).thenReturn(resourceArray);

                // When
                workspaceService.createAgentTemplate("test", "default");

                Resource mockResource1 = Mockito.mock(Resource.class);
                when(mockResource1.getFile()).thenReturn(new File("test1.jsonl"));
                resourceArray[0] = mockResource1;
                workspaceService.createAgentTemplate("test", "default");
            }
        });
    }

    @Test
    void test_filterAllIdsWithDependencies_should_equal_result() throws Exception {
        // Given
        List<ImportListInfo> importList = new ArrayList<>();
        ImportListInfo importListInfo = new ImportListInfo();
        importList.add(importListInfo);

        // When
        String result = workspaceService.filterAllIdsWithDependencies(importList, "test");

        // Then
        assertEquals("", result);
    }

    @Test
    void test_importResource_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given
            ImportRsp importRsp = new ImportRsp();
            when(workflowManagementService.importWorkflows(anyString(), anyString(), any(MultipartFile.class),
                anyString(),
                anyString(), anyString())).thenReturn(importRsp);
            ImportRsp importRsp1 = new ImportRsp();
            when(agentManagementService.importAgents(anyString(), anyString(), any(MultipartFile.class), anyString(),
                anyString(), anyString(), anyString())).thenReturn(importRsp1);

            MockMultipartFile file = new MockMultipartFile("file",  // 参数名
                "test.jsonl",  // 原始文件名
                "text/plain",  // MIME类型
                Constants.TEST_AGENT_EXPORT.getBytes()  // 文件内容
            );

            Map<String, String> resourceIds = new HashMap<>();
            resourceIds.put("test", "test");

            // When
            workspaceService.importResource("test", "test", file, "workflow", resourceIds);
            workspaceService.importResource("test", "test", file, "agent", resourceIds);
            workspaceService.importResource("test", "test", file, "controller", resourceIds);
            workspaceService.importResource("test", "test", file, "test", resourceIds);
        });
    }

    @Test
    void test_filterResourceIds_should_return_not_null() throws Exception {
        // Given
        List<ImportListInfo> importResultList = new ArrayList<>();
        ImportListInfo importListInfo = new ImportListInfo();
        importResultList.add(importListInfo);

        // When
        Map<String, String> result = workspaceService.filterResourceIds(importResultList);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_recursiveCollectIds_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given
            List<ImportListInfo> nodeList = new ArrayList<>();
            ImportListInfo importListInfo = new ImportListInfo();
            nodeList.add(importListInfo);

            Set<String> idSet = new HashSet<>();
            idSet.add("123");

            // When
            workspaceService.recursiveCollectIds(nodeList, "123", idSet);
        });
    }

    @Test
    @DisplayName("test getWorkspaceById should throw NullPointerException")
    void test_getWorkspaceById_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            try (MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils = mockStatic(
                RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
                // Given
                mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn(null);

                when(workspaceMemberService.queryWorkspaceMemberDetail(anyString(), anyString(),
                    anyString())).thenReturn(null);

                when(workspaceMapper.getWorkspaceByWorkspaceId(anyString(), anyString())).thenReturn(null);

                // When
                WorkspaceInfo result = workspaceService.queryWorkspaceById(null, null);
            }
        }, "message");
    }
}
