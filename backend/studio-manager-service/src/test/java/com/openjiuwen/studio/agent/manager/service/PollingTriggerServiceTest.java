/* Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.entity.PollingTriggerStateEntity;
import com.sun.net.httpserver.HttpServer;
import okhttp3.OkHttpClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.quartz.*;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.test.util.ReflectionTestUtils;

import java.net.InetSocketAddress;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class PollingTriggerServiceTest {
    private final PollingTriggerService service = new PollingTriggerService();
    private final PollingStateService state = mock(PollingStateService.class);
    private final MgAsyncService async = mock(MgAsyncService.class);
    private final RedisClient redis = mock(RedisClient.class);
    private final RedisLock lock = mock(RedisLock.class);
    private final OkHttpClientUtils http = mock(OkHttpClientUtils.class);
    private final JobExecutionContext context = mock(JobExecutionContext.class);
    private JobDetail job;

    @BeforeEach
    void setUp() throws Exception {
        job = JobBuilder.newJob(PollingTriggerService.class).withIdentity(UUID.randomUUID().toString())
            .usingJobData(CommonConstant.TRIGGER_ID, UUID.randomUUID().toString())
            .usingJobData(CommonConstant.PROJECT_ID, "project")
            .usingJobData(CommonConstant.POLL_URL, "http://localhost/").build();
        ReflectionTestUtils.setField(service, "pollingStateService", state);
        ReflectionTestUtils.setField(service, "mgAsyncService", async);
        ReflectionTestUtils.setField(service, "redisClient", redis);
        ReflectionTestUtils.setField(service, "urlCheckUtils", mock(UrlCheckUtils.class));
        ReflectionTestUtils.setField(service, "okHttpClientUtils", http);
        ReflectionTestUtils.setField(service, "maxResponseBytes", 1024L);
        ReflectionTestUtils.setField(service, "maxRedirects", 3);
        ReflectionTestUtils.setField(service, "checkTimeoutSeconds", 1L);
        ReflectionTestUtils.setField(service, "readTimeoutSeconds", 5L);
        when(context.getJobDetail()).thenReturn(job);
        when(redis.getLock(anyString())).thenReturn(lock);
        when(lock.tryLock(Duration.ZERO)).thenReturn(true);
        when(state.isCurrentConfiguration(any(), any())).thenReturn(true);
        when(state.getState(anyString())).thenReturn(new PollingTriggerStateEntity());
        when(http.getHttpClient()).thenReturn(new OkHttpClient());
        doAnswer(invocation -> {
            invocation.getArgument(0, Runnable.class).run();
            return null;
        }).when(async).callPollingCheck(any());
    }

    @Test
    void coalescesQueuedChecksAndReleasesAdmissionAfterCompletion() throws Exception {
        List<Runnable> queued = new ArrayList<>();
        doAnswer(invocation -> { queued.add(invocation.getArgument(0)); return null; })
            .when(async).callPollingCheck(any());
        when(state.isCurrentConfiguration(any(), any())).thenReturn(false);
        service.executeInternal(context);
        service.executeInternal(context);
        assertEquals(1, queued.size());
        queued.get(0).run();
        service.executeInternal(context);
        assertEquals(2, queued.size());
        queued.get(1).run();
        verify(http, never()).getHttpClient();
    }

    @Test
    void rejectedSubmissionDoesNotPermanentlyBlockFutureChecks() throws Exception {
        doThrow(new TaskRejectedException("full")).doAnswer(invocation -> {
            invocation.getArgument(0, Runnable.class).run(); return null;
        }).when(async).callPollingCheck(any());
        when(state.isCurrentConfiguration(any(), any())).thenReturn(false);
        service.executeInternal(context);
        service.executeInternal(context);
        verify(async, times(2)).callPollingCheck(any());
        verify(lock).unlock();
    }

    @Test
    void anotherNodeHoldingLockSkipsDownload() throws Exception {
        when(lock.tryLock(Duration.ZERO)).thenReturn(false);
        service.executeInternal(context);
        verify(state, never()).getState(anyString());
        verify(lock, never()).unlock();
        verify(http, never()).getHttpClient();
    }

    @Test
    void queuedOldConfigurationIsRejectedBeforeDownloading() throws Exception {
        when(state.isCurrentConfiguration(any(), any())).thenReturn(false);
        service.executeInternal(context);
        verify(http, never()).getHttpClient();
        verify(state, never()).completeCheck(any(), any(), any());
    }

    @Test
    void hashesEntireResponseAndCompletesCheck() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            try (exchange) {
                exchange.sendResponseHeaders(200, 3);
                exchange.getResponseBody().write(new byte[] {'a', 'b', 'c'});
            }
        });
        server.start();
        try {
            setUrl(server, "/");
            service.executeInternal(context);
            verify(state).completeCheck(eq(job.getKey()), any(),
                eq("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
        } finally {
            server.stop(0);
        }
    }

    @Test
    void streamingResponseAndRedirectsShareOneTimeBudget() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/redirect", exchange -> {
            try (exchange) {
                pause(600);
                exchange.getResponseHeaders().add("Location", "/slow");
                exchange.sendResponseHeaders(302, -1);
            }
        });
        server.createContext("/slow", exchange -> {
            try (exchange) {
                exchange.sendResponseHeaders(200, 0);
                for (int i = 0; i < 14; i++) {
                    exchange.getResponseBody().write('a');
                    exchange.getResponseBody().flush();
                    pause(50);
                }
            } catch (java.io.IOException expectedWhenClientTimesOut) {
                // The client closes the stream when the shared budget expires.
            }
        });
        server.start();
        try {
            setUrl(server, "/redirect");
            long start = System.nanoTime();
            service.executeInternal(context);
            long elapsedMillis = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
            assertTrue(elapsedMillis < 4000, "Slow responses must not use the global 900-second read timeout");
            verify(state).completeCheck(eq(job.getKey()), any(), isNull());
            verify(lock).unlock();
        } finally {
            server.stop(0);
        }
    }

    @Test
    void skipsCheckWhenStateIsNull() throws Exception {
        when(state.getState(anyString())).thenReturn(null);
        service.executeInternal(context);
        verify(state, never()).completeCheck(any(), any(), any());
        verify(lock).unlock();
    }

    @Test
    void httpErrorCompletesCheckWithNullHash() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            try (exchange) {
                exchange.sendResponseHeaders(500, -1);
            }
        });
        server.start();
        try {
            setUrl(server, "/");
            service.executeInternal(context);
            verify(state).completeCheck(eq(job.getKey()), any(), isNull());
            verify(lock).unlock();
        } finally {
            server.stop(0);
        }
    }

    @Test
    void emptyBodyStillHashesAndCompletesCheck() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", exchange -> {
            try (exchange) {
                exchange.sendResponseHeaders(200, 0);
            }
        });
        server.start();
        try {
            setUrl(server, "/");
            service.executeInternal(context);
            // 空内容的 SHA-256 = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            verify(state).completeCheck(eq(job.getKey()), any(),
                eq("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));
        } finally {
            server.stop(0);
        }
    }

    @Test
    void nonPositiveCheckTimeoutThrowsIllegalStateAndCompletesWithNull() throws Exception {
        ReflectionTestUtils.setField(service, "checkTimeoutSeconds", 0L);
        service.executeInternal(context);
        verify(state).completeCheck(eq(job.getKey()), any(), isNull());
        verify(lock).unlock();
    }

    private void setUrl(HttpServer server, String path) {
        job.getJobDataMap().put(CommonConstant.POLL_URL, "http://127.0.0.1:" + server.getAddress().getPort() + path);
    }

    private static void pause(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
        }
    }

}
