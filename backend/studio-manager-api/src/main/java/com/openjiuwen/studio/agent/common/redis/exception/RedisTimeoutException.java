/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * Redis 超时。
 *
 * 语义：对写/计数类操作，超时后**结果可能未知**（命令可能已生效），
 * 调用方禁止盲目重试（对齐 Python 260004）。
 */
public class RedisTimeoutException extends RedisAccessException {

    public RedisTimeoutException(String message) {
        super(message, null, null, null);
    }

    public RedisTimeoutException(String message, Throwable cause,
            String redisKey, String operation) {
        super(message, cause, redisKey, operation);
    }
}
