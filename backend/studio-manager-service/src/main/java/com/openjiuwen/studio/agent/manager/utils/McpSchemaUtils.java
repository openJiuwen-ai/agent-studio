package com.openjiuwen.studio.agent.manager.utils;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SchemaConfig;

/** Converts MCP JSON Schema types to the single-type representation used by workflow IR. */
public final class McpSchemaUtils {
    private McpSchemaUtils() {
    }

    /**
     * Normalize type arrays before Fastjson maps them to SchemaConfig's String type field.
     * Only a single non-null type can be represented by workflow IR. Required/default
     * metadata is left unchanged; nullable does not mean that a parameter is optional.
     *
     * @param schema MCP tool input or output schema
     * @return parsed schema, or null for an absent schema
     */
    public static SchemaConfig parseWorkflowSchema(String schema) {
        JSONObject parsed = JSON.parseObject(schema);
        if (parsed == null) {
            return null;
        }
        normalize(parsed, "$");
        return parsed.toJavaObject(SchemaConfig.class);
    }

    private static void normalize(JSONObject schema, String path) {
        Object type = schema.get("type");
        if (type instanceof JSONArray types) {
            schema.put("type", concreteType(types, path));
        }
        Object properties = schema.get("properties");
        if (properties instanceof JSONObject children) {
            children.forEach((name, child) -> {
                if (child instanceof JSONObject childSchema) {
                    normalize(childSchema, path + ".properties[" + JSON.toJSONString(name) + "]");
                }
            });
        }
        if (schema.get("items") instanceof JSONObject items) {
            normalize(items, path + ".items");
        }
        if (schema.get("oneOf") instanceof JSONArray alternatives) {
            for (int i = 0; i < alternatives.size(); i++) {
                if (alternatives.get(i) instanceof JSONObject alternative) {
                    normalize(alternative, path + ".oneOf[" + i + "]");
                }
            }
        }
    }

    private static String concreteType(JSONArray types, String path) {
        String concrete = null;
        for (Object value : types) {
            if (!(value instanceof String candidate)) {
                throw unsupportedType(path);
            }
            if ("null".equals(candidate)) {
                continue;
            }
            if (concrete != null && !concrete.equals(candidate)) {
                throw unsupportedType(path);
            }
            concrete = candidate;
        }
        if (concrete == null) {
            throw unsupportedType(path);
        }
        return concrete;
    }

    private static IllegalArgumentException unsupportedType(String path) {
        return new IllegalArgumentException("Unsupported MCP schema type array at " + path
            + ".type: workflow IR requires exactly one non-null string type");
    }
}
