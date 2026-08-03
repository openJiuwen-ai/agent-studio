package com.openjiuwen.studio.agent.common.customerheader;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * InternalRequestHeaderFactory 单元测试 — 验证内部请求 Header 构建的核心功能
 *
 * 覆盖功能:
 * - build(): 构建 manager→runtime / manager→agent_builder 的出站 header
 * - customer-passthrough 与平台生成 header 的合并逻辑
 * - 平台生成 header 覆盖客户 header（防注入）
 */
class InternalRequestHeaderFactoryTest {

    private CustomerHeaderProfile buildProfile(List<String> passthrough) {
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        profile.setEnabled(true);
        profile.setEnvironment("simple");

        CustomerHeaderProfile.Boundary boundary = new CustomerHeaderProfile.Boundary();
        CustomerHeaderProfile.BoundaryEntry rtEntry = new CustomerHeaderProfile.BoundaryEntry();
        rtEntry.setCustomerPassthrough(passthrough);
        boundary.setAgentRuntimeInbound(rtEntry);
        CustomerHeaderProfile.BoundaryEntry builderEntry = new CustomerHeaderProfile.BoundaryEntry();
        builderEntry.setCustomerPassthrough(passthrough);
        boundary.setAgentBuilderInbound(builderEntry);
        profile.setBoundary(boundary);

        profile.setTargets(Map.of());

        return profile;
    }

    private CapturedCustomerHeaders makeCaptured() {
        return CapturedCustomerHeaders.from(Map.of(
            "cust-userid", HeaderValue.customerCaptured("cust-userid", "test_user"),
            "cust-token", HeaderValue.customerCaptured("cust-token", "test_token")
        ));
    }

    @Test
    void build_includesPassthroughAndPlatformHeaders() {
        // 验证: build() 正确合并 customer-passthrough 和平台生成 header
        // 预期: 输出同时包含客户 header（passthrough）和平台 header（X-Auth-Token/X-Language）
        CustomerHeaderProfile profile = buildProfile(List.of("cust-userid", "cust-token"));
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        InternalRequestHeaderFactory factory = new InternalRequestHeaderFactory(engine);

        Map<String, String> generated = Map.of(
            "X-Auth-Token", "platform-token-abc",
            "X-Language", "zh_CN"
        );

        Map<String, String> result = factory.build(
            InternalTarget.AGENT_RUNTIME_INBOUND, makeCaptured(), generated);

        // 客户 header passthrough
        assertEquals("test_user", result.get("cust-userid"));
        assertEquals("test_token", result.get("cust-token"));
        // 平台 header
        assertEquals("platform-token-abc", result.get("x-auth-token"));
        assertEquals("zh_CN", result.get("x-language"));
    }

    @Test
    void build_platformHeadersOverrideCustomer() {
        // 验证: 平台生成 header 覆盖客户 header（防注入攻击）
        // 场景: 平台生成的 header 与客户 header 同名时，平台值优先
        CustomerHeaderProfile profile = buildProfile(List.of("cust-userid"));
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        InternalRequestHeaderFactory factory = new InternalRequestHeaderFactory(engine);

        Map<String, String> generated = Map.of("cust-userid", "platform-override-value");

        Map<String, String> result = factory.build(
            InternalTarget.AGENT_RUNTIME_INBOUND, makeCaptured(), generated);

        // 平台生成值覆盖客户值
        assertEquals("platform-override-value", result.get("cust-userid"));
    }

    @Test
    void build_emptyCapturedReturnsGeneratedOnly() {
        // 验证: captured 为空时，只返回平台生成 header
        CustomerHeaderProfile profile = buildProfile(List.of("cust-userid", "cust-token"));
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        InternalRequestHeaderFactory factory = new InternalRequestHeaderFactory(engine);

        Map<String, String> generated = Map.of("X-Auth-Token", "tok");
        Map<String, String> result = factory.build(
            InternalTarget.AGENT_RUNTIME_INBOUND, CapturedCustomerHeaders.empty(), generated);

        assertEquals("tok", result.get("x-auth-token"));
        assertNull(result.get("cust-userid"));
    }

    @Test
    void build_nullGeneratedReturnsPassthroughOnly() {
        // 验证: generated 为 null 时，只返回 customer-passthrough
        CustomerHeaderProfile profile = buildProfile(List.of("cust-userid", "cust-token"));
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        InternalRequestHeaderFactory factory = new InternalRequestHeaderFactory(engine);

        Map<String, String> result = factory.build(
            InternalTarget.AGENT_RUNTIME_INBOUND, makeCaptured(), null);

        assertEquals("test_user", result.get("cust-userid"));
        assertEquals("test_token", result.get("cust-token"));
        assertEquals(2, result.size());
    }

    @Test
    void build_emptyPassthroughListReturnsGeneratedOnly() {
        // 验证: passthrough 白名单为空时，只返回平台生成 header
        CustomerHeaderProfile profile = buildProfile(List.of());
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        InternalRequestHeaderFactory factory = new InternalRequestHeaderFactory(engine);

        Map<String, String> generated = Map.of("X-Auth-Token", "tok");
        Map<String, String> result = factory.build(
            InternalTarget.AGENT_RUNTIME_INBOUND, makeCaptured(), generated);

        assertEquals("tok", result.get("x-auth-token"));
        assertNull(result.get("cust-userid"));
    }
}