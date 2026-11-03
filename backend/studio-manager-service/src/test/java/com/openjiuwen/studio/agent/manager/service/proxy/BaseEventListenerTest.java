/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import com.openjiuwen.studio.agent.manager.observability.MdcKeys;

import okhttp3.Protocol;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.sse.EventSource;
import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.concurrent.CountDownLatch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

/**
 * DEF-02 §4.4 / §6.3：BaseEventListener 快照 scope 生命周期行为测试。
 * 证明回调期间安装构造时快照、回调结束（含异常）恢复工作线程原值、复用线程不串号。
 */
class BaseEventListenerTest {

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    /** 在 MDC 已设 execution-id 时构造，模拟请求线程已建立 scope；快照应含 execution-id。 */
    private BaseEventListener newListener() {
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        MDC.put(MdcKeys.REQUEST_ID, "req-1");
        BaseEventListener listener = new BaseEventListener("req-1", new org.springframework.http.HttpHeaders());
        listener.setSseEmitter(mock(SseEmitter.class));
        listener.setLatch(new CountDownLatch(1));
        MDC.clear(); // 清构造线程 MDC，模拟 OkHttp 回调线程无 execution-id
        return listener;
    }

    private EventSource source() {
        return new EventSource() {
            @Override
            public @NotNull Request request() {
                return null;
            }

            @Override
            public void cancel() {
            }
        };
    }

    private Response response() {
        return new Response.Builder().request(new Request.Builder().url("https://demo.com").build())
            .protocol(Protocol.HTTP_1_1).code(200).message("OK").build();
    }

    @Test
    void onOpen_installsSnapshot_andRestoresWorkerMdc() {
        BaseEventListener listener = newListener();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue"); // 模拟复用线程残留

        listener.onOpen(source(), response());

        // 回调后恢复工作线程原值：execution-id 未泄漏
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    void onEvent_callbackSeesSnapshotExecutionId_andRestores() {
        CapturingListener listener = CapturingListener.create();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onEvent(source(), "1", "msg", "data");

        // 回调期间可见快照中的 execution-id
        assertThat(listener.seenExec).isEqualTo("exec-1");
        // 回调后恢复
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    void onOpen_callbackSeesSnapshotExecutionId_andRestores() {
        AllHooksListener listener = AllHooksListener.create();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onOpen(source(), response());

        assertThat(listener.onOpenExec).isEqualTo("exec-1");
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
    }

    @Test
    void onFailure_callbackSeesSnapshotExecutionId_andRestores() {
        AllHooksListener listener = AllHooksListener.create();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onFailure(source(), new RuntimeException("boom"), response());

        assertThat(listener.onFailureExec).isEqualTo("exec-1");
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
    }

    @Test
    void onClosed_callbackSeesSnapshotExecutionId_andRestores() {
        AllHooksListener listener = AllHooksListener.create();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onClosed(source());

        assertThat(listener.onClosedExec).isEqualTo("exec-1");
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
    }

    @Test
    void onFailure_installsSnapshot_andRestores() {
        BaseEventListener listener = newListener();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onFailure(source(), new RuntimeException("boom"), response());

        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    void onClosed_installsSnapshot_andRestores() {
        BaseEventListener listener = newListener();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onClosed(source());

        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    void onEvent_hookThrows_stillRestoresAndPropagates() {
        ThrowingListener listener = ThrowingListener.create();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        assertThatThrownBy(() -> listener.onEvent(source(), "1", "msg", "data"))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("boom");

        // 异常路径仍恢复
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    void threadReuse_secondCallbackDoesNotReadFirstResidue() {
        BaseEventListener listener = newListener();
        // 工作线程有残留 execution-id
        MDC.put(MdcKeys.EXECUTION_ID, "first-exec");
        listener.onOpen(source(), response());
        // scope 恢复工作线程原值（first-exec 不被快照吸收，也不泄漏到下次回调）
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isEqualTo("first-exec");

        // 第二次回调用另一 Listener（快照 exec-1），不读 first-exec
        MDC.clear(); // 模拟工作线程清理后处理下次执行
        CapturingListener second = CapturingListener.create();
        second.onEvent(source(), "2", "msg", "data");
        assertThat(second.seenExec).isEqualTo("exec-1");
    }

    /** 捕获回调期间 MDC execution-id 的子类。工厂方法在 super 构造前设 MDC，使快照含 execution-id。 */
    static class CapturingListener extends BaseEventListener {
        String seenExec;

        private CapturingListener(String requestId, org.springframework.http.HttpHeaders headers) {
            super(requestId, headers);
        }

        static CapturingListener create() {
            MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
            MDC.put(MdcKeys.REQUEST_ID, "req-1");
            CapturingListener l = new CapturingListener("req-1", new org.springframework.http.HttpHeaders());
            l.setSseEmitter(mock(SseEmitter.class));
            l.setLatch(new CountDownLatch(1));
            MDC.clear();
            return l;
        }

        @Override
        protected void onEventBusinessHook(String id, String type, String data) {
            seenExec = MDC.get(MdcKeys.EXECUTION_ID);
        }
    }

    /** 捕获全部四个 hook 期间 MDC execution-id 的子类。 */
    static class AllHooksListener extends BaseEventListener {
        String onOpenExec;
        String onFailureExec;
        String onClosedExec;

        private AllHooksListener(String requestId, org.springframework.http.HttpHeaders headers) {
            super(requestId, headers);
        }

        static AllHooksListener create() {
            MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
            MDC.put(MdcKeys.REQUEST_ID, "req-1");
            AllHooksListener l = new AllHooksListener("req-1", new org.springframework.http.HttpHeaders());
            l.setSseEmitter(mock(SseEmitter.class));
            l.setLatch(new CountDownLatch(1));
            MDC.clear();
            return l;
        }

        @Override
        protected void onOpenInternal(okhttp3.Response response) {
            onOpenExec = MDC.get(MdcKeys.EXECUTION_ID);
            super.onOpenInternal(response);
        }

        @Override
        protected void onFailureInternal(Throwable t, okhttp3.Response response) {
            onFailureExec = MDC.get(MdcKeys.EXECUTION_ID);
            super.onFailureInternal(t, response);
        }

        @Override
        protected void onClosedBusinessHook() {
            onClosedExec = MDC.get(MdcKeys.EXECUTION_ID);
            super.onClosedBusinessHook();
        }
    }

    /** hook 抛异常的子类，验证异常路径恢复。 */
    static class ThrowingListener extends BaseEventListener {
        private ThrowingListener(String requestId, org.springframework.http.HttpHeaders headers) {
            super(requestId, headers);
        }

        static ThrowingListener create() {
            MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
            MDC.put(MdcKeys.REQUEST_ID, "req-1");
            ThrowingListener l = new ThrowingListener("req-1", new org.springframework.http.HttpHeaders());
            l.setSseEmitter(mock(SseEmitter.class));
            l.setLatch(new CountDownLatch(1));
            MDC.clear();
            return l;
        }

        @Override
        protected void onEventBusinessHook(String id, String type, String data) {
            throw new RuntimeException("boom");
        }
    }
}
