/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 */
package com.openjiuwen.studio.agent.manager.workflow.convert.adapt.difyadapter;

import com.alibaba.fastjson2.JSONObject;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.SpringBeanUtils;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.entity.md.ModelServiceBase;
import com.openjiuwen.studio.agent.manager.mapper.md.ModelServiceMapper;
import com.openjiuwen.studio.agent.manager.workflow.convert.adapt.enums.OutputParamsDiffType;

import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@SuppressWarnings("unchecked")
@Slf4j
public abstract class AbstractSDSLNodeConverter implements NodeConverter {

    private static final String DIFY_REF_REGEX = "\\{\\{#([^#}]+?)#\\}\\}";

    private static final String DIFY_VARIABLE_REGEX = "\\{\\{#(.*?)#}}";

    protected static final Map<String, String> OPERATOR_MAP;

    static {
        OPERATOR_MAP = Map.ofEntries(Map.entry("contains", "contain"), Map.entry("not contains", "not_contain"),
                Map.entry("is", "eq"), Map.entry("is not", "not_eq"), Map.entry("empty", "is_empty"),
                Map.entry("not empty", "is_not_empty"), Map.entry("=", "eq"), Map.entry("≠", "not_eq"),
                Map.entry(">", "longer_than"), Map.entry("<", "shorter_than"), Map.entry("≥", "longer_than_or_eq"),
                Map.entry("≤", "shorter_than_or_eq"));
    }

    @Override
    public WorkflowNodeVO parseMapData(Map<String, Object> nodeMap, Map<String, WorkflowNodeVO> workflowNodeMap) {
        WorkflowNodeVO workflowNodeVO = new WorkflowNodeVO();
        Map<String, Object> nodeConfig = (Map<String, Object>) nodeMap.get("data");
        workflowNodeVO.setId("node_" + nodeMap.get("id"));
        workflowNodeVO.setName(nodeConfig.get("title").toString());

        // 通用预处理
        // 处理循环节点的loop_body，标识哪些节点在循环内
        if (ObjectUtils.isNotEmpty(nodeMap.get("parentId")) && !workflowNodeVO.getId().contains("start")) {
            String parentId = (String) nodeMap.get("parentId");
            WorkflowNodeVO loopNode = workflowNodeMap.get(parentId);
            Map<String, Object> configs = loopNode.getConfigs();
            List<String> loopBody = (List<String>) configs.getOrDefault("loop_body", new ArrayList<String>());
            loopBody.add(workflowNodeVO.getId());
            configs.put("loop_body", loopBody);
            loopNode.setConfigs(configs);
        }
        WorkflowNodeVO adaptedWorkflowNodeVO = adapt(nodeConfig, workflowNodeVO, workflowNodeMap);
        if (adaptedWorkflowNodeVO.getConfigs() != null) {
            adaptedWorkflowNodeVO.getConfigs().put(CommonConstant.DIFY.DESCRIPTION_TEXT, nodeConfig.getOrDefault("desc",
                ""));
        }
        return adaptedWorkflowNodeVO;
    }

    /**
     * 变量转换：Dify -> AgentBuilder
     *
     * @param variables  Dify变量
     * @param workflowNodeMap  已转换节点map
     * @param currentNodeVO 当前节点的Node信息
     * @return AgentBuilder变量
     */
    public WorkflowFieldVOValue adaptWorkflowFieldVoValue(List<String> variables, Map<String, WorkflowNodeVO> workflowNodeMap, WorkflowNodeVO currentNodeVO) {
        // variables至少两个参数
        if (variables == null || variables.size() < 2) {
            return null;
        }
        Map<String, String> contentRef = new HashMap<>();
        // 预取值variables的前两个参数作为 difyRefNodeId 和 difyRefVarName
        String difyRefNodeId = variables.get(0);
        String difyRefVarName = variables.get(1);
        WorkflowNodeVO workflowNodeVO = workflowNodeMap.get(difyRefNodeId);

        if (ObjectUtils.isEmpty(workflowNodeVO)) {
            contentRef.put("ref_node_id", "node_" + difyRefNodeId);
            contentRef.put("ref_var_name", difyRefVarName);
            contentRef.put("source", WorkflowFieldVO.SourceEnum.USER.toString());
            return new WorkflowFieldVOValue()
                    .setType(WorkflowFieldVOValue.TypeEnum.REF)
                    .setContent(contentRef);
        }
        // 根据dify不同的参数类型适配：sys/env/node
        switch (difyRefNodeId) {
            case CommonConstant.DIFY.SYS_VARIABLE -> {
                contentRef.put("ref_node_id", "node_start");
                if ("query".equalsIgnoreCase(difyRefVarName)) {
                    contentRef.put("ref_var_name", difyRefVarName);
                } else {
                    contentRef.put("ref_var_name", CommonConstant.DIFY.SYS_VARIABLE + "." + difyRefVarName);
                }
                contentRef.put("source", WorkflowFieldVO.SourceEnum.SYSTEM.toString());
            }
            case CommonConstant.DIFY.CONVERSATION_VARIABLE -> {
                contentRef.put("ref_node_id", "node_start");
                contentRef.put("source", WorkflowFieldVO.SourceEnum.PRE_DEFINED.toString());
                contentRef.put("ref_var_name", "memory" + "." + difyRefVarName);
            }
            case CommonConstant.DIFY.ENV_VARIABLE -> {
                return new WorkflowFieldVOValue()
                    .setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
                    .setContent(getResolvedEnvReferenceValue(difyRefVarName, workflowNodeMap))
                    .setHint("环境变量");
            }
            default -> {
                switch (workflowNodeVO.getType()) {
                    case "Aggregation", "Agent" -> {
                        contentRef.put("ref_node_id", workflowNodeVO.getId());
                        contentRef.put("ref_var_name",
                                OutputParamsDiffType.getVariableName("Dify_" + workflowNodeVO.getType() + "_" + difyRefVarName.toLowerCase(Locale.ROOT)));
                        contentRef.put("source", WorkflowFieldVO.SourceEnum.USER.toString());
                    }
                    case "LLM" -> {
                        contentRef.put("ref_node_id", workflowNodeVO.getId());
                        contentRef.put("ref_var_name", buildVariablePath(variables));
                        contentRef.put("source", WorkflowFieldVO.SourceEnum.USER.toString());
                    }
                    default -> {
                        contentRef.put("ref_node_id", workflowNodeVO.getId());
                        // 对循环节点的中间变量进行特殊处理
                        if (NodeType.LOOP.getType().equals(workflowNodeVO.getType()) && JSONObject.toJSONString(
                                workflowNodeVO.getConfigs().get("loop_body")).contains(currentNodeVO.getId())) {
                            difyRefVarName = String.format("intermediate_loop_var.%s", difyRefVarName);
                        }
                        String refVarName = OutputParamsDiffType.getVariableName(
                                "Dify_" + workflowNodeVO.getType() + "_" + difyRefVarName);
                        // 3+ 段引用（如 code 节点 result.<嵌套key>）保留嵌套路径，与 LLM 分支的
                        // buildVariablePath 对齐：此前只用第 2 段（顶层输出名），嵌套 key 被丢弃，
                        // 导致不同字段的引用全部指向同一个输出对象（如 4 个电价字段全 ref 到 result 整对象）。
                        // ref 路径用原始 key——运行时数据 key 即代码返回 dict 的 key（可为中文），
                        // 拼音仅发生在用户手动改输入参数名时，不影响 ref。
                        if (variables.size() > 2) {
                            refVarName = refVarName + "." + String.join(".", variables.subList(2, variables.size()));
                        }
                        contentRef.put("ref_var_name", refVarName);
                        if (("query".equalsIgnoreCase(difyRefVarName) || "sys.query".equalsIgnoreCase(difyRefVarName)) && "node_start".equalsIgnoreCase(workflowNodeVO.getId())) {
                            contentRef.put("source", WorkflowFieldVO.SourceEnum.SYSTEM.toString());
                            contentRef.put("ref_var_name", "query");
                        } else {
                            contentRef.put("source", WorkflowFieldVO.SourceEnum.USER.toString());
                        }
                    }
                }
            }
        }
        return new WorkflowFieldVOValue()
                .setType(WorkflowFieldVOValue.TypeEnum.REF)
                .setContent(contentRef);
    }


    /**
     * 按模型名查平台模型注册表，补全 modelInfo 的 model_deployment_id / model_type。
     *
     * <p>背景：Dify yml 的模型只有名字（如 qwen3.7-plus），无平台 deployment id 概念；
     * IR 生成（{@code AbstractIRNodeAdapter.adaptModel}）读 configs.model.model_deployment_id
     * 拼 IR 模型名（{@code deploymentId|modelName}）并解析 extension，为空时产生
     * {@code "null|模型名"} 畸形名 + 空 extension（"包含空元素: model_deployment_id"）。</p>
     *
     * <p>查不到（模型未在平台注册/名字对不上）保持留空——用户在节点编辑器手动选模型，
     * 不阻断导入。多个同名模型取第一个（warn 提示）。解析异常不抛（warn 后留空）。</p>
     *
     * @param modelInfo 模型信息 map（调用方已放好 model_name，此处补全另两个 key）
     * @param modelName Dify 模型名
     */
    protected void fillModelDeploymentInfo(Map<String, String> modelInfo, String modelName) {
        try {
            String projectId = RequestContextUtils.getRequestProjectId();
            String workspaceId = RequestContextUtils.getRequestWorkspaceId();
            List<ModelServiceBase> models = SpringBeanUtils.getBean(ModelServiceMapper.class)
                .queryByModelName(projectId, workspaceId, modelName, null);
            if (models == null || models.isEmpty()) {
                log.warn("Dify import: no platform model for name {}, model_deployment_id left empty", modelName);
                return;
            }
            if (models.size() > 1) {
                log.warn("Dify import: {} models match name {}, using first (id={})",
                    models.size(), modelName, models.get(0).getId());
            }
            ModelServiceBase model = models.get(0);
            modelInfo.put(CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID, model.getId());
            modelInfo.put(CommonConstant.ModelParam.MODEL_TYPE, model.getModelType());
        } catch (Exception e) {
            log.warn("Dify import: model resolution failed for name {}", modelName, e);
        }
    }

    /**
     * 把环境变量引用转换成固定的值 （如果没有固定的值，则用 {{env.project_id}} 这种形式代替
     * @param varName 引用环境变量名字
     * @param workflowNodeMap 已经解析好的节点（key:节点名字，value：节点）
     * @return 引用转换后的 String
     */
    public Object getResolvedEnvReferenceValue(String varName,
        Map<String, WorkflowNodeVO> workflowNodeMap) {
        WorkflowNodeVO envNode = workflowNodeMap.get(CommonConstant.DIFY.ENV_VARIABLE);
        if (envNode != null && envNode.getOutputs() != null) {
            for (WorkflowFieldVO output : envNode.getOutputs()) {
                if (output.getName().equals(varName) && output.getValue() != null) {
                    Object defaultValue = output.getValue().getDefault();
                    if (defaultValue != null) {
                        return defaultValue;
                    }
                }
            }
        }
        return "{{" + CommonConstant.DIFY.ENV_VARIABLE + "." + varName + "}}";
    }

    // 无需适配输入参数的通配方法，需适配在对应的节点转换器复写
    @Override
    public List<WorkflowFieldVO> adaptInputs(Map<String, Object> data, Map<String, WorkflowNodeVO> workflowNodeMap) {
        return null;
    }

    // 无需适配configs的通配方法，需适配在对应的节点转换器复写
    @Override
    public Map<String, Object> adaptConfigs(Map<String, Object> data) {
        Map<String, Object> configsMap = new HashMap<>();
        configsMap.put(CommonConstant.DIFY.CONFIG_DEFAULT_NAME, false);
        return configsMap;
    }

    @Override
    public List<WorkflowFieldVO> adaptOutputs(Map<String, Object> data) {
        return null;
    }

    /**
     * 将{{#XXX.XXX#}}格式转换为WorkflowFieldVOValue
     * @param value 需要提取的文本 {{#XXX.XXX#}} 格式
     * @param workflowNodeMap 已转换的节点数据
     * @return 格式转换为WorkflowFieldVOValue
     */
    public WorkflowFieldVOValue extractValueToField(String value, WorkflowNodeVO workflowNodeVO, Map<String, WorkflowNodeVO> workflowNodeMap) {
        Pattern pattern = Pattern.compile(DIFY_VARIABLE_REGEX);
        Matcher matcher = pattern.matcher(value);

        if (matcher.find()) {
            String core = matcher.group(1);
            if (core.contains(".")) {
                String[] parts = core.split("\\.");
                if (parts.length == 2) {
                    return adaptWorkflowFieldVoValue(Arrays.asList(parts), workflowNodeMap, workflowNodeVO);
                }
            }
        }
        return new WorkflowFieldVOValue().setContent(value)
            .setType(WorkflowFieldVOValue.TypeEnum.LITERAL)
            .setHint("");
    }

    /**
     * 提取 ID 和 Name，支持一个 ID 对应多个 Name 且不重复
     * 支持格式：{{#id#}} 或 {{#id.name#}} 或 {{#id.name1.name2#}}
     *
     * @param text       原始文本
     * @param idNameMap  传入一个空的 Map<String, Set<List<String>>>，方法将填充此 Map。如果传null，代表只需要转文本即可
     * @return 替换后的文本 {{#id.name#}} -> {{_id_name}}
     */
    public String extractAndReplace(String text, Map<String, Set<List<String>>> idNameMap) {
        if (StringUtils.isEmpty(text)) {
            return text;
        }
        Pattern pattern = Pattern.compile(DIFY_REF_REGEX);
        Matcher matcher = pattern.matcher(text);
        StringBuilder sb = new StringBuilder();
        while (matcher.find()) {
            String content = matcher.group(1);
            String[] parts = content.split("\\.");
            String replacement = "{{_" + String.join("_", parts) + "}}";
            if (parts.length < 2) {
                matcher.appendReplacement(sb, Matcher.quoteReplacement("{{" + content + "}}"));
                continue;
            }
            if (idNameMap != null) {
                idNameMap.computeIfAbsent(parts[0], k -> new HashSet<>()).add(Arrays.asList(parts));
            }
            matcher.appendReplacement(sb, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(sb);
        return sb.toString();
    }

    /**
     * 将 idNameMap 转换为 List<WorkflowFieldVO>
     *
     * @param idNameMap      ID -> Name 集合的映射
     * @param workflowNodeMap ID -> WorkflowNodeVO 的映射
     * @return 转换后的 WorkflowFieldVO 列表
     */
    public List<WorkflowFieldVO> convertToFieldVOs(Map<String, Set<List<String>>> idNameMap,
                                                   Map<String, WorkflowNodeVO> workflowNodeMap) {

        List<WorkflowFieldVO> resultList = new ArrayList<>();
        for (Map.Entry<String, Set<List<String>>> entry : idNameMap.entrySet()) {
            String id = ("sys").equalsIgnoreCase(entry.getKey()) ? "node_start" : entry.getKey();
            Set<List<String>> refNames = entry.getValue();
            WorkflowNodeVO node = workflowNodeMap.get(id);
            for (List<String> refName : refNames) {
                WorkflowFieldVO newField = new WorkflowFieldVO();
                newField.setName("_" + String.join("_", refName));
                newField.setRequired(true);
                newField.setSource(WorkflowFieldVO.SourceEnum.USER);
                newField.setValue(adaptWorkflowFieldVoValue(refName, workflowNodeMap, workflowNodeMap.get(entry.getKey())));
                setTypeAndSchemaByName(newField, node, refName);
                resultList.add(newField);
            }
        }
        return resultList;
    }

    /**
     * 根据名称路径查找，并设置变量的type和schema
     * 传入的 List 第一个元素是 nodeId，从第二个元素开始作为变量名路径
     *
     * @param workflowFieldVO  待赋值的对象
     * @param targetNode       目标节点
     * @param targetNameList   路径列表，结构为 [nodeId, name1, name2...]
     */
    public void setTypeAndSchemaByName(WorkflowFieldVO workflowFieldVO, WorkflowNodeVO targetNode, List<String> targetNameList) {
        workflowFieldVO.setType("string");
        workflowFieldVO.setSchema("");

        // 如果找不到目标node或引用的参数长度不够，则返回默认值
        if (targetNode == null || targetNameList == null || targetNameList.size() < 2) {
            return;
        }

        // 变量赋值节点取前两个参数
        if (NodeType.AGGREGATION.getType().equals(targetNode.getType())) {
            targetNameList = targetNameList.subList(0, 2);
        }

        List<WorkflowFieldVO> variables = null;
        // 获取开始节点参数
        if (NodeType.START.getType().equals(targetNode.getType()) && targetNode.getOutputs() != null) {
            for (WorkflowFieldVO sysVariables : targetNode.getOutputs()) {
                if (CommonConstant.DIFY.SYS_VARIABLE.equals(sysVariables.getName()) && sysVariables.getSchema() instanceof List) {
                    variables = (List<WorkflowFieldVO>) sysVariables.getSchema();
                    break;
                }
            }
        } else {
            // 如果非开始节点 获取非开始节点参数
            variables = Optional.ofNullable(targetNode.getOutputs()).orElse(Collections.emptyList());
        }

        // 获取根节点参数名称
        WorkflowFieldVO currentField = null;
        String mappedFirstName = OutputParamsDiffType.getVariableName("Dify_" + targetNode.getType() + "_" + targetNameList.get(1));
        for (WorkflowFieldVO variable : variables) {
            if (mappedFirstName.equals(variable.getName())) {
                currentField = variable;
                break;
            }
        }
        // 找不到根节点参数返回默认值
        if (currentField == null) {
            return;
        }

        // 在schema中递归查找子项参数
        for (int i = 2; i < targetNameList.size(); i++) {
            String nextName = targetNameList.get(i);
            // 获取当前层的 schema，准备进入下一层
            Object schemaObj = currentField.getSchema();
            // 检查 schema 是否有效且为 List
            if (!(schemaObj instanceof List)) {
                return;
            }
            List<WorkflowFieldVO> nestedFields = (List<WorkflowFieldVO>) schemaObj;
            boolean foundInNextLevel = false;
            for (WorkflowFieldVO nestedField : nestedFields) {
                if (nextName.equals(nestedField.getName())) {
                    currentField = nestedField;
                    foundInNextLevel = true;
                    break;
                }
            }
            if (!foundInNextLevel) {
                return;
            }
        }
        Optional.ofNullable(currentField.getType()).ifPresent(workflowFieldVO::setType);
        Optional.ofNullable(currentField.getSchema()).ifPresent(workflowFieldVO::setSchema);
    }

    /**
     * 将 value_selector 列表转换为点分变量路径字符串
     * 规则：跳过第一个元素（ID），将剩余元素用 "." 拼接
     *
     * @param valueSelector 选择器列表
     * @return 拼接后的路径字符串
     */
    public static String buildVariablePath(List<String> valueSelector) {
        if (valueSelector == null || valueSelector.size() <= 1) {
            return "";
        }
        return valueSelector.stream()
                .skip(1)
                .map(Object::toString)
                .collect(Collectors.joining("."));
    }

    /**
     * 解析原始type字符串（如array[object]→array，object→object）
     * @param sourceType 原始类型字符串
     * @return 目标类型字符串
     */
    public String parseSourceType(String sourceType) {
        if (ObjectUtils.isEmpty(sourceType)) {
            return "string";
        }
        if (sourceType.startsWith("array[")) {
            return "array";
        }
        return sourceType;
    }

    /**
     * 解析原始type字符串（如array[object]→{"name":"","schema":[],"schema":"object"}）
     * @param sourceType 原始类型字符串
     * @return 目标类型Schema
     */
    public Object parseSchema(String sourceType) {
        if (ObjectUtils.isEmpty(sourceType)) {
            return "";
        }
        if (sourceType.startsWith("array[")) {
            HashMap<String, Object> schema = new HashMap<>();
            schema.put("name", "");
            schema.put("type", sourceType.substring(6, sourceType.length() - 1));
            return schema;
        }
        if ("object".equals(sourceType)) {
            return new ArrayList<>();
        }
        return null;
    }

    public WorkflowFieldVO getBranchFieldVO(Map<String, Object> data, WorkflowNodeVO workflowNodeVO, List<String> selector) {
        WorkflowFieldVO fieldVO = new WorkflowFieldVO();
        fieldVO.setSource(WorkflowFieldVO.SourceEnum.USER);
        fieldVO.setName("");
        fieldVO.setRequired(false);
        if (data.get("varType") == null) {
            setTypeAndSchemaByName(fieldVO, workflowNodeVO, selector);
        } else {
            fieldVO.setType(parseSourceType((String) data.get("varType")));
            fieldVO.setSchema(parseSchema((String) data.get("varType")));
        }
        return fieldVO;
    }
}
