/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class AgentNodeConverter extends AbstractSDSLNodeConverter {
    @Override
    public Boolean supportNodeType(NodeType nodeType) {
        return NodeType.AGENT.equals(nodeType);
    }

    /**
     * 转换 agent （目前仅支持迁移 agent 名字）
     */
    @Override
    public WorkflowNodeVO adapt(Map<String, Object> data, WorkflowNodeVO workflowNodeVO,
        Map<String, WorkflowNodeVO> workflowNodeMap) {
        workflowNodeVO.setType(NodeType.AGENT.getType());
        workflowNodeVO.setInputs(adaptInputs(data, workflowNodeMap));
        workflowNodeVO.setOutputs(adaptOutputs(data));
        workflowNodeVO.setConfigs(adaptConfigs(data));
        return workflowNodeVO;
    }

    /**
     * 转换 inputs （目前不支持 inputs 转换，返回默认配置）
     */
    @Override
    public List<WorkflowFieldVO> adaptInputs(Map<String, Object> data, Map<String, WorkflowNodeVO> workflowNodeMap) {
        return super.adaptInputs(data, workflowNodeMap);
    }

    /**
     * 转换 outputs （目前不支持 outputs 转换，返回默认配置）
     */
    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        List<WorkflowFieldVO> outputs = new ArrayList<>();
        WorkflowFieldVO output = new WorkflowFieldVO().setName("output")
            .setType("string")
            .setDescription("")
            .setRequired(false)
            .setSource(WorkflowFieldVO.SourceEnum.USER)
            .setReflection(false)
            .setValue(new WorkflowFieldVOValue().setType(WorkflowFieldVOValue.TypeEnum.GENERATED));
        outputs.add(output);
        return outputs;
    }

    /**
     * 转换 configs （目前不支持 configs 转换，返回默认配置）
     */
    @Override
    public Map<String, Object> adaptConfigs(Map<String, Object> data) {
        Map<String, Object> configs = super.adaptConfigs(data);
        configs.put(CommonConstant.DIFY.TOP_P, 0.1);
        configs.put(CommonConstant.DIFY.MAX_ITERATION, 1);
        configs.put(CommonConstant.ModelParam.MAX_TOKENS, 1);
        configs.put(CommonConstant.DIFY.TEMPERATURE, 0);
        configs.put(CommonConstant.DIFY.SYSTEM_PROMPT, "");
        configs.put(CommonConstant.Workflow.PLUGINS, new ArrayList<>());
        return configs;
    }
}
