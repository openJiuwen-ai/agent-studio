/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.tck;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * RedisClient 一致性测试套件（TCK）。
 *
 * <p>覆盖 {@link RedisClient} 契约的全部方法语义与边界（方法语义、错误分类中的确定性
 * 返回值边界、TTL 行为、结构类型边界）。所有 Provider 实现（内置或企业自研）均应继承本
 * 套件跑批通过后接入平台，保证可替换性。
 *
 * <p>实现方注意事项：
 * <ul>
 *   <li>每条用例使用独立 key，套件可重复执行</li>
 *   <li>TTL 用例使用 300ms 量级窗口，实现方应保证过期精度在百毫秒级</li>
 *   <li>分布式锁用例验证同 key 互斥与跨线程获取，实现方必须提供真实的互斥语义
 *       （内存实现可用 JVM 锁模拟）</li>
 * </ul>
 */
public abstract class AbstractRedisClientContractTest {
    /** TTL 用例等待窗口（毫秒）：实现方过期精度应优于该值。 */
    private static final long TTL_WAIT_MILLIS = 600;

    private static final long SHORT_TTL_MILLIS = 200;

    protected RedisClient client;

    @BeforeEach
    void setUpContract() {
        client = createClient();
    }

    /**
     * 创建被测客户端实例（每条用例独立实例）。
     */
    protected abstract RedisClient createClient();

    // ------------------------------------------------------------------
    // KV：get / set / exists / delete / getRaw / setObj / getAll
    // ------------------------------------------------------------------

    @Test
    void get_missingKey_returnsNull() {
        assertNull(client.get("tck:kv:missing"));
    }

    @Test
    void set_thenGet_roundTrip() {
        client.set("tck:kv:round", "value1");
        assertEquals("value1", client.get("tck:kv:round"));
    }

    @Test
    void set_overwritesValue() {
        client.set("tck:kv:overwrite", "value1");
        client.set("tck:kv:overwrite", "value2");
        assertEquals("value2", client.get("tck:kv:overwrite"));
    }

    @Test
    void setWithTtl_valueReadableThenExpires() throws InterruptedException {
        client.set("tck:kv:ttl", "value1", Duration.ofMillis(SHORT_TTL_MILLIS));
        assertEquals("value1", client.get("tck:kv:ttl"));

        Thread.sleep(TTL_WAIT_MILLIS);
        assertNull(client.get("tck:kv:ttl"));
        assertFalse(client.exists("tck:kv:ttl"));
    }

    @Test
    void getRaw_returnsSameStringAsGet() {
        client.set("tck:kv:raw", "plain-string");
        assertEquals(client.get("tck:kv:raw"), client.getRaw("tck:kv:raw"));
        assertEquals("plain-string", client.getRaw("tck:kv:raw"));
    }

    @Test
    void getRaw_missingKey_returnsNull() {
        assertNull(client.getRaw("tck:kv:raw:missing"));
    }

    @Test
    void exists_falseForMissingKey_trueAfterSet_falseAfterDelete() {
        assertFalse(client.exists("tck:kv:exists"));
        client.set("tck:kv:exists", "value1");
        assertTrue(client.exists("tck:kv:exists"));
        client.delete("tck:kv:exists");
        assertFalse(client.exists("tck:kv:exists"));
    }

    @Test
    void delete_existingKey_returnsTrueAndRemoves() {
        client.set("tck:kv:delete", "value1");
        assertTrue(client.delete("tck:kv:delete"));
        assertNull(client.get("tck:kv:delete"));
    }

    @Test
    void delete_missingKey_returnsFalse() {
        assertFalse(client.delete("tck:kv:delete:missing"));
    }

    @Test
    void expire_missingKey_returnsFalse() {
        assertFalse(client.expire("tck:kv:expire:missing", Duration.ofSeconds(60)));
    }

    @Test
    void expire_existingKey_returnsTrueAndAppliesTtl() throws InterruptedException {
        client.set("tck:kv:expire", "value1");
        assertTrue(client.expire("tck:kv:expire", Duration.ofMillis(SHORT_TTL_MILLIS)));

        Thread.sleep(TTL_WAIT_MILLIS);
        assertNull(client.get("tck:kv:expire"));
    }

    @Test
    void setObj_storesJsonString() {
        Map<String, String> obj = Map.of("name", "tck", "size", "1");
        client.setObj("tck:kv:setobj", obj);

        String json = client.get("tck:kv:setobj");
        assertTrue(json != null && json.contains("tck"), "setObj 应以 JSON 字符串存储: " + json);
    }

    @Test
    void getAll_returnsOnlyExistingKeys() {
        client.set("tck:kv:getall:1", "value1");
        client.set("tck:kv:getall:2", "value2");

        Map<String, Object> result = client.getAll(
            List.of("tck:kv:getall:1", "tck:kv:getall:2", "tck:kv:getall:missing"));
        assertEquals(2, result.size());
        assertEquals("value1", result.get("tck:kv:getall:1"));
        assertEquals("value2", result.get("tck:kv:getall:2"));
    }

    @Test
    void setAndKeepTtl_updatesValue() {
        client.set("tck:kv:keepttl", "value1", Duration.ofMinutes(10));
        client.setAndKeepTtl("tck:kv:keepttl", "value2", Duration.ofMinutes(10));
        assertEquals("value2", client.get("tck:kv:keepttl"));
    }

    // ------------------------------------------------------------------
    // 计数器：getAndIncrement / addAndGet
    // ------------------------------------------------------------------

    @Test
    void getAndIncrement_returnsPreIncrementValue() {
        assertEquals(0L, client.getAndIncrement("tck:counter:incr", 60));
        assertEquals(1L, client.getAndIncrement("tck:counter:incr", 60));
        assertEquals(2L, client.getAndIncrement("tck:counter:incr", 60));
    }

    @Test
    void addAndGet_accumulatesAndSupportsZeroDelta() {
        assertEquals(5L, client.addAndGet("tck:counter:add", 5, 60));
        assertEquals(8L, client.addAndGet("tck:counter:add", 3, 60));
        assertEquals(8L, client.addAndGet("tck:counter:add", 0, 60));
    }

    @Test
    void counters_areIsolatedByKey() {
        assertEquals(0L, client.getAndIncrement("tck:counter:a", 60));
        assertEquals(0L, client.getAndIncrement("tck:counter:b", 60));
    }

    // ------------------------------------------------------------------
    // 有序集合：scoredSorted*
    // ------------------------------------------------------------------

    @Test
    void scoredSortedGet_returnsMembersInScoreOrderWithinInclusiveRange() {
        client.scoredSortedSet("tck:zset:range", 300L, "m3");
        client.scoredSortedSet("tck:zset:range", 100L, "m1");
        client.scoredSortedSet("tck:zset:range", 200L, "m2");

        List<String> inRange = client.scoredSortedGet("tck:zset:range", 100L, 300L);
        assertEquals(List.of("m1", "m2", "m3"), inRange);

        // 闭区间边界
        assertEquals(List.of("m2"), client.scoredSortedGet("tck:zset:range", 200L, 200L));
        // 范围外
        assertTrue(client.scoredSortedGet("tck:zset:range", 301L, 400L).isEmpty());
    }

    @Test
    void scoredSortedSet_updatesScoreForExistingMember() {
        client.scoredSortedSet("tck:zset:update", 100L, "member");
        client.scoredSortedSet("tck:zset:update", 500L, "member");

        assertEquals(List.of("member"), client.scoredSortedGet("tck:zset:update", 500L, 500L));
        assertTrue(client.scoredSortedGet("tck:zset:update", 100L, 100L).isEmpty());
    }

    @Test
    void scoredSortedRemove_removesMember() {
        client.scoredSortedSet("tck:zset:remove", 100L, "m1");
        client.scoredSortedSet("tck:zset:remove", 200L, "m2");
        client.scoredSortedRemove("tck:zset:remove", "m1");

        assertEquals(List.of("m2"), client.scoredSortedGet("tck:zset:remove", 0L, 300L));
    }

    @Test
    void scoredSortedRemoveList_removesScoreRange() {
        client.scoredSortedSet("tck:zset:removerange", 100L, "m1");
        client.scoredSortedSet("tck:zset:removerange", 200L, "m2");
        client.scoredSortedSet("tck:zset:removerange", 300L, "m3");
        client.scoredSortedRemoveList("tck:zset:removerange", 100L, 200L);

        assertEquals(List.of("m3"), client.scoredSortedGet("tck:zset:removerange", 0L, 400L));
    }

    @Test
    void scoredSortedGet_missingKey_returnsEmptyList() {
        assertTrue(client.scoredSortedGet("tck:zset:missing", 0L, 100L).isEmpty());
    }

    // ------------------------------------------------------------------
    // List：rPushAll / lRange / lLen / lTrim
    // ------------------------------------------------------------------

    @Test
    void rPushAll_thenLRangeAndLLen() {
        client.rPushAll("tck:list:basic", List.of("a", "b", "c"), Duration.ofMinutes(5));

        assertEquals(3L, client.lLen("tck:list:basic"));
        assertEquals(List.of("a", "b", "c"), client.lRange("tck:list:basic", 0, -1));
        assertEquals(List.of("b", "c"), client.lRange("tck:list:basic", 1, -1));
        assertEquals(List.of("c"), client.lRange("tck:list:basic", -1, -1));
    }

    @Test
    void rPushAll_appendsToExistingList() {
        client.rPushAll("tck:list:append", List.of("a"), Duration.ofMinutes(5));
        client.rPushAll("tck:list:append", List.of("b"), Duration.ofMinutes(5));

        assertEquals(List.of("a", "b"), client.lRange("tck:list:append", 0, -1));
    }

    @Test
    void rPushAll_withTtl_expires() throws InterruptedException {
        client.rPushAll("tck:list:ttl", List.of("a"), Duration.ofMillis(SHORT_TTL_MILLIS));
        assertEquals(1L, client.lLen("tck:list:ttl"));

        Thread.sleep(TTL_WAIT_MILLIS);
        assertEquals(0L, client.lLen("tck:list:ttl"));
        assertTrue(client.lRange("tck:list:ttl", 0, -1).isEmpty());
    }

    @Test
    void lTrim_keepsOnlyRange() {
        client.rPushAll("tck:list:trim", List.of("a", "b", "c", "d"), Duration.ofMinutes(5));
        client.lTrim("tck:list:trim", 1, 2);

        assertEquals(List.of("b", "c"), client.lRange("tck:list:trim", 0, -1));
    }

    @Test
    void lRange_missingKey_returnsEmptyList() {
        assertTrue(client.lRange("tck:list:missing", 0, -1).isEmpty());
        assertEquals(0L, client.lLen("tck:list:missing"));
    }

    // ------------------------------------------------------------------
    // 分布式锁：getLock
    // ------------------------------------------------------------------

    @Test
    void lock_tryLockAndUnlock() throws Exception {
        RedisLock lock = client.getLock("tck:lock:basic");
        assertTrue(lock.tryLock(Duration.ofSeconds(1)));
        lock.unlock();
    }

    @Test
    void lock_sameKeyIsMutuallyExclusiveAcrossThreads() throws Exception {
        RedisLock lockA = client.getLock("tck:lock:mutex");
        RedisLock lockB = client.getLock("tck:lock:mutex");

        assertTrue(lockA.tryLock(Duration.ZERO));

        AtomicBoolean bAcquired = new AtomicBoolean(false);
        CountDownLatch done = new CountDownLatch(1);
        Thread threadB = new Thread(() -> {
            try {
                bAcquired.set(lockB.tryLock(Duration.ofMillis(150)));
            } catch (Exception e) {
                bAcquired.set(false);
            } finally {
                done.countDown();
            }
        });
        threadB.start();
        done.await();
        threadB.join();

        assertFalse(bAcquired.get(), "同 key 锁在线程 A 持有时，线程 B 短等待应获取失败");

        lockA.unlock();
        assertTrue(lockB.tryLock(Duration.ofSeconds(1)), "释放后应可重新获取");
        lockB.unlock();
    }

    // ------------------------------------------------------------------
    // 按前缀删除：deleteByPrefix
    // ------------------------------------------------------------------

    @Test
    void deleteByPrefix_removesOnlyMatchingKeysAcrossStructures() {
        client.set("tck:prefix:kv:1", "value1");
        client.set("tck:prefix:kv:2", "value2");
        client.set("tck:other:kv", "value3");
        client.scoredSortedSet("tck:prefix:zset", 100L, "m1");
        client.rPushAll("tck:prefix:list", List.of("a"), Duration.ofMinutes(5));

        client.deleteByPrefix("tck:prefix:");

        assertNull(client.get("tck:prefix:kv:1"));
        assertNull(client.get("tck:prefix:kv:2"));
        assertEquals("value3", client.get("tck:other:kv"));
        assertTrue(client.scoredSortedGet("tck:prefix:zset", 0L, 1000L).isEmpty());
        assertEquals(0L, client.lLen("tck:prefix:list"));
    }
}
