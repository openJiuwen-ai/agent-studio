/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MappingEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.HistoryWorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.MappingMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.plugin.PluginMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.mcp.auth.IMcpBase;
import com.openjiuwen.studio.agent.manager.service.mcp.model.dao.McpServiceDao;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.plugin.IPlugin;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.service.share.ShareInnerService;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;
import org.mockito.MockitoAnnotations;
import org.springframework.test.util.ReflectionTestUtils;

import com.openjiuwen.studio.agent.manager.dto.ListAppRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourceRelationsQo;
import com.openjiuwen.studio.agent.manager.dto.ListResourcesRelationsQo;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class RelationManagementServiceTest {

    private ReleaseVersionMapper releaseVersionMapper;
    private AgentMapper agentMapper;
    private MappingMapper mappingMapper;
    private WorkflowMapper workflowMapper;
    private HistoryWorkflowMapper historyWorkflowMapper;
    private PluginMapper pluginMapper;
    private ToolMapper toolMapper;
    private WorkspaceMapper workspaceMapper;
    private MemoryRepoMapper memoryRepoMapper;
    private IPlugin pluginService;
    private ModelServiceManager modelServiceManager;
    private ShareResourceManagerService shareResourceManagerService;
    private MgObsService mgObsService;
    private IPluginBase pluginBase;
    private ResourceService resourceService;
    private ShareInnerService shareInnerService;
    private IMcpBase mcpBase;
    private SkillMapper skillMapper;
    private KnowledgeBaseServiceImpl knowledgeBaseService;
    private McpServiceDao serviceDao;

    private RelationManagementService relationManagementService;

    @BeforeEach
    void setUp() {
        releaseVersionMapper = mock(ReleaseVersionMapper.class);
        agentMapper = mock(AgentMapper.class);
        mappingMapper = mock(MappingMapper.class);
        workflowMapper = mock(WorkflowMapper.class);
        historyWorkflowMapper = mock(HistoryWorkflowMapper.class);
        pluginMapper = mock(PluginMapper.class);
        toolMapper = mock(ToolMapper.class);
        workspaceMapper = mock(WorkspaceMapper.class);
        memoryRepoMapper = mock(MemoryRepoMapper.class);
        pluginService = mock(IPlugin.class);
        modelServiceManager = mock(ModelServiceManager.class);
        shareResourceManagerService = mock(ShareResourceManagerService.class);
        mgObsService = mock(MgObsService.class);
        pluginBase = mock(IPluginBase.class);
        resourceService = mock(ResourceService.class);
        shareInnerService = mock(ShareInnerService.class);
        mcpBase = mock(IMcpBase.class);
        skillMapper = mock(SkillMapper.class);
        knowledgeBaseService = mock(KnowledgeBaseServiceImpl.class);
        serviceDao = mock(McpServiceDao.class);

        MockitoAnnotations.openMocks(this);
        relationManagementService = new RelationManagementService();
        ReflectionTestUtils.setField(relationManagementService, "releaseVersionMapper", releaseVersionMapper);
        ReflectionTestUtils.setField(relationManagementService, "agentMapper", agentMapper);
        ReflectionTestUtils.setField(relationManagementService, "mappingMapper", mappingMapper);
        ReflectionTestUtils.setField(relationManagementService, "workflowMapper", workflowMapper);
        ReflectionTestUtils.setField(relationManagementService, "historyWorkflowMapper", historyWorkflowMapper);
        ReflectionTestUtils.setField(relationManagementService, "pluginMapper", pluginMapper);
        ReflectionTestUtils.setField(relationManagementService, "toolMapper", toolMapper);
        ReflectionTestUtils.setField(relationManagementService, "workspaceMapper", workspaceMapper);
        ReflectionTestUtils.setField(relationManagementService, "memoryRepoMapper", memoryRepoMapper);
        ReflectionTestUtils.setField(relationManagementService, "pluginService", pluginService);
        ReflectionTestUtils.setField(relationManagementService, "modelServiceManager", modelServiceManager);
        ReflectionTestUtils.setField(relationManagementService, "shareResourceManagerService", shareResourceManagerService);
        ReflectionTestUtils.setField(relationManagementService, "mgObsService", mgObsService);
        ReflectionTestUtils.setField(relationManagementService, "pluginBase", pluginBase);
        ReflectionTestUtils.setField(relationManagementService, "resourceService", resourceService);
        ReflectionTestUtils.setField(relationManagementService, "shareInnerService", shareInnerService);
        ReflectionTestUtils.setField(relationManagementService, "mcpBase", mcpBase);
        ReflectionTestUtils.setField(relationManagementService, "skillMapper", skillMapper);
        ReflectionTestUtils.setField(relationManagementService, "knowledgeBaseService", knowledgeBaseService);
        ReflectionTestUtils.setField(relationManagementService, "serviceDao", serviceDao);
        ReflectionTestUtils.setField(relationManagementService, "toolBoundLimit", 20);
        ReflectionTestUtils.setField(relationManagementService, "knowledgeRepoBoundLimit", 3);
        ReflectionTestUtils.setField(relationManagementService, "workflowBoundLimit", 5);
        ReflectionTestUtils.setField(relationManagementService, "controllerWorkflowLimit", 5);
        ReflectionTestUtils.setField(relationManagementService, "controllerSubAgentLimit", 3);
        ReflectionTestUtils.setField(relationManagementService, "mcpBoundLimit", 5);
        ReflectionTestUtils.setField(relationManagementService, "defaultMcpIcon", "default-mcp-icon");
    }

    @Test
    void testDeleteAgentResourceMapping_Success() {
        assertDoesNotThrow(() ->
            relationManagementService.deleteAgentResourceMapping("agent-1", List.of("0.0.1")));
    }

    @Test
    void testListResourcesRelations_EmptyResult() {
        ListResourcesRelationsQo qo = new ListResourcesRelationsQo();
        qo.setResourceIds(List.of("resource-1"));
        qo.setResourceType("tool");
        qo.setWorkspaceId("w1");
        qo.setOffset(0);
        qo.setLimit(10);

        when(mappingMapper.getByIds(anyList())).thenReturn(Collections.emptyList());

        var result = relationManagementService.listResourcesRelations("p1", qo);

        assertNotNull(result);
    }

    @Test
    void testListAppRelations_EmptyResult() {
        ListAppRelationsQo qo = new ListAppRelationsQo();
        qo.setWorkspaceId("w1");
        qo.setResourceType("tool");

        var result = relationManagementService.listAppRelations("p1", "app-1", qo);

        assertNotNull(result);
    }

    @Test
    void testListResourceRelations_EmptyResult() {
        ListResourceRelationsQo qo = new ListResourceRelationsQo();
        qo.setWorkspaceId("w1");
        qo.setResourceType("tool");
        qo.setOffset(0);
        qo.setLimit(10);

        when(mappingMapper.selectByResourceIdAndVersionId(anyString(), any(), any(), any(), any()))
            .thenReturn(Collections.emptyList());

        var result = relationManagementService.listResourceRelations("p1", "resource-1", qo);

        assertNotNull(result);
    }

    /** mock工作流DSL：包含带一个输入参数的node_start节点，满足parseWorkflowInput2ResourceParameter解析 */
    private void mockWorkflowDsl() {
        String dsl = "{\"nodes\":[{\"id\":\"node_start\",\"type\":\"Start\",\"outputs\":"
            + "[{\"name\":\"query\",\"type\":\"string\",\"description\":\"用户输入\",\"required\":true,"
            + "\"value\":{\"default\":\"\",\"type\":\"literal\"}}]}]}";
        when(mgObsService.downloadObsFile(anyString())).thenReturn(dsl);
    }

    @Test
    void testCreateAgentWorkflow_DanglingReferencedVersion_FallbackToLatest() {
        // 原引用的工作流版本已被删除（存量脏数据）：应回退跟随last_version_id，而不是沿用悬空版本号
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            Agent agent = new Agent();
            agent.setAgentId("agent-1");
            agent.setName("test-agent");
            agent.setType("agent");
            when(agentMapper.selectByProjectIdAndWorkspaceId(anyString(), anyString(), anyString())).thenReturn(agent);

            WorkflowEntity workflow = new WorkflowEntity();
            workflow.setId("wf-1");
            workflow.setName("wf");
            workflow.setWorkspaceId("w1");
            workflow.setDslPath("workflow/flow/wf-1/wf-1.json");
            workflow.setLastVersionId("v2");
            when(workflowMapper.selectByWorkflowIds(anyString(), anyString(), anyList()))
                .thenReturn(List.of(workflow));

            // 原引用版本v1已被删除（查询返回null），现存最新版本v2
            when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(null);
            mockWorkflowDsl();

            MappingEntity reference = new MappingEntity();
            reference.setResourceId("wf-1");
            reference.setResourceVersion("v1");
            reference.setResourceName("wf");

            relationManagementService.createAgentWorkflow("p1", "w1", "agent-1", null, List.of(reference));

            ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
            verify(mappingMapper).insertBatch(captor.capture());
            MappingEntity inserted = captor.getValue().get(0);
            // 悬空版本v1应被替换为last_version_id（v2），且下载DSL使用v2
            assertEquals("v2", inserted.getResourceVersion());
            verify(mgObsService).downloadObsFile("workflow/flow/wf-1/wf-1_v2.json");
        }
    }

    @Test
    void testCreateAgentWorkflow_ExistingReferencedVersion_Kept() {
        // 原引用的工作流版本仍存在：保持版本固定语义，不回退
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("w1");

            Agent agent = new Agent();
            agent.setAgentId("agent-1");
            agent.setName("test-agent");
            agent.setType("agent");
            when(agentMapper.selectByProjectIdAndWorkspaceId(anyString(), anyString(), anyString())).thenReturn(agent);

            WorkflowEntity workflow = new WorkflowEntity();
            workflow.setId("wf-1");
            workflow.setName("wf");
            workflow.setWorkspaceId("w1");
            workflow.setDslPath("workflow/flow/wf-1/wf-1.json");
            workflow.setLastVersionId("v2");
            when(workflowMapper.selectByWorkflowIds(anyString(), anyString(), anyList()))
                .thenReturn(List.of(workflow));

            // 原引用版本v1仍然存在
            ReleaseVersion existing = new ReleaseVersion();
            existing.setAppId("wf-1");
            existing.setVersionId("v1");
            when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(existing);
            mockWorkflowDsl();

            MappingEntity reference = new MappingEntity();
            reference.setResourceId("wf-1");
            reference.setResourceVersion("v1");
            reference.setResourceName("wf");

            relationManagementService.createAgentWorkflow("p1", "w1", "agent-1", null, List.of(reference));

            ArgumentCaptor<List<MappingEntity>> captor = ArgumentCaptor.forClass(List.class);
            verify(mappingMapper).insertBatch(captor.capture());
            MappingEntity inserted = captor.getValue().get(0);
            // 版本存在时沿用原版本号v1，不受last_version_id影响
            assertEquals("v1", inserted.getResourceVersion());
            verify(mgObsService).downloadObsFile("workflow/flow/wf-1/wf-1_v1.json");
        }
    }

    @Test
    void testHandleAgentWorkflow_DanglingBoundVersion_HealedToLatestVersion() {
        // 已绑定工作流的版本号悬空（版本已被删除）：保存时自愈回退到最新现存版本v2（保持锁定具体版本语义），
        // modify路径正常执行。workspaceId传null（共享工作流跳过空间过滤），stub需用nullable匹配
        // DB中已绑定的草稿引用，resource_version指向已删版本v1
        MappingEntity bound = new MappingEntity();
        bound.setAppId("agent-1");
        bound.setResourceId("wf-1");
        bound.setResourceVersion("v1");
        bound.setResourceType("workflow");
        bound.setValid(true);
        when(mappingMapper.selectByAppIdAndResourceType("agent-1", "workflow")).thenReturn(List.of(bound));
        // v1已被删除
        when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(null);
        // wf-1最新现存版本为v2
        WorkflowEntity workflow = new WorkflowEntity();
        workflow.setId("wf-1");
        workflow.setLastVersionId("v2");
        when(workflowMapper.selectByWorkflowIds(anyString(), nullable(String.class), anyList()))
            .thenReturn(List.of(workflow));

        // 前端保存时传回原绑定（版本未变更）
        MappingEntity incoming = new MappingEntity();
        incoming.setResourceId("wf-1");
        incoming.setResourceVersion("v1");
        incoming.setResourceType("workflow");

        relationManagementService.handleAgentWorkflow("p1", "w1", "agent-1", List.of(incoming));

        // 悬空引用被CAS回退到最新现存版本v2（保持锁定具体版本语义）
        verify(mappingMapper).updateResourceVersionIfMatch("wf-1", "v1", "v2");
        // 已绑定记录落入modify路径，且入参中的悬空版本号被同步规整为v2，
        // 避免updateResourceParameterByAppIDAndResourceId无条件回写resource_version时把脏值写回
        ArgumentCaptor<MappingEntity> modifyCaptor = ArgumentCaptor.forClass(MappingEntity.class);
        verify(mappingMapper).updateResourceParameterByAppIDAndResourceId(modifyCaptor.capture());
        assertEquals("v2", modifyCaptor.getValue().getResourceVersion());
    }

    @Test
    void testHandleAgentWorkflow_DanglingBoundVersion_NoRemainingVersion_HealedToNull() {
        // 悬空版本且工作流已无任何版本（版本全删）：无版本可回退，自愈为null（跟随最新）
        MappingEntity bound = new MappingEntity();
        bound.setAppId("agent-1");
        bound.setResourceId("wf-1");
        bound.setResourceVersion("v1");
        bound.setResourceType("workflow");
        bound.setValid(true);
        when(mappingMapper.selectByAppIdAndResourceType("agent-1", "workflow")).thenReturn(List.of(bound));
        when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(null);
        // wf-1无任何版本，last_version_id为null
        WorkflowEntity workflow = new WorkflowEntity();
        workflow.setId("wf-1");
        when(workflowMapper.selectByWorkflowIds(anyString(), nullable(String.class), anyList()))
            .thenReturn(List.of(workflow));

        MappingEntity incoming = new MappingEntity();
        incoming.setResourceId("wf-1");
        incoming.setResourceVersion("v1");
        incoming.setResourceType("workflow");

        relationManagementService.handleAgentWorkflow("p1", "w1", "agent-1", List.of(incoming));

        // 无版本可回退时CAS回退为null（跟随最新）
        verify(mappingMapper).updateResourceVersionIfMatch("wf-1", "v1", null);
        ArgumentCaptor<MappingEntity> modifyCaptor = ArgumentCaptor.forClass(MappingEntity.class);
        verify(mappingMapper).updateResourceParameterByAppIDAndResourceId(modifyCaptor.capture());
        assertNull(modifyCaptor.getValue().getResourceVersion());
    }

    @Test
    void testHandleAgentWorkflow_ExistingBoundVersion_NoHeal() {
        // 已绑定工作流的版本号仍存在：不触发自愈，正常路径零行为变化
        MappingEntity bound = new MappingEntity();
        bound.setAppId("agent-1");
        bound.setResourceId("wf-1");
        bound.setResourceVersion("v1");
        bound.setResourceType("workflow");
        bound.setValid(true);
        when(mappingMapper.selectByAppIdAndResourceType("agent-1", "workflow")).thenReturn(List.of(bound));
        ReleaseVersion existing = new ReleaseVersion();
        existing.setAppId("wf-1");
        existing.setVersionId("v1");
        when(releaseVersionMapper.selectByAppIdAndVersionId("wf-1", "v1")).thenReturn(existing);

        MappingEntity incoming = new MappingEntity();
        incoming.setResourceId("wf-1");
        incoming.setResourceVersion("v1");
        incoming.setResourceType("workflow");

        relationManagementService.handleAgentWorkflow("p1", "w1", "agent-1", List.of(incoming));

        // 版本存在时不执行任何回退
        verify(mappingMapper, never()).updateResourceVersionIfMatch(anyString(), anyString(), any());
        verify(mappingMapper).updateResourceParameterByAppIDAndResourceId(any(MappingEntity.class));
    }

    @Test
    void testParseNestedProperties_NullProperties_ReturnsEmptyList() {
        // 回归：properties 为 JSON Schema 可选节点，null 时返回空列表而非 NPE（issue #1758）
        List<Map<String, Object>> result =
            assertDoesNotThrow(() -> relationManagementService.parseNestedProperties(null));
        assertTrue(result.isEmpty());
    }

    @Test
    void testParseNestedProperties_ArrayItemsObjectWithoutProperties_NoNpe() {
        // 回归：array 字段的 items 为 {"type":"object"} 且无 properties（按 JSON Schema 规范 properties 可选），
        // 递归解析时不得抛 NPE（issue #1758）
        SchemaConfig arrayProp = SchemaConfig.builder()
            .type("array")
            .items(SchemaConfig.builder().type("object").build())
            .build();
        Map<String, SchemaConfig> properties = new HashMap<>();
        properties.put("columns", arrayProp);

        List<Map<String, Object>> result =
            assertDoesNotThrow(() -> relationManagementService.parseNestedProperties(properties));

        assertEquals(1, result.size());
        Map<String, Object> parsed = result.get(0);
        assertEquals("columns", parsed.get("name"));
        assertEquals("array", parsed.get("type"));
        @SuppressWarnings("unchecked")
        Map<String, Object> schema = (Map<String, Object>) parsed.get("schema");
        assertEquals("object", schema.get("type"));
        // items 缺省 properties 时输出空的 schema 列表，与 IrAdapterService 路径保持一致（issue #1758）
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> nestedSchema = (List<Map<String, Object>>) schema.get("schema");
        assertNotNull(nestedSchema);
        assertTrue(nestedSchema.isEmpty());
    }

    @Test
    void testBuildResourceInputSchema_ArrayItemsObjectWithoutProperties_NoNpe() {
        // 复现 issue #1758：tools 的 input_schema 中 array 字段的 items 为 {"type":"object"}（无 properties），
        // Agent 绑定工具保存链路 buildResourceInputSchema 不得抛 NPE
        String inputSchemaStr = "{"
            + "\"type\":\"object\","
            + "\"required\":[],"
            + "\"properties\":{"
            + "\"columns\":{"
            + "\"type\":\"array\","
            + "\"description\":\"table类型自定义列定义[{field,name,align,width}]\","
            + "\"items\":{\"type\":\"object\"}"
            + "}"
            + "}"
            + "}";

        String result = assertDoesNotThrow(() -> (String) ReflectionTestUtils.invokeMethod(
            relationManagementService, "buildResourceInputSchema", inputSchemaStr, "tool-1"));

        assertNotNull(result);
        JSONArray params = JSON.parseArray(result);
        JSONObject columns = null;
        for (int i = 0; i < params.size(); i++) {
            JSONObject param = params.getJSONObject(i);
            if ("columns".equals(param.getString("name"))) {
                columns = param;
                break;
            }
        }
        assertNotNull(columns);
        assertEquals("array", columns.getString("type"));
        JSONObject schema = columns.getJSONObject("schema");
        assertEquals("object", schema.getString("type"));
        // items 缺省 properties 时输出空的 schema 列表，与 IrAdapterService 路径保持一致（issue #1758）
        JSONArray nestedSchema = schema.getJSONArray("schema");
        assertNotNull(nestedSchema);
        assertTrue(nestedSchema.isEmpty());
    }

    @Test
    void testParseNestedProperties_NullPropertyValue_Skipped() {
        // 回归：properties 中存在值为 null 的条目（如 "properties":{"a":null}）时跳过而非 NPE（issue #1758）
        Map<String, SchemaConfig> properties = new HashMap<>();
        properties.put("bad", null);

        List<Map<String, Object>> result =
            assertDoesNotThrow(() -> relationManagementService.parseNestedProperties(properties));

        assertTrue(result.isEmpty());
    }

    @Test
    void testBuildResourceInputSchema_TopLevelObjectWithoutRequiredProperties_NoNpe() {
        // 回归：顶层 schema 为 {"type":"object"}（无 required/properties，JSON Schema 规范中均为可选字段），
        // buildResourceInputSchema 不得在 required/properties 解析处 NPE（issue #1758 同类路径）
        String inputSchemaStr = "{\"type\":\"object\"}";

        String result = assertDoesNotThrow(() -> (String) ReflectionTestUtils.invokeMethod(
            relationManagementService, "buildResourceInputSchema", inputSchemaStr, "tool-1"));

        assertNotNull(result);
        JSONArray params = JSON.parseArray(result);
        assertTrue(params.isEmpty());
    }

    @Test
    void testBuildResourceInputSchema_NullTopLevelPropertyValue_Skipped() {
        // 回归：顶层 properties 中存在值为 null 的条目（如 {"properties":{"a":null}}）时跳过而非 NPE（issue #1758）
        String inputSchemaStr = "{\"type\":\"object\",\"required\":[],\"properties\":{\"a\":null}}";

        String result = assertDoesNotThrow(() -> (String) ReflectionTestUtils.invokeMethod(
            relationManagementService, "buildResourceInputSchema", inputSchemaStr, "tool-1"));

        assertNotNull(result);
        assertTrue(JSON.parseArray(result).isEmpty());
    }

    @Test
    void testBuildResourceInputSchema_InvalidInputSchema_ThrowsToolInputSchemaInvalid() {
        // 回归：input_schema 为 JSON 字面量 null 或损坏 JSON（含 tool_id 数组包装格式）时，
        // 转为业务异常 TOOL_INPUT_SCHEMA_INVALID 而非裸 NPE/JSONException 500（issue #1758）
        AgentStudioException nullEx = assertThrows(AgentStudioException.class,
            () -> ReflectionTestUtils.invokeMethod(
                relationManagementService, "buildResourceInputSchema", "null", "tool-1"));
        assertEquals(StudioError.TOOL_INPUT_SCHEMA_INVALID, nullEx.getErrorCode());

        AgentStudioException arrayEx = assertThrows(AgentStudioException.class,
            () -> ReflectionTestUtils.invokeMethod(
                relationManagementService, "buildResourceInputSchema", "[{\"toolId\":\"t1\"}]", "tool-1"));
        assertEquals(StudioError.TOOL_INPUT_SCHEMA_INVALID, arrayEx.getErrorCode());
    }
}
