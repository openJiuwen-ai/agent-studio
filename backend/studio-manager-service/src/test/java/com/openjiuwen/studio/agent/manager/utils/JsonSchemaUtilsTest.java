/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

@MockitoSettings(strictness = Strictness.LENIENT)
class JsonSchemaUtilsTest {

    @Test
    void testIsJsonSchemaValid_WithBlankInput() {
        assertTrue(JsonSchemaUtils.isJsonSchemaValid("", 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithNullInput() {
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(null, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithInvalidJson() {
        assertFalse(JsonSchemaUtils.isJsonSchemaValid("not-json", 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithMissingType() {
        String schema = "{\"description\":\"test\"}";
        assertFalse(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithInvalidType() {
        String schema = "{\"type\":\"invalidType\"}";
        assertFalse(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithStringType() {
        String schema = "{\"type\":\"string\"}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithNumberType() {
        String schema = "{\"type\":\"number\"}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithIntegerType() {
        String schema = "{\"type\":\"integer\"}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithBooleanType() {
        String schema = "{\"type\":\"boolean\"}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithNullType() {
        String schema = "{\"type\":\"null\"}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithArrayType() {
        String schema = "{\"type\":\"array\",\"items\":{\"type\":\"string\"}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithObjectType() {
        String schema = "{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\",\"description\":\"name\",\"location\":\"Body\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithObjectMissingProperties() {
        String schema = "{\"type\":\"object\"}";
        assertFalse(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_WithAdditionalProperties() {
        String schema = "{\"type\":\"object\",\"additionalProperties\":{\"type\":\"string\"}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_DepthExceeded() {
        String schema = "{\"type\":\"object\",\"properties\":{\"a\":{\"type\":\"object\",\"properties\":{\"b\":{\"type\":\"object\",\"properties\":{\"c\":{\"type\":\"object\",\"properties\":{\"d\":{\"type\":\"object\",\"properties\":{\"e\":{\"type\":\"string\",\"description\":\"e\",\"location\":\"Body\"}},\"description\":\"d\",\"location\":\"Body\"}},\"description\":\"c\",\"location\":\"Body\"}},\"description\":\"b\",\"location\":\"Body\"}},\"description\":\"a\",\"location\":\"Body\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 2, true));
    }

    @Test
    void testIsJsonSchemaValid_PropCountExceeded() {
        String schema = "{\"type\":\"object\",\"properties\":{\"a\":{\"type\":\"string\",\"description\":\"a\",\"location\":\"Body\"},\"b\":{\"type\":\"string\",\"description\":\"b\",\"location\":\"Body\"},\"c\":{\"type\":\"string\",\"description\":\"c\",\"location\":\"Body\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 2, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_OutputNodeSkipsFieldValidation() {
        String schema = "{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, false));
    }

    @Test
    void testIsJsonSchemaValid_InputNodeMissingDescription() {
        String schema = "{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\",\"location\":\"Body\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_InputNodeInvalidLocation() {
        String schema = "{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\",\"description\":\"name\",\"location\":\"Invalid\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_DefaultValueNumberMismatch() {
        String schema = "{\"type\":\"object\",\"properties\":{\"age\":{\"type\":\"number\",\"description\":\"age\",\"location\":\"Body\",\"default\":\"notANumber\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_DefaultValueIntegerMismatch() {
        String schema = "{\"type\":\"object\",\"properties\":{\"count\":{\"type\":\"integer\",\"description\":\"count\",\"location\":\"Body\",\"default\":\"3.14\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_DefaultValueBooleanMismatch() {
        String schema = "{\"type\":\"object\",\"properties\":{\"flag\":{\"type\":\"boolean\",\"description\":\"flag\",\"location\":\"Body\",\"default\":\"notBool\"}}}";
        assertThrows(AgentStudioException.class,
            () -> JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_DefaultValueValidNumber() {
        String schema = "{\"type\":\"object\",\"properties\":{\"age\":{\"type\":\"number\",\"description\":\"age\",\"location\":\"Body\",\"default\":\"3.14\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_DefaultValueValidBoolean() {
        String schema = "{\"type\":\"object\",\"properties\":{\"flag\":{\"type\":\"boolean\",\"description\":\"flag\",\"location\":\"Body\",\"default\":\"true\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_NestedArrayInArrayThrows() {
        String schema = "{\"type\":\"array\",\"items\":{\"type\":\"array\",\"items\":{\"type\":\"string\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_FileParamWithoutDefaultValue() {
        // FEAT-073：file/<子类型> 为合法类型标识，按前缀放行
        String schema = "{\"type\":\"object\",\"properties\":{\"pic\":{\"type\":\"file/image\",\"description\":\"pic\",\"location\":\"Body\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_FileParamWithDefaultValue() {
        // FEAT-073 回归：file/<子类型> 带 default 时不得经
        // JsonSchemaType.valueOf("FILE/IMAGE")（IllegalArgumentException→接口500），
        // 其默认值为文件 URL 字符串，无类型格式校验，直接放行
        String schema = "{\"type\":\"object\",\"properties\":{\"pic\":{\"type\":\"file/image\",\"description\":\"pic\",\"location\":\"Body\",\"default\":\"https://example.com/a.png\"}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }

    @Test
    void testIsJsonSchemaValid_FileArrayParamWithDefaultValue() {
        // array<file/image> 的 items 带 default 同样放行
        String schema = "{\"type\":\"object\",\"properties\":{\"pics\":{\"type\":\"array\",\"description\":\"pics\",\"location\":\"Body\",\"items\":{\"type\":\"file/image\",\"description\":\"pic\",\"location\":\"Body\",\"default\":\"https://example.com/a.png\"}}}}";
        assertTrue(JsonSchemaUtils.isJsonSchemaValid(schema, 10, 5, true));
    }
}
