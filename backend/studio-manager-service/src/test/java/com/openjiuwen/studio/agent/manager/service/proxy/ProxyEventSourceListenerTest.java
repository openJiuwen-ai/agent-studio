/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service.proxy;

import okhttp3.MediaType;
import okhttp3.Protocol;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;
import okhttp3.sse.EventSource;

import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.slf4j.MDC;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.openjiuwen.studio.agent.manager.observability.MdcKeys;

import java.util.concurrent.CountDownLatch;

import static org.assertj.core.api.Assertions.assertThat;

class ProxyEventSourceListenerTest {
    @Test
    public void onEventTest() {
        SseEmitter emitter = new SseEmitter();
        ProxyEventSourceListener listener = new ProxyEventSourceListener("request", new CountDownLatch(1), emitter);

        EventSource source = new EventSource() {
            @Override
            public @NotNull Request request() {
                return null;
            }

            @Override
            public void cancel() {
            }
        };

        Response rsp = Mockito.mock(Response.class);

        listener.onOpen(source, rsp);

        listener.onEvent(source, "", "", "");
        listener.onClosed(source);
        listener.onEvent(source, "", "", "");
    }

    @Test
    public void onFailureTest() {
        SseEmitter emitter = new SseEmitter();
        ProxyEventSourceListener listener = new ProxyEventSourceListener("request", new CountDownLatch(1), emitter);

        EventSource source = new EventSource() {
            @Override
            public @NotNull Request request() {
                return null;
            }

            @Override
            public void cancel() {
            }
        };

        Response rsp = new Response.Builder().request(new Request.Builder().url("https://demo.com").build())
            .protocol(Protocol.HTTP_1_1)
            .code(200)
            .message("OK")
            .header("test", "aaa")
            .body(ResponseBody.create("{}", MediaType.get("application/json")))
            .build();

        listener.onFailure(source, new Exception(), rsp);
        listener.onFailure(source, null, rsp);
        listener = new ProxyEventSourceListener("request", new CountDownLatch(1), emitter);
        listener.onFailure(source, new Exception(), null);
    }

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    @Test
    public void onEvent_installsSnapshotExecutionId_andRestores() {
        // 构造前设 MDC，快照含 execution-id
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        SseEmitter emitter = new SseEmitter();
        ProxyEventSourceListener listener =
            new ProxyEventSourceListener("req-1", new CountDownLatch(1), emitter);
        MDC.clear(); // 模拟回调线程无 execution-id
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onEvent(source(), "", "", "");

        // 回调后恢复工作线程原值
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    public void onFailure_restoresWorkerMdc() {
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        SseEmitter emitter = new SseEmitter();
        ProxyEventSourceListener listener =
            new ProxyEventSourceListener("req-1", new CountDownLatch(1), emitter);
        MDC.clear();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        Response rsp = new Response.Builder().request(new Request.Builder().url("https://demo.com").build())
            .protocol(Protocol.HTTP_1_1).code(200).message("OK")
            .body(ResponseBody.create("{}", MediaType.get("application/json")))
            .build();
        listener.onFailure(source(), new Exception(), rsp);

        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    public void onOpen_installsSnapshotAndRestores() {
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        ProxyEventSourceListener listener =
            new ProxyEventSourceListener("req-1", new CountDownLatch(1), new SseEmitter());
        MDC.clear();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onOpen(source(), response());

        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    public void onClosed_installsSnapshotAndRestores() {
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        ProxyEventSourceListener listener =
            new ProxyEventSourceListener("req-1", new CountDownLatch(1), new SseEmitter());
        MDC.clear();
        MDC.put(MdcKeys.REQUEST_ID, "worker-residue");

        listener.onClosed(source());

        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("worker-residue");
    }

    @Test
    public void threadReuse_twoCallbacksNoLeakage() {
        MDC.put(MdcKeys.EXECUTION_ID, "exec-1");
        ProxyEventSourceListener listener =
            new ProxyEventSourceListener("req-1", new CountDownLatch(1), new SseEmitter());
        MDC.clear();

        // 第一次回调：工作线程有残留
        MDC.put(MdcKeys.REQUEST_ID, "first-residue");
        listener.onOpen(source(), response());
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("first-residue");

        // 第二次回调：残留恢复后，快照仍为 exec-1，不读 first-residue
        MDC.put(MdcKeys.REQUEST_ID, "second-residue");
        listener.onClosed(source());
        assertThat(MDC.get(MdcKeys.EXECUTION_ID)).isNull();
        assertThat(MDC.get(MdcKeys.REQUEST_ID)).isEqualTo("second-residue");
    }

    private Response response() {
        return new Response.Builder().request(new Request.Builder().url("https://demo.com").build())
            .protocol(Protocol.HTTP_1_1).code(200).message("OK").build();
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
}
