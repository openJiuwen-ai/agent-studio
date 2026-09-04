/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.redis.RedisClient;

import lombok.extern.slf4j.Slf4j;

import org.redisson.client.codec.StringCodec;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Comparator;

/**
 * Redis 历史消息清理服务
 * 当 Redis 读取发生 StreamConstraintsException 时，清理历史消息到配置比例后重试
 *
 */
@Service
@Slf4j
public class RedisHistoryEvictionService {

    private static final String TRUNCATED_MARK = "[TRUNCATED]";

    @Autowired
    private RedisClient redisClient;

    @Value("${redis.history-eviction-threshold:0.75}")
    private double evictionThreshold;

    @Value("${redis.max-single-message-length:-1}")
    private int maxSingleMessageLength;

    /**
     * 处理 Redis 读取溢出异常
     * 根据 key 类型选择对应的清理策略，清理后重试读取
     *
     * @param key Redis key
     * @return 清理后的数据 JSON 字符串，如果仍然失败则返回 null
     */
    public String handleReadOverflow(String key) {
        log.warn("Handling Redis read overflow for key: {}, eviction threshold: {}", key, evictionThreshold);
        try {
            if (key == null) {
                return null;
            }
            if (key.contains("trace_root_span_")) {
                return evictTraceInfo(key);
            } else if (key.contains("_conv_")) {
                return evictListData(key, "insight_conv");
            } else if (key.contains("_exec_rel_") || key.contains("_rel_")) {
                return evictListData(key, "exec_rel");
            } else {
                return evictWorkflowInstance(key);
            }
        } catch (Exception e) {
            log.error("Failed to evict history for key: {}", key, e);
        }
        return null;
    }

    /**
     * 使用 StringCodec 读取 Redis 中的原始 JSON 字符串（绕过 Jackson 反序列化限制）
     */
    private String readRawJson(String key) {
        String rawValue = redisClient.get(key, StringCodec.INSTANCE);
        if (rawValue == null) {
            return null;
        }
        if (rawValue.startsWith("\"")) {
            return JSON.parseObject(rawValue, String.class);
        }
        return rawValue;
    }

    /**
     * 清理 WorkflowInstanceEntity 或 AgentExecutionInfo 中的历史数据
     * 当 JSON 包含 eventList 时按 startTime 排序保留最近的事件；
     * 当 JSON 包含 invoke_list 时按 start_time 排序保留最近的调用记录；
     * 同时截断顶层 inputs/outputs 等大字符串字段
     */
    private String evictWorkflowInstance(String key) {
        String jsonStr = readRawJson(key);
        if (jsonStr == null) {
            return null;
        }

        JSONObject entity = JSON.parseObject(jsonStr);
        boolean modified = false;

        JSONArray eventList = entity.getJSONArray("eventList");
        if (eventList != null && !eventList.isEmpty()) {
            int originalSize = eventList.size();
            int targetSize = Math.max(1, (int) (originalSize * evictionThreshold));

            eventList.sort((a, b) -> {
                String timeA = a instanceof JSONObject joA ? extractStartTime(joA) : null;
                String timeB = b instanceof JSONObject joB ? extractStartTime(joB) : null;
                return Comparator.nullsFirst(String::compareTo).compare(timeA, timeB);
            });

            while (eventList.size() > targetSize) {
                eventList.remove(0);
            }

            truncateEventList(eventList);
            modified = true;
            log.info("Evicted workflow instance events: key={}, original={}, remaining={}",
                key, originalSize, eventList.size());
        }

        JSONArray invokeList = entity.getJSONArray("invoke_list");
        if (invokeList != null && !invokeList.isEmpty()) {
            int originalSize = invokeList.size();
            int targetSize = Math.max(1, (int) (originalSize * evictionThreshold));

            invokeList.sort((a, b) -> {
                Long timeA = a instanceof JSONObject joA ? extractLongField(joA, "start_time") : null;
                Long timeB = b instanceof JSONObject joB ? extractLongField(joB, "start_time") : null;
                return Comparator.nullsFirst(Long::compareTo).compare(timeA, timeB);
            });

            while (invokeList.size() > targetSize) {
                invokeList.remove(0);
            }

            truncateInvokeList(invokeList);
            modified = true;
            log.info("Evicted agent execution invoke list: key={}, original={}, remaining={}",
                key, originalSize, invokeList.size());
        }

        truncateStringField(entity, "inputs");
        truncateStringField(entity, "outputs");
        truncateStringField(entity, "error_info");
        modified = true;

        if (!modified) {
            return jsonStr;
        }

        String updatedJson = entity.toJSONString();
        redisClient.setAndKeepTtl(key, updatedJson, Duration.ofDays(7));

        return updatedJson;
    }

    /**
     * 清理 TraceInfo 中的历史事件
     */
    private String evictTraceInfo(String key) {
        String jsonStr = readRawJson(key);
        if (jsonStr == null) {
            return null;
        }

        JSONObject traceInfo = JSON.parseObject(jsonStr);
        JSONArray eventList = traceInfo.getJSONArray("jiuwenEventList");
        if (eventList == null || eventList.isEmpty()) {
            return jsonStr;
        }

        int originalSize = eventList.size();
        int targetSize = Math.max(1, (int) (originalSize * evictionThreshold));

        eventList.sort((a, b) -> {
            String timeA = a instanceof JSONObject joA ? extractStartTime(joA) : null;
            String timeB = b instanceof JSONObject joB ? extractStartTime(joB) : null;
            return Comparator.nullsFirst(String::compareTo).compare(timeA, timeB);
        });

        while (eventList.size() > targetSize) {
            eventList.remove(0);
        }

        truncateEventList(eventList);

        String updatedJson = traceInfo.toJSONString();
        redisClient.setAndKeepTtl(key, updatedJson, Duration.ofMinutes(10));

        log.info("Evicted trace info events: key={}, original={}, remaining={}",
            key, originalSize, eventList.size());

        return updatedJson;
    }

    /**
     * 清理列表类型数据（ExecutionInfoList / ConversationInfoList）
     */
    private String evictListData(String key, String type) {
        String jsonStr = readRawJson(key);
        if (jsonStr == null) {
            return null;
        }

        JSONArray list = JSON.parseArray(jsonStr);
        if (list == null || list.isEmpty()) {
            return jsonStr;
        }

        int originalSize = list.size();
        int targetSize = Math.max(1, (int) (originalSize * evictionThreshold));

        list.sort((a, b) -> {
            Long timeA = a instanceof JSONObject joA ? extractLongField(joA, "startTime") : null;
            Long timeB = b instanceof JSONObject joB ? extractLongField(joB, "startTime") : null;
            return Comparator.nullsFirst(Long::compareTo).compare(timeA, timeB);
        });

        while (list.size() > targetSize) {
            list.remove(0);
        }

        String updatedJson = list.toJSONString();
        redisClient.setAndKeepTtl(key, updatedJson, Duration.ofDays(7));

        log.info("Evicted list data: key={}, type={}, original={}, remaining={}",
            key, type, originalSize, list.size());

        return updatedJson;
    }

    private String extractStartTime(JSONObject event) {
        try {
            JSONObject data = event.getJSONObject("data");
            if (data != null) {
                return data.getString("startTime");
            }
        } catch (Exception e) {
            log.debug("Failed to extract startTime from event", e);
        }
        return null;
    }

    private Long extractLongField(JSONObject obj, String field) {
        try {
            return obj.getLong(field);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 截断事件列表中的大字段
     */
    private void truncateEventList(JSONArray eventList) {
        if (maxSingleMessageLength <= 0) {
            return;
        }
        for (int i = 0; i < eventList.size(); i++) {
            JSONObject event = eventList.getJSONObject(i);
            if (event == null) {
                continue;
            }
            JSONObject data = event.getJSONObject("data");
            if (data != null) {
                truncateMapFields(data.getJSONObject("inputs"));
                truncateMapFields(data.getJSONObject("outputs"));
                truncateMapFields(data.getJSONObject("metaData"));
            }
        }
    }

    private void truncateMapFields(JSONObject map) {
        if (map == null) {
            return;
        }
        for (String fieldKey : map.keySet()) {
            Object val = map.get(fieldKey);
            if (val instanceof String && ((String) val).length() > maxSingleMessageLength) {
                int cutLength = maxSingleMessageLength - TRUNCATED_MARK.length();
                if (cutLength <= 0) {
                    map.put(fieldKey, TRUNCATED_MARK);
                } else {
                    map.put(fieldKey, ((String) val).substring(0, cutLength) + TRUNCATED_MARK);
                }
            }
        }
    }

    private void truncateInvokeList(JSONArray invokeList) {
        if (maxSingleMessageLength <= 0) {
            return;
        }
        for (int i = 0; i < invokeList.size(); i++) {
            JSONObject invoke = invokeList.getJSONObject(i);
            if (invoke == null) {
                continue;
            }
            truncateStringField(invoke, "inputs");
            truncateStringField(invoke, "outputs");
            truncateStringField(invoke, "error_message");
        }
    }

    private void truncateStringField(JSONObject obj, String field) {
        if (obj == null || maxSingleMessageLength <= 0) {
            return;
        }
        String val = obj.getString(field);
        if (val != null && val.length() > maxSingleMessageLength) {
            int cutLength = maxSingleMessageLength - TRUNCATED_MARK.length();
            if (cutLength <= 0) {
                obj.put(field, TRUNCATED_MARK);
            } else {
                obj.put(field, val.substring(0, cutLength) + TRUNCATED_MARK);
            }
        }
    }
}
