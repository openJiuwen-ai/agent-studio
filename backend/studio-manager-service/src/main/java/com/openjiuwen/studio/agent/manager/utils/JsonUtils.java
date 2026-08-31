/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson.serializer.SerializerFeature;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;

import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * JsonUtils
 *
 */
@Slf4j
public class JsonUtils {
    public static final ObjectMapper JSON_MAPPER = JsonMapper.builder()
        .configure(MapperFeature.ACCEPT_CASE_INSENSITIVE_PROPERTIES, true)
        .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
        .build()
        .setDateFormat(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss"))
        .setSerializationInclusion(JsonInclude.Include.NON_NULL);

    /**
     * 解析json对象
     *
     * @param jsonStr json string
     * @param type List或Map等泛型对象类定义
     * @return 对象
     */
    public static <T> T json2Obj(String jsonStr, TypeReference<T> type) {
        try {
            if (StringUtils.isBlank(jsonStr)) {
                return null;
            }
            return JSON_MAPPER.readValue(jsonStr, type);
        } catch (JsonProcessingException e) {
            log.error("can't parse this obj, return null", e);
            return null;
        }
    }

    /**
     * 合并新老DSL数据
     * 优先使用新数据中的值（包括空字符串），如果新数据字段为null但老数据有值，则使用老数据
     * 如果新数据字段为空字符串，则使用新数据中的空值
     *
     * @param newAgentJson 新的Agent JSON字符串
     * @param oldDslJson 老的DSL JSON字符串
     * @param log 日志对象
     * @param context 上下文信息
     * @return 合并后的JSON字符串
     */
    public static String mergeDslData(String newAgentJson, String oldDslJson, org.slf4j.Logger log, String context) {
        if (StringUtils.isBlank(newAgentJson)) {
            return oldDslJson;
        }

        if (StringUtils.isBlank(oldDslJson)) {
            return newAgentJson;
        }
        try {
            JSONObject newJson = JSON.parseObject(newAgentJson);
            JSONObject oldJson = JSON.parseObject(oldDslJson);

            // 合并两个JSON对象
            JSONObject mergedJson = mergeJsonObjects(newJson, oldJson, log, context);

            // 使用配置进行序列化，避免转义问题
            String result = JSON.toJSONString(mergedJson, String.valueOf(SerializerFeature.WriteDateUseDateFormat));
            return result;
        } catch (Exception e) {
            log.error("Failed to merge DSL data for {}: {}", context, e.getMessage(), e);
            return newAgentJson;
        }
    }

    /**
     * 合并两个JSON对象
     *
     * @param newJson 新的JSON对象
     * @param oldJson 老的JSON对象
     * @param log 日志对象
     * @param context 上下文信息
     * @return 合并后的JSON对象
     */
    public static JSONObject mergeJsonObjects(JSONObject newJson, JSONObject oldJson, org.slf4j.Logger log,
        String context) {
        JSONObject mergedJson = new JSONObject(); // 新建合并对象

        // 遍历新数据，优先使用新数据中的值
        for (String key : newJson.keySet()) {
            Object newValue = newJson.get(key);
            Object oldValue = oldJson.get(key);

            // 如果新数据为null，但老数据有值，则使用老数据
            if (newValue == null && oldValue != null) {
                mergedJson.put(key, oldValue);
            } else {
                // 处理嵌套对象的合并
                if (newValue instanceof JSONObject && oldValue instanceof JSONObject) {
                    JSONObject mergedNested =
                        mergeJsonObjects((JSONObject) newValue, (JSONObject) oldValue, log, context);
                    mergedJson.put(key, mergedNested);
                } else {
                    // 使用新数据（包括空字符串）
                    mergedJson.put(key, newValue);
                }
            }
        }

        // 添加老数据中独有的字段
        for (String key : oldJson.keySet()) {
            if (!newJson.containsKey(key)) {
                Object oldValue = oldJson.get(key);
                mergedJson.put(key, oldValue);
            }
        }

        log.debug("Successfully merged JSON data for {}", context);
        return mergedJson;
    }

    /**
     * 合并列表字段（新数据有值则优先使用，新数据为空则使用老数据）
     *
     * @param newList 新的列表
     * @param oldList 老的列表
     * @return 合并后的列表
     */
    public static <T> List<T> mergeLists(List<T> newList, List<T> oldList) {
        if (CollectionUtils.isNotEmpty(newList)) {
            return newList;
        } else if (CollectionUtils.isNotEmpty(oldList)) {
            return oldList;
        } else {
            return Collections.emptyList();
        }
    }

    /**
     * 解析json对象
     *
     * @param jsonStream json InputStream
     * @param type List或Map等泛型对象类定义
     * @return 对象
     */
    public static <T> T json2Obj(InputStream jsonStream, TypeReference<T> type) {
        try {
            if (jsonStream == null) {
                return null;
            }
            return JSON_MAPPER.readValue(jsonStream, type);
        } catch (JsonProcessingException e) {
            log.error("can't parse this obj, return null", e);
            return null;
        } catch (IOException e) {
            log.error("jsonStream occur exception", e);
            return null;
        }
    }

    /**
     * 解析json数组
     *
     * @param jsonStr json string
     * @param clazz 泛型对象类定义
     * @return 对象
     */
    public static <E> List<E> json2Array(String jsonStr, Class<E> clazz) {
        try {
            if (StringUtils.isBlank(jsonStr)) {
                return null;
            }
            return JSON_MAPPER.readValue(jsonStr,
                JSON_MAPPER.getTypeFactory().constructCollectionType(List.class, clazz));
        } catch (JsonProcessingException e) {
            log.error("can't parse this obj, return null", e);
            return null;
        }
    }

    /**
     * 解析json字符串，转换为对象
     *
     * @param jsonStr json string
     * @param clazz clazz
     * @return 对象
     */
    public static <T> T json2ObjQuietly(String jsonStr, Class<T> clazz) {
        if (StringUtils.isEmpty(jsonStr)) {
            return null;
        }
        try {
            return JSON_MAPPER.readValue(jsonStr, clazz);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    /**
     * 解析对象转换为json字符串
     *
     * @param obj 对象
     * @return json字符串
     */
    public static String toJson(Object obj) {
        try {
            return JSON_MAPPER.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("can't parse this obj to String, return null", e);
            return null;
        }
    }

    /**
     * object对象解析为指定类型
     *
     * @param obj 对象
     * @return 指定类型
     */
    public static <T> T objectToClass(Object obj) {
        try {
            return JSON_MAPPER.convertValue(obj, new TypeReference<>() {});
        } catch (Exception e) {
            log.error("can't parse this obj to String, return null", e);
            return null;
        }
    }

    /**
     * object对象解析为指定类型
     *
     * @param obj 对象
     * @param toValueType 类型
     * @return 指定类型
     */
    public static <T> T objectToClassType(Object obj, Class<T> toValueType) {
        try {
            return JSON_MAPPER.convertValue(obj, toValueType);
        } catch (Exception e) {
            log.error("can't parse this obj to String, return null", e);
            return null;
        }
    }

    /**
     * object对象解析为指定类型（静默版：失败返回 null，不打印错误日志）。
     * 适用于失败属于预期场景的探测性转换（如导入时从各类型资源 metadata 中提取 WorkflowEntity 字段，
     * 插件等资源结构不兼容属正常情况），避免正常失败刷出误导排查的 ERROR 堆栈
     *
     * @param obj 对象
     * @param toValueType 类型
     * @return 指定类型，失败返回 null
     */
    public static <T> T objectToClassTypeQuiet(Object obj, Class<T> toValueType) {
        try {
            return JSON_MAPPER.convertValue(obj, toValueType);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * object对象解析为指定类型
     *
     * @param obj 对象
     * @return 指定类型
     */
    public static <T> T objectToClassRef(Object obj, TypeReference<T> toValueTypeRef) {
        try {
            return JSON_MAPPER.convertValue(obj, toValueTypeRef);
        } catch (Exception e) {
            log.error("can't parse this obj to String, return null", e);
            return null;
        }
    }

    /**
     * 验证字符串是否为有效的JSON格式
     * @param content 待验证的字符串
     * @return 有效的JSON节点对象
     * @throws JsonProcessingException 如果不是有效的JSON格式
     */
    public static JsonNode validateJson(String content) throws JsonProcessingException {
        if (content == null || content.trim().isEmpty()) {
            throw new JsonProcessingException("JSON内容不能为空") {};
        }
        // 尝试解析JSON，解析失败会抛出异常
        return JSON_MAPPER.readTree(content);
    }

    /**
     * 带fallback的序列化方法
     * 优先使用Jackson进行序列化，失败时回退到FastJSON
     *
     * @param obj 要序列化的对象
     * @param log 日志对象，用于记录错误信息
     * @param context 上下文信息，用于错误日志
     * @return 序列化后的JSON字符串
     * @throws RuntimeException 如果所有序列化方法都失败
     */
    public static String serializeWithFallback(Object obj, org.slf4j.Logger log, String context) {
        try {
            // 尝试使用Jackson序列化（包含所有字段）
            ObjectMapper objectMapper = new ObjectMapper();
            objectMapper.setSerializationInclusion(JsonInclude.Include.ALWAYS);
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize object for {}: {}", context, e.getMessage());
            return JSON.toJSONString(obj, JSONWriter.Feature.WriteMapNullValue);
        }
    }

    /**
     * 确保 JSON 字符串中指定字段的值是 JSONObject 而非转义字符串
     * 检测指定字段是否为转义的 JSON 字符串，如果是则将其还原为真正的 JSONObject。
     * 调用场景：
     * DSL 文件合并后（AgentManagementService.modifySingleAgent）</li>
     * IR 文件生成后（AgentManagementService.uploadAgentIr）</li>
     *
     * @param jsonStr   原始 JSON 字符串
     * @param fieldName 需要检查的字段名
     * @return 处理后的 JSON 字符串，确保指定字段是 JSONObject
     */
    public static String ensureJsonObjectField(String jsonStr, String fieldName) {
        if (StringUtils.isBlank(jsonStr) || StringUtils.isBlank(fieldName)) {
            return jsonStr;
        }
        try {
            JSONObject jsonObj = JSON.parseObject(jsonStr);
            Object fieldValue = jsonObj.get(fieldName);
            if (fieldValue instanceof String) {
                String strValue = (String) fieldValue;
                if (StringUtils.isNotBlank(strValue)) {
                    try {
                        JSONObject parsedValue = JSON.parseObject(strValue);
                        if (parsedValue != null) {
                            jsonObj.put(fieldName, parsedValue);
                        }
                    } catch (Exception e) {
                        log.error("Field {} value is not a valid JSON object string, keeping original value", fieldName);
                    }
                }
            }
            return JSON.toJSONString(jsonObj, String.valueOf(SerializerFeature.WriteDateUseDateFormat));
        } catch (Exception e) {
            log.error("Failed to ensure field {} as JSON object: {}", fieldName, e.getMessage(), e);
            return jsonStr;
        }
    }

    public static boolean isJsonString(String input) {
        if (input == null || input.trim().isEmpty()) {
            return false;
        }
        try {
            // 尝试解析 JSON 字符串
            JSONObject.parseObject(input);
            return true;
        } catch (Exception e) {
            // 如果解析失败，说明不是合法的 JSON 字符串
            return false;
        }
    }

    /**
     * 按 confidence 字段排序 JSON 数组
     * @param jsonArray 待排序的 JSON 数组
     * @param ascending true=升序，false=降序
     */
    public static void sortJsonArrayByConfidence(JSONArray jsonArray, boolean ascending) {
        // 空值校验，避免空指针
        if (jsonArray == null || jsonArray.isEmpty()) {
            return;
        }

        // 自定义比较器，按 confidence 排序
        jsonArray.sort(new Comparator<Object>() {
            @Override
            public int compare(Object o1, Object o2) {
                // 将对象转为 JSONObject
                JSONObject obj1 = (JSONObject) o1;
                JSONObject obj2 = (JSONObject) o2;

                // 获取 confidence 值（处理字段不存在的情况，默认 0）
                double conf1 = obj1.getDoubleValue("confidence");
                double conf2 = obj2.getDoubleValue("confidence");

                // 根据升序/降序返回比较结果
                if (ascending) {
                    return Double.compare(conf1, conf2); // 升序
                } else {
                    return Double.compare(conf2, conf1); // 降序
                }
            }
        });
    }

}
