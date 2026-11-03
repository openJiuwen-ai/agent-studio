/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;

import java.util.HashMap;
import java.util.Map;

/**
 * 模板转换节点转换 IR。模板正文原样下发，由 runtime 用 Jinja2 沙箱渲染。
 */
public class TemplateTransformNodeAdapter extends AbstractIRNodeAdapter {

    private static final String TEMPLATE = "template";

    @Override
    public Map<String, Object> adaptConfig(WorkflowNodeVO workflowNodeVo) {
        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> nodeConfigs = workflowNodeVo.getConfigs();
        Object template = nodeConfigs == null ? null : nodeConfigs.get(TEMPLATE);
        configs.put(TEMPLATE, template == null ? "" : template);
        return configs;
    }

    @Override
    public String getNodeType() {
        return NodeType.TEMPLATE_TRANSFORM.getIrType();
    }
}
