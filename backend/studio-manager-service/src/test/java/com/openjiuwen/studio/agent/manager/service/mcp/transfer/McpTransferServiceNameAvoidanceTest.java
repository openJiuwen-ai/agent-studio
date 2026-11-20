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
 * FEAT-134 名称避让（L2 §3.2）单元测试。
 *
 * 规则：当前空间大小写不敏感集合 + 本批次已分配名称；先截断基础名称
 * 保留完整后缀，-导入 / -导入-2 递增直到唯一；64 字符上限。
 */
@DisplayName("McpTransferService.allocateName")
class McpTransferServiceNameAvoidanceTest {

    private static final int NAME_MAX = 64;

    @Test
    @DisplayName("无冲突时直接加后缀")
    void noConflict() {
        Set<String> used = new HashSet<>();
        String result = McpTransferService.allocateName("test", used, "-导入");
        assertEquals("test-导入", result);
        assertTrue(used.contains("test-导入"));
    }

    @Test
    @DisplayName("同名单冲突时递增后缀 -导入-2")
    void singleConflict() {
        Set<String> used = new HashSet<>(Set.of("test-导入"));
        String result = McpTransferService.allocateName("test", used, "-导入");
        assertEquals("test-导入-2", result);
    }

    @Test
    @DisplayName("多次冲突递增到 -导入-N")
    void multipleConflicts() {
        Set<String> used = new HashSet<>(Set.of("test-导入", "test-导入-2", "test-导入-3"));
        String result = McpTransferService.allocateName("test", used, "-导入");
        assertEquals("test-导入-4", result);
    }

    @Test
    @DisplayName("大小写不敏感避让：已有 test-导入 时 Test 也会避让")
    void caseInsensitive() {
        // used 集合由 loadWorkspaceNames 以 toLowerCase 形态填入
        Set<String> used = new HashSet<>(Set.of("test-导入"));
        String result = McpTransferService.allocateName("Test", used, "-导入");
        assertEquals("Test-导入-2", result);
    }

    @Test
    @DisplayName("长名称截断保留完整后缀（总长不超过 64）")
    void longNameTruncated() {
        // 70 字符的基础名称
        String longName = "a".repeat(70);
        Set<String> used = new HashSet<>();
        String result = McpTransferService.allocateName(longName, used, "-导入");
        assertTrue(result.length() <= NAME_MAX, "result length " + result.length() + " > " + NAME_MAX);
        assertTrue(result.endsWith("-导入"));
        // 基础名称被截断（原 70 字符 -> 去掉后缀长度）
        assertTrue(result.startsWith("a".repeat(NAME_MAX - "-导入".length())));
    }

    @Test
    @DisplayName("本批次内同名连续分配产生不同名称")
    void batchDuplicates() {
        Set<String> used = new HashSet<>();
        String first = McpTransferService.allocateName("test", used, "-导入");
        String second = McpTransferService.allocateName("test", used, "-导入");
        assertNotEquals(first, second);
        assertEquals("test-导入", first);
        assertEquals("test-导入-2", second);
    }

    @Test
    @DisplayName("英文后缀 -import 避让（name_en 用）")
    void englishSuffix() {
        // used 集合以 toLowerCase 形态存入
        Set<String> used = new HashSet<>(Set.of("testservice-import"));
        String result = McpTransferService.allocateName("TestService", used, "-import");
        assertEquals("TestService-import-2", result);
    }

    @Test
    @DisplayName("极端长名称 + 递增后缀仍不超过 64")
    void longNameWithIncrement() {
        String longName = "b".repeat(70);
        Set<String> used = new HashSet<>();
        String first = McpTransferService.allocateName(longName, used, "-导入");
        String second = McpTransferService.allocateName(longName, used, "-导入");
        assertTrue(first.length() <= NAME_MAX);
        assertTrue(second.length() <= NAME_MAX);
        assertNotEquals(first, second);
    }
}
