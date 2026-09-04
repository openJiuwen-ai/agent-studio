/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

@MockitoSettings(strictness = Strictness.LENIENT)
class JsonUtilsTest {
    // 测试数据：简单对象
    static class TestObj {
        private String name;

        private int age;

        private Date createTime;

        // 必须有默认构造器（JSON反序列化需要）
        public TestObj() {
        }

        public TestObj(String name, int age, Date createTime) {
            this.name = name;
            this.age = age;
            this.createTime = createTime;
        }

        // Getter/Setter（JSON序列化需要）
        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public int getAge() {
            return age;
        }

        public void setAge(int age) {
            this.age = age;
        }

        public Date getCreateTime() {
            return createTime;
        }

        public void setCreateTime(Date createTime) {
            this.createTime = createTime;
        }

        // 用于断言对象相等
        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (o == null || getClass() != o.getClass()) {
                return false;
            }
            TestObj testObj = (TestObj) o;
            return age == testObj.age && name.equals(testObj.name) && createTime.equals(testObj.createTime);
        }

        @Override
        public int hashCode() {
            // 基于 name、age、createTime 计算哈希值
            return Objects.hash(name, age, createTime);
        }
    }

    /**
     * 测试 json2Obj(String, TypeReference) 方法
     * 场景1：正常解析（对象）
     * 场景2：正常解析（泛型集合）
     * 场景3：jsonStr为空/空白
     * 场景4：json格式错误（解析失败）
     */
    @Test
    void testJson2Obj() throws Exception {
        // 场景1：解析为对象
        String objJson = "{\"name\":\"test\",\"age\":18,\"createTime\":\"2024-01-01 12:00:00\"}";
        TestObj expectedObj = new TestObj("test", 18,
            new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse("2024-01-01 12:00:00"));
        TestObj actualObj = JsonUtils.json2Obj(objJson, new TypeReference<TestObj>() { });
        assertEquals(expectedObj, actualObj);

        // 场景2：解析为泛型集合（List<TestObj>）
        String listJson = "[{\"name\":\"a\",\"age\":20,\"createTime\":\"2024-01-02 10:00:00\"}]";
        List<TestObj> expectedList = new ArrayList<>();
        expectedList.add(
            new TestObj("a", 20, new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse("2024-01-02 10:00:00")));
        List<TestObj> actualList = JsonUtils.json2Obj(listJson, new TypeReference<List<TestObj>>() { });
        assertEquals(expectedList, actualList);

        // 场景3：jsonStr为空/空白
        assertNull(JsonUtils.json2Obj("", new TypeReference<TestObj>() { }));
        assertNull(JsonUtils.json2Obj("   ", new TypeReference<TestObj>() { }));
        assertNull(JsonUtils.json2Obj((String) null, new TypeReference<TestObj>() { }));

        // 场景4：json格式错误（解析失败）
        String invalidJson = "{invalid}";
        assertNull(JsonUtils.json2Obj(invalidJson, new TypeReference<TestObj>() { }));
    }

    /**
     * 测试 json2Obj(InputStream, TypeReference) 方法
     * 场景1：正常解析
     * 场景2：InputStream为null
     * 场景3：输入流内容格式错误
     * 场景4：输入流IO异常（模拟）
     */
    @Test
    void testJson2ObjWithInputStream() throws Exception {
        // 场景1：正常解析
        String json = "{\"name\":\"streamTest\",\"age\":25}";
        InputStream inputStream = new ByteArrayInputStream(json.getBytes(StandardCharsets.UTF_8));
        TestObj actual = JsonUtils.json2Obj(inputStream, new TypeReference<TestObj>() { });
        assertEquals("streamTest", actual.getName());
        assertEquals(25, actual.getAge());

        // 场景2：InputStream为null
        assertNull(JsonUtils.json2Obj((InputStream) null, new TypeReference<TestObj>() { }));

        // 场景3：输入流内容格式错误
        InputStream invalidStream = new ByteArrayInputStream("{invalid}".getBytes(StandardCharsets.UTF_8));
        assertNull(JsonUtils.json2Obj(invalidStream, new TypeReference<TestObj>() { }));

    }

    /**
     * 测试 json2Array 方法（解析为List）
     * 场景1：正常解析数组
     * 场景2：jsonStr为空/空白
     * 场景3：json格式错误
     */
    @Test
    void testJson2Array() {
        // 场景1：正常解析
        String arrayJson = "[\"a\",\"b\",\"c\"]";
        List<String> list = JsonUtils.json2Array(arrayJson, String.class);
        assertNotNull(list);
        assertEquals(3, list.size());
        assertEquals(List.of("a", "b", "c"), list);

        // 场景2：jsonStr为空/空白
        assertNull(JsonUtils.json2Array("", String.class));
        assertNull(JsonUtils.json2Array(null, String.class));

        // 场景3：json格式错误
        assertNull(JsonUtils.json2Array("{invalid}", String.class));
    }

    /**
     * 测试 json2ObjQuietly 方法（解析为Class对象）
     * 场景1：正常解析
     * 场景2：jsonStr为空/空白
     * 场景3：json格式错误
     */
    @Test
    void testJson2ObjQuietly() throws Exception {
        // 场景1：正常解析
        String json = "{\"name\":\"quiet\",\"age\":30}";
        TestObj obj = JsonUtils.json2ObjQuietly(json, TestObj.class);
        assertNotNull(obj);
        assertEquals("quiet", obj.getName());

        // 场景2：jsonStr为空/空白
        assertNull(JsonUtils.json2ObjQuietly("", TestObj.class));
        assertNull(JsonUtils.json2ObjQuietly(null, TestObj.class));

        // 场景3：json格式错误
        assertNull(JsonUtils.json2ObjQuietly("{invalid}", TestObj.class));
    }

    /**
     * 测试 toJson 方法（对象转JSON）
     * 场景1：正常转换
     */
    @Test
    void testToJson() {
        // 场景1：正常转换（验证非null字段，忽略null字段）
        TestObj obj = new TestObj("jsonTest", 22, null); // createTime为null，应被忽略
        String json = JsonUtils.toJson(obj);
        assertTrue(json.contains("\"name\":\"jsonTest\""));
        assertTrue(json.contains("\"age\":22"));
        assertFalse(json.contains("createTime")); // 因设置了NON_NULL

    }

    /**
     * 测试 objectToClassType 方法（对象转指定Class类型）
     * 场景1：正常转换
     * 场景2：转换失败
     */
    @Test
    void testObjectToClassType() {
        // 场景1：正常转换（Map转TestObj）
        Map<String, Object> map = Map.of("name", "typeTest", "age", 40);
        TestObj obj = JsonUtils.objectToClassType(map, TestObj.class);
        assertNotNull(obj);
        assertEquals("typeTest", obj.getName());

        // 场景2：转换失败（值类型不匹配，如String转int）
        Map<String, Object> invalidMap = Map.of("name", "err", "age", "notNumber"); // age应为int
        TestObj invalidObj = JsonUtils.objectToClassType(invalidMap, TestObj.class);
        assertNull(invalidObj);
    }

    /**
     * 测试 objectToClassTypeQuiet 方法（静默版对象转指定Class类型）
     * 场景1：正常转换；场景2：转换失败返回 empty；场景3：null 输入返回 empty
     */
    @Test
    void testObjectToClassTypeQuiet() {
        Map<String, Object> map = Map.of("name", "quietTest", "age", 41);
        Optional<TestObj> obj = JsonUtils.objectToClassTypeQuiet(map, TestObj.class);
        assertTrue(obj.isPresent());
        assertEquals("quietTest", obj.get().getName());

        Map<String, Object> invalidMap = Map.of("name", "err", "age", "notNumber");
        assertTrue(JsonUtils.objectToClassTypeQuiet(invalidMap, TestObj.class).isEmpty());

        assertTrue(JsonUtils.objectToClassTypeQuiet(null, TestObj.class).isEmpty());
    }

    /**
     * 测试 objectToClassRef 方法（对象转TypeReference类型）
     * 场景1：正常转换（Map转List<TestObj>）
     * 场景2：转换失败
     */
    @Test
    void testObjectToClassRef() {
        // 场景1：正常转换（List<Map>转List<TestObj>）
        List<Map<String, Object>> mapList = new ArrayList<>();
        mapList.add(Map.of("name", "refTest", "age", 45));
        List<TestObj> objList = JsonUtils.objectToClassRef(mapList, new TypeReference<List<TestObj>>() { });
        assertNotNull(objList);
        assertEquals(1, objList.size());
        assertEquals("refTest", objList.get(0).getName());

        // 场景2：转换失败（类型不兼容）
        String invalidObj = "not a list";
        List<TestObj> invalidList = JsonUtils.objectToClassRef(invalidObj, new TypeReference<List<TestObj>>() { });
        assertNull(invalidList);
    }

    /**
     * 测试 validateJson 方法（验证JSON格式）
     * 场景1：正常验证通过
     * 场景2：JSON内容为空/空白（抛异常）
     * 场景3：JSON格式错误（抛异常）
     */
    @Test
    void testValidateJson() throws JsonProcessingException {
        // 场景1：正常验证通过
        String validJson = "{\"valid\":true}";
        JsonNode node = JsonUtils.validateJson(validJson);
        assertTrue(node.get("valid").asBoolean());

        // 场景2：JSON内容为空/空白（抛异常）
        assertThrows(JsonProcessingException.class, () -> JsonUtils.validateJson(""));
        assertThrows(JsonProcessingException.class, () -> JsonUtils.validateJson(null));
        assertThrows(JsonProcessingException.class, () -> JsonUtils.validateJson("   "));

        // 场景3：JSON格式错误（抛异常）
        assertThrows(JsonProcessingException.class, () -> JsonUtils.validateJson("{invalid}"));
    }

    /**
     * 测试 JSON_MAPPER 的配置是否生效
     * 验证：忽略未知字段、大小写不敏感、日期格式、忽略null字段
     */
    @Test
    void testJsonMapperConfig() throws JsonProcessingException {
        // 1. 忽略未知字段（DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES=false）
        String jsonWithUnknownField = "{\"name\":\"configTest\",\"age\":50,\"unknownField\":\"xxx\"}";
        TestObj obj = JsonUtils.json2ObjQuietly(jsonWithUnknownField, TestObj.class);
        assertNotNull(obj); // 不会因unknownField报错

        // 2. 大小写不敏感（MapperFeature.ACCEPT_CASE_INSENSITIVE_PROPERTIES=true）
        String jsonWithUpperCase = "{\"NAME\":\"caseTest\",\"AGE\":55}";
        TestObj caseObj = JsonUtils.json2ObjQuietly(jsonWithUpperCase, TestObj.class);
        assertEquals("caseTest", caseObj.getName());
        assertEquals(55, caseObj.getAge());

        // 3. 日期格式（yyyy-MM-dd HH:mm:ss）
        String jsonWithDate = "{\"name\":\"dateTest\",\"createTime\":\"2024-01-04 08:00:00\"}";
        TestObj dateObj = JsonUtils.json2Obj(jsonWithDate, new TypeReference<TestObj>() { });
        assertEquals("2024-01-04 08:00:00",
            new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(dateObj.getCreateTime()));

        // 4. 忽略null字段（SerializationInclusion.NON_NULL）
        TestObj nullFieldObj = new TestObj(null, 60, null);
        String nullFieldJson = JsonUtils.toJson(nullFieldObj);
        assertFalse(nullFieldJson.contains("name")); // name为null，被忽略
        assertTrue(nullFieldJson.contains("age"));
    }

    @Test
    public void test_objectToClass_normal_conversion() throws Exception {
        // Given
        ObjectMapper mockMapper = mock(ObjectMapper.class);
        Object inputObj = new Object();

        // When
        Object result = JsonUtils.objectToClass(inputObj);

        // Then
        assertNull(result);
    }

    @Test
    void test_objectToClass_should_not_throw_exception() throws Exception {
        // When
        Object result = JsonUtils.objectToClass(null);
        assertNull(result);
    }

    /**
     * 使用SLF4J Logger
     */
    private static final Logger logger = LoggerFactory.getLogger(JsonUtilsTest.class);

    /**
     * 测试 mergeDslData 方法
     * 场景1：正常合并，新数据优先
     * 场景2：新数据为null/空白，返回老数据
     * 场景3：老数据为null/空白，返回新数据
     * 场景4：新数据字段为空但老数据有值，使用老数据值
     * 场景5：嵌套对象合并
     * 场景6：JSON格式异常，返回新数据
     */
    @Test
    void testMergeDslData() {
        // 场景1：正常合并，新数据优先
        String newJson1 = "{\"name\":\"newAgent\",\"version\":\"2.0\",\"enabled\":true}";
        String oldJson1 = "{\"name\":\"oldAgent\",\"version\":\"1.0\",\"settings\":{\"timeout\":30}}";
        String result1 = JsonUtils.mergeDslData(newJson1, oldJson1, logger, "test1");
        JSONObject merged1 = JSON.parseObject(result1);
        assertEquals("newAgent", merged1.getString("name"));
        assertEquals("2.0", merged1.getString("version"));
        assertTrue(merged1.getBoolean("enabled"));
        assertEquals(30, merged1.getJSONObject("settings").getInteger("timeout"));

        // 场景2：新数据为null/空白，返回老数据
        String result2 = JsonUtils.mergeDslData(null, oldJson1, logger, "test2");
        assertEquals(oldJson1, result2);
        String result3 = JsonUtils.mergeDslData("", oldJson1, logger, "test3");
        assertEquals(oldJson1, result3);
        String result4 = JsonUtils.mergeDslData("   ", oldJson1, logger, "test4");
        assertEquals(oldJson1, result4);

        // 场景3：老数据为null/空白，返回新数据
        String result5 = JsonUtils.mergeDslData(newJson1, null, logger, "test5");
        assertEquals(newJson1, result5);
        String result6 = JsonUtils.mergeDslData(newJson1, "", logger, "test6");
        assertEquals(newJson1, result6);

        // 场景4：新数据字段为空但老数据有值，使用新数据中的空字符串
        String newJson4 = "{\"name\":\"\",\"version\":\"2.0\",\"enabled\":false}";
        String oldJson4 = "{\"name\":\"oldName\",\"version\":\"1.0\",\"enabled\":true,\"settings\":{\"timeout\":30}}";
        String result7 = JsonUtils.mergeDslData(newJson4, oldJson4, logger, "test7");
        JSONObject merged7 = JSON.parseObject(result7);
        assertEquals("", merged7.getString("name")); // 使用新数据中的空字符串
        assertEquals("2.0", merged7.getString("version"));  // 使用新数据值
        assertFalse(merged7.getBoolean("enabled"));       // 使用新数据值
        assertEquals(30, merged7.getJSONObject("settings").getInteger("timeout"));

        // 场景5：新数据字段为null但老数据有值，使用老数据值
        String newJson5 = "{\"name\":null,\"version\":\"2.0\",\"enabled\":false}";
        String oldJson5 = "{\"name\":\"oldName\",\"version\":\"1.0\",\"enabled\":true,\"settings\":{\"timeout\":30}}";
        String result7_2 = JsonUtils.mergeDslData(newJson5, oldJson5, logger, "test7_2");
        JSONObject merged7_2 = JSON.parseObject(result7_2);
        assertEquals("oldName", merged7_2.getString("name")); // 使用老数据值（新数据为null）
        assertEquals("2.0", merged7_2.getString("version"));  // 使用新数据值
        assertFalse(merged7_2.getBoolean("enabled"));       // 使用新数据值
        assertEquals(30, merged7_2.getJSONObject("settings").getInteger("timeout"));

        // 场景6：嵌套对象合并
        String newJson6 =
            "{\"name\":\"newAgent\",\"settings\":{\"timeout\":60,\"retry\":3},\"extra\":{\"newField\":\"value\"}}";
        String oldJson6 =
            "{\"name\":\"oldAgent\",\"settings\":{\"timeout\":30,\"maxConnections\":10},\"extra\":{\"oldField\":\"oldValue\"}}";
        String result8 = JsonUtils.mergeDslData(newJson6, oldJson6, logger, "test8");
        JSONObject merged8 = JSON.parseObject(result8);
        assertEquals("newAgent", merged8.getString("name"));
        JSONObject settings8 = merged8.getJSONObject("settings");
        assertEquals(60, settings8.getInteger("timeout"));  // 新数据优先
        assertEquals(3, settings8.getInteger("retry"));     // 新数据优先
        assertEquals(10, settings8.getInteger("maxConnections")); // 老数据优先
        JSONObject extra8 = merged8.getJSONObject("extra");
        assertEquals("value", extra8.getString("newField")); // 新数据优先
        assertEquals("oldValue", extra8.getString("oldField")); // 老数据优先

        // 场景6：JSON格式异常，返回新数据
        String invalidJson = "{\"invalid json}";
        String result9 = JsonUtils.mergeDslData(newJson1, invalidJson, logger, "test9");
        assertEquals(newJson1, result9); // 异常时返回新数据
    }

    /**
     * 测试 mergeJsonObjects 方法
     * 场景1：最基本的对象合并
     * 场景2：新数据为空的字符串字段，使用老数据值
     * 场景3：嵌套对象合并
     * 场景4：混合类型字段处理
     */
    @Test
    void testMergeJsonObjects() {
        // 场景1：最基本的对象合并
        JSONObject newJson1 = new JSONObject();
        newJson1.put("name", "newName");
        newJson1.put("age", 25);
        newJson1.put("enabled", true);

        JSONObject oldJson1 = new JSONObject();
        oldJson1.put("name", "oldName");
        oldJson1.put("city", "Beijing");
        oldJson1.put("enabled", false);

        JSONObject result1 = JsonUtils.mergeJsonObjects(newJson1, oldJson1, logger, "test1");
        assertEquals("newName", result1.getString("name"));  // 新数据优先
        assertEquals(25, result1.getInteger("age"));      // 新数据优先
        assertTrue(result1.getBoolean("enabled"));        // 新数据优先
        assertEquals("Beijing", result1.getString("city")); // 老数据优先（新数据中没有）

        // 场景2：新数据为空的字符串字段，使用新数据中的空字符串；新数据为null的值，使用老数据值
        JSONObject newJson2 = new JSONObject();
        newJson2.put("name", "");  // 空字符串，应该使用新数据
        newJson2.put("description", null); // null值，应该使用老数据
        newJson2.put("age", 30);

        JSONObject oldJson2 = new JSONObject();
        oldJson2.put("name", "notEmpty");
        oldJson2.put("description", "some description");
        oldJson2.put("age", 25);

        JSONObject result2 = JsonUtils.mergeJsonObjects(newJson2, oldJson2, logger, "test2");
        assertEquals("", result2.getString("name")); // 使用新数据中的空字符串
        assertEquals("some description", result2.getString("description")); // 使用老数据值（新数据为null）
        assertEquals(30, result2.getInteger("age")); // 使用新数据值

        // 场景3：嵌套对象合并
        JSONObject newJson3 = new JSONObject();
        JSONObject nestedNew = new JSONObject();
        nestedNew.put("timeout", 60);
        nestedNew.put("retry", 3);
        newJson3.put("settings", nestedNew);

        JSONObject oldJson3 = new JSONObject();
        JSONObject nestedOld = new JSONObject();
        nestedOld.put("timeout", 30);
        nestedOld.put("maxConnections", 10);
        oldJson3.put("settings", nestedOld);

        JSONObject result3 = JsonUtils.mergeJsonObjects(newJson3, oldJson3, logger, "test3");
        JSONObject settings3 = result3.getJSONObject("settings");
        assertEquals(60, settings3.getInteger("timeout"));      // 新数据优先
        assertEquals(3, settings3.getInteger("retry"));        // 新数据优先
        assertEquals(10, settings3.getInteger("maxConnections")); // 老数据优先

        // 场景4：新数据字段为空字符串，应该使用新数据中的空值
        JSONObject newJson4 = new JSONObject();
        newJson4.put("name", "");  // 空字符串，应该使用新数据
        newJson4.put("age", 100);

        JSONObject oldJson4 = new JSONObject();
        oldJson4.put("name", "oldName");  // 老数据有值
        oldJson4.put("age", 200);
        oldJson4.put("city", "Beijing");  // 老数据独有的字段

        JSONObject result4 = JsonUtils.mergeJsonObjects(newJson4, oldJson4, logger, "test4");
        assertEquals("", result4.getString("name")); // 使用新数据中的空字符串
        assertEquals(100, result4.getInteger("age"));      // 新数据优先
        assertEquals("Beijing", result4.getString("city")); // 老数据优先（新数据中没有）

        // 场景5：混合类型字段处理
        JSONObject newJson5 = new JSONObject();
        newJson5.put("intField", 100);
        newJson5.put("stringField", "test");
        newJson5.put("booleanField", false);
        newJson5.put("objectField", new JSONObject(Map.of("inner", "new")));

        JSONObject oldJson5 = new JSONObject();
        oldJson5.put("intField", 200);
        oldJson5.put("stringField", "old");
        oldJson5.put("booleanField", true);
        oldJson5.put("objectField", new JSONObject(Map.of("inner", "old")));
        oldJson5.put("onlyInOld", "onlyOldValue");

        JSONObject result5 = JsonUtils.mergeJsonObjects(newJson5, oldJson5, logger, "test5");
        assertEquals(100, result5.getInteger("intField"));      // 新数据优先
        assertEquals("test", result5.getString("stringField")); // 新数据优先
        assertFalse(result5.getBoolean("booleanField"));     // 新数据优先
        assertEquals("new", result5.getJSONObject("objectField").getString("inner")); // 新数据优先
        assertEquals("onlyOldValue", result5.getString("onlyInOld")); // 老数据优先
    }

    /**
     * 测试 mergeLists 方法
     * 场景1：新列表有值，返回新列表
     * 场景2：新列表为空，老列表有值，返回老列表
     * 场景3：两个列表都为空，返回空列表
     * 场景4：泛型测试，String类型
     * 场景5：泛型测试，Integer类型
     * 场景6：null列表处理
     */
    @Test
    void testMergeLists() {
        // 场景1：新列表有值，返回新列表
        List<String> newList1 = List.of("item1", "item2", "item3");
        List<String> oldList1 = List.of("old1", "old2");
        List<String> result1 = JsonUtils.mergeLists(newList1, oldList1);
        assertEquals(newList1, result1);
        assertEquals(3, result1.size());
        assertEquals("item1", result1.get(0));

        // 场景2：新列表为空，老列表有值，返回老列表
        List<String> newList2 = new ArrayList<>();
        List<String> oldList2 = List.of("oldItem1", "oldItem2");
        List<String> result2 = JsonUtils.mergeLists(newList2, oldList2);
        assertEquals(oldList2, result2);
        assertEquals(2, result2.size());
        assertEquals("oldItem1", result2.get(0));

        // 场景3：两个列表都为空，返回空列表
        List<String> newList3 = new ArrayList<>();
        List<String> oldList3 = new ArrayList<>();
        List<String> result3 = JsonUtils.mergeLists(newList3, oldList3);
        assertTrue(result3.isEmpty());
        assertEquals(0, result3.size());

        // 场景4：泛型测试，Integer类型
        List<Integer> newList4 = List.of(1, 2, 3, 4);
        List<Integer> oldList4 = List.of(10, 20, 30);
        List<Integer> result4 = JsonUtils.mergeLists(newList4, oldList4);
        assertEquals(newList4, result4);
        assertEquals(4, result4.size());
        assertEquals(1, result4.get(0));

        // 场景5：泛型测试，自定义对象类型
        List<TestObj> newList5 = List.of(new TestObj("obj1", 1, null), new TestObj("obj2", 2, null));
        List<TestObj> oldList5 = List.of(new TestObj("oldObj", 99, null));
        List<TestObj> result5 = JsonUtils.mergeLists(newList5, oldList5);
        assertEquals(newList5, result5);
        assertEquals(2, result5.size());
        assertEquals("obj1", result5.get(0).getName());

        // 场景6：null列表处理
        List<String> result6 = JsonUtils.mergeLists(null, oldList1);
        assertEquals(oldList1, result6);

        List<String> result7 = JsonUtils.mergeLists(newList1, null);
        assertEquals(newList1, result7);

        List<String> result8 = JsonUtils.mergeLists(null, null);
        assertTrue(result8.isEmpty());
    }

    @Test
    void test_sortJsonArrayByConfidence_with_ascending_order() {
        JSONArray jsonArray = new JSONArray();
        JSONObject obj1 = mock(JSONObject.class);
        JSONObject obj2 = mock(JSONObject.class);
        when(obj1.getDoubleValue(eq("confidence"))).thenReturn(0.8);
        when(obj2.getDoubleValue(eq("confidence"))).thenReturn(0.6);
        jsonArray.add(obj1);
        jsonArray.add(obj2);

        JsonUtils.sortJsonArrayByConfidence(jsonArray, true);
        assertEquals(0.6, jsonArray.getJSONObject(0).getDoubleValue("confidence"));
        assertEquals(0.8, jsonArray.getJSONObject(1).getDoubleValue("confidence"));
    }

    @Test
    void test_sortJsonArrayByConfidence_with_descending_order() {
        JSONArray jsonArray = new JSONArray();
        JSONObject obj1 = mock(JSONObject.class);
        JSONObject obj2 = mock(JSONObject.class);
        when(obj1.getDoubleValue(eq("confidence"))).thenReturn(0.8);
        when(obj2.getDoubleValue(eq("confidence"))).thenReturn(0.6);
        jsonArray.add(obj1);
        jsonArray.add(obj2);

        JsonUtils.sortJsonArrayByConfidence(jsonArray, false);
        assertEquals(0.8, jsonArray.getJSONObject(0).getDoubleValue("confidence"));
        assertEquals(0.6, jsonArray.getJSONObject(1).getDoubleValue("confidence"));
    }


}
