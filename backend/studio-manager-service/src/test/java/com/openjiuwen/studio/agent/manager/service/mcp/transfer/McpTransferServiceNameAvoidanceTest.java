/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

/**
 * FEAT-134 名称避让单元测试。
 *
 * 规则（2026-11-21 用户裁定：纯数字后缀，不带"导入"字样）：
 * 原名未被占用时直接沿用；冲突时追加 -1、-2 递增直到唯一；
 * 大小写不敏感；先截断基础名称保留完整数字后缀，64 字符上限。
 */
@DisplayName("McpTransferService.allocateName")
class McpTransferServiceNameAvoidanceTest {

    private static final int NAME_MAX = 64;

    @Test
    @DisplayName("无冲突时直接沿用原名（不加任何后缀）")
    void noConflictKeepsOriginal() {
        Set<String> used = new HashSet<>();
        String result = McpTransferService.allocateName("test", used);
        assertEquals("test", result);
        assertTrue(used.contains("test"));
    }

    @Test
    @DisplayName("原名冲突时追加 -1")
    void singleConflict() {
        Set<String> used = new HashSet<>(Set.of("test"));
        String result = McpTransferService.allocateName("test", used);
        assertEquals("test-1", result);
    }

    @Test
    @DisplayName("多次冲突递增到 -N（-1/-2/-3 被占则取 -4）")
    void multipleConflicts() {
        Set<String> used = new HashSet<>(Set.of("test", "test-1", "test-2", "test-3"));
        String result = McpTransferService.allocateName("test", used);
        assertEquals("test-4", result);
    }

    @Test
    @DisplayName("大小写不敏感避让：已有 test 时 Test 也避让")
    void caseInsensitive() {
        // used 集合由 loadWorkspaceNames 以 toLowerCase 形态填入
        Set<String> used = new HashSet<>(Set.of("test"));
        String result = McpTransferService.allocateName("Test", used);
        assertEquals("Test-1", result);
    }

    @Test
    @DisplayName("长名称截断保留完整数字后缀（总长不超过 64）")
    void longNameTruncated() {
        // 70 字符的基础名称（超校验上限，仅测避让算法的截断路径），且已被占用迫使加后缀
        String longName = "a".repeat(70);
        Set<String> used = new HashSet<>(Set.of(longName));
        String result = McpTransferService.allocateName(longName, used);
        assertTrue(result.length() <= NAME_MAX, "result length " + result.length() + " > " + NAME_MAX);
        assertTrue(result.endsWith("-1"));
        // 基础名称被截断到 62 字符再拼 "-1"（总长 64）
        assertTrue(result.startsWith("a".repeat(NAME_MAX - "-1".length())));
    }

    @Test
    @DisplayName("本批次内同名连续分配：第一次原名、第二次 -1")
    void batchDuplicates() {
        Set<String> used = new HashSet<>();
        String first = McpTransferService.allocateName("test", used);
        String second = McpTransferService.allocateName("test", used);
        assertEquals("test", first);
        assertEquals("test-1", second);
        assertNotEquals(first, second);
    }

    @Test
    @DisplayName("英文名同样数字避让（name_en 与 name 同规则）")
    void englishNameNumericSuffix() {
        // used 集合以 toLowerCase 形态存入
        Set<String> used = new HashSet<>(Set.of("testservice"));
        String result = McpTransferService.allocateName("TestService", used);
        assertEquals("TestService-1", result);
    }

    @Test
    @DisplayName("极限长名称（64）+ 递增后缀仍不超过 64")
    void longNameWithIncrement() {
        // 64 字符为校验允许的最大长度（validateDefinition 2~64）
        String longName = "b".repeat(NAME_MAX);
        Set<String> used = new HashSet<>();
        String first = McpTransferService.allocateName(longName, used);
        String second = McpTransferService.allocateName(longName, used);
        String third = McpTransferService.allocateName(longName, used);
        assertTrue(first.length() <= NAME_MAX);
        assertTrue(second.length() <= NAME_MAX);
        assertTrue(third.length() <= NAME_MAX);
        assertNotEquals(first, second);
        assertNotEquals(second, third);
    }
}
