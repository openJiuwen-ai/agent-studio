/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * Redis 连接失败（含认证失败）：连不上 / 网络故障 / 认证不通过。
 *
 * 语义：可重试、可降级（对齐 Python 260002/260003）。
 */
public class RedisConnectionFailureException extends RedisAccessException {

    public RedisConnectionFailureException(String message) {
        super(message, null, null, null);
    }

    public RedisConnectionFailureException(String message, Throwable cause,
            String redisKey, String operation) {
        super(message, cause, redisKey, operation);
    }
}
