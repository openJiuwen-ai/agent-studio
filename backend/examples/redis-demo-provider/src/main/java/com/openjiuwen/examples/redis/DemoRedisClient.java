/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.examples.redis;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/**
 * 演示 Provider：增强内存后端（真实 TTL 懒过期、真实跨线程锁竞争、可选命令日志与延迟注入）。
 *
 * 语义与契约基类对齐：
 * - TTL：读路径懒判定（get/exists/getRaw/lRange/lLen/getAll 均先判过期）；
 * - 锁：ReentrantLock tryLock(timeout)，跨线程真实互斥；
 * - setAndKeepTtl：保留剩余 TTL（镜像 Redisson 实现语义）。
 *
 * 可选注入项（provider_config 透传）：logCommands=true 逐命令日志；latencyMillis=N 每命令注入延迟。
 */
public class DemoRedisClient implements RedisClient {

    private static final Logger log = LoggerFactory.getLogger(DemoRedisClient.class);

    private final boolean logCommands;

    private final long latencyMillis;

    /** expireAtMillis=0 表示永不过期 */
    private static final class ExpiringValue {
        final String value;
        final long expireAtMillis;

        ExpiringValue(String value, long expireAtMillis) {
            this.value = value;
            this.expireAtMillis = expireAtMillis;
        }
    }

    private static final class ExpiringCounter {
        long value;
        long expireAtMillis;

        ExpiringCounter(long value, long expireAtMillis) {
            this.value = value;
            this.expireAtMillis = expireAtMillis;
        }
    }

    private static final class ExpiringList {
        final List<String> values = new ArrayList<>();
        long expireAtMillis;
    }

    private final Map<String, ExpiringValue> strings = new ConcurrentHashMap<>();

    private final Map<String, ExpiringCounter> counters = new ConcurrentHashMap<>();

    private final Map<String, ExpiringList> lists = new ConcurrentHashMap<>();

    private final Map<String, ReentrantLock> locks = new ConcurrentHashMap<>();

    public DemoRedisClient(boolean logCommands, long latencyMillis) {
        this.logCommands = logCommands;
        this.latencyMillis = latencyMillis;
    }

    // ---------------------------------------------------------------- helpers

    private void before(String command, String key) {
        if (latencyMillis > 0) {
            try {
                Thread.sleep(latencyMillis);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        if (logCommands) {
            log.info("[demo-provider] {} key={}", command, key);
        }
    }

    private static long deadlineOf(Duration duration) {
        return duration == null ? 0L : System.currentTimeMillis() + duration.toMillis();
    }

    private static boolean expired(long expireAtMillis) {
        return expireAtMillis > 0 && System.currentTimeMillis() >= expireAtMillis;
    }

    private ExpiringValue readValue(String key) {
        ExpiringValue entry = strings.get(key);
        if (entry == null) {
            return null;
        }
        if (expired(entry.expireAtMillis)) {
            strings.remove(key);
            return null;
        }
        return entry;
    }

    // ---------------------------------------------------------------- String / Key

    @Override
    public boolean exists(String key) {
        before("exists", key);
        return readValue(key) != null;
    }

    @Override
    public String get(String key) {
        before("get", key);
        ExpiringValue entry = readValue(key);
        return entry == null ? null : entry.value;
    }

    @Override
    public String getRaw(String key) {
        // 内存后端无编解码层，原文即存储值
        return get(key);
    }

    @Override
    public void set(String key, String value, Duration duration) {
        before("set(ttl)", key);
        strings.put(key, new ExpiringValue(value, deadlineOf(duration)));
    }

    @Override
    public void set(String key, String value) {
        before("set", key);
        strings.put(key, new ExpiringValue(value, 0L));
    }

    @Override
    public boolean expire(String key, Duration duration) {
        before("expire", key);
        ExpiringValue entry = readValue(key);
        if (entry == null) {
            return false;
        }
        strings.put(key, new ExpiringValue(entry.value, deadlineOf(duration)));
        return true;
    }

    @Override
    public boolean delete(String key) {
        before("delete", key);
        counters.remove(key);
        lists.remove(key);
        return strings.remove(key) != null;
    }

    @Override
    public Map<String, Object> getAll(List<String> keyList) {
        Map<String, Object> result = new HashMap<>();
        for (String key : keyList) {
            ExpiringValue entry = readValue(key);
            if (entry != null) {
                result.put(key, entry.value);
            }
        }
        return result;
    }

    @Override
    public void deleteByPrefix(String prefix) {
        before("deleteByPrefix", prefix);
        strings.keySet().removeIf(k -> k.startsWith(prefix));
        counters.keySet().removeIf(k -> k.startsWith(prefix));
        lists.keySet().removeIf(k -> k.startsWith(prefix));
        locks.keySet().removeIf(k -> k.startsWith(prefix));
    }

    // ---------------------------------------------------------------- 计数器

    @Override
    public long getAndIncrement(String key, long timeoutSeconds) {
        before("getAndIncrement", key);
        ExpiringCounter counter = counters.compute(key, (k, old) -> {
            long now = System.currentTimeMillis();
            if (old == null || expired(old.expireAtMillis)) {
                return new ExpiringCounter(0L, now + timeoutSeconds * 1000L);
            }
            old.expireAtMillis = now + timeoutSeconds * 1000L;
            return old;
        });
        return counter.value++;
    }

    @Override
    public long addAndGet(String key, long delta, long timeoutSeconds) {
        before("addAndGet", key);
        ExpiringCounter counter = counters.compute(key, (k, old) -> {
            long now = System.currentTimeMillis();
            if (old == null || expired(old.expireAtMillis)) {
                return new ExpiringCounter(delta, now + timeoutSeconds * 1000L);
            }
            old.expireAtMillis = now + timeoutSeconds * 1000L;
            old.value += delta;
            return old;
        });
        return counter.value;
    }

    // ---------------------------------------------------------------- List

    @Override
    public void rPushAll(String key, List<String> values, Duration duration) {
        before("rPushAll", key);
        ExpiringList list = lists.computeIfAbsent(key, k -> new ExpiringList());
        if (values != null && !values.isEmpty()) {
            list.values.addAll(values);
        }
        list.expireAtMillis = deadlineOf(duration);
    }

    @Override
    public List<String> lRange(String key, int start, int end) {
        before("lRange", key);
        List<String> snapshot = readList(key);
        if (snapshot == null) {
            return List.of();
        }
        int size = snapshot.size();
        int from = Math.max(start, 0);
        int to = end < 0 ? size : Math.min(end + 1, size);
        if (from >= size || from >= to) {
            return List.of();
        }
        return List.copyOf(snapshot.subList(from, to));
    }

    @Override
    public void lTrim(String key, int start, int end) {
        before("lTrim", key);
        ExpiringList list = lists.get(key);
        if (list == null || expired(list.expireAtMillis)) {
            return;
        }
        int size = list.values.size();
        int from = Math.max(start, 0);
        int to = end < 0 ? size : Math.min(end + 1, size);
        if (from >= size || from >= to) {
            list.values.clear();
            return;
        }
        list.values.subList(0, from).clear();
        list.values.subList(to - from, list.values.size()).clear();
    }

    @Override
    public long lLen(String key) {
        before("lLen", key);
        List<String> snapshot = readList(key);
        return snapshot == null ? 0L : snapshot.size();
    }

    private List<String> readList(String key) {
        ExpiringList list = lists.get(key);
        if (list == null) {
            return null;
        }
        if (expired(list.expireAtMillis)) {
            lists.remove(key);
            return null;
        }
        synchronized (list) {
            return new ArrayList<>(list.values);
        }
    }

    // ---------------------------------------------------------------- 锁

    @Override
    public RedisLock getLock(String key) {
        ReentrantLock lock = locks.computeIfAbsent(key, k -> new ReentrantLock());
        return new RedisLock() {
            @Override
            public boolean tryLock(Duration maxWait) {
                try {
                    long waitMillis = maxWait == null ? 0L : maxWait.toMillis();
                    return lock.tryLock(waitMillis, TimeUnit.MILLISECONDS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return false;
                }
            }

            @Override
            public void unlock() {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            }
        };
    }

    // ---------------------------------------------------------------- setAndKeepTtl

    @Override
    public void setAndKeepTtl(String key, String value, Duration initialDuration) {
        before("setAndKeepTtl", key);
        ExpiringValue entry = readValue(key);
        long initialMillis = initialDuration == null ? 0L : initialDuration.toMillis();
        if (entry == null || entry.expireAtMillis == 0 || entry.expireAtMillis > System.currentTimeMillis() + initialMillis) {
            // 无 TTL 或剩余超过初始值：按初始 TTL 重置（镜像 Redisson 语义）
            strings.put(key, new ExpiringValue(value, initialMillis == 0 ? 0L
                : System.currentTimeMillis() + initialMillis));
        } else {
            // 保留剩余 TTL
            strings.put(key, new ExpiringValue(value, entry.expireAtMillis));
        }
    }
}
