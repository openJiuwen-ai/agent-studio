package com.openjiuwen.studio.conversation.infrastructure.adapter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.dto.agent.Message;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillContext;
import com.openjiuwen.studio.conversation.application.dto.ConversationSkillDescriptor;
import com.openjiuwen.studio.conversation.application.dto.SendMessageCmd;
import com.openjiuwen.studio.conversation.domain.model.Conversation;
import com.openjiuwen.studio.conversation.domain.repository.ConversationRepository;

import okhttp3.Request;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * 团队对话直传路径（Phase 5）单元测试。
 *
 * <p>run() 不再预烘焙 IR：URL 直接构建为 /v1/conversation/team（2026-08-12 直连引擎，dev 移除 Java runtime 层），
 * 请求体直传 conversationId + subAgentIds + modelDeploymentId + conversationHistory（无 systemPrompt、无 enable_history）。
 * 空 endpoint 时 URL 构建（Request.Builder.url）立即抛异常，不会进入真实网络，测试快速且确定性。</p>
 */
class AgentRuntimeAdapterTest {

    private ConversationRepository conversationRepository;
    private OkHttpClientUtils okHttpClientUtils;
    private AgentRuntimeAdapter adapter;

    @BeforeEach
    void setUp() {
        conversationRepository = mock(ConversationRepository.class);
        okHttpClientUtils = mock(OkHttpClientUtils.class);
        adapter = new AgentRuntimeAdapter(conversationRepository, okHttpClientUtils, new ObjectMapper());
        // @Value 字段在裸 new 下为 null，必须手工注入（Spring 只在 bean 创建时解析）。
        // 忠实模拟生产：${agent_runtime_endpoint:} → 空字符串，URL 无协议头 → OkHttp 抛 IllegalArgumentException
        ReflectionTestUtils.setField(adapter, "runtimeEndpoint", "");
    }

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();   // 清理 IAM 上下文，防串
    }

    /**
     * 团队端点 URL 形态（2026-08-12 直连引擎，dev 移除 Java runtime 层）：{endpoint}/v1/conversation/team，
     * conversationId 随请求体下发，不再走 /v1/inner/{project}/conversations/{conv}/team。
     */
    @Test
    void testBuildTeamUrl_TeamEndpointShape() {
        Conversation conv = Conversation.builder()
                .conversationId("c1").projectId("p1").workspaceId("w1").build();
        assertEquals("/v1/conversation/team", adapter.buildTeamUrl(conv));
    }

    /**
     * 空 endpoint（无协议头）→ URL 构建抛 IllegalArgumentException（构建先于网络，测试确定性）。
     * 注意：okhttp 异常消息会截断 URL（如 "/v1/in..."），故 URL 形态由 testBuildTeamUrl 独立断言。
     */
    @Test
    void testRun_EmptyEndpoint_ThrowsIllegalArgumentException() {
        Conversation conv = Conversation.builder()
                .conversationId("c1").projectId("p1").workspaceId("w1").build();
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("hi");
        cmd.setModelDeploymentId("m1");

        assertThrows(IllegalArgumentException.class,
                () -> adapter.run(conv, cmd, List.of(), ConversationSkillContext.empty(), "exec-1", new HttpHeaders()));
    }

    /**
     * 历史转换：平台 Message → 引擎契约 [{role, content}]（仅 role/content，避免跨服务反序列化类型坑）；
     * 空/null 返回 null（第一轮不注入）。
     */
    @Test
    void testToHistoryMaps_ConvertsMessagesToRoleContent() {
        List<Message> histories = List.of(
                new Message().setRole("user").setContent("上海的天气怎么样？"),
                new Message().setRole("assistant").setContent("上海多云 18-26℃"));
        List<Map<String, String>> maps = ReflectionTestUtils.invokeMethod(adapter, "toHistoryMaps", histories);
        assertNotNull(maps);
        assertEquals(2, maps.size());
        assertEquals("user", maps.get(0).get("role"));
        assertEquals("上海的天气怎么样？", maps.get(0).get("content"));
        assertEquals("assistant", maps.get(1).get("role"));

        assertNull(ReflectionTestUtils.invokeMethod(adapter, "toHistoryMaps", new Object[] { List.of() }));
        assertNull(ReflectionTestUtils.invokeMethod(adapter, "toHistoryMaps", new Object[] { null }));
    }

    /**
     * 直连引擎请求体（2026-08-12）：含 conversationId + query + subAgentIds + modelDeploymentId + conversationHistory；
     * 无 systemPrompt（监督者提示词固定引擎侧）。
     */
    @Test
    @SuppressWarnings("unchecked")
    void testBuildRequestBody_IncludesConversationIdAndTeamParams() {
        Conversation conv = Conversation.builder()
                .conversationId("c1").projectId("p1").workspaceId("w1").build();
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("上海的天气怎么样？");
        cmd.setModelDeploymentId("m1");
        List<Message> histories = List.of(
                new Message().setRole("user").setContent("之前的天气？"),
                new Message().setRole("assistant").setContent("昨天多云"));

        Map<String, Object> body = ReflectionTestUtils.invokeMethod(adapter, "buildRequestBody", conv, cmd, histories,
            ConversationSkillContext.empty());
        assertNotNull(body);
        assertEquals("c1", body.get("conversationId"));
        assertEquals("上海的天气怎么样？", body.get("query"));
        assertEquals(List.of("d321fa88-a768-4b63-8d68-13cd743c6903", "8dafdc64-2c52-40b5-9b24-49894314b763"),
                body.get("subAgentIds"));
        assertEquals("m1", body.get("modelDeploymentId"));
        assertNull(body.get("systemPrompt"));

        List<Map<String, String>> historyMaps = (List<Map<String, String>>) body.get("conversationHistory");
        assertNotNull(historyMaps);
        assertEquals(2, historyMaps.size());
        assertEquals("user", historyMaps.get(0).get("role"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void buildRequestBody_携带本轮文件引用和文件名() {
        Conversation conv = Conversation.builder().conversationId("c1").projectId("p1").workspaceId("w1").build();
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("总结附件");
        cmd.setModelDeploymentId("m1");
        cmd.setFileIds(List.of(Map.of("url", "https://files.test/report.pdf", "fileName", "report.pdf")));

        Map<String, Object> body = adapter.buildRequestBody(conv, cmd, List.of(), ConversationSkillContext.empty());

        assertEquals(cmd.getFileIds(), body.get("fileIds"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void buildRequestBody_包含可信技能目录和有序推荐() {
        ConversationSkillDescriptor skill = ConversationSkillDescriptor.builder()
            .skillId("s1").versionId("v1").name("meeting-minutes")
            .description("整理会议内容").objectKey("u1/skills/s1/v1/a.zip").build();
        ConversationSkillContext skillContext = new ConversationSkillContext(List.of(skill), List.of("s1"));
        Conversation conv = Conversation.builder().conversationId("c1").projectId("p1").workspaceId("w1").build();
        SendMessageCmd cmd = new SendMessageCmd();
        cmd.setQuery("整理会议");
        cmd.setModelDeploymentId("m1");
        cmd.setRecommendedSkillIds(List.of("browser-forged-id"));

        Map<String, Object> body = adapter.buildRequestBody(conv, cmd, List.of(), skillContext);

        assertEquals(List.of("s1"), body.get("recommendedSkillIds"));
        assertNotEquals(cmd.getRecommendedSkillIds(), body.get("recommendedSkillIds"));
        Map<String, Object> item = ((List<Map<String, Object>>) body.get("skillCatalog")).get(0);
        assertEquals("u1/skills/s1/v1/a.zip", item.get("objectKey"));
    }

    /**
     * 回归：header 来自传入的 HttpHeaders（manager 统一模式）；X-Auth-Token 以 IAM 上下文为准补齐。
     */
    @Test
    void testCopyRequestHeaders_AddsRequestHeadersAndAuthTokenFromIamContext() {
        RequestContextUtils.setRequestAuthTokenAndProjectId("u1|p1", "p1");
        HttpHeaders headers = new HttpHeaders();
        headers.add("X-Language", "zh-cn");
        headers.add("stream", "true");
        headers.add("X-Auth-Token", "external-token");   // 外部传入的 X-Auth-Token 应被忽略

        Request.Builder builder = new Request.Builder().url("http://runtime:31014/x");
        adapter.copyRequestHeaders(builder, headers);

        Request request = builder.build();
        assertEquals("zh-cn", request.header("X-Language"));
        assertEquals("true", request.header("stream"));
        // X-Auth-Token 取自 IAM 上下文，未重复添加外部值
        assertEquals("u1|p1", request.header("X-Auth-Token"));
    }
}
