package com.openjiuwen.studio.conversation.infrastructure.adapter;

import com.openjiuwen.studio.conversation.domain.model.ConversationMessage;
import com.openjiuwen.studio.conversation.domain.repository.ConversationRepository;

import okhttp3.Response;
import okhttp3.sse.EventSource;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockingDetails;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * 按轮持久化监听器单元测试（团队新协议）：
 * 入库粒度 = 每次 LLM 调用（一轮）——每轮 reasoning 行 + message 行，工具一次调用合并一行；
 * done/start 不落库（实时完成信号）；user_message 不落；error 只日志不落；
 * 轮边界 = 事件类型（tool_call/sub_done/run_done/error）；created_at 按到达序单调递增。
 */
class ConversationRunEventSourceListenerTest {

    private static final String EXEC = "exec-1";
    private static final String SUB = "sub-1";
    private static final String AGENT = "agent-a";

    private SseEmitter sseEmitter;
    private ConversationRepository conversationRepository;
    private ConversationRunEventSourceListener listener;

    @BeforeEach
    void setUp() {
        sseEmitter = mock(SseEmitter.class);
        conversationRepository = mock(ConversationRepository.class);
        listener = new ConversationRunEventSourceListener(sseEmitter, new CountDownLatch(1), "conv-1", EXEC,
            "model-1", conversationRepository);
    }

    private void feedEvent(String data) {
        listener.onEvent(mock(EventSource.class), null, null, data);
    }

    @SuppressWarnings("unchecked")
    private List<ConversationMessage> captureRows() {
        ArgumentCaptor<List<ConversationMessage>> captor = ArgumentCaptor.forClass(List.class);
        verify(conversationRepository).appendMessages(eq("conv-1"), captor.capture());
        return captor.getValue();
    }

    private static String json(String event, String data) {
        return "{\"event\":\"" + event + "\",\"data\":" + data + ",\"executionId\":\"" + EXEC + "\"}";
    }

    private static String subData(String inner) {
        return "{\"subExecutionId\":\"" + SUB + "\",\"agentId\":\"" + AGENT + "\"" + inner + "}";
    }

    // ---------------------------------------------------------------- 多轮聚合与轮边界

    @Test
    void testSubAgentMultiRound_PersistsReasoningMessageAndToolRows() {
        feedEvent(json("user_message", "{\"conversationId\":\"conv-1\",\"query\":\"hi\"}"));
        feedEvent(json("run_start", "{}"));
        feedEvent(json("sub_start", subData("")));
        feedEvent(json("reasoning", subData(",\"content\":\"想1\"")));
        feedEvent(json("message", subData(",\"delta\":\"出1\"")));
        // 第 1 轮结束：内部工具调用
        feedEvent(json("tool_call", subData(",\"toolCallId\":\"call-1\",\"toolName\":\"weather\","
            + "\"arguments\":{\"city\":\"上海\"}")));
        feedEvent(json("tool_result", subData(",\"toolCallId\":\"call-1\",\"toolName\":\"weather\","
            + "\"result\":\"晴\"")));
        // 第 2 轮
        feedEvent(json("reasoning", subData(",\"content\":\"想2\"")));
        feedEvent(json("message", subData(",\"delta\":\"出2\"")));
        feedEvent(json("sub_done", subData(",\"text\":\"权威文本\"")));
        feedEvent(json("run_done", "{\"text\":\"监督者最终\"}"));
        listener.onClosed(mock(EventSource.class));

        List<ConversationMessage> rows = captureRows();
        // 一轮 reasoning + message，工具合并一行，共 5 行；done 不落库
        assertEquals(5, rows.size());

        // 顺序：reasoning r1 → message r1 → tool → reasoning r2 → message r2（created_at 单调递增）
        ConversationMessage reasoning1 = rows.get(0);
        assertEquals("assistant", reasoning1.getRole());
        assertEquals("reasoning", reasoning1.getEvent());
        assertEquals("想1", reasoning1.getContent());
        assertEquals(SUB, reasoning1.getExecutionRef().getSubExecutionId());
        assertEquals(AGENT, reasoning1.getExecutionRef().getAgentId());

        ConversationMessage message1 = rows.get(1);
        assertEquals("message", message1.getEvent());
        assertEquals("出1", message1.getContent());

        ConversationMessage tool = rows.get(2);
        assertEquals("tool", tool.getRole());
        assertEquals("tool_call", tool.getEvent());
        assertEquals("晴", tool.getContent());
        assertEquals("weather", tool.getToolRef().getToolId());
        assertTrue(tool.getToolRef().getArgs().contains("上海"));
        assertEquals(SUB, tool.getExecutionRef().getSubExecutionId());

        assertEquals("想2", rows.get(3).getContent());
        assertEquals("出2", rows.get(4).getContent());

        for (int i = 1; i < rows.size(); i++) {
            assertTrue(rows.get(i).getCreatedAt().after(rows.get(i - 1).getCreatedAt()),
                "created_at 应按到达序单调递增");
        }
        rows.forEach(r -> assertEquals(EXEC, r.getExecutionRef().getExecutionId()));
    }

    @Test
    void testSupervisorMultiRound_HandoffToolRoutesToRunTable() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("message", "{\"delta\":\"决策1\"}"));
        // 监督者 handoff 工具：无 subExecutionId
        feedEvent(json("tool_call", "{\"toolCallId\":\"call-h\",\"toolName\":\"transfer_to_abcd1234\","
            + "\"arguments\":{\"query\":\"q\"}}"));
        feedEvent(json("tool_result", "{\"toolCallId\":\"call-h\",\"toolName\":\"transfer_to_abcd1234\","
            + "\"result\":\"[子Agent abcd] 答案\"}"));
        feedEvent(json("message", "{\"delta\":\"最终回答\"}"));
        feedEvent(json("run_done", "{\"text\":\"监督者最终\"}"));
        listener.onClosed(mock(EventSource.class));

        List<ConversationMessage> rows = captureRows();
        assertEquals(3, rows.size());

        // 三行都属于主 Agent（subExecutionId = null → run 表）
        rows.forEach(r -> assertNull(r.getExecutionRef().getSubExecutionId()));
        assertEquals("决策1", rows.get(0).getContent());
        ConversationMessage tool = rows.get(1);
        assertEquals("tool", tool.getRole());
        assertEquals("transfer_to_abcd1234", tool.getToolRef().getToolId());
        assertEquals("[子Agent abcd] 答案", tool.getContent());
        assertEquals("最终回答", rows.get(2).getContent());
    }

    @Test
    void testToolError_ErrorTextGoesIntoToolRow() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("tool_call", "{\"toolCallId\":\"call-1\",\"toolName\":\"weather\"}"));
        feedEvent(json("tool_result", "{\"toolCallId\":\"call-1\",\"toolName\":\"weather\","
            + "\"result\":\"Tool execution error: boom\"}"));
        feedEvent(json("run_done", "{\"text\":\"最终\"}"));
        listener.onClosed(mock(EventSource.class));

        ConversationMessage tool = captureRows().get(0);
        assertEquals("Tool execution error: boom", tool.getContent());
    }

    @Test
    void testToolCallWithoutResult_WritesNoResultMarker() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("tool_call", "{\"toolCallId\":\"call-1\",\"toolName\":\"weather\"}"));
        feedEvent(json("run_done", "{\"text\":\"最终\"}"));
        listener.onClosed(mock(EventSource.class));

        ConversationMessage tool = captureRows().get(0);
        assertEquals("（未返回结果）", tool.getContent());
        assertEquals("weather", tool.getToolRef().getToolId());
    }

    // ---------------------------------------------------------------- 异常/幂等/边界

    @Test
    void testNormalClose_PersistsBeforeSendingBrowserDoneMarker() throws Exception {
        feedEvent(json("message", "{\"delta\":\"最终回答\"}"));
        feedEvent(json("run_done", "{\"text\":\"最终回答\"}"));

        listener.onClosed(mock(EventSource.class));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<ConversationMessage>> rowsCaptor = ArgumentCaptor.forClass(List.class);
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Set<ResponseBodyEmitter.DataWithMediaType>> doneCaptor = ArgumentCaptor.forClass(Set.class);
        InOrder closeOrder = inOrder(conversationRepository, sseEmitter);
        closeOrder.verify(conversationRepository).appendMessages(eq("conv-1"), rowsCaptor.capture());
        closeOrder.verify(sseEmitter).send(doneCaptor.capture());
        closeOrder.verify(sseEmitter).complete();

        assertEquals("最终回答", rowsCaptor.getValue().get(0).getContent());
        String lastPayload = doneCaptor.getValue().stream()
            .map(data -> data.getData().toString())
            .collect(Collectors.joining());
        assertEquals("data:[DONE]\n\n", lastPayload);
    }

    @Test
    void testOnFailure_PersistsBufferedContent() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("reasoning", "{\"content\":\"思考中\"}"));
        feedEvent(json("message", "{\"delta\":\"部分输出\"}"));
        listener.onFailure(mock(EventSource.class), new RuntimeException("stream broken"), mock(Response.class));

        List<ConversationMessage> rows = captureRows();
        // 未结算轮也落库（已获取到的内容）
        assertEquals(2, rows.size());
        assertEquals("思考中", rows.get(0).getContent());
        assertEquals("部分输出", rows.get(1).getContent());
    }

    @Test
    void testOnClosedThenOnFailure_IdempotentSingleWrite() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("message", "{\"delta\":\"输出\"}"));
        feedEvent(json("run_done", "{\"text\":\"最终\"}"));
        listener.onClosed(mock(EventSource.class));
        listener.onFailure(mock(EventSource.class), new RuntimeException("late failure"), null);

        verify(conversationRepository, times(1)).appendMessages(eq("conv-1"), anyList());
    }

    @Test
    void testErrorEvent_NotPersisted() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("error", "{\"code\":\"supervisor_error\",\"message\":\"boom\"}"));
        listener.onClosed(mock(EventSource.class));

        // error 只记日志不落库；run_start 也不落 → 无行
        verify(conversationRepository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void testNoBoundary_StreamCloseSettlesPartialRound() {
        feedEvent(json("run_start", "{}"));
        feedEvent(json("reasoning", "{\"content\":\"想\"}"));
        feedEvent(json("message", "{\"delta\":\"增量1\"}"));
        listener.onClosed(mock(EventSource.class));

        List<ConversationMessage> rows = captureRows();
        assertEquals(2, rows.size());
        assertEquals("想", rows.get(0).getContent());
        assertEquals("增量1", rows.get(1).getContent());
    }

    @Test
    void testOnlyNonPersistedEvents_NoWrite() {
        feedEvent(json("user_message", "{\"conversationId\":\"conv-1\",\"query\":\"hi\"}"));
        feedEvent(json("run_start", "{}"));
        feedEvent(json("sub_start", subData("")));
        feedEvent(json("run_done", "{\"text\":\"最终\"}"));
        listener.onClosed(mock(EventSource.class));

        // user_message/run_start/sub_start/run_done 均不落库 → 无行
        verify(conversationRepository, never()).appendMessages(anyString(), anyList());
    }

    @Test
    void testSkillActivatedEvent_ForwardOnlyAndNeverPersisted() throws Exception {
        String event = "{\"event\":\"skill_activated\",\"data\":{\"skillId\":\"s1\","
            + "\"name\":\"会议纪要\",\"versionId\":\"v1\"},\"executionId\":\"exec-1\"}";
        feedEvent(event);
        listener.onClosed(mock(EventSource.class));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Set<ResponseBodyEmitter.DataWithMediaType>> captor = ArgumentCaptor.forClass(Set.class);
        verify(sseEmitter, times(2)).send(captor.capture());
        String payload = captor.getAllValues().stream()
            .flatMap(Set::stream)
            .map(data -> data.getData().toString())
            .collect(Collectors.joining());
        assertEquals("data:" + event + "\n\ndata:[DONE]\n\n", payload);
        verify(conversationRepository, never()).appendMessages(anyString(), anyList());
    }

    // ---------------------------------------------------------------- 透传

    @Test
    void testAllEventsRelayedToFrontend() throws Exception {
        feedEvent(json("user_message", "{\"query\":\"hi\"}"));
        feedEvent(json("run_start", "{}"));
        feedEvent(json("message", "{\"delta\":\"增量\"}"));
        feedEvent(json("reasoning", "{\"content\":\"想\"}"));
        feedEvent(json("tool_call", "{\"toolCallId\":\"c1\",\"toolName\":\"w\"}"));
        feedEvent(json("tool_result", "{\"toolCallId\":\"c1\",\"toolName\":\"w\",\"result\":\"r\"}"));
        feedEvent(json("sub_done", subData(",\"text\":\"t\"")));
        feedEvent(json("run_done", "{\"text\":\"最终\"}"));
        feedEvent(json("error", "{\"code\":\"e\",\"message\":\"m\"}"));
        listener.onClosed(mock(EventSource.class));

        // 每个业务事件都透传前端，并在正常关闭时补一个浏览器终止标记（9 + 1 次 send）。
        long sendCount = mockingDetails(sseEmitter).getInvocations().stream()
            .filter(i -> i.getMethod().getName().equals("send"))
            .count();
        assertEquals(10, sendCount);
    }
}
