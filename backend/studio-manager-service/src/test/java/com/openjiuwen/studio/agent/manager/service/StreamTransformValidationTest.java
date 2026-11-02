/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVOErrors;

/**
 * 流式消息节点校验（BUG2026102704593）相关纯函数单元测试。
 *
 * <p>覆盖 validateStreamTransformNodeConfig 中新增的"引用变量存在性校验"：
 * 占位符必须引用本节点输入参数；字段引用还要求子路径存在于输入参数（上游
 * 输出字段）schema 中。无法确认的场景（schema 缺失、上游解析失败）放行不误报。
 */
class StreamTransformValidationTest {

    private static final String REF_ERROR = "openjiuwen.02201100";

    private final WorkflowValidationService service = new WorkflowValidationService();

    private Map<String, WorkflowValidationService.Node> nodeMap;

    @BeforeEach
    void setUp() {
        I18nUtil i18nUtil = mock(I18nUtil.class);
        when(i18nUtil.getMessage(anyString())).thenAnswer(invocation -> invocation.getArgument(0));
        ReflectionTestUtils.setField(service, "i18nUtil", i18nUtil);
        nodeMap = new HashMap<>();
    }

    // ===== 辅助构造 =====

    private WorkflowValidationService.Node streamTransformNode(String frameTemplate, List<String> concat) {
        WorkflowNodeVO nodeVO = new WorkflowNodeVO();
        nodeVO.setId("st_node");
        nodeVO.setType("StreamTransform");

        Map<String, Object> configs = new HashMap<>();
        Map<String, Object> transformer = new HashMap<>();
        transformer.put("frame_template", frameTemplate);
        configs.put("transformer", transformer);
        configs.put("concat", concat == null ? new ArrayList<String>() : concat);
        nodeVO.setConfigs(configs);

        WorkflowFieldVO input = new WorkflowFieldVO();
        input.setName("raw_output").setType("object").setSource(WorkflowFieldVO.SourceEnum.USER);
        WorkflowFieldVOValue value = new WorkflowFieldVOValue();
        value.setType(WorkflowFieldVOValue.TypeEnum.REF);
        Map<String, String> refContent = new HashMap<>();
        refContent.put("ref_node_id", "upstream_node");
        refContent.put("ref_var_name", "userFields.stream_output");
        value.setContent(refContent);
        input.setValue(value);
        nodeVO.setInputs(List.of(input));
        return new WorkflowValidationService.Node(nodeVO);
    }

    private void addUpstreamNodeWithSchema(List<Map<String, Object>> subFields) {
        WorkflowNodeVO upstreamVO = new WorkflowNodeVO();
        upstreamVO.setId("upstream_node");
        upstreamVO.setType("Plugin");

        WorkflowFieldVO output = new WorkflowFieldVO();
        output.setName("stream_output").setType("object").setSchema(subFields);
        upstreamVO.setOutputs(List.of(output));
        nodeMap.put("upstream_node", new WorkflowValidationService.Node(upstreamVO));
    }

    private List<Map<String, Object>> schemaOf(Object... nameTypePairs) {
        List<Map<String, Object>> schema = new ArrayList<>();
        for (int i = 0; i + 1 < nameTypePairs.length; i += 2) {
            Map<String, Object> field = new HashMap<>();
            field.put("name", nameTypePairs[i]);
            field.put("type", nameTypePairs[i + 1]);
            schema.add(field);
        }
        return schema;
    }

    private List<WorkflowValidationVOErrors> validate(WorkflowValidationService.Node node) {
        List<WorkflowValidationVOErrors> errors = new ArrayList<>();
        ReflectionTestUtils.invokeMethod(service, "validateStreamTransformNodeConfig", nodeMap, node, errors);
        return errors;
    }

    private boolean hasRefError(List<WorkflowValidationVOErrors> errors) {
        return errors.stream().anyMatch(e -> REF_ERROR.equals(e.getReason()));
    }

    // ===== 引用变量存在性校验 =====

    @Test
    void placeholders_withNonInputPrefix_shouldReportRefError() {
        addUpstreamNodeWithSchema(schemaOf("data", "string"));
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{other.data}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertTrue(hasRefError(errors), "引用非输入参数应报 02201098");
    }

    @Test
    void placeholders_withMissingSubField_shouldReportRefError() {
        addUpstreamNodeWithSchema(schemaOf("data", "string"));
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output.nonexist}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertTrue(hasRefError(errors), "引用输入参数中不存在的字段应报 02201098");
    }

    @Test
    void placeholders_withExistingSubField_shouldPass() {
        addUpstreamNodeWithSchema(schemaOf("data", "string"));
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output.data}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertFalse(hasRefError(errors), "引用 schema 中存在的字段不应报错");
        assertTrue(errors.isEmpty(), "除引用校验外不应有其他错误");
    }

    @Test
    void placeholders_withArrayMissingElementSchema_shouldPass() {
        // 数组字段未声明元素 schema：无法确认引用路径，放行（与改动前行为一致，避免误拦）
        addUpstreamNodeWithSchema(schemaOf("items", "array"));
        WorkflowValidationService.Node node =
            streamTransformNode("{\"content\":\"{{raw_output.items[0].name}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertFalse(hasRefError(errors), "数组元素 schema 缺失无法确认时应放行");
    }

    @Test
    void placeholders_withWholeInputReference_shouldPass() {
        addUpstreamNodeWithSchema(schemaOf("data", "string"));
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertFalse(hasRefError(errors), "整体引用输入参数不应报错");
    }

    @Test
    void placeholders_withNestedSchemaPath_shouldPass() {
        List<Map<String, Object>> nested = new ArrayList<>();
        nested.add(Map.of("name", "text", "type", "string"));
        List<Map<String, Object>> schema = new ArrayList<>();
        Map<String, Object> dataField = new HashMap<>();
        dataField.put("name", "data");
        dataField.put("type", "object");
        dataField.put("schema", nested);
        schema.add(dataField);
        addUpstreamNodeWithSchema(schema);
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output.data.text}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertFalse(hasRefError(errors), "嵌套路径存在时不应报错");
    }

    @Test
    void placeholders_withMissingUpstreamSchema_shouldPass() {
        addUpstreamNodeWithSchema(null);
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output.data}}\"}", null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        assertFalse(hasRefError(errors), "schema 缺失无法确认时不应误报");
    }

    @Test
    void placeholders_withUnresolvableUpstream_shouldOnlyCheckPrefix() {
        // 上游节点不在 nodeMap 中：仅前缀错误会报，字段级引用放行
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output.data}}\"}", null);
        List<WorkflowValidationVOErrors> errors = validate(node);
        assertFalse(hasRefError(errors), "上游解析失败时应放行字段级引用");

        WorkflowValidationService.Node badNode = streamTransformNode("{\"content\":\"{{other.data}}\"}", null);
        List<WorkflowValidationVOErrors> badErrors = validate(badNode);
        assertTrue(hasRefError(badErrors), "前缀错误仍应报 02201098");
    }

    // ===== 既有格式校验回归 =====

    @Test
    void emptyFrameTemplate_shouldReportExistingError() {
        addUpstreamNodeWithSchema(schemaOf("data", "string"));
        WorkflowValidationService.Node node = streamTransformNode(null, null);

        List<WorkflowValidationVOErrors> errors = validate(node);

        boolean hasMissingContentError =
            errors.stream().anyMatch(e -> "openjiuwen.02201094".equals(e.getReason()));
        assertTrue(hasMissingContentError, "frame_template 缺失应报 02201094");
        assertEquals(1, errors.size());
    }

    @Test
    void concatFieldNotInTemplate_shouldReportExistingError() {
        addUpstreamNodeWithSchema(schemaOf("data", "string"));
        WorkflowValidationService.Node node = streamTransformNode("{\"content\":\"{{raw_output.data}}\"}",
            List.of("raw_output.other"));

        List<WorkflowValidationVOErrors> errors = validate(node);

        boolean hasConcatError = errors.stream().anyMatch(e -> "openjiuwen.02201096".equals(e.getReason()));
        assertTrue(hasConcatError, "concat 字段不在内容中应报 02201096");
    }
}