/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.plugin;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.HisIamInfo;
import com.openjiuwen.studio.agent.manager.dto.ToolReference;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowExportEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginAdapterImpl;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class PluginAdapterImplTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ToolMapper toolMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private PluginMapper pluginMapper;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private IPluginBase pluginBase;

    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private ShareInnerService shareInnerService;

    @Mock
    private EncryptionAdapter encryptionAdapter;

    @InjectMocks
    private PluginAdapterImpl pluginAdapterImpl;

    private AutoCloseable mockitoCloseable;

    @Mock
    private RedisClient redisClient;

    @BeforeEach
    void setUp() throws Exception {
        mockitoCloseable = MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(pluginAdapterImpl, "shareInnerService", shareInnerService);

        ReflectionTestUtils.setField(pluginAdapterImpl, "encryptionAdapter", encryptionAdapter);

        // 配置默认行为，防止报空指针
        // 当调用 encrypt/decrypt 时，直接返回原来的字符串，模拟加解密成功
        when(encryptionAdapter.encrypt(anyString(), anyString())).thenAnswer(i -> i.getArgument(0));
        when(encryptionAdapter.decrypt(anyString())).thenAnswer(i -> i.getArgument(0));
    }

    @AfterEach
    void tearDown() throws Exception {
        mockitoCloseable.close();
    }

    @Test
    void test_getToolReferences_should_return_not_null() throws Exception {
        // Given
        List<PluginEntity> pluginEntities = new ArrayList<>();
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setIcon("not_empty");
        pluginEntity.setRequestInfo("not_empty");
        pluginEntities.add(pluginEntity);
        ShareResourceEntity shareResourceEntity = new ShareResourceEntity();
        shareResourceEntity.setResourceId("0");
        List<ShareResourceEntity> shareResourceEntities = new ArrayList<>();
        shareResourceEntities.add(shareResourceEntity);
        // Given
        when(pluginMapper.selectByPrimaryIdAndToolIdsWithSearchCriteria(any(), any(), any(),
            eq(null))).thenReturn(pluginEntities);
        when(shareInnerService.getOriginSharedInfoByResourceId(anyList())).thenReturn(shareResourceEntities);

        List<String> pluginIds = new ArrayList<>();
        pluginIds.add("not_empty");

        // When
        List<ToolReference> result = pluginAdapterImpl.getToolReferences("not_empty", "not_empty", pluginIds);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getToolReferences_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(pluginMapper.selectByPrimaryIdAndToolIdsWithSearchCriteria(anyString(), anyString(), anyList(),
                    eq(null))).thenReturn(null);

            // When
            List<ToolReference> result = pluginAdapterImpl.getToolReferences(null, null, null);
        });
    }

    @Test
    void test_getToolReferences_should_return_not_null1() throws Exception {
        List<String> toolIds = new ArrayList<>();
        toolIds.add("testId");
        List<PluginEntity> pluginEntities = new ArrayList<>();
        PluginEntity plugin = new PluginEntity();
        plugin.setRequestInfo("{}");
        plugin.setType("inner");
        plugin.setIsFree(1);
        pluginEntities.add(plugin);
        ShareResourceEntity shareResourceEntity = new ShareResourceEntity();
        shareResourceEntity.setResourceId("0");
        List<ShareResourceEntity> shareResourceEntities = new ArrayList<>();
        shareResourceEntities.add(shareResourceEntity);
        // Given
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class)) {
            // 告诉 Mock：当代码请求 DomainID 时，返回 "test_domain_id"
            mockedRequestContext.when(RequestContextUtils::getRequestUserDomainId).thenReturn("test_domain_id");

            when(redisClient.get(any(), any())).thenReturn("5");
            when(pluginMapper.selectByPrimaryIdAndToolIdsWithSearchCriteria(any(), any(), any(),
                    eq(null))).thenReturn(pluginEntities);
            when(shareInnerService.getOriginSharedInfoByResourceId(anyList())).thenReturn(shareResourceEntities);

            // When
            List<ToolReference> result = pluginAdapterImpl.getToolReferences("test", "test", toolIds);

            // Then
            assertNotNull(result);
        }
    }

    @Test
    void test_isNewTool_should_return_true() throws Exception {
        // Given
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setRequestInfo("not_empty");

        // When
        boolean result = pluginAdapterImpl.isNewTool(pluginEntity);

        // Then
        assertFalse(result);
    }

    @Test
    void test_isNewTool_should_return_true1() throws Exception {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setRequestInfo(
                "{\"basic_info\":{\"host\":\"xybh.comasdad\",\"path\":\"/\",\"protocol\":\"https\"},\"tool_info\":[{\"tool_id\":\"bc60fd357b4847c7\",\"tool_display_name\":\"qweq\",\"tool_chinese_name\":\"qweq\",\"tool_desc\":\"qweqewq\",\"method\":\"GET\",\"path\":\"/wqeq\"}]}");
        // When
        boolean result = pluginAdapterImpl.isNewTool(pluginEntity);

        // Then
        assertTrue(result);
    }

    @Test
    void test_buildResourceId_should_return_not_null() throws Exception {
        // Given
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("not_empty");
        pluginEntity.setRequestInfo(
                "{\"basic_info\":{\"host\":\"xybh.comasdad\",\"path\":\"/\",\"protocol\":\"https\"},\"tool_info\":[{\"tool_id\":\"bc60fd357b4847c7\",\"tool_display_name\":\"qweq\",\"tool_chinese_name\":\"qweq\",\"tool_desc\":\"qweqewq\",\"method\":\"GET\",\"path\":\"/wqeq\"}]}");

        // When
        List<String> result = pluginAdapterImpl.buildResourceId(pluginEntity);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_buildResourceId_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // When
            List<String> result = pluginAdapterImpl.buildResourceId(null);
        });
    }

    @Test
    void test_buildResourceId_should_return_not_null1() throws Exception {
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("not_empty");
        pluginEntity.setRequestInfo(
                "{\"basic_info\":{\"host\":\"xybh.comasdad\",\"path\":\"/\",\"protocol\":\"https\"},\"tool_info\":[{\"tool_id\":\"bc60fd357b4847c7\",\"tool_display_name\":\"qweq\",\"tool_chinese_name\":\"qweq\",\"tool_desc\":\"qweqewq\",\"method\":\"GET\",\"path\":\"/wqeq\"}]}");

        // When
        List<String> result = pluginAdapterImpl.buildResourceId(pluginEntity);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getToolEntity_should_return_not_null() throws Exception {
        // Given
        ToolEntity toolEntity = new ToolEntity();
        when(pluginBase.getToolEntityByVersion(anyString(), anyString())).thenReturn(toolEntity);
        ToolEntity toolEntity1 = new ToolEntity();
        when(pluginBase.buildToolByPlugin(anyString(), anyString(), eq(null), anyString())).thenReturn(toolEntity1);

        ToolEntity toolEntity2 = new ToolEntity();
        when(toolMapper.selectByProjectId(anyString(), anyString(), anyString())).thenReturn(toolEntity2);

        Map<String, Object> pluginConfig = new HashMap<>();
        Object object = new Object();
        pluginConfig.put("not_empty", object);

        // When
        ToolEntity result = pluginAdapterImpl.getToolEntity("not_empty", "not_empty", "not_empty", "not_empty");

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getToolEntity_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(pluginBase.getToolEntityByVersion(anyString(), anyString())).thenReturn(null);
            when(pluginBase.buildToolByPlugin(anyString(), anyString(), eq(null), anyString())).thenReturn(null);

            when(toolMapper.selectByProjectId(anyString(), anyString(), anyString())).thenReturn(null);

            // When
            ToolEntity result = pluginAdapterImpl.getToolEntity(null, null, null, null);
        });
    }

    @Test
    void test_getToolEntity_should_return_not_null1() throws Exception {
        List<String> toolIds = new ArrayList<>();
        toolIds.add("testId");
        List<ToolEntity> toolEntities = new ArrayList<>();
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("testId");
        toolEntities.add(toolEntity);
        // Given
        when(pluginBase.getToolEntityByVersion(anyString(), anyString())).thenReturn(null);
        when(pluginBase.buildToolByPlugin(anyString(), anyString(), eq(null), anyString())).thenReturn(null);

        when(toolMapper.selectByProjectId(anyString(), anyString(), anyString())).thenReturn(null);

        // When
        ToolEntity result = pluginAdapterImpl.getToolEntity("testId#testId", null, null, null);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_validTools_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given
            List<PluginEntity> toolEntities = new ArrayList<>();
            PluginEntity toolEntity = new PluginEntity();
            toolEntities.add(toolEntity);
            when(pluginMapper.selectByIds(anyList())).thenReturn(toolEntities);

            List<String> toolIds = new ArrayList<>();
            toolIds.add("not_empty");
            List<ShareScopeEntity> shareScopeEntities = new ArrayList<>();
            ShareScopeEntity shareScopeEntity = new ShareScopeEntity();
            shareScopeEntity.setResourceId("testId");
            shareScopeEntities.add(shareScopeEntity);
            when(shareInnerService.getShareScopeByWorkspaceAndId(anyList(), anyString())).thenReturn(shareScopeEntities);
            // When
            pluginAdapterImpl.validTools("not_empty", "not_empty", toolIds);
        });
    }

    @Test
    void test_validTools_should_not_throw_exception1() throws Exception {
        List<String> toolIds = new ArrayList<>();
        toolIds.add("testId");
        List<PluginEntity> toolEntities = new ArrayList<>();
        PluginEntity toolEntity = new PluginEntity();
        toolEntity.setPluginId("testId");
        toolEntities.add(toolEntity);
        List<ShareScopeEntity> shareScopeEntities = new ArrayList<>();
        ShareScopeEntity shareScopeEntity = new ShareScopeEntity();
        shareScopeEntity.setResourceId("testId");
        shareScopeEntities.add(shareScopeEntity);
        assertDoesNotThrow(() -> {
            // Given
            when(pluginMapper.selectByIds(anyList())).thenReturn(toolEntities);
            when(shareInnerService.getShareScopeByWorkspaceAndId(anyList(), any())).thenReturn(shareScopeEntities);

            // When
            pluginAdapterImpl.validTools(null, null, toolIds);
        });
    }

    @Test
    void test_getToolReferences_newEntity() throws Exception {
        List<String> toolIds = new ArrayList<>();
        toolIds.add("0");
        List<PluginEntity> pluginEntities = new ArrayList<>();
        PluginEntity plugin = new PluginEntity();
        plugin.setPluginId("0");
        plugin.setRequestInfo("{\"basic_info\":{\"host\":\"\",\"path\":\"\",\"protocol\":\"http\"},\"tool_info\":[{\"tool_id\":\"0\",\"tool_display_name\":\"WeatherInfo_10\",\"tool_chinese_name\":\"天气查询_9\",\"tool_desc\":\"可以查询天气\",\"method\":\"GET\",\"path\":\"/v3/weather/weatherInfo\"}]}");
        pluginEntities.add(plugin);
        ShareResourceEntity shareResourceEntity = new ShareResourceEntity();
        shareResourceEntity.setResourceId("0");
        List<ShareResourceEntity> shareResourceEntities = new ArrayList<>();
        shareResourceEntities.add(shareResourceEntity);
        // Given
        when(pluginMapper.selectByPrimaryIdAndToolIdsWithSearchCriteria(any(), any(), any(),
                eq(null))).thenReturn(pluginEntities);
        when(shareInnerService.getOriginSharedInfoByResourceId(anyList())).thenReturn(shareResourceEntities);
        // When
        List<ToolReference> result = pluginAdapterImpl.getToolReferences("test", "test", toolIds);

        // Then
        assertNotNull(result);
    }

    @Test
    public void test_handleToolWithoutToolId_plugin_type_without_tool_id() throws Exception {
        // Given
        WorkflowExportEntity workflowExportEntity = mock(WorkflowExportEntity.class);
        WorkflowVO workflowVO = mock(WorkflowVO.class);
        WorkflowNodeVO nodeVO = mock(WorkflowNodeVO.class);
        Map<String, Object> configs = new HashMap<>();
        when(workflowExportEntity.getDsl()).thenReturn(workflowVO);
        when(workflowVO.getNodes()).thenReturn(Collections.singletonList(nodeVO));
        when(nodeVO.getType()).thenReturn("plugin");
        when(nodeVO.getConfigs()).thenReturn(configs);
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setRequestInfo("{}");
        when(pluginMapper.selectByPrimaryKey(anyString(),any())).thenReturn(pluginEntity);

        // When & Then
        try (MockedStatic<NodeType> mockedNodeType = mockStatic(NodeType.class)) {
            mockedNodeType.when(() -> NodeType.fromType("plugin")).thenReturn(NodeType.PLUGIN);
            pluginAdapterImpl.handleToolWithoutToolId(workflowExportEntity);
        }
    }


    @Test
    public void test_handleToolWithoutToolId_unsupported_node_type() throws Exception {
        // Given
        WorkflowExportEntity workflowExportEntity = mock(WorkflowExportEntity.class);
        WorkflowVO workflowVO = mock(WorkflowVO.class);
        WorkflowNodeVO nodeVO = mock(WorkflowNodeVO.class);
        when(workflowExportEntity.getDsl()).thenReturn(workflowVO);
        when(workflowVO.getNodes()).thenReturn(Collections.singletonList(nodeVO));
        when(nodeVO.getType()).thenReturn("unsupported_type");

        // When & Then
        try (MockedStatic<NodeType> mockedNodeType = mockStatic(NodeType.class)) {
            mockedNodeType.when(() -> NodeType.fromType("unsupported_type")).thenReturn(null);
            // Then
            assertThrows(AgentStudioException.class, () -> pluginAdapterImpl.handleToolWithoutToolId(workflowExportEntity));
        }
    }

    @Test
    public void test_plugin_node_with_version_id_and_id() throws Exception {
        // Given
        WorkflowExportEntity workflowExportEntity = mock(WorkflowExportEntity.class);
        WorkflowVO workflowVO = mock(WorkflowVO.class);
        WorkflowNodeVO nodeVO = mock(WorkflowNodeVO.class);
        Map<String, Object> configs = new HashMap<>();
        configs.put("id", "toolId");
        configs.put("version_id", "oldVersionId");
        when(workflowExportEntity.getDsl()).thenReturn(workflowVO);
        when(workflowVO.getNodes()).thenReturn(Collections.singletonList(nodeVO));
        when(nodeVO.getType()).thenReturn("plugin");
        when(nodeVO.getConfigs()).thenReturn(configs);

        PluginEntity pluginEntity = mock(PluginEntity.class);
        when(pluginEntity.getLastVersionId()).thenReturn("newVersionId");
        when(pluginMapper.selectByPrimaryKey(eq("toolId"), eq(null))).thenReturn(pluginEntity);

        // When & Then
        try (MockedStatic<NodeType> mockedNodeType = mockStatic(NodeType.class)) {
            mockedNodeType.when(() -> NodeType.fromType("plugin")).thenReturn(NodeType.PLUGIN);
            pluginAdapterImpl.handleToolReleaseVersionId(workflowExportEntity);
            assertEquals("newVersionId", configs.get("version_id"));
        }
    }

    @Test
    void test_encryptedAuthInfo() throws Exception {
        // Mock RequestContextUtils 静态方法，防止 NPE
        try (MockedStatic<RequestContextUtils> mockedRequestContext = mockStatic(RequestContextUtils.class)) {
            // 告诉 Mock：当代码请求 DomainID 时，返回 "test_domain_id"
            mockedRequestContext.when(RequestContextUtils::getRequestUserDomainId).thenReturn("test_domain_id");

            AuthInfo authInfo = new AuthInfo();
            HisIamInfo hisIamInfo = new HisIamInfo();
            hisIamInfo.setIamAccount("test");
            hisIamInfo.setIamProject("project");
            hisIamInfo.setIamSecret("te");
            authInfo.setScope(AuthInfo.ScopeEnum.HIS_IAM);
            authInfo.setHisIamInfo(hisIamInfo);

            pluginAdapterImpl.anonymizeAuthInfo(authInfo);
        }
    }
}
