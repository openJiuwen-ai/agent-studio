/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import lombok.extern.slf4j.Slf4j;

import com.fasterxml.jackson.core.exc.StreamConstraintsException;

import org.redisson.client.codec.Codec;
import org.springframework.util.function.ThrowingSupplier;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Redis包装类，打印redis客户端耗时，捕获异常，考虑到三方redis实现的简洁性，未使用切面
 * 注意：由于异常被捕获，要求redis故障时，能够做服务降级，或不影响业务主流程
 *
 */
@Slf4j
public class RedisClientWrapper implements RedisClient {
    private final RedisClient redisClient;

    private final boolean enableLog;

    public RedisClientWrapper(RedisClient redisClient, boolean enableLog) {
        this.redisClient = redisClient;
        this.enableLog = enableLog;
    }

    @Override
    public boolean exists(String key) {
        return run(() -> redisClient.exists(key), "exists");
    }

    @Override
    public String get(String key) {
        long startTime = getStartTime();
        try {
            String result = redisClient.get(key);
            redisCost(startTime, "get");
            return result;
        } catch (Exception e) {
            redisCost(startTime, "get");
            if (isStreamConstraintsException(e)) {
                log.warn("Redis read overflow for key: {}", key, e);
                throw new RedisReadOverflowException(key, e);
            }
            log.error("redis operation failed, method: get", e);
            return null;
        }
    }

    @Override
    public String get(String key, Codec codec) {
        return run(() -> redisClient.get(key, codec), "get");
    }

    @Override
    public void set(String key, String value, Duration duration) {
        run(() -> redisClient.set(key, value, duration), "set");
    }

    @Override
    public void set(String key, String value) {
        run(() -> redisClient.set(key, value), "set");
    }

    @Override
    public void setObj(String key, Object value) {
        run(() -> redisClient.setObj(key, value), "setObj");
    }

    @Override
    public boolean expire(String key, Duration duration) {
        return run(() -> redisClient.expire(key, duration), "expire");
    }

    @Override
    public boolean delete(String key) {
        return run(() -> redisClient.delete(key), "delete");
    }

    @Override
    public void scoredSortedSet(String key, Long timeStamp, String str) {
        run(() -> redisClient.scoredSortedSet(key, timeStamp, str), "scoredSortedSet");
    }

    @Override
    public List<String> scoredSortedGet(String key, Long startTime, Long endTime) {
        return run(() -> redisClient.scoredSortedGet(key, startTime, endTime), "scoredSortedGet");
    }

    @Override
    public void scoredSortedRemoveList(String key, Long startTime, Long endTime) {
        run(() -> redisClient.scoredSortedRemoveList(key, startTime, endTime), "scoredSortedRemoveList");
    }

    @Override
    public void scoredSortedRemove(String key, String str) {
        run(() -> redisClient.scoredSortedRemove(key, str), "scoredSortedRemove");
    }

    @Override
    public Map<String, Object> getAll(List<String> keyList) {
        return run(() -> redisClient.getAll(keyList), "getAll");
    }

    @Override
    public RedisLock getLock(String key) {
        RedisLock lock = redisClient.getLock(key);
        return new RedisLock() {
            @Override
            public boolean tryLock(Duration maxWait) {
                return run(() -> lock.tryLock(maxWait), "tryLock");
            }

            @Override
            public void unlock() {
                run(lock::unlock, "unlock");
            }
        };
    }

    private <T> T run(ThrowingSupplier<T> operation, String methodName) {
        long startTime = getStartTime();
        T result = null;
        try {
            result = operation.get();
        } catch (Exception e) {
            log.error("redis operation failed, method: {}", methodName, e);
        }
        redisCost(startTime, methodName);

        return result;
    }

    private void run(Runnable operation, String methodName) {
        long startTime = getStartTime();
        try {
            operation.run();
        } catch (Exception e) {
            log.error("redis operation failed, method: {}", methodName, e);
        }
        redisCost(startTime, methodName);
    }

    private long getStartTime() {
        if (!enableLog) {
            return 0;
        }
        return System.currentTimeMillis();
    }

    private void redisCost(long startTime, String method) {
        if (!enableLog) {
            return;
        }
        log.info("redis operation cost: {}ms, method: {}", System.currentTimeMillis() - startTime, method);
    }

    private boolean isStreamConstraintsException(Throwable e) {
        while (e != null) {
            if (e instanceof StreamConstraintsException) {
                return true;
            }
            e = e.getCause();
        }
        return false;
    }

    @Override
    public long getAndIncrement(String key, long timeoutSeconds) {
        return run(() -> redisClient.getAndIncrement(key, timeoutSeconds), "getAndIncrement");
    }

    @Override
    public long addAndGet(String key, long dela, long timeoutSeconds) {
        return run(() -> redisClient.addAndGet(key, dela, timeoutSeconds), "addAndGet");
    }

    @Override
    public void deleteByPrefix(String prefix) {
        run(() -> redisClient.deleteByPrefix(prefix), "deleteByPrefix");
    }

    @Override
    public void setAndKeepTtl(String key, String value, Duration initialDuration) {
        run(() -> redisClient.setAndKeepTtl(key, value, initialDuration), "set");
    }
}
