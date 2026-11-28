package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson2.JSON;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class McpSchemaUtilsTest {
    @ParameterizedTest
    @ValueSource(strings = {"string", "integer", "number", "boolean", "object", "array"})
    void nullableTypeWorksInEitherOrder(String type) {
        for (String types : List.of("[\"null\",\"" + type + "\"]", "[\"" + type + "\",\"null\"]")) {
            SchemaConfig parsed = McpSchemaUtils.parseWorkflowSchema("{\"type\":" + types + "}");
            assertEquals(type, parsed.getType());
        }
    }

    @Test
    void preservesNestedArrayObjectsAndRequiredFields() {
        SchemaConfig parsed = McpSchemaUtils.parseWorkflowSchema("""
            {
              "type": "object",
              "required": ["files"],
              "properties": {
                "files": {
                  "type": ["null", "array"],
                  "items": {
                    "type": ["object", "null"],
                    "required": ["name"],
                    "properties": {
                      "name": {"type": ["string", "null"]},
                      "metadata": {
                        "type": ["null", "object"],
                        "properties": {"size": {"type": ["null", "integer"]}}
                      }
                    }
                  }
                },
                "wait_seconds": {"type": ["null", "integer"], "default": 0}
              }
            }
            """);
        assertEquals(List.of("files"), parsed.getRequired());
        SchemaConfig files = parsed.getProperties().get("files");
        assertEquals("array", files.getType());
        assertEquals("object", files.getItems().getType());
        assertEquals(List.of("name"), files.getItems().getRequired());
        assertEquals("string", files.getItems().getProperties().get("name").getType());
        SchemaConfig metadata = files.getItems().getProperties().get("metadata");
        assertEquals("object", metadata.getType());
        assertEquals("integer", metadata.getProperties().get("size").getType());
        assertEquals("0", parsed.getProperties().get("wait_seconds").getDefaultValue());
    }

    @Test
    void preservesScalarSchemaAndOpaqueDefaultData() {
        String schema = """
            {
              "type": "object", "required": ["query"],
              "properties": {
                "query": {"type": "string", "description": "Query", "default": "hello"},
                "options": {
                  "type": "object",
                  "default": {"type": ["string", "integer"], "properties": {"type": "data"}}
                },
                "flag": {"type": "boolean", "default": false},
                "empty": {"type": "integer", "default": null}
              }
            }
            """;
        assertEquals(JSON.parseObject(schema, SchemaConfig.class), McpSchemaUtils.parseWorkflowSchema(schema));
    }

    @Test
    void preservesNullDefaultAndRequiredNullableParameter() {
        SchemaConfig parsed = McpSchemaUtils.parseWorkflowSchema("""
            {"type":"object","required":["value"],"properties":{
              "value":{"type":["null","integer"],"default":null}
            }}
            """);
        assertEquals(List.of("value"), parsed.getRequired());
        assertNull(parsed.getProperties().get("value").getDefaultValue());
    }

    @Test
    void preservesAbsentSchemas() {
        assertNull(McpSchemaUtils.parseWorkflowSchema(null));
        assertNull(McpSchemaUtils.parseWorkflowSchema(""));
        assertNull(McpSchemaUtils.parseWorkflowSchema("null"));
        assertNull(McpSchemaUtils.parseWorkflowSchema("{}").getType());
    }

    @Test
    void acceptsSingleTypeArray() {
        assertEquals("integer", McpSchemaUtils.parseWorkflowSchema("{\"type\":[\"integer\"]}").getType());
    }

    @ParameterizedTest
    @ValueSource(strings = {"", ",\"items\":null", ",\"items\":{}"})
    void nullableArrayWithoutItemConstraintsKeepsItemsAbsent(String items) {
        SchemaConfig parsed = McpSchemaUtils.parseWorkflowSchema("{\"type\":[\"null\",\"array\"]" + items + "}");
        assertEquals("array", parsed.getType());
        assertNull(parsed.getItems());
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "{\"properties\":{\"name\":{\"type\":\"string\"}}}",
        "{\"oneOf\":[{\"type\":\"object\"},{\"type\":\"null\"}]}",
        "{\"type\":null}", "{\"type\":\"\"}"
    })
    void constrainedArrayItemsWithoutATypeFailWithTheirPath(String items) {
        String schema = "{\"type\":\"object\",\"properties\":{\"files\":{"
            + "\"type\":[\"null\",\"array\"],\"items\":" + items + "}}}";
        IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
            () -> McpSchemaUtils.parseWorkflowSchema(schema));
        assertTrue(error.getMessage().contains("$.properties[\"files\"].items.type"));
    }

    @Test
    void preservesExistingOneOfRepresentation() {
        SchemaConfig parsed = McpSchemaUtils.parseWorkflowSchema("""
            {"oneOf":[{"type":"object","properties":{"count":{"type":["null","integer"]}}},
                      {"type":"null"}]}
            """);
        assertNull(parsed.getType());
        assertEquals(2, parsed.getOneOf().size());
        assertEquals("object", parsed.getOneOf().get(0).getType());
        assertEquals("integer", parsed.getOneOf().get(0).getProperties().get("count").getType());
        assertEquals("null", parsed.getOneOf().get(1).getType());
    }

    @ParameterizedTest
    @ValueSource(strings = {"[\"string\",\"integer\"]", "[\"null\",\"object\",\"array\"]",
        "[]", "[\"null\"]", "[null,\"integer\"]", "[1,\"integer\"]"})
    void rejectsUnrepresentableTypeArraysWithParameterPath(String types) {
        String schema = "{\"type\":\"object\",\"properties\":{\"files\":{\"type\":\"array\","
            + "\"items\":{\"type\":" + types + "}}}}";
        IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
            () -> McpSchemaUtils.parseWorkflowSchema(schema));
        assertTrue(error.getMessage().contains("$.properties[\"files\"].items.type"));
    }
}
