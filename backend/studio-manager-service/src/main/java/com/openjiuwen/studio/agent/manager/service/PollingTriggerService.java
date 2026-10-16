/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.utils.OkHttpClientUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;

import lombok.extern.slf4j.Slf4j;
import okhttp3.HttpUrl;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

import org.apache.commons.codec.binary.Hex;
import org.quartz.JobDataMap;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.quartz.JobKey;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.scheduling.quartz.QuartzJobBean;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * Quartz entry and execution logic for Polling triggers.
 */
@Slf4j
@Service
public class PollingTriggerService extends QuartzJobBean {
    private static final String USER_AGENT = "JiuwenTriggerPoller/1.0";

    // Quartz creates job instances per firing. Share admission across instances, including memory Redis mode.
    private static final Set<String> IN_FLIGHT = ConcurrentHashMap.newKeySet();

    @Autowired
    private PollingStateService pollingStateService;

    @Autowired
    private MgAsyncService mgAsyncService;

    @Autowired
    private RedisClient redisClient;

    @Autowired
    private UrlCheckUtils urlCheckUtils;

    @Autowired
    private OkHttpClientUtils okHttpClientUtils;

    /**
     * 最长响应报文长度
     */
    @Value("${trigger.polling.max-response-bytes:10485760}")
    private long maxResponseBytes;

    /**
     * 最大重定向次数
     */
    @Value("${trigger.polling.max-redirects:3}")
    private int maxRedirects;

    @Value("${trigger.polling.check-timeout-seconds:30}")
    private long checkTimeoutSeconds;

    @Value("${trigger.polling.read-timeout-seconds:10}")
    private long readTimeoutSeconds;

    @Override
    protected void executeInternal(JobExecutionContext context) throws JobExecutionException {
        JobDataMap jobDataMap = new JobDataMap(context.getJobDetail().getJobDataMap());
        String triggerId = jobDataMap.getString(CommonConstant.TRIGGER_ID);
        JobKey jobKey = context.getJobDetail().getKey();
        String admissionKey = jobKey.toString();
        if (!IN_FLIGHT.add(admissionKey)) {
            return;
        }
        try {
            mgAsyncService.callPollingCheck(() -> {
                try {
                    executeCheck(jobKey, jobDataMap, triggerId);
                } finally {
                    IN_FLIGHT.remove(admissionKey);
                }
            });
        } catch (TaskRejectedException exception) {
            IN_FLIGHT.remove(admissionKey);
            log.error("Polling trigger {} check was rejected because pollingCheckExecutor is full.", triggerId,
                exception);
        } catch (RuntimeException exception) {
            IN_FLIGHT.remove(admissionKey);
            throw exception;
        }
    }

    private void executeCheck(JobKey jobKey, JobDataMap jobDataMap, String triggerId) {
        RedisLock lock = null;
        boolean acquired = false;
        try {
            lock = redisClient.getLock("polling:check:" + triggerId);
            acquired = lock.tryLock(Duration.ZERO);
            if (acquired) {
                check(jobKey, jobDataMap, triggerId);
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            log.warn("Polling trigger {} check was interrupted.", triggerId, exception);
        } catch (Exception exception) {
            log.error("Polling trigger {} check failed.", triggerId, exception);
        } finally {
            if (acquired) {
                lock.unlock();
            }
        }
    }

    private void check(JobKey jobKey, JobDataMap jobDataMap, String triggerId) {
        if (!pollingStateService.isCurrentConfiguration(jobKey, jobDataMap)) {
            return;
        }
        if (pollingStateService.getState(triggerId) == null) {
            log.info("Polling trigger {} has no runtime state, skip this check.", triggerId);
            return;
        }

        String currentHash;
        try {
            currentHash = fetchHash(jobDataMap.getString(CommonConstant.PROJECT_ID),
                jobDataMap.getString(CommonConstant.POLL_URL));
        } catch (IOException | RuntimeException exception) {
            pollingStateService.completeCheck(jobKey, jobDataMap, null);
            log.error("Polling trigger {} failed to check URL.", triggerId, exception);
            return;
        }
        pollingStateService.completeCheck(jobKey, jobDataMap, currentHash);
    }

    private String fetchHash(String projectId, String pollUrl) throws IOException {
        if (checkTimeoutSeconds <= 0 || readTimeoutSeconds <= 0) {
            throw new IllegalStateException("Polling timeouts must be positive");
        }
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(checkTimeoutSeconds);
        HttpUrl currentUrl = validateUrl(projectId, pollUrl);
        for (int redirectCount = 0; redirectCount <= maxRedirects; redirectCount++) {
            Request request = new Request.Builder()
                .url(currentUrl)
                .header("User-Agent", USER_AGENT)
                .get()
                .build();
            // All redirect hops share one budget. callTimeout also bounds streaming response reads.
            long remaining = remainingNanos(deadline);
            try (Response response = okHttpClientUtils.getHttpClient().newBuilder()
                .callTimeout(remaining, TimeUnit.NANOSECONDS)
                .readTimeout(Math.min(remaining, TimeUnit.SECONDS.toNanos(readTimeoutSeconds)), TimeUnit.NANOSECONDS)
                .followRedirects(false)
                .followSslRedirects(false)
                .build().newCall(request).execute()) {
                if (response.isRedirect()) {
                    if (redirectCount == maxRedirects) {
                        throw new IOException("Polling redirect limit exceeded");
                    }
                    String location = response.header("Location");
                    HttpUrl redirectUrl = location == null ? null : currentUrl.resolve(location);
                    if (redirectUrl == null) {
                        throw new IOException("Polling response contains an invalid redirect URL");
                    }
                    currentUrl = validateUrl(projectId, redirectUrl.toString());
                    continue;
                }
                if (!response.isSuccessful()) {
                    throw new IOException("Polling request failure: HTTP " + response.code());
                }
                String hash = calculateHash(response.body());
                remainingNanos(deadline);
                return hash;
            }
        }
        throw new IOException("Polling redirect limit exceeded");
    }

    private long remainingNanos(long deadline) throws InterruptedIOException {
        long remaining = deadline - System.nanoTime();
        if (remaining <= 0 || Thread.currentThread().isInterrupted()) {
            throw new InterruptedIOException("Polling check timed out or was interrupted");
        }
        return remaining;
    }

    private HttpUrl validateUrl(String projectId, String url) throws IOException {
        try {
            urlCheckUtils.validateUrlSyntax(url);
            urlCheckUtils.checkUrl(projectId, url);
        } catch (RuntimeException exception) {
            throw new IOException("Polling URL validation failed", exception);
        }
        HttpUrl parsedUrl = HttpUrl.parse(url);
        if (parsedUrl == null) {
            throw new IOException("Invalid Polling URL");
        }
        return parsedUrl;
    }

    private String calculateHash(ResponseBody responseBody) throws IOException {
        if (responseBody == null) {
            throw new IOException("Polling response body is empty");
        }
        if (responseBody.contentLength() > maxResponseBytes) {
            throw new IOException("Polling response exceeds the configured size limit");
        }

        //创建 SHA-256 计算器
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }

        //准备读取缓存区
        byte[] buffer = new byte[8192];//8 KiB 字节数组
        long totalBytes = 0;//记录累计量

        //不断读取下一批字节
        try (InputStream inputStream = responseBody.byteStream()) {
            int readBytes;
            while ((readBytes = inputStream.read(buffer)) != -1) {
                totalBytes += readBytes;
                if (totalBytes > maxResponseBytes) {
                    throw new IOException("Polling response exceeds the configured size limit");
                }
                digest.update(buffer, 0, readBytes);
            }
        }
        return Hex.encodeHexString(digest.digest());
    }
}
