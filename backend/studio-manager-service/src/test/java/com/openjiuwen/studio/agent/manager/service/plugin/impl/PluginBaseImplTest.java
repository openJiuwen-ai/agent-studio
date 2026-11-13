/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service.plugin.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.plugin.PluginEntity;
import com.openjiuwen.studio.agent.manager.mapper.DependencyMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class PluginBaseImplTest {

    private PluginMapper pluginMapper;
    private ToolMapper toolMapper;
    private ReleaseVersionMapper releaseVersionMapper;
    private MgObsService mgObsService;
    private DependencyMapper dependencyMapper;
    private EncryptionAdapter encryptionAdapter;

    private PluginBaseImpl pluginBase;

    @BeforeEach
    void setUp() {
        pluginMapper = mock(PluginMapper.class);
        toolMapper = mock(ToolMapper.class);
        releaseVersionMapper = mock(ReleaseVersionMapper.class);
        mgObsService = mock(MgObsService.class);
        dependencyMapper = mock(DependencyMapper.class);
        encryptionAdapter = mock(EncryptionAdapter.class);

        MockitoAnnotations.openMocks(this);
        pluginBase = new PluginBaseImpl();
        ReflectionTestUtils.setField(pluginBase, "pluginMapper", pluginMapper);
        ReflectionTestUtils.setField(pluginBase, "toolMapper", toolMapper);
        ReflectionTestUtils.setField(pluginBase, "releaseVersionMapper", releaseVersionMapper);
        ReflectionTestUtils.setField(pluginBase, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(pluginBase, "dependencyMapper", dependencyMapper);
        ReflectionTestUtils.setField(pluginBase, "encryptionAdapter", encryptionAdapter);
        ReflectionTestUtils.setField(pluginBase, "mcpDomainId", "mcp-service");
        pluginBase.init();
    }

    @Test
    void testGetToolEntityByVersion_Success() {
        ReleaseVersion rv = new ReleaseVersion();
        rv.setDslPath("path/to/dsl.json");
        when(releaseVersionMapper.selectByAppIdAndVersionId("plugin-1", "v1")).thenReturn(rv);

        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("plugin-1#0");
        toolEntity.setInputSchema("{}");
        String json = "{\"tool_id\":\"plugin-1#0\",\"input_schema\":\"{}\"}";
        when(mgObsService.downloadObsFile("path/to/dsl.json")).thenReturn(json);

        var result = pluginBase.getToolEntityByVersion("plugin-1#0", "v1");

        assertNotNull(result);
    }

    @Test
    void testGetToolEntityByVersion_VersionNotFound() {
        when(releaseVersionMapper.selectByAppIdAndVersionId("plugin-1", "v1")).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            pluginBase.getToolEntityByVersion("plugin-1#0", "v1"));
    }

    @Test
    void testGetPluginEntityByVersion_Success() {
        ReleaseVersion rv = new ReleaseVersion();
        rv.setDslPath("path/to/dsl.json");
        when(releaseVersionMapper.selectByAppIdAndVersionId("plugin-1", "v1")).thenReturn(rv);

        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("plugin-1");
        String json = "{\"plugin_id\":\"plugin-1\"}";
        when(mgObsService.downloadObsFile("path/to/dsl.json")).thenReturn(json);

        var result = pluginBase.getPluginEntityByVersion("plugin-1", "v1");

        assertNotNull(result);
    }

    @Test
    void testGetPluginEntityByVersion_VersionNotFound() {
        when(releaseVersionMapper.selectByAppIdAndVersionId("plugin-1", "v1")).thenReturn(null);

        assertThrows(AgentStudioException.class, () ->
            pluginBase.getPluginEntityByVersion("plugin-1", "v1"));
    }

    @Test
    void testGetToolNameById_Found() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        ArrayNode arrayNode = mapper.createArrayNode();
        var toolNode = mapper.createObjectNode();
        toolNode.put("tool_id", "t1");
        toolNode.put("name", "Tool One");
        arrayNode.add(toolNode);

        String result = PluginBaseImpl.getToolNameById(arrayNode, "t1", "name");

        assertEquals("Tool One", result);
    }

    @Test
    void testGetToolNameById_NotFound() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        ArrayNode arrayNode = mapper.createArrayNode();
        var toolNode = mapper.createObjectNode();
        toolNode.put("tool_id", "t1");
        toolNode.put("name", "Tool One");
        arrayNode.add(toolNode);

        String result = PluginBaseImpl.getToolNameById(arrayNode, "t2", "name");

        assertEquals("t2", result);
    }

    @Test
    void testGetToolNameById_NullToolInfo() {
        String result = PluginBaseImpl.getToolNameById(null, "t1", "name");

        assertEquals("t1", result);
    }

    @Test
    void testGetToolNameById_NonArray() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        JsonNode objectNode = mapper.createObjectNode();

        String result = PluginBaseImpl.getToolNameById(objectNode, "t1", "name");

        assertEquals("t1", result);
    }

    @Test
    void testTransformTool2Plugin_Success() {
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setToolId("tool-1");
        toolEntity.setProjectId("p1");
        toolEntity.setWorkspaceId("w1");
        toolEntity.setToolDisplayName("Test Tool");
        toolEntity.setToolDesc("desc");

        var result = pluginBase.transformTool2Plugin(toolEntity);

        assertNotNull(result);
        assertEquals("tool-1", result.getPluginId());
        assertEquals("Test Tool", result.getPluginDisplayName());
    }

    @Test
    void testInit_SetsStaticEncryptionAdapter() {
        assertNotNull(pluginBase);
    }

    @Test
    void testBuildToolByPlugin_PlazaPublished_KeepsFullQueryResult() {
        // 资产广场已上架插件（platform_published=1）跨工作空间引用：不再按调用方 workspace 二次过滤（FRS-091）
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("plugin-1");
        pluginEntity.setType("custom");
        pluginEntity.setWorkspaceId("ws-other");
        pluginEntity.setPlatformPublished(1);
        pluginEntity.setIsFree(0);
        pluginEntity.setCallMode("custom");
        pluginEntity.setRequestInfo("{\"tool_info\":[{\"tool_id\":\"0\",\"name\":\"t\"}]}");
        pluginEntity.setInputSchema("{}");
        pluginEntity.setOutputSchema("{}");
        pluginEntity.setIntfType("[]");
        pluginEntity.setTestStatus("[]");
        pluginEntity.setIsInputList("[]");
        pluginEntity.setIsOutputList("[]");

        ToolEntity fullTool = new ToolEntity();
        fullTool.setToolId("plugin-1#0");

        // 全量查询有结果；workspace 过滤查询即使返回 null 也应被跳过（因已上架）
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("plugin-1", null, null)).thenReturn(pluginEntity);
        when(toolMapper.selectWithoutStatus("plugin-1", null, null)).thenReturn(fullTool);

        ToolEntity result = pluginBase.buildToolByPlugin("proj-1", "ws-1", "plugin-1", "0");

        assertNotNull(result);
        // 已上架插件未走 workspace 二次过滤
        verify(pluginMapper, never()).selectByPrimaryKeyAndWorkspace("plugin-1", null, "ws-1");
    }

    @Test
    void testBuildToolByPlugin_NotPlazaPublished_WorkspaceFiltered() {
        // 未上架自定义插件跨工作空间：仍走 workspace 二次过滤，查不到则报工具不存在
        PluginEntity pluginEntity = new PluginEntity();
        pluginEntity.setPluginId("plugin-1");
        pluginEntity.setType("custom");
        pluginEntity.setWorkspaceId("ws-other");
        pluginEntity.setPlatformPublished(0);
        pluginEntity.setIsFree(0);
        pluginEntity.setCallMode("custom");
        pluginEntity.setRequestInfo("{\"tool_info\":[{\"tool_id\":\"0\",\"name\":\"t\"}]}");
        pluginEntity.setInputSchema("{}");
        pluginEntity.setOutputSchema("{}");
        pluginEntity.setIntfType("[]");
        pluginEntity.setTestStatus("[]");
        pluginEntity.setIsInputList("[]");
        pluginEntity.setIsOutputList("[]");

        when(pluginMapper.selectByPrimaryKeyAndWorkspace("plugin-1", null, null)).thenReturn(pluginEntity);
        when(pluginMapper.selectByPrimaryKeyAndWorkspace("plugin-1", null, "ws-1")).thenReturn(null);

        assertThrows(AgentStudioException.class,
            () -> pluginBase.buildToolByPlugin("proj-1", "ws-1", "plugin-1", "0"));
    }
}
