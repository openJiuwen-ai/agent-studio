/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RequestContextUtilsTest {

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    @Test
    void testSetContextAndGetRequestAuthToken() {
        RequestContextUtils.setContext("test-token", "project-1", "domain-1");
        assertEquals("test-token", RequestContextUtils.getRequestAuthToken());
    }

    @Test
    void testSetContextAndGetRequestProjectId() {
        RequestContextUtils.setContext("token", "project-1", "domain-1");
        assertEquals("project-1", RequestContextUtils.getRequestProjectId());
    }

    @Test
    void testSetContextAndGetRequestUserDomainId() {
        RequestContextUtils.setContext("token", "project-1", "domain-1");
        assertEquals("domain-1", RequestContextUtils.getRequestUserDomainId());
    }

    @Test
    void testSetContextAndGetRequestUserDomainIdOptional() {
        RequestContextUtils.setContext("token", "project-1", "domain-1");
        Optional<String> domainId = RequestContextUtils.getRequestUserDomainIdOptional();
        assertTrue(domainId.isPresent());
        assertEquals("domain-1", domainId.get());
    }

    @Test
    void testGetRequestIamCtxOptional_Empty() {
        Optional<SimpleUser> user = RequestContextUtils.getRequestIamCtxOptional();
        assertTrue(user.isEmpty());
    }

    @Test
    void testGetRequestIamCtx_ThrowsWhenEmpty() {
        assertThrows(RuntimeException.class, RequestContextUtils::getRequestIamCtx);
    }

    @Test
    void testSetRequestAuthTokenAndProjectId() {
        RequestContextUtils.setRequestAuthTokenAndProjectId("my-token", "my-project");
        assertEquals("my-token", RequestContextUtils.getRequestAuthToken());
        assertEquals("my-project", RequestContextUtils.getRequestProjectId());
    }

    @Test
    void testSetRequestAuthTokenAndUserId() {
        RequestContextUtils.setRequestAuthTokenAndUserId("token", "project", "user-1");
        assertEquals("user-1", RequestContextUtils.getRequestUserId());
    }

    @Test
    void testSetContextWithSimpleUser() {
        SimpleUser user = new SimpleUser();
        user.setToken("t");
        user.setProjectId("p");
        user.setUserId("u");
        user.setUserName("name");
        user.setDomainId("d");
        user.setDomainName("dn");
        RequestContextUtils.setContext(user);

        assertEquals("t", RequestContextUtils.getRequestAuthToken());
        assertEquals("p", RequestContextUtils.getRequestProjectId());
        assertEquals("u", RequestContextUtils.getRequestUserId());
        assertEquals("name", RequestContextUtils.getRequestUserName());
        assertEquals("d", RequestContextUtils.getRequestUserDomainId());
        assertEquals("dn", RequestContextUtils.getRequestUserDomainName());
    }

    @Test
    void testGetRequestUser() {
        RequestContextUtils.setContext("token", "project", "domain");
        SimpleUser user = RequestContextUtils.getRequestUser();
        assertNotNull(user);
        assertEquals("token", user.getToken());
    }

    @Test
    void testSetAndGetHeaders() {
        Map<String, String> headers = new HashMap<>();
        headers.put("key", "value");
        RequestContextUtils.setHeaders(headers);
        Map<String, String> result = RequestContextUtils.getHeaders();
        assertNotNull(result);
        assertEquals("value", result.get("key"));
    }

    @Test
    void testRemove() {
        RequestContextUtils.setContext("token", "project", "domain");
        RequestContextUtils.remove();
        assertThrows(RuntimeException.class, RequestContextUtils::getRequestIamCtx);
    }

    // ===== 瘦身修订回归：ThreadLocal 优先于 request attribute =====

    @Test
    void testThreadLocalTakesPriorityOverRequestAttribute() {
        // ThreadLocal(显式 set 的上下文,如 TaskRuntimeService 切换任务归属
        // 用户)优先于 request attribute(filter 写入的登录用户)——显式 set
        // 是意图覆盖,须被尊重;attribute 优先会静默忽略请求线程内的显式 set
        SimpleUser threadLocalUser = new SimpleUser();
        threadLocalUser.setToken("task-token");
        threadLocalUser.setUserId("task-user");
        RequestContextUtils.setContext(threadLocalUser);

        // getRequestIamCtx 应返回 ThreadLocal 的值(无 request 上下文时)
        SimpleUser result = RequestContextUtils.getRequestIamCtx();
        assertEquals("task-token", result.getToken());
        assertEquals("task-user", result.getUserId());
    }

    @Test
    void testCurrentUserKeyMatchesFilterWriteKey() {
        // RequestContextUtils 读取键与 SimpleUserContextFilter 写入键
        // 均为 "CURRENT_USER"(大写)——瘦身修订将原 "currentUser"(小写,
        // 不命中)改为 "CURRENT_USER",此测试守护键名对齐不被回退
        // (键名私有,通过 ThreadLocal 路径间接验证:有 ThreadLocal 时
        // 必命中,无 ThreadLocal 时 attribute 兜底——两条路径共用同一个
        // getRequestIamCtx 出口,键名对齐是 attribute 路径可用的前提)
        SimpleUser user = new SimpleUser();
        user.setToken("filter-token");
        RequestContextUtils.setContext(user);
        assertEquals("filter-token", RequestContextUtils.getRequestAuthToken());
    }
}
