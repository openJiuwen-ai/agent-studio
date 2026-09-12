package com.openjiuwen.studio.conversation.application;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.foundation.connection.model.PageResult;
import com.openjiuwen.studio.agent.manager.mapper.SkillMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMapper;
import com.openjiuwen.studio.agent.manager.mapper.workspace.WorkspaceMemberMapper;
import com.openjiuwen.studio.agent.manager.entity.WorkspaceEntity;
import com.openjiuwen.studio.conversation.application.dto.ConversationCreateCmd;
import com.openjiuwen.studio.conversation.application.dto.ConversationDetailVo;
import com.openjiuwen.studio.conversation.application.dto.ConversationListQuery;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillVo;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillContext;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillDescriptor;
import com.openjiuwen.studio.conversation.application.dto.ConversationVo;
import com.openjiuwen.studio.conversation.application.dto.MessageVo;
import com.openjiuwen.studio.conversation.application.dto.SendMessageCmd;
import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.model.ConversationMessage;
import com.openjiuwen.studio.conversation.domain.repository.ConversationRepository;
import com.openjiuwen.studio.conversation.domain.service.ConversationHistoryAssembler;
import com.openjiuwen.studio.conversation.infrastructure.adapter.AgentRuntimeAdapter;
import com.openjiuwen.studio.conversation.interfaces.controller.ConversationWorkspaceController;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Optional;
import java.lang.reflect.Method;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class ConversationWorkspaceAppServiceTest {

    private ConversationRepository repository;
    private ConversationHistoryAssembler historyAssembler;
    private AgentRuntimeAdapter runtimeAdapter;
    private ConversationSkillResolver skillResolver;
    private ConversationWorkspaceAccessGuard workspaceAccessGuard;
    private ConversationAgentResourceResolver agentResourceResolver;
    private ConversationWorkspaceAppService appService;

    @BeforeEach
    void setUp() {
        repository = mock(ConversationRepository.class);
        historyAssembler = mock(ConversationHistoryAssembler.class);
        runtimeAdapter = mock(AgentRuntimeAdapter.class);
        skillResolver = mock(ConversationSkillResolver.class);
        workspaceAccessGuard = mock(ConversationWorkspaceAccessGuard.class);
        agentResourceResolver = mock(ConversationAgentResourceResolver.class);
        appService = new ConversationWorkspaceAppService(repository, historyAssembler, runtimeAdapter, skillResolver,
            workspaceAccessGuard, agentResourceResolver);

        SimpleUser user = new SimpleUser();
        user.setUserId("u1");
        user.setDomainId("d1");
        user.setProjectId("p1");
        RequestContextUtils.setContext(user);
    }

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();   // 清理 ThreadLocal，防串
    }

    // ---------- create ----------

    @Test
    void listSkills_只返回浏览器可见字段() {
        when(skillResolver.listAvailable("p1", "w1", "d1"))
            .thenReturn(List.of(ConversationSkillVo.builder()
                .skillId("s1").name("会议纪要").description("整理会议内容").build()));

        List<ConversationSkillVo> result = appService.listSkills("p1", "w1");

        assertEquals("s1", result.get(0).getSkillId());
    }

    @Test
    void listSkills_序列化时仅暴露浏览器字段() throws Exception {
        ConversationSkillVo skill = ConversationSkillVo.builder()
            .skillId("s1").name("会议纪要").description("整理会议内容").build();

        ObjectMapper objectMapper = new ObjectMapper();
        JsonNode node = objectMapper.readTree(objectMapper.writeValueAsString(skill));
        Set<String> fields = new HashSet<>();
        node.fieldNames().forEachRemaining(fields::add);

        assertEquals(Set.of("skill_id", "name", "description"), fields);
        assertFalse(node.has("versionId"));
        assertFalse(node.has("version_id"));
        assertFalse(node.has("objectKey"));
        assertFalse(node.has("object_key"));
    }

    @Test
    void listSkills_请求项目不是认证项目时拒绝且不查询技能() {
        SkillMapper mapper = mock(SkillMapper.class);
        ConversationWorkspaceAppService guarded = guardedAppService(mapper, mock(WorkspaceMapper.class),
            mock(WorkspaceMemberMapper.class));
        RequestContextUtils.getRequestUser().setProjectId("p2");

        assertThrows(AgentStudioException.class, () -> guarded.listSkills("p1", "w1"));

        verifyNoInteractions(mapper);
    }

    @Test
    void listSkills_当前用户不是工作空间成员时拒绝且不查询技能() {
        SkillMapper mapper = mock(SkillMapper.class);
        WorkspaceMapper workspaceMapper = mock(WorkspaceMapper.class);
        WorkspaceMemberMapper workspaceMemberMapper = mock(WorkspaceMemberMapper.class);
        when(workspaceMapper.getWorkspaceByWorkspaceId("p1", "w1"))
            .thenReturn(new WorkspaceEntity().setId("w1").setProjectId("p1"));
        ConversationWorkspaceAppService guarded = guardedAppService(mapper, workspaceMapper, workspaceMemberMapper);

        assertThrows(AgentStudioException.class, () -> guarded.listSkills("p1", "w1"));

        verifyNoInteractions(mapper);
    }

    @Test
    void listSkills_工作空间不存在时拒绝且不查询技能() {
        SkillMapper mapper = mock(SkillMapper.class);
        ConversationWorkspaceAppService guarded = guardedAppService(mapper, mock(WorkspaceMapper.class),
            mock(WorkspaceMemberMapper.class));

        assertThrows(AgentStudioException.class, () -> guarded.listSkills("p1", "w1"));

        verifyNoInteractions(mapper);
    }

    @Test
    void listSkills_暴露固定路由并转发工作空间参数() throws NoSuchMethodException {
        ConversationWorkspaceAppService controllerAppService = mock(ConversationWorkspaceAppService.class);
        ConversationWorkspaceController controller = new ConversationWorkspaceController(controllerAppService);
        List<ConversationSkillVo> expected = List.of(ConversationSkillVo.builder().skillId("s1").build());
        when(controllerAppService.listSkills("p1", "w1")).thenReturn(expected);

        Method method = ConversationWorkspaceController.class.getMethod("listSkills", String.class, String.class);
        assertEquals(List.of("/skills"), List.of(method.getAnnotation(GetMapping.class).value()));
        assertEquals("workspace_id", method.getParameters()[1].getAnnotation(RequestParam.class).value());
        assertEquals(expected, controller.listSkills("p1", "w1"));
    }

    @Test
    void testCreate_BlankTitle_UseDefaultTitle() {
        ConversationCreateCmd cmd = new ConversationCreateCmd();
        // 不 setTitle，保持 null
        ConversationVo vo = appService.create("p1", "w1", cmd);
        assertEquals("新会话", vo.getTitle());
        verify(repository).save(any());   // 断言确实保存了
    }

    @Test
    void testCreate_WithTitle_UseGivenTitle() {
        ConversationCreateCmd cmd = new ConversationCreateCmd();
        cmd.setTitle("自定义标题");
        cmd.setSource("source1");
        ConversationVo vo = appService.create("p1", "w1", cmd);
        assertEquals("自定义标题", vo.getTitle());
        assertEquals("source1", vo.getSource());
        verify(repository).save(any());   // 断言确实保存了
    }

    // ---------- list ----------

    @Test
    void testList_MapsRepositoryToVos() {
        when(repository.countByOwner("p1", "w1", "u1")).thenReturn(3L);
        when(repository.listByOwner("p1", "w1", "u1", 0, 20)).thenReturn(List.of(
                ownedConversation("c1"),
                ownedConversation("c2")));

        PageResult<ConversationVo> result = appService.list("p1", "w1", new ConversationListQuery());

        assertEquals(3L, result.getTotalCount());
        assertEquals(2, result.getItems().size());
        assertEquals("c1", result.getItems().get(0).getConversationId());
        assertEquals("c2", result.getItems().get(1).getConversationId());
    }

    @Test
    void testList_WithCustomPageSize() {
        when(repository.countByOwner("p1", "w1", "u1")).thenReturn(0L);
        when(repository.listByOwner("p1", "w1", "u1", 2, 50)).thenReturn(List.of());

        ConversationListQuery query = new ConversationListQuery();
        query.setPage(2);
        query.setSize(50);
        PageResult<ConversationVo> result = appService.list("p1", "w1", query);

        assertEquals(0L, result.getTotalCount());
        assertTrue(result.getItems().isEmpty());
        verify(repository).listByOwner("p1", "w1", "u1", 2, 50);
    }

    // ---------- detail ----------

    @Test
    void testDetail_ConversationNotFound_Throws() {
        when(repository.findById("c1")).thenReturn(Optional.empty());

        assertThrows(AgentStudioException.class, () -> appService.detail("p1", "w1", "c1"));
    }

    @Test
    void testDetail_NotOwned_Throws() {
        Conversation other = ownedConversation("c1");
        other.setOwnerUserId("other-user");
        when(repository.findById("c1")).thenReturn(Optional.of(other));

        assertThrows(AgentStudioException.class, () -> appService.detail("p1", "w1", "c1"));
    }

    @Test
    void testDetail_Owned_ReturnsMessages() {
        Conversation conv = ownedConversation("c1");
        conv.setMessages(List.of(
                ConversationMessage.builder().role("user").content("hi").build()));
        when(repository.findById("c1")).thenReturn(Optional.of(conv));

        ConversationDetailVo vo = appService.detail("p1", "w1", "c1");

        assertEquals("c1", vo.getConversationId());
        assertEquals(1, vo.getMessages().size());
        assertEquals("user", vo.getMessages().get(0).getRole());
    }

    @Test
    void testDetail_MessageWithoutRefs_MapsNullFields() {
        Conversation conv = ownedConversation("c1");
        conv.setMessages(List.of(
                ConversationMessage.builder().role("user").content("hi").build()));
        when(repository.findById("c1")).thenReturn(Optional.of(conv));

        ConversationDetailVo vo = appService.detail("p1", "w1", "c1");

        MessageVo m = vo.getMessages().get(0);
        assertEquals("user", m.getRole());
        // 引用为 null 时，映射不抛异常且字段为 null
        assertNull(m.getToolId());
        assertNull(m.getToolArgs());
        assertNull(m.getFileIds());
        assertNull(m.getExecutionId());
        assertNull(m.getSubExecutionId());
        assertNull(m.getAgentId());
    }

    // ---------- delete ----------

    @Test
    void testDelete_Owned_CallsSoftDelete() {
        when(repository.findById("c1")).thenReturn(Optional.of(ownedConversation("c1")));

        appService.delete("p1", "w1", "c1");

        verify(repository).softDelete("c1");
    }

    @Test
    void testDelete_NotOwned_Throws() {
        Conversation other = ownedConversation("c1");
        other.setOwnerUserId("other-user");
        when(repository.findById("c1")).thenReturn(Optional.of(other));

        assertThrows(AgentStudioException.class, () -> appService.delete("p1", "w1", "c1"));
        verify(repository, never()).softDelete("c1");   // 未授权：不允许软删
    }

    // ---------- sendMessage ----------

    @Test
    void testSendMessage_BlankQuery_Throws() {
        SendMessageCmd cmd = new SendMessageCmd();

        assertThrows(AgentStudioException.class,
                () -> appService.sendMessage("p1", "w1", "c1", cmd, new HttpHeaders()));
        verify(repository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void testSendMessage_BlankModelDeploymentId_Throws() {
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("hi");

        assertThrows(AgentStudioException.class,
                () -> appService.sendMessage("p1", "w1", "c1", cmd, new HttpHeaders()));
        verify(repository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void testSendMessage_HappyPath_AppendsUserMessageAndRuns() {
        Conversation conv = ownedConversation("c1");
        when(repository.findById("c1")).thenReturn(Optional.of(conv));
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("你好");
        cmd.setModelDeploymentId("m1");
        SseEmitter emitter = new SseEmitter();
        ConversationSkillContext skillContext = new ConversationSkillContext(List.of(
            ConversationSkillDescriptor.builder().skillId("s1").versionId("v1").name("meeting")
                .description("meeting skill").objectKey("u1/skills/s1/v1/a.zip").build()), List.of("s1"));
        when(skillResolver.resolveForRun("p1", "w1", "d1", List.of()))
            .thenReturn(skillContext);
        when(historyAssembler.assemble(conv)).thenReturn(List.of());
        when(runtimeAdapter.run(eq(conv), eq(cmd), anyList(), same(skillContext), anyString(), any()))
            .thenReturn(emitter);

        SseEmitter result = appService.sendMessage("p1", "w1", "c1", cmd, new HttpHeaders());

        assertSame(emitter, result);
        ArgumentCaptor<List<ConversationMessage>> captor = ArgumentCaptor.forClass(List.class);
        InOrder inOrder = inOrder(repository, workspaceAccessGuard, skillResolver, historyAssembler, runtimeAdapter);
        inOrder.verify(repository).findById("c1");
        inOrder.verify(workspaceAccessGuard).requireAccess("p1", "w1");
        inOrder.verify(skillResolver).resolveForRun("p1", "w1", "d1", List.of());
        inOrder.verify(repository).appendMessages(eq("c1"), captor.capture());
        inOrder.verify(historyAssembler).assemble(conv);
        inOrder.verify(runtimeAdapter).run(eq(conv), eq(cmd), anyList(), same(skillContext), anyString(), any());
        List<ConversationMessage> appended = captor.getValue();
        assertEquals(1, appended.size());
        assertEquals("user", appended.get(0).getRole());
        assertEquals("你好", appended.get(0).getContent());
    }

    @Test
    void sendMessage_路径项目与认证项目不同时拒绝且不触发下游调用() {
        Conversation conv = ownedConversation("c1");
        conv.setProjectId("p2");
        when(repository.findById("c1")).thenReturn(Optional.of(conv));
        doThrow(new AgentStudioException(com.openjiuwen.studio.agent.common.enums.StudioError.USER_WORKSPACE_PERMISSION_INVALID))
            .when(workspaceAccessGuard).requireAccess("p2", "w1");

        assertThrows(AgentStudioException.class,
            () -> appService.sendMessage("p2", "w1", "c1", validCmd(List.of()), new HttpHeaders()));

        verify(workspaceAccessGuard).requireAccess("p2", "w1");
        verifyNoInteractions(skillResolver, historyAssembler, runtimeAdapter);
        verify(repository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void sendMessage_当前用户非工作空间成员时拒绝且不触发下游调用() {
        Conversation conv = ownedConversation("c1");
        when(repository.findById("c1")).thenReturn(Optional.of(conv));
        doThrow(new AgentStudioException(com.openjiuwen.studio.agent.common.enums.StudioError.USER_WORKSPACE_PERMISSION_INVALID))
            .when(workspaceAccessGuard).requireAccess("p1", "w1");

        assertThrows(AgentStudioException.class,
            () -> appService.sendMessage("p1", "w1", "c1", validCmd(List.of()), new HttpHeaders()));

        verify(workspaceAccessGuard).requireAccess("p1", "w1");
        verifyNoInteractions(skillResolver, historyAssembler, runtimeAdapter);
        verify(repository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void sendMessage_推荐技能非法时不写用户消息() {
        Conversation conv = ownedConversation("c1");
        when(repository.findById("c1")).thenReturn(Optional.of(conv));
        SendMessageCmd cmd = validCmd(List.of("forbidden"));
        when(skillResolver.resolveForRun("p1", "w1", "d1", List.of("forbidden")))
            .thenThrow(new AgentStudioException(
                com.openjiuwen.studio.agent.common.enums.StudioError.METHOD_ARGUMENT_NOT_VALID,
                List.of("recommended skill is unavailable")));

        assertThrows(AgentStudioException.class,
            () -> appService.sendMessage("p1", "w1", "c1", cmd, new HttpHeaders()));

        verify(repository, never()).appendMessages(anyString(), anyList());
        verifyNoInteractions(runtimeAdapter);
    }

    @Test
    void sendMessage_当前请求域与会话域不一致时拒绝且不解析技能() {
        Conversation conv = ownedConversation("c1");
        when(repository.findById("c1")).thenReturn(Optional.of(conv));
        RequestContextUtils.getRequestUser().setDomainId("d2");

        assertThrows(AgentStudioException.class,
            () -> appService.sendMessage("p1", "w1", "c1", validCmd(List.of()), new HttpHeaders()));

        verifyNoInteractions(skillResolver, runtimeAdapter);
        verify(repository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void testSendMessage_ConversationNotFound_Throws() {
        when(repository.findById("c1")).thenReturn(Optional.empty());
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("hi");
        cmd.setModelDeploymentId("m1");

        assertThrows(AgentStudioException.class,
                () -> appService.sendMessage("p1", "w1", "c1", cmd, new HttpHeaders()));
        verify(repository, never()).appendMessages(anyString(), anyList());
    }

    // ---------- 工具方法 ----------

    private Conversation ownedConversation(String conversationId) {
        return Conversation.builder()
                .conversationId(conversationId)
                .title("会话")
                .projectId("p1")
                .workspaceId("w1")
                .domainId("d1")
                .ownerUserId("u1")
                .status(ConversationWorkspaceAppService.STATUS_ACTIVE)
                .build();
    }

    private SendMessageCmd validCmd(List<String> recommendedIds) {
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("整理会议");
        cmd.setModelDeploymentId("m1");
        cmd.setRecommendedSkillIds(recommendedIds);
        return cmd;
    }

    private ConversationWorkspaceAppService guardedAppService(SkillMapper mapper, WorkspaceMapper workspaceMapper,
                                                              WorkspaceMemberMapper workspaceMemberMapper) {
        return new ConversationWorkspaceAppService(repository, historyAssembler, runtimeAdapter,
            new ConversationSkillResolver(mapper),
            new ConversationWorkspaceAccessGuard(workspaceMapper, workspaceMemberMapper),
            agentResourceResolver);
    }
}
