/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.VariableEnum;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class TemplateTransformNodeConverter extends AbstractSDSLNodeConverter {

    @Override
    public Boolean supportNodeType(NodeType nodeType) {
        return NodeType.TEMPLATE_TRANSFORM_DIFY.equals(nodeType);
    }

    @Override
    public WorkflowNodeVO adapt(Map<String, Object> data, WorkflowNodeVO workflowNodeVO, Map<String, WorkflowNodeVO> workflowNodeMap) {
        workflowNodeVO.setType(NodeType.TEMPLATE_TRANSFORM.getType());
        workflowNodeVO.setInputs(adaptInputs(data, workflowNodeMap));
        workflowNodeVO.setOutputs(adaptOutputs(data));
        workflowNodeVO.setConfigs(adaptConfigs(data));
        return workflowNodeVO;
    }

    @Override
    public Map<String, Object> adaptConfigs(Map<String, Object> data) {
        Map<String, Object> configsMap = super.adaptConfigs(data);
        Object template = data.get("template");
        configsMap.put("template", template == null ? "" : template);
        return configsMap;
    }

    @SuppressWarnings("unchecked")
    @Override
    public List<WorkflowFieldVO> adaptInputs(Map<String, Object> data, Map<String, WorkflowNodeVO> workflowNodeMap) {
        List<Map<String, Object>> variables = (List<Map<String, Object>>) data.get("variables");
        List<WorkflowFieldVO> inputs = new ArrayList<>();
        if (variables != null) {
            for (Map<String, Object> variable : variables) {
                List<String> selector = (List<String>) variable.get("value_selector");
                if (CollectionUtils.isEmpty(selector)) {
                    continue;
                }
                WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO();
                workflowFieldVO.setSource(WorkflowFieldVO.SourceEnum.USER);
                workflowFieldVO.setName((String) variable.get("variable"));
                workflowFieldVO.setType((String) variable.get("value_type"));
                workflowFieldVO.setValue(adaptWorkflowFieldVoValue(selector, workflowNodeMap, workflowNodeMap.get(selector.get(0))));
                inputs.add(workflowFieldVO);
            }
        }
        return inputs;
    }

    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        WorkflowFieldVO workflowFieldVO = new WorkflowFieldVO()
                .setName("output")
                .setSource(WorkflowFieldVO.SourceEnum.USER)
                .setType(VariableEnum.TEXT_INPUT.getDslType())
                .setValue(new WorkflowFieldVOValue()
                        .setType(WorkflowFieldVOValue.TypeEnum.GENERATED)
                        .setContent(""));
        return List.of(workflowFieldVO);
    }
}
