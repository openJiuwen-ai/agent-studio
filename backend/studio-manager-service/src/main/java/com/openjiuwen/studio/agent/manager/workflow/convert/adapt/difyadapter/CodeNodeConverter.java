/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;

import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 代码节点转换
 *
 */
@Component
public class CodeNodeConverter extends AbstractSDSLNodeConverter {
    @Override
    public Boolean supportNodeType(NodeType nodeType) {
        return NodeType.CODE.equals(nodeType);
    }

    @Override
    public WorkflowNodeVO adapt(Map<String, Object> data, WorkflowNodeVO workflowNodeVO,
        Map<String, WorkflowNodeVO> workflowNodeMap) {
        workflowNodeVO.setType(NodeType.CODE.getType());
        workflowNodeVO.setInputs(adaptInputs(data, workflowNodeVO, workflowNodeMap));
        workflowNodeVO.setOutputs(adaptOutputs(data));
        workflowNodeVO.setConfigs(adaptConfigs(data));
        return workflowNodeVO;
    }

    @SuppressWarnings("unchecked")
    public List<WorkflowFieldVO> adaptInputs(Map<String, Object> data, WorkflowNodeVO workflowNodeVO, Map<String, WorkflowNodeVO> workflowNodeMap) {
        List<Map<String, Object>> variables = (List<Map<String, Object>>) data.get("variables");
        List<WorkflowFieldVO> inputs = new ArrayList<>();
        if (variables != null) {
            inputs = variables.stream().map(variable -> {
                List<String> selector = (List<String>) variable.get("value_selector");
                WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO();
                workflowFieldVO.setSource(WorkflowFieldVO.SourceEnum.USER);
                workflowFieldVO.setName((String) variable.get("variable"));
                String valueType = (String) variable.get("value_type");
                if (StringUtils.isEmpty(valueType)) {
                    // 部分版本 Dify yml 的 code variables 不带 value_type，此时从上游输出回填 type/schema。
                    // 否则 DSL type 为空会在 IR 生成时被 formatWorkflowType 兜底为 string，
                    // 运行时 _coerce_inputs 据此把 object 输入 str() 化，代码节点 .get() 报
                    // 'str' object has no attribute 'get'。找不到上游时 helper 自身兜底 string，与原行为一致
                    WorkflowNodeVO refNode = (selector != null && !selector.isEmpty())
                        ? workflowNodeMap.get(selector.get(0)) : null;
                    setTypeAndSchemaByName(workflowFieldVO, refNode, selector);
                } else {
                    workflowFieldVO.setType(valueType);
                }
                workflowFieldVO.setValue(adaptWorkflowFieldVoValue(selector, workflowNodeMap, workflowNodeVO));
                return workflowFieldVO;
            }).toList();
        }
        return inputs;
    }

    @SuppressWarnings("unchecked")
    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        List<WorkflowFieldVO> outputs = new ArrayList<>();
        if (ObjectUtils.isNotEmpty(data.get("outputs"))) {
            Map<String, Map<String, Object>> outputsVariables = (Map<String, Map<String, Object>>) data.get("outputs");

            outputsVariables.forEach((outputName, outputsVariable) -> {
                WorkflowFieldVO outputFieldVO = new WorkflowFieldVO();
                outputFieldVO.setSource(WorkflowFieldVO.SourceEnum.USER);
                outputFieldVO.setName(outputName);
                outputFieldVO.setDescription(outputName);
                outputFieldVO.setRequired(true);
                outputFieldVO.setType(parseSourceType((String) outputsVariable.get("type")));
                outputFieldVO.setSchema(parseSchema((String) outputsVariable.get("type")));
                outputFieldVO.setValue(new WorkflowFieldVOValue().setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                    .setHint("")
                    .setDefault(""));
                outputs.add(outputFieldVO);
            });
        }
        return outputs;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> adaptConfigs(Map<String, Object> data) {
        Map<String, Object> configs = new HashMap<>();
        configs.put(CommonConstant.DIFY.CODE, data.get("code"));
        configs.put(CommonConstant.DIFY.EXEC_ENV, "fg");
        if ("fail-branch".equals(data.get("error_strategy"))) {
            Map<String, Object> failBranchMap = new HashMap<>();
            failBranchMap.put("handle_type", "errorbranch");
            failBranchMap.put("retry_times", 0);
            failBranchMap.put("timeout", 900);
            configs.put("exception_process", failBranchMap);
        }
        if ("default-value".equals(data.get("error_strategy"))) {
            Map<String, Object> failBranchMap = new HashMap<>();
            Map<String, Object> res = new HashMap<>();
            List<Map<String, Object>> defaultValue = (List<Map<String, Object>>) data.get("default_value");
            res.put("result", ObjectUtils.isNotEmpty(defaultValue) ? defaultValue.get(0).get("value"): "");
            failBranchMap.put("default_outputs", res);
            failBranchMap.put("handle_type", "defaultOutputs");
            failBranchMap.put("retry_times", 0);
            failBranchMap.put("timeout", 900);
            configs.put("exception_process", failBranchMap);
        }
        return configs;
    }
}
