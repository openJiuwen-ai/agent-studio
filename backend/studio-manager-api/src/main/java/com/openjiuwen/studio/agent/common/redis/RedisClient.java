/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import com.openjiuwen.studio.agent.common.redis.exception.CapabilityUnsupportedException;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * RedisClient接口，有不同的实现：Redisson、内存（UT使用）、企业自研 Provider。
 *
 * 本接口为 Provider SPI 的核心契约（零 Redisson 依赖）：
 * - 值统一按 String 读写；编解码差异由实现内部消化。
 * - 原文读取场景（溢出清理等）使用 {@link #getRaw(String)}。
 * - 历史死接口（setObj / scoredSorted*）已 default 化，不计入自研 Provider 强制实现面。
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
     * 原文读取：绕过值解码（如 JSON 编解码、双编码还原）直接取存储原文。
     * 供溢出清理等需要原始字节数据的场景使用。
     *
     * @param key 键
     * @return 存储原文；key 不存在时返回 null
     */
    default String getRaw(String key) {
        // default 回退 get：本方法为 PR 内新增，不带 default 会破坏按旧接口
        // 编译的存量实现（legacy RedisClient3rd）二进制兼容——未覆写时首次
        // 调用抛 AbstractMethodError，该 Error 会击穿 catch(Exception) 防线
        return get(key);
    }

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
     * @deprecated 主业务树零调用，属死接口，已 default 化（不计入自研 Provider 强制实现面）。
     *             未覆写的实现调用时抛 {@link CapabilityUnsupportedException}。
     */
    @Deprecated
    default void setObj(String key, Object value) {
        throw new CapabilityUnsupportedException(
            "setObj is a deprecated dead operation, not implemented by this provider: " + key);
    }

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
     * @deprecated 主业务树零调用，属死接口，已 default 化。未覆写的实现调用时抛 {@link CapabilityUnsupportedException}。
     */
    @Deprecated
    default void scoredSortedSet(String key, Long timeStamp, String str) {
        throw new CapabilityUnsupportedException(
            "scoredSortedSet is a deprecated dead operation, not implemented by this provider: " + key);
    }

    /**
     * 获取redis有序集合中，指定score范围内的元素列表
     *
     * @param key key
     * @param startTime startTime
     * @param endTime endTime
     * @return List<String> list
     * @deprecated 主业务树零调用，属死接口，已 default 化。未覆写的实现调用时抛 {@link CapabilityUnsupportedException}。
     */
    @Deprecated
    default List<String> scoredSortedGet(String key, Long startTime, Long endTime) {
        throw new CapabilityUnsupportedException(
            "scoredSortedGet is a deprecated dead operation, not implemented by this provider: " + key);
    }

    /**
     * redis有序集合中，删除指定score范围内的元素列表
     *
     * @param key key
     * @param startTime startTime
     * @param endTime endTime
     * @deprecated 主业务树零调用，属死接口，已 default 化。未覆写的实现调用时抛 {@link CapabilityUnsupportedException}。
     */
    @Deprecated
    default void scoredSortedRemoveList(String key, Long startTime, Long endTime) {
        throw new CapabilityUnsupportedException(
            "scoredSortedRemoveList is a deprecated dead operation, not implemented by this provider: " + key);
    }

    /**
     * redis有序集合中，删除指定元素
     *
     * @param key key
     * @param str str
     * @deprecated 主业务树零调用，属死接口，已 default 化。未覆写的实现调用时抛 {@link CapabilityUnsupportedException}。
     */
    @Deprecated
    default void scoredSortedRemove(String key, String str) {
        throw new CapabilityUnsupportedException(
            "scoredSortedRemove is a deprecated dead operation, not implemented by this provider: " + key);
    }

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
