/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

/**
 * FEAT-134 McpToolFetchResult 单元测试。
 *
 * 核心语义：区分「合法空工具列表」与「失败」（L2 §5.4 / §8.2）。
 */
@DisplayName("McpToolFetchResult")
class McpToolFetchResultTest {

    @Test
    @DisplayName("ok() 构造成功结果")
    void okConstruction() {
        List<Map<String, Object>> tools = List.of(Map.of("name", "tool1"));
        McpToolFetchResult result = McpToolFetchResult.ok(tools);
        assertTrue(result.success());
        assertEquals(1, result.tools().size());
        assertNull(result.errorCode());
        assertNull(result.safeReason());
    }

    @Test
    @DisplayName("ok() 空列表也是合法成功（空工具≠失败）")
    void emptyOkIsSuccess() {
        McpToolFetchResult result = McpToolFetchResult.ok(List.of());
        assertTrue(result.success());
        assertEquals(0, result.tools().size());
    }

    @Test
    @DisplayName("fail() 构造失败结果")
    void failConstruction() {
        McpToolFetchResult result = McpToolFetchResult.fail("1149", "connection refused");
        assertEquals(false, result.success());
        assertEquals(0, result.tools().size());
        assertEquals("1149", result.errorCode());
        assertEquals("connection refused", result.safeReason());
    }

    @Test
    @DisplayName("fail() 工具列表始终为空")
    void failToolsAlwaysEmpty() {
        McpToolFetchResult result = McpToolFetchResult.fail("1150", "timeout");
        assertTrue(result.tools().isEmpty());
    }
}
