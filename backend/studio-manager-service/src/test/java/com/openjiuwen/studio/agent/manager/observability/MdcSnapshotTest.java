/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MdcSnapshotTest {

    @BeforeEach
    void setUpMdc() {
        // 前序测试（如 Spring 上下文测试）可能遗留 MDC——先清再跑，保证空快照用例的基线
        MDC.clear();
    }

    @AfterEach
    void clearMdc() {
        // 测试清理可用 clear()：覆盖白名单与用例写入的非白名单 key，避免跨用例污染（审视 §3.3）
        MDC.clear();
    }

    @Test
    void capture_empty_when_no_keys_set() {
        MdcSnapshot snapshot = MdcSnapshot.capture();
        assertThat(snapshot.isEmpty()).isTrue();
    }

    @Test
    void capture_records_present_and_absent_keys() {
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        MDC.put(MdcKeys.TRACE_ID, "trace-1");
        MdcSnapshot snapshot = MdcSnapshot.capture();
        assertThat(snapshot.isEmpty()).isFalse();
        assertThat(snapshot.isPresent(MdcKeys.REQUEST_ID)).isTrue();
        assertThat(snapshot.valueOf(MdcKeys.REQUEST_ID)).isEqualTo("req-1");
        assertThat(snapshot.isPresent(MdcKeys.EXECUTION_ID)).isFalse();
        assertThat(snapshot.isPresent(MdcKeys.CONVERSATION_ID)).isFalse();
    }

    @Test
    void openScope_replaces_whitelist_and_restores_on_close() {
        // capture snapshot with request-id + trace_id only (execution-id/conversation-id absent)
        MDC.put(MdcKeys.REQUEST_ID, "req-2");
        MDC.put(MdcKeys.TRACE_ID, "trace-2");
        MdcSnapshot snapshot = MdcSnapshot.capture();
        MDC.remove(MdcKeys.REQUEST_ID);
        MDC.remove(MdcKeys.TRACE_ID);
        // worker thread has residue on keys the snapshot lacks
        MDC.put(MdcKeys.EXECUTION_ID, "residue-exec");
        MDC.put(MdcKeys.CONVERSATION_ID, "residue-conv");

        try (MdcScope ignored = snapshot.openScope()) {
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("req-2");
            assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("trace-2");
            // residue cleared (absent in snapshot -> removed)
            assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
            assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isNull();
        }

        // worker pre-scope state restored
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("residue-exec");
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("residue-conv");
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    @Test
    void openScope_with_empty_snapshot_clears_all_four() {
        MDC.put(MdcKeys.REQUEST_ID, "r");
        MDC.put(MdcKeys.EXECUTION_ID, "e");
        MdcSnapshot trulyEmpty = MdcSnapshot.empty();
        assertThat(trulyEmpty.isEmpty()).isTrue();

        try (MdcScope ignored = trulyEmpty.openScope()) {
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
            assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
            for (String key : MdcKeys.orderedKeys()) {
                assertThat(MDC.get(key)).isNull();
            }
        }
        // restored
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("r");
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("e");
    }
}
