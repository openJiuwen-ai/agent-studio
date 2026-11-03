/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.exception;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.agent.common.redis.RedisReadOverflowException;
import com.openjiuwen.studio.agent.common.redis.spi.RedisProviderException;

import org.junit.jupiter.api.Test;

/**
 * J4 异常体系：分类器字符串匹配规则 + 既有异常归族 + 上下文携带。
 */
class RedisExceptionClassifierTest {

    /** 模拟 Redisson 异常类名（SPI 零 Redisson 依赖，用同名局部类验证类名匹配） */
    static class RedisConnectionException extends RuntimeException {
        RedisConnectionException(String m) {
            super(m);
        }
    }

    static class RedisResponseTimeoutException extends RuntimeException {
        RedisResponseTimeoutException(String m) {
            super(m);
        }
    }

    static class RedisAuthException extends RuntimeException {
        RedisAuthException(String m) {
            super(m);
        }
    }

    @Test
    void classify_alreadyFamily_returnsSameInstance() {
        RedisAccessException original = new RedisTimeoutException("t", null, "k", "op");
        assertSame(original, RedisExceptionClassifier.classify(original, "op", "k"));
    }

    @Test
    void classify_connectionByName() {
        RedisAccessException translated =
            RedisExceptionClassifier.classify(new RedisConnectionException("refused"), "get", "k1");
        assertInstanceOf(RedisConnectionFailureException.class, translated);
        assertEquals("k1", translated.getRedisKey());
        assertEquals("get", translated.getOperation());
        assertEquals("CONNECTION", RedisExceptionClassifier.categoryOf(translated));
    }

    @Test
    void classify_authByName_mapsToConnection() {
        RedisAccessException translated =
            RedisExceptionClassifier.classify(new RedisAuthException("denied"), "get", null);
        assertInstanceOf(RedisConnectionFailureException.class, translated);
    }

    @Test
    void classify_timeoutByName() {
        RedisAccessException translated =
            RedisExceptionClassifier.classify(new RedisResponseTimeoutException("slow"), "set", "k2");
        assertInstanceOf(RedisTimeoutException.class, translated);
        assertEquals("TIMEOUT", RedisExceptionClassifier.categoryOf(translated));
    }

    @Test
    void classify_wrongTypeByMessage() {
        RedisAccessException translated = RedisExceptionClassifier.classify(
            new RuntimeException("WRONGTYPE Operation against a key holding the wrong kind of value"),
            "hgetall", "k3");
        assertInstanceOf(RedisWrongTypeException.class, translated);
        assertEquals("WRONGTYPE", RedisExceptionClassifier.categoryOf(translated));
    }

    @Test
    void classify_noScriptByMessage_mapsToCommand() {
        RedisAccessException translated =
            RedisExceptionClassifier.classify(new RuntimeException("NOSCRIPT no script"), "eval", null);
        assertInstanceOf(RedisCommandException.class, translated);
        assertEquals("COMMAND", RedisExceptionClassifier.categoryOf(translated));
    }

    @Test
    void classify_unsupportedOperation_mapsToCapability() {
        RedisAccessException translated = RedisExceptionClassifier.classify(
            new UnsupportedOperationException("nope"), "setObj", "k4");
        assertInstanceOf(CapabilityUnsupportedException.class, translated);
        assertEquals("CAPABILITY", RedisExceptionClassifier.categoryOf(translated));
    }

    @Test
    void classify_unknown_mapsToRoot() {
        RedisAccessException translated =
            RedisExceptionClassifier.classify(new RuntimeException("whatever"), "expire", "k5");
        assertInstanceOf(RedisAccessException.class, translated);
        assertEquals(RedisAccessException.class, translated.getClass());
        assertEquals("ACCESS", RedisExceptionClassifier.categoryOf(translated));
    }

    @Test
    void readOverflowException_isCommandFamily_withContext() {
        RedisReadOverflowException ex = new RedisReadOverflowException("bigkey", new RuntimeException("c"));
        assertInstanceOf(RedisCommandException.class, ex);
        assertEquals("bigkey", ex.getRedisKey());
        assertEquals("get", ex.getOperation());
        assertTrue(ex.getMessage().contains("bigkey"));
    }

    @Test
    void providerException_isAccessFamily() {
        RedisProviderException ex = new RedisProviderException("load failed");
        assertInstanceOf(RedisAccessException.class, ex);
        assertEquals("provider", ex.getOperation());
    }
}
