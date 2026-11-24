/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import org.redisson.client.codec.Codec;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * RedisClient接口，有不同的实现：Redisson、、内存（UT使用）
 *
 */
public interface RedisClient {
    /**
     * 检查给定 key 是否存在
     *
     * @param key 键
     * @return 存在返回<code>true</code>，不存在返回<code>false</code>
     */
    boolean exists(String key);

    /**
     * 返回 key 所关联的字符串值
     *
     * @param key 键
     * @return 当 key 不存在时，返回 null ，否则，返回 key 的值。
     */
    String get(String key);

    /**
     * 根据给定的键和编解码器获取字符串。
     *
     * @param key   用于查找值的键。
     * @param codec 用于解码值的编解码器。
     * @return 解码后的字符串。
     */
    String get(String key, Codec codec);

    /**
     * 将字符串值 value 关联到 key
     * 该方法实现需要使用同步写入（重要！！！）
     *
     * @param key 键
     * @param value 值
     * @param duration 生存时间
     */
    void set(String key, String value, Duration duration);

    /**
     * 将字符串值 value 关联到 key
     *
     * @param key 键
     * @param value 值
     */
    void set(String key, String value);

    /**
     * 将指定的键值对存储到对象中。
     *
     * @param key   用于标识值的键。
     * @param value 与键关联的对象。
     */
    void setObj(String key, Object value);

    /**
     * 为给定 key 设置生存时间，当 key 过期时(生存时间为0)，它会被自动删除
     *
     * @param key 键
     * @param duration 生存时间
     * @return 设置成功返回<code>true</code>。当key不存在或者不能为key设置生存时间时返回<code>false</code>
     */
    boolean expire(String key, Duration duration);

    /**
     * 删除给定的 key 。 不存在的 key 会被忽略
     *
     * @param key 键
     * @return key存在并删除成功返回<code>true</code>，否则返回<code>false</code>
     */
    boolean delete(String key);

    /**
     * 设置redis的有序集合，timeStamp:value
     *
     * @param key 键
     */
    void scoredSortedSet(String key, Long timeStamp, String str);

    /**
     * 获取redis有序集合中，指定score范围内的元素列表
     *
     * @param key key
     * @param startTime startTime
     * @param endTime endTime
     * @return List<String> list
     */
    List<String> scoredSortedGet(String key, Long startTime, Long endTime);

    /**
     * redis有序集合中，删除指定score范围内的元素列表
     *
     * @param key key
     * @param startTime startTime
     * @param endTime endTime
     */
    void scoredSortedRemoveList(String key, Long startTime, Long endTime);

    /**
     * redis有序集合中，删除指定元素
     *
     * @param key key
     * @param str str
     */
    void scoredSortedRemove(String key, String str);

    /**
     * 返回 key列表 所关联的字符串值列表
     *
     * @param keyList keyList
     * @return map
     */
    Map<String, Object> getAll(List<String> keyList);

    /**
     * 获取锁
     *
     * @param key 键
     * @return RedisLock
     */
    RedisLock getLock(String key);

    /**
     * 增量加1
     *
     * @param key 键
     * @param timeoutSeconds 数据超时时间
     * @return 加1之前数据
     */
    long getAndIncrement(String key, long timeoutSeconds);

    /**
     * 增加并获取更新后只
     *
     * @param key key
     * @param dela 增加值
     * @param timeoutSeconds 过期时间
     * @return 更新后值
     */
    long addAndGet(String key, long dela, long timeoutSeconds);

    void deleteByPrefix(String prefix);

    /**
     * 向 Redis List 追加元素（RPUSH）。若 key 不存在则创建，并按 duration 设置生存时间。
     * 用于调试记录事件流的增量追加，避免将整个 eventList 序列化为单个大 String 导致的 O(N²) 读写阻塞。
     *
     * @param key      键
     * @param values   要追加的元素列表
     * @param duration 生存时间
     */
    void rPushAll(String key, List<String> values, Duration duration);

    /**
     * 获取 Redis List 指定范围的元素（LRANGE）。end=-1 表示取到末尾。
     *
     * @param key   键
     * @param start 起始索引（含）
     * @param end   结束索引（含），-1 表示末尾
     * @return 元素列表，key 不存在时返回空列表
     */
    List<String> lRange(String key, int start, int end);

    /**
     * 裁剪 Redis List，只保留 [start, end] 范围内的元素（LTRIM）。end=-1 表示到末尾。
     *
     * @param key   键
     * @param start 起始索引（含）
     * @param end   结束索引（含），-1 表示末尾
     */
    void lTrim(String key, int start, int end);

    /**
     * 获取 Redis List 的长度（LLEN）。
     *
     * @param key 键
     * @return 列表长度，key 不存在时返回 0
     */
    long lLen(String key);

    /**
     * 设置值，并保持 ttl 不变
     *
     * @param key 键
     * @param value 值
     * @param initialDuration 最开始设置的 ttl
     */
    default void setAndKeepTtl(String key, String value, Duration initialDuration) {
        set(key, value, initialDuration);
    }
}
