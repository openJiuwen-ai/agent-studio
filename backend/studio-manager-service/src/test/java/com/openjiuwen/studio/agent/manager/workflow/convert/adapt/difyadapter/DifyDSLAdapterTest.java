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
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.when;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.dto.WorkflowInfo;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.service.WorkflowValidationService;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
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
 *
 * <p>另含 Dify 导入 bug②④⑥ 的行为哨兵（分支编号 / 模型补全 / 输入类型回填），
 * 详细背景见 bugfix 文档《Dify导入代码节点代码丢失.md》。</p>
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
     * bug⑥ 哨兵：Dify yml 的 code variables 不带 value_type 时，CodeNodeConverter 必须从被引用
     * 节点的输出回填 type。否则 DSL type=null 在 IR 生成时被 formatWorkflowType 兜底为 string，
     * runtime _coerce_inputs 据此把 object 输入 str() 化，代码节点 .get() 报
     * 'str' object has no attribute 'get'。value_type 有值原样保留；上游不存在兜底 string。
     */
    @Test
    void convertCodeNodeBackfillsInputTypeFromRefTargetWhenValueTypeAbsent() {
        Map<String, Object> dsl = buildCodeChainDsl();
        adapter.validateFormat(dsl);

        WorkflowInfo info = adapter.convert(dsl);

        JSONObject details = new JSONObject(info.getWorkflowDetails());
        JSONObject nodeB = findNodeById(details.getJSONArray("nodes"), "node_code_b");
        assertNotNull(nodeB, "下游代码节点应完成转换");
        JSONArray inputs = nodeB.getJSONArray("inputs");

        // value_type 缺失：type 从被引用输出的声明回填
        assertEquals("object", findFieldByName(inputs, "user").getString("type"));
        assertEquals("string", findFieldByName(inputs, "thought").getString("type"));
        // value_type 有值：原样保留，不走回填
        assertEquals("number", findFieldByName(inputs, "note").getString("type"));
        // 上游节点不存在：helper 兜底 string，与回填前 IR 生成的兜底行为一致
        assertEquals("string", findFieldByName(inputs, "ghost").getString("type"));
    }

    /**
     * bug② 哨兵：question-classifier 的出边 branch 必须映射为数字序号（branch_1..N，按 classes
     * 数组顺序），与 QuestionClassifierNodeConverter.adaptBranches 的节点侧编号一致——
     * runtime 意图路由链强依赖 branch_(\d+) 格式，Dify 语义 class id（如 dj/zx）会导致分类列表
     * 为空 + 条件全部兜底"分类0"→101021。
     */
    @Test
    void convertMapsIntentClassifierEdgesToNumberedBranches() {
        Map<String, Object> dsl = buildIntentDsl();
        adapter.validateFormat(dsl);

        WorkflowInfo info = adapter.convert(dsl);

        JSONObject details = new JSONObject(info.getWorkflowDetails());

        // 节点侧：branches 按 classes 顺序编号 branch_1..3
        JSONObject classifier = findNodeById(details.getJSONArray("nodes"), "node_classifier");
        assertNotNull(classifier);
        JSONArray branches = classifier.getJSONArray("branches");
        assertEquals(3, branches.size());
        assertEquals("branch_1", branches.getJSONObject(0).getString("id"));
        assertEquals("branch_2", branches.getJSONObject(1).getString("id"));
        assertEquals("branch_3", branches.getJSONObject(2).getString("id"));

        // 边侧：sourceHandle 的语义 class id 映射为同序号（dj 是 classes 第 2 个 → branch_2）
        assertEquals("branch_1", findEdge(details.getJSONArray("edges"), "node_classifier", "node_answer_zx")
            .getString("branch"));
        assertEquals("branch_2", findEdge(details.getJSONArray("edges"), "node_classifier", "node_answer_dj")
            .getString("branch"));
        assertEquals("branch_3", findEdge(details.getJSONArray("edges"), "node_classifier", "node_answer_kc")
            .getString("branch"));
    }

    /**
     * bug④ 哨兵（降级路径）：模型注册表查不到/解析失败时导入不得中断——model_name 保留，
     * model_deployment_id 留空交用户在编辑器手选。裸 UT 无 Spring 上下文，getBean 返回 null，
     * fillModelDeploymentInfo 走 catch 分支，正好覆盖该降级契约。
     */
    @Test
    void convertLlmNodeLeavesModelDeploymentIdEmptyWhenResolutionFails() {
        Map<String, Object> dsl = buildLlmDsl("ut-model-unregistered");
        adapter.validateFormat(dsl);

        WorkflowInfo info = adapter.convert(dsl);

        JSONObject details = new JSONObject(info.getWorkflowDetails());
        JSONObject llmNode = findNodeById(details.getJSONArray("nodes"), "node_llm");
        assertNotNull(llmNode);
        JSONObject model = llmNode.getJSONObject("configs").getJSONObject("model");
        assertEquals("ut-model-unregistered", model.getString("model_name"));
        assertTrue(model.getString("model_deployment_id") == null
            || model.getString("model_deployment_id").isEmpty(), "解析失败时 model_deployment_id 应留空");
    }

    /**
     * bug④ 哨兵（补全路径）：按模型名查到注册表记录时 model_deployment_id/model_type 必须补全
     * （IR 生成读这两个 key 拼 IR 模型名，缺失产生 "null|模型名" 畸形名 + 空 extension）。
     */
    @Test
    void convertLlmNodeFillsModelDeploymentIdFromRegistry() {
        ModelServiceBase registered = new ModelServiceBase()
            .setId("ut-deploy-1")
            .setModelType("llm");
        ModelServiceMapper mapper = mock(ModelServiceMapper.class);
        when(mapper.queryByModelName("ut-project", "ut-workspace", "ut-model", null))
            .thenReturn(List.of(registered));

        try (MockedStatic<RequestContextUtils> requestContext = mockStatic(RequestContextUtils.class);
             MockedStatic<SpringBeanUtils> springBeans = mockStatic(SpringBeanUtils.class)) {
            requestContext.when(RequestContextUtils::getRequestProjectId).thenReturn("ut-project");
            requestContext.when(RequestContextUtils::getRequestWorkspaceId).thenReturn("ut-workspace");
            springBeans.when(() -> SpringBeanUtils.getBean(ModelServiceMapper.class)).thenReturn(mapper);

            Map<String, Object> dsl = buildLlmDsl("ut-model");
            adapter.validateFormat(dsl);
            WorkflowInfo info = adapter.convert(dsl);

            JSONObject details = new JSONObject(info.getWorkflowDetails());
            JSONObject llmNode = findNodeById(details.getJSONArray("nodes"), "node_llm");
            assertNotNull(llmNode);
            JSONObject model = llmNode.getJSONObject("configs").getJSONObject("model");
            assertEquals("ut-model", model.getString("model_name"));
            assertEquals("ut-deploy-1", model.getString("model_deployment_id"));
            assertEquals("llm", model.getString("model_type"));
        }
    }

    private JSONObject findNodeById(JSONArray nodes, String id) {
        for (int i = 0; i < nodes.size(); i++) {
            JSONObject node = nodes.getJSONObject(i);
            if (id.equals(node.getString("id"))) {
                return node;
            }
        }
        return null;
    }

    private JSONObject findEdge(JSONArray edges, String source, String target) {
        for (int i = 0; i < edges.size(); i++) {
            JSONObject edge = edges.getJSONObject(i);
            if (source.equals(edge.getString("source")) && target.equals(edge.getString("target"))) {
                return edge;
            }
        }
        return null;
    }

    private Map<String, Object> difyVariable(String name, List<String> selector, String valueType) {
        Map<String, Object> variable = new HashMap<>();
        variable.put("variable", name);
        variable.put("value_selector", selector);
        if (valueType != null) {
            variable.put("value_type", valueType);
        }
        return variable;
    }

    private Map<String, Object> edgeOf(String id, String source, String sourceHandle, String target,
        String sourceType, String targetType) {
        Map<String, Object> edge = new HashMap<>();
        edge.put("id", id);
        edge.put("source", source);
        edge.put("sourceHandle", sourceHandle);
        edge.put("target", target);
        edge.put("targetHandle", "target");
        edge.put("type", "custom");
        edge.put("data", Map.of("sourceType", sourceType, "targetType", targetType,
            "isInIteration", false, "isInLoop", false));
        return edge;
    }

    private Map<String, Object> startNodeOf() {
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
        return nodeOf("start", startData, 50, 100);
    }

    private Map<String, Object> answerNodeOf(String id, int x) {
        Map<String, Object> answerData = new HashMap<>();
        answerData.put("type", "answer");
        answerData.put("title", "回复" + id);
        answerData.put("desc", "");
        answerData.put("answer", "你好");
        return nodeOf(id, answerData, x, 100);
    }

    /**
     * start → code_a(声明 user=object/thought=string 输出) → code_b(variables 混合：
     * 无 value_type 的 user/thought/ghost、带 value_type 的 note)。
     */
    private Map<String, Object> buildCodeChainDsl() {
        Map<String, Object> codeAData = new HashMap<>();
        codeAData.put("type", "code");
        codeAData.put("title", "上游代码");
        codeAData.put("desc", "");
        codeAData.put("variables", new ArrayList<>(List.of(
            difyVariable("user_meta", List.of("start", "user_meta"), null))));
        Map<String, Object> codeAOutputs = new HashMap<>();
        codeAOutputs.put("user", Map.of("type", "object"));
        codeAOutputs.put("thought", Map.of("type", "string"));
        codeAData.put("outputs", codeAOutputs);
        codeAData.put("code", "def main(user_meta: str) -> dict:\n    return {}\n");
        Map<String, Object> codeANode = nodeOf("code_a", codeAData, 250, 100);

        Map<String, Object> codeBData = new HashMap<>();
        codeBData.put("type", "code");
        codeBData.put("title", "下游代码");
        codeBData.put("desc", "");
        codeBData.put("variables", new ArrayList<>(List.of(
            difyVariable("user", List.of("code_a", "user"), null),
            difyVariable("thought", List.of("code_a", "thought"), null),
            difyVariable("note", List.of("code_a", "user"), "number"),
            difyVariable("ghost", List.of("code_missing", "user"), null))));
        codeBData.put("outputs", Map.of("result", Map.of("type", "object")));
        codeBData.put("code", "def main(user: dict) -> dict:\n    return {}\n");
        Map<String, Object> codeBNode = nodeOf("code_b", codeBData, 450, 100);

        Map<String, Object> graph = new HashMap<>();
        graph.put("nodes", List.of(startNodeOf(), codeANode, codeBNode));
        graph.put("edges", List.of(
            edgeOf("e_start_code_a", "start", "source", "code_a", "start", "code"),
            edgeOf("e_code_a_code_b", "code_a", "source", "code_b", "code", "code")));
        graph.put("viewport", Map.of("x", 0, "y", 0, "zoom", 1));
        return wrapGraph(graph, "ut-dify-code-chain");
    }

    /**
     * start → classifier(classes: zx/dj/kc) → 三个 answer 节点，出边 sourceHandle 用语义 class id。
     */
    private Map<String, Object> buildIntentDsl() {
        Map<String, Object> classifierData = new HashMap<>();
        classifierData.put("type", "question-classifier");
        classifierData.put("title", "场景识别");
        classifierData.put("desc", "");
        classifierData.put("query_variable_selector", List.of("start", "user_meta"));
        classifierData.put("classes", List.of(
            Map.of("id", "zx", "name", "综合咨询"),
            Map.of("id", "dj", "name", "电价方案"),
            Map.of("id", "kc", "name", "勘查方案")));
        Map<String, Object> classifierNode = nodeOf("classifier", classifierData, 250, 100);

        Map<String, Object> graph = new HashMap<>();
        graph.put("nodes", List.of(startNodeOf(), classifierNode,
            answerNodeOf("answer_zx", 450), answerNodeOf("answer_dj", 450), answerNodeOf("answer_kc", 450)));
        graph.put("edges", List.of(
            edgeOf("e_start_classifier", "start", "source", "classifier", "start", "question-classifier"),
            edgeOf("e_zx", "classifier", "zx", "answer_zx", "question-classifier", "answer"),
            edgeOf("e_dj", "classifier", "dj", "answer_dj", "question-classifier", "answer"),
            edgeOf("e_kc", "classifier", "kc", "answer_kc", "question-classifier", "answer")));
        graph.put("viewport", Map.of("x", 0, "y", 0, "zoom", 1));
        return wrapGraph(graph, "ut-dify-intent");
    }

    /**
     * start → llm(模型名可注入) → answer。
     */
    private Map<String, Object> buildLlmDsl(String modelName) {
        Map<String, Object> llmData = new HashMap<>();
        llmData.put("type", "llm");
        llmData.put("title", "LLM");
        llmData.put("desc", "");
        llmData.put("model", Map.of("name", modelName, "completion_params", Map.of("temperature", 0.5)));
        Map<String, Object> llmNode = nodeOf("llm", llmData, 250, 100);

        Map<String, Object> graph = new HashMap<>();
        graph.put("nodes", List.of(startNodeOf(), llmNode, answerNodeOf("answer", 450)));
        graph.put("edges", List.of(
            edgeOf("e_start_llm", "start", "source", "llm", "start", "llm"),
            edgeOf("e_llm_answer", "llm", "source", "answer", "llm", "answer")));
        graph.put("viewport", Map.of("x", 0, "y", 0, "zoom", 1));
        return wrapGraph(graph, "ut-dify-llm");
    }

    private Map<String, Object> wrapGraph(Map<String, Object> graph, String appName) {
        Map<String, Object> workflow = new HashMap<>();
        workflow.put("graph", graph);
        workflow.put("environment_variables", new ArrayList<>());
        workflow.put("conversation_variables", new ArrayList<>());

        Map<String, Object> dsl = new HashMap<>();
        dsl.put("app", Map.of("mode", "advanced-chat", "name", appName, "description", "UT夹具"));
        dsl.put("kind", "app");
        dsl.put("version", "0.1.0");
        dsl.put("workflow", workflow);
        return dsl;
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
