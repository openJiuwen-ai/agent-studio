/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import java.util.List;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolCredentialMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.mcp.McpServiceManager;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.nodes.ParamExtractionNodeService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.impl.PluginBaseImpl;
import com.openjiuwen.studio.agent.manager.service.workspace.WorkspaceMappingService;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class IrAdapterServiceTest {

    private MappingMapper mappingMapper;
    private MgObsService obsService;
    private ModelServiceManager modelServiceManager;
    private IPlugin pluginService;
    private PluginBaseImpl pluginBase;
    private KnowledgeBaseServiceImpl knowledgeBaseService;
    private McpServiceManager mcpServiceManager;
    private ToolCredentialMapper toolCredentialMapper;
    private SkillMapper skillMapper;
    private ParamExtractionNodeService paramExtractionNodeService;
    private WorkspaceMappingService workspaceMappingService;
    private EncryptionAdapter encryptionAdapter;
    private RedisClient redisClient;

    private IrAdapterService irAdapterService;

    @BeforeEach
    void setUp() {
        mappingMapper = mock(MappingMapper.class);
        obsService = mock(MgObsService.class);
        modelServiceManager = mock(ModelServiceManager.class);
        pluginService = mock(IPlugin.class);
        pluginBase = mock(PluginBaseImpl.class);
        knowledgeBaseService = mock(KnowledgeBaseServiceImpl.class);
        mcpServiceManager = mock(McpServiceManager.class);
        toolCredentialMapper = mock(ToolCredentialMapper.class);
        skillMapper = mock(SkillMapper.class);
        paramExtractionNodeService = mock(ParamExtractionNodeService.class);
        workspaceMappingService = mock(WorkspaceMappingService.class);
        encryptionAdapter = mock(EncryptionAdapter.class);
        redisClient = mock(RedisClient.class);

        MockitoAnnotations.openMocks(this);
        irAdapterService = new IrAdapterService();
        ReflectionTestUtils.setField(irAdapterService, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(irAdapterService, "mgObsService", obsService);
        ReflectionTestUtils.setField(irAdapterService, "modelServiceManager", modelServiceManager);
        ReflectionTestUtils.setField(irAdapterService, "pluginService", pluginService);
        ReflectionTestUtils.setField(irAdapterService, "pluginBaseImpl", pluginBase);
        ReflectionTestUtils.setField(irAdapterService, "knowledgeBaseService", knowledgeBaseService);
        ReflectionTestUtils.setField(irAdapterService, "mcpServiceManager", mcpServiceManager);
        ReflectionTestUtils.setField(irAdapterService, "toolCredentialMapper", toolCredentialMapper);
        ReflectionTestUtils.setField(irAdapterService, "skillMapper", skillMapper);
        ReflectionTestUtils.setField(irAdapterService, "paramExtractionNodeService", paramExtractionNodeService);
        ReflectionTestUtils.setField(irAdapterService, "workspaceMappingService", workspaceMappingService);
        ReflectionTestUtils.setField(irAdapterService, "encryptionAdapter", encryptionAdapter);
        ReflectionTestUtils.setField(irAdapterService, "redisClient", redisClient);
    }

    @Test
    void testServiceCreation() {
        assertNotNull(irAdapterService);
    }

    @Test
    void testLegacyAgentAllToolsRejectsOfflineTool() {
        McpServiceEntity service = serviceWithOfflineTool();
        AgentStudioException error = assertThrows(AgentStudioException.class,
            () -> ReflectionTestUtils.invokeMethod(irAdapterService, "checkOfflineMcpTools", service, null));
        assertEquals(StudioError.MCP_SERVER_TOOL_OFFLINE, error.getErrorCode());
    }

    @Test
    void testExplicitSelectionChecksOnlyChosenTools() {
        McpServiceEntity service = serviceWithOfflineTool();
        assertDoesNotThrow(() -> ReflectionTestUtils.invokeMethod(irAdapterService,
            "checkOfflineMcpTools", service, List.of()));
        assertDoesNotThrow(() -> ReflectionTestUtils.invokeMethod(irAdapterService,
            "checkOfflineMcpTools", service, List.of("keep")));
        AgentStudioException error = assertThrows(AgentStudioException.class,
            () -> ReflectionTestUtils.invokeMethod(irAdapterService, "checkOfflineMcpTools", service, List.of("gone")));
        assertEquals(StudioError.MCP_SERVER_TOOL_OFFLINE, error.getErrorCode());
    }

    private McpServiceEntity serviceWithOfflineTool() {
        McpServiceEntity service = new McpServiceEntity();
        service.setId("mcp-1");
        service.setName("mcp-service");
        service.setTools("""
            [{"name":"gone","offline":true,
              "inputSchema":{"type":"object","properties":{}},
              "outputSchema":{"type":"object","properties":{}}}]
            """);
        return service;
    }
}
