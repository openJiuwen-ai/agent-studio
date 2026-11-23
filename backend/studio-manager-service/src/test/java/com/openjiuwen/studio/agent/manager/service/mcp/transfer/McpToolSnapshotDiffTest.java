/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.service.mcp.transfer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * FEAT-134 工具差异计算（L2 §2.5）单元测试。
 *
 * 差异按单服务内工具原始 name 精确匹配（不能用界面展示名匹配）；
 * 同名工具内容变化列入 changed_tools；整个 schema 快照替换。
 */
@DisplayName("McpToolSnapshotService.computeDiff")
class McpToolSnapshotDiffTest {

    private static Map<String, Object> tool(String name) {
        Map<String, Object> t = new LinkedHashMap<>();
        t.put("name", name);
        t.put("description", "tool " + name);
        return t;
    }

    private static Map<String, Object> tool(String name, String description) {
        Map<String, Object> t = new LinkedHashMap<>();
        t.put("name", name);
        t.put("description", description);
        return t;
    }

    @Test
    @DisplayName("R-01: 新增工具正确计数")
    void addedTools() {
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(
            List.of(tool("a"), tool("b")),
            List.of(tool("a"), tool("b"), tool("c")));
        assertEquals(3, diff.get("tool_count"));
        assertEquals(1, diff.get("added_count"));
        assertEquals(0, diff.get("removed_count"));
        assertEquals(List.of("c"), diff.get("added_tools"));
    }

    @Test
    @DisplayName("R-02: 删除工具正确计数")
    void removedTools() {
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(
            List.of(tool("a"), tool("b"), tool("legacy")),
            List.of(tool("a"), tool("b")));
        assertEquals(2, diff.get("tool_count"));
        assertEquals(1, diff.get("removed_count"));
        assertEquals(List.of("legacy"), diff.get("removed_tools"));
    }

    @Test
    @DisplayName("R-02: 同名工具 schema 变化列入 changed_tools")
    void changedToolSchema() {
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(
            List.of(tool("same", "old description")),
            List.of(tool("same", "new description")));
        assertEquals(1, diff.get("tool_count"));
        assertEquals(0, diff.get("added_count"));
        assertEquals(0, diff.get("removed_count"));
        assertEquals(List.of("same"), diff.get("changed_tools"));
    }

    @Test
    @DisplayName("R-02: 删除 + 修改同时发生")
    void removalAndChange() {
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(
            List.of(tool("keep"), tool("removed"), tool("modified", "old")),
            List.of(tool("keep"), tool("modified", "new"), tool("fresh")));
        assertEquals(3, diff.get("tool_count"));
        assertEquals(1, diff.get("added_count"));
        assertEquals(1, diff.get("removed_count"));
        assertEquals(List.of("fresh"), diff.get("added_tools"));
        assertEquals(List.of("removed"), diff.get("removed_tools"));
        assertEquals(List.of("modified"), diff.get("changed_tools"));
    }

    @Test
    @DisplayName("R-04: 无变化重复重载增删为 0")
    void noChange() {
        List<Map<String, Object>> tools = List.of(tool("a"), tool("b"));
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(tools, tools);
        assertEquals(2, diff.get("tool_count"));
        assertEquals(0, diff.get("added_count"));
        assertEquals(0, diff.get("removed_count"));
        assertEquals(0, ((List<?>) diff.get("added_tools")).size());
        assertEquals(0, ((List<?>) diff.get("removed_tools")).size());
        assertEquals(0, ((List<?>) diff.get("changed_tools")).size());
    }

    @Test
    @DisplayName("R-03: 合法零工具=删除全部旧工具")
    void zeroToolsRemovesAll() {
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(
            List.of(tool("a"), tool("b"), tool("c")),
            List.of());
        assertEquals(0, diff.get("tool_count"));
        assertEquals(3, diff.get("removed_count"));
        assertEquals(List.of("a", "b", "c"), diff.get("removed_tools"));
    }

    @Test
    @DisplayName("旧快照为空 + 新快照有工具 = 全部新增")
    void emptyPrevious() {
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(
            List.of(),
            List.of(tool("a"), tool("b")));
        assertEquals(2, diff.get("tool_count"));
        assertEquals(2, diff.get("added_count"));
    }

    @Test
    @DisplayName("previous_tool_count 附加（重载路径）")
    void previousToolCount() {
        List<Map<String, Object>> previous = List.of(tool("a"), tool("b"), tool("c"));
        List<Map<String, Object>> current = List.of(tool("a"), tool("new"));
        Map<String, Object> diff = McpToolSnapshotService.computeDiff(previous, current);
        // executeReload 里 diff.put("previous_tool_count", ...)——computeDiff 本身不含该 key
        // 测试确认 computeDiff 输出的 key 是差异面而非 previous_tool_count
        assertTrue(diff.containsKey("tool_count"));
        assertEquals(2, diff.get("tool_count"));
    }
}
