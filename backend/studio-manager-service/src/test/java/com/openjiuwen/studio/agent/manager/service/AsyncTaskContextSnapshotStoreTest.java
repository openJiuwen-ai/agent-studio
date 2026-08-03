/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.customerheader.AsyncExecutionSnapshot;
import com.openjiuwen.studio.agent.common.customerheader.AsyncIdentitySnapshot;
import com.openjiuwen.studio.agent.common.customerheader.AsyncTaskContextSnapshot;
import com.openjiuwen.studio.agent.common.customerheader.HeaderValue;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * AsyncTaskContextSnapshotStore 单元测试（单信封）
 *
 * <p>验证 save/load/delete 生命周期 + schema 不符/缺失 → null（调用方应置任务 FAILED，不回退）。
 */
@ExtendWith(MockitoExtension.class)
class AsyncTaskContextSnapshotStoreTest {

    @Mock
    private RedisClient redisClient;

    @InjectMocks
    private AsyncTaskContextSnapshotStore store;

    private static final String TASK_ID = "task-123";
    private static final String CONTEXT_KEY = "agent:runtime:async:context:" + TASK_ID;

    @Test
    void save_then_load_roundTrips() {
        Map<String, HeaderValue> headers = new LinkedHashMap<>();
        headers.put("cust-userid", HeaderValue.customerCaptured("cust-userid", "customer-123"));

        // 捕获 save 写入的 JSON，供 load 读取（验证 key 格式 + 序列化/反序列化往返）
        AtomicReference<String> savedJson = new AtomicReference<>();
        doAnswer(inv -> {
            savedJson.set(inv.getArgument(1));
            return null;
        }).when(redisClient).set(eq(CONTEXT_KEY), anyString(), any(Duration.class));

        store.save(TASK_ID,
            new AsyncIdentitySnapshot("platform-token", "customer-123"),
            new AsyncExecutionSnapshot(headers));

        // save 写入后，stub get 返回捕获的 JSON
        when(redisClient.get(CONTEXT_KEY)).thenReturn(savedJson.get());
        AsyncTaskContextSnapshot loaded = store.load(TASK_ID);

        assertNotNull(loaded);
        assertEquals("v1", loaded.schemaVersion());
        assertEquals("platform-token", loaded.identity().platformToken());
        assertEquals("customer-123", loaded.identity().effectiveUserId());
        assertEquals("customer-123", loaded.execution().customerHeaders().get("cust-userid").value());
    }

    @Test
    void load_returnsNull_whenKeyMissing() {
        when(redisClient.get(CONTEXT_KEY)).thenReturn(null);
        assertNull(store.load(TASK_ID));
    }

    @Test
    void load_returnsNull_whenSchemaMismatch() {
        // 旧/不符 schema 版本的 JSON → load 返回 null（任务 FAILED 不回退）
        when(redisClient.get(CONTEXT_KEY))
            .thenReturn("{\"schemaVersion\":\"v0\",\"identity\":null,\"execution\":null}");
        assertNull(store.load(TASK_ID));
    }

    @Test
    void delete_callsRedisDeleteWithCorrectKey() {
        store.delete(TASK_ID);
        verify(redisClient).delete(CONTEXT_KEY);
    }
}
