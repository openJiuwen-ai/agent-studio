/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.redis.RedisClient;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.redisson.client.codec.Codec;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Duration;

/**
 * RedisHistoryEvictionService 行为锁定测试。
 * 以「输入原始 JSON -> 溢出清理后返回/写回的 JSON」为断言面，锁住排序、保留条数、
 * 空值语义与写回参数，供 G.TYP.13 / G.MET.06 安全扫描修复前后对比行为是否漂移。
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class RedisHistoryEvictionServiceTest {

    @Mock
    private RedisClient redisClient;

    @InjectMocks
    private RedisHistoryEvictionService service;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(service, "evictionThreshold", 0.75d);
        ReflectionTestUtils.setField(service, "maxSingleMessageLength", -1);
    }

    private void stubRaw(String key, String rawJson) {
        when(redisClient.get(eq(key), any(Codec.class))).thenReturn(rawJson);
    }

    private String writeBackValue(String key) {
        ArgumentCaptor<String> valueCaptor = ArgumentCaptor.forClass(String.class);
        verify(redisClient).setAndKeepTtl(eq(key), valueCaptor.capture(), any(Duration.class));
        return valueCaptor.getValue();
    }

    private static String event(String startTime) {
        JSONObject data = new JSONObject();
        data.put("startTime", startTime);
        JSONObject event = new JSONObject();
        event.put("data", data);
        return event.toJSONString();
    }

    /** 生成 n 个事件，startTime 递增（ISO 定宽格式保证字典序==时间序）。 */
    private static String eventsJson(String field, int n, boolean nestedData) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            if (i > 0) {
                sb.append(',');
            }
            String ts = String.format("2025-01-01T00:00:%02d", i);
            sb.append(nestedData
                ? "{\"data\":{\"startTime\":\"" + ts + "\"}}"
                : "{\"start_time\":" + i + ",\"startTime\":" + i + "}");
        }
        return "[" + sb + "]";
    }

    // ---------- 路由与空值语义 ----------

    @Test
    void handleReadOverflow_nullKey_returnsNull_noRedisAccess() {
        assertNull(service.handleReadOverflow(null).orElse(null));
        verify(redisClient, never()).get(any(), any(Codec.class));
    }

    @Test
    void handleReadOverflow_keyMissing_returnsNull() {
        stubRaw("wf_inst_key", null);
        assertNull(service.handleReadOverflow("wf_inst_key").orElse(null));
    }

    @Test
    void handleReadOverflow_readFailureJsonParse_errorSwallowedReturnsNull() {
        // 非法 JSON -> 内层异常被捕获 -> 返回 null（不抛出）
        stubRaw("trace_root_span_1", "{not-json");
        assertNull(service.handleReadOverflow("trace_root_span_1").orElse(null));
    }

    // ---------- evictWorkflowInstance: eventList ----------

    @Test
    void evictWorkflowInstance_eventList_keepsLatestByThreshold() {
        String key = "wf_inst_001";
        stubRaw(key, "{\"eventList\":" + eventsJson("startTime", 10, true) + "}");

        String result = service.handleReadOverflow(key).orElse(null);

        assertNotNull(result);
        JSONArray kept = JSON.parseObject(result).getJSONArray("eventList");
        assertEquals(7, kept.size());
        // 升序排序后从头部删除最旧 3 条 -> 剩余 t03..t09
        assertEquals("2025-01-01T00:00:03",
            kept.getJSONObject(0).getJSONObject("data").getString("startTime"));
        assertEquals("2025-01-01T00:00:09",
            kept.getJSONObject(6).getJSONObject("data").getString("startTime"));
        // 写回内容与返回值一致
        assertEquals(result, writeBackValue(key));
    }

    @Test
    void evictWorkflowInstance_eventList_singleEvent_notEvicted() {
        String key = "wf_inst_single";
        stubRaw(key, "{\"eventList\":" + eventsJson("startTime", 1, true) + "}");

        String result = service.handleReadOverflow(key).orElse(null);

        assertEquals(1, JSON.parseObject(result).getJSONArray("eventList").size());
    }

    @Test
    void evictWorkflowInstance_nullStartTime_evictedFirst() {
        String key = "wf_inst_nullts";
        String raw = "{\"eventList\":[" + event("2025-01-01T00:00:01") + ","
            + "{\"data\":{}}," + event("2025-01-01T00:00:02") + ","
            + event("2025-01-01T00:00:03") + "]}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key).orElse(null);

        JSONArray kept = JSON.parseObject(result).getJSONArray("eventList");
        assertEquals(3, kept.size());
        // nullsFirst：缺时间的排最前、先被清理
        assertEquals("2025-01-01T00:00:01",
            kept.getJSONObject(0).getJSONObject("data").getString("startTime"));
    }

    @Test
    void evictWorkflowInstance_dirtyStringElement_treatedAsMissingTime() {
        // G.TYP.13 修复后行为：数组混入非对象元素不再抛 CCE，
        // 按「时间缺失」排最前、优先被清理，整体清理成功写回。
        // （修复前锁定行为：CCE 被吞 -> 返回 null 且不写回）
        String key = "wf_inst_dirty";
        String raw = "{\"eventList\":[" + event("2025-01-01T00:00:02") + ",\"junk\","
            + event("2025-01-01T00:00:01") + "]}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key).orElse(null);

        assertNotNull(result);
        JSONArray kept = JSON.parseObject(result).getJSONArray("eventList");
        assertEquals(2, kept.size());
        assertEquals("2025-01-01T00:00:01",
            kept.getJSONObject(0).getJSONObject("data").getString("startTime"));
        assertEquals("2025-01-01T00:00:02",
            kept.getJSONObject(1).getJSONObject("data").getString("startTime"));
    }

    // ---------- evictWorkflowInstance: invoke_list ----------

    @Test
    void evictWorkflowInstance_invokeList_sortByStartTimeKeepLatest() {
        String key = "wf_exec_001";
        stubRaw(key, "{\"invoke_list\":" + eventsJson("start_time", 10, false) + "}");

        String result = service.handleReadOverflow(key).orElse(null);

        JSONArray kept = JSON.parseObject(result).getJSONArray("invoke_list");
        assertEquals(7, kept.size());
        assertEquals(3L, kept.getJSONObject(0).getLong("start_time"));
        assertEquals(9L, kept.getJSONObject(6).getLong("start_time"));
    }

    // ---------- evictTraceInfo ----------

    @Test
    void evictTraceInfo_keepsLatestWithTenMinuteTtl() {
        String key = "trace_root_span_42";
        stubRaw(key, "{\"jiuwenEventList\":" + eventsJson("startTime", 6, true) + "}");

        String result = service.handleReadOverflow(key).orElse(null);

        JSONArray kept = JSON.parseObject(result).getJSONArray("jiuwenEventList");
        assertEquals(4, kept.size());
        assertEquals("2025-01-01T00:00:02",
            kept.getJSONObject(0).getJSONObject("data").getString("startTime"));
        ArgumentCaptor<Duration> ttl = ArgumentCaptor.forClass(Duration.class);
        verify(redisClient).setAndKeepTtl(eq(key), any(), ttl.capture());
        assertEquals(Duration.ofMinutes(10), ttl.getValue());
    }

    @Test
    void evictTraceInfo_emptyEventList_returnsOriginalNoWrite() {
        String key = "trace_root_span_empty";
        stubRaw(key, "{\"jiuwenEventList\":[]}");

        String result = service.handleReadOverflow(key).orElse(null);

        assertEquals("{\"jiuwenEventList\":[]}", result);
        verify(redisClient, never()).setAndKeepTtl(any(), any(), any());
    }

    // ---------- evictListData ----------

    @Test
    void evictListData_conversationKey_keepsLatestWithSevenDayTtl() {
        String key = "agent_001_conv_x";
        stubRaw(key, eventsJson("startTime", 8, false));

        String result = service.handleReadOverflow(key).orElse(null);

        JSONArray kept = JSON.parseArray(result);
        assertEquals(6, kept.size());
        assertEquals(2L, kept.getJSONObject(0).getLong("startTime"));
        assertEquals(7L, kept.getJSONObject(5).getLong("startTime"));
        ArgumentCaptor<Duration> ttl = ArgumentCaptor.forClass(Duration.class);
        verify(redisClient).setAndKeepTtl(eq(key), any(), ttl.capture());
        assertEquals(Duration.ofDays(7), ttl.getValue());
    }

    @Test
    void evictListData_relKey_sortedByStartTime() {
        String key = "agent_001_exec_rel_y";
        stubRaw(key, eventsJson("startTime", 4, false));

        String result = service.handleReadOverflow(key).orElse(null);

        assertEquals(3, JSON.parseArray(result).size());
    }

    @Test
    void evictListData_nonArrayJson_parseFailsReturnsNull() {
        String key = "agent_001_conv_bad";
        stubRaw(key, "{\"not\":\"anArray\"}");

        // JSON.parseArray 抛异常 -> 外层 catch -> empty
        assertNull(service.handleReadOverflow(key).orElse(null));
    }
}
