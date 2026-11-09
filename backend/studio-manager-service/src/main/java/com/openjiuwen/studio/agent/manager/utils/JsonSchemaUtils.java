/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.utils;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.enums.JsonSchemaType;
import com.openjiuwen.studio.agent.manager.enums.ToolParamLocation;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.lang3.StringUtils;

import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * JsonSchema工具类
 *
 */
@Slf4j
public class JsonSchemaUtils {
    private static final String TYPE = "type";

    private static final String LOCATION = "location";

    private static final String DESCRIPTION = "description";

    private static final String DEFAULT = "default";

    private static final String OBJECT_KEY = "properties";

    private static final String MAP_KEY = "additionalProperties";

    private static final String ARRAY_KEY = "items";

    private JsonSchemaUtils() {
    }

    /**
     * 校验JsonSchema格式是否有效
     *
     * @param jsonSchema JsonSchema字符串
     * @param maxPropLimit 模型支持的最大属性数量
     * @param maxDepthLimit 模型支持的最大嵌套深度
     * @param isInput 是否为输入JsonSchema
     * @return true：有效；非法时抛出 {@link AgentStudioException}，details 中带属性名与缺失字段
     */
    public static boolean isJsonSchemaValid(String jsonSchema, int maxPropLimit, int maxDepthLimit, boolean isInput) {
        if (StringUtils.isBlank(jsonSchema)) {
            return true;
        }
        ObjectMapper mapper = new ObjectMapper();
        JsonNode schemaNode;
        try {
            schemaNode = mapper.readTree(jsonSchema);
        } catch (JsonProcessingException exception) {
            log.error("The format of tool json schema is invalid");
            throw invalid("The schema is not valid JSON.");
        }
        JsonSchemaNode node = new JsonSchemaNode(schemaNode, 0, false, isInput);
        return isJsonSchemaValid(node, maxPropLimit, maxDepthLimit);
    }

    /**
     * 递归判断JsonNode及其子Node是否满足格式要求
     *
     * @param node JsonSchemaNode
     * @param maxPropLimit 每层字段的最大数量
     * @param maxDepthLimit Json最大深度，比如 arr[arr[str]]、arr[object] 深度都是2
     * @return true：当前JsonNode满足校验；非法时抛异常
     */
    private static boolean isJsonSchemaValid(JsonSchemaNode node, int maxPropLimit, int maxDepthLimit) {
        // 1、递归边界条件判断

        // 节点深度大于限制
        int depth = node.getDepth();
        if (depth > maxDepthLimit) {
            throw invalid("The parameter nesting depth cannot exceed " + maxDepthLimit + ".");
        }

        JsonNode jsonNode = node.getNode();
        if (Objects.isNull(jsonNode)) {
            // array 缺 items 时 son 为 null
            if (node.isArraySonNode()) {
                throw invalid(String.format("%s is missing required field [items].", label(node)));
            }
            throw invalid(String.format("%s is missing required field [type].", label(node)));
        }
        if (Objects.isNull(jsonNode.get(TYPE))) {
            throw invalid(String.format("%s is missing required field [type].", label(node)));
        }
        String type = jsonNode.get(TYPE).asText();
        if (isNotJsonSchemaType(type)) {
            log.error("type:{} is not json schema type.", type);
            throw invalid(String.format("%s has unsupported type [%s].", label(node), type));
        }

        checkNodeField(jsonNode, depth, node);

        // 当前节点是基础类型，无子节点
        if (isFoundationJsonSchemaType(type)) {
            return true;
        }

        // 2、分情况获取子节点，进行递归

        if (JsonSchemaType.ARRAY.type.equals(type)) {
            return isArrayNodeValid(node, depth, maxPropLimit, maxDepthLimit);
        }

        return isObjectNodeValid(node, depth, maxPropLimit, maxDepthLimit);
    }

    /**
     * 校验数组子节点
     */
    private static boolean isArrayNodeValid(JsonSchemaNode node, int depth, int maxPropLimit, int maxDepthLimit) {
        JsonNode sonNode = node.getNode().get(ARRAY_KEY);
        // 将父参数名传入 items，嵌套数组等错误可指出属性名
        JsonSchemaNode schemaSonNode = new JsonSchemaNode(sonNode, depth, true, node.getName(), node.isInputNode());
        return isJsonSchemaValid(schemaSonNode, maxPropLimit, maxDepthLimit);
    }

    /**
     * 校验Object子节点
     */
    private static boolean isObjectNodeValid(JsonSchemaNode node, int depth, int maxPropLimit, int maxDepthLimit) {
        JsonNode sonNode;
        JsonSchemaNode schemaSonNode;

        sonNode = node.getNode().get(MAP_KEY);
        if (!Objects.isNull(sonNode)) {
            throw invalid(String.format("%s must not use [additionalProperties] (not supported).", label(node)));
        }

        sonNode = node.getNode().get(OBJECT_KEY);
        if (Objects.isNull(sonNode)) {
            throw invalid(String.format("%s is missing required field [properties].", label(node)));
        }
        Iterator<JsonNode> elements = sonNode.elements();
        Iterator<String> fieldNames = sonNode.fieldNames();
        int size = 0;
        while (elements.hasNext()) {
            JsonNode innerNode = elements.next();
            String filedName = fieldNames.next();
            schemaSonNode = new JsonSchemaNode(innerNode, depth + 1, false, filedName, node.isInputNode());
            size++;
            isJsonSchemaValid(schemaSonNode, maxPropLimit, maxDepthLimit);
        }
        if (size < 1) {
            throw invalid(String.format("%s field [properties] cannot be empty.", label(node)));
        }
        if (size > maxPropLimit) {
            throw invalid(String.format(
                "%s has %d properties, which exceeds the limit of %d.", label(node), size, maxPropLimit));
        }
        return true;
    }

    /**
     * 判断当前字段类型，是否不属于JsonSchema类型。
     *
     * FEAT-073：file/<子类型>（如 file/image、file/video、file/default）为插件
     * File 类型入参的合法类型标识，与开始节点 File 参数、运行时引擎的识别
     * 体系三方一致，按前缀放行。
     *
     * @param type 字段类型
     * @return true：不属于JsonSchema类型，false：属于JsonSchema类型
     */
    private static boolean isNotJsonSchemaType(String type) {
        if (type != null && type.startsWith("file/")) {
            return false;
        }
        return Arrays.stream(JsonSchemaType.values()).noneMatch(jsonSchemaType -> jsonSchemaType.type.equals(type));
    }

    /**
     * 判断当前字段类型，是否属于基础类型（用于判断嵌套深度）
     * 基础类型包括：String、number、integer、boolean、null
     *
     * @param type 字段类型
     * @return true：属于基础类型，false：不属于基础类型
     */
    private static boolean isFoundationJsonSchemaType(String type) {
        if (isNotJsonSchemaType(type)) {
            return false;
        }
        return !JsonSchemaType.ARRAY.type.equals(type) && !JsonSchemaType.OBJECT.type.equals(type);
    }

    /**
     * 插件参数的属性校验
     *
     * @param jsonNode JsonNode
     * @param depth 嵌套深度
     * @param node JsonSchemaNode
     */
    private static void checkNodeField(JsonNode jsonNode, int depth, JsonSchemaNode node) {
        // jsonSchema最外层无需校验
        if (depth == 0) {
            return;
        }
        String type = jsonNode.get(TYPE).asText();
        String name = node.getName();
        if (node.isArraySonNode()) {
            // 不支持数组嵌套数组
            if (JsonSchemaType.ARRAY.type.equals(type)) {
                throw invalid(String.format("The parameter [%s] cannot be nested array.",
                    StringUtils.defaultIfBlank(name, "items")));
            }
            // 数组的子节点无需校验 description/location
            return;
        }
        // 响应参数无需其他校验
        if (!node.isInputNode()) {
            return;
        }

        // 描述，必填
        if (Objects.isNull(jsonNode.get(DESCRIPTION)) || StringUtils.isBlank(jsonNode.get(DESCRIPTION).asText())) {
            throw invalid(String.format("The parameter [%s] is missing required field [description].", name));
        }
        // 位置，必填，且只能取 Body Headers Query 和 Path
        if (Objects.isNull(jsonNode.get(LOCATION)) || StringUtils.isBlank(jsonNode.get(LOCATION).asText())
            || Arrays.stream(ToolParamLocation.values())
                .noneMatch(toolParam -> toolParam.location.equals(jsonNode.get(LOCATION).asText()))) {
            throw invalid(String.format(
                "The parameter [%s] is missing required field [location] "
                    + "(must be one of: Body, Headers, Query, Path).",
                name));
        }
        // 默认值，非必填，值要与参数类型匹配
        if (Objects.nonNull(jsonNode.get(DEFAULT))) {
            JsonNode defaultNode = jsonNode.get(DEFAULT);
            if (StringUtils.isBlank(defaultNode.asText())) {
                return;
            }
            // FEAT-073：file/<子类型>（file/image 等）不在 JsonSchemaType 枚举内，
            // valueOf 会抛 IllegalArgumentException 使接口 500 而非受控错误；
            // 其默认值为文件 URL 字符串，无 number/integer/boolean 格式校验，直接放行
            if (type.startsWith("file/")) {
                return;
            }
            switch (JsonSchemaType.valueOf(type.toUpperCase(Locale.ROOT))) {
                case NUMBER:
                    if (!isNumber(defaultNode.asText())) {
                        throw invalid(String.format(
                            "The parameter [%s]'s default value must be a number.", name));
                    }
                    break;
                case INTEGER:
                    if (!isInteger(defaultNode.asText())) {
                        throw invalid(String.format(
                            "The parameter [%s]'s default value must be an integer.", name));
                    }
                    break;
                case BOOLEAN:
                    if (!isBoolean(defaultNode.asText())) {
                        throw invalid(String.format(
                            "The parameter [%s]'s default value must be a boolean.", name));
                    }
                    break;
                default:
                    break;
            }
        }
    }

    private static String label(JsonSchemaNode node) {
        if (StringUtils.isNotBlank(node.getName())) {
            return "The parameter [" + node.getName() + "]";
        }
        return "The schema root";
    }

    private static AgentStudioException invalid(String detail) {
        // details + args[0]：若未被 remap 为 02401002/003，对外 02401001 也能带上具体原因
        return new AgentStudioException(StudioError.TOOL_INPUT_INVALID, List.of(detail), detail);
    }

    private static boolean isBoolean(String defaultValue) {
        return "true".equalsIgnoreCase(defaultValue) || "false".equalsIgnoreCase(defaultValue);
    }

    private static boolean isInteger(String defaultValue) {
        if (defaultValue == null) {
            return false;
        }
        try {
            Integer.parseInt(defaultValue);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    private static boolean isNumber(String defaultValue) {
        if (defaultValue == null) {
            return false;
        }
        try {
            Double.parseDouble(defaultValue);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /**
     * json schema 节点
     */
    @Data
    static class JsonSchemaNode {
        /**
         * 节点
         */
        private JsonNode node;

        /**
         * 是否为数组子节点
         */
        private boolean isArraySonNode;

        /**
         * 嵌套层数
         */
        private int depth;

        /**
         * 节点属性名
         */
        private String name;

        /**
         * 是否为入参节点
         */
        private boolean isInputNode;

        JsonSchemaNode(JsonNode node, int depth, boolean isArraySonNode, boolean isInputNode) {
            this(node, depth, isArraySonNode, null, isInputNode);
        }

        JsonSchemaNode(JsonNode node, int depth, boolean isArraySonNode, String name, boolean isInputNode) {
            this.node = node;
            this.depth = depth;
            this.isArraySonNode = isArraySonNode;
            this.name = name;
            this.isInputNode = isInputNode;
        }
    }
}
