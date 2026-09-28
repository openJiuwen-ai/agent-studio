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
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Component
public class ParameterExtractorNodeConverter extends AbstractSDSLNodeConverter {

    private static final Pattern TYPE_PATTERN = Pattern.compile("^array\\[(.*)\\]");

    @Override
    public Boolean supportNodeType(NodeType nodeType) {
        return NodeType.PARAMETER_EXTRACTOR.equals(nodeType);
    }

    @Override
    public WorkflowNodeVO adapt(Map<String, Object> data, WorkflowNodeVO workflowNodeVO, Map<String, WorkflowNodeVO> workflowNodeMap) {
        workflowNodeVO.setType(NodeType.PARAMETER_EXTRACTOR.getType());
        List<WorkflowFieldVO> needConvertFields = new ArrayList<>();
        workflowNodeVO.setConfigs(adaptConfigs(data, needConvertFields, workflowNodeMap, workflowNodeVO));
        workflowNodeVO.setInputs(needConvertFields);
        workflowNodeVO.setOutputs(adaptOutputs(data));
        return workflowNodeVO;
    }


    @SuppressWarnings("unchecked")
    public Map<String, Object> adaptConfigs(Map<String, Object> data, List<WorkflowFieldVO> needConvertFields, Map<String, WorkflowNodeVO> workflowNodeMap, WorkflowNodeVO workflowNodeVO) {
        Map<String, Object> configs = new HashMap<>();
        configs.put(CommonConstant.DIFY.CONFIG_DEFAULT_NAME, false);
        configs.put("stream", false);
        configs.put("response_format", "json");
        configs.put("safety_barrier", false);
        configs.put(CommonConstant.DIFY.TEMPLATE_CONTENT, " ");

        // 适配模型参数
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

        // 适配视觉参数
        Map<String, Object> visualParams = MapReadUtil.safeCastToMapWithStringKey(data.get("vision"));
        if (visualParams != null && (Boolean) visualParams.get("enabled")) {
            List<String> visualParamsConfigs = (List<String>) MapReadUtil.safeCastToMapWithStringKey(visualParams.get("configs")).get("variable_selector");
            configs.put("vision", visualParamsConfigs.get(1));
        }

        // 适配异常处理
        Map<String, Object> errorConfig = new HashMap<>();
        errorConfig.put("timeout", 900);
        errorConfig.put("retry_times", 0);
        if (data.containsKey(CommonConstant.DIFY.ERROR_STRATEGY)) {
            switch (data.get(CommonConstant.DIFY.ERROR_STRATEGY).toString()) {
                case CommonConstant.DIFY.FAIL_BRANCH -> errorConfig.put("handle_type", "errorbranch");
                case CommonConstant.DIFY.DEFAULT_VALUE -> {
                    Map<String, String> defaultOutputs = new HashMap<>();
                    List<Map<String, Object>> defaultValue = MapReadUtil.safeCastToListWithMap(MapReadUtil.getMapDeepValue(data, List.class, "default_value"));
                    defaultValue.forEach(item -> {
                        defaultOutputs.put(item.get("key").toString(), item.get("value").toString());
                    });
                    errorConfig.put("handle_type", "defaultOutputs");
                    errorConfig.put("default_outputs", defaultOutputs);
                }
            }
        } else {
            // dify默认中断流程
            errorConfig.put("handle_type", "interrupt");
        }
        configs.put("exception_process", errorConfig);

        // 适配输入参数
        List<String> query = MapReadUtil.safeCastToList(data.get("query"), String.class);
        if (query != null && !query.isEmpty()) {
            if (workflowNodeMap.get(query.get(0)) != null) {
                WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO()
                        .setRequired(true)
                        .setReflection(false)
                        .setDescription("")
                        .setName("query")
                        .setSource(WorkflowFieldVO.SourceEnum.USER)
                        .setValue(adaptWorkflowFieldVoValue(query, workflowNodeMap, workflowNodeVO));
                setTypeAndSchemaByName(workflowFieldVO, workflowNodeMap.get(query.get(0)), query);
                needConvertFields.add(workflowFieldVO);
            }
        }

        // 适配系统与用户提示词
        String instruction = Optional.ofNullable((String) data.get("instruction")).orElse(null);
        if (instruction != null && !instruction.isEmpty()) {
            // 拼接用户提示词
            Map<String, Set<List<String>>> idNameMap = new HashMap<>();
            configs.put(CommonConstant.DIFY.SYSTEM_PROMPT, extractAndReplace(instruction, idNameMap));
            configs.put(CommonConstant.DIFY.TEMPLATE_CONTENT, " ");
            // 转换输入参数
            needConvertFields.addAll(convertToFieldVOs(idNameMap, workflowNodeMap));
        }

        // 返回
        return configs;
    }

    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        // 提取参数 -> 输出参数
        List<WorkflowFieldVO> outputs = Optional.ofNullable(MapReadUtil.safeCastToListWithMap(data.get("parameters"))).orElseGet(Collections::emptyList)
                .stream().map(variable -> {
                    WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO()
                            .setName(String.valueOf(variable.get("name")))
                            .setDescription(String.valueOf(variable.get("description")))
                            .setRequired(Boolean.parseBoolean(variable.get("required").toString()))
                            .setValue(new WorkflowFieldVOValue().setType(WorkflowFieldVOValue.TypeEnum.LITERAL).setContent(null));
                    setTypeAndSchemaByType(workflowFieldVO, String.valueOf(variable.get("type")));
                    return workflowFieldVO;
                })
                .collect(Collectors.toList());

        // 适配dify默认输出参数
        outputs.add(new WorkflowFieldVO()
                .setName("__is_success")
                .setDescription("是否成功。成功时值为 1，失败时值为 0。")
                .setType(VariableEnum.NUMBER.getDslType())
                .setRequired(true)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                        .setContent(null)));

        outputs.add(new WorkflowFieldVO()
                .setName("__reason")
                .setDescription("错误原因")
                .setType(VariableEnum.STRING.getDslType())
                .setRequired(true)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                        .setContent(null)));

        outputs.add(new WorkflowFieldVO()
                .setName("__usage")
                .setDescription("模型用量信息")
                .setType(VariableEnum.JSON_OBJECT.getDslType())
                .setRequired(true)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                        .setContent(null)));

        return outputs;
    }


    /**
     * 解析dify的type字段
     * type ->  type + schema
     *
     * @param workflowFieldVO 要设置的变量
     * @param type dify的type
     */
    private void setTypeAndSchemaByType(WorkflowFieldVO workflowFieldVO, String type) {
        Matcher matcher = TYPE_PATTERN.matcher(type);
        if (matcher.matches()) {
            workflowFieldVO.setType(VariableEnum.ARRAY.getDslType());
            workflowFieldVO.setSchema(new WorkflowFieldVO().setType(matcher.group(1)).setName(""));
        } else {
            workflowFieldVO.setType(type);
        }
    }

}
