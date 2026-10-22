/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.common.redis.spi;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * getRawConfig 类型契约（review 修复回归锁）：
 * 泛型擦除下 (T) 强转不在本方法内抛 CCE，必须按 defaultValue 运行时类型显式校验
 * （JSON 数字 Integer 传 Long 锚点等错配须返回默认值而非调用方裸 CCE）；
 * null 值配置项被剔除（Map.copyOf 拒绝 null 的显式契约）。
 */
class RedisProviderContextRawConfigTest {

    private RedisProviderContext contextWith(Map<String, Object> raw) {
        return new RedisProviderContext.Builder().rawConfig(raw).build();
    }

    @Test
    void typeMismatch_returnsDefault_notCallerCce() {
        // Jackson 解析 JSON 数字 500 得 Integer；Long 锚点不得在调用方炸 CCE
        Map<String, Object> raw = new HashMap<>();
        raw.put("timeoutMs", 500);
        RedisProviderContext ctx = contextWith(raw);

        Long value = ctx.getRawConfig("timeoutMs", 1000L);
        assertEquals(1000L, value);
    }

    @Test
    void typeMatch_returnsValue() {
        Map<String, Object> raw = new HashMap<>();
        raw.put("logCommands", Boolean.TRUE);
        raw.put("port", 6379);
        RedisProviderContext ctx = contextWith(raw);

        assertEquals(Boolean.TRUE, ctx.getRawConfig("logCommands", Boolean.FALSE));
        assertEquals(6379, ctx.getRawConfig("port", 0));
    }

    @Test
    void missingOrNullKey_returnsDefault() {
        Map<String, Object> raw = new HashMap<>();
        raw.put("absent", null); // null 值项被剔除
        RedisProviderContext ctx = contextWith(raw);

        assertEquals("fallback", ctx.getRawConfig("absent", "fallback"));
        assertEquals("fallback", ctx.getRawConfig("never-set", "fallback"));
        assertEquals(30L, ctx.getRawConfig("never-set", 30L));
    }

    @Test
    void nullValueInRawConfig_isFilteredNotNpe() {
        Map<String, Object> raw = new HashMap<>();
        raw.put("appId", "x");
        raw.put("passport", null);
        RedisProviderContext ctx = contextWith(raw);

        Map<String, Object> view = ctx.getRawConfigMap();
        assertEquals(1, view.size());
        assertEquals("x", view.get("appId"));
    }

    @Test
    void nullDefault_returnsNullWithoutTypeCheck() {
        Map<String, Object> raw = new HashMap<>();
        raw.put("k", "v");
        RedisProviderContext ctx = contextWith(raw);

        // defaultValue 为 null 时无类型锚点，原样返回 null default（调用方自行处理）
        assertNull(ctx.getRawConfig("k", null));
    }
}
