/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.dto.md;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;

import org.junit.jupiter.api.Test;

import java.util.Map;

class ModelServiceCheckReqTest {

    @Test
    void testSetGetModelType() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNull(req.getModelType());
        ModelServiceCheckReq result = req.setModelType("llm");
        assertSame(req, result);
        assertEquals("llm", req.getModelType());
    }

    @Test
    void testSetGetApiUrl() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNull(req.getApiUrl());
        ModelServiceCheckReq result = req.setApiUrl("http://api.example.com");
        assertSame(req, result);
        assertEquals("http://api.example.com", req.getApiUrl());
    }

    @Test
    void testSetApiUrlTrimsWhitespace() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        ModelServiceCheckReq result = req.setApiUrl("  https://api.example.com/v1/chat/completions  ");
        assertSame(req, result);
        assertEquals("https://api.example.com/v1/chat/completions", req.getApiUrl());
    }

    @Test
    void testSetApiUrlNullRemainsNull() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        req.setApiUrl("http://api.example.com");
        req.setApiUrl(null);
        assertNull(req.getApiUrl());
    }

    @Test
    void testSetGetAuthType() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNull(req.getAuthType());
        ModelServiceCheckReq result = req.setAuthType("token");
        assertSame(req, result);
        assertEquals("token", req.getAuthType());
    }

    @Test
    void testSetGetAuthInfo() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNull(req.getAuthInfo());
        Map<String, String> authInfo = Map.of("key", "value");
        ModelServiceCheckReq result = req.setAuthInfo(authInfo);
        assertSame(req, result);
        assertEquals(authInfo, req.getAuthInfo());
    }

    @Test
    void testSetGetModelName() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNull(req.getModelName());
        ModelServiceCheckReq result = req.setModelName("gpt-4");
        assertSame(req, result);
        assertEquals("gpt-4", req.getModelName());
    }

    @Test
    void testSetGetInterfaceProtocol() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNull(req.getInterfaceProtocol());
        ModelServiceCheckReq result = req.setInterfaceProtocol("openai");
        assertSame(req, result);
        assertEquals("openai", req.getInterfaceProtocol());
    }

    @Test
    void testChainedSetters() {
        ModelServiceCheckReq req = new ModelServiceCheckReq()
                .setModelType("llm")
                .setApiUrl("http://api.example.com")
                .setAuthType("token")
                .setAuthInfo(Map.of("key", "value"))
                .setModelName("gpt-4")
                .setInterfaceProtocol("openai");
        assertEquals("llm", req.getModelType());
        assertEquals("http://api.example.com", req.getApiUrl());
        assertEquals("token", req.getAuthType());
        assertEquals("gpt-4", req.getModelName());
        assertEquals("openai", req.getInterfaceProtocol());
    }

    @Test
    void testNoArgsConstructor() {
        ModelServiceCheckReq req = new ModelServiceCheckReq();
        assertNotNull(req);
    }
}
