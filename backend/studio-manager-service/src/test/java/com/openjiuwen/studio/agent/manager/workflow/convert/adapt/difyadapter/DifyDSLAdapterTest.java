/*
 *  Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.manager.service.WorkflowValidationService;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * DifyDSLAdapter 转换测试。
 *
 * <p>核心用例是 fastjson2 2.0.58~2.0.65 的 {@code JSON.toJSON} 树转换缺陷的防回退哨兵：
 * {@link DifyDSLAdapter#convert} 中 workflowDetails 的生成必须走
 * {@code JSONObject.parseObject(JSON.toJSONString(vo))} 而不是 {@code JSONObject.from(vo)}——
 * 后者在序列化含 Object 类型字段(schema/content)的 bean 图时会因访问器错配导致 JVM 级崩溃
 * (hs_err_pid*.log, EXCEPTION_ACCESS_VIOLATION)，Start 节点先于其他节点序列化时 100% 触发。
 * 若有人将实现改回 {@code JSONObject.from}，本用例会在测试期崩溃 surefire JVM 使构建失败。</p>
 */
class DifyDSLAdapterTest {

    private DifyDSLAdapter adapter;

    @BeforeEach
    void setUp() {
        List<NodeConverter> converters = Arrays.asList(
            new AgentNodeConverter(), new AggregationNodeConverter(), new AnswerNodeConverter(),
            new CodeNodeConverter(), new DocumentExtractorConverter(), new EmptyNodeConverter(),
            new EndNodeConverter(), new HttpNodeConverter(new CheckUrlService()),
            new IfElseNodeConverter(), new IterationNodeConverter(), new IterationStartNodeConverter(),
            new KnowledgeRepoNodeConverter(), new LLMNodeConverter(), new ListOperatorNodeConverter(),
            new LoopEndConverter(), new LoopNodeConverter(), new LoopStartNodeConverter(),
            new ParameterExtractorNodeConverter(), new QuestionClassifierNodeConverter(),
            new SetVariableNodeConverter(), new StartNodeConverter(), new TemplateTransformNodeConverter(),
            new ToolNodeConverter());
        adapter = new DifyDSLAdapter(converters);
        ReflectionTestUtils.setField(adapter, "blockNodes", "");

        WorkflowValidationService validationService = mock(WorkflowValidationService.class);
        when(validationService.sanitizeName(anyString())).thenAnswer(invocation -> invocation.getArgument(0));
        ReflectionTestUtils.setField(adapter, "workflowValidationService", validationService);

        converters.stream().filter(c -> c instanceof LoopNodeConverter).findFirst()
            .ifPresent(loop -> converters.stream().filter(c -> c instanceof IterationNodeConverter).findFirst()
                .ifPresent(iteration -> ReflectionTestUtils.setField(iteration, "loopNodeConverter", loop)));
        converters.stream().filter(c -> c instanceof HttpNodeConverter)
            .forEach(http -> ReflectionTestUtils.setField(http, "blockNodes", ""));
    }

    /**
     * 含 Start 节点(schema 为 Object 类型字段)的 DSL 转换后，workflowDetails 中各 Object 字段的
     * JSON 形态必须保真：sys.schema 保持数组、嵌套 conversation_history.schema 保持对象、
     * value.content 保持对象——这是升级前(2.0.51 JSONObject.from)的既有输出契约。
     */
    @Test
    void convertWithStartNodePreservesObjectFieldJsonShape() {
        Map<String, Object> dsl = buildMiniDsl();
        adapter.validateFormat(dsl);

        WorkflowInfo info = adapter.convert(dsl);

        assertNotNull(info);
        assertEquals("ut-dify-import", info.getName());
        assertEquals("chat", info.getType());

        Map<String, Object> detailsMap = info.getWorkflowDetails();
        assertNotNull(detailsMap);
        JSONObject details = new JSONObject(detailsMap);
        assertEquals(3, details.getJSONArray("nodes").size());
        assertEquals(2, details.getJSONArray("edges").size());

        JSONObject startNode = findNodeByType(details.getJSONArray("nodes"), "Start");
        assertNotNull(startNode);

        JSONArray outputs = startNode.getJSONArray("outputs");
        JSONObject sysOutput = findFieldByName(outputs, "sys");
        assertNotNull(sysOutput);
        Object sysSchema = sysOutput.get("schema");
        assertTrue(sysSchema instanceof JSONArray, "sys.schema 应保持数组类型");
        JSONObject conversationHistory = ((JSONArray) sysSchema).getJSONObject(0);
        assertEquals("conversation_history", conversationHistory.getString("name"));
        assertTrue(conversationHistory.get("schema") instanceof JSONObject,
            "conversation_history.schema 应保持对象类型");
        assertTrue(sysOutput.getJSONObject("value").get("content") instanceof JSONObject,
            "sys.value.content 应保持对象类型");

        JSONObject userMeta = findFieldByName(outputs, "user_meta");
        assertNotNull(userMeta);
        assertEquals("string", userMeta.getString("type"));
        assertEquals("user", userMeta.getString("source"));
    }

    @Test
    void validateFormatRejectsMissingAppOrWorkflow() {
        assertThrows(AgentStudioException.class, () -> adapter.validateFormat(Map.of("app", Map.of())));
        assertThrows(AgentStudioException.class, () -> adapter.validateFormat(Map.of("workflow", Map.of())));
    }

    private JSONObject findNodeByType(JSONArray nodes, String type) {
        for (int i = 0; i < nodes.size(); i++) {
            JSONObject node = nodes.getJSONObject(i);
            if (type.equals(node.getString("type"))) {
                return node;
            }
        }
        return null;
    }

    private JSONObject findFieldByName(JSONArray outputs, String name) {
        for (int i = 0; i < outputs.size(); i++) {
            JSONObject field = outputs.getJSONObject(i);
            if (name.equals(field.getString("name"))) {
                return field;
            }
        }
        return null;
    }

    /**
     * 最小 Dify DSL：Start 节点(带变量, 由 adaptPresetVariable 生成含嵌套 schema 的 sys 系统变量)
     * + Answer 节点 + 连线。Start 在前、其他节点在后，正是触发 fastjson2 toJSON 缓存污染的顺序。
     */
    private Map<String, Object> buildMiniDsl() {
        Map<String, Object> startData = new HashMap<>();
        startData.put("type", "start");
        startData.put("title", "开始");
        startData.put("desc", "");
        Map<String, Object> variable = new HashMap<>();
        variable.put("variable", "user_meta");
        variable.put("label", "用户元数据");
        variable.put("type", "paragraph");
        variable.put("required", false);
        variable.put("max_length", 50000);
        startData.put("variables", new ArrayList<>(List.of(variable)));
        Map<String, Object> startNode = nodeOf("start", startData, 50, 100);

        Map<String, Object> answerData = new HashMap<>();
        answerData.put("type", "answer");
        answerData.put("title", "回复");
        answerData.put("desc", "");
        answerData.put("answer", "你好");
        Map<String, Object> answerNode = nodeOf("answer", answerData, 350, 100);

        Map<String, Object> edge = new HashMap<>();
        edge.put("id", "e_start_answer");
        edge.put("source", "start");
        edge.put("sourceHandle", "source");
        edge.put("target", "answer");
        edge.put("targetHandle", "target");
        edge.put("type", "custom");
        edge.put("data", Map.of("sourceType", "start", "targetType", "answer",
            "isInIteration", false, "isInLoop", false));

        Map<String, Object> graph = new HashMap<>();
        graph.put("nodes", List.of(startNode, answerNode));
        graph.put("edges", List.of(edge));
        graph.put("viewport", Map.of("x", 0, "y", 0, "zoom", 1));

        Map<String, Object> workflow = new HashMap<>();
        workflow.put("graph", graph);
        workflow.put("environment_variables", new ArrayList<>());
        workflow.put("conversation_variables", new ArrayList<>());

        Map<String, Object> dsl = new HashMap<>();
        dsl.put("app", Map.of("mode", "advanced-chat", "name", "ut-dify-import", "description", "UT夹具"));
        dsl.put("kind", "app");
        dsl.put("version", "0.1.0");
        dsl.put("workflow", workflow);
        return dsl;
    }

    private Map<String, Object> nodeOf(String id, Map<String, Object> data, int x, int y) {
        Map<String, Object> node = new HashMap<>();
        node.put("id", id);
        node.put("type", "custom");
        node.put("data", data);
        node.put("position", Map.of("x", x, "y", y));
        node.put("positionAbsolute", Map.of("x", x, "y", y));
        return node;
    }
}
