/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.entity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;

import org.junit.jupiter.api.Test;

/**
 * ToolEntity 实体类单元测试，验证 callMode 字段的 getter/setter 及 JSON 序列化 key。
 *
 */
class ToolEntityTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * 用例描述：验证 callMode 字段的 getter/setter 正常工作
     * 预制条件：创建一个空的 ToolEntity 对象
     * 输入参数：callMode 设置为 "custom"
     * 预期结果：getCallMode 返回 "custom"
     *
     * @throws Exception 序列化异常
     */
    @Test
    public void testCallModeGetterSetterShouldReturnValue() throws Exception {
        // Given
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setCallMode("custom");

        // Then
        assertEquals("custom", toolEntity.getCallMode());
    }

    /**
     * 用例描述：验证 callMode 字段默认值为 null
     * 预制条件：创建一个空的 ToolEntity 对象，不设置 callMode
     * 输入参数：无
     * 预期结果：getCallMode 返回 null
     *
     * @throws Exception 序列化异常
     */
    @Test
    public void testCallModeDefaultShouldBeNull() throws Exception {
        // Given
        ToolEntity toolEntity = new ToolEntity();

        // Then
        assertNull(toolEntity.getCallMode());
    }

    /**
     * 用例描述：验证 callMode 字段序列化到 JSON 时 key 为 "call_mode"（@JsonProperty 注解生效）
     * 预制条件：创建 ToolEntity 并设置 callMode 为 "custom"
     * 输入参数：无
     * 预期结果：序列化后的 JSON 包含 key "call_mode" 且值为 "custom"，不包含 "callMode"
     *
     * @throws Exception 序列化异常
     */
    @Test
    public void testCallModeSerializationShouldUseSnakeCaseKey() throws Exception {
        // Given
        ToolEntity toolEntity = new ToolEntity();
        toolEntity.setCallMode("custom");

        // When
        String json = MAPPER.writeValueAsString(toolEntity);
        JsonNode node = MAPPER.readTree(json);

        // Then
        assertNotNull(node.get("call_mode"), "JSON should contain 'call_mode' key");
        assertEquals("custom", node.get("call_mode").asText());
        assertNull(node.get("callMode"), "JSON should not contain 'callMode' key");
    }

    /**
     * 用例描述：验证 JSON 中 "call_mode" 键可以正确反序列化到 callMode 字段
     * 预制条件：构造包含 "call_mode":"api" 的 JSON 字符串
     * 输入参数：JSON 字符串 {"call_mode":"api"}
     * 预期结果：反序列化后 getCallMode 返回 "api"
     *
     * @throws Exception 序列化异常
     */
    @Test
    public void testCallModeDeserializationShouldReadSnakeCaseKey() throws Exception {
        // Given
        String json = "{\"call_mode\":\"api\"}";

        // When
        ToolEntity toolEntity = MAPPER.readValue(json, ToolEntity.class);

        // Then
        assertEquals("api", toolEntity.getCallMode());
    }
}
