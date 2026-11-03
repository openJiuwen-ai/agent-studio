/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.observability;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MdcScopeTest {

    @AfterEach
    void clearMdc() {
        // 测试清理可用 clear()：除白名单外还需清掉用例写入的非白名单 key（task-id/traceId 等），
        // 否则跨用例污染（审视 §3.3：replaceWhitelist 用例遗留 task-id 导致顺序依赖失败）
        MDC.clear();
    }

    // ---- open(Map) partial-override semantics ----

    @Test
    void open_no_old_value_close_removes() {
        try (MdcScope ignored = MdcScope.open(Map.of(MdcKeys.REQUEST_ID, "req-1"))) {
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("req-1");
        }
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    @Test
    void open_has_old_value_close_restores() {
        MDC.put(MdcKeys.REQUEST_ID, "old");
        try (MdcScope ignored = MdcScope.open(Map.of(MdcKeys.REQUEST_ID, "new"))) {
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("new");
        }
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("old");
    }

    @Test
    void open_nested_two_layers_restores_lifo() {
        try (MdcScope outer = MdcScope.open(Map.of(MdcKeys.REQUEST_ID, "outer"))) {
            try (MdcScope inner = MdcScope.open(Map.of(MdcKeys.REQUEST_ID, "inner"))) {
                assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("inner");
            }
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("outer");
        }
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    @Test
    void open_exception_in_try_still_restores() {
        MDC.put(MdcKeys.TRACE_ID, "old-trace");
        assertThatThrownBy(() -> {
            try (MdcScope ignored = MdcScope.open(Map.of(MdcKeys.TRACE_ID, "tmp"))) {
                assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("tmp");
                throw new IllegalStateException("boom");
            }
        }).isInstanceOf(IllegalStateException.class);
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("old-trace");
    }

    @Test
    void open_close_is_idempotent() {
        MdcScope scope = MdcScope.open(Map.of(MdcKeys.REQUEST_ID, "v"));
        scope.close();
        // second close must not throw and must not corrupt state
        scope.close();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    @Test
    void open_null_value_throws_and_no_partial_write() {
        Map<String, String> values = new HashMap<>();
        values.put(MdcKeys.REQUEST_ID, "ok");
        values.put(MdcKeys.TRACE_ID, null);
        assertThatThrownBy(() -> MdcScope.open(values))
            .isInstanceOf(IllegalArgumentException.class);
        // no partial modification
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isNull();
    }

    @Test
    void open_multi_key_scope() {
        Map<String, String> values = Map.of(
            MdcKeys.REQUEST_ID, "r",
            MdcKeys.TRACE_ID, "t",
            MdcKeys.EXECUTION_ID, "e",
            MdcKeys.CONVERSATION_ID, "c"
        );
        try (MdcScope ignored = MdcScope.open(values)) {
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("r");
            assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("t");
            assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("e");
            assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("c");
        }
        for (String key : MdcKeys.orderedKeys()) {
            assertThat(MDC.get(key)).isNull();
        }
    }

    @Test
    void open_non_whitelist_key_throws_and_no_partial_write() {
        Map<String, String> values = new HashMap<>();
        values.put(MdcKeys.REQUEST_ID, "ok");
        values.put("task-id", "leak"); // not in whitelist
        assertThatThrownBy(() -> MdcScope.open(values))
            .isInstanceOf(IllegalArgumentException.class);
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
        assertThat(MDC.get("task-id")).isNull();
    }

    @Test
    void open_mixed_supported_and_unsupported_wholesale_rejected() {
        Map<String, String> values = new HashMap<>();
        values.put(MdcKeys.TRACE_ID, "t");
        values.put("traceId", "leak"); // bare legacy key, not whitelist
        assertThatThrownBy(() -> MdcScope.open(values))
            .isInstanceOf(IllegalArgumentException.class);
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isNull();
        assertThat(MDC.get("traceId")).isNull();
    }

    @Test
    void open_caller_mutates_map_after_open_close_still_restores_open_time_keys() {
        // 审视 §4.2：ownedKeys 必须是打开时的快照，不能跟随调用方 Map 动态变化
        Map<String, String> values = new HashMap<>();
        values.put(MdcKeys.REQUEST_ID, "r");
        MdcScope scope = MdcScope.open(values);
        // 调用方在 close 前修改原 Map：新增 + 删除
        values.put(MdcKeys.TRACE_ID, "added-after-open");   // 非 scope 所有权，close 不应动它
        values.remove(MdcKeys.REQUEST_ID);                  // 删除也不影响 scope 恢复 request-id

        // added-after-open 由调用方自己写入的 MDC（scope.open 时只 put 了 request-id）
        scope.close();

        // request-id 属于打开时所有权：被恢复为打开前状态（null）
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    // ---- replaceWhitelist semantics ----

    @Test
    void replaceWhitelist_absent_key_clears_worker_residue() {
        // capture snapshot when only request-id is set (conversation-id absent in snapshot)
        MDC.put(MdcKeys.REQUEST_ID, "snap-req");
        MdcSnapshot snapshot = MdcSnapshot.capture();
        MDC.remove(MdcKeys.REQUEST_ID);
        // now add worker residue on a key the snapshot lacks
        MDC.put(MdcKeys.CONVERSATION_ID, "worker-residue");

        try (MdcScope ignored = MdcScope.replaceWhitelist(snapshot)) {
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("snap-req");
            assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isNull(); // residue cleared
        }
        // worker residue restored on close
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isEqualTo("worker-residue");
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }

    @Test
    void replaceWhitelist_non_whitelist_key_untouched() {
        MDC.put("task-id", "must-survive"); // legacy key, not managed
        MDC.put(MdcKeys.REQUEST_ID, "r");
        MdcSnapshot snapshot = MdcSnapshot.capture();
        MDC.remove(MdcKeys.REQUEST_ID);

        try (MdcScope ignored = MdcScope.replaceWhitelist(snapshot)) {
            // non-whitelist key is never touched by the scope
            assertThat(MDC.get("task-id")).isEqualTo("must-survive");
            assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("r");
        }
        // close only restores whitelist keys; task-id unaffected
        assertThat(MDC.get("task-id")).isEqualTo("must-survive");
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
    }
}
