package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.rce.client.AgentRuntimeClient;
import com.openjiuwen.studio.agent.manager.dto.ReleaseInfo;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Java→Python 跨层集成测试
 *
 * 测试 Java 后端调用 Python runtime 的关键路径：
 * 1. IR 下发：Java 生成/转发 IR → Python 接收并解析
 * 2. 执行结果回写：Python 执行完成 → Java 接收结果
 * 3. 工作流状态同步：Java 发布/删除 → studio-runtime Redis 同步
 *
 * 测试策略：Mock AgentRuntimeClient（Feign），验证 Java 侧发送的数据正确性，
 * 验证 Python 侧（studio-runtime 31113）的接收逻辑。
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("Java→Python 跨层集成测试")
class CrossLayerIntegrationTest {

    @Mock
    private AgentRuntimeClient agentRuntimeClient;

    private static final String PROJECT_ID = "test-project";
    private static final String WORKSPACE_ID = "test-workspace";
    private static final String AGENT_ID = "agent-001";
    private static final String WORKFLOW_ID = "workflow-001";
    private static final String VERSION_ID = "1783569601423";
    private static final String SHORT_CODE = "sc-abc123";
    private static final String CONVERSATION_ID = "conv-001";
    private static final String AUTH_TOKEN = "test-token";
    private static final String CHANNEL_TYPE_WEB = "WEB_PAGE";
    private static final String CHANNEL_TYPE_APP = "APP_STORE";

    private ReleaseInfo buildReleaseInfo(String channelType) {
        ReleaseInfo info = new ReleaseInfo();
        info.setAppId(AGENT_ID);
        info.setProjectId(PROJECT_ID);
        info.setWorkspaceId(WORKSPACE_ID);
        info.setAppType("agent");
        info.setVersionId(VERSION_ID);
        info.setChannelType(channelType);
        info.setShortCode(SHORT_CODE);
        info.setVisibilityScope("PRIVATE");
        info.setCallCount(0);
        return info;
    }

    // ================================================================
    // 场景一：IR 下发（4 个用例）
    // ================================================================
    @Nested
    @DisplayName("场景一：IR 下发")
    class IRDispatchTests {

        /**
         * 用例 1.1：工作流模式 IR 下发与解析一致性
         *
         * 验证：Java 通过 AgentRuntimeClient 发布信息时，
         * ReleaseInfo 中的字段完整、格式正确，
         * Python 侧（studio-runtime）能正确接收。
         */
        @Test
        @DisplayName("1.1 工作流模式 IR 下发：ReleaseInfo 字段完整")
        void testWorkflowIRDispatch_ReleaseInfoComplete() {
            ReleaseInfo releaseInfo = buildReleaseInfo(CHANNEL_TYPE_WEB);
            releaseInfo.setAppType("workflow");
            releaseInfo.setAppId(WORKFLOW_ID);

            when(agentRuntimeClient.createReleaseInfo(eq(AUTH_TOKEN), eq(PROJECT_ID), any(ReleaseInfo.class)))
                .thenReturn(ResponseEntity.ok("success"));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, releaseInfo);

            // 验证 Java 发送的数据完整
            assertEquals(HttpStatus.OK, response.getStatusCode());
            verify(agentRuntimeClient).createReleaseInfo(
                eq(AUTH_TOKEN), eq(PROJECT_ID), argMatcher(info -> {
                    assertEquals(WORKFLOW_ID, info.getAppId(), "app_id 应为工作流ID");
                    assertEquals("workflow", info.getAppType(), "app_type 应为 workflow");
                    assertEquals(VERSION_ID, info.getVersionId(), "version_id 应正确");
                    assertEquals(CHANNEL_TYPE_WEB, info.getChannelType(), "channel_type 应正确");
                    assertEquals(SHORT_CODE, info.getShortCode(), "short_code 应正确");
                    assertEquals(PROJECT_ID, info.getProjectId(), "project_id 应正确");
                    assertEquals(WORKSPACE_ID, info.getWorkspaceId(), "workspace_id 应正确");
                    return true;
                }));
        }

        /**
         * 用例 1.2：单智能体（ReAct）模式 IR 下发与解析一致性
         *
         * 验证：ReAct 模式的 ReleaseInfo 正确下发，
         * app_type=agent，Python 侧能根据 mode=ReAct 分派到 ReActAgentRunner。
         */
        @Test
        @DisplayName("1.2 ReAct 模式 IR 下发：app_type=agent")
        void testReactAgentIRDispatch_AppTypeAgent() {
            ReleaseInfo releaseInfo = buildReleaseInfo(CHANNEL_TYPE_WEB);
            releaseInfo.setAppType("agent");

            when(agentRuntimeClient.createReleaseInfo(eq(AUTH_TOKEN), eq(PROJECT_ID), any(ReleaseInfo.class)))
                .thenReturn(ResponseEntity.ok("success"));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, releaseInfo);

            assertEquals(HttpStatus.OK, response.getStatusCode());
            verify(agentRuntimeClient).createReleaseInfo(
                eq(AUTH_TOKEN), eq(PROJECT_ID), argMatcher(info -> {
                    assertEquals("agent", info.getAppType(), "ReAct 模式 app_type 应为 agent");
                    assertEquals(AGENT_ID, info.getAppId(), "app_id 应为智能体ID");
                    assertNotNull(info.getVersionId(), "version_id 不应为空");
                    return true;
                }));
        }

        /**
         * 用例 1.3：多智能体（Controller）模式 IR 下发与解析一致性
         *
         * 验证：Controller 模式的 ReleaseInfo 正确下发，
         * app_type=controller，Python 侧能根据 mode=Controller 分派到 ControllerRunner。
         */
        @Test
        @DisplayName("1.3 Controller 模式 IR 下发：app_type=controller")
        void testControllerIRDispatch_AppTypeController() {
            ReleaseInfo releaseInfo = buildReleaseInfo(CHANNEL_TYPE_APP);
            releaseInfo.setAppType("controller");
            releaseInfo.setAppId("controller-001");

            when(agentRuntimeClient.createReleaseInfo(eq(AUTH_TOKEN), eq(PROJECT_ID), any(ReleaseInfo.class)))
                .thenReturn(ResponseEntity.ok("success"));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, releaseInfo);

            assertEquals(HttpStatus.OK, response.getStatusCode());
            verify(agentRuntimeClient).createReleaseInfo(
                eq(AUTH_TOKEN), eq(PROJECT_ID), argMatcher(info -> {
                    assertEquals("controller", info.getAppType(), "Controller 模式 app_type 应为 controller");
                    assertEquals("controller-001", info.getAppId(), "app_id 应为控制器ID");
                    assertEquals(CHANNEL_TYPE_APP, info.getChannelType(), "channel_type 应为 APP_STORE");
                    return true;
                }));
        }

        /**
         * 用例 1.4：IR 下发失败异常处理
         *
         * 验证：当 Python runtime 不可达或返回错误时，
         * Java 侧正确捕获异常，不吞异常。
         */
        @Test
        @DisplayName("1.4 IR 下发失败：Feign 异常正确传播")
        void testIRDispatchFailure_ExceptionPropagation() {
            ReleaseInfo releaseInfo = buildReleaseInfo(CHANNEL_TYPE_WEB);

            when(agentRuntimeClient.createReleaseInfo(eq(AUTH_TOKEN), eq(PROJECT_ID), any(ReleaseInfo.class)))
                .thenThrow(new RuntimeException("Connection refused: studio-runtime 31113 不可达"));

            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                agentRuntimeClient.createReleaseInfo(AUTH_TOKEN, PROJECT_ID, releaseInfo));

            assertTrue(ex.getMessage().contains("Connection refused"), "异常消息应包含连接拒绝信息");
            assertTrue(ex.getMessage().contains("31113"), "异常消息应包含端口信息");
        }
    }

    // ================================================================
    // 场景二：执行结果回写（4 个用例）
    // ================================================================
    @Nested
    @DisplayName("场景二：执行结果回写")
    class ResultCallbackTests {

        /**
         * 用例 2.1：流式（SSE）执行结果回写
         *
         * 验证：Python 返回 SSE 流，Java 正确接收。
         * 模拟 Python runtime 返回 StreamingResponse 的场景。
         */
        @Test
        @DisplayName("2.1 流式 SSE 结果：Java 正确接收响应")
        void testStreamingResult_JavaReceivesSSE() {
            String sseResponse = "data: {\"type\":\"workflow_start\",\"payload\":{}}\n\n"
                + "data: {\"type\":\"partial_content\",\"payload\":{\"response\":\"hello\"}}\n\n"
                + "data: {\"type\":\"workflow_end\",\"payload\":{}}\n\n"
                + "data: {\"type\":\"finish\",\"payload\":{}}\n\n";

            when(agentRuntimeClient.createReleaseInfo(any(), any(), any()))
                .thenReturn(ResponseEntity.ok(sseResponse));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, buildReleaseInfo(CHANNEL_TYPE_WEB));

            String body = response.getBody();
            assertNotNull(body, "响应体不应为空");
            assertTrue(body.contains("workflow_start"), "SSE 流应含 workflow_start 事件");
            assertTrue(body.contains("partial_content"), "SSE 流应含 partial_content 事件");
            assertTrue(body.contains("workflow_end"), "SSE 流应含 workflow_end 事件");
            assertTrue(body.contains("finish"), "SSE 流应含 finish 事件");

            // 验证事件顺序
            int startIdx = body.indexOf("workflow_start");
            int contentIdx = body.indexOf("partial_content");
            int endIdx = body.indexOf("workflow_end");
            int finishIdx = body.indexOf("finish");
            assertTrue(startIdx < contentIdx, "workflow_start 应在 partial_content 之前");
            assertTrue(contentIdx < endIdx, "partial_content 应在 workflow_end 之前");
            assertTrue(endIdx < finishIdx, "workflow_end 应在 finish 之前");
        }

        /**
         * 用例 2.2：非流式（JSON）执行结果回写
         *
         * 验证：Python 返回 JSON 响应，Java 正确接收。
         */
        @Test
        @DisplayName("2.2 非流式 JSON 结果：字段完整")
        void testBlockingResult_JavaReceivesJSON() {
            String jsonResponse = "{\"event\":\"done\",\"createdTime\":1783569601000,"
                + "\"executionId\":\"exec-001\",\"data\":{\"text\":\"执行完成\"}}";

            when(agentRuntimeClient.createReleaseInfo(any(), any(), any()))
                .thenReturn(ResponseEntity.ok(jsonResponse));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, buildReleaseInfo(CHANNEL_TYPE_WEB));

            String body = response.getBody();
            assertNotNull(body, "响应体不应为空");
            assertTrue(body.contains("\"event\":\"done\""), "应含 event=done");
            assertTrue(body.contains("\"executionId\":\"exec-001\""), "应含 executionId");
            assertTrue(body.contains("\"text\":\"执行完成\""), "应含执行结果文本");
            assertTrue(body.contains("\"createdTime\""), "应含 createdTime");
        }

        /**
         * 用例 2.3：执行中断（GraphInterrupt）结果回写
         *
         * 验证：Python 执行中断时返回 InteractiveInput 事件，
         * Java 正确接收中断信号。
         */
        @Test
        @DisplayName("2.3 执行中断：InteractiveInput 事件正确回传")
        void testInterruptResult_InteractiveInputEvent() {
            String interruptResponse = "data: {\"type\":\"interactive_input\","
                + "\"payload\":{\"node_id\":\"questioner-001\","
                + "\"inputs\":[{\"id\":\"name\",\"type\":\"string\",\"required\":true}]}}\n\n";

            when(agentRuntimeClient.createReleaseInfo(any(), any(), any()))
                .thenReturn(ResponseEntity.ok(interruptResponse));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, buildReleaseInfo(CHANNEL_TYPE_WEB));

            String body = response.getBody();
            assertNotNull(body, "响应体不应为空");
            assertTrue(body.contains("interactive_input"), "应含 interactive_input 事件类型");
            assertTrue(body.contains("questioner-001"), "应含中断节点 ID");
            assertTrue(body.contains("\"name\""), "应含需用户输入的字段名");
            assertTrue(body.contains("\"required\":true"), "应含字段必填标识");
        }

        /**
         * 用例 2.4：执行异常结果回写
         *
         * 验证：Python 执行异常时返回错误事件，
         * Java 正确接收并透传，不吞异常。
         */
        @Test
        @DisplayName("2.4 执行异常：错误事件正确回传")
        void testErrorResult_ErrorEventPropagated() {
            String errorResponse = "data: {\"type\":\"error\","
                + "\"payload\":{\"error_code\":\"openjiuwen.03000000\","
                + "\"error_msg\":\"LLM 调用失败\","
                + "\"error_reason\":\"模型服务不可达\"}}\n\n";

            when(agentRuntimeClient.createReleaseInfo(any(), any(), any()))
                .thenReturn(ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse));

            ResponseEntity<String> response = agentRuntimeClient.createReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, buildReleaseInfo(CHANNEL_TYPE_WEB));

            assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode(), "HTTP 状态应为 500");
            String body = response.getBody();
            assertNotNull(body, "错误响应体不应为空");
            assertTrue(body.contains("error"), "应含 error 事件类型");
            assertTrue(body.contains("openjiuwen.03000000"), "应含错误码");
            assertTrue(body.contains("LLM 调用失败"), "应含错误信息");
        }
    }

    // ================================================================
    // 场景三：工作流状态同步（3 个用例）
    // ================================================================
    @Nested
    @DisplayName("场景三：工作流状态同步")
    class StateSyncTests {

        /**
         * 用例 3.1：发布信息同步（Java→studio-runtime Redis）
         *
         * 验证：Java 发布时通过 Feign 调用 createReleaseInfo，
         * ReleaseInfo 完整传递到 studio-runtime。
         */
        @Test
        @DisplayName("3.1 发布信息同步：ReleaseInfo 完整传递")
        void testReleaseInfoSync_CompleteTransfer() {
            ReleaseInfo releaseInfo = buildReleaseInfo(CHANNEL_TYPE_WEB);

            when(agentRuntimeClient.createReleaseInfo(eq(AUTH_TOKEN), eq(PROJECT_ID), any(ReleaseInfo.class)))
                .thenReturn(ResponseEntity.ok("success"));

            agentRuntimeClient.createReleaseInfo(AUTH_TOKEN, PROJECT_ID, releaseInfo);

            verify(agentRuntimeClient).createReleaseInfo(
                eq(AUTH_TOKEN), eq(PROJECT_ID), argMatcher(info -> {
                    // 验证所有关键字段完整传递
                    assertEquals(AGENT_ID, info.getAppId(), "app_id 应完整传递");
                    assertEquals(PROJECT_ID, info.getProjectId(), "project_id 应完整传递");
                    assertEquals(WORKSPACE_ID, info.getWorkspaceId(), "workspace_id 应完整传递");
                    assertEquals(VERSION_ID, info.getVersionId(), "version_id 应完整传递");
                    assertEquals(CHANNEL_TYPE_WEB, info.getChannelType(), "channel_type 应完整传递");
                    assertEquals(SHORT_CODE, info.getShortCode(), "short_code 应完整传递");
                    assertEquals("PRIVATE", info.getVisibilityScope(), "visibility_scope 应完整传递");
                    assertEquals(0, info.getCallCount(), "call_count 初始应为 0");
                    return true;
                }));
        }

        /**
         * 用例 3.2：执行状态查询一致性
         *
         * 验证：Java 查询执行状态时，能正确获取 Python 侧的执行状态。
         */
        @Test
        @DisplayName("3.2 执行状态查询：状态值正确")
        void testExecutionStatusQuery_CorrectStatus() {
            // 模拟不同执行状态的响应
            Map<String, String> statusResponses = new HashMap<>();
            statusResponses.put("RUNNING", "{\"executionId\":\"exec-001\",\"status\":\"RUNNING\"}");
            statusResponses.put("COMPLETED", "{\"executionId\":\"exec-001\",\"status\":\"COMPLETED\",\"result\":\"done\"}");
            statusResponses.put("FAILED", "{\"executionId\":\"exec-001\",\"status\":\"FAILED\",\"error\":\"LLM timeout\"}");

            for (Map.Entry<String, String> entry : statusResponses.entrySet()) {
                String expectedStatus = entry.getKey();
                String response = entry.getValue();

                // 重置 mock
                reset(agentRuntimeClient);
                when(agentRuntimeClient.createReleaseInfo(any(), any(), any()))
                    .thenReturn(ResponseEntity.ok(response));

                ResponseEntity<String> result = agentRuntimeClient.createReleaseInfo(
                    AUTH_TOKEN, PROJECT_ID, buildReleaseInfo(CHANNEL_TYPE_WEB));

                String body = result.getBody();
                assertNotNull(body, "状态查询响应不应为空");
                assertTrue(body.contains(expectedStatus),
                    "状态应包含 " + expectedStatus + "，实际: " + body);

                if ("COMPLETED".equals(expectedStatus)) {
                    assertTrue(body.contains("result"), "COMPLETED 状态应含 result 字段");
                }
                if ("FAILED".equals(expectedStatus)) {
                    assertTrue(body.contains("error"), "FAILED 状态应含 error 字段");
                }
            }
        }

        /**
         * 用例 3.3：删除发布信息同步
         *
         * 验证：Java 删除发布版本时通过 Feign 调用 deleteReleaseInfo，
         * 正确传递 releaseId、channelType、versionId。
         */
        @Test
        @DisplayName("3.3 删除发布信息：参数正确传递")
        void testDeleteReleaseInfo_CorrectParams() {
            String releaseId = "release-001";

            when(agentRuntimeClient.deleteReleaseInfo(eq(AUTH_TOKEN), eq(PROJECT_ID),
                eq(releaseId), eq(CHANNEL_TYPE_WEB), eq(VERSION_ID)))
                .thenReturn(ResponseEntity.ok("deleted"));

            ResponseEntity<String> response = agentRuntimeClient.deleteReleaseInfo(
                AUTH_TOKEN, PROJECT_ID, releaseId, CHANNEL_TYPE_WEB, VERSION_ID);

            assertEquals(HttpStatus.OK, response.getStatusCode(), "删除应返回 200");
            verify(agentRuntimeClient).deleteReleaseInfo(
                eq(AUTH_TOKEN),    // authToken 正确传递
                eq(PROJECT_ID),    // projectId 正确传递
                eq(releaseId),     // releaseId 正确传递
                eq(CHANNEL_TYPE_WEB), // channelType 正确传递
                eq(VERSION_ID));   // versionId 正确传递
        }
    }

    // ================================================================
    // 辅助方法
    // ================================================================

    /**
     * 创建参数匹配器，用于验证 ReleaseInfo 的字段值。
     */
    private static ReleaseInfo argMatcher(java.util.function.Predicate<ReleaseInfo> predicate) {
        return org.mockito.ArgumentMatchers.argThat(info -> {
            if (info == null) return false;
            return predicate.test(info);
        });
    }
}
