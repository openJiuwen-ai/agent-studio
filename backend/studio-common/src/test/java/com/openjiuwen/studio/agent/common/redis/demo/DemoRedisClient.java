/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.demo;

import com.openjiuwen.studio.agent.common.redis.impl.RedisClientMemory;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 演示用企业自研客户端：在内存实现之上叠加读写操作统计（模拟自研代理的审计/计量能力）。
 *
 * <p>不修改框架源码，仅通过 Provider 插件机制接入（见 {@link DemoRedisClientProvider}）。
 */
public class DemoRedisClient extends RedisClientMemory {
    private final AtomicInteger readOps = new AtomicInteger();

    private final AtomicInteger writeOps = new AtomicInteger();

    @Override
    public String get(String key) {
        readOps.incrementAndGet();
        return super.get(key);
    }

    @Override
    public String getRaw(String key) {
        readOps.incrementAndGet();
        return super.getRaw(key);
    }

    @Override
    public void set(String key, String value, Duration duration) {
        writeOps.incrementAndGet();
        super.set(key, value, duration);
    }

    @Override
    public void set(String key, String value) {
        writeOps.incrementAndGet();
        super.set(key, value);
    }

    @Override
    public boolean delete(String key) {
        writeOps.incrementAndGet();
        return super.delete(key);
    }

    public int getReadOps() {
        return readOps.get();
    }

    public int getWriteOps() {
        return writeOps.get();
    }
}
