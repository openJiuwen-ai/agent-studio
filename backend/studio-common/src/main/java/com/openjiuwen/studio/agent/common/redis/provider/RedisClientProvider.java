/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.provider;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;

/**
 * Redis 客户端 Provider 插件接口（Redis 适配层 SPI）。
 *
 * <p>企业自研 Redis（自研代理、改造集群、自定义认证链路等）通过实现本接口接入平台，
 * 无需 fork 修改框架源码。接入方式（任选其一）：
 * <ul>
 *   <li><b>ServiceLoader 插件包</b>：实现类以无参构造注册到
 *       {@code META-INF/services/com.openjiuwen.studio.agent.common.redis.provider.RedisClientProvider}，
 *       配置 {@code redis.provider.type=&lt;name()&gt;} 启用</li>
 *   <li><b>显式类名</b>：配置 {@code redis.provider.class=&lt;实现类全限定名&gt;}
 *       （实现类需提供无参构造），优先级最高</li>
 * </ul>
 *
 * <p><b>实现契约</b>：
 * <ul>
 *   <li>{@link #name()} 返回全局唯一的 provider 标识（小写字母、数字、中划线；内置标识
 *       {@code redisson} / {@code memory} 不可复用）；平台用其在 ServiceLoader 注册表中定位</li>
 *   <li>{@link #createClient(RedisClientConfig)} 返回的 {@link RedisClient} 必须满足
 *       RedisClient 接口的完整契约（方法语义、错误分类、前置条件），并通过一致性测试套件
 *       （TCK：{@code studio-common} 测试源码 tck 包）自验证</li>
 *   <li>实现必须线程安全；{@code createClient} 在应用生命周期内通常只调用一次</li>
 *   <li>客户端连接的创建、关闭等生命周期由 Provider 实现方自行管理（建议惰性连接）</li>
 *   <li>底层异常应原样抛出（不做吞并），由平台包装层统一做错误分类与降级</li>
 * </ul>
 */
public interface RedisClientProvider {
    /**
     * Provider 唯一标识（用于配置 {@code redis.provider.type} 匹配）。
     *
     * @return 全局唯一标识，如 "redisson" / "memory" / 企业自定义标识
     */
    String name();

    /**
     * 创建 Redis 客户端实例。
     *
     * <p>注意：返回裸客户端（无需自行包装），平台会统一套上
     * {@code RedisClientWrapper}（耗时日志 + 错误分类降级）。
     *
     * @param config Redis 连接配置（单机/集群/哨兵地址、密码等；实现方按需取用）
     * @return RedisClient 实例（非 null）
     */
    RedisClient createClient(RedisClientConfig config);
}
