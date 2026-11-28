/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
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
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;
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

    // ===== FEAT-093 appendDynamicAuthParamsToSchema 的返回值契约（检视修复回归）=====

    private static AuthInfo dynamicAuth(String targetName) {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.DYNAMIC);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        AuthKeyInfo keyInfo = new AuthKeyInfo();
        keyInfo.setTargetName(targetName);
        keyInfo.setSourceName("userToken");
        authInfo.setAuthKeys(java.util.List.of(keyInfo));
        return authInfo;
    }

    @Test
    void appendDynamicAuthParams_nullSchemaDynamicAuth_returnsNewSchemaWithHeaderParam() {
        // 严重检视项回归：空入参 schema（纯动态鉴权插件既有支持场景）+
        // DYNAMIC ——追加须经返回值传播（此前 helper 就地重赋局部参数，
        // 调用方仍持 null → 参数列表为空 → 运行期无法注入动态凭证）
        SchemaConfig result = IrAdapterService.appendDynamicAuthParamsToSchema(dynamicAuth("Authorization"), null);
        assertNotNull(result, "空 schema + DYNAMIC 须返回新 schema（非 null）");
        assertNotNull(result.getProperties());
        SchemaConfig param = result.getProperties().get("Authorization");
        assertNotNull(param, "动态头须追加为 Headers 入参");
        assertEquals("Headers", param.getLocation());
        assertEquals(IrAdapterService.DYNAMIC_AUTH_PARAM_DESC, param.getDescription());
    }

    @Test
    void appendDynamicAuthParams_nullSchemaDynamicAuth_newSchemaHasObjectType() {
        // 检视项回归：新 schema 缺 type=object 时，下游 parseAgentPluginParams/
        // parseWorkflowPluginParams 对 getType()=null 直接返回空列表——动态头
        // 参数进不了 ARGUMENTS/arguments，前端编排侧看不到可绑定参数
        SchemaConfig result = IrAdapterService.appendDynamicAuthParamsToSchema(dynamicAuth("Authorization"), null);
        assertNotNull(result);
        assertEquals("object", result.getType(), "空 schema 构造的新实例须带 type=object（下游解析门槛）");
    }

    @Test
    void appendDynamicAuthParams_nullSchemaDynamicAuth_downstreamParserProducesArguments() {
        // 端到端：null schema + DYNAMIC → helper 返回 → parseWorkflowPluginParams
        // （反射调用私有方法）须产出含动态头的参数列表（非空）
        SchemaConfig result = IrAdapterService.appendDynamicAuthParamsToSchema(dynamicAuth("Authorization"), null);
        @SuppressWarnings("unchecked")
        java.util.List<java.util.Map<String, Object>> arguments = (java.util.List<java.util.Map<String, Object>>)
            org.springframework.test.util.ReflectionTestUtils.invokeMethod(
                irAdapterService, "parseWorkflowPluginParams", result, true);
        assertNotNull(arguments);
        assertFalse(arguments.isEmpty(), "parseWorkflowPluginParams 须解析出动态头参数（非空列表）");
        boolean hasAuthorization = arguments.stream()
            .anyMatch(param -> "Authorization".equals(param.get("name")));
        assertTrue(hasAuthorization, "arguments 须含 Authorization 动态头参数");
    }

    @Test
    void appendDynamicAuthParams_nullSchemaDynamicAuth_agentParserProducesArguments() {
        // 端到端：同上，走 parseAgentPluginParams（agent 插件参数链路）
        SchemaConfig result = IrAdapterService.appendDynamicAuthParamsToSchema(dynamicAuth("Authorization"), null);
        @SuppressWarnings("unchecked")
        java.util.List<java.util.Map<String, Object>> arguments = (java.util.List<java.util.Map<String, Object>>)
            org.springframework.test.util.ReflectionTestUtils.invokeMethod(
                irAdapterService, "parseAgentPluginParams", result, true);
        assertNotNull(arguments);
        assertFalse(arguments.isEmpty(), "parseAgentPluginParams 须解析出动态头参数（非空列表）");
        boolean hasAuthorization = arguments.stream()
            .anyMatch(param -> "Authorization".equals(param.get("name")));
        assertTrue(hasAuthorization, "arguments 须含 Authorization 动态头参数");
    }

    @Test
    void appendDynamicAuthParams_existingSchema_mutatesAndReturnsSameInstance() {
        SchemaConfig schema = new SchemaConfig();
        schema.setProperties(new java.util.HashMap<>());
        SchemaConfig result = IrAdapterService.appendDynamicAuthParamsToSchema(dynamicAuth("X-Token"), schema);
        assertSame(schema, result, "非 null 入参须返回同一实例（既有调用方语义）");
        assertTrue(result.getProperties().containsKey("X-Token"));
    }

    @Test
    void appendDynamicAuthParams_nonDynamic_nullSchema_returnsNullPassThrough() {
        AuthInfo noAuth = new AuthInfo();
        assertNull(IrAdapterService.appendDynamicAuthParamsToSchema(noAuth, null),
            "非 DYNAMIC 时原样返回入参（null 透传）");
    }

    // ===== issue-1729 回归：getPluginToolEntity 的工具 ID 归一化契约 =====
    // 广场选择插件后写入 configs.plugins 的形态为 {"id": pluginId, "tool_id": toolId}（无 #），
    // AGENT 节点分支校验/保存时不做预拼接，原始配置直达本方法，归一化兜底必须在此完成。

    @Test
    void getPluginToolEntity_idWithoutHashWithToolId_normalizesWithToolId() {
        java.util.Map<String, Object> pluginConfig = new java.util.HashMap<>();
        pluginConfig.put("id", "plaza-plugin-1");
        pluginConfig.put("tool_id", "tool-9");
        ToolEntity tool = new ToolEntity();
        when(pluginService.getToolEntity(anyString(), any(), any(), any())).thenReturn(tool);

        ToolEntity result = irAdapterService.getPluginToolEntity("proj-1", pluginConfig);

        assertSame(tool, result);
        assertEquals("plaza-plugin-1#tool-9", pluginConfig.get("id"), "无 # 的 id 须用 tool_id 补全");
        verify(pluginService).getToolEntity(eq("plaza-plugin-1#tool-9"), eq("proj-1"), isNull(), isNull());
        verify(pluginService, never()).getToolIdFromPlugin(anyString());
    }

    @Test
    void getPluginToolEntity_idWithoutHashNoToolId_usesPluginToolMapping() {
        // 无 tool_id 时回退查询插件下的工具映射
        java.util.Map<String, Object> pluginConfig = new java.util.HashMap<>();
        pluginConfig.put("id", "plaza-plugin-2");
        when(pluginService.getToolIdFromPlugin("plaza-plugin-2")).thenReturn("tool-3");
        when(pluginService.getToolEntity(anyString(), any(), any(), any())).thenReturn(new ToolEntity());

        irAdapterService.getPluginToolEntity("proj-1", pluginConfig);

        assertEquals("plaza-plugin-2#tool-3", pluginConfig.get("id"));
        verify(pluginService).getToolEntity(eq("plaza-plugin-2#tool-3"), any(), any(), any());
    }

    @Test
    void getPluginToolEntity_idWithoutHashNoMapping_fallsBackToZero() {
        // 插件下查不到工具映射时兜底为 #0
        java.util.Map<String, Object> pluginConfig = new java.util.HashMap<>();
        pluginConfig.put("id", "plaza-plugin-3");
        when(pluginService.getToolIdFromPlugin("plaza-plugin-3")).thenReturn(null);
        when(pluginService.getToolEntity(anyString(), any(), any(), any())).thenReturn(new ToolEntity());

        irAdapterService.getPluginToolEntity("proj-1", pluginConfig);

        assertEquals("plaza-plugin-3#0", pluginConfig.get("id"), "查不到工具映射时须兜底 #0");
        verify(pluginService).getToolEntity(eq("plaza-plugin-3#0"), any(), any(), any());
    }

    @Test
    void getPluginToolEntity_idWithHash_passesThrough() {
        // 已带 # 的 id 原样透传，不再触发归一化
        java.util.Map<String, Object> pluginConfig = new java.util.HashMap<>();
        pluginConfig.put("id", "plaza-plugin-4#tool-1");
        when(pluginService.getToolEntity(anyString(), any(), any(), any())).thenReturn(new ToolEntity());

        irAdapterService.getPluginToolEntity("proj-1", pluginConfig);

        assertEquals("plaza-plugin-4#tool-1", pluginConfig.get("id"));
        verify(pluginService, never()).getToolIdFromPlugin(anyString());
        verify(pluginService).getToolEntity(eq("plaza-plugin-4#tool-1"), any(), any(), any());
    }

    @Test
    void getPluginToolEntity_versionId_passedThrough() {
        // version_id 须透传给插件服务（issue-1735 的锚定解析在 PluginAdapterImpl 侧完成）
        java.util.Map<String, Object> pluginConfig = new java.util.HashMap<>();
        pluginConfig.put("id", "plaza-plugin-5#tool-1");
        pluginConfig.put("version_id", "v-123");
        when(pluginService.getToolEntity(anyString(), any(), any(), any())).thenReturn(new ToolEntity());

        irAdapterService.getPluginToolEntity("proj-1", pluginConfig);

        verify(pluginService).getToolEntity(eq("plaza-plugin-5#tool-1"), eq("proj-1"), isNull(), eq("v-123"));
    }

    @Test
    void getPluginToolEntity_toolNotFound_throwsToolNotExist() {
        java.util.Map<String, Object> pluginConfig = new java.util.HashMap<>();
        pluginConfig.put("id", "ghost-plugin#tool-0");
        when(pluginService.getToolEntity(anyString(), any(), any(), any())).thenReturn(null);

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> irAdapterService.getPluginToolEntity("proj-1", pluginConfig));
        assertEquals(StudioError.TOOL_NOT_EXIST, ex.getErrorCode());
    }
}
