/* Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved. */
package com.openjiuwen.studio.agent.manager.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;

import org.junit.jupiter.api.Test;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.util.List;
import java.util.Map;

@MockitoSettings(strictness = Strictness.LENIENT)
class McpJsonUtilsTest {

    @Test
    void testToJson_ValidObject() {
        Map<String, String> map = Map.of("key", "value");
        String json = McpJsonUtils.toJson(map);
        assertNotNull(json);
        assertTrue(json.contains("\"key\""));
        assertTrue(json.contains("\"value\""));
    }

    @Test
    void testToJson_EmptyObject() {
        String json = McpJsonUtils.toJson(Map.of());
        assertEquals("{}", json);
    }

    @Test
    void testIsValidJson_ValidJson() {
        assertTrue(McpJsonUtils.isValidJson("{\"key\":\"value\"}"));
    }

    @Test
    void testIsValidJson_ValidArray() {
        assertTrue(McpJsonUtils.isValidJson("[1,2,3]"));
    }

    @Test
    void testIsValidJson_InvalidJson() {
        assertFalse(McpJsonUtils.isValidJson("{invalid}"));
    }

    @Test
    void testIsValidJson_PlainString() {
        assertFalse(McpJsonUtils.isValidJson("not json"));
    }

    @Test
    void testIsValidJson_JsonStringLiteral() {
        assertFalse(McpJsonUtils.isValidJson("\"异常\""));
    }

    @Test
    void testIsValidJson_JsonNumber() {
        assertFalse(McpJsonUtils.isValidJson("123"));
    }

    @Test
    void testIsValidJson_JsonBoolean() {
        assertFalse(McpJsonUtils.isValidJson("true"));
    }

    @Test
    void testIsValidJson_EmptyObject() {
        assertTrue(McpJsonUtils.isValidJson("{}"));
    }

    @Test
    void testFromJson_ValidJson() {
        Map result = McpJsonUtils.fromJson("{\"key\":\"value\"}", Map.class);
        assertNotNull(result);
        assertEquals("value", result.get("key"));
    }

    @Test
    void testFromJson_InvalidJson() {
        assertThrows(AgentStudioException.class, () -> McpJsonUtils.fromJson("invalid", Map.class));
    }

    @Test
    void testToList_ValidJsonArray() {
        List<String> result = McpJsonUtils.toList("[\"a\",\"b\",\"c\"]", String.class);
        assertNotNull(result);
        assertEquals(3, result.size());
        assertEquals("a", result.get(0));
    }

    @Test
    void testToList_InvalidJson() {
        assertThrows(AgentStudioException.class, () -> McpJsonUtils.toList("invalid", String.class));
    }

    @Test
    void testToMap_ValidJson() {
        Map<String, Object> result = McpJsonUtils.toMap("{\"a\":1,\"b\":2}", String.class, Object.class);
        assertNotNull(result);
        assertEquals(2, result.size());
    }

    @Test
    void testToMap_InvalidJson() {
        assertThrows(AgentStudioException.class,
            () -> McpJsonUtils.toMap("invalid", String.class, Object.class));
    }

    @Test
    void testFromJsonWithTypeReference_ValidJson() {
        List<String> result = McpJsonUtils.fromJson("[\"x\",\"y\"]", new TypeReference<List<String>>() {});
        assertNotNull(result);
        assertEquals(2, result.size());
    }

    @Test
    void testFromJsonWithTypeReference_InvalidJson() {
        assertThrows(AgentStudioException.class,
            () -> McpJsonUtils.fromJson("invalid", new TypeReference<List<String>>() {}));
    }

    @Test
    void testToPrettyJson_ValidObject() {
        Map<String, String> map = Map.of("key", "value");
        String pretty = McpJsonUtils.toPrettyJson(map);
        assertNotNull(pretty);
        assertTrue(pretty.contains("\n"));
    }

    @Test
    void testStrToJson_ValidJson() {
        JsonNode node = McpJsonUtils.strToJson("{\"key\":\"value\"}");
        assertNotNull(node);
        assertEquals("value", node.get("key").asText());
    }

    @Test
    void testStrToJson_InvalidJson() {
        JsonNode node = McpJsonUtils.strToJson("not json");
        assertNull(node);
    }

    @Test
    void testStrToJson_NullInput() {
        JsonNode node = McpJsonUtils.strToJson(null);
        assertNull(node);
    }

    @Test
    void testParseToolFromString_BlankInput() {
        var result = McpJsonUtils.parseToolFromString("", "testMcp");
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testParseToolFromString_NullInput() {
        var result = McpJsonUtils.parseToolFromString(null, "testMcp");
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testParseToolFromString_InvalidJson() {
        assertThrows(AgentStudioException.class,
            () -> McpJsonUtils.parseToolFromString("not json", "testMcp"));
    }
}
