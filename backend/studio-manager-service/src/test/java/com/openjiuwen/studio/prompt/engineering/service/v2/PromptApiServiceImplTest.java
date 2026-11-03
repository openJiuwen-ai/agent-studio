/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.prompt.engineering.service.v2;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Answers.RETURNS_DEEP_STUBS;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.github.pagehelper.PageInfo;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.prompt.engineering.dto.CreatePromptResp;
import com.openjiuwen.studio.prompt.engineering.dto.GetPromptListsQo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptNewListVo;
import com.openjiuwen.studio.prompt.engineering.dto.PePromptTemplateNewVo;
import com.openjiuwen.studio.prompt.engineering.entity.Industry;
import com.openjiuwen.studio.prompt.engineering.entity.PePromptTemplate;
import com.openjiuwen.studio.prompt.engineering.mapper.PePromptTemplateMapper;
import com.openjiuwen.studio.prompt.engineering.service.PromptTransactionService;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.springframework.beans.BeanUtils;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.List;

/**
 * promptApiService 的单元测试类，用于验证 createCustomPromptApiAction 方法的行为
 */
class PromptApiServiceImplTest {
    private static final String PROJECT_ID = "project_id";

    private static final String WORKSPACE_ID = "workspace_id";

    private static final String CONNECTOR_ID = "connector_id";

    private static final String PROMPT_ID = "prompt_id";

    @Mock
    private PePromptTemplateMapper pePromptTemplateMapper;

    @Mock
    private PromptTransactionService conversionTransaction;

    // 将模拟对象注入到 promptApiService 实例中，以便在测试中使用这些模拟依赖
    @InjectMocks
    private PromptApiServiceImpl promptApiService;

    // 用于管理 Mockito 模拟对象的生命周期，确保每次测试后正确关闭资源
    private AutoCloseable mockitoCloseable;

    @BeforeEach
    void setUp() {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(promptApiService, "templateQuota", 500);
    }

    /**
     * 在每个测试方法执行后关闭 Mockito 模拟对象，释放相关资源
     *
     * @throws Exception 如果关闭过程中发生异常
     */
    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }


    /**
     * 测试 createCustomPromptApiAction 方法在正常参数下的行为
     * 验证方法是否能正确返回非空结果
     */
    @Test
    public void test_createCustomPromptApiAction_normal() {
        // Given: 准备测试数据
        PePromptTemplateNewVo body = new PePromptTemplateNewVo();
        body.setName("test-name");
        body.setSource("PLAYGROUND");
        body.setIndustryId("test-industry");
        body.setTags(Arrays.asList("tag1", "tag2"));
        body.setPtType("multi");
        body.setVariables("[{\"name\":\"rt\",\"content\":\"good\",\"type\":\"text\"},{\"name\":\"drt\",\"content\":\"excellent\",\"type\":\"multi\"}]");
        // 模拟用户信息
        SimpleUser mockUserInfo = new SimpleUser();
        mockUserInfo.setUserName("RT");
        mockUserInfo.setDomainName("RT");

        // 模拟 RequestContextUtils
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class,
            RETURNS_DEEP_STUBS)) {
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUser()).thenReturn(mockUserInfo);
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("RT-TEST");

            // 模拟 pePromptTemplateMapper
            doReturn(false).when(pePromptTemplateMapper)
                .isNameExist(anyString(), anyString(), anyString(), anyString());
            doReturn(1).when(pePromptTemplateMapper).countPresetTemplateByProjectId(anyString(), anyString());
            doNothing().when(conversionTransaction)
                .insertOneTemplate(any(PePromptTemplate.class), anyList(), anyString());
            // When: 调用方法
            String result = promptApiService.createCustomPromptApiAction(PROJECT_ID, WORKSPACE_ID, body);

            // Then: 验证结果
            assertNotNull(result);
        }
    }

    /**
     * 测试 createCustomPromptApiAction 方法在正常参数下的行为
     * 验证方法是否能正确返回非空结果
     */
    @Test
    public void test_savePromptTemplate_exception1() {
        // Given: 准备测试数据
        PePromptTemplateNewVo body = new PePromptTemplateNewVo();
        body.setName("test-name");
        body.setSource("PLAYGROUND");
        body.setIndustryId("test-industry");
        body.setTags(Arrays.asList("tag1", "tag2"));
        body.setPtType("multi");
        body.setVariables("[{\"name\":\"rt\",\"content\":\"good\",\"type\":\"text\"},{\"name\":\"drt\",\"content\":\"excellent\",\"type\":\"multi\"}]");
        // 模拟用户信息
        SimpleUser mockUserInfo = new SimpleUser();
        mockUserInfo.setUserName("RT");
        mockUserInfo.setDomainName("RT");

        // 模拟 RequestContextUtils
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class,
                RETURNS_DEEP_STUBS)) {
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUser()).thenReturn(mockUserInfo);
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("RT-TEST");

            // 模拟 pePromptTemplateMapper
            doReturn(false).when(pePromptTemplateMapper)
                    .isNameExist(anyString(), anyString(), anyString(), anyString());
            doReturn(501).when(pePromptTemplateMapper).countTemplateByProjectId(anyString(), anyString());
            doNothing().when(conversionTransaction)
                    .insertOneTemplate(any(PePromptTemplate.class), anyList(), anyString());
            // When & Then: 调用方法并断言抛出异常
            assertThrows(AgentStudioException.class, () -> {
                promptApiService.savePromptTemplate(PROJECT_ID, WORKSPACE_ID, body);
            });
        }
    }

    @Test
    public void test_savePromptTemplate_exception2() {
        // Given: 准备测试数据
        String templateId = "test-id";

        PePromptTemplateNewVo body = new PePromptTemplateNewVo();
        body.setId(templateId);
        body.setName("test-name");
        body.setSource("PLAYGROUND");
        body.setIndustryId("test-industry");
        body.setTags(Arrays.asList("tag1", "tag2"));
        body.setPtType("multi");

        // 模拟用户信息
        SimpleUser mockUserInfo = new SimpleUser();
        mockUserInfo.setDomainName("RT");

        // 模拟 RequestContextUtils
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUser()).thenReturn(mockUserInfo);
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("RT-TEST");

            // 模拟 pePromptTemplateMapper
            when(pePromptTemplateMapper.isNameExist(anyString(), anyString(), anyString(), anyString())).thenReturn(false);
            when(pePromptTemplateMapper.updateTemplate(any(PePromptTemplate.class), anyString())).thenReturn(1);
            when(pePromptTemplateMapper.queryTemplateIds(anyString(), anyString())).thenReturn(null);

            // When & Then: 调用方法并断言抛出异常
            assertThrows(AgentStudioException.class, () -> {
                promptApiService.savePromptTemplate(PROJECT_ID, WORKSPACE_ID, body);
            });
        }
    }

    @Test
    public void test_savePromptTemplate_exception3() {
        // 模拟 RequestContextUtils
        assertThrows(AgentStudioException.class, () -> {
            promptApiService.savePromptTemplate(PROJECT_ID, WORKSPACE_ID, null);
        });
    }


    @Test
    void test_deleteCustomConnectorAction_normal() {
        // When: 调用被测试的方法
        String result = promptApiService.deleteCustomConnectorAction(PROJECT_ID, WORKSPACE_ID, CONNECTOR_ID);

        // Then: 验证方法返回的结果不为 null
        assertNotNull(result);
    }

    @Test
    public void test_deleteCustomConnectorAction_exception1() {
        // When & Then: 调用方法并验证是否抛出 RuntimeException
        assertThrows(RuntimeException.class, () -> {
            promptApiService.deleteCustomConnectorAction(null, WORKSPACE_ID, CONNECTOR_ID);
        });
    }

    @Test
    public void test_deleteCustomConnectorAction_exception2() {
        // When & Then: 调用方法并验证是否抛出 RuntimeException
        assertThrows(RuntimeException.class, () -> {
            promptApiService.deleteCustomConnectorAction(PROJECT_ID, null, CONNECTOR_ID);
        });
    }

    @Test
    void test_getPromptLists_normal1() {
        GetPromptListsQo getPromptListsQo = new GetPromptListsQo();

        getPromptListsQo.setName("testPrompt");
        getPromptListsQo.setOffset(5);
        getPromptListsQo.setLimit(10);
        getPromptListsQo.setWorkspaceId(WORKSPACE_ID);

        when(pePromptTemplateMapper.queryTemplateIdsByCondition2(anyString(), anyString(), anyString())).thenReturn(List.of("test-id"));
        // When: 调用被测试的方法
        PePromptNewListVo result = promptApiService.getPromptLists(PROJECT_ID, getPromptListsQo);

        // Then: 验证方法返回的结果不为 null
        assertNotNull(result);
    }

    @Test
    void test_getPromptLists_normal2() {
        GetPromptListsQo getPromptListsQo = new GetPromptListsQo();
        getPromptListsQo.setName("testPrompt");
        getPromptListsQo.setOffset(5);
        getPromptListsQo.setLimit(10);
        getPromptListsQo.setWorkspaceId(WORKSPACE_ID);

        // 模拟 queryTemplateIdsByCondition2 返回非空的 List<String>
        List<String> templateIds = new ArrayList<>();
        templateIds.add("templateId1");
        templateIds.add("templateId2");

        when(pePromptTemplateMapper.queryTemplateIdsByCondition2(anyString(), anyString(), anyString()))
                .thenReturn(templateIds);

        // 模拟 queryTemplateDetailByTemplateIds 返回非空的 PePromptTemplate 列表
        List<PePromptTemplate> pePromptTemplates = new ArrayList<>();
        PePromptTemplate template1 = new PePromptTemplate();
        template1.setId("templateId1");
        template1.setName("模板1");
        template1.setContent("内容1");
        template1.setVariables("变量1");
        template1.setWorkspaceId(WORKSPACE_ID);

        PePromptTemplate template2 = new PePromptTemplate();
        template2.setId("templateId2");
        template2.setName("模板2");
        template2.setContent("内容2");
        template2.setVariables("变量2");
        template2.setCreator("用户2");
        template2.setWorkspaceId(WORKSPACE_ID);

        pePromptTemplates.add(template1);
        pePromptTemplates.add(template2);

        when(pePromptTemplateMapper.queryTemplateDetailByTemplateIds(anyList(), anyString()))
            .thenReturn(pePromptTemplates);

        // 模拟 BeanUtils.copyProperties
        try (MockedStatic<BeanUtils> mockedBeanUtils = mockStatic(BeanUtils.class)) {
            PageInfo<String> pageInfo = new PageInfo<>();
            pageInfo.setList(templateIds);
            pageInfo.setTotal(2);
            PageInfo<PePromptTemplateNewVo> targetPage = new PageInfo<>();
            mockedBeanUtils.when(() -> BeanUtils.copyProperties(targetPage, pageInfo)).thenAnswer(invocation -> null);

            // When: 调用被测试的方法
            PePromptNewListVo result = promptApiService.getPromptLists(PROJECT_ID, getPromptListsQo);

            // Then: 验证方法返回的结果不为 null
            assertNotNull(result);
        }
    }

    @Test
    public void test_getPromptLists_exception1() {
        // When & Then: 调用方法并验证是否抛出 RuntimeException
        assertThrows(RuntimeException.class, () -> {
            promptApiService.getPromptLists(PROJECT_ID, new GetPromptListsQo());
        });
    }

    @Test
    public void test_getPromptLists_exception2() {
        // When & Then: 调用方法并验证是否抛出 RuntimeException
        assertThrows(RuntimeException.class, () -> {
            promptApiService.getPromptLists(PROJECT_ID, null);
        });
    }

    @Test
    public void test_getPromptLists_exception3() {
        assertThrows(RuntimeException.class, () -> {
            promptApiService.getPromptLists(PROJECT_ID, new GetPromptListsQo());
        });
    }

    @Test
    void test_getPromptLists_exception4() {
        GetPromptListsQo getPromptListsQo = new GetPromptListsQo();

        getPromptListsQo.setName("testPrompt");
        getPromptListsQo.setLimit(10);
        getPromptListsQo.setWorkspaceId(WORKSPACE_ID);

        assertThrows(AgentStudioException.class, () -> {
            promptApiService.getPromptLists(PROJECT_ID, getPromptListsQo);
        });
    }

    /**
     * 测试 updateCustomPromptApiAction 方法在正常参数下的行为
     * 验证方法是否能正确返回非空结果
     */
    @Test
    public void test_updateCustomPromptApiAction_normal() {
        // Given: 准备测试数据
        String templateId = "test-id";

        PePromptTemplateNewVo body = new PePromptTemplateNewVo();
        body.setId(templateId);
        body.setName("test-name");
        body.setSource("PLAYGROUND");
        body.setIndustryId("test-industry");
        body.setTags(Arrays.asList("tag1", "tag2"));
        body.setPtType("multi");

        PePromptTemplate pePromptTemplate = new PePromptTemplate();
        pePromptTemplate.setId(templateId);
        // 模拟用户信息
        SimpleUser mockUserInfo = new SimpleUser();
        mockUserInfo.setUserName("RT");
        mockUserInfo.setDomainName("RT");

        // 模拟 RequestContextUtils
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUser()).thenReturn(mockUserInfo);
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("RT-TEST");

            // 模拟 pePromptTemplateMapper
            when(pePromptTemplateMapper.isNameExist(anyString(), anyString(), anyString(), anyString())).thenReturn(
                false);
            when(pePromptTemplateMapper.updateTemplate(any(PePromptTemplate.class), anyString())).thenReturn(1);
            when(pePromptTemplateMapper.queryTemplateIds(anyString(), anyString())).thenReturn(pePromptTemplate);

            // When: 调用方法
            CreatePromptResp result = promptApiService.updateCustomPromptApiAction(PROJECT_ID, WORKSPACE_ID, body);

            // Then: 验证结果
            assertNotNull(result);
            assertEquals(200, result.getCode());
            assertEquals("success to update", result.getMessage());
            assertEquals(templateId, result.getData());
        }
    }

    @Test
    public void test_updateCustomPromptApiAction_exception1() {
        assertThrows(AgentStudioException.class, () -> {
            promptApiService.updateCustomPromptApiAction(PROJECT_ID, WORKSPACE_ID, new PePromptTemplateNewVo());
        });
    }

    @Test
    public void test_updateCustomPromptApiAction_exception2() {
        // Given: 准备测试数据
        String templateId = "test-id";

        PePromptTemplateNewVo body = new PePromptTemplateNewVo();
        body.setId(templateId);
        body.setName("test-name");
        body.setSource("PLAYGROUND");
        body.setIndustryId("test-industry");
        body.setTags(Arrays.asList("tag1", "tag2"));
        body.setPtType("multi");

        PePromptTemplate pePromptTemplate = new PePromptTemplate();
        pePromptTemplate.setId(templateId);
        // 模拟用户信息
        SimpleUser mockUserInfo = new SimpleUser();
        mockUserInfo.setUserName("RT");
        mockUserInfo.setDomainName("RT");

        // 模拟 RequestContextUtils
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUser()).thenReturn(mockUserInfo);
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("RT-TEST");

            // 模拟 pePromptTemplateMapper
            when(pePromptTemplateMapper.isNameExist(anyString(), anyString(), anyString(), anyString())).thenReturn(
                    false);
            when(pePromptTemplateMapper.updateTemplate(any(PePromptTemplate.class), anyString())).thenReturn(0);
            when(pePromptTemplateMapper.queryTemplateIds(anyString(), anyString())).thenReturn(pePromptTemplate);

            // When & Then: 调用方法并断言抛出异常
            assertThrows(AgentStudioException.class, () -> {
                promptApiService.updateCustomPromptApiAction(PROJECT_ID, WORKSPACE_ID, body);
            });
        }
    }

    @Test
    public void test_updateCustomPromptApiAction_exception3() {
        // Given: 准备测试数据
        String templateId = "test-id";

        PePromptTemplateNewVo body = new PePromptTemplateNewVo();
        body.setId(templateId);
        body.setName("test-name");
        body.setSource("PLAYGROUND");
        body.setIndustryId("test-industry");
        body.setPtType("multi");

        PePromptTemplate pePromptTemplate = new PePromptTemplate();
        pePromptTemplate.setId(templateId);
        // 模拟用户信息
        SimpleUser mockUserInfo = new SimpleUser();
        mockUserInfo.setUserName("RT");
        mockUserInfo.setDomainName("RT");

        // 模拟 RequestContextUtils
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class, RETURNS_DEEP_STUBS)) {
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUser()).thenReturn(mockUserInfo);
            mockedRequestContext.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("RT-TEST");

            // 模拟 pePromptTemplateMapper
            when(pePromptTemplateMapper.isNameExist(anyString(), anyString(), anyString(), anyString())).thenReturn(
                    false);
            when(pePromptTemplateMapper.updateTemplate(any(PePromptTemplate.class), anyString())).thenReturn(1);
            when(pePromptTemplateMapper.queryTemplateIds(anyString(), anyString())).thenReturn(pePromptTemplate);

            // When: 调用方法
            CreatePromptResp result = promptApiService.updateCustomPromptApiAction(PROJECT_ID, WORKSPACE_ID, body);

            // Then: 验证结果
            assertNotNull(result);
            assertEquals(200, result.getCode());
            assertEquals("success to update", result.getMessage());
            assertEquals(templateId, result.getData());
        }
    }

    /**
     * 测试 copyCustomPromptApiAction 方法在正常参数下的行为
     * 验证方法是否能正确返回非空结果
     */
    @Test
    public void test_copyCustomPromptApiAction_normal() {
        PePromptTemplate pePromptTemplate = new PePromptTemplate();
        pePromptTemplate.setName("not_empty");
        Industry industry = new Industry();
        industry.setId("not_empty");
        pePromptTemplate.setIndustry(industry);
        when(pePromptTemplateMapper.queryTemplate(CONNECTOR_ID)).thenReturn(pePromptTemplate);
        when(pePromptTemplateMapper.isNameExist2(anyString(), eq(PROJECT_ID), eq(WORKSPACE_ID))).thenReturn(
            null); // 表示名称未被占用

        try (MockedStatic<RequestContextUtils> mockedUtils = mockStatic(RequestContextUtils.class)) {
            // 设置模拟行为
            mockedUtils.when(() -> RequestContextUtils.getRequestUserName()).thenReturn("testUser");

            // 调用被测试方法
            String result = promptApiService.copyCustomPromptApiAction(PROJECT_ID, WORKSPACE_ID, CONNECTOR_ID);

            // 断言
            assertNotNull(result);
        }
    }
}
