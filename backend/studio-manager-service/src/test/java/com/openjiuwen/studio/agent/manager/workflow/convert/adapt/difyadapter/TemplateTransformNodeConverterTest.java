/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Dify template-transform 导入：落成 TemplateTransform（非 Empty），并保留 template。
 */
class TemplateTransformNodeConverterTest {

    private TemplateTransformNodeConverter converter;
    private Map<String, WorkflowNodeVO> workflowNodeMap;

    @BeforeEach
    void setUp() {
        converter = new TemplateTransformNodeConverter();
        workflowNodeMap = new HashMap<>();
    }

    @Test
    void supportNodeType_onlyDifyTemplateTransform() {
        assertTrue(converter.supportNodeType(NodeType.TEMPLATE_TRANSFORM_DIFY));
        assertFalse(converter.supportNodeType(NodeType.TEMPLATE_TRANSFORM));
        assertFalse(converter.supportNodeType(NodeType.CODE));
    }

    @Test
    void adapt_setsTypeToTemplateTransformNotEmpty() {
        Map<String, Object> data = new HashMap<>();
        data.put("template", "Hello {{ name }}");
        WorkflowNodeVO nodeVO = new WorkflowNodeVO();

        WorkflowNodeVO result = converter.adapt(data, nodeVO, workflowNodeMap);

        assertEquals(NodeType.TEMPLATE_TRANSFORM.getType(), result.getType());
        assertFalse("Empty".equals(result.getType()));
        assertEquals("Hello {{ name }}", result.getConfigs().get("template"));
    }

    @Test
    void adaptConfigs_nullTemplateBecomesEmptyString() {
        Map<String, Object> data = new HashMap<>();

        Map<String, Object> configs = converter.adaptConfigs(data);

        assertEquals("", configs.get("template"));
    }

    @Test
    void adaptOutputs_singleUserStringNamedOutput() {
        List<WorkflowFieldVO> outputs = converter.adaptOutputs(new HashMap<>());

        assertEquals(1, outputs.size());
        assertEquals("output", outputs.get(0).getName());
        assertEquals(WorkflowFieldVO.SourceEnum.USER, outputs.get(0).getSource());
        assertEquals("string", outputs.get(0).getType());
    }
}
