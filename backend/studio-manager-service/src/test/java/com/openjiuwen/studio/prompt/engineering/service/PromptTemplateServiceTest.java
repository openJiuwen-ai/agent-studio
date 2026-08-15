/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static com.openjiuwen.studio.prompt.engineering.constant.CommonConstant.REQUIRED_FIELD_MISSING;
import static org.mockito.Answers.RETURNS_DEEP_STUBS;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.dto.ManualPePromptTemplateDto;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateDto;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateListVo;
import com.openjiuwen.studio.prompt.engineering.dto.QueryTemplateCondition;
import com.openjiuwen.studio.prompt.engineering.entity.Industry;
import com.openjiuwen.studio.prompt.engineering.entity.PePromptTemplate;
import com.openjiuwen.studio.prompt.engineering.entity.PeTag;
import com.openjiuwen.studio.prompt.engineering.entity.PeTask;
import com.openjiuwen.studio.prompt.engineering.mapper.PeIndustryMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PePromptTemplateMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PeTagMapper;
import com.openjiuwen.studio.prompt.engineering.mapper.PeTaskMapper;
import com.openjiuwen.studio.prompt.engineering.utils.ExcelI18nHandler;

import com.alibaba.excel.EasyExcel;
import cn.afterturn.easypoi.handler.inter.II18nHandler;
import jakarta.servlet.http.HttpServletResponse;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * PromptTemplateService 单元测试
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class PromptTemplateServiceTest {

    @Mock
    private PePromptTemplateMapper pePromptTemplateMapper;

    @Mock
    private PromptTransactionService conversionTransaction;

    @InjectMocks
    private PromptTemplateService promptTemplateService;

    @Mock
    private MessageSource messageSource;

    @Mock
    private ShareInnerPromptService shareInnerPromptService;

    @Mock
    private PeTaskMapper peTaskMapper;

    @Mock
    private PeIndustryMapper industryMapper;

    @Mock
    private PeTagMapper tagMapper;

    @Mock
    private HttpServletResponse response;

    @InjectMocks
    private II18nHandler i18nHandler = new ExcelI18nHandler(messageSource);

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(promptTemplateService, "templateQuota", 500);
        ReflectionTestUtils.setField(promptTemplateService, "templateDownloadQuota", 100);
        ReflectionTestUtils.setField(promptTemplateService, "promptContentMaxLength", 10000);
        ReflectionTestUtils.setField(promptTemplateService, "templateImportQuota", 100);
        ReflectionTestUtils.setField(promptTemplateService, "adminName", "op_svc");
        ReflectionTestUtils.setField(promptTemplateService, "isSoftDelete", true);
    }

    // ========== savePromptTemplate ==========

    @Test
    void testSavePromptTemplate_Success() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        String name = "Template1";
        PePromptTemplateDto promptTemplateDto = new PePromptTemplateDto();
        promptTemplateDto.setName(name);
        promptTemplateDto.setTags(Collections.singletonList("tag1"));
        promptTemplateDto.setSource("PRESET");

        when(pePromptTemplateMapper.isNameExist(anyString(), anyString(), anyString(), anyString())).thenReturn(false);
        when(pePromptTemplateMapper.countTemplateByProjectId(anyString(), anyString())).thenReturn(10);
        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("test");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.savePromptTemplate(projectId, workspaceId, promptTemplateDto);

            assertEquals(HttpStatus.OK.toString(), result);
            verify(pePromptTemplateMapper).isNameExist(name, null, projectId, workspaceId);
            verify(pePromptTemplateMapper).countTemplateByProjectId(projectId, workspaceId);
            verify(conversionTransaction).insertOneTemplate(any(PePromptTemplate.class), anyList(), eq(projectId));
        }
    }

    @Test
    void testSavePromptTemplate_ExceedsQuota() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        String name = "Template1";
        PePromptTemplateDto promptTemplateDto = new PePromptTemplateDto();
        promptTemplateDto.setName(name);

        when(pePromptTemplateMapper.isNameExist(anyString(), anyString(), anyString(), anyString())).thenReturn(false);
        when(pePromptTemplateMapper.countTemplateByProjectId(anyString(), anyString())).thenReturn(500);
        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("test");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.savePromptTemplate(projectId, workspaceId, promptTemplateDto));
            verify(pePromptTemplateMapper).isNameExist(name, null, projectId, workspaceId);
            verify(pePromptTemplateMapper).countTemplateByProjectId(projectId, workspaceId);
        }
    }

    @Test
    void testSavePromptTemplate_NameDuplicate_Throws() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        PePromptTemplateDto dto = new PePromptTemplateDto();
        dto.setName("重复名称");

        when(pePromptTemplateMapper.isNameExist("重复名称", null, projectId, workspaceId)).thenReturn(true);

        assertThrows(AgentStudioException.class,
            () -> promptTemplateService.savePromptTemplate(projectId, workspaceId, dto));
    }

    // ========== downloadPromptTemplateV2 ==========

    @Test
    void testDownloadPromptTemplateV2() {
        String projectId = "project-123";
        String workspaceId = "workspace-123";
        List<String> templateIds = new ArrayList<>();
        templateIds.add("template");

        PePromptTemplate vo1 = new PePromptTemplate();
        vo1.setName("模板1");
        vo1.setContent("内容1");
        vo1.setDescription("描述1");
        vo1.setVariables("变量1");
        vo1.setIndustry(new Industry());
        vo1.setCreator("创建人1");

        List<PePromptTemplate> templateDownloadVos = new ArrayList<>();
        templateDownloadVos.add(vo1);

        when(pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(anyList())).thenReturn(templateDownloadVos);
        when(pePromptTemplateMapper.queryTemplateDetailByPersonTemplateIds(anyList(), anyString())).thenReturn(
            templateDownloadVos);

        assertThrows(AgentStudioException.class, () -> {
            promptTemplateService.downloadPromptTemplateV2(projectId, workspaceId, templateIds);
        });
    }

    @Test
    void testDownloadPromptTemplateV2_ExceedsQuota() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        List<String> templateIds = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            templateIds.add("tmpl-" + i);
        }

        assertThrows(AgentStudioException.class,
            () -> promptTemplateService.downloadPromptTemplateV2(projectId, workspaceId, templateIds));
    }

    @Test
    void testImportPromptTemplateV2_RowCountExceedsLimit() {
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        List<List<String>> head = List.of(
            List.of("模板名称"),
            List.of("模板内容"),
            List.of("模板描述"),
            List.of("标签"),
            List.of("行业"),
            List.of("变量")
        );
        List<List<String>> rows = new ArrayList<>();
        for (int index = 0; index < 101; index++) {
            rows.add(List.of("模板" + index, "内容" + index, "描述", "", "", ""));
        }
        EasyExcel.write(outputStream).head(head).sheet().doWrite(rows);
        MockMultipartFile file = new MockMultipartFile(
            "file",
            "templates.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            outputStream.toByteArray()
        );

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            AgentStudioException exception = assertThrows(AgentStudioException.class,
                () -> promptTemplateService.importPromptTemplateV2("workspace1", "project1", file));

            assertEquals(StudioError.PROMPT_TEMPLATE_IMPORT_NUM_EXCEED, exception.getErrorCode());
        }
    }

    // ========== createPromptTemplate ==========

    @Test
    void testCreatePromptTemplate_Success() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        PePromptTemplateDto body = new PePromptTemplateDto();
        body.setName("测试模板");
        body.setTaskId("task-001");

        when(peTaskMapper.isIdExist("task-001", workspaceId)).thenReturn(true);
        when(pePromptTemplateMapper.isNameExist("测试模板", null, projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.countTemplateByProjectId(projectId, workspaceId)).thenReturn(10);

        PeTask task = PeTask.builder().id("task-001").industry(new Industry()).workspaceId(workspaceId).build();
        when(peTaskMapper.queryTaskDetailsByTaskIds(Collections.singletonList("task-001"), workspaceId))
            .thenReturn(Collections.singletonList(task));
        when(peTaskMapper.queryTagIdsByTaskId("task-001", workspaceId)).thenReturn(Collections.emptyList());

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.createPromptTemplate(projectId, workspaceId, body);
            assertEquals(HttpStatus.OK.toString(), result);
        }
    }

    @Test
    void testCreatePromptTemplate_TaskNotExist() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        PePromptTemplateDto body = new PePromptTemplateDto();
        body.setName("测试模板");
        body.setTaskId("task-999");

        when(peTaskMapper.isIdExist("task-999", workspaceId)).thenReturn(false);

        assertThrows(AgentStudioException.class,
            () -> promptTemplateService.createPromptTemplate(projectId, workspaceId, body));
    }

    @Test
    void testCreatePromptTemplate_NameExist() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        PePromptTemplateDto body = new PePromptTemplateDto();
        body.setName("重复名称");
        body.setTaskId("task-001");

        when(peTaskMapper.isIdExist("task-001", workspaceId)).thenReturn(true);
        when(pePromptTemplateMapper.isNameExist("重复名称", null, projectId, workspaceId)).thenReturn(true);

        assertThrows(AgentStudioException.class,
            () -> promptTemplateService.createPromptTemplate(projectId, workspaceId, body));
    }

    @Test
    void testCreatePromptTemplate_ExceedsQuota() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        PePromptTemplateDto body = new PePromptTemplateDto();
        body.setName("测试模板");
        body.setTaskId("task-001");

        when(peTaskMapper.isIdExist("task-001", workspaceId)).thenReturn(true);
        when(pePromptTemplateMapper.isNameExist("测试模板", null, projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.countTemplateByProjectId(projectId, workspaceId)).thenReturn(500);

        assertThrows(AgentStudioException.class,
            () -> promptTemplateService.createPromptTemplate(projectId, workspaceId, body));
    }

    @Test
    void testCreatePromptTemplate_InnerException_Throws() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        PePromptTemplateDto body = new PePromptTemplateDto();
        body.setName("测试模板");
        body.setTaskId("task-001");

        when(peTaskMapper.isIdExist("task-001", workspaceId)).thenReturn(true);
        when(pePromptTemplateMapper.isNameExist("测试模板", null, projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.countTemplateByProjectId(projectId, workspaceId)).thenReturn(10);

        PeTask task = PeTask.builder().id("task-001").industry(new Industry()).workspaceId(workspaceId).build();
        when(peTaskMapper.queryTaskDetailsByTaskIds(Collections.singletonList("task-001"), workspaceId))
            .thenReturn(Collections.singletonList(task));
        when(peTaskMapper.queryTagIdsByTaskId("task-001", workspaceId)).thenReturn(Collections.emptyList());

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            doThrow(new RuntimeException("DB error")).when(conversionTransaction)
                .insertOneTemplate(any(PePromptTemplate.class), anyList(), anyString());

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.createPromptTemplate(projectId, workspaceId, body));
        }
    }

    // ========== deletePromptTemplate ==========

    @Test
    void testDeletePromptTemplate_Success() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("NO_SOURCE");
        template.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.singletonList(template));
        when(shareInnerPromptService.cancelPromptShared(templateId, projectId, workspaceId)).thenReturn(true);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.deletePromptTemplate(projectId, templateId, workspaceId);
            assertEquals(templateId, result);
        }
    }

    @Test
    void testDeletePromptTemplate_NotExist() {
        String projectId = "project1";
        String templateId = "tmpl-999";
        String workspaceId = "workspace1";

        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.emptyList());

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.deletePromptTemplate(projectId, templateId, workspaceId));
        }
    }

    @Test
    void testDeletePromptTemplate_PresetNoAdmin() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("PRESET");
        template.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.singletonList(template));

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.deletePromptTemplate(projectId, templateId, workspaceId));
        }
    }

    @Test
    void testDeletePromptTemplate_SharedResource() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("NO_SOURCE");
        template.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.singletonList(template));

        when(shareInnerPromptService.cancelPromptShared(templateId, projectId, workspaceId))
            .thenThrow(new AgentStudioException(com.openjiuwen.studio.agent.common.enums.StudioError.SHARE_RESOURCE_CANNOT_BE_DELETE_DIRECTLY));

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.deletePromptTemplate(projectId, templateId, workspaceId));
        }
    }

    @Test
    void testDeletePromptTemplate_SoftDelete() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("NO_SOURCE");
        template.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.singletonList(template));
        when(shareInnerPromptService.cancelPromptShared(templateId, projectId, workspaceId)).thenReturn(true);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.deletePromptTemplate(projectId, templateId, workspaceId);
            assertEquals(templateId, result);
            verify(pePromptTemplateMapper).copyToHistory(templateId, workspaceId, "[]");
            verify(pePromptTemplateMapper).unbindTemplateIdAndTagId(templateId, workspaceId);
            verify(pePromptTemplateMapper).deleteTemplateByTemplateId(templateId, workspaceId);
        }
    }

    @Test
    void testDeletePromptTemplate_SoftDeleteWithTags() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PeTag tag1 = new PeTag();
        tag1.setId("tag-001");
        tag1.setName("标签1");
        PeTag tag2 = new PeTag();
        tag2.setId("tag-002");
        tag2.setName("标签2");

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("NO_SOURCE");
        template.setTags(List.of(tag1, tag2));
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.singletonList(template));
        when(shareInnerPromptService.cancelPromptShared(templateId, projectId, workspaceId)).thenReturn(true);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.deletePromptTemplate(projectId, templateId, workspaceId);
            assertEquals(templateId, result);
            verify(pePromptTemplateMapper).copyToHistory(eq(templateId), eq(workspaceId), anyString());
        }
    }

    // ========== batchDeletePromptTemplate ==========

    @Test
    void testBatchDelete_Success() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        List<String> templateIds = List.of("tmpl-001", "tmpl-002");

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("NO_SOURCE");
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(templateIds, workspaceId))
            .thenReturn(List.of(template));

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.batchDeletePromptTemplate(projectId, workspaceId, templateIds);
            assertEquals(HttpStatus.OK.toString(), result);
            verify(pePromptTemplateMapper).batchUnbindTemplateIdAndTagId(templateIds, workspaceId);
            verify(pePromptTemplateMapper).batchDeleteTemplateByTemplateId(templateIds, workspaceId);
        }
    }

    @Test
    void testBatchDelete_NotExist_Throws() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        List<String> templateIds = List.of("tmpl-999");

        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(templateIds, workspaceId))
            .thenReturn(Collections.emptyList());

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.batchDeletePromptTemplate(projectId, workspaceId, templateIds));
        }
    }

    @Test
    void testBatchDelete_PresetNoAdmin_Throws() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        List<String> templateIds = List.of("tmpl-001");

        PePromptTemplate template = new PePromptTemplate();
        template.setSource("PRESET");
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(templateIds, workspaceId))
            .thenReturn(List.of(template));

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.batchDeletePromptTemplate(projectId, workspaceId, templateIds));
        }
    }

    // ========== listPromptTemplates ==========

    @Test
    void testListPromptTemplates_Success() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        String category = null;
        QueryTemplateCondition body = new QueryTemplateCondition();
        body.setLimit(10);
        body.setOffset(0);

        when(pePromptTemplateMapper.queryTemplateIdsByCondition(body, projectId, workspaceId, category))
            .thenReturn(Collections.singletonList("tmpl-001"));

        PePromptTemplate template = new PePromptTemplate();
        template.setId("tmpl-001");
        template.setName("测试");
        template.setSource("NO_SOURCE");
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateId(Collections.singletonList("tmpl-001"), workspaceId))
            .thenReturn(Collections.singletonList(template));

        PePromptTemplateListVo result = promptTemplateService.listPromptTemplates(projectId, workspaceId, category, body);
        assertNotNull(result);
    }

    @Test
    void testListPromptTemplates_NoResults() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        QueryTemplateCondition body = new QueryTemplateCondition();
        body.setLimit(10);
        body.setOffset(0);

        when(pePromptTemplateMapper.queryTemplateIdsByCondition(body, projectId, workspaceId, null))
            .thenReturn(Collections.emptyList());

        PePromptTemplateListVo result = promptTemplateService.listPromptTemplates(projectId, workspaceId, null, body);
        assertNotNull(result);
    }

    // ========== updatePromptTemplate ==========

    @Test
    void testUpdatePromptTemplate_Success() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setId("tmpl-001");
        body.setName("更新模板");
        body.setSource("NO_SOURCE");
        body.setTagList(Collections.emptyList());

        when(pePromptTemplateMapper.isNameExist("更新模板", "tmpl-001", projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.updateTemplate(any(PePromptTemplate.class), any())).thenReturn(1);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.updatePromptTemplate(projectId, workspaceId, body);
            assertEquals(HttpStatus.OK.toString(), result);
        }
    }

    @Test
    void testUpdatePromptTemplate_NotAdmin() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setId("tmpl-001");
        body.setName("更新模板");
        body.setSource("PRESET");
        body.setTagList(Collections.emptyList());

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.updatePromptTemplate(projectId, workspaceId, body));
        }
    }

    @Test
    void testUpdatePromptTemplate_NameExist() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setId("tmpl-001");
        body.setName("重复名称");
        body.setSource("NO_SOURCE");
        body.setTagList(Collections.emptyList());

        when(pePromptTemplateMapper.isNameExist("重复名称", "tmpl-001", projectId, workspaceId)).thenReturn(true);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.updatePromptTemplate(projectId, workspaceId, body));
        }
    }

    @Test
    void testUpdatePromptTemplate_DataNotExist_Throws() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setId("tmpl-999");
        body.setName("不存在");
        body.setSource("NO_SOURCE");
        body.setTagList(Collections.emptyList());

        when(pePromptTemplateMapper.isNameExist("不存在", "tmpl-999", projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.updateTemplate(any(PePromptTemplate.class), any())).thenReturn(0);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("testUser");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.updatePromptTemplate(projectId, workspaceId, body));
        }
    }

    // ========== queryPromptTemplate ==========

    @Test
    void testQueryPromptTemplate_Success() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PePromptTemplate template = new PePromptTemplate();
        template.setId(templateId);
        template.setName("测试模板");
        template.setCreatedOn(new Date());
        template.setUpdatedOn(new Date());
        template.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(Collections.singletonList(templateId)))
            .thenReturn(Collections.singletonList(template));

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(projectId);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(workspaceId);

            var result = promptTemplateService.queryPromptTemplate(projectId, templateId, workspaceId);
            assertNotNull(result);
            assertEquals("测试模板", result.getTemplateName());
        }
    }

    @Test
    void testQueryPromptTemplate_OfficialFirst() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        PePromptTemplate officialTemplate = new PePromptTemplate();
        officialTemplate.setId(templateId);
        officialTemplate.setName("官方模板");
        officialTemplate.setCreatedOn(new Date());
        officialTemplate.setUpdatedOn(new Date());
        officialTemplate.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(Collections.singletonList(templateId)))
            .thenReturn(Collections.singletonList(officialTemplate));

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(projectId);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(workspaceId);

            var result = promptTemplateService.queryPromptTemplate(projectId, templateId, workspaceId);
            assertNotNull(result);
            assertEquals("官方模板", result.getTemplateName());
            verify(pePromptTemplateMapper, never()).queryTemplateDetailByTemplateIds(anyList(), anyString());
        }
    }

    @Test
    void testQueryPromptTemplate_FallbackToPersonalWorkspace() {
        String projectId = "project1";
        String templateId = "tmpl-001";
        String workspaceId = "workspace1";

        when(pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(Collections.singletonList(templateId)))
            .thenReturn(Collections.emptyList());

        PePromptTemplate personalTemplate = new PePromptTemplate();
        personalTemplate.setId(templateId);
        personalTemplate.setName("个人模板");
        personalTemplate.setCreatedOn(new Date());
        personalTemplate.setUpdatedOn(new Date());
        personalTemplate.setTags(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.singletonList(personalTemplate));

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(projectId);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(workspaceId);

            var result = promptTemplateService.queryPromptTemplate(projectId, templateId, workspaceId);
            assertNotNull(result);
            assertEquals("个人模板", result.getTemplateName());
        }
    }

    @Test
    void testQueryPromptTemplate_NotFound_Throws() {
        String projectId = "project1";
        String templateId = "tmpl-999";
        String workspaceId = "workspace1";

        when(pePromptTemplateMapper.queryTemplateDetailByCreatorTemplateIds(Collections.singletonList(templateId)))
            .thenReturn(Collections.emptyList());
        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(Collections.singletonList(templateId), workspaceId))
            .thenReturn(Collections.emptyList());

        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestProjectId).thenReturn(projectId);
            mocked.when(RequestContextUtils::getRequestWorkspaceId).thenReturn(workspaceId);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.queryPromptTemplate(projectId, templateId, workspaceId));
        }
    }

    // ========== manualCreatePromptTemplate ==========

    @Test
    void testManualCreate_Success() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setName("预置模板");
        body.setTagList(Collections.emptyList());

        when(pePromptTemplateMapper.isNameExist("预置模板", null, projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.countPresetTemplateByProjectId(projectId, workspaceId)).thenReturn(10);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("admin");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            String result = promptTemplateService.manualCreatePromptTemplate(projectId, workspaceId, body);
            assertEquals(HttpStatus.OK.toString(), result);
        }
    }

    @Test
    void testManualCreate_NotAdmin() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setName("预置模板");
        body.setTagList(Collections.emptyList());

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("normalUser");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.manualCreatePromptTemplate(projectId, workspaceId, body));
        }
    }

    @Test
    void testManualCreate_ExceedsQuota() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setName("预置模板");
        body.setTagList(Collections.emptyList());

        when(pePromptTemplateMapper.isNameExist("预置模板", null, projectId, workspaceId)).thenReturn(false);
        when(pePromptTemplateMapper.countPresetTemplateByProjectId(projectId, workspaceId)).thenReturn(500);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("admin");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.manualCreatePromptTemplate(projectId, workspaceId, body));
        }
    }

    @Test
    void testManualCreate_NameDuplicate_Throws() {
        String projectId = "project1";
        String workspaceId = "workspace1";
        ManualPePromptTemplateDto body = new ManualPePromptTemplateDto();
        body.setName("重复名");
        body.setTagList(Collections.emptyList());

        when(pePromptTemplateMapper.isNameExist("重复名", null, projectId, workspaceId)).thenReturn(true);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("admin");
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertThrows(AgentStudioException.class,
                () -> promptTemplateService.manualCreatePromptTemplate(projectId, workspaceId, body));
        }
    }

    // ========== checkAuth ==========

    @Test
    void testCheckAuth_Admin() {
        SimpleUser userInfo = new SimpleUser();
        userInfo.setDomainName("op_svc");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertTrue(promptTemplateService.checkAuth("project1", "workspace1"));
        }
    }

    @Test
    void testCheckAuth_NotAdmin() {
        SimpleUser userInfo = new SimpleUser();
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            assertFalse(promptTemplateService.checkAuth("project1", "workspace1"));
        }
    }

    @Test
    void testCheckAuth_NullUser() {
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(null);

            boolean result = promptTemplateService.checkAuth("project1", "workspace1");
            assertFalse(result);
        }
    }

    // ========== importPromptTemplateV2（修复：导入失败提示不明确） ==========

    @Test
    void testImportV2_HeaderMismatch_ThrowsExcelHeaderError() throws IOException {
        // 表头与模板不一致：应抛出 EXCEL_HEADER_ERROR，而不是被统一包装成 UPLOAD_FILE_FAILED
        byte[] content = buildExcelBytes(List.of("错误表头", "模板内容", "描述", "标签", "行业", "变量"),
            List.of(List.of("名称A", "内容A", "", "", "金融", "")));
        MockMultipartFile file = new MockMultipartFile("file", "header_mismatch.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", content);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("test");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> promptTemplateService.importPromptTemplateV2("workspace1", "project1", file));
            assertEquals(StudioError.EXCEL_HEADER_ERROR, ex.getErrorCode());
        }
    }

    @Test
    void testImportV2_EmptyTemplateName_ReturnsRequiredFieldMessage() throws IOException {
        // 必填项"模板名称"为空：应返回明确的必填提示，而不是抛 NPE 后被包装成 UPLOAD_FILE_FAILED
        byte[] content = buildExcelBytes(List.of("模板名称", "模板内容", "描述", "标签", "行业", "变量"),
            List.of(Arrays.asList(null, "内容A", null, null, "金融", null)));
        MockMultipartFile file = new MockMultipartFile("file", "empty_template_name.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", content);

        when(messageSource.getMessage(anyString(), any(), any(Locale.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));
        Industry industry = mock(Industry.class);
        when(industry.getName()).thenReturn("金融");
        when(industry.getId()).thenReturn("industry-1");
        when(industryMapper.queryAll()).thenReturn(List.of(industry));
        when(tagMapper.queryAll()).thenReturn(Collections.emptyList());
        when(pePromptTemplateMapper.countPresetTemplateByProjectId("project1", "workspace1")).thenReturn(0);

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("test");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            List<String> messages = promptTemplateService.importPromptTemplateV2("workspace1", "project1", file);

            assertEquals(1, messages.size());
            assertTrue(messages.get(0).contains(REQUIRED_FIELD_MISSING));
        }
    }

    @Test
    void testImportV2_CorruptedFile_ThrowsExcelHeaderError() {
        // 损坏文件解析后表头为空，DynamicExcelListener 抛出 EXCEL_HEADER_ERROR（业务异常），
        // 修复后该异常被原样透传，前端可得到明确的表头错误提示，而不再被包装成 UPLOAD_FILE_FAILED
        MockMultipartFile file = new MockMultipartFile("file", "corrupt.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", new byte[] {0, 1, 2, 3});

        SimpleUser userInfo = new SimpleUser();
        userInfo.setUserName("test");
        userInfo.setDomainName("normal_domain");
        try (MockedStatic<RequestContextUtils> mocked = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mocked.when(RequestContextUtils::getRequestUser).thenReturn(userInfo);

            AgentStudioException ex = assertThrows(AgentStudioException.class,
                () -> promptTemplateService.importPromptTemplateV2("workspace1", "project1", file));
            assertEquals(StudioError.EXCEL_HEADER_ERROR, ex.getErrorCode());
        }
    }

    /**
     * 构造内存中的 xlsx 文件字节，表头固定为第一行；值为 null 的单元格不写入（模拟空单元格）
     */
    private byte[] buildExcelBytes(List<String> header, List<List<String>> rows) throws IOException {
        try (XSSFWorkbook workbook = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            XSSFSheet sheet = workbook.createSheet("Sheet1");
            XSSFRow headerRow = sheet.createRow(0);
            for (int i = 0; i < header.size(); i++) {
                headerRow.createCell(i).setCellValue(header.get(i));
            }
            for (int r = 0; r < rows.size(); r++) {
                XSSFRow row = sheet.createRow(r + 1);
                List<String> values = rows.get(r);
                for (int c = 0; c < values.size(); c++) {
                    if (values.get(c) != null) {
                        row.createCell(c).setCellValue(values.get(c));
                    }
                }
            }
            workbook.write(out);
            return out.toByteArray();
        }
    }
}
