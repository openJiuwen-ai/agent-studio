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
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

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

    /**
     * Dify 分类 id 为 UUID 时，意图识别节点分支与出边 branch 必须按 classes 顺序统一重排为
     * branch_N 数字后缀（运行时按 branch_N 约定匹配分类结果，UUID 分支会导致 101021）。
     */
    @Test
    void convertRenumbersClassifierBranchesAndKeepsEdgesInSync() {
        Map<String, Object> dsl = buildClassifierDsl();
        WorkflowInfo info = adapter.convert(dsl);

        JSONObject details = new JSONObject(info.getWorkflowDetails());

        JSONObject classifier = findNodeByType(details.getJSONArray("nodes"), "IntentDetection");
        assertNotNull(classifier);
        JSONArray branches = classifier.getJSONArray("branches");
        assertEquals(2, branches.size());
        assertEquals("branch_1", branches.getJSONObject(0).getString("id"));
        assertEquals("branch_2", branches.getJSONObject(1).getString("id"));
        assertEquals("Class A", branches.getJSONObject(0).getJSONObject("configs").getString("category"));
        assertEquals("Class B", branches.getJSONObject(1).getJSONObject("configs").getString("category"));
        assertEquals("gpt-4", classifier.getJSONObject("configs").getJSONObject("llm")
            .getJSONObject("model").getString("model_name"));

        Set<String> classifierEdgeBranches = new HashSet<>();
        for (int i = 0; i < details.getJSONArray("edges").size(); i++) {
            JSONObject edge = details.getJSONArray("edges").getJSONObject(i);
            if ("node_qc_1".equals(edge.getString("source"))) {
                classifierEdgeBranches.add(edge.getString("branch"));
            }
        }
        assertEquals(new HashSet<>(Arrays.asList("branch_1", "branch_2")), classifierEdgeBranches);
    }

    /**
     * 代码节点输入 type 丢失修复：Dify 代码节点 variables 不携带 value_type，
     * 缺失时按引用目标节点输出推断类型；exec_env 统一为 sandbox（不再硬编码 fg）。
     */
    @Test
    void convertCodeNodeInfersInputTypeAndUsesSandboxEnv() {
        Map<String, Object> dsl = buildClassifierDsl();
        WorkflowInfo info = adapter.convert(dsl);

        JSONObject details = new JSONObject(info.getWorkflowDetails());

        JSONObject codeNode = findNodeByType(details.getJSONArray("nodes"), "Code");
        assertNotNull(codeNode);

        assertEquals("sandbox", codeNode.getJSONObject("configs").getString("exec_env"));
        assertEquals("def main(arg1, arg2):", codeNode.getJSONObject("configs").getString("code"));

        JSONArray inputs = codeNode.getJSONArray("inputs");
        JSONObject arg1 = findFieldByName(inputs, "arg1");
        JSONObject arg2 = findFieldByName(inputs, "arg2");
        assertNotNull(arg1);
        assertNotNull(arg2);
        // arg1 无 value_type，按开始节点 query 输出推断为 string
        assertEquals("string", arg1.getString("type"));
        assertEquals("ref", arg1.getJSONObject("value").getString("type"));
        // arg2 携带 value_type 时保持原值
        assertEquals("number", arg2.getString("type"));

        JSONArray outputs = codeNode.getJSONArray("outputs");
        assertEquals("string", findFieldByName(outputs, "result").getString("type"));

        // 意图识别节点输入引用代码节点输出，类型推断不应缺失
        JSONObject classifier = findNodeByType(details.getJSONArray("nodes"), "IntentDetection");
        assertEquals("string", findFieldByName(classifier.getJSONArray("inputs"), "input").getString("type"));
    }

    private Map<String, Object> buildClassifierDsl() {
        Map<String, Object> startData = new HashMap<>();
        startData.put("type", "start");
        startData.put("title", "开始");
        startData.put("desc", "");
        startData.put("variables", new ArrayList<>());
        Map<String, Object> startNode = nodeOf("start", startData, 50, 100);

        Map<String, Object> codeData = new HashMap<>();
        codeData.put("type", "code");
        codeData.put("title", "代码");
        codeData.put("desc", "");
        codeData.put("code", "def main(arg1, arg2):");
        codeData.put("code_language", "python3");
        Map<String, Object> arg1 = new HashMap<>();
        arg1.put("variable", "arg1");
        arg1.put("value_selector", new ArrayList<>(List.of("start", "query")));
        Map<String, Object> arg2 = new HashMap<>();
        arg2.put("variable", "arg2");
        arg2.put("value_selector", new ArrayList<>(List.of("start", "query")));
        arg2.put("value_type", "number");
        codeData.put("variables", new ArrayList<>(Arrays.asList(arg1, arg2)));
        Map<String, Object> codeOutput = new HashMap<>();
        codeOutput.put("type", "string");
        codeOutput.put("children", null);
        codeData.put("outputs", Map.of("result", codeOutput));
        Map<String, Object> codeNode = nodeOf("code_1", codeData, 300, 100);

        String classIdA = "3f9a2c1e-1111-4b8b-9f2e-aaaaaaaaaaa1";
        String classIdB = "9b8c7d6e-2222-4c8b-8f3e-bbbbbbbbbbb2";
        Map<String, Object> classifierData = new HashMap<>();
        classifierData.put("type", "question-classifier");
        classifierData.put("title", "问题分类器");
        classifierData.put("desc", "");
        classifierData.put("classes", new ArrayList<>(Arrays.asList(
            Map.of("id", classIdA, "name", "Class A"),
            Map.of("id", classIdB, "name", "Class B"))));
        Map<String, Object> classifierModel = new HashMap<>();
        classifierModel.put("name", "gpt-4");
        classifierModel.put("provider", "langgenius/openai/openai");
        classifierModel.put("completion_params", Map.of("temperature", 0.7));
        classifierData.put("model", classifierModel);
        classifierData.put("query_variable_selector", new ArrayList<>(List.of("code_1", "result")));
        classifierData.put("instruction", "classify the question");
        Map<String, Object> classifierNode = nodeOf("qc_1", classifierData, 550, 100);

        Map<String, Object> graph = new HashMap<>();
        graph.put("nodes", List.of(startNode, codeNode, classifierNode, llmNode("llm_1", 800, 50), llmNode("llm_2", 800, 200)));
        graph.put("edges", Arrays.asList(
            edgeOf("start", "source", "code_1", "start", "code"),
            edgeOf("code_1", "source", "qc_1", "code", "question-classifier"),
            edgeOf("qc_1", classIdA, "llm_1", "question-classifier", "llm"),
            edgeOf("qc_1", classIdB, "llm_2", "question-classifier", "llm")));
        graph.put("viewport", Map.of("x", 0, "y", 0, "zoom", 1));

        Map<String, Object> workflow = new HashMap<>();
        workflow.put("graph", graph);
        workflow.put("environment_variables", new ArrayList<>());
        workflow.put("conversation_variables", new ArrayList<>());

        Map<String, Object> dsl = new HashMap<>();
        dsl.put("app", Map.of("mode", "advanced-chat", "name", "ut-dify-classifier", "description", "UT夹具"));
        dsl.put("kind", "app");
        dsl.put("version", "0.1.0");
        dsl.put("workflow", workflow);
        return dsl;
    }

    private Map<String, Object> llmNode(String id, int x, int y) {
        Map<String, Object> data = new HashMap<>();
        data.put("type", "llm");
        data.put("title", id);
        data.put("desc", "");
        Map<String, Object> model = new HashMap<>();
        model.put("name", "gpt-4");
        model.put("provider", "langgenius/openai/openai");
        model.put("completion_params", new HashMap<>());
        data.put("model", model);
        data.put("prompt_template", new ArrayList<>(List.of(Map.of("role", "user", "text", "hello"))));
        return nodeOf(id, data, x, y);
    }

    private Map<String, Object> edgeOf(String source, String sourceHandle, String target, String sourceType, String targetType) {
        Map<String, Object> edge = new HashMap<>();
        edge.put("id", source + "-" + sourceHandle + "-" + target);
        edge.put("source", source);
        edge.put("sourceHandle", sourceHandle);
        edge.put("target", target);
        edge.put("targetHandle", "target");
        edge.put("type", "custom");
        edge.put("data", Map.of("sourceType", sourceType, "targetType", targetType,
            "isInIteration", false, "isInLoop", false));
        return edge;
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
