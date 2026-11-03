/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * 能力未支持：调用了 Provider 未实现 / 未声明 / 已 Deprecated 的能力
 * （对齐 Python 260007）。
 */
public class CapabilityUnsupportedException extends RedisAccessException {

    public CapabilityUnsupportedException(String message) {
        super(message, null, null, null);
    }

    public CapabilityUnsupportedException(String message, Throwable cause,
            String redisKey, String operation) {
        super(message, cause, redisKey, operation);
    }
}
