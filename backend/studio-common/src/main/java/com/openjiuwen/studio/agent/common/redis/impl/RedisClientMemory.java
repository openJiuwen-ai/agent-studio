/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.impl;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import lombok.extern.slf4j.Slf4j;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Redis 内存实现（仅用于测试）。
 *
 * <p>语义与 {@link RedisClient} 契约对齐（作为一致性测试套件的参考实现）：
 * KV 生存时间、DEL/EXPIRE 返回值、有序集合、批量读取等行为均按 Redis 命令语义模拟。
 */
@Slf4j
public class RedisClientMemory implements RedisClient {
    private static final Object LOCK = new Object();

    /** 字符串结构：key -> 带过期时间的值 */
    private final Map<String, CacheData<String>> cache = new HashMap<>();

    /** 计数器结构：key -> 带过期时间的数值 */
    private final Map<String, CacheData<Long>> numberCache = new HashMap<>();

    /** List 结构：key -> 带过期时间的列表 */
    private final Map<String, CacheData<List<String>>> listCache = new HashMap<>();

    /** 有序集合结构：key -> (member -> score) */
    private final Map<String, Map<String, Long>> zsetCache = new HashMap<>();

    /** 可重入锁结构：key -> 锁对象 */
    private final Map<String, ReentrantLock> lockCache = new HashMap<>();

    public RedisClientMemory() {
        Executors.newSingleThreadScheduledExecutor()
            .scheduleAtFixedRate(this::clearExpiredData, 1, 1, TimeUnit.MINUTES);
    }

    private void clearExpiredData() {
        try {
            synchronized (LOCK) {
                cache.entrySet().removeIf(entry -> entry.getValue().isExpired());
                numberCache.entrySet().removeIf(entry -> entry.getValue().isExpired());
                listCache.entrySet().removeIf(entry -> entry.getValue().isExpired());
            }
        } catch (Exception e) {
            log.warn("Clear expired data exception. {}", e.getMessage());
        }
    }

    @Override
    public boolean exists(String key) {
        synchronized (LOCK) {
            CacheData<String> data = cache.get(key);
            if (data != null) {
                if (data.isExpired()) {
                    cache.remove(key);
                } else {
                    return true;
                }
            }
            CacheData<List<String>> list = listCache.get(key);
            if (list != null && !list.isExpired()) {
                return true;
            }
            Map<String, Long> zset = zsetCache.get(key);
            return zset != null && !zset.isEmpty();
        }
    }

    @Override
    public String get(String key) {
        synchronized (LOCK) {
            CacheData<String> data = cache.get(key);
            if (data == null) {
                return null;
            }
            if (data.isExpired()) {
                cache.remove(key);
                return null;
            }
            return data.data;
        }
    }

    @Override
    public void set(String key, String value, Duration duration) {
        synchronized (LOCK) {
            cache.put(key, new CacheData<>(value, duration.toMillis()));
        }
    }

    @Override
    public void set(String key, String value) {
        synchronized (LOCK) {
            // Redis SET 语义：覆盖旧值并清除 TTL
            cache.put(key, new CacheData<>(value, (Long) null));
        }
    }

    @Override
    public void setObj(String key, Object value) {
        set(key, JSONObject.toJSONString(value));
    }

    @Override
    public boolean expire(String key, Duration duration) {
        synchronized (LOCK) {
            CacheData<String> data = cache.get(key);
            if (data == null || data.isExpired()) {
                return false;
            }
            data.expireTime = System.currentTimeMillis() + duration.toMillis();
            return true;
        }
    }

    @Override
    public boolean delete(String key) {
        synchronized (LOCK) {
            boolean removed = cache.remove(key) != null;
            removed |= numberCache.remove(key) != null;
            removed |= listCache.remove(key) != null;
            removed |= zsetCache.remove(key) != null;
            return removed;
        }
    }

    @Override
    public void scoredSortedSet(String key, Long timeStamp, String str) {
        synchronized (LOCK) {
            // 根据set中的元素判断，如果是新元素则添加，如果是相同元素则更新 score
            zsetCache.computeIfAbsent(key, k -> new LinkedHashMap<>()).put(str, timeStamp);
        }
    }

    @Override
    public List<String> scoredSortedGet(String key, Long startTime, Long endTime) {
        synchronized (LOCK) {
            Map<String, Long> zset = zsetCache.get(key);
            if (zset == null || zset.isEmpty()) {
                return new ArrayList<>();
            }
            // 按 score 升序返回 [startTime, endTime] 闭区间内的成员
            return zset.entrySet().stream()
                .filter(entry -> entry.getValue() >= startTime && entry.getValue() <= endTime)
                .sorted(Comparator.comparingLong(Map.Entry::getValue))
                .map(Map.Entry::getKey)
                .toList();
        }
    }

    @Override
    public void scoredSortedRemoveList(String key, Long startTime, Long endTime) {
        synchronized (LOCK) {
            Map<String, Long> zset = zsetCache.get(key);
            if (zset == null) {
                return;
            }
            zset.values().removeIf(score -> score >= startTime && score <= endTime);
        }
    }

    @Override
    public void scoredSortedRemove(String key, String str) {
        synchronized (LOCK) {
            Map<String, Long> zset = zsetCache.get(key);
            if (zset != null) {
                zset.remove(str);
            }
        }
    }

    @Override
    public Map<String, Object> getAll(List<String> keyList) {
        Map<String, Object> result = new HashMap<>();
        if (keyList == null) {
            return result;
        }
        synchronized (LOCK) {
            for (String key : keyList) {
                if (cache.containsKey(key)) {
                    String value = get(key);
                    if (value != null) {
                        result.put(key, value);
                    }
                }
            }
        }
        return result;
    }

    @Override
    public RedisLock getLock(String key) {
        ReentrantLock lock;
        synchronized (LOCK) {
            lock = lockCache.computeIfAbsent(key, k -> new ReentrantLock());
        }
        return new RedisLock() {
            @Override
            public boolean tryLock(Duration maxWait) throws Exception {
                return lock.tryLock(maxWait.toNanos(), TimeUnit.NANOSECONDS);
            }

            @Override
            public void unlock() {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            }
        };
    }

    @Override
    public long getAndIncrement(String key, long timeoutSeconds) {
        synchronized (LOCK) {
            CacheData<Long> cacheData = numberCache.computeIfAbsent(key, k -> new CacheData<>(0L, (Long) null));
            if (cacheData.isExpired()) {
                cacheData = new CacheData<>(0L, (Long) null);
                numberCache.put(key, cacheData);
            }
            // 每次访问刷新 TTL（对齐 Redisson timeout 选项语义）
            cacheData.expireTime = System.currentTimeMillis() + timeoutSeconds * 1000L;
            long before = cacheData.data;
            cacheData.data++;
            return before;
        }
    }

    @Override
    public long addAndGet(String key, long dela, long timeoutSeconds) {
        synchronized (LOCK) {
            CacheData<Long> cacheData = numberCache.computeIfAbsent(key, k -> new CacheData<>(0L, (Long) null));
            if (cacheData.isExpired()) {
                cacheData = new CacheData<>(0L, (Long) null);
                numberCache.put(key, cacheData);
            }
            cacheData.expireTime = System.currentTimeMillis() + timeoutSeconds * 1000L;
            cacheData.data += dela;
            return cacheData.data;
        }
    }

    @Override
    public void deleteByPrefix(String prefix) {
        synchronized (LOCK) {
            cache.keySet().removeIf(key -> key.startsWith(prefix));
            numberCache.keySet().removeIf(key -> key.startsWith(prefix));
            listCache.keySet().removeIf(key -> key.startsWith(prefix));
            zsetCache.keySet().removeIf(key -> key.startsWith(prefix));
        }
    }

    @Override
    public void rPushAll(String key, List<String> values, Duration duration) {
        synchronized (LOCK) {
            CacheData<List<String>> listData = listCache.get(key);
            if (listData == null || listData.isExpired()) {
                listData = new CacheData<>(new ArrayList<>(), (Long) null);
                listCache.put(key, listData);
            }
            if (values != null) {
                listData.data.addAll(values);
            }
            // 刷新 TTL，活跃事件流保活
            listData.expireTime = System.currentTimeMillis() + duration.toMillis();
        }
    }

    @Override
    public List<String> lRange(String key, int start, int end) {
        synchronized (LOCK) {
            List<String> list = liveList(key);
            if (list == null || list.isEmpty()) {
                return new ArrayList<>();
            }
            int size = list.size();
            int from = normalizeIndex(start, size);
            int to = normalizeIndex(end, size);
            if (from > to || from >= size) {
                return new ArrayList<>();
            }
            if (to >= size) {
                to = size - 1;
            }
            return new ArrayList<>(list.subList(from, to + 1));
        }
    }

    @Override
    public void lTrim(String key, int start, int end) {
        synchronized (LOCK) {
            CacheData<List<String>> listData = listCache.get(key);
            if (listData == null || listData.isExpired()) {
                return;
            }
            List<String> list = listData.data;
            if (list.isEmpty()) {
                return;
            }
            int size = list.size();
            int from = normalizeIndex(start, size);
            int to = normalizeIndex(end, size);
            if (from > to || from >= size) {
                listCache.put(key, new CacheData<>(new ArrayList<>(), listData));
                return;
            }
            if (to >= size) {
                to = size - 1;
            }
            listCache.put(key, new CacheData<>(new ArrayList<>(list.subList(from, to + 1)), listData));
        }
    }

    @Override
    public long lLen(String key) {
        synchronized (LOCK) {
            List<String> list = liveList(key);
            return list == null ? 0L : list.size();
        }
    }

    @Override
    public void setAndKeepTtl(String key, String value, Duration initialDuration) {
        synchronized (LOCK) {
            CacheData<String> old = cache.get(key);
            long now = System.currentTimeMillis();
            if (old == null || old.isExpired()) {
                cache.put(key, new CacheData<>(value, initialDuration.toMillis()));
                return;
            }
            long remainTtl = old.expireTime - now;
            if (remainTtl < 0 || remainTtl > initialDuration.toMillis()) {
                cache.put(key, new CacheData<>(value, initialDuration.toMillis()));
            } else {
                // 保持剩余 TTL（KEEPTTL 语义）
                cache.put(key, new CacheData<>(value, remainTtl));
            }
        }
    }

    private List<String> liveList(String key) {
        CacheData<List<String>> listData = listCache.get(key);
        if (listData == null) {
            return null;
        }
        if (listData.isExpired()) {
            listCache.remove(key);
            return null;
        }
        return listData.data;
    }

    /**
     * 将 Redis 风格的索引（支持负数从末尾算）归一化为非负索引。
     */
    private int normalizeIndex(int index, int size) {
        int normalized = index < 0 ? size + index : index;
        return Math.max(0, normalized);
    }

    private static class CacheData<T> {
        /** 永不过期标记 */
        private static final long NEVER_EXPIRE = Long.MAX_VALUE;

        private T data;

        /** 过期时刻（绝对时间戳） */
        private long expireTime;

        CacheData(T data, Long timeOutMillis) {
            this.data = data;
            this.expireTime = timeOutMillis == null ? NEVER_EXPIRE
                : System.currentTimeMillis() + timeOutMillis;
        }

        /** 以旧数据的过期时刻构造新数据（保留剩余 TTL 语义） */
        CacheData(T data, CacheData<?> inheritExpiryFrom) {
            this.data = data;
            this.expireTime = inheritExpiryFrom.expireTime;
        }

        boolean isExpired() {
            return System.currentTimeMillis() > expireTime;
        }
    }
}
