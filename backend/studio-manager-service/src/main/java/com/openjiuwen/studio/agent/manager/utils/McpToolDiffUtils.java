/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;

/**
 * MCP 工具清单差异计算工具。
 *
 * <p>工具清单以 MCP 协议返回的原始 JSON 数组形式存取，本工具只关注工具定义本身，
 * 不感知业务状态，便于单独做单元测试。
 */
@Slf4j
public final class McpToolDiffUtils {
    /**
     * 工具下线标记字段，持久化在工具原始 JSON 中，前端据此灰显
     */
    public static final String OFFLINE_FIELD = "offline";

    /**
     * 参与"是否变更"判断的工具定义字段，名称与工具原始 JSON 保持一致
     */
    private static final String[] DEFINITION_FIELDS = {"description", "inputSchema", "outputSchema", "_meta"};

    private McpToolDiffUtils() {
    }

    /**
     * 解析工具清单 JSON，非法或空内容返回空数组
     *
     * @param toolsJson 工具清单 JSON 字符串
     * @return 工具 JSON 数组
     */
    public static JSONArray parseToolArray(String toolsJson) {
        if (StringUtils.isBlank(toolsJson)) {
            return new JSONArray();
        }
        try {
            JSONArray array = JSON.parseArray(toolsJson);
            return array == null ? new JSONArray() : array;
        } catch (Exception e) {
            log.warn("Failed to parse MCP tools json, treat as empty list.");
            return new JSONArray();
        }
    }

    /**
     * 按工具名建立索引，忽略无名称的脏数据
     *
     * @param tools 工具 JSON 数组
     * @return 工具名到工具定义的映射
     */
    public static Map<String, JSONObject> indexByName(JSONArray tools) {
        Map<String, JSONObject> index = new LinkedHashMap<>();
        if (tools == null) {
            return index;
        }
        for (int i = 0; i < tools.size(); i++) {
            JSONObject tool = tools.getJSONObject(i);
            if (tool == null || StringUtils.isBlank(tool.getString("name"))) {
                continue;
            }
            index.put(tool.getString("name"), tool);
        }
        return index;
    }

    /**
     * 工具是否已被标记为下线
     *
     * @param tool 工具定义
     * @return true 表示已下线
     */
    public static boolean isOffline(JSONObject tool) {
        return tool != null && Boolean.TRUE.equals(tool.getBoolean(OFFLINE_FIELD));
    }

    /**
     * 比较新旧工具清单，得出新增、下线、变更（schema 等定义变化）三类差异
     *
     * @param oldTools 旧工具清单
     * @param newTools 本次拉取到的新工具清单
     * @return 差异结果
     */
    public static DiffResult diff(JSONArray oldTools, JSONArray newTools) {
        Map<String, JSONObject> oldIndex = indexByName(oldTools);
        Map<String, JSONObject> newIndex = indexByName(newTools);
        Set<String> added = new LinkedHashSet<>();
        Set<String> updated = new LinkedHashSet<>();
        for (Map.Entry<String, JSONObject> entry : newIndex.entrySet()) {
            String name = entry.getKey();
            JSONObject oldTool = oldIndex.get(name);
            if (oldTool == null) {
                added.add(name);
                continue;
            }
            // 之前已下线、本次重新出现的工具，按"恢复可用"归入新增
            if (isOffline(oldTool)) {
                added.add(name);
                continue;
            }
            if (!hasSameDefinition(oldTool, entry.getValue())) {
                updated.add(name);
            }
        }
        Set<String> removed = new LinkedHashSet<>(oldIndex.keySet());
        removed.removeAll(newIndex.keySet());
        return new DiffResult(sorted(added), sorted(removed), sorted(updated));
    }

    /**
     * 合并新工具清单与需保留的已下线工具，已下线工具会带上 offline 标记
     *
     * @param newTools 本次拉取到的新工具清单
     * @param oldTools 旧工具清单，用于取回被保留工具的定义
     * @param offlineToolNames 需保留并标记下线的工具名
     * @return 合并后的工具清单 JSON 字符串
     */
    public static String mergeWithOfflineTools(JSONArray newTools, JSONArray oldTools, Set<String> offlineToolNames) {
        JSONArray merged = new JSONArray();
        if (newTools != null) {
            merged.addAll(newTools);
        }
        if (offlineToolNames == null || offlineToolNames.isEmpty()) {
            return merged.toJSONString();
        }
        Map<String, JSONObject> oldIndex = indexByName(oldTools);
        for (String toolName : offlineToolNames) {
            JSONObject oldTool = oldIndex.get(toolName);
            if (oldTool == null) {
                continue;
            }
            JSONObject offlineTool = new JSONObject(oldTool);
            offlineTool.put(OFFLINE_FIELD, true);
            merged.add(offlineTool);
        }
        return merged.toJSONString();
    }

    /**
     * 判断两个工具定义是否一致（忽略下线标记）
     *
     * @param oldTool 旧工具定义
     * @param newTool 新工具定义
     * @return true 表示定义未变化
     */
    public static boolean hasSameDefinition(JSONObject oldTool, JSONObject newTool) {
        if (oldTool == null || newTool == null) {
            return oldTool == newTool;
        }
        for (String field : DEFINITION_FIELDS) {
            if (!Objects.equals(canonicalize(oldTool.get(field)), canonicalize(newTool.get(field)))) {
                return false;
            }
        }
        return true;
    }

    /**
     * 规范化 JSON 值：对象按 key 排序后序列化，避免服务端字段顺序变化被误判为变更
     */
    private static String canonicalize(Object value) {
        return JSON.toJSONString(normalize(value));
    }

    private static Object normalize(Object value) {
        if (value instanceof JSONObject) {
            Map<String, Object> sorted = new TreeMap<>();
            for (Map.Entry<String, Object> entry : ((JSONObject) value).entrySet()) {
                if (OFFLINE_FIELD.equals(entry.getKey())) {
                    continue;
                }
                sorted.put(entry.getKey(), normalize(entry.getValue()));
            }
            return sorted;
        }
        if (value instanceof Map) {
            Map<String, Object> sorted = new TreeMap<>();
            ((Map<?, ?>) value).forEach((key, item) -> sorted.put(String.valueOf(key), normalize(item)));
            return sorted;
        }
        if (value instanceof JSONArray) {
            return normalizeList((JSONArray) value);
        }
        if (value instanceof List) {
            return normalizeList((List<?>) value);
        }
        return value;
    }

    private static List<Object> normalizeList(Iterable<?> source) {
        List<Object> normalized = new ArrayList<>();
        for (Object item : source) {
            normalized.add(normalize(item));
        }
        return normalized;
    }

    private static List<String> sorted(Set<String> names) {
        List<String> result = new ArrayList<>(names);
        Collections.sort(result);
        return result;
    }

    /**
     * 工具清单差异结果
     */
    public static class DiffResult {
        private final List<String> added;

        private final List<String> removed;

        private final List<String> updated;

        public DiffResult(List<String> added, List<String> removed, List<String> updated) {
            this.added = added;
            this.removed = removed;
            this.updated = updated;
        }

        public List<String> getAdded() {
            return added;
        }

        public List<String> getRemoved() {
            return removed;
        }

        public List<String> getUpdated() {
            return updated;
        }
    }
}
