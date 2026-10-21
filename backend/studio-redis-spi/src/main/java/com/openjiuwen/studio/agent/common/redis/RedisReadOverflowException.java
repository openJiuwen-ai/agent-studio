/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import com.openjiuwen.studio.agent.common.redis.exception.RedisCommandException;

/**
 * Redis 读取溢出异常，当 Redis 中的数据超过 Jackson StreamReadConstraints 限制时抛出。
 *
 * J4 归族：语义属命令错误（{@link RedisCommandException} 子类），
 * 既有 catch（按本类型捕获）不受影响。
 */
public class RedisReadOverflowException extends RedisCommandException {

    public RedisReadOverflowException(String redisKey, Throwable cause) {
        super("Redis read overflow for key: " + redisKey, cause, redisKey, "get");
    }
}
