/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * Redis 客户端能力抽象接口（平台缓存适配层契约）。
 *
 * <p><b>能力面</b>：以平台实际使用的 Redis 命令与语义为限定义（KV、TTL、有序集合、List、
 * 计数器、分布式锁、按前缀删除等），不绑定具体 Redis 客户端实现与协议细节。
 *
 * <p><b>实现方式</b>：
 * <ul>
 *   <li>{@code RedisClientRedisson}：默认原生实现（单机/集群/哨兵）</li>
 *   <li>{@code RedisClientMemory}：内存实现（仅用于单元测试，语义与本契约对齐）</li>
 *   <li>企业自研实现：通过 {@code RedisClientProvider} 插件机制接入，见 provider 包契约文档</li>
 * </ul>
 *
 * <p><b>统一契约（前置条件与错误分类）</b>：
 * <ul>
 *   <li>前置条件：{@code key} 必须非 null（实现方可直接抛出 {@link NullPointerException}
 *       或自行兜底，不做静默吞并）；value 允许为 null 的方法在 Javadoc 中单独说明</li>
 *   <li>错误分类（三层，由包装层 {@code RedisClientWrapper} 统一处理）：
 *     <ol>
 *       <li>读取溢出（读取内容超出解码约束）：抛出 {@code RedisReadOverflowException}，
 *           由调用方决定清理降级策略</li>
 *       <li>数据解码失败（存量数据格式损坏/不兼容）：记录告警并降级返回 null，不影响主流程</li>
 *       <li>连接/超时等运行时故障：记录错误并降级（读操作返回 null / 写操作静默失败），
 *           要求调用方在 Redis 故障时具备服务降级能力</li>
 *     </ol>
 *   </li>
 *   <li>未经过包装层的裸实现应将底层异常原样抛出，错误分类由包装层完成</li>
 *   <li>线程安全：实现必须线程安全</li>
 *   <li>所有 TTL 参数必须为正数；{@code Duration} 为 0 或负数的行为未定义</li>
 * </ul>
 */
public interface RedisClient {
    /**
     * 检查给定 key 是否存在。
     *
     * <p>语义：等价于 Redis EXISTS。key 已过期（TTL 归零）视为不存在。
     *
     * @param key 键（非 null）
     * @return 存在返回<code>true</code>，不存在返回<code>false</code>
     */
    boolean exists(String key);

    /**
     * 返回 key 所关联的字符串值（对象解码主路径）。
     *
     * <p>语义：等价于 Redis GET。默认实现方按自身默认编解码器解码为字符串；
     * 当存量数据格式与默认编解码器不兼容时，实现方允许回退到原始字符串读取（见 {@link #getRaw}），
     * 但读取溢出与连接故障不得回退，必须按错误分类契约抛出。
     *
     * @param key 键（非 null）
     * @return 当 key 不存在时返回 null ，否则，返回 key 的值。
     */
    String get(String key);

    /**
     * 返回 key 所关联的原始字符串值（绕过对象解码）。
     *
     * <p>语义：以字符串原样读取 value，不经过实现方的对象编解码器，供溢出清理等
     * 场景读取超长原始数据；双编码数据应还原为 JSON 原文。
     *
     * <p>默认实现回退到 {@link #get(String)}（适用于无对象编解码层的实现方）；
     * 存在独立对象编解码层的实现方（如 Redisson JsonJacksonCodec）必须覆写本方法。
     *
     * @param key 键（非 null）
     * @return 原始字符串值，key 不存在时返回 null
     */
    default String getRaw(String key) {
        return get(key);
    }

    /**
     * 将字符串值 value 关联到 key，并设置生存时间。
     * 该方法实现需要使用同步写入（重要！！！）
     *
     * <p>语义：等价于 Redis SET key value EX。重复 set 覆盖旧值并重置 TTL；
     * key 已存在关联的 List/zset 等其他类型结构时行为未定义（调用方需保证类型一致）。
     *
     * @param key 键（非 null）
     * @param value 值
     * @param duration 生存时间（正数）
     */
    void set(String key, String value, Duration duration);

    /**
     * 将字符串值 value 关联到 key（无生存时间，永久存储）。
     *
     * <p>语义：等价于 Redis SET key value。重复 set 覆盖旧值且清除已有 TTL。
     *
     * @param key 键（非 null）
     * @param value 值
     */
    void set(String key, String value);

    /**
     * 将指定对象序列化后存储（JSON 字符串形式）。
     *
     * <p>语义：对象序列化为 JSON 后写入（等价于 set(key, json)，无 TTL）。
     * 读取方通过 {@link #get(String)} 获取 JSON 字符串后自行反序列化。
     *
     * @param key   用于标识值的键（非 null）
     * @param value 与键关联的对象
     */
    void setObj(String key, Object value);

    /**
     * 为给定 key 设置生存时间，当 key 过期时(生存时间为0)，它会被自动删除。
     *
     * <p>语义：等价于 Redis EXPIRE。
     *
     * @param key 键（非 null）
     * @param duration 生存时间（正数）
     * @return 设置成功返回<code>true</code>。当key不存在或者不能为key设置生存时间时返回<code>false</code>
     */
    boolean expire(String key, Duration duration);

    /**
     * 删除给定的 key 。 不存在的 key 会被忽略。
     *
     * <p>语义：等价于 Redis DEL。
     *
     * @param key 键（非 null）
     * @return key存在并删除成功返回<code>true</code>，key不存在返回<code>false</code>
     */
    boolean delete(String key);

    /**
     * 设置redis的有序集合，timeStamp:value。
     *
     * <p>语义：等价于 Redis ZADD：member 已存在时更新其 score；member 与 score 均未变化时为幂等操作。
     *
     * @param key 键（非 null）
     * @param timeStamp 分数（score）
     * @param str 成员（member）
     */
    void scoredSortedSet(String key, Long timeStamp, String str);

    /**
     * 获取redis有序集合中，指定score范围内的元素列表（按 score 升序，边界含端点）。
     *
     * <p>语义：等价于 Redis ZRANGEBYSCORE min max。key 不存在时返回空列表。
     *
     * @param key key
     * @param startTime score 下界（含）
     * @param endTime score 上界（含）
     * @return List<String> list
     */
    List<String> scoredSortedGet(String key, Long startTime, Long endTime);

    /**
     * redis有序集合中，删除指定score范围内的元素列表（边界含端点）。
     *
     * <p>语义：等价于 Redis ZREMRANGEBYSCORE min max。key 不存在时为幂等操作。
     *
     * @param key key
     * @param startTime score 下界（含）
     * @param endTime score 上界（含）
     */
    void scoredSortedRemoveList(String key, Long startTime, Long endTime);

    /**
     * redis有序集合中，删除指定元素。
     *
     * <p>语义：等价于 Redis ZREM。member 不存在时为幂等操作。
     *
     * @param key key
     * @param str 成员（member）
     */
    void scoredSortedRemove(String key, String str);

    /**
     * 返回 key列表 所关联的字符串值列表（批量读取）。
     *
     * <p>语义：等价于 Redis MGET，返回结果仅包含实际存在的 key（值为实现方解码后的对象），
     * 不存在的 key不出现在结果 Map 中。
     *
     * @param keyList keyList（非 null）
     * @return 存在的 key → 值 的 Map；全部不存在时返回空 Map
     */
    Map<String, Object> getAll(List<String> keyList);

    /**
     * 获取分布式锁。
     *
     * <p>语义：等价于 Redis SETNX 语义的可重入锁；锁的互斥性以 key 为粒度，
     * 由实现方保证同 key 互斥。返回的锁对象必须先 tryLock 成功后才能 unlock。
     *
     * @param key 键（非 null）
     * @return RedisLock
     */
    RedisLock getLock(String key);

    /**
     * 增量加1（计数器，带生存时间）。
     *
     * <p>语义：等价于 Redis INCRBY key 1 并首次创建时设置 TTL；
     * key 因 TTL 过期后再次调用从 0 重新开始。
     *
     * @param key 键（非 null）
     * @param timeoutSeconds 数据超时时间
     * @return 加1之前数据
     */
    long getAndIncrement(String key, long timeoutSeconds);

    /**
     * 增加并获取更新后的值（计数器，带生存时间）。
     *
     * <p>语义：等价于 Redis INCRBY key delta（delta=0 时仅读取当前值）；
     * key 因 TTL 过期后再次调用从 0 重新开始。
     *
     * @param key key
     * @param dela 增加值
     * @param timeoutSeconds 过期时间
     * @return 更新后值
     */
    long addAndGet(String key, long dela, long timeoutSeconds);

    /**
     * 按 key 前缀删除所有匹配的键（覆盖 KV/List/zset/计数器等全部结构）。
     *
     * <p>语义：等价于 KEYS prefix* + 批量 DEL；生产实现方应使用 SCAN 渐进式扫描避免阻塞。
     *
     * @param prefix 键前缀（非 null）
     */
    void deleteByPrefix(String prefix);

    /**
     * 向 Redis List 追加元素（RPUSH）。若 key 不存在则创建，并按 duration 设置生存时间。
     * 用于调试记录事件流的增量追加，避免将整个 eventList 序列化为单个大 String 导致的 O(N²) 读写阻塞。
     *
     * <p>语义：等价于 Redis RPUSH + EXPIRE（每次追加后刷新 TTL，活跃事件流保活）。
     *
     * @param key      键（非 null）
     * @param values   要追加的元素列表（null 或空列表时仅刷新 TTL）
     * @param duration 生存时间（正数）
     */
    void rPushAll(String key, List<String> values, Duration duration);

    /**
     * 获取 Redis List 指定范围的元素（LRANGE）。end=-1 表示取到末尾。
     *
     * <p>语义：等价于 Redis LRANGE，索引支持负数（从末尾计数）。
     *
     * @param key   键（非 null）
     * @param start 起始索引（含）
     * @param end   结束索引（含），-1 表示末尾
     * @return 元素列表，key 不存在时返回空列表
     */
    List<String> lRange(String key, int start, int end);

    /**
     * 裁剪 Redis List，只保留 [start, end] 范围内的元素（LTRIM）。end=-1 表示到末尾。
     *
     * <p>语义：等价于 Redis LTRIM，索引支持负数（从末尾计数）。key 不存在时为幂等操作。
     *
     * @param key   键（非 null）
     * @param start 起始索引（含）
     * @param end   结束索引（含），-1 表示末尾
     */
    void lTrim(String key, int start, int end);

    /**
     * 获取 Redis List 的长度（LLEN）。
     *
     * @param key 键（非 null）
     * @return 列表长度，key 不存在时返回 0
     */
    long lLen(String key);

    /**
     * 设置值，并保持 ttl 不变。
     *
     * <p>语义：等价于 Redis SET key value KEEPTTL：
     * <ul>
     *   <li>key 存在且剩余 TTL 小于 initialDuration：写入新值并保持剩余 TTL</li>
     *   <li>key 不存在、无 TTL 或剩余 TTL 不小于 initialDuration：写入新值并按 initialDuration 重置</li>
     * </ul>
     *
     * @param key 键（非 null）
     * @param value 值
     * @param initialDuration 最开始设置的 ttl
     */
    default void setAndKeepTtl(String key, String value, Duration initialDuration) {
        set(key, value, initialDuration);
    }
}
