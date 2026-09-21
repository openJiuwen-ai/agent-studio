/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.redis.RedisClient;

import org.redisson.client.codec.StringCodec;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
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
        // 对齐生产实现：readRawJson 通过 StringCodec.INSTANCE 双参读取原始 JSON
        when(redisClient.get(eq(key), eq(StringCodec.INSTANCE))).thenReturn(rawJson);
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
        assertNull(service.handleReadOverflow(null));
        verify(redisClient, never()).get(anyString(), any());
    }

    @Test
    void handleReadOverflow_keyMissing_returnsNull() {
        stubRaw("wf_inst_key", null);
        assertNull(service.handleReadOverflow("wf_inst_key"));
    }

    @Test
    void handleReadOverflow_readFailureJsonParse_errorSwallowedReturnsNull() {
        // 非法 JSON -> 内层异常被捕获 -> 返回 null（不抛出）
        stubRaw("trace_root_span_1", "{not-json");
        assertNull(service.handleReadOverflow("trace_root_span_1"));
    }

    // ---------- evictWorkflowInstance: eventList ----------

    @Test
    void evictWorkflowInstance_eventList_keepsLatestByThreshold() {
        String key = "wf_inst_001";
        stubRaw(key, "{\"eventList\":" + eventsJson("startTime", 10, true) + "}");

        String result = service.handleReadOverflow(key);

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

        String result = service.handleReadOverflow(key);

        assertEquals(1, JSON.parseObject(result).getJSONArray("eventList").size());
    }

    @Test
    void evictWorkflowInstance_nullStartTime_evictedFirst() {
        String key = "wf_inst_nullts";
        String raw = "{\"eventList\":[" + event("2025-01-01T00:00:01") + ","
            + "{\"data\":{}}," + event("2025-01-01T00:00:02") + ","
            + event("2025-01-01T00:00:03") + "]}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

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

        String result = service.handleReadOverflow(key);

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

        String result = service.handleReadOverflow(key);

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

        String result = service.handleReadOverflow(key);

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

        String result = service.handleReadOverflow(key);

        assertEquals("{\"jiuwenEventList\":[]}", result);
        verify(redisClient, never()).setAndKeepTtl(any(), any(), any());
    }

    // ---------- evictListData ----------

    @Test
    void evictListData_conversationKey_keepsLatestWithSevenDayTtl() {
        String key = "agent_001_conv_x";
        stubRaw(key, eventsJson("startTime", 8, false));

        String result = service.handleReadOverflow(key);

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

        String result = service.handleReadOverflow(key);

        assertEquals(3, JSON.parseArray(result).size());
    }

    @Test
    void evictListData_nonArrayJson_parseFailsReturnsNull() {
        String key = "agent_001_conv_bad";
        stubRaw(key, "{\"not\":\"anArray\"}");

        // JSON.parseArray 抛异常 -> 外层 catch -> null
        assertNull(service.handleReadOverflow(key));
    }

    // ---------- 修改点1：readRawJson 对齐生产实现，走双参 redisClient.get(key, StringCodec.INSTANCE) ----------

    /**
     * 用例描述：readRawJson 对齐生产实现后，通过双参 redisClient.get(key, StringCodec.INSTANCE)
     *          读取原始 JSON（StringCodec 绕过解码，供溢出清理读取超长数据）
     * 预制条件：mock RedisClient 的双参 get(String, Codec) 返回原始 JSON 字符串
     * 输入参数：key = wf_inst_001，底层原始值为未加引号的 JSON 对象（单编码）
     * 预期结果：handleReadOverflow 正常清理并写回；通过 verify 锁定双参 get(key, StringCodec.INSTANCE) 被调用
     */
    @Test
    void handleReadOverflow_readsViaStringCodecGetFromRedisClient() {
        String key = "wf_inst_001";
        stubRaw(key, "{\"eventList\":" + eventsJson("startTime", 10, true) + "}");

        String result = service.handleReadOverflow(key);

        assertNotNull(result);
        assertEquals(7, JSON.parseObject(result).getJSONArray("eventList").size());
        // 修改点1：readRawJson 必须走 redisClient.get(key, StringCodec.INSTANCE) 双参路径
        // 对齐生产：readRawJson 通过 StringCodec.INSTANCE 双参读取
        verify(redisClient).get(eq(key), eq(StringCodec.INSTANCE));
    }

    /**
     * 用例描述：readRawJson 返回的原始 JSON 为单编码（不以引号开头）时不做双编码还原，原样交给 JSON 解析，
     *          保证溢出清理链路对常规（未双编码）数据行为不变
     * 预制条件：mock 双参 get(String, Codec) 返回未加引号的原始 JSON（单编码）
     * 输入参数：key = trace_root_span_42，原始 JSON 含 6 条 jiuwenEventList 事件
     * 预期结果：按阈值 0.75 保留 4 条并写回 10 分钟 TTL
     */
    @Test
    void handleReadOverflow_usesRawStringFromStringCodecGetDirectly() {
        String key = "trace_root_span_42";
        stubRaw(key, "{\"jiuwenEventList\":" + eventsJson("startTime", 6, true) + "}");

        String result = service.handleReadOverflow(key);

        assertEquals(4, JSON.parseObject(result).getJSONArray("jiuwenEventList").size());
        // 对齐生产：readRawJson 通过 StringCodec.INSTANCE 双参读取
        verify(redisClient).get(eq(key), eq(StringCodec.INSTANCE));
    }

    /**
     * 用例描述：路由分支中 key 仅含 "_rel_"（不含 "_exec_rel_"）时，
     *          走 || 短路条件的第二分支 evictListData(key, "exec_rel")
     * 预制条件：mock 双参 get(String, Codec) 返回 4 条带 startTime 的列表 JSON
     * 输入参数：key = agent_001_rel_only
     * 预期结果：按阈值 0.75 保留 3 条并返回清理后的 JSON
     */
    @Test
    void evictListData_relOnlyKey_matchesRelShortCircuitBranch() {
        String key = "agent_001_rel_only";
        stubRaw(key, eventsJson("startTime", 4, false));

        String result = service.handleReadOverflow(key);

        assertEquals(3, JSON.parseArray(result).size());
        // 对齐生产：readRawJson 通过 StringCodec.INSTANCE 双参读取
        verify(redisClient).get(eq(key), eq(StringCodec.INSTANCE));
    }

    // ---------- 修改点2：readRawJson 双编码还原行为（修复后） ----------

    /**
     * 用例描述：readRawJson 遇到以引号开头的双编码原始值（历史写入时被整体 JSON 字符串化）
     *          时，通过 JSON.parseObject(rawValue, String.class) 还原为 JSON 原文，
     *          保证后续 evict 解析不再因外层引号而失败（溢出清理修复的核心路径）
     * 预制条件：mock 双参 get(String, Codec) 返回双编码字符串（外层带引号的 JSON 字符串字面量）
     * 输入参数：key = wf_inst_enc，底层原始值为 JSON.toJSONString(plainJson) 产生的双编码串
     * 预期结果：readRawJson 返回还原后的 JSON 原文（不带外层引号），且可被 JSON.parseObject 正常解析
     */
    @Test
    void readRawJson_doubleEncoded_restoresPlainJson() {
        String key = "wf_inst_enc";
        String plainJson = "{\"eventList\":[]}";
        // 双编码：外层带引号、内部转义，等价于历史写入时的整体字符串化存储
        String doubleEncoded = JSON.toJSONString(plainJson);
        stubRaw(key, doubleEncoded);

        String result = ReflectionTestUtils.invokeMethod(service, "readRawJson", key);

        assertEquals(plainJson, result);
        // 还原结果必须是可解析的 JSON 对象（修复前带引号原始值会导致解析失败）
        assertNotNull(JSON.parseObject(result).getJSONArray("eventList"));
    }

    /**
     * 用例描述：readRawJson 对不以引号开头的单编码原始 JSON 不做任何还原，原样返回，
     *          保证常规（未双编码）数据的读取行为不变
     * 预制条件：mock 双参 get(String, Codec) 返回单编码 JSON 字符串（不以引号开头）
     * 输入参数：key = wf_inst_plain，底层原始值为普通 JSON 对象字符串
     * 预期结果：readRawJson 返回与输入完全一致的字符串
     */
    @Test
    void readRawJson_singleEncoded_returnedAsIs() {
        String key = "wf_inst_plain";
        String raw = "{\"eventList\":[{\"data\":{\"startTime\":\"2025-01-01T00:00:00\"}}]}";
        stubRaw(key, raw);

        String result = ReflectionTestUtils.invokeMethod(service, "readRawJson", key);

        assertEquals(raw, result);
        assertEquals("2025-01-01T00:00:00",
            JSON.parseObject(result).getJSONArray("eventList").getJSONObject(0)
                .getJSONObject("data").getString("startTime"));
    }

    /**
     * 用例描述：readRawJson 在底层 key 不存在（get 返回 null）时返回 null，
     *          由上层 evict 方法转换为「不做清理、直接返回 null」语义
     * 预制条件：mock 双参 get(String, Codec) 返回 null（key 缺失）
     * 输入参数：key = wf_inst_missing，底层无数据
     * 预期结果：readRawJson 返回 null
     */
    @Test
    void readRawJson_missingKey_returnsNull() {
        String key = "wf_inst_missing";
        stubRaw(key, null);

        String result = ReflectionTestUtils.invokeMethod(service, "readRawJson", key);

        assertNull(result);
    }

    // ---------- 覆盖率补充：截断逻辑（maxSingleMessageLength > 0） ----------

    /**
     * 用例描述：maxSingleMessageLength 生效时，eventList 内 data.inputs/outputs 中的超长字符串
     *          按「前 N 字符 + [TRUNCATED]」截断（substring 分支），其余正常清理并写回
     * 预制条件：evictionThreshold=0.75、maxSingleMessageLength=20（cutLength=9>0），
     *          底层为单编码 JSON（1 条事件，data.inputs.prompt 与 data.outputs.text 各 30 字符）
     * 输入参数：key = wf_inst_trunc_sub
     * 预期结果：超长字段被截断为 9 字符前缀 + "[TRUNCATED]"；eventList 仍保留 1 条；写回与返回值一致
     */
    @Test
    void evictWorkflowInstance_truncatesEventDataSubstringFields() {
        ReflectionTestUtils.setField(service, "maxSingleMessageLength", 20);
        String key = "wf_inst_trunc_sub";
        String raw = "{\"eventList\":[{\"data\":{\"startTime\":\"2025-01-01T00:00:00\","
            + "\"inputs\":{\"prompt\":\"abcdefghijklmnopqrstuvwxyz0123\"},"
            + "\"outputs\":{\"text\":\"0123456789abcdefghijklmnopqrst\"}}}]}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

        JSONObject data = JSON.parseObject(result).getJSONArray("eventList").getJSONObject(0)
            .getJSONObject("data");
        assertEquals("abcdefghi[TRUNCATED]", data.getJSONObject("inputs").getString("prompt"));
        assertEquals("012345678[TRUNCATED]", data.getJSONObject("outputs").getString("text"));
        assertEquals("2025-01-01T00:00:00", data.getString("startTime"));
        assertEquals(result, writeBackValue(key));
    }

    /**
     * 用例描述：maxSingleMessageLength 生效时，invoke_list 元素的 inputs/outputs/error_message
     *          与顶层 inputs/outputs/error_info 超长字符串均被截断（substring 分支）
     * 预制条件：maxSingleMessageLength=20（cutLength=9>0），单编码 JSON 含 2 条 invoke_list 记录，
     *          各记录与顶层的超长字符串字段均为 30 字符
     * 输入参数：key = wf_inst_trunc_inv
     * 预期结果：所有超长字符串被截断为 9 字符前缀 + "[TRUNCATED]"，invoke_list 保留 2 条
     */
    @Test
    void evictWorkflowInstance_truncatesInvokeAndTopLevelFields() {
        ReflectionTestUtils.setField(service, "maxSingleMessageLength", 20);
        String key = "wf_inst_trunc_inv";
        String raw = "{\"invoke_list\":[{\"start_time\":1,\"inputs\":\"abcdefghijklmnopqrstuvwxyz0123\","
            + "\"outputs\":\"0123456789abcdefghijklmnopqrst\",\"error_message\":\"zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz\"}],"
            + "\"inputs\":\"iiiiiiiiiiiiiiiiiiiiiiiiiiiiii\",\"outputs\":\"oooooooooooooooooooooooooooooo\","
            + "\"error_info\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeee\"}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

        JSONObject entity = JSON.parseObject(result);
        JSONObject invoke = entity.getJSONArray("invoke_list").getJSONObject(0);
        assertEquals("abcdefghi[TRUNCATED]", invoke.getString("inputs"));
        assertEquals("012345678[TRUNCATED]", invoke.getString("outputs"));
        assertEquals("zzzzzzzzz[TRUNCATED]", invoke.getString("error_message"));
        assertEquals("iiiiiiiii[TRUNCATED]", entity.getString("inputs"));
        assertEquals("ooooooooo[TRUNCATED]", entity.getString("outputs"));
        assertEquals("eeeeeeeee[TRUNCATED]", entity.getString("error_info"));
    }

    /**
     * 用例描述：maxSingleMessageLength 过小（cutLength<=0）时，超长字段整体替换为 "[TRUNCATED]" 标记，
     *          覆盖 truncateMapFields / truncateStringField 的标记替换分支
     * 预制条件：maxSingleMessageLength=5（cutLength=5-11=-6<=0），单编码 JSON 含 1 条事件与顶层超长字段
     * 输入参数：key = wf_inst_trunc_mark
     * 预期结果：data.inputs.prompt 与顶层 outputs 均被替换为 "[TRUNCATED]"
     */
    @Test
    void evictWorkflowInstance_oversizedFields_markReplacesTooLongContent() {
        ReflectionTestUtils.setField(service, "maxSingleMessageLength", 5);
        String key = "wf_inst_trunc_mark";
        String raw = "{\"eventList\":[{\"data\":{\"startTime\":\"2025-01-01T00:00:00\","
            + "\"inputs\":{\"prompt\":\"abcdefghijklmnopqrstuvwxyz0123\"}}}],"
            + "\"outputs\":\"0123456789abcdefghijklmnopqrst\"}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

        JSONObject entity = JSON.parseObject(result);
        assertEquals("[TRUNCATED]",
            entity.getJSONArray("eventList").getJSONObject(0).getJSONObject("data")
                .getJSONObject("inputs").getString("prompt"));
        assertEquals("[TRUNCATED]", entity.getString("outputs"));
    }

    // ---------- 覆盖率补充：各 evict 路径的空值 / 空列表语义 ----------

    /**
     * 用例描述：trace 类型 key 底层数据缺失（get 返回 null）时，evictTraceInfo 不做清理直接返回 null
     * 预制条件：mock 双参 get(String, Codec) 返回 null
     * 输入参数：key = trace_root_span_missing
     * 预期结果：handleReadOverflow 返回 null，且不写回
     */
    @Test
    void evictTraceInfo_keyMissing_returnsNull() {
        String key = "trace_root_span_missing";
        stubRaw(key, null);

        assertNull(service.handleReadOverflow(key));
        verify(redisClient, never()).setAndKeepTtl(any(), any(), any());
    }

    /**
     * 用例描述：列表类型 key 底层数据缺失（get 返回 null）时，evictListData 不做清理直接返回 null
     * 预制条件：mock 双参 get(String, Codec) 返回 null
     * 输入参数：key = agent_001_conv_missing
     * 预期结果：handleReadOverflow 返回 null，且不写回
     */
    @Test
    void evictListData_keyMissing_returnsNull() {
        String key = "agent_001_conv_missing";
        stubRaw(key, null);

        assertNull(service.handleReadOverflow(key));
        verify(redisClient, never()).setAndKeepTtl(any(), any(), any());
    }

    /**
     * 用例描述：列表类型 key 底层为空数组时，evictListData 原样返回且不写回
     * 预制条件：mock 双参 get(String, Codec) 返回空数组 "[]"
     * 输入参数：key = agent_001_conv_empty
     * 预期结果：handleReadOverflow 返回 "[]"，未调用 setAndKeepTtl
     */
    @Test
    void evictListData_emptyArray_returnsOriginalNoWrite() {
        String key = "agent_001_conv_empty";
        stubRaw(key, "[]");

        String result = service.handleReadOverflow(key);

        assertEquals("[]", result);
        verify(redisClient, never()).setAndKeepTtl(any(), any(), any());
    }

    // ---------- 覆盖率补充：列表混入脏元素（非 JSONObject）的排序分支 ----------

    /**
     * 用例描述：invoke_list 混入字符串元素时，该元素按「start_time 缺失」排最前、优先被清理，
     *          其余记录按 start_time 升序保留（覆盖排序 lambda 的非 JSONObject 分支）
     * 预制条件：threshold=0.75，单编码 JSON 含 3 条 invoke_list 记录（中间 1 条为 "junk"）
     * 输入参数：key = wf_exec_dirty，start_time 分别为 2、1（junk 无时间）
     * 预期结果：junk 被删除，保留 2 条，首条 start_time=1
     */
    @Test
    void evictWorkflowInstance_invokeList_dirtyElement_treatedAsMissingTime() {
        String key = "wf_exec_dirty";
        String raw = "{\"invoke_list\":[{\"start_time\":2,\"startTime\":2},\"junk\","
            + "{\"start_time\":1,\"startTime\":1}]}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

        JSONArray kept = JSON.parseObject(result).getJSONArray("invoke_list");
        assertEquals(2, kept.size());
        assertEquals(1L, kept.getJSONObject(0).getLong("start_time"));
    }

    /**
     * 用例描述：jiuwenEventList 混入字符串元素时，该元素按「startTime 缺失」排最前、优先被清理，
     *          其余事件按 startTime 升序保留（覆盖 evictTraceInfo 排序 lambda 的非 JSONObject 分支）
     * 预制条件：threshold=0.75，单编码 JSON 含 3 条事件（中间 1 条为 "junk"）
     * 输入参数：key = trace_root_span_dirty，startTime 分别为 02、01（junk 无时间）
     * 预期结果：junk 被删除，保留 2 条，首条 startTime=2025-01-01T00:00:01
     */
    @Test
    void evictTraceInfo_dirtyElement_treatedAsMissingTime() {
        String key = "trace_root_span_dirty";
        String raw = "{\"jiuwenEventList\":[" + event("2025-01-01T00:00:02") + ",\"junk\","
            + event("2025-01-01T00:00:01") + "]}";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

        JSONArray kept = JSON.parseObject(result).getJSONArray("jiuwenEventList");
        assertEquals(2, kept.size());
        assertEquals("2025-01-01T00:00:01",
            kept.getJSONObject(0).getJSONObject("data").getString("startTime"));
    }

    /**
     * 用例描述：列表数据混入字符串元素时，该元素按「startTime 缺失」排最前、优先被清理，
     *          其余记录按 startTime 升序保留（覆盖 evictListData 排序 lambda 的非 JSONObject 分支）
     * 预制条件：threshold=0.75，单编码数组含 3 条记录（中间 1 条为 "junk"）
     * 输入参数：key = agent_001_rel_dirty，startTime 分别为 2、1（junk 无时间）
     * 预期结果：junk 被删除，保留 2 条，首条 startTime=1
     */
    @Test
    void evictListData_dirtyElement_treatedAsMissingTime() {
        String key = "agent_001_rel_dirty";
        String raw = "[{\"start_time\":2,\"startTime\":2},\"junk\",{\"start_time\":1,\"startTime\":1}]";
        stubRaw(key, raw);

        String result = service.handleReadOverflow(key);

        JSONArray kept = JSON.parseArray(result);
        assertEquals(2, kept.size());
        assertEquals(1L, kept.getJSONObject(0).getLong("startTime"));
    }
}
