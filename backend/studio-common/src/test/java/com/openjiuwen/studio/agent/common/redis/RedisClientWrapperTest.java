/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */

package com.openjiuwen.studio.agent.common.redis;

import com.alibaba.fastjson2.JSONException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.exc.StreamConstraintsException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Method;
import java.time.Duration;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RedisClientWrapperTest {

    @Mock
    private RedisClient redisClient;

    private RedisClientWrapper wrapperWithLog;

    private RedisClientWrapper wrapperWithoutLog;

    @BeforeEach
    void setUp() {
        wrapperWithLog = new RedisClientWrapper(redisClient, true);
        wrapperWithoutLog = new RedisClientWrapper(redisClient, false);
    }

    @Test
    void testExists_True() {
        when(redisClient.exists("key1")).thenReturn(true);
        assertTrue(wrapperWithLog.exists("key1"));
        verify(redisClient).exists("key1");
    }

    @Test
    void testExists_False() {
        when(redisClient.exists("key1")).thenReturn(false);
        assertFalse(wrapperWithLog.exists("key1"));
    }

    @Test
    void testExists_Exception() {
        when(redisClient.exists("key1")).thenThrow(new RuntimeException("Redis error"));
        assertThrows(NullPointerException.class, () -> wrapperWithLog.exists("key1"));
    }

    @Test
    void testGet() {
        when(redisClient.get("key1")).thenReturn("value1");
        assertEquals("value1", wrapperWithLog.get("key1"));
    }

    @Test
    void testGet_Null() {
        when(redisClient.get("key1")).thenReturn(null);
        assertNull(wrapperWithLog.get("key1"));
    }

    @Test
    void testGet_Exception() {
        when(redisClient.get("key1")).thenThrow(new RuntimeException("Redis error"));
        assertNull(wrapperWithLog.get("key1"));
    }

    @Test
    void testGetWithCodec() {
        when(redisClient.get(eq("key1"), any())).thenReturn("value1");
        assertEquals("value1", wrapperWithLog.get("key1", null));
    }

    @Test
    void testSetWithDuration() {
        Duration duration = Duration.ofMinutes(5);
        wrapperWithLog.set("key1", "value1", duration);
        verify(redisClient).set("key1", "value1", duration);
    }

    @Test
    void testSetWithDuration_Exception() {
        Duration duration = Duration.ofMinutes(5);
        doThrow(new RuntimeException("Redis error")).when(redisClient).set("key1", "value1", duration);
        wrapperWithLog.set("key1", "value1", duration);
    }

    @Test
    void testSetWithoutDuration() {
        wrapperWithLog.set("key1", "value1");
        verify(redisClient).set("key1", "value1");
    }

    @Test
    void testSetWithoutDuration_Exception() {
        doThrow(new RuntimeException("Redis error")).when(redisClient).set("key1", "value1");
        wrapperWithLog.set("key1", "value1");
    }

    @Test
    void testSetObj() {
        Object obj = new Object();
        wrapperWithLog.setObj("key1", obj);
        verify(redisClient).setObj("key1", obj);
    }

    @Test
    void testSetObj_Exception() {
        Object obj = new Object();
        doThrow(new RuntimeException("Redis error")).when(redisClient).setObj("key1", obj);
        wrapperWithLog.setObj("key1", obj);
    }

    @Test
    void testExpire() {
        Duration duration = Duration.ofMinutes(5);
        when(redisClient.expire("key1", duration)).thenReturn(true);
        assertTrue(wrapperWithLog.expire("key1", duration));
    }

    @Test
    void testExpire_Exception() {
        Duration duration = Duration.ofMinutes(5);
        when(redisClient.expire("key1", duration)).thenThrow(new RuntimeException("Redis error"));
        assertThrows(NullPointerException.class, () -> wrapperWithLog.expire("key1", duration));
    }

    @Test
    void testDelete() {
        when(redisClient.delete("key1")).thenReturn(true);
        assertTrue(wrapperWithLog.delete("key1"));
    }

    @Test
    void testDelete_Exception() {
        when(redisClient.delete("key1")).thenThrow(new RuntimeException("Redis error"));
        assertThrows(NullPointerException.class, () -> wrapperWithLog.delete("key1"));
    }

    @Test
    void testScoredSortedSet() {
        wrapperWithLog.scoredSortedSet("key1", 1000L, "value1");
        verify(redisClient).scoredSortedSet("key1", 1000L, "value1");
    }

    @Test
    void testScoredSortedSet_Exception() {
        doThrow(new RuntimeException("Redis error")).when(redisClient).scoredSortedSet("key1", 1000L, "value1");
        wrapperWithLog.scoredSortedSet("key1", 1000L, "value1");
    }

    @Test
    void testScoredSortedGet() {
        List<String> expected = Arrays.asList("v1", "v2");
        when(redisClient.scoredSortedGet("key1", 0L, 1000L)).thenReturn(expected);
        assertEquals(expected, wrapperWithLog.scoredSortedGet("key1", 0L, 1000L));
    }

    @Test
    void testScoredSortedGet_Exception() {
        when(redisClient.scoredSortedGet("key1", 0L, 1000L)).thenThrow(new RuntimeException("Redis error"));
        assertNull(wrapperWithLog.scoredSortedGet("key1", 0L, 1000L));
    }

    @Test
    void testScoredSortedRemoveList() {
        wrapperWithLog.scoredSortedRemoveList("key1", 0L, 1000L);
        verify(redisClient).scoredSortedRemoveList("key1", 0L, 1000L);
    }

    @Test
    void testScoredSortedRemove() {
        wrapperWithLog.scoredSortedRemove("key1", "value1");
        verify(redisClient).scoredSortedRemove("key1", "value1");
    }

    @Test
    void testGetAll() {
        Map<String, Object> expected = new HashMap<>();
        expected.put("key1", "value1");
        List<String> keys = Arrays.asList("key1");
        when(redisClient.getAll(keys)).thenReturn(expected);
        assertEquals(expected, wrapperWithLog.getAll(keys));
    }

    @Test
    void testGetAll_Exception() {
        List<String> keys = Arrays.asList("key1");
        when(redisClient.getAll(keys)).thenThrow(new RuntimeException("Redis error"));
        assertNull(wrapperWithLog.getAll(keys));
    }

    @Test
    void testGetLock() {
        RedisLock mockLock = new RedisLock() {
            @Override
            public boolean tryLock(Duration maxWait) {
                return true;
            }

            @Override
            public void unlock() {
            }
        };
        when(redisClient.getLock("lockKey")).thenReturn(mockLock);
        RedisLock lock = wrapperWithLog.getLock("lockKey");
        assertNotNull(lock);
    }

    @Test
    void testGetLock_TryLock() throws Exception {
        RedisLock mockLock = new RedisLock() {
            @Override
            public boolean tryLock(Duration maxWait) {
                return true;
            }

            @Override
            public void unlock() {
            }
        };
        when(redisClient.getLock("lockKey")).thenReturn(mockLock);
        RedisLock lock = wrapperWithLog.getLock("lockKey");
        assertTrue(lock.tryLock(Duration.ofSeconds(1)));
    }

    @Test
    void testGetLock_Unlock() {
        RedisLock mockLock = new RedisLock() {
            @Override
            public boolean tryLock(Duration maxWait) {
                return true;
            }

            @Override
            public void unlock() {
            }
        };
        when(redisClient.getLock("lockKey")).thenReturn(mockLock);
        RedisLock lock = wrapperWithLog.getLock("lockKey");
        lock.unlock();
    }

    @Test
    void testGetAndIncrement() {
        when(redisClient.getAndIncrement("counter", 60)).thenReturn(5L);
        assertEquals(5L, wrapperWithLog.getAndIncrement("counter", 60));
    }

    @Test
    void testGetAndIncrement_Exception() {
        when(redisClient.getAndIncrement("counter", 60)).thenThrow(new RuntimeException("Redis error"));
        assertThrows(NullPointerException.class, () -> wrapperWithLog.getAndIncrement("counter", 60));
    }

    @Test
    void testAddAndGet() {
        when(redisClient.addAndGet("counter", 5, 60)).thenReturn(10L);
        assertEquals(10L, wrapperWithLog.addAndGet("counter", 5, 60));
    }

    @Test
    void testAddAndGet_Exception() {
        when(redisClient.addAndGet("counter", 5, 60)).thenThrow(new RuntimeException("Redis error"));
        assertThrows(NullPointerException.class, () -> wrapperWithLog.addAndGet("counter", 5, 60));
    }

    @Test
    void testDeleteByPrefix() {
        wrapperWithLog.deleteByPrefix("prefix_");
        verify(redisClient).deleteByPrefix("prefix_");
    }

    @Test
    void testDeleteByPrefix_Exception() {
        doThrow(new RuntimeException("Redis error")).when(redisClient).deleteByPrefix("prefix_");
        wrapperWithLog.deleteByPrefix("prefix_");
    }

    @Test
    void testSetAndKeepTtl() {
        Duration duration = Duration.ofMinutes(5);
        wrapperWithLog.setAndKeepTtl("key1", "value1", duration);
        verify(redisClient).setAndKeepTtl("key1", "value1", duration);
    }

    @Test
    void testSetAndKeepTtl_Exception() {
        Duration duration = Duration.ofMinutes(5);
        doThrow(new RuntimeException("Redis error")).when(redisClient).setAndKeepTtl("key1", "value1", duration);
        wrapperWithLog.setAndKeepTtl("key1", "value1", duration);
    }

    @Test
    void testWithoutLog_Exists() {
        when(redisClient.exists("key1")).thenReturn(true);
        assertTrue(wrapperWithoutLog.exists("key1"));
    }

    @Test
    void testWithoutLog_Get() {
        when(redisClient.get("key1")).thenReturn("value1");
        assertEquals("value1", wrapperWithoutLog.get("key1"));
    }

    @Test
    void testWithoutLog_Set() {
        wrapperWithoutLog.set("key1", "value1");
        verify(redisClient).set("key1", "value1");
    }

    // ---------- 修改点：get(String key) 解码失败降级与 StreamConstraintsException 分支 ----------

    /**
     * 用例描述：get(key) 底层抛出解码失败异常（异常链中包含 JsonProcessingException）时，
     *          走 isDecodingException 分支 warn 日志并降级返回 null，不影响主流程
     * 预制条件：mock redisClient.get(key) 抛出 RuntimeException，其 cause 为 JsonProcessingException
     * 输入参数：key = key1
     * 预期结果：返回 null（区别于普通连接故障，走解码失败分支）
     */
    @Test
    @SuppressWarnings("serial")
    void testGet_DecodingException_ReturnsNull() {
        // JsonProcessingException 构造器为 protected，用匿名子类构造解码失败异常
        when(redisClient.get("key1")).thenThrow(
            new RuntimeException("decode wrapper", new JsonProcessingException("decode failed") {
            }));
        assertNull(wrapperWithLog.get("key1"));
    }

    /**
     * 用例描述：get(key) 底层异常链包含 StreamConstraintsException（读取溢出）时，
     *          isStreamConstraintsException 分支优先匹配，包装为 RedisReadOverflowException 抛出
     * 预制条件：mock redisClient.get(key) 抛出 RuntimeException，其 cause 为 StreamConstraintsException
     *          （StreamConstraintsException 为受检异常，接口未声明 throws，故用 RuntimeException 包装）
     * 输入参数：key = key1
     * 预期结果：抛出 RedisReadOverflowException，redisKey 字段等于 key1，cause 链含 StreamConstraintsException
     */
    @Test
    void testGet_StreamConstraintsException_ThrowsRedisReadOverflow() {
        when(redisClient.get("key1"))
            .thenThrow(new RuntimeException(new StreamConstraintsException("stream overflow")));
        RedisReadOverflowException ex = assertThrows(RedisReadOverflowException.class,
            () -> wrapperWithLog.get("key1"));
        assertEquals("key1", ex.getRedisKey());
        assertTrue(ex.getCause() instanceof RuntimeException);
        assertTrue(ex.getCause().getCause() instanceof StreamConstraintsException);
    }

    // ---------- 修改点：isDecodingException 新增 fastjson2 JSONException 识别 ----------

    /**
     * 用例描述：isDecodingException 遍历异常 cause 链，命中 JsonProcessingException 时返回 true
     * 预制条件：wrapperWithLog 已初始化；异常链为 RuntimeException -> JsonProcessingException
     * 输入参数：抛出异常 cause 链中含 JsonProcessingException（Jackson 解码异常）
     * 预期结果：返回 true（识别为解码失败）
     */
    @Test
    @SuppressWarnings("serial")
    void testIsDecodingException_shouldReturnTrueWhenCauseChainContainsJsonProcessingException() throws Exception {
        RuntimeException ex = new RuntimeException("decode wrapper",
            new JsonProcessingException("decode failed") {
            });
        assertTrue(invokeIsDecodingException(ex),
            "异常 cause 链含 JsonProcessingException 时应识别为解码失败");
    }

    /**
     * 用例描述：isDecodingException 遍历异常 cause 链，命中 fastjson2 JSONException 时返回 true
     *          （get() 双编码还原走 fastjson2 JSON.parseObject，损坏数据抛 JSONException）
     * 预制条件：wrapperWithLog 已初始化；异常链为 RuntimeException -> fastjson2 JSONException
     * 输入参数：抛出异常 cause 链中含 com.alibaba.fastjson2.JSONException
     * 预期结果：返回 true（此前未被识别，修复后正确识别为解码失败）
     */
    @Test
    void testIsDecodingException_shouldReturnTrueWhenCauseChainContainsFastjson2JSONException() throws Exception {
        RuntimeException ex = new RuntimeException("decode wrapper", new JSONException("bad json"));
        assertTrue(invokeIsDecodingException(ex),
            "异常 cause 链含 fastjson2 JSONException 时应识别为解码失败（修复 2 新增能力）");
    }

    /**
     * 用例描述：isDecodingException 支持多层嵌套 cause 链（深度遍历），
     *          最深层为 fastjson2 JSONException 时仍应识别
     * 预制条件：wrapperWithLog 已初始化；异常链为 RuntimeException -> RuntimeException -> JSONException
     * 输入参数：抛出异常为三层嵌套异常
     * 预期结果：返回 true
     */
    @Test
    void testIsDecodingException_shouldReturnTrueForDeepCauseChain() throws Exception {
        RuntimeException ex = new RuntimeException("outer",
            new RuntimeException("middle", new JSONException("bad json")));
        assertTrue(invokeIsDecodingException(ex),
            "多层嵌套 cause 链中命中 fastjson2 JSONException 时仍应识别为解码失败");
    }

    /**
     * 用例描述：isDecodingException 对普通运行时异常（无解码类异常 cause）返回 false
     * 预制条件：wrapperWithLog 已初始化
     * 输入参数：普通 RuntimeException，无 cause
     * 预期结果：返回 false（区别于解码失败，走连接/超时降级路径）
     */
    @Test
    void testIsDecodingException_shouldReturnFalseForOrdinaryException() throws Exception {
        assertFalse(invokeIsDecodingException(new RuntimeException("redis connection timeout")),
            "普通运行时异常（无解码类 cause）不应识别为解码失败");
    }

    /**
     * 用例描述：isDecodingException 对 null 入参返回 false（遍历循环正常退出）
     * 预制条件：wrapperWithLog 已初始化
     * 输入参数：null
     * 预期结果：返回 false，不抛异常
     */
    @Test
    void testIsDecodingException_shouldReturnFalseForNull() throws Exception {
        assertFalse(invokeIsDecodingException(null),
            "null 入参时遍历循环正常退出，应返回 false");
    }

    /**
     * 通过反射调用私有方法 isDecodingException(Throwable)，
     * 精确验证异常 cause 链识别逻辑的返回值
     */
    private boolean invokeIsDecodingException(Throwable e) throws Exception {
        Method method = RedisClientWrapper.class.getDeclaredMethod("isDecodingException", Throwable.class);
        method.setAccessible(true);
        return (boolean) method.invoke(wrapperWithLog, e);
    }
}
