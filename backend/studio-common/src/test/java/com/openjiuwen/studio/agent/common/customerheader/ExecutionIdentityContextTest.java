package com.openjiuwen.studio.agent.common.customerheader;

import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * ExecutionIdentityContext / PlatformPrincipal 单元测试 — 验证执行身份上下文的核心功能
 *
 * 覆盖功能:
 * - ExecutionIdentityContext: 携带平台 principal 和 effective userId（cust-userid 覆盖后的值）
 * - PlatformPrincipal: 平台身份记录（不可变），与 SimpleUser 互转
 * - 设计原则: platformPrincipal.userId 保持平台值，effectiveUserId 可为 cust-userid
 */
class ExecutionIdentityContextTest {

    @Test
    void record_construction() {
        // 验证: record 构造方法正确存储 platformPrincipal 和 effectiveUserId
        PlatformPrincipal principal = new PlatformPrincipal(
            "platform_user", "platform_token", "TestUser", "proj-1", "dom-1", "Domain1"
        );
        ExecutionIdentityContext ctx = new ExecutionIdentityContext(principal, "effective_user");

        assertEquals("platform_user", ctx.platformPrincipal().userId());
        assertEquals("effective_user", ctx.effectiveUserId());
    }

    @Test
    void effectiveUserId_canDifferFromPrincipal() {
        // 验证: effectiveUserId 可以与 platformPrincipal.userId 不同（核心特性）
        // 场景: cust-userid 覆盖了 effective userId，但平台 principal 保持不变
        PlatformPrincipal principal = new PlatformPrincipal(
            "platform_user", "tok", "User", "p1", "d1", "D1"
        );
        ExecutionIdentityContext ctx = new ExecutionIdentityContext(principal, "cust_user_001");

        assertEquals("platform_user", ctx.platformPrincipal().userId());
        assertEquals("cust_user_001", ctx.effectiveUserId());
    }

    @Test
    void platformPrincipal_fromSimpleUser() {
        // 验证: PlatformPrincipal.from 从 SimpleUser 构造（防御性副本）
        // 预期: 字段值正确复制
        SimpleUser user = SimpleUser.builder()
            .userId("user1")
            .token("tok1")
            .userName("TestUser")
            .projectId("proj-1")
            .domainId("dom-1")
            .domainName("Domain1")
            .build();

        PlatformPrincipal principal = PlatformPrincipal.from(user);

        assertEquals("user1", principal.userId());
        assertEquals("tok1", principal.token());
        assertEquals("TestUser", principal.userName());
        assertEquals("proj-1", principal.projectId());
    }

    @Test
    void platformPrincipal_toSimpleUserCopy() {
        // 验证: toSimpleUserCopy 生成 SimpleUser 防御性副本
        // 预期: 字段值正确复制，domain 不为 null 时使用原值
        PlatformPrincipal principal = new PlatformPrincipal(
            "user1", "tok1", "TestUser", "proj-1", "dom-1", "Domain1"
        );

        SimpleUser copy = principal.toSimpleUserCopy();

        assertEquals("user1", copy.getUserId());
        assertEquals("tok1", copy.getToken());
        assertEquals("TestUser", copy.getUserName());
        assertEquals("proj-1", copy.getProjectId());
        assertEquals("dom-1", copy.getDomainId());
        assertEquals("Domain1", copy.getDomainName());
    }

    @Test
    void platformPrincipal_toSimpleUserCopy_nullDomainDefaults() {
        // 验证: toSimpleUserCopy 处理 null domain（默认值为 "0"）
        // 预期: domainId/domainName 为 null 时使用 "0" 作为默认值
        PlatformPrincipal principal = new PlatformPrincipal(
            "user1", "tok1", "TestUser", "proj-1", null, null
        );

        SimpleUser copy = principal.toSimpleUserCopy();

        assertEquals("0", copy.getDomainId());
        assertEquals("0", copy.getDomainName());
    }

    @Test
    void record_equality() {
        // 验证: record equals 方法 — 相同字段值的两个实例相等
        PlatformPrincipal p = new PlatformPrincipal("u", "t", "n", "p", "d", "dn");
        ExecutionIdentityContext a = new ExecutionIdentityContext(p, "eff");
        ExecutionIdentityContext b = new ExecutionIdentityContext(p, "eff");
        assertEquals(a, b);
    }
}