/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.manager.dto.AdditionalQuestionsConfig;
import com.openjiuwen.studio.agent.manager.entity.Agent;
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

import java.util.Map;

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
        ReflectionTestUtils.setField(irAdapterService, "relationManagementService",
            mock(RelationManagementService.class));
    }

    @Test
    void testServiceCreation() {
        assertNotNull(irAdapterService);
    }

    @Test
    void testAdaptAgentIncludesAdditionalQuestionsConfig() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setAdditionalQuestionsConfig(new AdditionalQuestionsConfig()
            .setEnable(true).setPrompt("saved follow-up rules"));

        Map<String, Object> ir = irAdapterService.adaptAgent(agent, Map.of());
        JSONObject configs = JSON.parseObject(JSON.toJSONString(ir)).getJSONObject("configs");
        JSONObject questionsConfig = configs.getJSONObject("additional_questions_config");

        assertEquals("saved follow-up rules", questionsConfig.getString("prompt"));
        assertTrue(questionsConfig.getBoolean("enable"));
    }

    @Test
    void testAdaptAgentWithoutAdditionalQuestionsConfig() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");

        Map<String, Object> ir = irAdapterService.adaptAgent(agent, Map.of());

        assertNull(((Map<?, ?>) ir.get("configs")).get("additional_questions_config"));
    }
}
