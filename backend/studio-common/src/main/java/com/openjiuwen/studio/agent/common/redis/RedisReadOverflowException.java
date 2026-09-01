/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis;

import lombok.Getter;

/**
 * Redis 读取溢出异常，当 Redis 中的数据超过 Jackson StreamReadConstraints 限制时抛出
 *
 */
@Getter
public class RedisReadOverflowException extends RuntimeException {
    private final String redisKey;

    public RedisReadOverflowException(String redisKey, Throwable cause) {
        super("Redis read overflow for key: " + redisKey, cause);
        this.redisKey = redisKey;
    }

}
