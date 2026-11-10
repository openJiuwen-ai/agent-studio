/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.mcp;

import com.openjiuwen.studio.agent.common.dto.auth.AuthInfo;
import com.openjiuwen.studio.agent.common.dto.auth.AuthKeyInfo;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.entity.McpServiceEntity;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * FEAT-093 调测期动态凭证护栏（mergeDynamicDebugHeaders）直接单测。
 *
 * 方法仅依赖入参实体与两个 Map（无 Spring 依赖），可裸实例直测。
 */
class McpServiceManagerTest {

    private static final String SVC_ID = "svc-e2e-0001";

    private McpServiceManager newManager() {
        return new McpServiceManager();
    }

    private McpServiceEntity dynamicService(String... targetNames) {
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.DYNAMIC);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        authInfo.setAuthKeys(java.util.Arrays.stream(targetNames)
            .map(name -> {
                AuthKeyInfo key = new AuthKeyInfo();
                key.setTargetName(name);
                key.setAuthKey(null);
                return key;
            })
            .collect(java.util.stream.Collectors.toList()));

        McpServiceEntity entity = new McpServiceEntity();
        entity.setId(SVC_ID);
        entity.setName("FEAT093-E2E-credential-echo");
        entity.setAuthInfo(authInfo);
        return entity;
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：已登记头名 + 合法值 → 并入出站 headerInfo")
    void test_merge_debug_headers_positive() {
        Map<String, String> headerInfo = new HashMap<>();
        newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
            Map.of("Authorization", "Bearer tok-1"), headerInfo);
        Assertions.assertEquals("Bearer tok-1", headerInfo.get("Authorization"));
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：登记头名的大小写变体 → 接受（HTTP 头名大小写不敏感）")
    void test_merge_debug_headers_case_variant_accepted() {
        Map<String, String> headerInfo = new HashMap<>();
        newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
            Map.of("authorization", "Bearer tok-2"), headerInfo);
        Assertions.assertEquals("Bearer tok-2", headerInfo.get("authorization"));
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：未登记头名 → 拒绝")
    void test_merge_debug_headers_unregistered_rejected() {
        Map<String, String> headerInfo = new HashMap<>();
        Assertions.assertThrows(AgentStudioException.class,
            () -> newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
                Map.of("X-Other", "v"), headerInfo));
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：平台保留关联头 → 就地拒绝（D-02/B07）")
    void test_merge_debug_headers_reserved_correlation_rejected() {
        for (String reserved : new String[] {"X-Request-Id", "X-Execution-Id", "traceparent"}) {
            Map<String, String> headerInfo = new HashMap<>();
            Assertions.assertThrows(AgentStudioException.class,
                () -> newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
                    Map.of(reserved, "fake"), headerInfo), "reserved: " + reserved);
        }
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：非法头名字符（空格/冒号）与逐跳敏感头 → 拒绝")
    void test_merge_debug_headers_illegal_name_rejected() {
        for (String bad : new String[] {"Bad Header", "Auth:Inj", "Host", "Content-Length"}) {
            Map<String, String> headerInfo = new HashMap<>();
            Assertions.assertThrows(AgentStudioException.class,
                () -> newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
                    Map.of(bad, "v"), headerInfo), "name: " + bad);
        }
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：非法头值（非 Latin-1/控制字符）→ 拒绝")
    void test_merge_debug_headers_illegal_value_rejected() {
        Map<String, String> headerInfo = new HashMap<>();
        Assertions.assertThrows(AgentStudioException.class,
            () -> newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
                Map.of("Authorization", "Bearer 中文令牌"), headerInfo));
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：空白值 → 跳过（=本次不注入，不报错）")
    void test_merge_debug_headers_blank_value_skipped() {
        Map<String, String> headerInfo = new HashMap<>();
        newManager().mergeDynamicDebugHeaders(dynamicService("Authorization"),
            Map.of("Authorization", "   "), headerInfo);
        Assertions.assertFalse(headerInfo.containsKey("Authorization"));
    }

    @Test
    @DisplayName("FEAT-093 调测护栏：非 DYNAMIC scope → 整段忽略不报错")
    void test_merge_debug_headers_non_dynamic_ignored() {
        AuthKeyInfo key = new AuthKeyInfo();
        key.setTargetName("Authorization");
        key.setAuthKey("stored-value");
        AuthInfo authInfo = new AuthInfo();
        authInfo.setScope(AuthInfo.ScopeEnum.SERVICE);
        authInfo.setDomain(AuthInfo.DomainEnum.HEADERS);
        authInfo.setAuthKeys(List.of(key));
        McpServiceEntity entity = new McpServiceEntity();
        entity.setId(SVC_ID);
        entity.setName("svc");
        entity.setAuthInfo(authInfo);

        Map<String, String> headerInfo = new HashMap<>();
        newManager().mergeDynamicDebugHeaders(entity,
            Map.of("Authorization", "Bearer tok-3"), headerInfo);
        Assertions.assertTrue(headerInfo.isEmpty());
    }
}
