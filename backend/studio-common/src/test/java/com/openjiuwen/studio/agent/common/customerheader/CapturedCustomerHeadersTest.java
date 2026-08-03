package com.openjiuwen.studio.agent.common.customerheader;

import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

/**
 * CapturedCustomerHeaders 单元测试 — 验证客户 Header 捕获容器的核心功能
 *
 * 覆盖功能:
 * - capture(): 从 HTTP 请求按白名单捕获 cust-* header
 * - get(): 按名称获取 header 值（大小写不敏感）
 * - contains(): 检查是否包含指定 header
 * - asMap(): 返回不可变 Map（防篡改）
 * - 空值/null 参数处理
 */
class CapturedCustomerHeadersTest {

    @Test
    void capture_fromRequest() {
        // 验证: 从 HttpServletRequest 按白名单捕获 header
        // 预期: cust-userid/cust-token 被成功捕获并存储
        HttpServletRequest request = Mockito.mock(HttpServletRequest.class);
        when(request.getHeader("cust-userid")).thenReturn("user001");
        when(request.getHeader("cust-token")).thenReturn("tok123");

        String[] allowList = {"cust-userid", "cust-token"};
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.capture(allowList, request);

        assertEquals("user001", captured.get("cust-userid"));
        assertEquals("tok123", captured.get("cust-token"));
        assertFalse(captured.isEmpty());
    }

    @Test
    void capture_missingHeaderSkipped() {
        // 验证: 缺失的 header（返回 null）被跳过，不存入容器
        // 预期: 只有 cust-userid 被捕获，cust-token 为 null
        HttpServletRequest request = Mockito.mock(HttpServletRequest.class);
        when(request.getHeader("cust-userid")).thenReturn("user001");
        when(request.getHeader("cust-token")).thenReturn(null);

        String[] allowList = {"cust-userid", "cust-token"};
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.capture(allowList, request);

        assertEquals("user001", captured.get("cust-userid"));
        assertNull(captured.get("cust-token"));
    }

    @Test
    void capture_emptyHeaderSkipped() {
        // 验证: 空字符串 header 被跳过（不存入容器）
        // 预期: cust-userid 为空字符串被跳过，cust-token 正常捕获
        HttpServletRequest request = Mockito.mock(HttpServletRequest.class);
        when(request.getHeader("cust-userid")).thenReturn("");
        when(request.getHeader("cust-token")).thenReturn("tok");

        String[] allowList = {"cust-userid", "cust-token"};
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.capture(allowList, request);

        assertNull(captured.get("cust-userid"));
        assertEquals("tok", captured.get("cust-token"));
    }

    @Test
    void capture_nullAllowListReturnsEmpty() {
        // 验证: allowList 为 null 时返回空容器（安全防御）
        // 预期: 空容器，无任何 header
        HttpServletRequest request = Mockito.mock(HttpServletRequest.class);
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.capture(null, request);
        assertTrue(captured.isEmpty());
    }

    @Test
    void capture_nullRequestReturnsEmpty() {
        // 验证: request 为 null 时返回空容器（安全防御）
        // 预期: 空容器，无任何 header
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.capture(
            new String[]{"cust-userid"}, null);
        assertTrue(captured.isEmpty());
    }

    @Test
    void empty_returnsEmptyInstance() {
        // 验证: empty() 工厂方法返回空容器实例
        // 预期: isEmpty()=true，get/contains 返回 null/false
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.empty();
        assertTrue(captured.isEmpty());
        assertNull(captured.get("anything"));
        assertFalse(captured.contains("anything"));
    }

    @Test
    void from_constructsFromMap() {
        // 验证: from() 工厂方法从已有 Map 构造容器
        // 预期: Map 中的 header 被正确存储并可查询
        Map<String, HeaderValue> map = Map.of(
            "cust-userid", HeaderValue.customerCaptured("cust-userid", "alice"),
            "cust-token", HeaderValue.customerCaptured("cust-token", "secret")
        );
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.from(map);

        assertEquals("alice", captured.get("cust-userid"));
        assertEquals("secret", captured.get("cust-token"));
    }

    @Test
    void from_nullMapReturnsEmpty() {
        // 验证: from(null) 返回空容器（安全防御）
        // 预期: 空容器，无任何 header
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.from(null);
        assertTrue(captured.isEmpty());
    }

    @Test
    void get_caseInsensitive() {
        // 验证: get() 方法大小写不敏感（统一规范化为小写）
        // 预期: Cust-UserId/CUST-USERID/cust-userid 都能查到同一值
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.from(
            Map.of("cust-userid", HeaderValue.customerCaptured("cust-userid", "alice"))
        );

        assertEquals("alice", captured.get("Cust-UserId"));
        assertEquals("alice", captured.get("CUST-USERID"));
        assertEquals("alice", captured.get("cust-userid"));
    }

    @Test
    void get_nullReturnsNull() {
        // 验证: get(null) 返回 null（安全防御）
        // 预期: null 输入 → null 输出
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.empty();
        assertNull(captured.get(null));
    }

    @Test
    void contains_returnsTrueForExisting() {
        // 验证: contains() 方法检查 header 是否存在（大小写不敏感）
        // 预期: 存在的 header 返回 true，不存在的返回 false，null 返回 false
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.from(
            Map.of("cust-userid", HeaderValue.customerCaptured("cust-userid", "alice"))
        );
        assertTrue(captured.contains("cust-userid"));
        assertTrue(captured.contains("Cust-UserId"));
        assertFalse(captured.contains("cust-token"));
        assertFalse(captured.contains(null));
    }

    @Test
    void asMap_returnsUnmodifiableMap() {
        // 验证: asMap() 返回不可变 Map（防篡改）
        // 预期: 尝试 put 操作抛出 UnsupportedOperationException
        CapturedCustomerHeaders captured = CapturedCustomerHeaders.from(
            Map.of("cust-userid", HeaderValue.customerCaptured("cust-userid", "alice"))
        );
        Map<String, HeaderValue> map = captured.asMap();
        assertThrows(UnsupportedOperationException.class,
            () -> map.put("new-key", HeaderValue.customerCaptured("new", "val")));
    }
}