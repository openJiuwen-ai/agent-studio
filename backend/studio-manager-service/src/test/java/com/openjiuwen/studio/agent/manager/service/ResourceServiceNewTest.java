package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.util.Collections;
import java.util.List;
import java.util.Map;

import com.openjiuwen.studio.agent.agentbase.service.KnowledgeBaseServiceImpl;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.dto.KnowledgeBaseListItem;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesQo;
import com.openjiuwen.studio.agent.manager.dto.ListKnowledgeBasesResponseBody;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.CommonMeta;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceData;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.McpServiceMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.ToolMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ResourceServiceNewTest {

    @Mock
    private ModelServiceMapper modelServiceMapper;

    @Mock
    private McpServiceMapper mcpServiceMapper;

    @Mock
    private AgentMapper agentMapper;

    @Mock
    private WorkflowMapper workflowMapper;

    @Mock
    private ToolMapper toolMapper;

    @Mock
    private MemoryRepoMapper memoryRepoMapper;

    @Mock
    private SkillMapper skillMapper;

    @Mock
    private KnowledgeBaseServiceImpl knowledgeBaseService;

    @Mock
    private ShareResourceMapper shareResourceMapper;

    @Mock
    private ShareScopeMapper shareScopeMapper;

    @InjectMocks
    private ResourceService resourceService;

    @Test
    void testValidResourceExist_AllIdsExist() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("Test Agent");
        agent.setProjectId("p1");
        agent.setWorkspaceId("w1");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1")))
            .thenReturn(List.of(agent));

        resourceService.validResourceExist(List.of("agent-1"), "agent", "p1", "w1");
    }

    @Test
    void testValidResourceExist_OneIdNotInMap() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("Test Agent");
        agent.setProjectId("p1");
        agent.setWorkspaceId("w1");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1", "agent-2")))
            .thenReturn(List.of(agent));

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> resourceService.validResourceExist(List.of("agent-1", "agent-2"), "agent", "p1", "w1"));
        assertEquals(StudioError.RESOURCE_NOT_EXISTS, ex.getErrorCode());
    }

    @Test
    void testValidResourceExist_MapIsNull() {
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1")))
            .thenReturn(Collections.emptyList());

        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> resourceService.validResourceExist(List.of("agent-1"), "agent", "p1", "w1"));
        assertEquals(StudioError.RESOURCE_NOT_EXISTS, ex.getErrorCode());
    }

    @Test
    void testValidResourceExist_EmptyIdsList() {
        resourceService.validResourceExist(Collections.emptyList(), "agent", "p1", "w1");
    }

    @Test
    void testGetResourceMeta_AgentType() {
        Agent agent = new Agent();
        agent.setAgentId("agent-1");
        agent.setName("Test Agent");
        agent.setDomainId("d1");
        agent.setProjectId("p1");
        agent.setWorkspaceId("w1");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1")))
            .thenReturn(List.of(agent));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("agent-1"), "agent", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("agent-1"));
        assertEquals("Test Agent", result.get("agent-1").getName());
        verify(agentMapper).selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("agent-1"));
    }

    @Test
    void testGetResourceMeta_ControllerType() {
        Agent agent = new Agent();
        agent.setAgentId("ctrl-1");
        agent.setName("Test Controller");
        agent.setDomainId("d1");
        agent.setProjectId("p1");
        agent.setWorkspaceId("w1");
        when(agentMapper.selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("ctrl-1")))
            .thenReturn(List.of(agent));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("ctrl-1"), "controller", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("ctrl-1"));
        verify(agentMapper).selectByIdsAndProjectIdAndWorkspaceId("p1", "w1", List.of("ctrl-1"));
    }

    @Test
    void testGetResourceMeta_WorkflowType() {
        WorkflowEntity wf = new WorkflowEntity();
        wf.setId("wf-1");
        wf.setName("Test Workflow");
        wf.setDomainId("d1");
        wf.setProjectId("p1");
        wf.setWorkspaceId("w1");
        when(workflowMapper.getWorkflowEntityByIds("p1", "w1", List.of("wf-1")))
            .thenReturn(List.of(wf));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("wf-1"), "workflow", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("wf-1"));
        assertEquals("Test Workflow", result.get("wf-1").getName());
        verify(workflowMapper).getWorkflowEntityByIds("p1", "w1", List.of("wf-1"));
    }

    @Test
    void testGetResourceMeta_ToolType() {
        ToolEntity tool = new ToolEntity();
        tool.setToolId("tool-1");
        tool.setToolDisplayName("Test Tool");
        tool.setDomainId("d1");
        tool.setProjectId("p1");
        tool.setWorkspaceId("w1");
        tool.setType("inner");
        when(toolMapper.selectByToolIdsAndWorkspaceId(List.of("tool-1"), "p1", "w1"))
            .thenReturn(List.of(tool));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("tool-1"), "tool", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("tool-1"));
        assertEquals("Test Tool", result.get("tool-1").getName());
        verify(toolMapper).selectByToolIdsAndWorkspaceId(List.of("tool-1"), "p1", "w1");
    }

    @Test
    void testGetResourceMeta_ToolType_CustomCrossWorkspace_PlazaPublished() {
        // 跨空间 custom 插件，platform_published=1 且 published=1 → 放行（FRS-091）
        ToolEntity tool = new ToolEntity();
        tool.setToolId("tool-1");
        tool.setToolDisplayName("Test Tool");
        tool.setDomainId("d1");
        tool.setProjectId("pA");
        tool.setWorkspaceId("wA");
        tool.setType("custom");
        tool.setPlatformPublished(1);
        tool.setPublished(1);
        when(toolMapper.selectByToolIdsAndWorkspaceId(List.of("tool-1"), "pB", "wB"))
            .thenReturn(List.of(tool));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("tool-1"), "tool", "pB", "wB");

        assertNotNull(result);
        assertTrue(result.containsKey("tool-1"));
    }

    @Test
    void testGetResourceMeta_ToolType_CustomCrossWorkspace_NotPlazaPublished() {
        // 跨空间 custom 插件，未上架 → 拦截 TOOLS_NOT_EXIST_OR_NO_PERMISSION
        ToolEntity tool = new ToolEntity();
        tool.setToolId("tool-2");
        tool.setToolDisplayName("Test Tool");
        tool.setDomainId("d1");
        tool.setProjectId("pA");
        tool.setWorkspaceId("wA");
        tool.setType("custom");
        tool.setPlatformPublished(0);
        tool.setPublished(1);
        when(toolMapper.selectByToolIdsAndWorkspaceId(List.of("tool-2"), "pB", "wB"))
            .thenReturn(List.of(tool));

        assertThrows(AgentStudioException.class,
            () -> resourceService.getResourceMeta(List.of("tool-2"), "tool", "pB", "wB"));
    }

    @Test
    void testGetResourceMeta_ToolType_CustomCrossWorkspace_PlazaOffShelf() {
        // 跨空间 custom 插件，曾上架但已下架（platform_published=0，published 仍=1）→ 拦截
        ToolEntity tool = new ToolEntity();
        tool.setToolId("tool-3");
        tool.setToolDisplayName("Test Tool");
        tool.setDomainId("d1");
        tool.setProjectId("pA");
        tool.setWorkspaceId("wA");
        tool.setType("custom");
        tool.setPlatformPublished(0);
        tool.setPublished(1);
        when(toolMapper.selectByToolIdsAndWorkspaceId(List.of("tool-3"), "pB", "wB"))
            .thenReturn(List.of(tool));

        assertThrows(AgentStudioException.class,
            () -> resourceService.getResourceMeta(List.of("tool-3"), "tool", "pB", "wB"));
    }

    @Test
    void testGetResourceMeta_McpType() {
        McpServiceEntity mcp = new McpServiceEntity();
        mcp.setId("mcp-1");
        mcp.setName("Test MCP");
        mcp.setDomainId("d1");
        mcp.setProjectId("p1");
        mcp.setWorkspaceId("w1");
        when(mcpServiceMapper.selectByIdsAndWorkspace(List.of("mcp-1"), "p1", "w1"))
            .thenReturn(List.of(mcp));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("mcp-1"), "mcp", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("mcp-1"));
        assertEquals("Test MCP", result.get("mcp-1").getName());
        verify(mcpServiceMapper).selectByIdsAndWorkspace(List.of("mcp-1"), "p1", "w1");
    }

    @Test
    void testGetResourceMeta_ModelType() {
        ModelServiceData model = new ModelServiceData();
        model.setId("model-1");
        model.setModelName("Test Model");
        model.setProjectId("p1");
        model.setWorkspaceId("w1");
        when(modelServiceMapper.queryByIds(any(), eq("p1"), eq("w1")))
            .thenReturn(List.of(model));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("model-1"), "model", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("model-1"));
        assertEquals("Test Model", result.get("model-1").getName());
        verify(modelServiceMapper).queryByIds(List.of("model-1"), "p1", "w1");
    }

    @Test
    void testGetResourceMeta_MemoryType() {
        MemoryRepoEntity memory = MemoryRepoEntity.builder()
            .id("mem-1")
            .name("Test Memory")
            .projectId("p1")
            .workspaceId("w1")
            .build();
        when(memoryRepoMapper.selectByCondition(eq("p1"), eq("w1"), isNull(), any(), isNull()))
            .thenReturn(List.of(memory));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("mem-1"), "memory", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("mem-1"));
        assertEquals("Test Memory", result.get("mem-1").getName());
        verify(memoryRepoMapper).selectByCondition("p1", "w1", null, List.of("mem-1"), null);
    }

    @Test
    void testGetResourceMeta_SkillType() {
        SkillDetails skill = new SkillDetails();
        skill.setSkillId("skill-1");
        skill.setName("Test Skill");
        when(skillMapper.searchBySkillIds(List.of("skill-1")))
            .thenReturn(List.of(skill));

        Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("skill-1"), "skill", "p1", "w1");

        assertNotNull(result);
        assertTrue(result.containsKey("skill-1"));
        assertEquals("Test Skill", result.get("skill-1").getName());
        verify(skillMapper).searchBySkillIds(List.of("skill-1"));
    }

    @Test
    void testGetResourceMeta_RepoType() {
        try (MockedStatic<RequestContextUtils> ctx = mockStatic(RequestContextUtils.class)) {
            ctx.when(RequestContextUtils::getRequestProjectId).thenReturn("p1");

            KnowledgeBaseListItem kbItem = new KnowledgeBaseListItem();
            kbItem.setKnowledgeBaseId("repo-1");
            kbItem.setName("Test Repo");

            ListKnowledgeBasesResponseBody resp = new ListKnowledgeBasesResponseBody();
            resp.setItems(List.of(kbItem));
            resp.setTotal(1L);

            when(knowledgeBaseService.listKnowledgeBases(eq("p1"), any(ListKnowledgeBasesQo.class)))
                .thenReturn(resp);

            Map<String, CommonMeta> result = resourceService.getResourceMeta(List.of("repo-1"), "repo", "p1", "w1");

            assertNotNull(result);
            assertTrue(result.containsKey("repo-1"));
            assertEquals("Test Repo", result.get("repo-1").getName());
            verify(knowledgeBaseService).listKnowledgeBases(eq("p1"), any(ListKnowledgeBasesQo.class));
        }
    }

    @Test
    void testGetResourceMeta_InvalidType() {
        assertNull(resourceService.getResourceMeta(List.of("id-1"), "invalid_type", "p1", "w1"));
    }
}
