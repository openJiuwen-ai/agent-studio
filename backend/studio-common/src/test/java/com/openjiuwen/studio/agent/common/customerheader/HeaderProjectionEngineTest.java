package com.openjiuwen.studio.agent.common.customerheader;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * HeaderProjectionEngine 单元测试 — 验证 Header 投影引擎的核心原语
 *
 * 覆盖功能:
 * - project: rename 原语，将 cust-* header 按 Target mappings 改名
 * - passthrough: boundary 白名单原样转发
 * - forwardList: IR auth_keys 前向声明
 * - 黑名单防护: 禁止覆盖 authorization/host/x-forwarded-* 等保留 header
 */
class HeaderProjectionEngineTest {

    private CustomerHeaderProfile buildProfile(Map<String, CustomerHeaderProfile.TargetConfig> targets,
                                               List<String> passthrough) {
        CustomerHeaderProfile profile = new CustomerHeaderProfile();
        profile.setEnabled(true);
        profile.setEnvironment("simple");

        CustomerHeaderProfile.Capture capture = new CustomerHeaderProfile.Capture();
        capture.setCustomerAllow(List.of("cust-userid", "cust-token"));
        profile.setCapture(capture);

        CustomerHeaderProfile.Boundary boundary = new CustomerHeaderProfile.Boundary();
        CustomerHeaderProfile.BoundaryEntry rtEntry = new CustomerHeaderProfile.BoundaryEntry();
        rtEntry.setCustomerPassthrough(passthrough);
        boundary.setAgentRuntimeInbound(rtEntry);
        CustomerHeaderProfile.BoundaryEntry builderEntry = new CustomerHeaderProfile.BoundaryEntry();
        builderEntry.setCustomerPassthrough(passthrough);
        boundary.setAgentBuilderInbound(builderEntry);
        profile.setBoundary(boundary);

        profile.setTargets(targets);

        return profile;
    }

    private CustomerHeaderProfile buildDefaultProfile() {
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

        return buildProfile(
            Map.of(
                "RUNTIME_LLM_CHAT", llmTarget,
                "LAKESEARCH", lakeTarget,
                "IR_AUTH_KEYS", irTarget
            ),
            List.of("cust-userid", "cust-token")
        );
    }

    private CapturedCustomerHeaders makeCaptured(String userId, String token) {
        Map<String, HeaderValue> map = new java.util.LinkedHashMap<>();
        if (userId != null) {
            map.put("cust-userid", HeaderValue.customerCaptured("cust-userid", userId));
        }
        if (token != null) {
            map.put("cust-token", HeaderValue.customerCaptured("cust-token", token));
        }
        return CapturedCustomerHeaders.from(map);
    }

    // ── project (rename) 原语测试 ──

    @Test
    void project_basicRename() {
        // 验证: 基本 rename 功能 — cust-userid→userid, cust-token→token
        // 预期: 输出包含 rename 后的 userid/token，原始 cust-* 不出现
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, String> result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured);

        assertEquals("alice", result.get("userid"));
        assertEquals("secret", result.get("token"));
        assertNull(result.get("cust-userid"));
        assertNull(result.get("cust-token"));
    }

    @Test
    void project_withConfigHeaders() {
        // 验证: configHeaders 不参与 rename，直接透传到输出
        // 预期: rename 后的 userid/token + configHeaders 的 x-model-id/x-api-version 都出现在结果中
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, String> config = Map.of("x-model-id", "gpt-4", "x-api-version", "2024-01");
        Map<String, String> result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured, config);

        assertEquals("alice", result.get("userid"));
        assertEquals("secret", result.get("token"));
        assertEquals("gpt-4", result.get("x-model-id"));
        assertEquals("2024-01", result.get("x-api-version"));
    }

    @Test
    void project_blacklistBlocksReservedHeaders() {
        // 验证:  黑名单防护 — mappings 目标名为 authorization/host 时拒绝生成
        // 预期: 黑名单中的 header 不出现在输出中，即使 profile 配置了 rename
        CustomerHeaderProfile.Mapping m1 = new CustomerHeaderProfile.Mapping();
        m1.setFrom("cust-userid");
        m1.setTo("authorization");
        CustomerHeaderProfile.Mapping m2 = new CustomerHeaderProfile.Mapping();
        m2.setFrom("cust-token");
        m2.setTo("host");

        CustomerHeaderProfile.TargetConfig target = new CustomerHeaderProfile.TargetConfig();
        target.setMappings(List.of(m1, m2));

        CustomerHeaderProfile profile = buildProfile(
            Map.of("RUNTIME_LLM_CHAT", target),
            List.of("cust-userid", "cust-token")
        );
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, String> result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured);

        assertNull(result.get("authorization"));
        assertNull(result.get("host"));
    }

    @Test
    void project_configBlacklistHeadersAlsoBlocked() {
        // 验证: configHeaders 中的黑名单 header 也不允许通过
        // 预期: authorization/host 被拦截，x-safe 正常透传
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, String> config = Map.of("authorization", "Bearer evil", "host", "evil.com", "x-safe", "ok");
        Map<String, String> result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured, config);

        assertNull(result.get("authorization"));
        assertNull(result.get("host"));
        assertEquals("ok", result.get("x-safe"));
    }

    @Test
    void project_noMappingsReturnsConfigOnly() {
        // 验证: Target 未配置 mappings 时，只返回 configHeaders
        // 预期: BUILDER_LLM_CHAT 无 mappings，输出只有 configHeaders
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, String> config = Map.of("x-model-id", "gpt-4");
        Map<String, String> result = engine.project(InternalTarget.BUILDER_LLM_CHAT, captured, config);

        assertEquals(Map.of("x-model-id", "gpt-4"), result);
    }

    @Test
    void project_emptyCapturedReturnsConfigOnly() {
        // 验证: captured 为空时，只返回 configHeaders（无 rename 输入）
        // 预期: 空 captured + 无 configHeaders → 空输出
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);

        Map<String, String> result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, CapturedCustomerHeaders.empty());

        assertTrue(result.isEmpty());
    }

    @Test
    void project_caseInsensitiveMapping() {
        // 验证: mapping 的 from/to 大小写不敏感（统一规范化为小写）
        // 预期: from=Cust-UserId, to=UserId → 仍能匹配 cust-userid 并输出 userid
        CustomerHeaderProfile.Mapping m = new CustomerHeaderProfile.Mapping();
        m.setFrom("Cust-UserId");
        m.setTo("UserId");

        CustomerHeaderProfile.TargetConfig target = new CustomerHeaderProfile.TargetConfig();
        target.setMappings(List.of(m));

        CustomerHeaderProfile profile = buildProfile(
            Map.of("RUNTIME_LLM_CHAT", target),
            List.of("cust-userid")
        );
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", null);

        Map<String, String> result = engine.project(InternalTarget.RUNTIME_LLM_CHAT, captured);

        assertEquals("alice", result.get("userid"));
    }

    // ── passthrough (boundary 转发) 原语测试 ──

    @Test
    void passthrough_boundaryWhitelist() {
        // 验证:  boundary passthrough — 按白名单原样转发 cust-* header
        // 预期: AGENT_RUNTIME_INBOUND 白名单中的 cust-userid/cust-token 原样出现在输出中
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, HeaderValue> result = engine.passthrough(InternalTarget.AGENT_RUNTIME_INBOUND, captured);

        assertEquals(2, result.size());
        assertEquals("alice", result.get("cust-userid").value());
        assertEquals("secret", result.get("cust-token").value());
    }

    @Test
    void passthrough_emptyCapturedReturnsEmpty() {
        // 验证: captured 为空时，passthrough 返回空 Map
        // 预期: 无捕获 header → 无 passthrough 输出
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);

        Map<String, HeaderValue> result = engine.passthrough(
            InternalTarget.AGENT_RUNTIME_INBOUND, CapturedCustomerHeaders.empty());

        assertTrue(result.isEmpty());
    }

    @Test
    void passthrough_nonBoundaryTargetReturnsEmpty() {
        // 验证: 非 boundary Target（如 LAKESEARCH）调用 passthrough 返回空
        // 预期: passthrough 只对 AGENT_RUNTIME_INBOUND / AGENT_BUILDER_INBOUND 有效
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);
        CapturedCustomerHeaders captured = makeCaptured("alice", "secret");

        Map<String, HeaderValue> result = engine.passthrough(InternalTarget.LAKESEARCH, captured);

        assertTrue(result.isEmpty());
    }

    // ── forwardList (IR auth_keys 声明) 原语测试 ──

    @Test
    void forwardList_irAuthKeys() {
        // 验证:  IR_AUTH_KEYS forward-list — 返回 Profile 配置的 forward-list
        // 预期: 返回 [cust-userid, cust-token, x-auth-token]
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);

        List<String> result = engine.forwardList(InternalTarget.IR_AUTH_KEYS);

        assertEquals(List.of("cust-userid", "cust-token", "x-auth-token"), result);
    }

    @Test
    void forwardList_nonIrTargetReturnsEmpty() {
        // 验证: 非 IR_AUTH_KEYS Target 调用 forwardList 返回空
        // 预期: RUNTIME_LLM_CHAT 不是 IR target → 空列表
        CustomerHeaderProfile profile = buildDefaultProfile();
        HeaderProjectionEngine engine = new HeaderProjectionEngine(profile);

        List<String> result = engine.forwardList(InternalTarget.RUNTIME_LLM_CHAT);

        assertTrue(result.isEmpty());
    }

    // ── 黑名单内容验证 ──

    @Test
    void reservedBlacklist_containsExpectedHeaders() {
        // 验证:  黑名单包含所有保留 header（防注入攻击）
        // 预期: authorization/host/x-forwarded-* 等都在黑名单中
        var blacklist = HeaderProjectionEngine.getReservedBlacklist();
        assertTrue(blacklist.contains("authorization"));
        assertTrue(blacklist.contains("host"));
        assertTrue(blacklist.contains("x-forwarded-for"));
        assertTrue(blacklist.contains("x-forwarded-host"));
        assertTrue(blacklist.contains("x-real-ip"));
    }

    @Test
    void reservedBlacklist_doesNotContainUserid() {
        // 验证: userid/token 不在黑名单中（它们是合法的 rename 目标）
        // 预期: userid/token 可被正常生成
        var blacklist = HeaderProjectionEngine.getReservedBlacklist();
        assertFalse(blacklist.contains("userid"));
        assertFalse(blacklist.contains("token"));
    }
}