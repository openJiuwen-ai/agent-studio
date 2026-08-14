/*
 * Copyright (c) 2022-2023 Lypxc (545685602@qq.com)
 * Copyright (c) Huawei Technologies Co., Ltd. 2022-2023. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

/**
 * @description
 * @since 2025/5/9
 **/

import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.dto.McpServiceToolEntity;
import com.openjiuwen.studio.agent.manager.service.mcp.McpConfig;

import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
public class McpJsonUtils {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper()
            // 忽略未知属性
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            // 允许空字符串转为null
            .configure(DeserializationFeature.ACCEPT_EMPTY_STRING_AS_NULL_OBJECT, true);

    private static final String TOOL_OUTPUT_PARAM
            = "{\"type\":\"object\",\"properties\":{\"isError\":{\"type\":\"boolean\"},\"content\":{\"type\":\"array\",\"items\":{\"type\":\"object\",\"properties\":{\"type\":{\"type\":\"string\"},\"text\":{\"type\":\"string\"}},\"required\":[\"type\",\"text\"],\"additionalProperties\":false}}},\"required\":[\"content\"],\"additionalProperties\":false}";

    static {
        // 初始化配置
        OBJECT_MAPPER.registerModule(new JavaTimeModule()); // 支持Java8时间类型
        OBJECT_MAPPER.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false); // 日期不写为时间戳
        OBJECT_MAPPER.configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false); // 空对象不报错
    }

    /**
     * 对象转JSON字符串
     */
    public static String toJson(Object object) {
        try {
            return OBJECT_MAPPER.writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new AgentStudioException(StudioError.MCP_JSON_CONVERSION_ERROR);
        }
    }

    /**
     * @param jsonStr 字符串数据
     * @return boolean
     * @description 验证字符串是否为json格式  true json格式  false 非json格式
     * @date 16:24 2025/5/10
     **/
    public static boolean isValidJson(String jsonStr) {
        try {
            JsonNode node = OBJECT_MAPPER.readTree(jsonStr);
            return node != null && (node.isObject() || node.isArray());
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * JSON字符串转对象
     */
    public static <T> T fromJson(String json, Class<T> clazz) {
        try {
            return OBJECT_MAPPER.readValue(json, clazz);
        } catch (IOException e) {
            throw new AgentStudioException(StudioError.MCP_JSON_CONVERSION_ERROR);
        }
    }

    /**
     * JSON字符串转List
     */
    public static <T> List<T> toList(String json, Class<T> clazz) {
        try {
            return OBJECT_MAPPER.readValue(json,
                    OBJECT_MAPPER.getTypeFactory().constructCollectionType(List.class, clazz));
        } catch (IOException e) {
            throw new AgentStudioException(StudioError.MCP_JSON_CONVERSION_ERROR);
        }
    }

    /**
     * JSON字符串转Map
     */
    public static <K, V> Map<K, V> toMap(String json, Class<K> keyClass, Class<V> valueClass) {
        try {
            return OBJECT_MAPPER.readValue(json,
                    OBJECT_MAPPER.getTypeFactory().constructMapType(Map.class, keyClass, valueClass));
        } catch (IOException e) {
            log.error("JSON to Map conversion failed", e);
            throw new AgentStudioException(StudioError.MCP_JSON_CONVERSION_ERROR);
        }
    }

    /**
     * JSON字符串转复杂类型（如List<MyClass>）
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) {
        try {
            return OBJECT_MAPPER.readValue(json, typeReference);
        } catch (IOException e) {
            throw new AgentStudioException(StudioError.MCP_JSON_CONVERSION_ERROR);
        }
    }

    /**
     * 美化输出JSON
     */
    public static String toPrettyJson(Object object) {
        try {
            return OBJECT_MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(object);
        } catch (JsonProcessingException e) {
            throw new AgentStudioException(StudioError.MCP_JSON_CONVERSION_ERROR);
        }
    }

    /**
     * @param jsonStr 字符串数据
     * @return boolean
     * @description 验证字符串是否为json格式  true json格式  false 非json格式
     * @date 16:24 2025/5/10
     **/
    public static JsonNode strToJson(String jsonStr) {
        try {
            return OBJECT_MAPPER.readTree(jsonStr);  // 解析 JSON 树
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * @param toolInfo 工具信息
     * @param mcpName mcp 名称
     * @return java.util.List<com.openjiuwen.studio.agent.manager.entity.McpServiceToolEntity>
     * @description 解析工具信息
     * @date 21:51 2025/8/8
     **/
    public static List<McpServiceToolEntity> parseToolFromString(String toolInfo, String mcpName) {
        if (StringUtils.isBlank(toolInfo)) {
            return new ArrayList<>();
        }
        try {
            ObjectMapper mapper = new ObjectMapper();
            List<JSONObject> toolsOrg = mapper.readValue(toolInfo, new TypeReference<>() { });
            return toolsOrg.stream().map(json -> {
                McpServiceToolEntity tool = new McpServiceToolEntity();
                tool.setName(json.getString("name"));
                tool.setDescription(json.getString("description"));
                tool.setInput(json.getString("inputSchema"));
                // 适配数据加工、合成节点
                if (json.containsKey("_meta")) {
                    String meta = json.getString("_meta");
                    JSONObject metaObj = JSONObject.parseObject(meta);
                    // 数据获取节点返回config_schema，其他节点返回meta
                    tool.setConfig(metaObj.getOrDefault("config_schema", meta).toString());
                }
                tool.setOutput(getOutputSchema(json.getString("outputSchema")));

                return tool;
            }).toList();
        } catch (JsonProcessingException e) {
            log.info("Failed to parse tool string.", e);
            throw new AgentStudioException(StudioError.QUERY_MCP_SERVICE_TOOL_ERROR, mcpName);
        }
    }

    private static String getOutputSchema(String outputSchema) {
        if (StringUtils.isNotEmpty(outputSchema)) {
            try {
                JsonNode node = OBJECT_MAPPER.readTree(outputSchema);
                //适配其他非properties，比如交投的additionalProperties
                if (node != null && node.has("properties")) {
                    return outputSchema;
                }
            } catch (Exception e) {
                log.warn("Failed to parse outputSchema: {}, fallback to default.", outputSchema, e);
            }
        }
        return StringUtils.isEmpty(SpringBeanUtils.getBean(McpConfig.class).getOutputSchema())
                ? TOOL_OUTPUT_PARAM
                : SpringBeanUtils.getBean(McpConfig.class).getOutputSchema();
    }
}

