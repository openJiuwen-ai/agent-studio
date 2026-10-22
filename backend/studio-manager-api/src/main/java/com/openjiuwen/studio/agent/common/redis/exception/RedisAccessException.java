/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * Redis 访问异常根（J4 异常体系）。
 *
 * 携带 redisKey / operation 上下文便于日志排查。子类语义对齐 Python 侧
 * redis_spi.exceptions 的 260000 段分类（见 interface_contract.md §3）：
 * 连接失败（可重试/可降级）、超时（写结果可能未知，禁止盲重试）、
 * 命令错误（调用方错误，含 WRONGTYPE）、能力未支持、Provider 装配失败。
 *
 * 落地原则（Q12 拍板）：RedisClientWrapper 现有降级行为不变——
 * 本族供需要区分异常的调用方与自研 Provider 边界翻译使用。
 */
public class RedisAccessException extends RuntimeException {

    /** 关联的 Redis key（可空：无 key 上下文的操作） */
    private final String redisKey;

    /** 操作名（可空：如 "get" / "pipeline.execute" / "provider"） */
    private final String operation;

    public RedisAccessException(String message) {
        this(message, null, null, null);
    }

    public RedisAccessException(String message, Throwable cause) {
        this(message, cause, null, null);
    }

    public RedisAccessException(String message, Throwable cause, String redisKey, String operation) {
        super(message, cause);
        this.redisKey = redisKey;
        this.operation = operation;
    }

    public String getRedisKey() {
        return redisKey;
    }

    public String getOperation() {
        return operation;
    }
}
