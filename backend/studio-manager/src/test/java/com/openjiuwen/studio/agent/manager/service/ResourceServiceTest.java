/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyList;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.bo.SkillDetails;
import com.openjiuwen.studio.agent.manager.enums.ResourceTypeEnum;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.utils.BaseTest;

import lombok.extern.slf4j.Slf4j;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentMatchers;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.Collections;

@Transactional
@Slf4j
@Sql(scripts = {"classpath:sql/resource_setup_db.sql"}, executionPhase = Sql.ExecutionPhase.BEFORE_TEST_CLASS)
@Sql(scripts = {"classpath:sql/after_test_clear_db.sql"}, executionPhase = Sql.ExecutionPhase.AFTER_TEST_CLASS)
public class ResourceServiceTest extends BaseTest {
    @Autowired
    private ResourceService resourceService;

    @Mock
    private SkillMapper skillMapper;

    @Test
    @Transactional
    public void validAgentResourceExist() {
        resourceService.validResourceExist(Arrays.asList("test_resource_agent_id"), ResourceTypeEnum.AGENT.toString(),
                "test_resource_project_id", "default");
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_agent_id"),
                    ResourceTypeEnum.AGENT.toString(), "test_resource_project_id", "default1");
        });
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_agent_id"),
                    ResourceTypeEnum.AGENT.toString(), "test_resource_project_id1", "default");
        });
    }

    @Test
    @Transactional
    public void validWorkflowResourceExist() {
        resourceService.validResourceExist(Arrays.asList("test_resource_workflow_id"),
                ResourceTypeEnum.WORKFLOW.toString(), "test_resource_project_id", "default");
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_workflow_id"),
                    ResourceTypeEnum.WORKFLOW.toString(), "test_resource_project_id", "default1");
        });
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_workflow_id"),
                    ResourceTypeEnum.WORKFLOW.toString(), "test_resource_project_id1", "default");
        });
    }

    @Test
    @Transactional
    public void validToolResourceExist() {
        resourceService.validResourceExist(Arrays.asList("test_resource_tool_id"), ResourceTypeEnum.TOOL.toString(),
                "test_resource_project_id", "default");
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_tool_id"), ResourceTypeEnum.TOOL.toString(),
                    "test_resource_project_id", "default1");
        });
        resourceService.validResourceExist(Arrays.asList("test_resource_tool_id"), ResourceTypeEnum.TOOL.toString(),
                "test_resource_project_id1", "default");
    }

    @Test
    @Transactional
    public void validMcpResourceExist() {
        resourceService.validResourceExist(Arrays.asList("test_resource_mcp_id"), ResourceTypeEnum.MCP.toString(),
                "test_resource_project_id", "default");
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_mcp_id"), ResourceTypeEnum.MCP.toString(),
                    "test_resource_project_id", "default1");
        });
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_mcp_id"), ResourceTypeEnum.MCP.toString(),
                    "test_resource_project_id1", "default");
        });
    }

    @Test
    @Transactional
    public void validModelResourceExist() {
        resourceService.validResourceExist(Arrays.asList("test_resource_model_id"), ResourceTypeEnum.MODEL.toString(),
                "test_resource_project_id", "default");
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_model_id"),
                    ResourceTypeEnum.MODEL.toString(), "test_resource_project_id", "default1");
        });
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_resource_model_id"),
                    ResourceTypeEnum.MODEL.toString(), "test_resource_project_id1", "default");
        });
    }

    @Test
    @Transactional
    public void validMemoryRepoResourceExist() {
        resourceService.validResourceExist(Arrays.asList("test_memory_repo_id"), ResourceTypeEnum.MEMORY.toString(),
            "test_resource_project_id", "test_workspace_id");
        assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(Arrays.asList("test_memory_repo_id"),
                ResourceTypeEnum.MEMORY.toString(), "test_resource_project_id", "test_workspace_id1");
        });
    }

    @Test
    @Transactional
    public void validSkillResourceExist_failed() {
        String skillId = "test_skill_id";
        String type = ResourceTypeEnum.SKILL.toString();
        String projectId = "test_resource_project_id";
        String workspaceId = "test_workspace_id1";

        Mockito.when(skillMapper.searchBySkillIds(anyList(), ArgumentMatchers.any()))
            .thenReturn(Collections.singletonList(new SkillDetails()));

        Assertions.assertThrows(AgentStudioException.class, () -> {
            resourceService.validResourceExist(
                Collections.singletonList(skillId), type, projectId, workspaceId);
        });
    }

    @Test
    @Transactional
    public void validSkillResourceExist_success() {
        Object originalMapper = ReflectionTestUtils.getField(resourceService, "skillMapper");

        try {
            ReflectionTestUtils.setField(resourceService, "skillMapper", skillMapper);

            String skillId = "test_skill_id";
            SkillDetails mockDetail = new SkillDetails();
            mockDetail.setSkillId(skillId);
            mockDetail.setName("Test Skill");

            Mockito.when(skillMapper.searchBySkillIds(ArgumentMatchers.anyList(), ArgumentMatchers.any()))
                .thenReturn(Collections.singletonList(mockDetail));

            Assertions.assertDoesNotThrow(() -> {
                resourceService.validResourceExist(
                    Collections.singletonList(skillId),
                    ResourceTypeEnum.SKILL.toString(),
                    "test_project_id",
                    "test_workspace_id"
                );
            });

        } finally {
            ReflectionTestUtils.setField(resourceService, "skillMapper", originalMapper);
        }
    }
}

