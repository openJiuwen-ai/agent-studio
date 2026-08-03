/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
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
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.AuthUserConfig;
import com.openjiuwen.studio.common.service.service.EncryptionAdapter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

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
    private CustomerHeaderProfile customerHeaderProfile;

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
        customerHeaderProfile = mock(CustomerHeaderProfile.class);

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
        ReflectionTestUtils.setField(irAdapterService, "customerHeaderProfile", customerHeaderProfile);
    }

    @Test
    void testServiceCreation() {
        assertNotNull(irAdapterService);
    }

    /**
     * Profile 启用（simple 模式）时 auth_keys 由 IR_AUTH_KEYS forward-list 确定性声明，
     * 不读当次发布请求。
     */
    @Test
    void getRetrievalAuth_whenProfileEnabled_readsForwardListDeterministically() {
        when(customerHeaderProfile.isEnabledInSimpleMode()).thenReturn(true);
        when(customerHeaderProfile.getIrAuthKeysForwardList())
            .thenReturn(Arrays.asList("cust-userid", "cust-token", "X-Auth-Token"));
        ReflectionTestUtils.setField(irAdapterService, "knowledgeSource", "CUSTOM");

        AuthUserConfig auth = ReflectionTestUtils.invokeMethod(irAdapterService, "getRetrievalAuth");

        assertNotNull(auth);
        assertEquals(AuthInfo.ScopeEnum.USER.toString(), auth.getScope());
        assertEquals("headers", auth.getTarget().getDomain());
        // 确定性 forward-list（三个 header 名，不存值）
        assertEquals(Arrays.asList("cust-userid", "cust-token", "X-Auth-Token"),
            auth.getTarget().getAuthKeys());
        // source 与 target 共用同一 Info
        assertEquals(auth.getSource().getAuthKeys(), auth.getTarget().getAuthKeys());
    }

    /**
     * Profile 未启用时保持原有业务语义：非 CUSTOM 源仅声明 X-Auth-Token。
     */
    @Test
    void getRetrievalAuth_whenProfileDisabled_keepsLegacyXAuthTokenOnly() {
        when(customerHeaderProfile.isEnabledInSimpleMode()).thenReturn(false);
        ReflectionTestUtils.setField(irAdapterService, "knowledgeSource", "PLATFORM");

        AuthUserConfig auth = ReflectionTestUtils.invokeMethod(irAdapterService, "getRetrievalAuth");

        assertNotNull(auth);
        assertEquals(Collections.singletonList("X-Auth-Token"), auth.getTarget().getAuthKeys());
    }
}
