/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * Redis 命令错误：WRONGTYPE / 参数错误 / 脚本错误等调用方错误
 * （对齐 Python 260005/260008）。
 */
public class RedisCommandException extends RedisAccessException {

    public RedisCommandException(String message) {
        super(message, null, null, null);
    }

    public RedisCommandException(String message, Throwable cause,
            String redisKey, String operation) {
        super(message, cause, redisKey, operation);
    }
}
