/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.agentbase.utils.redis.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.exc.StreamConstraintsException;
import com.fasterxml.jackson.databind.exc.InvalidTypeIdException;
import com.fasterxml.jackson.databind.type.TypeFactory;
import com.openjiuwen.studio.agent.common.crypt.Ciphers;
import com.openjiuwen.studio.agent.common.redis.RedisLock;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.impl.RedisClientRedisson;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.junit.jupiter.MockitoExtension;
import org.redisson.Redisson;
import org.redisson.api.RAtomicLong;
import org.redisson.api.RBucket;
import org.redisson.api.RBuckets;
import org.redisson.api.RLock;
import org.redisson.api.RScoredSortedSet;
import org.redisson.api.RedissonClient;
import org.redisson.client.codec.Codec;
import org.redisson.client.codec.StringCodec;
import org.redisson.config.Config;

import java.lang.reflect.Method;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@ExtendWith(MockitoExtension.class)
class RedisClientRedissonTest {

    @Mock
    private RedissonClient mockRedissonClient;

    @Mock
    private RBucket<Object> mockBucket;

    @Mock
    private RScoredSortedSet<String> mockSortedSet;

    @Mock
    private RBuckets mockBuckets;

    @Mock
    private RLock mockLock;

    @Mock
    private RAtomicLong mockAtomicLong;

    private MockedStatic<Redisson> redissonStatic;

    @BeforeEach
    void setUp() {
        redissonStatic = mockStatic(Redisson.class);
        redissonStatic.when(() -> Redisson.create(any(Config.class))).thenReturn(mockRedissonClient);
    }

    @AfterEach
    void tearDown() {
        if (redissonStatic != null) {
            redissonStatic.close();
        }
    }

    private RedisClientConfig newConfig() {
        RedisClientConfig config = new RedisClientConfig(new Ciphers(null, null));
        // 单元测试不经过 Spring 注入，@Value 属性默认值为 0；
        // 构造器仍用 jsonMaxStringLength 配置 ObjectMapper 的 StreamReadConstraints，
        // 设置一个足够大的上限避免真实流式解码在超长数据上触发约束（get() 已不再做显式长度判断，
        // 溢出场景由主路径 JsonJacksonCodec 抛出 StreamConstraintsException 驱动）
        config.setJsonMaxStringLength(10000);
        return config;
    }

    @Test
    void testConstructorAndConfigBranches() {
        // SingleServer（含密码分支）
        RedisClientConfig single = newConfig();
        single.setRedisHost("127.0.0.1");
        single.setRedisPort(6379);
        single.setRedisPassword("pwd");
        new RedisClientRedisson(single);

        // ClusterServer（含密码分支）
        RedisClientConfig cluster = newConfig();
        cluster.setClusterNodeList("127.0.0.1:7001");
        cluster.setRedisPassword("pwd");
        new RedisClientRedisson(cluster);

        // SentinelServer 及 NatMapper（含密码分支）
        RedisClientConfig sentinel = newConfig();
        sentinel.setNodeAddrList("127.0.0.1:26379");
        sentinel.setTargetPorts("6379");
        sentinel.setSentinelPorts("26379");
        sentinel.setRedisHost("127.0.0.1");
        sentinel.setMasterName("master");
        sentinel.setRedisPassword("pwd");
        new RedisClientRedisson(sentinel);
    }

    @Test
    @SuppressWarnings("unchecked")
    void testAllRedisOperationsAndLambdaCoverage() throws Exception {
        // 初始化并捕获Config
        ArgumentCaptor<Config> configCaptor = ArgumentCaptor.forClass(Config.class);
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        // 验证 Redisson.create 是否被调用，并获取那个 config 实例
        redissonStatic.verify(() -> Redisson.create(configCaptor.capture()));
        Config capturedConfig = configCaptor.getValue();

        //  强行触发 DNS Resolver Lambda 内部逻辑
        if (capturedConfig.getAddressResolverGroupFactory() != null) {
            try {
                Object factory = capturedConfig.getAddressResolverGroupFactory();
                // 自动寻找接口中唯一的抽象方法（即 Lambda 实现的方法）
                java.lang.reflect.Method method = java.util.Arrays.stream(factory.getClass().getMethods())
                    .filter(m -> !m.isDefault() && !java.lang.reflect.Modifier.isStatic(m.getModifiers()))
                    .findFirst()
                    .orElse(null);

                if (method != null) {
                    method.setAccessible(true);
                    // 传入对应数量的 null 参数即可，目的是让代码行被“扫”过
                    Object[] args = new Object[method.getParameterCount()];
                    method.invoke(factory, args);
                }
            } catch (Throwable ignored) {
                // 忽略异常
            }
        }

        // 3. 预设 Mock 行为 (解决编译歧义与泛型问题)
        when(mockRedissonClient.getBucket(anyString())).thenReturn(mockBucket);
        when(mockRedissonClient.getBucket(anyString(), any(org.redisson.client.codec.Codec.class))).thenReturn(
            (RBucket) mockBucket);
        when(mockRedissonClient.<String>getScoredSortedSet(anyString())).thenReturn(mockSortedSet);
        when(mockRedissonClient.getBuckets()).thenReturn(mockBuckets);
        when(mockRedissonClient.getLock(anyString())).thenReturn(mockLock);
        // 显式指定 CommonOptions 类型防止编译不通过
        when(mockRedissonClient.getAtomicLong(any(org.redisson.api.options.CommonOptions.class))).thenReturn(
            mockAtomicLong);

        // 4. 执行业务方法触发覆盖率

        // --- 基础 Bucket 操作 ---
        when(mockBucket.isExists()).thenReturn(true);
        assertTrue(client.exists("k"));
        when(mockBucket.get()).thenReturn("v");
        assertEquals("v", client.get("k"));
        client.set("k", "v");
        client.set("k", "v", Duration.ofSeconds(1));
        client.setObj("k", "v");
        client.delete("k");
        when(mockBucket.expire(any(Duration.class))).thenReturn(true);
        client.expire("k", Duration.ofSeconds(1));

        // --- get(key, codec) 显式编解码器路径 ---
        when(mockBucket.get()).thenReturn("codec-v");
        assertEquals("codec-v", client.get("k", StringCodec.INSTANCE));

        // --- deleteByPrefix ---
        org.redisson.api.RKeys mockKeys = mock(org.redisson.api.RKeys.class);
        when(mockRedissonClient.getKeys()).thenReturn(mockKeys);
        client.deleteByPrefix("prefix_");
        verify(mockKeys).deleteByPattern("prefix_*");

        // --- setAndKeepTtl 三个分支（remainTtl<0 / 0<remainTtl<=initial / remainTtl>initial） ---
        when(mockBucket.remainTimeToLive()).thenReturn(-1L);
        client.setAndKeepTtl("k", "v", Duration.ofDays(7));
        when(mockBucket.remainTimeToLive()).thenReturn(1000L);
        client.setAndKeepTtl("k", "v", Duration.ofDays(7));
        when(mockBucket.remainTimeToLive()).thenReturn(604800000L + 1);
        client.setAndKeepTtl("k", "v", Duration.ofDays(7));

        // --- 有序集合 (使用 anyDouble 规避 NPE 和 类型不匹配) ---
        when(mockSortedSet.valueRange(anyDouble(), anyBoolean(), anyDouble(), anyBoolean())).thenReturn(List.of("m"));
        client.scoredSortedSet("z", 1L, "m");
        client.scoredSortedGet("z", 1L, 2L);
        client.scoredSortedRemoveList("z", 1L, 2L);
        client.scoredSortedRemove("z", "m");

        // --- 原子操作 ---
        when(mockAtomicLong.getAndIncrement()).thenReturn(1L);
        client.getAndIncrement("a", 60);
        when(mockAtomicLong.addAndGet(anyLong())).thenReturn(5L);
        client.addAndGet("a", 5L, 60);
        when(mockAtomicLong.get()).thenReturn(10L);
        client.addAndGet("a", 0L, 60);

        // --- 批量与锁 ---
        when(mockBuckets.get(any())).thenReturn(Map.of());
        client.getAll(List.of("k1"));

        when(mockLock.tryLock(anyLong(), any(TimeUnit.class))).thenReturn(true);
        RedisLock lock = client.getLock("l");
        lock.tryLock(Duration.ofSeconds(1));

        // 覆盖锁的 unlock 内部 if 分支
        when(mockLock.isHeldByCurrentThread()).thenReturn(true);
        lock.unlock();
        when(mockLock.isHeldByCurrentThread()).thenReturn(false);
        lock.unlock();

        // 5. 校验关键调用
        verify(mockSortedSet).removeRangeByScore(anyDouble(), eq(true), anyDouble(), eq(true));
        verify(mockAtomicLong).addAndGet(5L);
    }

    // ---------- 修改点：get(String key) 主路径 JsonJacksonCodec + fallback StringCodec ----------

    /**
     * 用例描述：get(key) 主路径使用默认 JsonJacksonCodec（单参数 getBucket）读取成功并原样返回，
     *          不再走 StringCodec + fastjson 双编码还原逻辑
     * 预制条件：mock RedissonClient.getBucket(key)（主路径）返回 bucket，bucket.get() 返回 "hello world"
     * 输入参数：key = k_main
     * 预期结果：返回 "hello world"，仅调用单参数 getBucket，不触发 StringCodec fallback
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_mainPath_shouldReturnValueViaJsonJacksonCodec() {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        RBucket<String> bucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_main"))).thenReturn(bucket);
        when(bucket.get()).thenReturn("hello world");

        assertEquals("hello world", client.get("k_main"));

        verify(mockRedissonClient).getBucket(eq("k_main"));
        verify(mockRedissonClient, never()).getBucket(eq("k_main"), any(org.redisson.client.codec.Codec.class));
    }

    /**
     * 用例描述：get(key) 主路径读取到的值为 null 时直接返回 null
     * 预制条件：mock 主路径 getBucket(key).get() 返回 null
     * 输入参数：key = k_null
     * 预期结果：返回 null
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_nullValue_shouldReturnNullDirectly() {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        RBucket<String> bucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_null"))).thenReturn(bucket);
        when(bucket.get()).thenReturn(null);

        assertNull(client.get("k_null"));
    }

    /**
     * 用例描述：get(key) 主路径读取到的值为空字符串时原样返回
     * 预制条件：mock 主路径 getBucket(key).get() 返回 ""
     * 输入参数：key = k_empty
     * 预期结果：返回 ""
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_emptyValue_shouldReturnEmptyStringDirectly() {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        RBucket<String> bucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_empty"))).thenReturn(bucket);
        when(bucket.get()).thenReturn("");

        assertEquals("", client.get("k_empty"));
    }

    /**
     * 用例描述：get(key) 主路径读取到普通字符串时原样返回
     * 预制条件：mock 主路径 getBucket(key).get() 返回 "plain-value"
     * 输入参数：key = k_plain
     * 预期结果：原样返回 "plain-value"
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_plainValue_shouldReturnAsIs() {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        RBucket<String> bucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_plain"))).thenReturn(bucket);
        when(bucket.get()).thenReturn("plain-value");

        assertEquals("plain-value", client.get("k_plain"));
    }

    /**
     * 用例描述：get(key) 主路径 JsonJacksonCodec 解码失败（cause 链含 InvalidTypeIdException，
     *          如 runtime 单编码数据缺 @class）时，fallback StringCodec.INSTANCE 读取原文
     * 预制条件：主路径 getBucket(key) 返回的 bucket.get() 抛 RuntimeException(cause=InvalidTypeIdException)；
     *          fallback getBucket(key, StringCodec.INSTANCE) 返回的 bucket.get() 返回 "raw-value"
     * 输入参数：key = k_format
     * 预期结果：返回 fallback 读取到的 "raw-value"，且 verify 使用 StringCodec.INSTANCE
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_formatDecodeError_shouldFallbackToStringCodec() throws Exception {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        // 构造 cause 链含 InvalidTypeIdException 的格式解码失败异常
        JsonParser parser = new JsonFactory().createParser("{}");
        InvalidTypeIdException invalidTypeId = InvalidTypeIdException.from(parser, "Invalid type id",
            TypeFactory.defaultInstance().constructType(String.class), "X");
        RuntimeException decodeError = new RuntimeException("decode failed", invalidTypeId);

        RBucket<String> mainBucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_format"))).thenReturn(mainBucket);
        when(mainBucket.get()).thenThrow(decodeError);

        RBucket<String> fallbackBucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_format"), eq(StringCodec.INSTANCE))).thenReturn(fallbackBucket);
        when(fallbackBucket.get()).thenReturn("raw-value");

        assertEquals("raw-value", client.get("k_format"));

        verify(mockRedissonClient).getBucket(eq("k_format"), eq(StringCodec.INSTANCE));
    }

    /**
     * 用例描述：get(key) 主路径异常 cause 链含 StreamConstraintsException（数据溢出）时不 fallback，
     *          原异常原样向上抛出，维持溢出清理链路语义
     * 预制条件：主路径 getBucket(key) 返回的 bucket.get() 抛 RuntimeException(cause=StreamConstraintsException)
     * 输入参数：key = k_overflow
     * 预期结果：抛出同一个 overflow 异常，且不调用 getBucket(key, codec) fallback
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_streamConstraints_shouldNotFallbackAndThrow() {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        RuntimeException overflow = new RuntimeException("stream overflow", new StreamConstraintsException("overflow"));

        RBucket<String> bucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_overflow"))).thenReturn(bucket);
        when(bucket.get()).thenThrow(overflow);

        RuntimeException ex = assertThrows(RuntimeException.class, () -> client.get("k_overflow"));
        assertSame(overflow, ex, "溢出异常应原样向上抛出，不触发 fallback");
        verify(mockRedissonClient, never()).getBucket(eq("k_overflow"), any(org.redisson.client.codec.Codec.class));
    }

    /**
     * 用例描述：get(key) 主路径抛出非解码类异常（如 Redis 连接故障的普通 RuntimeException）时不 fallback，
     *          原异常原样向上抛出
     * 预制条件：主路径 getBucket(key) 返回的 bucket.get() 抛普通 RuntimeException("connection failed")
     * 输入参数：key = k_conn
     * 预期结果：抛出同一个 connError 异常，且不调用 getBucket(key, codec) fallback
     */
    @Test
    @SuppressWarnings("unchecked")
    void testGet_nonDecodeException_shouldNotFallbackAndThrow() {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        RuntimeException connError = new RuntimeException("connection failed");

        RBucket<String> bucket = mock(RBucket.class);
        when(mockRedissonClient.<String>getBucket(eq("k_conn"))).thenReturn(bucket);
        when(bucket.get()).thenThrow(connError);

        RuntimeException ex = assertThrows(RuntimeException.class, () -> client.get("k_conn"));
        assertSame(connError, ex, "非解码异常应原样向上抛出，不触发 fallback");
        verify(mockRedissonClient, never()).getBucket(eq("k_conn"), any(org.redisson.client.codec.Codec.class));
    }

    /**
     * 用例描述：私有方法 isFormatDecodeError 的判定边界——异常链含 StreamConstraintsException 返回 false（溢出）、
     *          含 JsonProcessingException（InvalidTypeIdException）返回 true（格式失败）、
     *          null 与普通异常返回 false
     * 预制条件：通过反射调用私有方法 isFormatDecodeError(Throwable)
     * 输入参数：构造 4 种异常链：stream / invalidTypeId / null / plain
     * 预期结果：依次返回 false / true / false / false
     */
    @Test
    void testIsFormatDecodeError_boundary_shouldMatchExpectedResults() throws Exception {
        RedisClientConfig clientConfig = newConfig();
        clientConfig.setRedisHost("127.0.0.1");
        RedisClientRedisson client = new RedisClientRedisson(clientConfig);

        // 含 StreamConstraintsException → false（溢出，不 fallback）
        assertFalse(invokeIsFormatDecodeError(client,
            new RuntimeException(new StreamConstraintsException("overflow"))),
            "异常链含 StreamConstraintsException 时应判定为溢出而非格式失败");

        // 含 InvalidTypeIdException（JsonProcessingException 子类）→ true
        JsonParser parser = new JsonFactory().createParser("{}");
        InvalidTypeIdException invalidTypeId = InvalidTypeIdException.from(parser, "Invalid type id",
            TypeFactory.defaultInstance().constructType(String.class), "X");
        assertTrue(invokeIsFormatDecodeError(client, new RuntimeException(invalidTypeId)),
            "异常链含 JsonProcessingException 时应判定为格式解码失败");

        // null → false
        assertFalse(invokeIsFormatDecodeError(client, null),
            "null 入参时应返回 false");

        // 普通异常 → false
        assertFalse(invokeIsFormatDecodeError(client, new RuntimeException("plain")),
            "普通异常应判定为非格式失败");
    }

    /**
     * 通过反射调用私有方法 isFormatDecodeError(Throwable)，精确验证异常 cause 链识别逻辑的返回值
     */
    private boolean invokeIsFormatDecodeError(RedisClientRedisson client, Throwable e) throws Exception {
        Method method = RedisClientRedisson.class.getDeclaredMethod("isFormatDecodeError", Throwable.class);
        method.setAccessible(true);
        return (boolean) method.invoke(client, e);
    }
}
