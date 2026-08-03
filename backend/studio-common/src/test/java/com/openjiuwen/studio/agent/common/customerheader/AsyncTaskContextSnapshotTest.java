/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.customerheader;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * AsyncTaskContextSnapshot 序列化往返测试（单信封）
 *
 * <p>验证 record + {@code Map<String,HeaderValue>} 经 Jackson 序列化/反序列化后值不丢
 * （provenance 在 Redis 往返不丢）。异步恢复依赖此契约，破坏即异步执行失败。
 */
class AsyncTaskContextSnapshotTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void roundTrip_preservesPlatformTokenEffectiveUserIdAndCustomerHeaders() throws Exception {
        Map<String, HeaderValue> customerHeaders = new LinkedHashMap<>();
        customerHeaders.put("cust-userid", HeaderValue.customerCaptured("cust-userid", "customer-123"));
        customerHeaders.put("cust-token", HeaderValue.customerCaptured("cust-token", "secret-token"));

        AsyncTaskContextSnapshot original = new AsyncTaskContextSnapshot(
            "v1",
            new AsyncIdentitySnapshot("platform-token-abc", "customer-123"),
            new AsyncExecutionSnapshot(customerHeaders));

        String json = mapper.writeValueAsString(original);
        AsyncTaskContextSnapshot restored = mapper.readValue(json, AsyncTaskContextSnapshot.class);

        assertEquals("v1", restored.schemaVersion());
        assertNotNull(restored.identity());
        assertEquals("platform-token-abc", restored.identity().platformToken());
        assertEquals("customer-123", restored.identity().effectiveUserId());
        assertNotNull(restored.execution());
        assertNotNull(restored.execution().customerHeaders());
        assertEquals(2, restored.execution().customerHeaders().size());
        assertEquals("customer-123", restored.execution().customerHeaders().get("cust-userid").value());
        assertEquals(HeaderProvenance.CUSTOMER_CAPTURED,
            restored.execution().customerHeaders().get("cust-userid").provenance());
        assertEquals("secret-token", restored.execution().customerHeaders().get("cust-token").value());
    }

    @Test
    void roundTrip_handlesEmptyCustomerHeaders() throws Exception {
        AsyncTaskContextSnapshot original = new AsyncTaskContextSnapshot(
            "v1",
            new AsyncIdentitySnapshot("token", "user"),
            new AsyncExecutionSnapshot(Map.of()));

        String json = mapper.writeValueAsString(original);
        AsyncTaskContextSnapshot restored = mapper.readValue(json, AsyncTaskContextSnapshot.class);

        assertEquals("token", restored.identity().platformToken());
        assertTrue(restored.execution().customerHeaders() == null
            || restored.execution().customerHeaders().isEmpty());
    }
}
