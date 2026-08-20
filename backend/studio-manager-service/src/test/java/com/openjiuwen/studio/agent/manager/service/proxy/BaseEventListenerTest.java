/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.manager.dto.JiuwenAgentEvent;

import okhttp3.Protocol;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * BaseEventListener 单元测试：覆盖 G.MET.06 修改的
 * parseJiuWenEventFromSseData（Optional.ofNullable/empty）与 createErrorRsp（Optional 转换）
 */
class BaseEventListenerTest {

    private BaseEventListener listener;

    @BeforeEach
    void setUp() {
        listener = new BaseEventListener("request-id-1", new HttpHeaders());
    }

    // ============ parseJiuWenEventFromSseData ============

    @Test
    void parseSseData_validJson_shouldReturnPresent() {
        String sseData = "{\"event\":\"message\",\"executionId\":\"exec-1\"}";

        Optional<JiuwenAgentEvent> result = listener.parseJiuWenEventFromSseData(sseData, JiuwenAgentEvent.class);

        assertTrue(result.isPresent());
        assertEquals("message", result.get().getEvent());
        assertEquals("exec-1", result.get().getExecutionId());
    }

    @Test
    void parseSseData_invalidJson_shouldReturnEmpty() {
        Optional<JiuwenAgentEvent> result = listener.parseJiuWenEventFromSseData("not a json", JiuwenAgentEvent.class);

        assertTrue(result.isEmpty());
    }

    @Test
    void parseSseData_nullLiteral_shouldReturnEmpty() {
        // fastjson 对字面量 null 返回 null，应映射为 Optional.empty 而非 NPE
        Optional<JiuwenAgentEvent> result = listener.parseJiuWenEventFromSseData("null", JiuwenAgentEvent.class);

        assertTrue(result.isEmpty());
    }

    // ============ createErrorRsp ============

    @Test
    void createErrorRsp_alreadyConnected_shouldReturnEmpty() throws Exception {
        listener.openConnect = true;

        Optional<org.springframework.http.ResponseEntity<Object>> result = listener.createErrorRsp(null, null);

        assertTrue(result.isEmpty());
    }

    @Test
    void createErrorRsp_withResponse_shouldReturnPresentWithStatusCode() throws Exception {
        Response response = new Response.Builder()
            .request(new Request.Builder().url("http://localhost/test").build())
            .protocol(Protocol.HTTP_1_1)
            .code(400)
            .message("Bad Request")
            .body(ResponseBody.create("{\"errorMsg\":\"bad\"}", null))
            .build();

        Optional<org.springframework.http.ResponseEntity<Object>> result = listener.createErrorRsp(null, response);

        assertTrue(result.isPresent());
        assertEquals(400, result.get().getStatusCode().value());
        assertFalse(result.get().getBody() == null);
    }

    @Test
    void createErrorRsp_noResponse_shouldReturn500InternalError() throws Exception {
        Optional<org.springframework.http.ResponseEntity<Object>> result = listener.createErrorRsp(
            new RuntimeException("boom"), null);

        assertTrue(result.isPresent());
        assertEquals(500, result.get().getStatusCode().value());
        assertInstanceOf(com.openjiuwen.studio.agent.common.dto.ErrorRsp.class, result.get().getBody());
    }
}
