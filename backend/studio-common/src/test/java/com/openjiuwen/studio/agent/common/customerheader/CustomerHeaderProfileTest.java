package com.openjiuwen.studio.agent.common.customerheader;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * CustomerHeaderProfile 单元测试 — 验证 Profile 配置 Bean 的核心功能
 *
 * 覆盖功能:
 * - enabled/isEnabledInSimpleMode:  门控逻辑（simple 模式判断）
 * - getCaptureAllowList: 捕获白名单
 * - getBoundaryPassthrough: boundary 透传白名单
 * - getTargetMappings: Target mappings 配置
 * - getIrAuthKeysForwardList: IR_AUTH_KEYS forward-list
 * - Identity 配置解析
 */
class CustomerHeaderProfileTest {

    private CustomerHeaderProfile buildEnabledProfile() {
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        profile.setEnabled(true);
        profile.setEnvironment("simple");

        CustomerHeaderProfile.Identity identity = new CustomerHeaderProfile.Identity();
        identity.setUserIdHeader("cust-userid");
        identity.setTokenHeader("cust-token");
        identity.setFallback("iam");
        profile.setIdentity(identity);

        CustomerHeaderProfile.Capture capture = new CustomerHeaderProfile.Capture();
        capture.setCustomerAllow(List.of("cust-userid", "cust-token"));
        profile.setCapture(capture);

        CustomerHeaderProfile.Boundary boundary = new CustomerHeaderProfile.Boundary();
        CustomerHeaderProfile.BoundaryEntry rtEntry = new CustomerHeaderProfile.BoundaryEntry();
        rtEntry.setCustomerPassthrough(List.of("cust-userid", "cust-token"));
        boundary.setAgentRuntimeInbound(rtEntry);
        CustomerHeaderProfile.BoundaryEntry builderEntry = new CustomerHeaderProfile.BoundaryEntry();
        builderEntry.setCustomerPassthrough(List.of("cust-userid", "cust-token"));
        boundary.setAgentBuilderInbound(builderEntry);
        profile.setBoundary(boundary);

        CustomerHeaderProfile.Mapping m1 = new CustomerHeaderProfile.Mapping();
        m1.setFrom("cust-userid");
        m1.setTo("userid");
        CustomerHeaderProfile.Mapping m2 = new CustomerHeaderProfile.Mapping();
        m2.setFrom("cust-token");
        m2.setTo("token");

        CustomerHeaderProfile.TargetConfig llmTarget = new CustomerHeaderProfile.TargetConfig();
        llmTarget.setMappings(List.of(m1, m2));

        CustomerHeaderProfile.TargetConfig lakeTarget = new CustomerHeaderProfile.TargetConfig();
        lakeTarget.setMappings(List.of(m1, m2));

        CustomerHeaderProfile.TargetConfig irTarget = new CustomerHeaderProfile.TargetConfig();
        irTarget.setForwardList(List.of("cust-userid", "cust-token", "x-auth-token"));

        profile.setTargets(Map.of(
            "RUNTIME_LLM_CHAT", llmTarget,
            "LAKESEARCH", lakeTarget,
            "IR_AUTH_KEYS", irTarget
        ));

        return profile;
    }

    // ── enabled / simple mode 门控 ──

    @Test
    void isEnabled_returnsTrue() {
        // 验证: isEnabled 返回 true（Profile 已启用）
        CustomerHeaderProfile profile = buildEnabledProfile();
        assertTrue(profile.isEnabled());
    }

    @Test
    void isEnabled_returnsFalseByDefault() {
        // 验证: 默认构造函数创建 disabled Profile
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        assertFalse(profile.isEnabled());
    }

    @Test
    void isEnabledInSimpleMode_returnsTrue() {
        // 验证:  门控 — enabled=true 且 environment=simple 时返回 true
        CustomerHeaderProfile profile = buildEnabledProfile();
        assertTrue(profile.isEnabledInSimpleMode());
    }

    @Test
    void isEnabledInSimpleMode_returnsFalseWhenDisabled() {
        // 验证:  门控 — enabled=false 时返回 false（即使 environment=simple）
        CustomerHeaderProfile profile = buildEnabledProfile();
        profile.setEnabled(false);
        assertFalse(profile.isEnabledInSimpleMode());
    }

    @Test
    void isEnabledInSimpleMode_returnsFalseForNonSimpleEnv() {
        // 验证:  门控 — environment!=simple 时返回 false（即使 enabled=true）
        CustomerHeaderProfile profile = buildEnabledProfile();
        profile.setEnvironment("production");
        assertFalse(profile.isEnabledInSimpleMode());
    }

    // ── capture 白名单 ──

    @Test
    void getCaptureAllowList_returnsList() {
        // 验证: 获取捕获白名单
        CustomerHeaderProfile profile = buildEnabledProfile();
        String[] allowList = profile.getCaptureAllowList();
        assertArrayEquals(new String[]{"cust-userid", "cust-token"}, allowList);
    }

    @Test
    void getCaptureAllowList_returnsEmptyWhenDisabled() {
        // 验证: disabled 时返回空数组
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        assertArrayEquals(new String[0], profile.getCaptureAllowList());
    }

    // ── boundary passthrough ──

    @Test
    void getBoundaryPassthrough_runtime() {
        // 验证: 获取 AGENT_RUNTIME_INBOUND 的 passthrough 白名单
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<String> passthrough = profile.getBoundaryPassthrough(InternalTarget.AGENT_RUNTIME_INBOUND);
        assertEquals(List.of("cust-userid", "cust-token"), passthrough);
    }

    @Test
    void getBoundaryPassthrough_builder() {
        // 验证: 获取 AGENT_BUILDER_INBOUND 的 passthrough 白名单
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<String> passthrough = profile.getBoundaryPassthrough(InternalTarget.AGENT_BUILDER_INBOUND);
        assertEquals(List.of("cust-userid", "cust-token"), passthrough);
    }

    @Test
    void getBoundaryPassthrough_nonBoundaryTarget() {
        // 验证: 非 boundary Target 返回空列表
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<String> passthrough = profile.getBoundaryPassthrough(InternalTarget.LAKESEARCH);
        assertTrue(passthrough.isEmpty());
    }

    @Test
    void getBoundaryPassthrough_returnsEmptyWhenDisabled() {
        // 验证: disabled 时返回空列表
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        assertTrue(profile.getBoundaryPassthrough(InternalTarget.AGENT_RUNTIME_INBOUND).isEmpty());
    }

    // ── target mappings ──

    @Test
    void getTargetMappings_runtimeLlmChat() {
        // 验证: 获取 RUNTIME_LLM_CHAT 的 mappings（cust-userid→userid, cust-token→token）
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<CustomerHeaderProfile.Mapping> mappings = profile.getTargetMappings(InternalTarget.RUNTIME_LLM_CHAT);
        assertEquals(2, mappings.size());
        assertEquals("cust-userid", mappings.get(0).getFrom());
        assertEquals("userid", mappings.get(0).getTo());
        assertEquals("cust-token", mappings.get(1).getFrom());
        assertEquals("token", mappings.get(1).getTo());
    }

    @Test
    void getTargetMappings_lakesearch() {
        // 验证: 获取 LAKESEARCH 的 mappings
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<CustomerHeaderProfile.Mapping> mappings = profile.getTargetMappings(InternalTarget.LAKESEARCH);
        assertEquals(2, mappings.size());
    }

    @Test
    void getTargetMappings_unknownTargetReturnsEmpty() {
        // 验证: 未配置的 Target 返回空列表
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<CustomerHeaderProfile.Mapping> mappings = profile.getTargetMappings(InternalTarget.MEMORY_LLM);
        assertTrue(mappings.isEmpty());
    }

    @Test
    void getTargetMappings_returnsEmptyWhenDisabled() {
        // 验证: disabled 时返回空列表
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        assertTrue(profile.getTargetMappings(InternalTarget.RUNTIME_LLM_CHAT).isEmpty());
    }

    // ── IR auth_keys forward-list ──

    @Test
    void getIrAuthKeysForwardList_returnsList() {
        // 验证: 获取 IR_AUTH_KEYS 的 forward-list
        CustomerHeaderProfile profile = buildEnabledProfile();
        List<String> fl = profile.getIrAuthKeysForwardList();
        assertEquals(List.of("cust-userid", "cust-token", "x-auth-token"), fl);
    }

    @Test
    void getIrAuthKeysForwardList_returnsEmptyWhenDisabled() {
        // 验证: disabled 时返回空列表
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        assertTrue(profile.getIrAuthKeysForwardList().isEmpty());
    }

    // ── identity 配置 ──

    @Test
    void identity_gettersWork() {
        // 验证: Identity 配置的 getter 方法正确返回 userIdHeader/tokenHeader/fallback
        CustomerHeaderProfile profile = buildEnabledProfile();
        CustomerHeaderProfile.Identity identity = profile.getIdentity();
        assertNotNull(identity);
        assertEquals("cust-userid", identity.getUserIdHeader());
        assertEquals("cust-token", identity.getTokenHeader());
        assertEquals("iam", identity.getFallback());
    }
}