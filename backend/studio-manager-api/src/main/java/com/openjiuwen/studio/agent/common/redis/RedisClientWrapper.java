/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import lombok.extern.slf4j.Slf4j;

import com.alibaba.fastjson2.JSONException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.exc.StreamConstraintsException;
import com.openjiuwen.studio.agent.common.redis.exception.RedisAccessException;
import com.openjiuwen.studio.agent.common.redis.exception.RedisExceptionClassifier;

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
        // false 是合法业务值（键不存在）：配额/会话类判定会把降级 false 当业务结论（故障期 fail-open），
        // 故障时显式抛出保持 fail-closed，仅以清晰异常替代原先的拆箱 NPE
        return runOrThrow(() -> redisClient.exists(key), "exists");
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
            if (isDecodingException(e)) {
                // 数据解码失败（格式损坏/不兼容）：可观测但降级返回 null，不影响主流程
                log.warn("Redis data decode failed, method: get, key: {}, degraded to null", key, e);
                return null;
            }
            // Redis 连接/超时等故障：服务降级返回 null；先经 classify 翻译再取类别，
            // 使原生实现（Redisson 等）的底层异常也能正确分类（非 J4 族时 categoryOf 恒为 ACCESS）
            RedisAccessException translated = RedisExceptionClassifier.classify(e, "get", key);
            log.error("redis operation failed, method: get, category: {}",
                RedisExceptionClassifier.categoryOf(translated), e);
            return null;
        }
    }

    @Override
    public String getRaw(String key) {
        return run(() -> redisClient.getRaw(key), "getRaw");
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
        // TTL 静默失效会改变业务窗口语义（如配额键永不过期、恢复后被永久锁死），故障时显式抛出
        return runOrThrow(() -> redisClient.expire(key, duration), "expire");
    }

    @Override
    public boolean delete(String key) {
        return Boolean.TRUE.equals(run(() -> redisClient.delete(key), "delete"));
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
                return Boolean.TRUE.equals(run(() -> lock.tryLock(maxWait), "tryLock"));
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
            logCategoryError(e, methodName, null);
        }
        redisCost(startTime, methodName);

        return result;
    }

    /**
     * primitive 返回值方法专用：false/0 既是合法业务值又是潜在降级值，调用方无法区分
     * （存在性/配额类判定会把降级当业务结论，形成故障期 fail-open），故故障时记录后
     * 显式抛出包装异常保持 fail-closed，仅以清晰异常替代原先的拆箱 NPE。
     */
    private <T> T runOrThrow(ThrowingSupplier<T> operation, String methodName) {
        long startTime = getStartTime();
        try {
            return operation.get();
        } catch (Exception e) {
            logCategoryError(e, methodName, null);
            throw new IllegalStateException("Redis operation failed: " + methodName, e);
        } finally {
            redisCost(startTime, methodName);
        }
    }

    private void run(Runnable operation, String methodName) {
        long startTime = getStartTime();
        try {
            operation.run();
        } catch (Exception e) {
            logCategoryError(e, methodName, null);
        }
        redisCost(startTime, methodName);
    }

    /** 统一分类错误日志：先经 classify 翻译（字符串匹配覆盖任意实现的底层异常）再取短类别。 */
    private void logCategoryError(Exception e, String methodName, String key) {
        RedisAccessException translated = RedisExceptionClassifier.classify(e, methodName, key);
        log.error("redis operation failed, method: {}, category: {}",
            methodName, RedisExceptionClassifier.categoryOf(translated), e);
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

    /**
     * 判断是否为数据解码失败（区别于 Redis 连接/超时故障）
     * 解码失败异常链最终为 Jackson 解码异常（MismatchedInputException / InvalidTypeIdException / JsonParseException 等）
     * 或 fastjson2 解析异常（JSON.parseObject 双编码还原）
     */
    private boolean isDecodingException(Throwable e) {
        while (e != null) {
            if (e instanceof JsonProcessingException || e instanceof JSONException) {
                return true;
            }
            e = e.getCause();
        }
        return false;
    }

    @Override
    public long getAndIncrement(String key, long timeoutSeconds) {
        // 0 是合法业务值（首次计数）：配额类调用方（如上传次数判定）无法区分降级与真实 0，
        // 故障时显式抛出保持 fail-closed，仅以清晰异常替代原先的拆箱 NPE
        return runOrThrow(() -> redisClient.getAndIncrement(key, timeoutSeconds), "getAndIncrement");
    }

    @Override
    public long addAndGet(String key, long dela, long timeoutSeconds) {
        return runOrThrow(() -> redisClient.addAndGet(key, dela, timeoutSeconds), "addAndGet");
    }

    @Override
    public void deleteByPrefix(String prefix) {
        run(() -> redisClient.deleteByPrefix(prefix), "deleteByPrefix");
    }

    @Override
    public void rPushAll(String key, List<String> values, Duration duration) {
        run(() -> redisClient.rPushAll(key, values, duration), "rPushAll");
    }

    @Override
    public List<String> lRange(String key, int start, int end) {
        return run(() -> redisClient.lRange(key, start, end), "lRange");
    }

    @Override
    public void lTrim(String key, int start, int end) {
        run(() -> redisClient.lTrim(key, start, end), "lTrim");
    }

    @Override
    public long lLen(String key) {
        Long result = run(() -> redisClient.lLen(key), "lLen");
        return result == null ? 0L : result;
    }

    @Override
    public void setAndKeepTtl(String key, String value, Duration initialDuration) {
        run(() -> redisClient.setAndKeepTtl(key, value, initialDuration), "setAndKeepTtl");
    }
}
