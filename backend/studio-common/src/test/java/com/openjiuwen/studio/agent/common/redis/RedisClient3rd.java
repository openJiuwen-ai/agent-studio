/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import com.openjiuwen.studio.agent.common.redis.impl.RedisClientMemory;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 存量 RedisClient3rd 扩展点的测试替身（模拟企业既有第三方实现）：
 * 构造签名固定 host/password/port，行为委托内存实现，记录构造参数供断言。
 */
public class RedisClient3rd implements RedisClient {
    /** 记录所有实例的构造参数（host:port:password），供工厂测试断言。 */
    public static final List<String> CONSTRUCTED = new CopyOnWriteArrayList<>();

    private final RedisClient delegate = new RedisClientMemory();

    private final String host;

    private final String password;

    private final int port;

    public RedisClient3rd(String host, String password, int port) {
        this.host = host;
        this.password = password;
        this.port = port;
        CONSTRUCTED.add(host + ":" + port + ":" + password);
    }

    public String getHost() {
        return host;
    }

    public String getPassword() {
        return password;
    }

    public int getPort() {
        return port;
    }

    @Override
    public boolean exists(String key) {
        return delegate.exists(key);
    }

    @Override
    public String get(String key) {
        return delegate.get(key);
    }

    @Override
    public String getRaw(String key) {
        return delegate.getRaw(key);
    }

    @Override
    public void set(String key, String value, Duration duration) {
        delegate.set(key, value, duration);
    }

    @Override
    public void set(String key, String value) {
        delegate.set(key, value);
    }

    @Override
    public void setObj(String key, Object value) {
        delegate.setObj(key, value);
    }

    @Override
    public boolean expire(String key, Duration duration) {
        return delegate.expire(key, duration);
    }

    @Override
    public boolean delete(String key) {
        return delegate.delete(key);
    }

    @Override
    public void scoredSortedSet(String key, Long timeStamp, String str) {
        delegate.scoredSortedSet(key, timeStamp, str);
    }

    @Override
    public List<String> scoredSortedGet(String key, Long startTime, Long endTime) {
        return delegate.scoredSortedGet(key, startTime, endTime);
    }

    @Override
    public void scoredSortedRemoveList(String key, Long startTime, Long endTime) {
        delegate.scoredSortedRemoveList(key, startTime, endTime);
    }

    @Override
    public void scoredSortedRemove(String key, String str) {
        delegate.scoredSortedRemove(key, str);
    }

    @Override
    public Map<String, Object> getAll(List<String> keyList) {
        return delegate.getAll(keyList);
    }

    @Override
    public RedisLock getLock(String key) {
        return delegate.getLock(key);
    }

    @Override
    public long getAndIncrement(String key, long timeoutSeconds) {
        return delegate.getAndIncrement(key, timeoutSeconds);
    }

    @Override
    public long addAndGet(String key, long dela, long timeoutSeconds) {
        return delegate.addAndGet(key, dela, timeoutSeconds);
    }

    @Override
    public void deleteByPrefix(String prefix) {
        delegate.deleteByPrefix(prefix);
    }

    @Override
    public void rPushAll(String key, List<String> values, Duration duration) {
        delegate.rPushAll(key, values, duration);
    }

    @Override
    public List<String> lRange(String key, int start, int end) {
        return delegate.lRange(key, start, end);
    }

    @Override
    public void lTrim(String key, int start, int end) {
        delegate.lTrim(key, start, end);
    }

    @Override
    public long lLen(String key) {
        return delegate.lLen(key);
    }
}
