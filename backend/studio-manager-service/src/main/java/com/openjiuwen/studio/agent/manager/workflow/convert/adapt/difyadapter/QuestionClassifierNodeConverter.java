/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.utils.MapReadUtil;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class QuestionClassifierNodeConverter extends AbstractSDSLNodeConverter {

    private static final String CHAT_HISTORY_MAX_TURN = "chat_history_max_turn";

    @Override
    public Boolean supportNodeType(NodeType nodeType) {
        return NodeType.INTENT_DETECTION.equals(nodeType);
    }

    @Override
    public WorkflowNodeVO adapt(Map<String, Object> data, WorkflowNodeVO workflowNodeVO, Map<String, WorkflowNodeVO> workflowNodeMap) {
        workflowNodeVO.setType(NodeType.INTENT_DETECTION.getType());
        workflowNodeVO.setConfigs(adaptConfigs(data));
        workflowNodeVO.setInputs(adaptInputs(data, workflowNodeMap));
        workflowNodeVO.setOutputs(adaptOutputs(data));
        workflowNodeVO.setBranches(adaptBranches(data));
        return workflowNodeVO;
    }


    public Map<String, Object> adaptConfigs(Map<String, Object> data) {
        Map<String, Object> configsMap = new HashMap<>();
        configsMap.put(CommonConstant.DIFY.CONFIG_DEFAULT_NAME, false);
        configsMap.put(CHAT_HISTORY_MAX_TURN, 0);
        String prompt = data.getOrDefault("instruction", "").toString();
        configsMap.put("prompt", extractAndReplace(prompt, null));
        Map<String, Object> modelConfig = MapReadUtil.safeCastToMapWithStringKey(data.get("model"));
        if (modelConfig != null) {
            Map<String, String> modelInfo = new HashMap<>();
            modelInfo.put(CommonConstant.ModelParam.MODEL_NAME, modelConfig.get("name").toString());
            Map<String, Object> llmConfig = new HashMap<>();
            llmConfig.put(CommonConstant.ModelParam.MODEL, modelInfo);
            Map<String, Object> modelParams = MapReadUtil.safeCastToMapWithStringKey(modelConfig.get("completion_params"));
            llmConfig.put(CommonConstant.ModelParam.MAX_TOKENS, modelParams.get(CommonConstant.ModelParam.MAX_TOKENS) == null ? 2048 : modelParams.get(CommonConstant.ModelParam.MAX_TOKENS));
            llmConfig.put(CommonConstant.DIFY.TEMPERATURE, modelParams.get(CommonConstant.DIFY.TEMPERATURE) == null ? 0.5 : modelParams.get(CommonConstant.DIFY.TEMPERATURE));
            llmConfig.put(CommonConstant.DIFY.TOP_P, modelParams.get(CommonConstant.DIFY.TOP_P) == null ? 0.5 : modelParams.get(CommonConstant.DIFY.TOP_P));
            configsMap.put("llm", llmConfig);
        }
        return configsMap;
    }

    @SuppressWarnings("unchecked")
    @Override
    public List<WorkflowFieldVO> adaptInputs(Map<String, Object> data, Map<String, WorkflowNodeVO> workflowNodeMap) {
        List<String> variableSelector = (List<String>) data.get("query_variable_selector");
        if (!CollectionUtils.isEmpty(variableSelector) && workflowNodeMap.get(variableSelector.get(0)) != null) {
            WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO();
            workflowFieldVO.setRequired(false);
            workflowFieldVO.setName("input");
            workflowFieldVO.setSource(WorkflowFieldVO.SourceEnum.SYSTEM);
            workflowFieldVO.setValue(adaptWorkflowFieldVoValue(variableSelector, workflowNodeMap, workflowNodeMap.get(variableSelector.get(0))));
            setTypeAndSchemaByName(workflowFieldVO, workflowNodeMap.get(variableSelector.get(0)), variableSelector);
            return List.of(workflowFieldVO);
        }
        return List.of(new WorkflowFieldVO()
                .setName("input")
                .setType("string")
                .setRequired(false)
                .setSource(WorkflowFieldVO.SourceEnum.SYSTEM)
                .setValue(new WorkflowFieldVOValue().setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                        .setContent("")));
    }

    private List<WorkflowBranchVO> adaptBranches(Map<String, Object> data) {
        List<Map<String, Object>> classesMaps = MapReadUtil.safeCastToListWithMap(MapReadUtil.getMapDeepValue(data, List.class, "classes"));
        if (classesMaps == null) {
            return null;
        }
        List<WorkflowBranchVO> branches = new ArrayList<>();
        for (int i = 0; i < classesMaps.size(); i++) {
            Map<String, Object> classesMap = classesMaps.get(i);
            WorkflowBranchVO workflowBranchVO = new WorkflowBranchVO();
            // Dify 分类 id 可能为 UUID，而运行时按 branch_N 数字后缀约定匹配分类结果，统一按 classes 顺序重排编号
            workflowBranchVO.setId("branch_" + (i + 1));
            Map<String, Object> configs = new HashMap<>();
            configs.put("category", extractAndReplace(classesMap.get("name").toString(), null));
            workflowBranchVO.setConfigs(configs);
            branches.add(workflowBranchVO);
        }
        return branches;
    }

    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        List<WorkflowFieldVO> outputs = new ArrayList<>();
        outputs.add(new WorkflowFieldVO()
                .setName("classification_id")
                .setType("integer")
                .setDescription("intentDetection.outputs_id_description")
                .setRequired(true)
                .setSource(WorkflowFieldVO.SourceEnum.SYSTEM)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                        .setHint("")
                )
        );
        outputs.add(new WorkflowFieldVO()
                .setName("name")
                .setType("string")
                .setDescription("intentDetection.outputs_name_description")
                .setRequired(true)
                .setSource(WorkflowFieldVO.SourceEnum.SYSTEM)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                        .setHint("")
                )
        );
        outputs.add(new WorkflowFieldVO()
                .setName("result")
                .setType("string")
                .setDescription("输出的分类分支名")
                .setRequired(false)
                .setSource(WorkflowFieldVO.SourceEnum.SYSTEM)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                        .setContent("")
                        .setHint("")
                )
        );
        outputs.add(new WorkflowFieldVO()
                .setName("reason")
                .setType("string")
                .setDescription("")
                .setRequired(true)
                .setSource(WorkflowFieldVO.SourceEnum.SYSTEM)
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                        .setHint("")
                )
        );
        return outputs;
    }
}
