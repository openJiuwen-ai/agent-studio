package com.openjiuwen.studio.agent.common.utils;

import com.openjiuwen.studio.agent.common.customerheader.CapturedCustomerHeaders;
import com.openjiuwen.studio.agent.common.customerheader.ExecutionIdentityContext;
import com.openjiuwen.studio.agent.common.customerheader.HeaderValue;
import com.openjiuwen.studio.agent.common.customerheader.PlatformPrincipal;
import com.openjiuwen.studio.agent.common.dto.simple.SimpleUser;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * RequestContextUtils 新增方法测试 — 验证请求上下文工具类的客户 Header 相关功能
 *
 * 覆盖功能:
 * - ExecutionIdentityContext: 执行身份上下文（平台 principal + effective userId）
 * - getEffectiveExecutionUserId: 获取执行用 effective userId
 * - customerHeaders: 捕获的客户 header 存储
 * - remove: 清理所有 ThreadLocal
 */
class RequestContextUtilsV19Test {

    @AfterEach
    void tearDown() {
        RequestContextUtils.remove();
    }

    // ── ExecutionIdentityContext ──

    @Test
    void setAndGetIdentityContext() {
        // 验证: setIdentityContext / getExecutionIdentityContext 正确存储和读取
        PlatformPrincipal principal = new PlatformPrincipal(
            "platform_user", "tok", "User", "p1", "d1", "D1"
        );
        ExecutionIdentityContext ctx = new ExecutionIdentityContext(principal, "effective_user");
        RequestContextUtils.setIdentityContext(ctx);

        ExecutionIdentityContext retrieved = RequestContextUtils.getExecutionIdentityContext();
        assertNotNull(retrieved);
        assertEquals("platform_user", retrieved.platformPrincipal().userId());
        assertEquals("effective_user", retrieved.effectiveUserId());
    }

    @Test
    void getExecutionIdentityContext_returnsNullWhenNotSet() {
        // 验证: 未设置时返回 null（安全防御）
        assertNull(RequestContextUtils.getExecutionIdentityContext());
    }

    // ── getEffectiveExecutionUserId ──

    @Test
    void getEffectiveExecutionUserId_returnsEffectiveWhenSet() {
        // 验证: getEffectiveExecutionUserId 返回 effectiveUserId（cust-userid 覆盖后的值）
        PlatformPrincipal principal = new PlatformPrincipal(
            "platform_user", "tok", "User", "p1", "d1", "D1"
        );
        ExecutionIdentityContext ctx = new ExecutionIdentityContext(principal, "cust_effective");
        RequestContextUtils.setIdentityContext(ctx);

        assertEquals("cust_effective", RequestContextUtils.getEffectiveExecutionUserId());
    }

    @Test
    void getEffectiveExecutionUserId_fallsBackToPlatformUserId() {
        // 验证: 未设置 identity context 时，回退到平台 userId（回退逻辑）
        RequestContextUtils.setContext("token", "project", "domain");
        SimpleUser user = new SimpleUser();
        user.setUserId("platform_user");
        user.setToken("token");
        user.setProjectId("project");
        user.setDomainId("domain");
        RequestContextUtils.setContext(user);

        assertEquals("platform_user", RequestContextUtils.getEffectiveExecutionUserId());
    }

    // ── getRequestUserId vs getEffectiveExecutionUserId ──

    @Test
    void getRequestUserId_returnsPlatformUserId_notEffective() {
        // 验证: getRequestUserId 返回平台 userId，不受 cust-userid 影响
        // 场景: platform_user 为平台值，cust_user_001 为 effective 值
        // 预期: getRequestUserId 返回 platform_user，getEffectiveExecutionUserId 返回 cust_user_001
        SimpleUser user = new SimpleUser();
        user.setUserId("platform_user");
        user.setToken("tok");
        user.setProjectId("p1");
        user.setDomainId("d1");
        RequestContextUtils.setContext(user);

        PlatformPrincipal principal = PlatformPrincipal.from(user);
        RequestContextUtils.setIdentityContext(
            new ExecutionIdentityContext(principal, "cust_user_001")
        );

        // getRequestUserId 返回平台 userId
        assertEquals("platform_user", RequestContextUtils.getRequestUserId());
        // getEffectiveExecutionUserId 返回 cust-userid
        assertEquals("cust_user_001", RequestContextUtils.getEffectiveExecutionUserId());
    }

    // ── CustomerHeaders ──

    @Test
    void setAndGetCustomerHeaders() {
        // 验证: setCustomerHeaders / getCustomerHeaders 正确存储和读取
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.from(Map.of(
            "cust-userid", HeaderValue.customerCaptured("cust-userid", "alice"),
            "cust-token", HeaderValue.customerCaptured("cust-token", "secret")
        ));
        RequestContextUtils.setCustomerHeaders(captured);

        CapturedCustomerHeaders retrieved = RequestContextUtils.getCustomerHeaders();
        assertNotNull(retrieved);
        assertEquals("alice", retrieved.get("cust-userid"));
        assertEquals("secret", retrieved.get("cust-token"));
    }

    @Test
    void getCustomerHeaders_returnsNullWhenNotSet() {
        // 验证: 未设置时返回 null（安全防御）
        assertNull(RequestContextUtils.getCustomerHeaders());
    }

    // ── remove cleans all ThreadLocals ──

    @Test
    void remove_cleansIdentityContext() {
        // 验证: remove 清理 ExecutionIdentityContext ThreadLocal
        PlatformPrincipal principal = new PlatformPrincipal(
            "u", "t", "n", "p", "d", "dn"
        );
        RequestContextUtils.setIdentityContext(
            new ExecutionIdentityContext(principal, "eff")
        );
        RequestContextUtils.remove();

        assertNull(RequestContextUtils.getExecutionIdentityContext());
    }

    @Test
    void remove_cleansCustomerHeaders() {
        // 验证: remove 清理 CustomerHeaders ThreadLocal
        RequestContextUtils.setCustomerHeaders(
            CapturedCustomerHeaders.from(Map.of(
                "cust-userid", HeaderValue.customerCaptured("cust-userid", "alice")
            ))
        );
        RequestContextUtils.remove();

        assertNull(RequestContextUtils.getCustomerHeaders());
    }

    @Test
    void remove_cleansAllThreadLocals() {
        // 验证: remove 清理所有 ThreadLocal（完整性）
        // 场景: 同时设置 IAM context / IdentityContext / CustomerHeaders
        // 预期: remove 后全部为 null/empty
        RequestContextUtils.setContext("token", "project", "domain");
        PlatformPrincipal principal = new PlatformPrincipal(
            "u", "t", "n", "p", "d", "dn"
        );
        RequestContextUtils.setIdentityContext(
            new ExecutionIdentityContext(principal, "eff")
        );
        RequestContextUtils.setCustomerHeaders(
            CapturedCustomerHeaders.from(Map.of(
                "cust-userid", HeaderValue.customerCaptured("cust-userid", "alice")
            ))
        );

        // 清理
        RequestContextUtils.remove();

        // 全部为 null/empty
        assertNull(RequestContextUtils.getExecutionIdentityContext());
        assertNull(RequestContextUtils.getCustomerHeaders());
        assertThrows(RuntimeException.class, RequestContextUtils::getRequestIamCtx);
    }
}