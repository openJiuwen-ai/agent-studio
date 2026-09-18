/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * WorkflowValidationService 默认值类型校验相关纯函数单元测试。
 * 覆盖 bug001 高/中/低风险修复：parseJsonValue / isElementTypeValid / isDefaultValueTypeValid / isNameValid。
 * 被测方法为 private 纯函数，不依赖任何 @Autowired 字段，直接 new 实例 + 反射调用。
 */
class WorkflowValidationServiceTest {

    private final WorkflowValidationService service = new WorkflowValidationService();

    // ===== parseJsonValue（高风险：默认值 JSON 字符串解析）=====

    @Test
    void parseJsonObjectString_shouldReturnMap() {
        Object result = invoke("parseJsonValue", "{\"a\":1}");
        assertTrue(result instanceof Map, "JSON 对象字符串应解析为 Map");
    }

    @Test
    void parseJsonArrayString_shouldReturnList() {
        Object result = invoke("parseJsonValue", "[1,2,3]");
        assertTrue(result instanceof List, "JSON 数组字符串应解析为 List");
    }

    @Test
    void parseEmptyArrayString_shouldReturnEmptyList() {
        Object result = invoke("parseJsonValue", "[]");
        assertTrue(result instanceof List, "空数组字符串应解析为空 List");
        assertEquals(0, ((List<?>) result).size());
    }

    @Test
    void parseNonJsonString_shouldReturnOriginal() {
        // 非 JSON 字符串应原样返回（交给后续 instanceof 判定）
        Object result = invoke("parseJsonValue", "hello");
        assertEquals("hello", result);
    }

    @Test
    void parseNonString_shouldReturnOriginal() {
        // 非 String 输入原样返回
        List<Object> list = List.of(1, 2);
        Object result = invoke("parseJsonValue", list);
        assertSame(list, result);
    }

    @Test
    void parseBlankString_shouldReturnOriginal() {
        Object result = invoke("parseJsonValue", "   ");
        assertEquals("   ", result, "空白字符串原样返回");
    }

    // ===== isNameValid（字段名正则：不能以数字开头）=====

    @Test
    void isNameValid_legalName_shouldReturnTrue() {
        assertTrue(invokeNameValid("ppp"), "合法字段名应通过");
        assertTrue(invokeNameValid("_name"), "下划线开头合法");
        assertTrue(invokeNameValid("name_1"), "含数字合法");
    }

    @Test
    void isNameValid_digitStart_shouldReturnFalse() {
        assertFalse(invokeNameValid("123"), "数字开头应拒绝");
        assertFalse(invokeNameValid("1abc"), "数字开头应拒绝");
    }

    @Test
    void isNameValid_null_shouldReturnFalse() {
        assertFalse(invokeNameValid(null), "null 应拒绝");
    }

    // ===== isElementTypeValid：integer 整数约束（低风险）=====

    @Test
    void isElementTypeValid_integer_shouldRejectFloat() {
        assertFalse(invokeIsElementTypeValid(1.5, "integer", null), "integer 不应接受浮点 1.5");
        assertFalse(invokeIsElementTypeValid("1.5", "integer", null), "integer 不应接受字符串 \"1.5\"");
    }

    @Test
    void isElementTypeValid_integer_shouldAcceptInteger() {
        assertTrue(invokeIsElementTypeValid(1, "integer", null), "integer 应接受整数 1");
        assertTrue(invokeIsElementTypeValid(1.0, "integer", null), "1.0 无小数部分应通过");
        assertTrue(invokeIsElementTypeValid(-3, "integer", null), "负整数应通过");
        assertTrue(invokeIsElementTypeValid("1", "integer", null), "字符串整数应通过");
    }

    @Test
    void isElementTypeValid_number_shouldAcceptFloat() {
        assertTrue(invokeIsElementTypeValid(1.5, "number", null), "number 应接受浮点");
        assertTrue(invokeIsElementTypeValid("1.5", "number", null), "number 应接受字符串浮点");
        assertTrue(invokeIsElementTypeValid(1, "number", null), "number 应接受整数");
    }

    @Test
    void isElementTypeValid_string_shouldRejectNumber() {
        assertFalse(invokeIsElementTypeValid(1, "string", null), "string 不应接受数字");
        assertTrue(invokeIsElementTypeValid("abc", "string", null), "string 应接受字符串");
    }

    @Test
    void isElementTypeValid_boolean_shouldRejectString() {
        assertFalse(invokeIsElementTypeValid("true", "boolean", null), "boolean 不应接受字符串");
        assertTrue(invokeIsElementTypeValid(true, "boolean", null), "boolean 应接受布尔");
    }

    @Test
    void isElementTypeValid_object_jsonString_shouldParseAndValidate() {
        // object 分支应解析 JSON 字符串再校验
        assertTrue(invokeIsElementTypeValid("{\"a\":1}", "object", null), "JSON 对象字符串应通过");
        assertFalse(invokeIsElementTypeValid("hello", "object", null), "非 JSON 字符串应拒绝");
    }

    @Test
    void isElementTypeValid_array_jsonString_shouldParseAndValidate() {
        // array 分支应解析 JSON 字符串，并递归校验元素类型（中风险 2）
        assertTrue(invokeIsElementTypeValid("[1,2]", "array", null), "JSON 数组字符串无 schema 应通过");
        assertFalse(invokeIsElementTypeValid("123", "array", null), "非数组应拒绝");
    }

    @Test
    void isElementTypeValid_array_withElementSchema_shouldValidateElements() {
        // array + schema={type:string}：元素应为 string，数字元素应拒绝（中风险 2）
        Map<String, Object> schema = new HashMap<>();
        schema.put("type", "string");
        assertFalse(invokeIsElementTypeValid(List.of(1, 2), "array", schema), "array<string> 元素为数字应拒绝");
        assertTrue(invokeIsElementTypeValid(List.of("a", "b"), "array", schema), "array<string> 元素为字符串应通过");
    }

    @Test
    void isElementTypeValid_array_withObjectElementSchema_shouldValidateSubFields() {
        // array + schema={type:object, schema:[{name:name,type:string}]}：元素子字段类型应递归校验
        Map<String, Object> nameField = new HashMap<>();
        nameField.put("name", "name");
        nameField.put("type", "string");
        Map<String, Object> elementSchema = new HashMap<>();
        elementSchema.put("type", "object");
        elementSchema.put("schema", List.of(nameField));

        Map<String, Object> validObj = new HashMap<>();
        validObj.put("name", "ppp");
        assertTrue(invokeIsElementTypeValid(List.of(validObj), "array", elementSchema), "元素子字段类型正确应通过");

        Map<String, Object> invalidObj = new HashMap<>();
        invalidObj.put("name", 123); // name 应 string 实 number
        assertFalse(invokeIsElementTypeValid(List.of(invalidObj), "array", elementSchema), "元素子字段类型错误应拒绝");
    }

    // ===== isDefaultValueTypeValid：默认值类型校验（高风险 + 中风险）=====

    @Test
    void isDefaultValueTypeValid_arrayJsonString_shouldNotFalseReport() {
        // 高风险：前端复杂类型默认值以 JSON 字符串写入 value.default，不应被误报类型不匹配
        WorkflowFieldVO field = buildField("array<object>",
            buildObjectElementSchema(List.of(buildSubField("name", "string"))));
        assertTrue(invokeIsDefaultValueTypeValid(field, "[{\"name\":\"x\"}]"), "合法 array<object> JSON 字符串默认值不应被误报");
    }

    @Test
    void isDefaultValueTypeValid_objectJsonString_shouldNotFalseReport() {
        WorkflowFieldVO field = buildField("object",
            List.of(buildSubField("a", "integer")));
        assertTrue(invokeIsDefaultValueTypeValid(field, "{\"a\":1}"), "合法 object JSON 字符串默认值不应被误报");
    }

    @Test
    void isDefaultValueTypeValid_arrayObject_mismatchedElementField_shouldReject() {
        // 中风险：array<object> 元素子字段类型不匹配应拒绝
        WorkflowFieldVO field = buildField("array<object>",
            buildObjectElementSchema(List.of(buildSubField("name", "string"))));
        assertFalse(invokeIsDefaultValueTypeValid(field, "[{\"name\":123}]"), "元素子字段 name 应 string 实 number 应拒绝");
    }

    @Test
    void isDefaultValueTypeValid_integerFloat_shouldReject() {
        // 低风险：integer 默认值 1.5 应拒绝
        WorkflowFieldVO field = buildField("integer", null);
        assertFalse(invokeIsDefaultValueTypeValid(field, "1.5"), "integer 默认值 1.5 应拒绝");
        assertTrue(invokeIsDefaultValueTypeValid(field, "1"), "integer 默认值 1 应通过");
    }

    // ===== 辅助方法 =====

    private Object invoke(String methodName, Object... args) {
        return ReflectionTestUtils.invokeMethod(service, methodName, args);
    }

    private boolean invokeNameValid(String name) {
        return (boolean) ReflectionTestUtils.invokeMethod(service, "isNameValid", name);
    }

    private boolean invokeIsElementTypeValid(Object value, String type, Object schema) {
        return (boolean) ReflectionTestUtils.invokeMethod(service, "isElementTypeValid", value, type, schema);
    }

    private boolean invokeIsDefaultValueTypeValid(WorkflowFieldVO field, Object defaultValue) {
        return (boolean) ReflectionTestUtils.invokeMethod(service, "isDefaultValueTypeValid", field, defaultValue);
    }

    private static void assertSame(Object expected, Object actual) {
        assertTrue(expected == actual, "应返回同一对象引用");
    }

    /** 构造 WorkflowFieldVO，type 为声明类型，schema 为子字段声明。 */
    private WorkflowFieldVO buildField(String type, Object schema) {
        WorkflowFieldVO field = new WorkflowFieldVO();
        field.setName("test_field");
        field.setType(type);
        field.setSchema(schema);
        return field;
    }

    /** 构造后端 schema 子字段描述 Map（{name, type, schema}）。 */
    private Map<String, Object> buildSubField(String name, String type) {
        Map<String, Object> sub = new HashMap<>();
        sub.put("name", name);
        sub.put("type", type);
        return sub;
    }

    /** array<object> 的 schema 为元素描述 {type:object, schema:[子字段列表]}。 */
    private Map<String, Object> buildObjectElementSchema(List<Map<String, Object>> subFields) {
        Map<String, Object> elementSchema = new HashMap<>();
        elementSchema.put("type", "object");
        elementSchema.put("schema", subFields);
        return elementSchema;
    }
}
