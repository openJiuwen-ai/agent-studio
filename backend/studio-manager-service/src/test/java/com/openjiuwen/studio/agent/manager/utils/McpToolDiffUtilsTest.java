/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashSet;
import java.util.Set;

/**
 * McpToolDiffUtils 单元测试
 */
class McpToolDiffUtilsTest {

    private static JSONObject tool(String name, String description) {
        JSONObject tool = new JSONObject();
        tool.put("name", name);
        tool.put("description", description);
        JSONObject inputSchema = new JSONObject();
        inputSchema.put("type", "object");
        tool.put("inputSchema", inputSchema);
        return tool;
    }

    private static JSONArray array(JSONObject... tools) {
        JSONArray array = new JSONArray();
        for (JSONObject tool : tools) {
            array.add(tool);
        }
        return array;
    }

    @Test
    void testParseToolArray_InvalidOrBlank() {
        assertTrue(McpToolDiffUtils.parseToolArray(null).isEmpty());
        assertTrue(McpToolDiffUtils.parseToolArray(" ").isEmpty());
        assertTrue(McpToolDiffUtils.parseToolArray("not-a-json").isEmpty());
        assertEquals(1, McpToolDiffUtils.parseToolArray("[{\"name\":\"a\"}]").size());
    }

    @Test
    void testDiff_AddedRemovedUpdatedAndUnchanged() {
        JSONArray oldTools = array(tool("keep", "same"), tool("change", "old"), tool("gone", "old"));
        JSONArray newTools = array(tool("keep", "same"), tool("change", "new"), tool("fresh", "new"));

        McpToolDiffUtils.DiffResult diff = McpToolDiffUtils.diff(oldTools, newTools);

        assertEquals(1, diff.getAdded().size());
        assertEquals("fresh", diff.getAdded().get(0));
        assertEquals(1, diff.getRemoved().size());
        assertEquals("gone", diff.getRemoved().get(0));
        assertEquals(1, diff.getUpdated().size());
        assertEquals("change", diff.getUpdated().get(0));
    }

    @Test
    void testDiff_OfflineToolComesBackTreatedAsAdded() {
        JSONObject offlineTool = tool("restored", "same");
        offlineTool.put(McpToolDiffUtils.OFFLINE_FIELD, true);
        JSONArray oldTools = array(offlineTool);
        JSONArray newTools = array(tool("restored", "same"));

        McpToolDiffUtils.DiffResult diff = McpToolDiffUtils.diff(oldTools, newTools);

        assertEquals(1, diff.getAdded().size());
        assertEquals("restored", diff.getAdded().get(0));
        assertTrue(diff.getUpdated().isEmpty());
        assertTrue(diff.getRemoved().isEmpty());
    }

    @Test
    void testMergeWithOfflineTools_KeepsReferencedToolWithOfflineFlag() {
        JSONArray oldTools = array(tool("gone", "old description"));
        JSONArray newTools = array(tool("fresh", "new description"));
        Set<String> offlineTools = new LinkedHashSet<>();
        offlineTools.add("gone");
        // 未在下线集合中的历史工具不应被保留
        offlineTools.add("not-exist");

        String merged = McpToolDiffUtils.mergeWithOfflineTools(newTools, oldTools, offlineTools);
        JSONArray mergedArray = McpToolDiffUtils.parseToolArray(merged);

        assertEquals(2, mergedArray.size());
        JSONObject offline = McpToolDiffUtils.indexByName(mergedArray).get("gone");
        assertTrue(McpToolDiffUtils.isOffline(offline));
        assertEquals("old description", offline.getString("description"));
        assertFalse(McpToolDiffUtils.isOffline(McpToolDiffUtils.indexByName(mergedArray).get("fresh")));
    }

    @Test
    void testMergeWithOfflineTools_NoOfflineTool() {
        JSONArray newTools = array(tool("fresh", "new description"));

        String merged = McpToolDiffUtils.mergeWithOfflineTools(newTools, new JSONArray(), null);

        assertEquals(1, McpToolDiffUtils.parseToolArray(merged).size());
    }

    @Test
    void testHasSameDefinition_IgnoreKeyOrderAndOfflineFlag() {
        JSONObject first = new JSONObject();
        first.put("name", "tool");
        first.put("description", "desc");
        JSONObject firstSchema = new JSONObject();
        firstSchema.put("type", "object");
        firstSchema.put("required", JSONArray.of("a"));
        first.put("inputSchema", firstSchema);
        first.put(McpToolDiffUtils.OFFLINE_FIELD, true);

        JSONObject second = new JSONObject();
        JSONObject secondSchema = new JSONObject();
        secondSchema.put("required", JSONArray.of("a"));
        secondSchema.put("type", "object");
        second.put("inputSchema", secondSchema);
        second.put("description", "desc");
        second.put("name", "tool");

        assertTrue(McpToolDiffUtils.hasSameDefinition(first, second));
        second.put("description", "changed");
        assertFalse(McpToolDiffUtils.hasSameDefinition(first, second));
    }
}
