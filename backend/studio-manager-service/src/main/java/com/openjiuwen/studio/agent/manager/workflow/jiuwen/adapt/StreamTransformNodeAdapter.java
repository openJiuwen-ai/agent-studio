/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
public class StreamTransformNodeAdapter extends AbstractIRNodeAdapter {

    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String TRANSFORMER = "transformer";

    private static final String FRAME_TEMPLATE = "frame_template";

    private static final String FINAL_TEMPLATE = "final_template";

    private static final String CONCAT = "concat";

    private static final String SRC_PATH = "src_path";

    private static final String EMIT_FINAL_CONCAT_FRAME = "emit_final_concat_frame";

    private static final String PRUNE_NONE_FIELDS = "prune_none_fields";

    private static final String ADD_IS_LAST = "add_is_last";

    private static final String USER_FIELDS = "userFields";

    private static final String VARIABLES = "variables";

    private static final String SYSTEM_FIELDS = "systemFields";

    private static final String SOURCE_TYPE = "sourceType";

    private static final String INPUTS = "inputs";

    private static final String OUTPUTS = "outputs";

    private static final String ID = "id";

    private static final String TYPE = "type";

    private static final String REQUIRED = "required";

    private static final String REF_PARAMETERS_TYPE = "ref";

    private static final String NAME = "name";

    private static final Pattern DYNAMIC_VAR_PATTERN = Pattern.compile("\\{\\{(?<inputVarName>.*?)\\.(?<srcPath>.*?)"
        + "\\}\\}");

    @Override
    public String getNodeType() {
        return NodeType.STREAM_TRANSFORM.getIrType();
    }

    @Override
    @SuppressWarnings("unchecked")
    public Map<String, Object> adaptConfig(WorkflowNodeVO workflowNodeVo) {
        Map<String, Object> configs = new HashMap<>();

        Map<String, Object> nodeConfigs = workflowNodeVo.getConfigs();
        List<WorkflowFieldVO> inputs = workflowNodeVo.getInputs();

        // 1. 获取输入参数名称
        String inputVarNames = extractInputNames(inputs);

        // 2. 获取 transformer 部分
        Map<String, Object> originTransformer = (Map<String, Object>) nodeConfigs.get(TRANSFORMER);
        if (originTransformer == null) {
            throw new AgentStudioException(StudioError.MISSING_TRANSFORMER);
        }

        // 获取中间帧格式
        String originFrameTemplate = (String) originTransformer.get(FRAME_TEMPLATE);

        // 获取聚合字段
        List<String> concatFields = (List<String>) nodeConfigs.get(CONCAT);

        // 3. 解析模板并生成变量映射
        List<Map<String, Object>> variables = new ArrayList<>();
        String frameTemplate = processStreamNodeFrameTemplateAndVariables(originFrameTemplate, concatFields, inputVarNames, variables);

        // 4. 构建 IR Config 结构
        Map<String, Object> irTransformer = new HashMap<>();
        irTransformer.put(VARIABLES, variables);

        // 尝试解析为 JSON 对象
        // 支持纯占位符格式（如 {{raw_output}}）：将整个输入作为帧引用
        if (variables.isEmpty() && frameTemplate.matches("\\{\\{[^.}]+\\}\\}")) {
            // 纯占位符：创建变量，name 和 src_path 都设为实际输入参数名
            // 这样 _build_transformer_config 会匹配 v.name == _source_field 并清空 src_path
            // 运行时 _read_src 在 src_path 为空时返回整个帧对象
            Map<String, Object> wholeInputVar = new HashMap<>();
            wholeInputVar.put(NAME, inputVarNames);
            wholeInputVar.put(SRC_PATH, inputVarNames);
            wholeInputVar.put(CONCAT, false);
            variables.add(wholeInputVar);
            irTransformer.put(VARIABLES, variables);
            // frame_template 使用实际输入参数名引用
            String wrappedTemplate = "{\"" + inputVarNames + "\": \"{{" + inputVarNames + "}}\"}";
            try {
                irTransformer.put(FRAME_TEMPLATE, objectMapper.readTree(wrappedTemplate));
                irTransformer.put(FINAL_TEMPLATE, objectMapper.readTree(wrappedTemplate));
            } catch (Exception e) {
                throw new AgentStudioException(StudioError.FRAME_TEMPLATE_INVALID_JSON);
            }
        } else {
            try {
                irTransformer.put(FRAME_TEMPLATE, objectMapper.readTree(frameTemplate));
                irTransformer.put(FINAL_TEMPLATE, objectMapper.readTree(convertJson(variables, frameTemplate)));
            } catch (Exception e) {
                throw new AgentStudioException(StudioError.FRAME_TEMPLATE_INVALID_JSON);
            }
        }

        // 有聚合字段时，必须设置成true
        if (!concatFields.isEmpty()) {
            irTransformer.put(EMIT_FINAL_CONCAT_FRAME, true);
        }
        irTransformer.put(PRUNE_NONE_FIELDS, false);
        irTransformer.put(ADD_IS_LAST, false);

        // 设置固定配置项
        complementFieldsConfig(configs, inputVarNames);

        configs.put(TRANSFORMER, irTransformer);
        return configs;
    }

    /**
     * 流式处理节点：
     * 1. 获取variables,
     * 比如：中间帧的结构中存在 {"content": "{{raw_output.content[0].text}}"},
     * 则生成一个 {"name": "ref_1", "src_path": content[0].text, "concat": false}
     * 2. 转换中间帧
     * 比如：中间帧的结构中存在 {"content": "{{raw_output.content[0].text}}"},
     * 则转换为 {"content": "{{ref_1}}"}
     * @return  转换后的中间帧
     */
    private String processStreamNodeFrameTemplateAndVariables(String frameTemplateDslStr,
        List<String> concatFields,
        String inputName,
        List<Map<String, Object>> variables) {

        if (frameTemplateDslStr == null) {
            throw new AgentStudioException(StudioError.MISSING_FRAME_TEMPLATE);
        }

        Matcher matcher = DYNAMIC_VAR_PATTERN.matcher(frameTemplateDslStr);
        StringBuilder sb = new StringBuilder();
        while (matcher.find()) {
            String inputVarName = matcher.group("inputVarName");
            String srcPath = matcher.group("srcPath");

            if (inputName.equals(inputVarName)) {
                String refName = "ref_" + (variables.size() + 1);
                Map<String, Object> varEntry = new HashMap<>();
                varEntry.put(NAME, refName);
                varEntry.put(SRC_PATH, srcPath);

                // 判断是否需要聚合
                for (String concatField : concatFields) {
                    // 只获取第一个.的后面部分
                    String processedConcatField = concatField.replaceFirst(inputName + "\\.", "");

                    if (processedConcatField.equals(srcPath)) {
                        varEntry.put(CONCAT, true);
                    }
                }
                variables.add(varEntry);
                matcher.appendReplacement(sb, "{{" + refName + "}}");
            } else {
                matcher.appendReplacement(sb, matcher.group(0));
            }
        }

        matcher.appendTail(sb);
        return sb.toString();
    }

    /**
     * 流式处理节点： 获取输入参数名字, 流式处理节点只允许有一个输入
     */
    private String extractInputNames(List<WorkflowFieldVO> inputs) {
        if (inputs.size() != 1) {
            throw new AgentStudioException("Invalid inputs format");
        }

        WorkflowFieldVO input = inputs.get(0);
        return input.getName();
    }

    /**
     * 流式处理节点： 补全节点缺失的 userFields 和 systemFields 配置
     */
    private void complementFieldsConfig(Map<String, Object> nodeConfig, String inputName) {
        // 1. 构造 userFields
        Map<String, Object> userFields = new HashMap<>();
        List<Map<String, Object>> userInputs = new ArrayList<>();


        Map<String, Object> inputItem = new HashMap<>();
        inputItem.put(ID, inputName);
        inputItem.put(TYPE, "object");
        inputItem.put(REQUIRED, true);
        inputItem.put(SOURCE_TYPE, REF_PARAMETERS_TYPE);
        userInputs.add(inputItem);


        userFields.put(INPUTS, userInputs);
        userFields.put(OUTPUTS, new ArrayList<>());

        // 2. 构造 systemFields
        Map<String, Object> systemFields = new HashMap<>();
        systemFields.put(INPUTS, new ArrayList<>());
        systemFields.put(OUTPUTS, new ArrayList<>());

        nodeConfig.put(USER_FIELDS, userFields);
        nodeConfig.put(SYSTEM_FIELDS, systemFields);
    }

    /**
     * 核心转换方法
     * @param configList List<Map<String, Object>> 配置
     * @param sourceJson 原始JSON字符串
     * @return 过滤后的JSON
     */
    public String convertJson(List<Map<String, Object>> configList, String sourceJson) {
        try {
            // ===================== 关键：只收集 concat=true 的 name =====================
            Set<String> validRefNames = new HashSet<>();
            for (Map<String, Object> config : configList) {
                boolean concat = Boolean.parseBoolean(String.valueOf(config.getOrDefault("concat", false)));
                // 只有 concat=true 才保留
                if (concat) {
                    validRefNames.add(config.get("name").toString());
                }
            }

            // 解析原始JSON
            JsonNode sourceNode = objectMapper.readTree(sourceJson);

            // 递归过滤
            ObjectNode resultNode = (ObjectNode) filterValidFields(sourceNode, validRefNames);

            // 格式化输出
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(resultNode);
        } catch (Exception e) {
            log.error("Failed to convert json", e);
            return sourceJson;
        }
    }

    /**
     * 递归过滤：只保留 值包含【concat=true 的 name】的字段
     */
    private JsonNode filterValidFields(JsonNode node, Set<String> validRefNames) {
        if (!node.isObject()) {
            return node;
        }

        ObjectNode result = objectMapper.createObjectNode();
        ObjectNode sourceObj = (ObjectNode) node;

        sourceObj.fields().forEachRemaining(entry -> {
            String fieldName = entry.getKey();
            JsonNode value = entry.getValue();

            // 1. 跳过 null
            if (value.isNull()) {
                return;
            }

            // 2. 递归处理嵌套对象
            if (value.isObject()) {
                JsonNode filteredChild = filterValidFields(value, validRefNames);
                if (!filteredChild.isEmpty()) {
                    result.set(fieldName, filteredChild);
                }
                return;
            }

            // 3. 字符串：只保留包含【合法name】的字段（concat=true）
            if (value.isTextual()) {
                String text = value.asText();
                boolean match = validRefNames.stream().anyMatch(text::contains);
                if (match) {
                    result.put(fieldName, text);
                }
            }
        });

        return result;
    }
}
