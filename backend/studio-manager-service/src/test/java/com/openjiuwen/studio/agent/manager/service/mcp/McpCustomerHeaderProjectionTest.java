/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp;

import com.openjiuwen.studio.agent.common.customerheader.CapturedCustomerHeaders;
import com.openjiuwen.studio.agent.common.customerheader.CustomerHeaderProfile;
import com.openjiuwen.studio.agent.common.customerheader.HeaderValue;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * {@link McpCustomerHeaderProjection} 单元测试 — 对齐 agent-runtime Python 7 用例。
 *
 * <p>覆盖：profile 启用引擎路（配置驱动 rename，仅自身 auth_keys，无 hard编码）、profile 关闭原样透传（不 rename）、
 * 无 profile 不重命名、无 cust- 不动、非 cust- 保留原值与大小写、null/空 map 不报错、大小写不敏感前缀匹配。
 */
class McpCustomerHeaderProjectionTest {

    @AfterEach
    void clearCtx() {
        // 清理 captured ThreadLocal，避免用例间泄漏
        RequestContextUtils.remove();
    }

    private CustomerHeaderProfile buildProfile(boolean enabled,
        Map<String, CustomerHeaderProfile.TargetConfig> targets) {
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        profile.setEnabled(enabled);
        profile.setActiveProfile("test");

        CustomerHeaderProfile.Profile p = new CustomerHeaderProfile.Profile();
        p.setEnvironment("simple");

        CustomerHeaderProfile.Capture capture = new CustomerHeaderProfile.Capture();
        capture.setCustomerAllow(List.of("cust-userid", "cust-token"));
        p.setCapture(capture);

        p.setTargets(targets);
        profile.setProfiles(Map.of("test", p));
        return profile;
    }

    private CustomerHeaderProfile buildEnabledProfile() {
        return buildProfileWithMappings(true);
    }

    private CustomerHeaderProfile buildDisabledProfileWithMappings() {
        return buildProfileWithMappings(false);
    }

    private CustomerHeaderProfile buildProfileWithMappings(boolean enabled) {
        CustomerHeaderProfile.Mapping m1 = new CustomerHeaderProfile.Mapping();
        m1.setFrom("cust-userid");
        m1.setTo("userid");
        CustomerHeaderProfile.Mapping m2 = new CustomerHeaderProfile.Mapping();
        m2.setFrom("cust-token");
        m2.setTo("token");
        CustomerHeaderProfile.TargetConfig target = new CustomerHeaderProfile.TargetConfig();
        target.setMappings(List.of(m1, m2));
        return buildProfile(enabled, Map.of("RUNTIME_MCP_CALL", target));
    }

    private Map<String, String> safeHeaders() {
        return new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
    }

    @Test
    void profileEnabled_stripsPrefixFromStaticAuthKeys() {
        Map<String, String> headers = safeHeaders();
        headers.put("cust-token", "mock-token");
        headers.put("cust-userid", "123456");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", buildEnabledProfile());

        assertEquals("mock-token", headers.get("token"));
        assertEquals("123456", headers.get("userid"));
        assertNull(headers.get("cust-token"));
        assertNull(headers.get("cust-userid"));
        assertEquals(2, headers.size());
    }

    @Test
    void profileEnabled_capturedIgnored_usesStaticOnly() {
        // MCP 调测不透传上游 captured，仅使用自身配置的 auth_keys
        Map<String, String> headers = safeHeaders();
        headers.put("cust-token", "static-tok");
        headers.put("cust-userid", "static-uid");

        // 设置上游 captured（应被忽略）
        Map<String, HeaderValue> cap = new LinkedHashMap<>();
        cap.put("cust-token", HeaderValue.customerCaptured("cust-token", "captured-tok"));
        RequestContextUtils.setCustomerHeaders(CapturedCustomerHeaders.from(cap));

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", buildEnabledProfile());

        // captured 被忽略，保留静态值（static-only）
        assertEquals("static-tok", headers.get("token"));
        assertEquals("static-uid", headers.get("userid"));
        assertNull(headers.get("cust-token"));
        assertNull(headers.get("cust-userid"));
    }

    @Test
    void profileDisabled_passthroughAsIs() {
        // profile 关闭：即使 RUNTIME_MCP_CALL mappings 存在，也不 rename——原样透传 cust-*（向后兼容）
        Map<String, String> headers = safeHeaders();
        headers.put("cust-token", "mock-token");
        headers.put("cust-userid", "123456");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc",
            buildDisabledProfileWithMappings());

        // cust-* 原样留存，未剥前缀、未生成 token/userid
        assertEquals("mock-token", headers.get("cust-token"));
        assertEquals("123456", headers.get("cust-userid"));
        assertNull(headers.get("token"));
        assertNull(headers.get("userid"));
        assertEquals(2, headers.size());
    }

    @Test
    void profileDisabled_noMappings_noRename() {
        // profile 关闭且无 RUNTIME_MCP_CALL mappings：无可剥配置，原样不动（cust-* 留存）
        Map<String, String> headers = safeHeaders();
        headers.put("cust-token", "mock-token");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", buildProfile(false, Map.of()));

        assertEquals("mock-token", headers.get("cust-token"));
        assertNull(headers.get("token"));
    }

    @Test
    void nullProfile_noRename() {
        // 无 Spring 上下文 / 无配置：无 mappings，不重命名（安全 no-op）
        Map<String, String> headers = safeHeaders();
        headers.put("cust-token", "mock-token");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", null);

        assertEquals("mock-token", headers.get("cust-token"));
        assertNull(headers.get("token"));
    }

    @Test
    void noCustHeaders_isNoOp() {
        Map<String, String> headers = safeHeaders();
        headers.put("Authorization", "Bearer x");
        headers.put("X-Custom", "v");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", buildEnabledProfile());

        assertEquals("Bearer x", headers.get("Authorization"));
        assertEquals("v", headers.get("X-Custom"));
        assertEquals(2, headers.size());
    }

    @Test
    void nonCustHeadersPreservedValueAndCase() {
        Map<String, String> headers = safeHeaders();
        headers.put("cust-token", "mock-token");
        headers.put("Authorization", "Bearer x");
        headers.put("Content-Length", "42");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", buildEnabledProfile());

        assertEquals("mock-token", headers.get("token"));
        assertEquals("Bearer x", headers.get("Authorization"));
        assertEquals("42", headers.get("Content-Length"));
        assertNull(headers.get("cust-token"));
    }

    @Test
    void nullOrEmptyHeaders_isNoOp() {
        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(null, "svc", buildEnabledProfile());
        Map<String, String> empty = safeHeaders();
        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(empty, "svc", buildEnabledProfile());
        assertTrue(empty.isEmpty());
    }

    @Test
    void caseInsensitiveCustPrefix() {
        Map<String, String> headers = safeHeaders();
        headers.put("CUST-TOKEN", "mock-token");
        headers.put("Cust-Userid", "123456");

        McpCustomerHeaderProjection.renameOutboundCustomerHeaders(headers, "svc", buildEnabledProfile());

        assertEquals("mock-token", headers.get("token"));
        assertEquals("123456", headers.get("userid"));
        assertNull(headers.get("CUST-TOKEN"));
        assertNull(headers.get("Cust-Userid"));
    }
}
