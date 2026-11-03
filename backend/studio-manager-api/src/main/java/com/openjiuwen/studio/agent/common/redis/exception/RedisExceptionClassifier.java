/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

/**
 * Redis 异常分类器（J4）。
 *
 * 基于类名与消息的字符串匹配将底层客户端异常翻译为 J4 异常族——
 * SPI 模块零 Redisson 依赖，天然适用于任何自研 Provider 的边界翻译
 * （企业 Provider 也可在自身边界直接抛 J4 族绕过本分类器）。
 *
 * 匹配规则（自上而下）：
 * 1. 已是 RedisAccessException 族 → 原样返回；
 * 2. 类名含 RedisConnection / RedisAuth → 连接失败；
 * 3. 类名含 Timeout → 超时（写/计数结果可能未知，禁止盲重试）；
 * 4. 消息含 WRONGTYPE → WRONGTYPE（命令错误子类）；
 * 5. 消息含 NOSCRIPT 或类名含 Script → 命令错误（脚本语义）；
 * 6. UnsupportedOperationException / 消息含 not supported / unsupported → 能力未支持；
 * 7. 其余 → RedisAccessException 根。
 */
public final class RedisExceptionClassifier {

    private RedisExceptionClassifier() {
    }

    /**
     * 翻译为 J4 异常族实例（保留 cause 链与 key/operation 上下文）。
     */
    public static RedisAccessException classify(Throwable cause, String operation, String redisKey) {
        if (cause instanceof RedisAccessException) {
            return (RedisAccessException) cause;
        }
        String message = String.valueOf(cause.getMessage());
        String className = cause.getClass().getName();

        if (className.contains("RedisConnection") || className.contains("RedisAuth")) {
            return new RedisConnectionFailureException(message, cause, redisKey, operation);
        }
        if (className.contains("Timeout")) {
            return new RedisTimeoutException(message, cause, redisKey, operation);
        }
        String upper = message.toUpperCase();
        if (upper.contains("WRONGTYPE")) {
            return new RedisWrongTypeException(message, cause, redisKey, operation);
        }
        if (upper.contains("NOSCRIPT") || className.contains("Script")) {
            return new RedisCommandException(message, cause, redisKey, operation);
        }
        if (cause instanceof UnsupportedOperationException
                || upper.contains("NOT SUPPORTED")
                || upper.contains("UNSUPPORTED")) {
            return new CapabilityUnsupportedException(message, cause, redisKey, operation);
        }
        return new RedisAccessException(message, cause, redisKey, operation);
    }

    /**
     * 短类别名（日志用）：CONNECTION / TIMEOUT / WRONGTYPE / COMMAND /
     * CAPACITY / ACCESS。
     */
    public static String categoryOf(Throwable cause) {
        if (cause instanceof RedisWrongTypeException) {
            return "WRONGTYPE";
        }
        if (cause instanceof RedisCommandException) {
            return "COMMAND";
        }
        if (cause instanceof RedisConnectionFailureException) {
            return "CONNECTION";
        }
        if (cause instanceof RedisTimeoutException) {
            return "TIMEOUT";
        }
        if (cause instanceof CapabilityUnsupportedException) {
            return "CAPABILITY";
        }
        return "ACCESS";
    }
}
