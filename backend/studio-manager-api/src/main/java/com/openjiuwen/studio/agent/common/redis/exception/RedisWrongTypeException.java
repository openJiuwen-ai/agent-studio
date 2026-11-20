/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * WRONGTYPE：对持有错误类型值的 key 执行命令（对齐 Python 260006）。
 */
public class RedisWrongTypeException extends RedisCommandException {

    public RedisWrongTypeException(String message) {
        super(message, null, null, null);
    }

    public RedisWrongTypeException(String message, Throwable cause,
            String redisKey, String operation) {
        super(message, cause, redisKey, operation);
    }
}
