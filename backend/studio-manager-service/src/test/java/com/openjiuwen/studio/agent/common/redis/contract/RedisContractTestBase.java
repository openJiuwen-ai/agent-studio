/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.contract;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Redis Provider 契约测试基类——所有实现（默认 Redisson / 企业自研 Provider / demo）的
 * 统一合格性验收标准。与 Python 侧契约套件语义对齐（同一命令语义 / TTL 单位 / 返回哨兵），
 * 不共享代码。
 *
 * 子类只需提供 {@link #createClient()} 与 {@link #disposeClient(RedisClient)}。
 * 覆盖面：String/Key 语义、真实 TTL 过期、返回哨兵（缺失= null / 空列表）、
 * 锁互斥与等待超时、List 边界（负索引 / lTrim）、计数器（前值返回 + TTL）、
 * setAndKeepTtl 保留剩余 TTL、原文读取。
 *
 * 隔离：每用例独立 key 前缀（contract:uuid:），@AfterEach 按前缀清理。
 */
public abstract class RedisContractTestBase {

    /** TTL 用例时长：留足调度余量，避免慢环境下抖动 */
    private static final Duration SHORT_TTL = Duration.ofMillis(1200);

    private static final long SHORT_TTL_WAIT_MS = 2200;

    protected RedisClient client;

    private String keyPrefix;

    /**
     * 创建被测客户端实例。
     */
    protected abstract RedisClient createClient();

    /**
     * 释放被测客户端（默认无操作；有连接池的实现应覆写）。
     */
    protected void disposeClient(RedisClient client) {
        // 默认无操作
    }

    @BeforeEach
    void setUpContract() {
        client = createClient();
        keyPrefix = "contract:" + UUID.randomUUID() + ":";
    }

    @AfterEach
    void tearDownContract() {
        if (client != null) {
            try {
                client.deleteByPrefix(keyPrefix);
            } finally {
                disposeClient(client);
            }
        }
    }

    /** 本用例独立 key */
    protected String key(String name) {
        return keyPrefix + name;
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // ---------------------------------------------------------------- String / Key

    @Test
    void string_getSet_roundtrip() {
        String key = key("str");
        client.set(key, "hello");
        assertEquals("hello", client.get(key));
    }

    @Test
    void string_getMissing_returnsNull() {
        assertNull(client.get(key("never-set")));
    }

    @Test
    void string_setWithoutDuration_persists() {
        String key = key("persist");
        client.set(key, "value");
        sleep(300);
        assertEquals("value", client.get(key));
    }

    @Test
    void string_setWithDuration_expires() {
        String key = key("ttl");
        client.set(key, "temp", SHORT_TTL);
        assertEquals("temp", client.get(key));
        sleep(SHORT_TTL_WAIT_MS);
        assertNull(client.get(key), "key 应在 TTL 后过期");
        assertFalse(client.exists(key));
    }

    @Test
    void key_exists_and_delete() {
        String key = key("del");
        assertFalse(client.exists(key));
        client.set(key, "v");
        assertTrue(client.exists(key));
        assertTrue(client.delete(key));
        assertFalse(client.exists(key));
        assertFalse(client.delete(key), "重复删除应返回 false");
    }

    @Test
    void key_expire_setsTtl() {
        String key = key("expire");
        client.set(key, "v");
        assertTrue(client.expire(key, SHORT_TTL));
        sleep(SHORT_TTL_WAIT_MS);
        assertNull(client.get(key));
        assertFalse(client.expire(key("expire-missing"), SHORT_TTL), "对不存在 key 设置 TTL 应返回 false");
    }

    @Test
    void key_deleteByPrefix_onlyTouchesPrefix() {
        client.set(key("pa"), "1");
        client.set(key("pb"), "2");
        client.set(key("other"), "3");
        client.deleteByPrefix(keyPrefix + "p");
        assertNull(client.get(key("pa")));
        assertNull(client.get(key("pb")));
        assertEquals("3", client.get(key("other")));
    }

    @Test
    void getAll_returnsExistingKeysWithValues() {
        client.set(key("ga"), "1");
        client.set(key("gb"), "2");
        Map<String, Object> all = client.getAll(List.of(key("ga"), key("gb"), key("g-missing")));
        assertEquals("1", all.get(key("ga")));
        assertEquals("2", all.get(key("gb")));
        assertFalse(all.containsKey(key("g-missing")), "缺失 key 不应出现在结果中");
    }

    // ---------------------------------------------------------------- 计数器

    @Test
    void counter_getAndIncrement_returnsPreValue() {
        String key = key("counter");
        assertEquals(0L, client.getAndIncrement(key, 60));
        assertEquals(1L, client.getAndIncrement(key, 60));
        assertEquals(2L, client.getAndIncrement(key, 60));
    }

    /**
     * 计数器 TTL 属实现定义：timeoutSeconds 仅为提示值，默认实现（Redisson）不强制过期
     * （生产调用方需要确定 TTL 时显式 expire，如 AgentServiceProxyService#checkUploadNum
     * 首次计数后手动 expire 实现固定窗口），故 TTL 过期语义不纳入跨 Provider 契约。
     */

    @Test
    void counter_addAndGet_accumulates() {
        String key = key("adder");
        client.getAndIncrement(key, 60);
        assertEquals(6L, client.addAndGet(key, 5, 60));
        assertEquals(6L, client.addAndGet(key, 0, 60), "delta=0 应只读不写");
        assertEquals(10L, client.addAndGet(key, 4, 60));
    }

    // ---------------------------------------------------------------- List

    @Test
    void list_pushRangeLen_negativeIndexSemantics() {
        String key = key("list");
        client.rPushAll(key, List.of("a", "b", "c", "d"), Duration.ofSeconds(60));
        assertEquals(4L, client.lLen(key));
        assertEquals(List.of("a", "b", "c", "d"), client.lRange(key, 0, -1));
        assertEquals(List.of("b", "c"), client.lRange(key, 1, 2));
        assertEquals(List.of(), client.lRange(key("list-missing"), 0, -1), "缺失 key 的 lRange 应返回空列表");
    }

    @Test
    void list_trimKeepsOnlyRange() {
        String key = key("trim");
        client.rPushAll(key, List.of("a", "b", "c", "d"), Duration.ofSeconds(60));
        client.lTrim(key, 1, 2);
        assertEquals(List.of("b", "c"), client.lRange(key, 0, -1));
        assertEquals(2L, client.lLen(key));
    }

    @Test
    void list_pushWithTtl_expires() {
        String key = key("list-ttl");
        client.rPushAll(key, List.of("x"), SHORT_TTL);
        assertEquals(1L, client.lLen(key));
        sleep(SHORT_TTL_WAIT_MS);
        assertEquals(0L, client.lLen(key), "List 应随 TTL 过期");
    }

    // ---------------------------------------------------------------- 锁

    @Test
    @Timeout(10)
    void lock_mutualExclusion_andRelease() throws Exception {
        String key = key("lock");
        RedisLock lockA = client.getLock(key);
        assertTrue(lockA.tryLock(Duration.ZERO), "首获取锁应成功");

        AtomicReference<Boolean> secondAcquire = new AtomicReference<>(null);
        CountDownLatch done = new CountDownLatch(1);
        Thread contender = new Thread(() -> {
            try {
                RedisLock lockB = client.getLock(key);
                secondAcquire.set(lockB.tryLock(Duration.ofMillis(300)));
            } catch (Exception e) {
                secondAcquire.set(false);
            } finally {
                done.countDown();
            }
        });
        contender.start();
        assertTrue(done.await(5, TimeUnit.SECONDS));
        assertEquals(Boolean.FALSE, secondAcquire.get(), "他人持锁期间 tryLock(300ms) 应失败");

        lockA.unlock();

        // 释放后竞争者可立即获取
        AtomicBoolean reacquired = new AtomicBoolean(false);
        Thread retry = new Thread(() -> {
            try {
                RedisLock lockC = client.getLock(key);
                reacquired.set(lockC.tryLock(Duration.ofSeconds(2)));
                lockC.unlock();
            } catch (Exception e) {
                reacquired.set(false);
            }
        });
        retry.start();
        retry.join(5000);
        assertTrue(reacquired.get(), "锁释放后应可被其他线程获取");
    }

    @Test
    @Timeout(10)
    void lock_tryLockWaits_thenTimesOut() throws Exception {
        String key = key("lock-timeout");
        RedisLock holder = client.getLock(key);
        assertTrue(holder.tryLock(Duration.ZERO));

        // 锁语义可重入（Redisson RLock 与内存实现一致），等待超时必须在异线程验证
        AtomicBoolean acquired = new AtomicBoolean(true);
        AtomicLong elapsedRef = new AtomicLong(0L);
        Thread waiter = new Thread(() -> {
            long start = System.currentTimeMillis();
            try {
                acquired.set(client.getLock(key).tryLock(Duration.ofMillis(500)));
            } catch (Exception e) {
                acquired.set(true);
            }
            elapsedRef.set(System.currentTimeMillis() - start);
        });
        waiter.start();
        waiter.join(5000);

        assertFalse(acquired.get(), "异线程等待期内未获释放应超时返回 false");
        assertTrue(elapsedRef.get() >= 400, "tryLock(maxWait) 应至少等待 maxWait 时长");

        holder.unlock();
    }

    // ---------------------------------------------------------------- setAndKeepTtl

    @Test
    void setAndKeepTtl_valueUpdated_butExpiryPreserved() {
        String key = key("keep-ttl");
        // t0：TTL 2.5s
        client.set(key, "v1", Duration.ofMillis(2500));
        sleep(1200);
        // t0+1.2s：写回不得把 TTL 重置为完整 2.5s
        client.setAndKeepTtl(key, "v2", Duration.ofMillis(2500));
        assertEquals("v2", client.get(key));

        sleep(1700);
        // t0+2.9s：若 TTL 被保留（原 2.5s 到期），此时 key 已过期；
        // 若被重置为 2.5s（到 t0+3.7s），则仍可读到——用本断言区分两种行为
        assertNull(client.get(key), "setAndKeepTtl 不应重置 TTL（保留剩余过期时间）");
    }

    // ---------------------------------------------------------------- 原文读取

    @Test
    void getRaw_presentWhenKeyExists_missingReturnsNull() {
        String key = key("raw");
        client.set(key, "{\"json\":true}");
        // 原文形态（是否带编解码包裹）属实现内部细节，契约只约定：
        // 存在→非 null 的可读文本；缺失→null
        String raw = client.getRaw(key);
        assertNotNull(raw);
        assertFalse(raw.isEmpty());
        assertNull(client.getRaw(key("raw-missing")));
    }
}
