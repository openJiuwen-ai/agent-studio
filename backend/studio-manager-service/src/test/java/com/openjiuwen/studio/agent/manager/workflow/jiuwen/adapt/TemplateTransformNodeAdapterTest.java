/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.jiuwen.adapt;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

/**
 * 模板转换节点 IR 适配：configs.template 原样下发。
 */
class TemplateTransformNodeAdapterTest {

    private final TemplateTransformNodeAdapter adapter = new TemplateTransformNodeAdapter();

    @Test
    void getNodeType_isTemplateTransformIrType() {
        assertEquals(NodeType.TEMPLATE_TRANSFORM.getIrType(), adapter.getNodeType());
    }

    @Test
    void adaptConfig_putsTemplateFromNodeConfigs() {
        WorkflowNodeVO vo = new WorkflowNodeVO();
        Map<String, Object> configs = new HashMap<>();
        configs.put("template", "用户名称：{{ data.get('customerName') }}");
        configs.put("isDefaultName", true);
        vo.setConfigs(configs);

        Map<String, Object> result = adapter.adaptConfig(vo);

        assertEquals("用户名称：{{ data.get('customerName') }}", result.get("template"));
        assertEquals(1, result.size());
    }

    @Test
    void adaptConfig_nullTemplateBecomesEmptyString() {
        WorkflowNodeVO vo = new WorkflowNodeVO();
        vo.setConfigs(new HashMap<>());

        Map<String, Object> result = adapter.adaptConfig(vo);

        assertEquals("", result.get("template"));
    }

    @Test
    void adaptConfig_nullConfigsBecomesEmptyTemplate() {
        WorkflowNodeVO vo = new WorkflowNodeVO();
        vo.setConfigs(null);

        Map<String, Object> result = adapter.adaptConfig(vo);

        assertEquals("", result.get("template"));
    }
}
