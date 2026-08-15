/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.LanguageUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBranchListRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentBriefRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentInfoReq;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentListRsp;
import com.openjiuwen.studio.agent.manager.dto.ComplexIntentRsp;
import com.openjiuwen.studio.agent.manager.dto.ListComplexIntentBranchQo;
import com.openjiuwen.studio.agent.manager.dto.ListComplexIntentQo;
import com.openjiuwen.studio.agent.manager.entity.ComplexIntentBranchEntity;
import com.openjiuwen.studio.agent.manager.entity.ComplexIntentEntity;
import com.openjiuwen.studio.agent.manager.mapper.ComplexIntentBranchMapper;
import com.openjiuwen.studio.agent.manager.mapper.ComplexIntentMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.MessageSource;
import org.springframework.core.io.Resource;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

@ExtendWith(MockitoExtension.class)
class ComplexIntentManagementServiceTest {

    @Mock
    private ComplexIntentMapper complexIntentMapper;

    @Mock
    private ComplexIntentBranchMapper complexIntentBranchMapper;

    @Mock
    private MessageSource messageSource;

    @InjectMocks
    private ComplexIntentManagementService complexIntentManagementService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(complexIntentManagementService, "complexIntentRepoId", "repo-1");
        ReflectionTestUtils.setField(complexIntentManagementService, "maxComplexIntentImportFileSize", 10);
        ReflectionTestUtils.setField(complexIntentManagementService, "maxComplexIntentImportBranchSize", 200);
        ReflectionTestUtils.setField(complexIntentManagementService, "envType", "SIMPLE");
    }

    @Test
    void testImportEntryPointsAreTransactional() throws NoSuchMethodException {
        assertNotNull(ComplexIntentManagementService.class
            .getMethod("importIntent", String.class, String.class, MultipartFile.class, String.class)
            .getAnnotation(Transactional.class));
        assertNotNull(ComplexIntentManagementService.class
            .getMethod("importIntentBranch", String.class, String.class, String.class, MultipartFile.class)
            .getAnnotation(Transactional.class));
    }

    @Test
    void testCreateComplexIntent_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("userName");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ComplexIntentInfoReq body = new ComplexIntentInfoReq();
            body.setName("TestIntent");
            body.setDescription("Test description");

            when(complexIntentMapper.getEntitiesAccurate(any())).thenReturn(new ArrayList<>());

            ComplexIntentBriefRsp result = complexIntentManagementService.createComplexIntent("proj-1", "ws-1", body);
            assertNotNull(result);
            assertNotNull(result.getIntentId());
            verify(complexIntentMapper).createEntity(any());
        }
    }

    @Test
    void testCreateComplexIntent_WithBranch() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("userName");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ComplexIntentBranchInfoReq branchReq = new ComplexIntentBranchInfoReq();
            branchReq.setName("branch-1");
            branchReq.setExamples(List.of("example1", "example2"));

            ComplexIntentInfoReq body = new ComplexIntentInfoReq();
            body.setName("TestIntent");
            body.setDescription("Test description");
            body.setBranches(List.of(branchReq));

            when(complexIntentMapper.getEntitiesAccurate(any())).thenReturn(new ArrayList<>());
            when(complexIntentMapper.getByKeyAndWorkspaceId(anyString(), anyString(), anyString()))
                .thenReturn(new ComplexIntentEntity());
            when(complexIntentBranchMapper.getEntities(any())).thenReturn(new ArrayList<>());
            when(complexIntentBranchMapper.maxBranchIndex(anyString(), anyString(), anyString())).thenReturn(null);
            when(complexIntentBranchMapper.countBranch(anyString(), anyString(), anyString())).thenReturn(1);

            ComplexIntentBriefRsp result = complexIntentManagementService.createComplexIntent("proj-1", "ws-1", body);
            assertNotNull(result);
            assertNotNull(result.getIntentId());
            assertNotNull(result.getBranchId());
        }
    }

    @Test
    void testCreateComplexIntent_DuplicateName() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");
            reqCtx.when(RequestContextUtils::getRequestUserName).thenReturn("userName");
            reqCtx.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain-1");

            ComplexIntentInfoReq body = new ComplexIntentInfoReq();
            body.setName("ExistingIntent");

            ComplexIntentEntity existingEntity = new ComplexIntentEntity();
            existingEntity.setIntentId("other-id");
            existingEntity.setName("ExistingIntent");

            when(complexIntentMapper.getEntitiesAccurate(any())).thenReturn(List.of(existingEntity));

            assertThrows(AgentStudioException.class,
                () -> complexIntentManagementService.createComplexIntent("proj-1", "ws-1", body));
        }
    }

    @Test
    void testCreateComplexIntentBranch_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");

            ComplexIntentEntity originEntity = new ComplexIntentEntity();
            originEntity.setIntentId("intent-1");
            when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(originEntity);

            ComplexIntentBranchInfoReq body = new ComplexIntentBranchInfoReq();
            body.setName("new-branch");
            body.setExamples(List.of("ex1", "ex2"));

            when(complexIntentBranchMapper.getEntities(any())).thenReturn(new ArrayList<>());
            when(complexIntentBranchMapper.maxBranchIndex(anyString(), anyString(), anyString())).thenReturn(0);
            when(complexIntentBranchMapper.countBranch(anyString(), anyString(), anyString())).thenReturn(1);

            ComplexIntentBranchBriefRsp result = complexIntentManagementService.createComplexIntentBranch(
                "proj-1", "intent-1", "ws-1", body);
            assertNotNull(result);
            assertNotNull(result.getBranchId());
        }
    }

    @Test
    void testCreateComplexIntentBranch_DuplicateExamples() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");

            ComplexIntentEntity originEntity = new ComplexIntentEntity();
            originEntity.setIntentId("intent-1");
            when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(originEntity);

            ComplexIntentBranchInfoReq body = new ComplexIntentBranchInfoReq();
            body.setName("branch-1");
            body.setExamples(List.of("same", "same"));

            assertThrows(AgentStudioException.class,
                () -> complexIntentManagementService.createComplexIntentBranch("proj-1", "intent-1", "ws-1", body));
        }
    }

    @Test
    void testDeleteComplexIntent_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            ComplexIntentEntity originEntity = new ComplexIntentEntity();
            originEntity.setIntentId("intent-1");
            when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(originEntity);
            when(complexIntentBranchMapper.getEntities(any())).thenReturn(new ArrayList<>());

            ComplexIntentBriefRsp result = complexIntentManagementService.deleteComplexIntent("proj-1", "intent-1", "ws-1");
            assertNotNull(result);
            assertEquals("intent-1", result.getIntentId());
            verify(complexIntentBranchMapper).deleteByIntentId("intent-1", "proj-1");
            verify(complexIntentMapper).deleteByKey("intent-1", "proj-1");
        }
    }

    @Test
    void testDeleteComplexIntent_NoPermission() {
        when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(null);

        assertThrows(AgentStudioException.class,
            () -> complexIntentManagementService.deleteComplexIntent("proj-1", "intent-1", "ws-1"));
    }

    @Test
    void testDeleteComplexIntentBranch_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            ComplexIntentBranchEntity branchEntity = new ComplexIntentBranchEntity();
            branchEntity.setBranchId("branch-1");
            branchEntity.setFaqIds("faq-1");
            when(complexIntentBranchMapper.getByKeyAndWorkspaceId("branch-1", "intent-1", "proj-1", "ws-1"))
                .thenReturn(branchEntity);
            when(complexIntentBranchMapper.getByKey("branch-1", "intent-1", "proj-1")).thenReturn(branchEntity);
            when(complexIntentBranchMapper.countBranch(anyString(), anyString(), anyString())).thenReturn(0);

            ComplexIntentBranchBriefRsp result = complexIntentManagementService.deleteComplexIntentBranch(
                "proj-1", "intent-1", "branch-1", "ws-1");
            assertNotNull(result);
            assertEquals("branch-1", result.getBranchId());
        }
    }

    @Test
    void testDeleteComplexIntentBranch_NoPermission() {
        when(complexIntentBranchMapper.getByKeyAndWorkspaceId("branch-1", "intent-1", "proj-1", "ws-1"))
            .thenReturn(null);

        assertThrows(AgentStudioException.class,
            () -> complexIntentManagementService.deleteComplexIntentBranch("proj-1", "intent-1", "branch-1", "ws-1"));
    }

    @Test
    void testListComplexIntent_Success() {
        ComplexIntentEntity entity = new ComplexIntentEntity();
        entity.setIntentId("intent-1");
        entity.setProjectId("proj-1");
        entity.setWorkspaceId("ws-1");
        entity.setName("TestIntent");
        entity.setBranchesCnt(2);

        when(complexIntentMapper.getEntities(any())).thenReturn(List.of(entity));

        ListComplexIntentQo query = new ListComplexIntentQo();
        query.setOffset(0);
        query.setLimit(10);
        query.setWorkspaceId("ws-1");

        ComplexIntentListRsp result = complexIntentManagementService.listComplexIntent("proj-1", query);
        assertNotNull(result);
        assertNotNull(result.getIntents());
    }

    @Test
    void testListComplexIntentBranch_Success() {
        ComplexIntentBranchEntity branchEntity = new ComplexIntentBranchEntity();
        branchEntity.setBranchId("branch-1");
        branchEntity.setIntentId("intent-1");
        branchEntity.setProjectId("proj-1");
        branchEntity.setBranchName("branch-name");
        branchEntity.setBranchIndex(1);
        branchEntity.setContent("{\"description\":\"desc\",\"examples\":[\"ex1\"]}");

        when(complexIntentBranchMapper.getEntities(any())).thenReturn(List.of(branchEntity));

        ListComplexIntentBranchQo query = new ListComplexIntentBranchQo();
        query.setWorkspaceId("ws-1");

        ComplexIntentBranchListRsp result = complexIntentManagementService.listComplexIntentBranch(
            "proj-1", "intent-1", query);
        assertNotNull(result);
        assertNotNull(result.getBranches());
    }

    @Test
    void testRetrieveComplexIntent_Success() {
        ComplexIntentEntity entity = new ComplexIntentEntity();
        entity.setIntentId("intent-1");
        entity.setName("TestIntent");
        entity.setDescription("desc");
        entity.setBranchesCnt(3);

        when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(entity);

        ComplexIntentRsp result = complexIntentManagementService.retrieveComplexIntent("proj-1", "intent-1", "ws-1");
        assertNotNull(result);
        assertEquals("intent-1", result.getIntentId());
        assertEquals("TestIntent", result.getName());
        assertEquals(3, result.getBranchesCnt());
    }

    @Test
    void testRetrieveComplexIntent_NotFound() {
        when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(null);

        assertThrows(AgentStudioException.class,
            () -> complexIntentManagementService.retrieveComplexIntent("proj-1", "intent-1", "ws-1"));
    }

    @Test
    void testModifyComplexIntent_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            ComplexIntentEntity originEntity = new ComplexIntentEntity();
            originEntity.setIntentId("intent-1");
            when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(originEntity);
            when(complexIntentMapper.getEntitiesAccurate(any())).thenReturn(new ArrayList<>());

            ComplexIntentInfoReq body = new ComplexIntentInfoReq();
            body.setName("UpdatedIntent");
            body.setDescription("Updated desc");

            ComplexIntentBriefRsp result = complexIntentManagementService.modifyComplexIntent(
                "proj-1", "intent-1", "ws-1", body);
            assertNotNull(result);
            assertEquals("intent-1", result.getIntentId());
            verify(complexIntentMapper).updateByKey(any());
        }
    }

    @Test
    void testModifyComplexIntent_NoPermission() {
        when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(null);

        ComplexIntentInfoReq body = new ComplexIntentInfoReq();
        body.setName("UpdatedIntent");

        assertThrows(AgentStudioException.class,
            () -> complexIntentManagementService.modifyComplexIntent("proj-1", "intent-1", "ws-1", body));
    }

    @Test
    void testModifyComplexIntentBranch_Success() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            ComplexIntentBranchEntity branchEntity = new ComplexIntentBranchEntity();
            branchEntity.setBranchId("branch-1");
            when(complexIntentBranchMapper.getByKeyAndWorkspaceId("branch-1", "intent-1", "proj-1", "ws-1"))
                .thenReturn(branchEntity);
            when(complexIntentBranchMapper.getEntitiesAccurate(any())).thenReturn(new ArrayList<>());

            ComplexIntentBranchInfoReq body = new ComplexIntentBranchInfoReq();
            body.setBranchId("branch-1");
            body.setName("updated-branch");
            body.setExamples(List.of("ex1"));

            ComplexIntentBranchBriefRsp result = complexIntentManagementService.modifyComplexIntentBranch(
                "proj-1", "intent-1", "branch-1", "ws-1", body);
            assertNotNull(result);
            assertEquals("branch-1", result.getBranchId());
        }
    }

    @Test
    void testModifyComplexIntentBranch_NullBranchId_CreatesNew() {
        try (MockedStatic<RequestContextUtils> reqCtx = mockStatic(RequestContextUtils.class)) {
            reqCtx.when(RequestContextUtils::getRequestUserId).thenReturn("user-1");

            ComplexIntentEntity originEntity = new ComplexIntentEntity();
            originEntity.setIntentId("intent-1");
            when(complexIntentMapper.getByKeyAndWorkspaceId("intent-1", "proj-1", "ws-1")).thenReturn(originEntity);

            ComplexIntentBranchInfoReq body = new ComplexIntentBranchInfoReq();
            body.setName("new-branch");
            body.setExamples(List.of("ex1"));

            when(complexIntentBranchMapper.getEntities(any())).thenReturn(new ArrayList<>());
            when(complexIntentBranchMapper.maxBranchIndex(anyString(), anyString(), anyString())).thenReturn(null);
            when(complexIntentBranchMapper.countBranch(anyString(), anyString(), anyString())).thenReturn(1);

            ComplexIntentBranchBriefRsp result = complexIntentManagementService.modifyComplexIntentBranch(
                "proj-1", "intent-1", "branch-1", "ws-1", body);
            assertNotNull(result);
            assertNotNull(result.getBranchId());
        }
    }

    @Test
    void testExportIntentTemplate_Success() {
        try (MockedStatic<LanguageUtils> langUtils = mockStatic(LanguageUtils.class)) {
            langUtils.when(LanguageUtils::getLanguageLocale).thenReturn(Locale.CHINESE);
            when(messageSource.getMessage(anyString(), any(), any(Locale.class))).thenReturn("意图模板");

            Resource result = complexIntentManagementService.exportIntentTemplate("proj-1", "ws-1");
            assertNotNull(result);
        }
    }
}
