package com.openjiuwen.studio.agent.common.customerheader;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * HeaderValue 单元测试 — 验证不可变 Header 值记录的核心功能
 *
 * 覆盖功能:
 * - customerCaptured(): 创建客户捕获来源的 HeaderValue
 * - platformGenerated(): 创建平台生成来源的 HeaderValue
 * - normalizedName(): 规范化为小写
 * - record 不可变性（equals/hashCode 行为）
 */
class HeaderValueTest {

    @Test
    void customerCaptured_factory() {
        // 验证: customerCaptured() 工厂方法正确构造 HeaderValue
        // 预期: normalizedName 为小写，value 原样保留，provenance=CUSTOMER_CAPTURED
        HeaderValue hv = HeaderValue.customerCaptured("Cust-UserId", "alice");
        assertEquals("cust-userid", hv.normalizedName());
        assertEquals("alice", hv.value());
        assertEquals(HeaderProvenance.CUSTOMER_CAPTURED, hv.provenance());
    }

    @Test
    void platformGenerated_factory() {
        // 验证: platformGenerated() 工厂方法正确构造 HeaderValue
        // 预期: normalizedName 为小写，value 原样保留，provenance=PLATFORM_GENERATED
        HeaderValue hv = HeaderValue.platformGenerated("X-Exec-Id", "abc123");
        assertEquals("x-exec-id", hv.normalizedName());
        assertEquals("abc123", hv.value());
        assertEquals(HeaderProvenance.PLATFORM_GENERATED, hv.provenance());
    }

    @Test
    void record_equality() {
        // 验证: record equals 方法 — 相同字段值的两个实例相等
        HeaderValue a = HeaderValue.customerCaptured("cust-userid", "alice");
        HeaderValue b = HeaderValue.customerCaptured("cust-userid", "alice");
        assertEquals(a, b);
    }

    @Test
    void record_inequality_differentValue() {
        // 验证: record equals 方法 — value 不同则不相等
        HeaderValue a = HeaderValue.customerCaptured("cust-userid", "alice");
        HeaderValue b = HeaderValue.customerCaptured("cust-userid", "bob");
        assertNotEquals(a, b);
    }

    @Test
    void record_inequality_differentProvenance() {
        // 验证: record equals 方法 — provenance 不同则不相等（即使 name/value 相同）
        HeaderValue a = HeaderValue.customerCaptured("cust-userid", "alice");
        HeaderValue b = HeaderValue.platformGenerated("cust-userid", "alice");
        assertNotEquals(a, b);
    }

    @Test
    void normalizedName_lowercased() {
        // 验证: normalizedName 自动规范化为小写（HTTP header 大小写不敏感）
        // 预期: X-FORWARDED-FOR → x-forwarded-for
        HeaderValue hv = HeaderValue.customerCaptured("X-FORWARDED-FOR", "1.2.3.4");
        assertEquals("x-forwarded-for", hv.normalizedName());
    }
}