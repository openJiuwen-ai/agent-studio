/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.memory;

import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.manager.dto.AgentMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.CreateMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.DeleteMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryReposResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ListMemoryRepositoriesQo;
import com.openjiuwen.studio.agent.manager.dto.LongTermMemoryStrategy;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryRepoRequestBody;
import com.openjiuwen.studio.agent.manager.dto.ModifyMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.dto.ShowMemoryRepoResponseBody;
import com.openjiuwen.studio.agent.manager.entity.Agent;
import com.openjiuwen.studio.agent.manager.entity.MemoryRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.mapper.AgentMapper;
import com.openjiuwen.studio.agent.manager.mapper.MemoryRepoMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.service.IMemoryServiceInstanceService;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.mockito.ArgumentCaptor;

@MockitoSettings(strictness = Strictness.LENIENT)
class MemoryRepoManagementServiceTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private MemoryRepoMapper memoryRepoMapper;

    @Mock
    private AgentMapper agentMapper;

    @Mock
    private AgentRuntimeClient agentRuntimeClient;

    @Mock
    private WorkflowMapper workflowMapper;

    @Mock
    private MgObsService mgObsService;

    @Mock
    private IMemoryServiceInstanceService memoryServiceInstanceService;

    @InjectMocks
    private MemoryRepoManagementService memoryRepoManagementService;


    MockedStatic<RequestContextUtils> mockedStaticRequestContextUtils;

    @BeforeEach
    void setUp() throws Exception {
        mockedStaticRequestContextUtils = mockStatic(
            RequestContextUtils.class, RETURNS_DEEP_STUBS);
        // Given
        mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestAuthToken).thenReturn("token");
        mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserDomainId).thenReturn("domain_id");
        mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserName).thenReturn("name");
        mockedStaticRequestContextUtils.when(RequestContextUtils::getRequestUserId).thenReturn("user_id");
    }

    @AfterEach
    void tearDown() throws Exception {
        mockedStaticRequestContextUtils.close();
    }

    @Test
    void test_createMemoryRepo_should_return_not_null() throws Exception {
        // Given
        when(memoryRepoMapper.insert(any(MemoryRepoEntity.class))).thenReturn(0);

        CreateMemoryRepoRequestBody body = new CreateMemoryRepoRequestBody();
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        LongTermMemoryStrategy longTermMemoryStrategy = new LongTermMemoryStrategy();
        longTermMemoryStrategy.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        longTermMemoryStrategy.setPrompt("test_prompt");
        strategies.add(longTermMemoryStrategy);
        body.setName("test_name");
        body.setDescription("test_description");
        body.setLongTermMemoryStrategies(strategies);


        // When
        CreateMemoryRepoResponseBody result = memoryRepoManagementService.createMemoryRepo("not_empty", "not_empty", body);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_createMemoryRepo_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(memoryRepoMapper.insert(any(MemoryRepoEntity.class))).thenReturn(0);

            // When
            CreateMemoryRepoResponseBody result = memoryRepoManagementService.createMemoryRepo(null, null, null);
        });
    }

    @Test
    void test_createMemoryRepo_strategies_empty_should_throw() {
        // Given
        CreateMemoryRepoRequestBody body = new CreateMemoryRepoRequestBody();
        body.setName("test_name");
        body.setLongTermMemoryStrategies(new ArrayList<>());

        // When/Then
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> memoryRepoManagementService.createMemoryRepo("not_empty", "not_empty", body));
        assertEquals(StudioError.MEMORY_STRATEGY_INVALID, ex.getErrorCode());
    }

    @Test
    void test_createMemoryRepo_strategies_contains_null_should_throw() {
        // Given
        CreateMemoryRepoRequestBody body = new CreateMemoryRepoRequestBody();
        body.setName("test_name");
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        strategies.add(null);
        body.setLongTermMemoryStrategies(strategies);

        // When/Then
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> memoryRepoManagementService.createMemoryRepo("not_empty", "not_empty", body));
        assertEquals(StudioError.MEMORY_STRATEGY_INVALID, ex.getErrorCode());
    }

    @Test
    void test_createMemoryRepo_strategies_duplicate_type_should_throw() {
        // Given
        LongTermMemoryStrategy s1 = new LongTermMemoryStrategy();
        s1.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        s1.setPrompt("p1");
        LongTermMemoryStrategy s2 = new LongTermMemoryStrategy();
        s2.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        s2.setPrompt("p2");
        CreateMemoryRepoRequestBody body = new CreateMemoryRepoRequestBody();
        body.setName("test_name");
        body.setLongTermMemoryStrategies(List.of(s1, s2));

        // When/Then
        AgentStudioException ex = assertThrows(AgentStudioException.class,
            () -> memoryRepoManagementService.createMemoryRepo("not_empty", "not_empty", body));
        assertEquals(StudioError.MEMORY_STRATEGY_DUPLICATE, ex.getErrorCode());
    }


    @Test
    void test_deleteMemoryRepo_should_return_not_null() throws Exception {
        // Given
        when(memoryRepoMapper.deleteById(anyString())).thenReturn(1);
        MemoryRepoEntity memoryRepoEntity = MemoryRepoEntity.builder().build();
        when(memoryRepoMapper.selectById(anyString())).thenReturn(memoryRepoEntity);


        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("not_empty", "not_empty", "not_empty");

        // Then
        assertNotNull(result);
    }

    @Test
    void test_deleteMemoryRepo_should_return_not_null2() throws Exception {
        // Given
        when(memoryRepoMapper.deleteById(anyString())).thenReturn(0);
        when(memoryRepoMapper.selectById(anyString())).thenReturn(null);

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo(null, null, null);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_listMemoryRepositories_should_return_not_null() throws Exception {
        // Given
        List<MemoryRepoEntity> memoryRepos = new ArrayList<>();
        MemoryRepoEntity memoryRepoEntity = MemoryRepoEntity.builder().build();
        memoryRepos.add(memoryRepoEntity);
        when(memoryRepoMapper.selectByCondition(anyString(), anyString(), anyString(), any(), anyString())).thenReturn(memoryRepos);

        ListMemoryRepositoriesQo query = new ListMemoryRepositoriesQo();

        // When
        ListMemoryReposResponseBody result = memoryRepoManagementService.listMemoryRepositories("not_empty", query);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_listMemoryRepositories_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(memoryRepoMapper.selectByCondition(anyString(), anyString(), anyString(), any(), anyString())).thenReturn(null);

            // When
            ListMemoryReposResponseBody result = memoryRepoManagementService.listMemoryRepositories(null, null);
        });
    }


    @Test
    void test_modifyMemoryRepo_should_return_not_null() throws Exception {
        // Given
        when(memoryRepoMapper.updateById(any(MemoryRepoEntity.class))).thenReturn(0);

        ModifyMemoryRepoRequestBody body = new ModifyMemoryRepoRequestBody();
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        LongTermMemoryStrategy longTermMemoryStrategy = new LongTermMemoryStrategy();
        longTermMemoryStrategy.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        longTermMemoryStrategy.setPrompt("test_prompt");
        strategies.add(longTermMemoryStrategy);
        body.setName("test_name");
        body.setDescription("test_description");
        body.setLongTermMemoryStrategies(strategies);

        // When
        ModifyMemoryRepoResponseBody result = memoryRepoManagementService.modifyMemoryRepo("not_empty", "not_empty", "not_empty", body);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_modifyMemoryRepo_should_not_throw_exception() throws Exception {
        assertThrows(NullPointerException.class, () -> {
            // Given
            when(memoryRepoMapper.updateById(any(MemoryRepoEntity.class))).thenReturn(0);

            // When
            ModifyMemoryRepoResponseBody result = memoryRepoManagementService.modifyMemoryRepo(null, null, null, null);
        });
    }


    @Test
    void test_modifyMemoryRepo_should_not_default_backend_type_to_builtin_when_omitted() throws Exception {
        // Given — 编辑请求仅改名称，未携带 memory_backend_type
        when(memoryRepoMapper.updateById(any(MemoryRepoEntity.class))).thenReturn(1);

        ModifyMemoryRepoRequestBody body = new ModifyMemoryRepoRequestBody();
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        LongTermMemoryStrategy strategy = new LongTermMemoryStrategy();
        strategy.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        strategy.setPrompt("prompt");
        strategies.add(strategy);
        body.setName("renamed-repo");
        body.setDescription("renamed-desc");
        body.setLongTermMemoryStrategies(strategies);
        // memoryBackendType 与 memoryServiceInstanceId 均未设置

        // When
        memoryRepoManagementService.modifyMemoryRepo("project1", "repo-external", "ws1", body);

        // Then — 写入实体的 memoryBackendType 必须保持为 null（不默认 BUILTIN），
        // 这样 MyBatis 选择性更新会跳过该列，EXTERNAL 记忆库不会被静默改写。
        ArgumentCaptor<MemoryRepoEntity> captor = ArgumentCaptor.forClass(MemoryRepoEntity.class);
        verify(memoryRepoMapper).updateById(captor.capture());
        assertNull(captor.getValue().getMemoryBackendType(),
            "修改时缺失 memory_backend_type 不得默认为 BUILTIN");
        assertNull(captor.getValue().getMemoryServiceInstanceId(),
            "修改时缺失 memory_service_instance_id 不得被篡改");
    }

    @Test
    void test_modifyMemoryRepo_should_preserve_explicit_external_backend_type() throws Exception {
        // Given — 显式携带 EXTERNAL + 实例ID，应原样写入
        when(memoryRepoMapper.updateById(any(MemoryRepoEntity.class))).thenReturn(1);

        ModifyMemoryRepoRequestBody body = new ModifyMemoryRepoRequestBody();
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        LongTermMemoryStrategy strategy = new LongTermMemoryStrategy();
        strategy.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        strategy.setPrompt("prompt");
        strategies.add(strategy);
        body.setName("external-repo");
        body.setLongTermMemoryStrategies(strategies);
        body.setMemoryBackendType("EXTERNAL");
        body.setMemoryServiceInstanceId("instance-001");

        // When
        memoryRepoManagementService.modifyMemoryRepo("project1", "repo-external", "ws1", body);

        // Then
        ArgumentCaptor<MemoryRepoEntity> captor = ArgumentCaptor.forClass(MemoryRepoEntity.class);
        verify(memoryRepoMapper).updateById(captor.capture());
        assertEquals("EXTERNAL", captor.getValue().getMemoryBackendType());
        assertEquals("instance-001", captor.getValue().getMemoryServiceInstanceId());
    }


    @Test
    void test_showMemoryRepo_should_return_not_null() throws Exception {
        // Given
        List<LongTermMemoryStrategy> longTermMemoryStrategies = new ArrayList<>();
        LongTermMemoryStrategy longTermMemoryStrategy = new LongTermMemoryStrategy();
        longTermMemoryStrategies.add(longTermMemoryStrategy);
        Date createTime = new Date();
        Date updateTime = mock(Date.class, Answers.RETURNS_DEEP_STUBS);
        MemoryRepoEntity memoryRepoEntity = MemoryRepoEntity.builder().id("not_empty").name("not_empty").description("not_empty").longTermMemoryStrategies(longTermMemoryStrategies).createdUserId("not_empty").createdUserName("not_empty").lastUpdateUserId("not_empty").lastUpdateUserName("not_empty").createTime(createTime).updateTime(updateTime).build();
        when(memoryRepoMapper.selectById(anyString())).thenReturn(memoryRepoEntity);

        // When
        ShowMemoryRepoResponseBody result = memoryRepoManagementService.showMemoryRepo("not_empty", "not_empty", "not_empty");

        // Then
        assertNotNull(result);
    }


    @Test
    void test_showMemoryRepo_should_return_not_null2() throws Exception {
        // Given
        when(memoryRepoMapper.selectById(anyString())).thenReturn(null);

        // When
        ShowMemoryRepoResponseBody result = memoryRepoManagementService.showMemoryRepo(null, null, null);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_showMemoryRepo_maps_conversationRound_and_timeSpan() throws Exception {
        // Given
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        LongTermMemoryStrategy strategy = new LongTermMemoryStrategy();
        strategy.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        strategy.setPrompt("prompt");
        strategies.add(strategy);

        MemoryRepoEntity entity = MemoryRepoEntity.builder()
            .id("repo-1")
            .name("test-repo")
            .description("desc")
            .longTermMemoryStrategies(strategies)
            .conversationRound(5)
            .timeSpan(30)
            .createdUserId("user1")
            .createdUserName("User One")
            .lastUpdateUserId("user1")
            .lastUpdateUserName("User One")
            .createTime(new Date())
            .updateTime(new Date())
            .build();
        when(memoryRepoMapper.selectById("repo-1")).thenReturn(entity);

        // When
        ShowMemoryRepoResponseBody result = memoryRepoManagementService.showMemoryRepo("project1", "repo-1", "ws1");

        // Then
        assertNotNull(result);
        assertEquals("repo-1", result.getMemoryRepoId());
        assertEquals(5, result.getConversationRound());
        assertEquals(30, result.getTimeSpan());
    }

    @Test
    void test_showMemoryRepo_null_conversationRound_and_timeSpan() throws Exception {
        // Given
        MemoryRepoEntity entity = MemoryRepoEntity.builder()
            .id("repo-2")
            .name("test-repo")
            .description("desc")
            .longTermMemoryStrategies(new ArrayList<>())
            .createdUserId("user1")
            .createdUserName("User One")
            .lastUpdateUserId("user1")
            .lastUpdateUserName("User One")
            .createTime(new Date())
            .updateTime(new Date())
            .build();
        when(memoryRepoMapper.selectById("repo-2")).thenReturn(entity);

        // When
        ShowMemoryRepoResponseBody result = memoryRepoManagementService.showMemoryRepo("project1", "repo-2", "ws1");

        // Then
        assertNotNull(result);
        assertNull(result.getConversationRound());
        assertNull(result.getTimeSpan());
    }

    @Test
    void test_createMemoryRepo_maps_conversationRound_and_timeSpan() throws Exception {
        // Given
        when(memoryRepoMapper.insert(any(MemoryRepoEntity.class))).thenReturn(1);

        CreateMemoryRepoRequestBody body = new CreateMemoryRepoRequestBody();
        List<LongTermMemoryStrategy> strategies = new ArrayList<>();
        LongTermMemoryStrategy strategy = new LongTermMemoryStrategy();
        strategy.setType(LongTermMemoryStrategy.TypeEnum.SEMANTIC_MEMORY);
        strategy.setPrompt("test");
        strategies.add(strategy);
        body.setName("test-repo");
        body.setLongTermMemoryStrategies(strategies);
        body.setConversationRound(10);
        body.setTimeSpan(60);

        // When
        CreateMemoryRepoResponseBody result = memoryRepoManagementService.createMemoryRepo("project1", "ws1", body);

        // Then
        assertNotNull(result);
        assertNotNull(result.getMemoryRepoId());
    }

    @Test
    void test_deleteMemoryRepo_should_unbind_agents() throws Exception {
        // Given
        String repoId = "repo-to-delete";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);

        AgentMemoryConfig memCfg = new AgentMemoryConfig();
        memCfg.setMemoryRepoId(repoId);
        Agent boundAgent = new Agent();
        boundAgent.setAgentId("agent-1");
        boundAgent.setMemoryConfig(memCfg);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of(boundAgent));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then
        assertNotNull(result);
        assertEquals(repoId, result.getMemoryRepoId());
        verify(agentMapper).selectByMemoryRepoId(repoId);
        verify(agentMapper).clearMemoryConfig("agent-1");
    }

    @Test
    void test_deleteMemoryRepo_should_unbind_multiple_agents() throws Exception {
        // Given
        String repoId = "repo-multi";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);

        AgentMemoryConfig memCfg1 = new AgentMemoryConfig();
        memCfg1.setMemoryRepoId(repoId);
        Agent agent1 = new Agent();
        agent1.setAgentId("agent-a");
        agent1.setMemoryConfig(memCfg1);

        AgentMemoryConfig memCfg2 = new AgentMemoryConfig();
        memCfg2.setMemoryRepoId(repoId);
        Agent agent2 = new Agent();
        agent2.setAgentId("agent-b");
        agent2.setMemoryConfig(memCfg2);

        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of(agent1, agent2));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then
        assertNotNull(result);
        verify(agentMapper).clearMemoryConfig("agent-a");
        verify(agentMapper).clearMemoryConfig("agent-b");
    }

    @Test
    void test_deleteMemoryRepo_should_skip_agent_with_non_matching_memory_config() throws Exception {
        // Given — SQL LIKE returned a false-positive candidate
        String repoId = "repo-exact-match";
        String otherRepoId = "repo-exact-match-suffix";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);

        AgentMemoryConfig memCfg = new AgentMemoryConfig();
        memCfg.setMemoryRepoId(otherRepoId); // different repoId that matched LIKE
        Agent falsePositive = new Agent();
        falsePositive.setAgentId("agent-fp");
        falsePositive.setMemoryConfig(memCfg);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of(falsePositive));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — false-positive candidate must NOT be unbound
        assertNotNull(result);
        verify(agentMapper, org.mockito.Mockito.never()).clearMemoryConfig("agent-fp");
    }

    @Test
    void test_deleteMemoryRepo_should_skip_agent_with_null_memory_config() throws Exception {
        // Given — agent returned by LIKE but memoryConfig is null
        String repoId = "repo-null-cfg";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);

        Agent agent = new Agent();
        agent.setAgentId("agent-null");
        // memoryConfig is null
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of(agent));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then
        assertNotNull(result);
        verify(agentMapper, org.mockito.Mockito.never()).clearMemoryConfig("agent-null");
    }

    @Test
    void test_deleteMemoryRepo_no_bound_agents() throws Exception {
        // Given
        String repoId = "repo-no-agents";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then
        assertNotNull(result);
        verify(agentMapper).selectByMemoryRepoId(repoId);
        verify(agentMapper, org.mockito.Mockito.never()).clearMemoryConfig(anyString());
    }

    @Test
    void test_deleteMemoryRepo_unbind_failure_does_not_block_deletion() throws Exception {
        // Given
        String repoId = "repo-unbind-fail";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenThrow(new RuntimeException("DB error"));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — deletion still succeeds
        assertNotNull(result);
        assertEquals(repoId, result.getMemoryRepoId());
    }

    @Test
    void test_deleteMemoryRepo_should_clean_workflow_dsl_with_matching_memory_config() throws Exception {
        // Given
        String repoId = "repo-wf-clean";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());

        WorkflowEntity wf = new WorkflowEntity();
        wf.setId("wf-1");
        wf.setDslPath("obs://dsl/wf-1.json");
        when(workflowMapper.getAll()).thenReturn(List.of(wf));

        String dslJson = "{\"configs\":{\"memory_config\":{\"memory_repo_id\":\"repo-wf-clean\"},\"other\":\"value\"}}";
        when(mgObsService.downloadObsFile("obs://dsl/wf-1.json")).thenReturn(dslJson);

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then
        assertNotNull(result);
        verify(workflowMapper).getAll();
        verify(mgObsService).downloadObsFile("obs://dsl/wf-1.json");
        verify(mgObsService).uploadObsFile(
            org.mockito.ArgumentMatchers.eq("obs://dsl/wf-1.json"),
            org.mockito.ArgumentMatchers.<String>argThat(json -> {
                com.alibaba.fastjson2.JSONObject obj = com.alibaba.fastjson2.JSON.parseObject(json);
                return !obj.getJSONObject("configs").containsKey("memory_config")
                    && "value".equals(obj.getJSONObject("configs").getString("other"));
            }),
            org.mockito.ArgumentMatchers.eq(-1)
        );
    }

    @Test
    void test_deleteMemoryRepo_should_skip_workflow_with_different_memory_config() throws Exception {
        // Given
        String repoId = "repo-wf-skip";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());

        WorkflowEntity wf = new WorkflowEntity();
        wf.setId("wf-2");
        wf.setDslPath("obs://dsl/wf-2.json");
        when(workflowMapper.getAll()).thenReturn(List.of(wf));

        String dslJson = "{\"configs\":{\"memory_config\":{\"memory_repo_id\":\"other-repo-id\"}}}";
        when(mgObsService.downloadObsFile("obs://dsl/wf-2.json")).thenReturn(dslJson);

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — download happens but upload does not
        assertNotNull(result);
        verify(mgObsService).downloadObsFile("obs://dsl/wf-2.json");
        verify(mgObsService, org.mockito.Mockito.never()).uploadObsFile(
            anyString(), anyString(), org.mockito.ArgumentMatchers.anyInt()
        );
    }

    @Test
    void test_deleteMemoryRepo_should_skip_workflow_with_no_dsl_path() throws Exception {
        // Given
        String repoId = "repo-wf-nopath";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());

        WorkflowEntity wf = new WorkflowEntity();
        wf.setId("wf-3");
        wf.setDslPath(null);
        when(workflowMapper.getAll()).thenReturn(List.of(wf));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — no download/upload attempted
        assertNotNull(result);
        verify(mgObsService, org.mockito.Mockito.never()).downloadObsFile(anyString());
    }

    @Test
    void test_deleteMemoryRepo_workflow_cleanup_failure_does_not_block_deletion() throws Exception {
        // Given
        String repoId = "repo-wf-fail";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());
        when(workflowMapper.getAll()).thenThrow(new RuntimeException("DB error"));

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — deletion still succeeds
        assertNotNull(result);
        assertEquals(repoId, result.getMemoryRepoId());
    }

    @Test
    void test_deleteMemoryRepo_single_workflow_dsl_parse_failure_does_not_block_others() throws Exception {
        // Given
        String repoId = "repo-wf-partial";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());

        WorkflowEntity badWf = new WorkflowEntity();
        badWf.setId("wf-bad");
        badWf.setDslPath("obs://dsl/bad.json");

        WorkflowEntity goodWf = new WorkflowEntity();
        goodWf.setId("wf-good");
        goodWf.setDslPath("obs://dsl/good.json");

        when(workflowMapper.getAll()).thenReturn(List.of(badWf, goodWf));
        when(mgObsService.downloadObsFile("obs://dsl/bad.json")).thenThrow(new RuntimeException("OBS error"));
        String goodDslJson = "{\"configs\":{\"memory_config\":{\"memory_repo_id\":\"repo-wf-partial\"}}}";
        when(mgObsService.downloadObsFile("obs://dsl/good.json")).thenReturn(goodDslJson);

        // When
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — good workflow still cleaned
        assertNotNull(result);
        verify(mgObsService).downloadObsFile("obs://dsl/bad.json");
        verify(mgObsService).downloadObsFile("obs://dsl/good.json");
        verify(mgObsService).uploadObsFile(
            org.mockito.ArgumentMatchers.eq("obs://dsl/good.json"),
            anyString(),
            org.mockito.ArgumentMatchers.eq(-1)
        );
    }

    @Test
    void test_deleteMemoryRepo_runtime_data_failure_does_not_block_but_is_logged() throws Exception {
        // Given — runtime 数据删除失败
        String repoId = "repo-runtime-fail";
        when(memoryRepoMapper.deleteById(repoId)).thenReturn(1);
        when(agentMapper.selectByMemoryRepoId(repoId)).thenReturn(List.of());
        doThrow(new RuntimeException("Connection refused"))
            .when(agentRuntimeClient).deleteMemoryRepoData(repoId);

        // When — 删除仍然成功
        DeleteMemoryRepoResponseBody result = memoryRepoManagementService.deleteMemoryRepo("project1", repoId, "ws1");

        // Then — 删除成功，且调用了 runtime 删除（失败被 catch）
        assertNotNull(result);
        assertEquals(repoId, result.getMemoryRepoId());
        verify(agentRuntimeClient).deleteMemoryRepoData(repoId);
    }
}
