/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpHeaders;

import com.openjiuwen.studio.agent.manager.observability.MdcKeys;

import okhttp3.sse.EventSource;

/**
 * BaseEventListener MdcSnapshot install+restore 状态断言（阻断2 补齐测试）。
 *
 * <p>对抗评审指出：机制已落地（4 回调包 snapshot.openScope），但无测试断言 install+restore 不变量。
 * 本测试用状态断言（非调用断言）：构造时捕获快照 → 清线程 MDC → 调回调 → 断言回调内 MDC==快照值
 * （install）+ 回调后线程 MDC 恢复进入前（restore）。再连续两次回调断言无线程复用残留。
 */
class BaseEventListenerMdcScopeTest {

    /** 捕获 passThrough 执行时的 MDC（在 scope 内）。 */
    static final class CapturingListener extends BaseEventListener {
        volatile Map<String, String> mdcDuringCallback;

        CapturingListener(String requestId, HttpHeaders headers) {
            super(requestId, headers);
        }

        @Override
        protected void passThrough(String data) {
            Map<String, String> snap = new LinkedHashMap<>();
            snap.put(MdcKeys.REQUEST_ID, MDC.get(MdcKeys.REQUEST_ID));
            snap.put(MdcKeys.EXECUTION_ID, MDC.get(MdcKeys.EXECUTION_ID));
            snap.put(MdcKeys.TRACE_ID, MDC.get(MdcKeys.TRACE_ID));
            snap.put(MdcKeys.CONVERSATION_ID, MDC.get(MdcKeys.CONVERSATION_ID));
            mdcDuringCallback = snap;
        }

        void callOnEvent(String data) {
            onEvent((EventSource) null, null, null, data);
        }
    }

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    @Test
    void callback_installs_snapshot_and_restores_prior_mdc() {
        // 构造线程设 MDC，listener 构造时捕获快照
        MDC.put(MdcKeys.REQUEST_ID, "req-A");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-A");
        MDC.put(MdcKeys.TRACE_ID, "trace-A");
        MDC.put(MdcKeys.CONVERSATION_ID, "conv-A");
        CapturingListener listener = new CapturingListener("req-A", new HttpHeaders());

        // 模拟工作线程：清空 MDC（与快照不同），调回调
        MDC.clear();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();  // 进入前为空

        listener.callOnEvent("data");

        // install 断言：回调内 MDC == 快照值（非空，与构造时一致）
        Map<String, String> seen = listener.mdcDuringCallback;
        assertThat(seen.get(MdcKeys.REQUEST_ID)).isEqualTo("req-A");
        assertThat(seen.get(MdcKeys.EXECUTION_ID)).isEqualTo("exec-A");
        assertThat(seen.get(MdcKeys.TRACE_ID)).isEqualTo("trace-A");
        assertThat(seen.get(MdcKeys.CONVERSATION_ID)).isEqualTo("conv-A");

        // restore 断言：回调后线程 MDC 恢复进入前状态（空，无残留）
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isNull();
        assertThat(MDC.get(MdcKeys.CONVERSATION_ID)).isNull();
    }

    @Test
    void repeated_callbacks_no_thread_residue() {
        MDC.put(MdcKeys.REQUEST_ID, "req-B");
        MDC.put(MdcKeys.EXECUTION_ID, "exec-B");
        CapturingListener listener = new CapturingListener("req-B", new HttpHeaders());
        MDC.clear();
        // snapshot 只含 REQUEST_ID/EXECUTION_ID；TRACE_ID/CONVERSATION_ID 在 snapshot 中 absent

        // 第一次回调
        listener.callOnEvent("d1");
        assertThat(listener.mdcDuringCallback.get(MdcKeys.REQUEST_ID)).isEqualTo("req-B");
        // 第一次后线程 MDC 应为空（restore），不残留 "req-B"
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isNull();

        // 模拟线程复用 + 跨请求残留：第二次回调前线程 MDC 有别的值（被别处写入），
        // 包括 snapshot 所 absent 的 TRACE_ID（上一请求残留）——验证 full-replace（absent key 被 remove）
        // 而非 partial-override（absent key 保留残留致跨请求 trace_id 污染）
        MDC.put(MdcKeys.REQUEST_ID, "other-thread-value");
        MDC.put(MdcKeys.TRACE_ID, "stale-from-prev-request");
        listener.callOnEvent("d2");
        // present key：snapshot 覆盖线程值
        assertThat(listener.mdcDuringCallback.get(MdcKeys.REQUEST_ID)).isEqualTo("req-B");
        // absent key（TRACE_ID 不在 snapshot）：full-replace 必须 remove → 回调内为 null
        // 若 replaceWhitelist 退化为 partial-override，此处会读到 "stale-from-prev-request" → 测试失败
        assertThat(listener.mdcDuringCallback.get(MdcKeys.TRACE_ID))
            .as("snapshot absent 的 key 必须在 scope 内被 remove（full-replace 语义，防跨请求残留）")
            .isNull();
        // restore：第二次进入前的值（present + absent 都恢复）
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("other-thread-value");
        assertThat(MDC.get(MdcKeys.TRACE_ID)).isEqualTo("stale-from-prev-request");
    }
}
