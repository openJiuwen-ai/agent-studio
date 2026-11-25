/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.redis.impl;

import com.openjiuwen.studio.agent.common.redis.RedisLock;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RedisClientMemoryTest {

    private RedisClientMemory redisClient;

    @BeforeEach
    void setUp() {
        redisClient = new RedisClientMemory();
    }

    @Test
    void testExists_KeyNotExists() {
        assertFalse(redisClient.exists("nonexistent"));
    }

    @Test
    void testExists_KeyExists() {
        redisClient.set("key1", "value1");
        assertTrue(redisClient.exists("key1"));
    }

    @Test
    void testGet_KeyNotExists() {
        assertNull(redisClient.get("nonexistent"));
    }

    @Test
    void testGet_KeyExists() {
        redisClient.set("key1", "value1");
        assertEquals("value1", redisClient.get("key1"));
    }

    @Test
    void testGetWithCodec() {
        redisClient.set("key1", "value1");
        assertEquals("value1", redisClient.get("key1", null));
    }

    @Test
    void testSetWithDuration() {
        redisClient.set("key1", "value1", Duration.ofMinutes(5));
        assertEquals("value1", redisClient.get("key1"));
    }

    @Test
    void testSetWithoutDuration() {
        redisClient.set("key1", "value1");
        assertEquals("value1", redisClient.get("key1"));
    }

    @Test
    void testSetObj() {
        Map<String, String> obj = Map.of("name", "test");
        redisClient.setObj("key1", obj);
        assertNotNull(redisClient.get("key1"));
        assertTrue(redisClient.get("key1").contains("test"));
    }

    @Test
    void testExpire() {
        assertTrue(redisClient.expire("key1", Duration.ofMinutes(5)));
    }

    @Test
    void testDelete_ExistingKey() {
        redisClient.set("key1", "value1");
        assertTrue(redisClient.delete("key1"));
        assertNull(redisClient.get("key1"));
    }

    @Test
    void testDelete_NonExistingKey() {
        assertTrue(redisClient.delete("nonexistent"));
    }

    @Test
    void testScoredSortedSet() {
        redisClient.scoredSortedSet("key1", 1000L, "value1");
        assertNotNull(redisClient.get("1000"));
    }

    @Test
    void testScoredSortedGet() {
        List<String> result = redisClient.scoredSortedGet("key1", 0L, 1000L);
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testScoredSortedRemoveList() {
        redisClient.scoredSortedRemoveList("key1", 0L, 1000L);
    }

    @Test
    void testScoredSortedRemove() {
        redisClient.scoredSortedRemove("key1", "value1");
    }

    @Test
    void testGetAll() {
        Map<String, Object> result = redisClient.getAll(Arrays.asList("key1", "key2"));
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetLock() {
        RedisLock lock = redisClient.getLock("lockKey");
        assertNotNull(lock);
    }

    @Test
    void testGetLock_TryLock() throws Exception {
        RedisLock lock = redisClient.getLock("lockKey");
        assertTrue(lock.tryLock(Duration.ofSeconds(1)));
    }

    @Test
    void testGetLock_Unlock() {
        RedisLock lock = redisClient.getLock("lockKey");
        lock.unlock();
    }

    @Test
    void testGetAndIncrement_FirstCall() {
        long result = redisClient.getAndIncrement("counter", 60);
        assertEquals(0L, result);
    }

    @Test
    void testGetAndIncrement_MultipleCalls() {
        long first = redisClient.getAndIncrement("counter", 60);
        long second = redisClient.getAndIncrement("counter", 60);
        long third = redisClient.getAndIncrement("counter", 60);
        assertEquals(0L, first);
        assertEquals(1L, second);
        assertEquals(2L, third);
    }

    @Test
    void testAddAndGet_FirstCall() {
        long result = redisClient.addAndGet("counter", 5, 60);
        assertEquals(5L, result);
    }

    @Test
    void testAddAndGet_MultipleCalls() {
        redisClient.addAndGet("counter", 5, 60);
        long result = redisClient.addAndGet("counter", 3, 60);
        assertEquals(8L, result);
    }

    @Test
    void testDeleteByPrefix() {
        redisClient.set("prefix_key1", "value1");
        redisClient.set("prefix_key2", "value2");
        redisClient.set("other_key", "value3");
        redisClient.deleteByPrefix("prefix_");
        assertNull(redisClient.get("prefix_key1"));
        assertNull(redisClient.get("prefix_key2"));
        assertEquals("value3", redisClient.get("other_key"));
    }

    @Test
    void testDeleteByPrefix_NoMatch() {
        redisClient.set("key1", "value1");
        redisClient.deleteByPrefix("nonexistent_");
        assertEquals("value1", redisClient.get("key1"));
    }

    @Test
    void testSetAndKeepTtl() {
        redisClient.setAndKeepTtl("key1", "value1", Duration.ofMinutes(5));
        assertEquals("value1", redisClient.get("key1"));
    }

    @Test
    void testSetOverwrite() {
        redisClient.set("key1", "value1");
        redisClient.set("key1", "value2");
        assertEquals("value2", redisClient.get("key1"));
    }

    @Test
    void testGetAndIncrement_DifferentKeys() {
        long result1 = redisClient.getAndIncrement("counter1", 60);
        long result2 = redisClient.getAndIncrement("counter2", 60);
        assertEquals(0L, result1);
        assertEquals(0L, result2);
    }

    @Test
    void testAddAndGet_DifferentKeys() {
        long result1 = redisClient.addAndGet("counter1", 5, 60);
        long result2 = redisClient.addAndGet("counter2", 10, 60);
        assertEquals(5L, result1);
        assertEquals(10L, result2);
    }
}
