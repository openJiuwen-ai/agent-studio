/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.environment;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.openjiuwen.studio.agent.manager.observability.MdcKeys;
import com.openjiuwen.studio.agent.manager.observability.MdcScope;
import com.openjiuwen.studio.agent.manager.observability.MdcSnapshot;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * #1652/#1721：入队时捕获 MDC，处理时按项恢复四 key（不启动常驻处理线程，避免测试泄漏）。
 */
class GlobalSyncAgentOpsStatusTest {

    @BeforeEach
    @AfterEach
    void resetSingletonAndMdc() {
        ReflectionTestUtils.setField(GlobalSyncAgentOpsStatus.class, "instance", null);
        MDC.clear();
    }

    @Test
    void addData_captures_mdc_restored_when_processing_item() {
        GlobalSyncAgentOpsStatus<String> queue = GlobalSyncAgentOpsStatus.getInstance();

        MDC.put(MdcKeys.REQUEST_ID, "req-a4-001");
        MDC.put(MdcKeys.TRACE_ID, "trace-a4-001");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-a4-001");
        MDC.put(MdcKeys.CONVERSATION_ID, "conv-a4-001");
        queue.addData("env-1");
        MDC.clear();

        @SuppressWarnings("unchecked")
        ConcurrentLinkedQueue<Object> rawQueue =
            (ConcurrentLinkedQueue<Object>) ReflectionTestUtils.getField(queue, "queue");
        assertNotNull(rawQueue);
        Object item = rawQueue.poll();
        assertNotNull(item);
        MdcSnapshot snapshot = (MdcSnapshot) ReflectionTestUtils.getField(item, "snapshot");
        Object data = ReflectionTestUtils.getField(item, "data");
        assertEquals("env-1", data);
        assertFalse(snapshot.isEmpty());

        try (MdcScope scope = snapshot.openScope()) {
            assertEquals("req-a4-001", MDC.get(MdcKeys.REQUEST_ID));
            assertEquals("trace-a4-001", MDC.get(MdcKeys.TRACE_ID));
            assertEquals("exec-a4-001", MDC.get(MdcKeys.EXECUTION_ID));
            assertEquals("conv-a4-001", MDC.get(MdcKeys.CONVERSATION_ID));
        }
        assertEquals(null, MDC.get(MdcKeys.REQUEST_ID));
    }
}
