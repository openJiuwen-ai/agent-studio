/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.VariableEnum;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.utils.MapReadUtil;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

@SuppressWarnings("unchecked")
@Component
public class LLMNodeConverter extends AbstractSDSLNodeConverter {

    @Override
    public Boolean supportNodeType(NodeType nodeType) {
        return NodeType.LLM.equals(nodeType);
    }

    @Override
    public WorkflowNodeVO adapt(Map<String, Object> data, WorkflowNodeVO workflowNodeVO, Map<String, WorkflowNodeVO> workflowNodeMap) {
        workflowNodeVO.setType(NodeType.LLM.getType());
        List<WorkflowFieldVO> needConvertFields = new ArrayList<>();
        workflowNodeVO.setConfigs(adaptConfigs(data, needConvertFields, workflowNodeMap));
        workflowNodeVO.setInputs(needConvertFields);
        workflowNodeVO.setOutputs(adaptOutputs(data));
        return workflowNodeVO;
    }

    @SuppressWarnings("unchecked")
    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        List<WorkflowFieldVO> outputs = new ArrayList<>();
        WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO()
                .setName("text")
                .setSource(WorkflowFieldVO.SourceEnum.USER)
                .setType(VariableEnum.TEXT_INPUT.getDslType())
                .setDescription("该节点原始输出")
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                        .setContent(""));
        outputs.add(workflowFieldVO);
        // 非JSON格式返回固定text
        if (!data.containsKey("structured_output_enabled") || !(Boolean) data.get("structured_output_enabled")) {
            return outputs;
        }

        Map<String, Object> structuredOutputMap = MapReadUtil.safeCastToMapWithStringKey(data.get("structured_output"));
        if (structuredOutputMap == null) {
            return outputs;
        }
        Map<String, Object> schemaMap = MapReadUtil.safeCastToMapWithStringKey(structuredOutputMap.get("schema"));
        WorkflowFieldVO rootFieldVO = getWorkflowFieldVO(schemaMap, "structured_output");
        outputs.add(rootFieldVO);
        return outputs;
    }

    /**
     * 递归解析字段定义
     *
     * @param fieldDef  字段定义 Map (即 schema 定义)
     * @param fieldName 字段名称
     * @return 解析后的 WorkflowFieldVO
     */
    private WorkflowFieldVO getWorkflowFieldVO(Map<String, Object> fieldDef, String fieldName) {
        WorkflowFieldVO fieldVO = new WorkflowFieldVO();
        fieldVO.setName(fieldName);

        String type = "object"; // 默认值
        if (fieldDef != null && fieldDef.containsKey("type")) {
            type = String.valueOf(fieldDef.get("type"));
        }
        fieldVO.setType(type);

        if (fieldDef != null && fieldDef.containsKey("description")) {
            fieldVO.setDescription(String.valueOf(fieldDef.get("description")));
        } else {
            fieldVO.setDescription(fieldName);
        }
        fieldVO.setRequired(false);
        fieldVO.setSource(WorkflowFieldVO.SourceEnum.USER);
        fieldVO.setValue(new WorkflowFieldVOValue()
                .setHint("")
                .setDefault("")
                .setType(WorkflowFieldVOValue.TypeEnum.GENERATED));

        if (fieldDef == null) {
            return fieldVO;
        }

        if ("object".equals(type)) {
            Map<String, Object> nestedProperties = MapReadUtil.safeCastToMapWithStringKey(fieldDef.get("properties"));
            if (nestedProperties != null && !nestedProperties.isEmpty()) {
                List<WorkflowFieldVO> schemaList = new ArrayList<>();
                for (Map.Entry<String, Object> nestedEntry : nestedProperties.entrySet()) {
                    // 递归解析子字段
                    schemaList.add(getWorkflowFieldVO((Map<String, Object>) nestedEntry.getValue(), nestedEntry.getKey()));
                }
                fieldVO.setSchema(schemaList);
            }
        }

        if ("array".equals(type)) {
            Map<String, Object> itemsDef = MapReadUtil.safeCastToMapWithStringKey(fieldDef.get("items"));
            if (itemsDef != null) {
                WorkflowFieldVO itemsVO = getWorkflowFieldVO(itemsDef, "");
                fieldVO.setSchema(itemsVO);
            }
        }
        return fieldVO;
    }

    /**
     * 适配大模型节点的configs，dify中没有输入参数，只存在引用变量，需要将prompt中引用的变量转变为输入参数
     * @param data
     * @param needConvertFields
     * @param workflowNodeMap
     * @return
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> adaptConfigs(Map<String, Object> data, List<WorkflowFieldVO> needConvertFields, Map<String, WorkflowNodeVO> workflowNodeMap) {
        Map<String, Object> configs = new HashMap<>();
        configs.put(CommonConstant.DIFY.CONFIG_DEFAULT_NAME, false);
        Map<String, Object> modelConfig = MapReadUtil.safeCastToMapWithStringKey(data.get("model"));
        if (modelConfig != null) {
            Map<String, String> modelInfo = new HashMap<>();
            String modelName = modelConfig.get("name").toString();
            modelInfo.put(CommonConstant.ModelParam.MODEL_NAME, modelName);
            // Dify 只有模型名，补全平台 deployment id/type（IR 生成必需），查不到留空用户手选
            fillModelDeploymentInfo(modelInfo, modelName);
            configs.put(CommonConstant.ModelParam.MODEL, modelInfo);
            Map<String, Object> modelParams = MapReadUtil.safeCastToMapWithStringKey(modelConfig.get("completion_params"));
            configs.put(CommonConstant.ModelParam.MAX_TOKENS, modelParams.get(CommonConstant.ModelParam.MAX_TOKENS) == null ? 2048 : modelParams.get(CommonConstant.ModelParam.MAX_TOKENS));
            configs.put(CommonConstant.ModelParam.FREQUENCY_PENALTY, modelParams.get(CommonConstant.ModelParam.FREQUENCY_PENALTY) == null ? 0 : modelParams.get(CommonConstant.ModelParam.FREQUENCY_PENALTY));
            configs.put(CommonConstant.DIFY.TEMPERATURE, modelParams.get(CommonConstant.DIFY.TEMPERATURE) == null ? 0.5 : modelParams.get(CommonConstant.DIFY.TEMPERATURE));
            configs.put(CommonConstant.DIFY.TOP_P, modelParams.get(CommonConstant.DIFY.TOP_P) == null ? 0.5 : modelParams.get(CommonConstant.DIFY.TOP_P));
            // dify默认开启深度思考
            configs.put(CommonConstant.DIFY.THINKING, true);
            configs.put(CommonConstant.DIFY.ENABLE_HISTORY, false);
        }

        // 适配上下文转输入参数
        Map<String, Object> context = MapReadUtil.safeCastToMapWithStringKey(data.get("context"));
        if (context != null && (Boolean) context.get("enabled")) {
            List<String> variableSelector = (List<String>) context.get("variable_selector");
            if (workflowNodeMap.get(variableSelector.get(0)) != null) {
                WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO();
                workflowFieldVO.setRequired(true);
                workflowFieldVO.setName("context");
                workflowFieldVO.setSource(WorkflowFieldVO.SourceEnum.USER);
                workflowFieldVO.setValue(adaptWorkflowFieldVoValue(variableSelector, workflowNodeMap, workflowNodeMap.get(variableSelector.get(0))));
                setTypeAndSchemaByName(workflowFieldVO, workflowNodeMap.get(variableSelector.get(0)), variableSelector);
                needConvertFields.add(workflowFieldVO);
            }
        }

        // 适配系统与用户提示词
        List<Map<String, Object>> promptTemplate = MapReadUtil.getMapDeepValue(data, List.class, "prompt_template");
        if (promptTemplate != null) {
            // 拼接用户提示词
            Map<String, Set<List<String>>> idNameMap = new HashMap<>();
            AtomicReference<String> templateContent = new AtomicReference<>("");
            promptTemplate.forEach(prompt -> {
                switch (prompt.get("role").toString()) {
                    case "system" -> {
                        String systemPrompt = prompt.get("text").toString();
                        configs.put(CommonConstant.DIFY.SYSTEM_PROMPT, extractAndReplace(systemPrompt, idNameMap));
                    }
                    case "user" -> {
                        String userPrompt = prompt.get("text").toString();
                        templateContent.set(templateContent.get() + " user: " + extractAndReplace(userPrompt, idNameMap));
                    }
                    case "assistant" -> {
                        String assistantPrompt = prompt.get("text").toString();
                        templateContent.set(templateContent.get() + " assistant: " + extractAndReplace(assistantPrompt, idNameMap));
                    }
                    default -> {}
                }
            });
            configs.put(CommonConstant.DIFY.TEMPLATE_CONTENT, templateContent.get());
            // 转换输入参数
            needConvertFields.addAll(convertToFieldVOs(idNameMap, workflowNodeMap));
        }

        // 适配视觉参数
        Map<String, Object> visualParams = MapReadUtil.safeCastToMapWithStringKey(data.get("vision"));
        if (visualParams != null && (Boolean) visualParams.get("enabled")) {
            List<String> visualParamsConfigs = (List<String>) MapReadUtil.safeCastToMapWithStringKey(visualParams.get("configs")).get("variable_selector");
            configs.put("vision", visualParamsConfigs.get(1));
        }

        // 默认流式输出，如果输出是JSON为非流式输出.
        boolean isStructuredOutputEnabled = data.containsKey("structured_output_enabled") && (Boolean) data.get("structured_output_enabled");
        if (isStructuredOutputEnabled) {
            configs.put("stream", false);
            configs.put("response_format", "json");
        } else {
            configs.put("stream", true);
            configs.put("response_format", "text");
        }

        // 适配异常处理
        Map<String, Object> errorConfig = new HashMap<>();
        errorConfig.put("timeout", 900);
        errorConfig.put("retry_times", 0);
        if (data.containsKey(CommonConstant.DIFY.ERROR_STRATEGY) && isStructuredOutputEnabled) {
            switch (data.get(CommonConstant.DIFY.ERROR_STRATEGY).toString()) {
                case CommonConstant.DIFY.FAIL_BRANCH -> errorConfig.put(CommonConstant.DIFY.HANDLE_TYPE, CommonConstant.DIFY.ERROR_BRANCH);
                case CommonConstant.DIFY.DEFAULT_VALUE -> {
                    Map<String, String> defaultOutputs = new HashMap<>();
                    List<Map<String, Object>> defaultValue = MapReadUtil.safeCastToListWithMap(MapReadUtil.getMapDeepValue(data, List.class, "default_value"));
                    defaultValue.forEach(item -> {
                        defaultOutputs.put(item.get("key").toString(), item.get("value").toString());
                    });
                    errorConfig.put(CommonConstant.DIFY.HANDLE_TYPE, "defaultOutputs");
                    errorConfig.put("default_outputs", defaultOutputs);
                }
            }
        } else {
            // dify默认中断流程
            errorConfig.put(CommonConstant.DIFY.HANDLE_TYPE, CommonConstant.DIFY.INTERRUPT);
        }
        configs.put(CommonConstant.DIFY.EXCEPTION_PROCESS, errorConfig);
        return configs;
    }
}
