/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.utils.redis;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.RedisClientWrapper;
import com.openjiuwen.studio.agent.common.redis.RedisLock;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Answers;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.redisson.client.codec.Codec;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class RedisClientWrapperTest {
    @Mock(answer = Answers.RETURNS_DEEP_STUBS)
    private RedisClient redisClient;

    private RedisClientWrapper redisClientWrapper;

    @BeforeEach
    void setUp() throws Exception {
        redisClientWrapper = new RedisClientWrapper(redisClient, true);
    }

    @AfterEach
    void tearDown() throws Exception {
    }

    @Test
    void test_exists_should_return_true() throws Exception {
        // Given
        when(redisClient.exists(anyString())).thenReturn(true);

        // When
        boolean result = redisClientWrapper.exists("not_empty");

        // Then
        assertTrue(result);
    }

    @Test
    void test_get_should_equal_result() throws Exception {
        // Given
        when(redisClient.get(anyString())).thenReturn("not_empty");

        // When
        String result = redisClientWrapper.get("not_empty");

        // Then
        assertEquals("not_empty", result);
    }

    @Test
    void test_get1_should_equal_result() throws Exception {
        // Given
        when(redisClient.get(anyString(), any(Codec.class))).thenReturn("not_empty");

        Codec codec = mock(Codec.class, Answers.RETURNS_DEEP_STUBS);

        // When
        String result = redisClientWrapper.get("not_empty", codec);

        // Then
        assertEquals("not_empty", result);
    }

    @Test
    void test_set_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given
            Duration duration = mock(Duration.class, Answers.RETURNS_DEEP_STUBS);

            // When
            redisClientWrapper.set("not_empty", "not_empty", duration);
        });
    }

    @Test
    void test_set_should_not_throw_exception1() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.set(null, null, (Duration) null);
        });
    }

    @Test
    void test_set1_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.set("not_empty", "not_empty");
        });
    }

    @Test
    void test_set1_should_not_throw_exception1() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.set(null, null);
        });
    }

    @Test
    void test_setObj_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {
            // Given
            Object value = new Object();

            // When
            redisClientWrapper.setObj("not_empty", value);
        });
    }

    @Test
    void test_setObj_should_not_throw_exception1() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.setObj(null, null);
        });
    }

    @Test
    void test_expire_should_return_true() throws Exception {
        // Given
        when(redisClient.expire(anyString(), any(Duration.class))).thenReturn(true);

        Duration duration = mock(Duration.class, Answers.RETURNS_DEEP_STUBS);

        // When
        boolean result = redisClientWrapper.expire("not_empty", duration);

        // Then
        assertTrue(result);
    }

    @Test
    void test_delete_should_return_true() throws Exception {
        // Given
        when(redisClient.delete(anyString())).thenReturn(true);

        // When
        boolean result = redisClientWrapper.delete("not_empty");

        // Then
        assertTrue(result);
    }

    @Test
    void test_scoredSortedSet_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.scoredSortedSet("not_empty", 0L, "not_empty");
        });
    }

    @Test
    void test_scoredSortedSet_should_not_throw_exception1() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.scoredSortedSet(null, (Long) null, null);
        });
    }

    @Test
    void test_scoredSortedGet_should_return_not_null() throws Exception {
        // Given
        List<String> list = new ArrayList<>();
        list.add("not_empty");
        when(redisClient.scoredSortedGet(anyString(), anyLong(), anyLong())).thenReturn(list);

        // When
        List<String> result = redisClientWrapper.scoredSortedGet("not_empty", 0L, 0L);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_scoredSortedGet_should_return_not_null1() throws Exception {
        // Given
        when(redisClient.scoredSortedGet(anyString(), anyLong(), anyLong())).thenReturn(null);

        // When
        List<String> result = redisClientWrapper.scoredSortedGet(null, (Long) null, (Long) null);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_scoredSortedRemoveList_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.scoredSortedRemoveList("not_empty", 0L, 0L);
        });
    }

    @Test
    void test_scoredSortedRemoveList_should_not_throw_exception1() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.scoredSortedRemoveList(null, (Long) null, (Long) null);
        });
    }

    @Test
    void test_scoredSortedRemove_should_not_throw_exception() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.scoredSortedRemove("not_empty", "not_empty");
        });
    }

    @Test
    void test_scoredSortedRemove_should_not_throw_exception1() throws Exception {
        assertDoesNotThrow(() -> {

            // When
            redisClientWrapper.scoredSortedRemove(null, null);
        });
    }

    @Test
    void test_getAll_should_return_not_null() throws Exception {
        // Given
        Map map = new HashMap<>();
        Object object = new Object();
        map.put("not_empty", object);
        when(redisClient.getAll(anyList())).thenReturn(map);

        List<String> keyList = new ArrayList<>();
        keyList.add("not_empty");

        // When
        Map<String, Object> result = redisClientWrapper.getAll(keyList);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getAll_should_return_not_null1() throws Exception {
        // Given
        when(redisClient.getAll(anyList())).thenReturn(null);

        // When
        Map<String, Object> result = redisClientWrapper.getAll(null);

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getLock_should_return_not_null() throws Exception {
        // Given
        RedisLock lock = mock(RedisLock.class, Answers.RETURNS_DEEP_STUBS);
        when(lock.tryLock(any(Duration.class))).thenReturn(true);
        when(redisClient.getLock(anyString())).thenReturn(lock);

        // When
        RedisLock result = redisClientWrapper.getLock("not_empty");

        // Then
        assertNotNull(result);
    }

    @Test
    void test_getAndIncrement_should_equal_result() throws Exception {
        // Given
        when(redisClient.getAndIncrement(anyString(), anyInt())).thenReturn(0L);

        // When
        long result = redisClientWrapper.getAndIncrement("not_empty", 0);

        // Then
        assertEquals(0L, result);
    }

    @Test
    void test_getAndIncrement_should_equal_result1() throws Exception {
        // Given
        when(redisClient.getAndIncrement(anyString(), anyInt())).thenReturn(0L);

        // When
        long result = redisClientWrapper.getAndIncrement(null, 0);

        // Then
        assertEquals(0L, result);
    }

    @Test
    void test_addAndGet_should_equal_result() throws Exception {
        // Given
        when(redisClient.addAndGet(anyString(), anyLong(), anyInt())).thenReturn(0L);

        // When
        long result = redisClientWrapper.addAndGet("not_empty", 0L, 0);

        // Then
        assertEquals(0L, result);
    }

    @Test
    void test_addAndGet_should_equal_result1() throws Exception {
        // Given
        when(redisClient.addAndGet(anyString(), anyLong(), anyInt())).thenReturn(0L);

        // When
        long result = redisClientWrapper.addAndGet(null, 0L, 0);

        // Then
        assertEquals(0L, result);
    }
}