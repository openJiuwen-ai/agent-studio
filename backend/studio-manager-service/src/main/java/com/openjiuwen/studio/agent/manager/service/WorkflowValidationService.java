/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
 */

package com.openjiuwen.studio.agent.manager.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openjiuwen.studio.agent.common.constant.Constants;
import com.openjiuwen.studio.agent.common.enums.NodeType;
import com.openjiuwen.studio.agent.common.enums.StudioError;
import com.openjiuwen.studio.agent.common.enums.TypeEnum;
import com.openjiuwen.studio.agent.common.exception.AgentStudioException;
import com.openjiuwen.studio.agent.common.sensitive.SensitiveEntity;
import com.openjiuwen.studio.agent.common.utils.I18nUtil;
import com.openjiuwen.studio.agent.common.utils.RequestContextUtils;
import com.openjiuwen.studio.agent.common.utils.UrlCheckUtils;
import com.openjiuwen.studio.agent.manager.bo.ValidateConfigWrapper;
import com.openjiuwen.studio.agent.manager.constant.CommonConstant;
import com.openjiuwen.studio.agent.manager.dto.ExceptionProcess;
import com.openjiuwen.studio.agent.manager.dto.ParamExtractionExceptionConfig;
import com.openjiuwen.studio.agent.manager.dto.UserProfileMemoryConfig;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchConfigVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowBranchVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowEdgeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowFieldVOValue;
import com.openjiuwen.studio.agent.manager.dto.WorkflowNodeVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVO;
import com.openjiuwen.studio.agent.manager.dto.WorkflowValidationVOErrors;
import com.openjiuwen.studio.agent.manager.entity.KnowledgeRepoEntity;
import com.openjiuwen.studio.agent.manager.entity.ReleaseVersion;
import com.openjiuwen.studio.agent.manager.entity.ShareResourceEntity;
import com.openjiuwen.studio.agent.manager.entity.ShareScopeEntity;
import com.openjiuwen.studio.agent.manager.entity.ToolEntity;
import com.openjiuwen.studio.agent.manager.entity.WorkflowEntity;
import com.openjiuwen.studio.agent.manager.enums.ToolType;
import com.openjiuwen.studio.agent.manager.mapper.ReleaseVersionMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareResourceMapper;
import com.openjiuwen.studio.agent.manager.mapper.ShareScopeMapper;
import com.openjiuwen.studio.agent.manager.mapper.WorkflowMapper;
import com.openjiuwen.studio.agent.manager.obs.MgObsService;
import com.openjiuwen.studio.agent.manager.service.environment.EnvironmentServiceManagerService;
import com.openjiuwen.studio.agent.manager.service.md.ModelServiceManager;
import com.openjiuwen.studio.agent.manager.service.memory.AgentMemoryConfigService;
import com.openjiuwen.studio.agent.manager.service.plugin.IPluginBase;
import com.openjiuwen.studio.agent.manager.utils.JsonUtils;
import com.openjiuwen.studio.agent.manager.utils.McpJsonUtils;
import com.openjiuwen.studio.agent.manager.utils.WorkflowUtils;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.GroupConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.IRConfig;
import com.openjiuwen.studio.agent.manager.workflow.jiuwen.models.SetVariableConfig;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Strings;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Queue;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BiConsumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import javax.annotation.PostConstruct;

/**
 * workflow校验服务
 *
 */
@Slf4j
@Service
public class WorkflowValidationService {
    /**
     * 中英文名长度限制
     */
    private static final int MAX_NAME_SIZE = 64;

    /**
     * 参数名称字段
     */
    private static final int KB = 1024;

    /**
     * 参数名称字段
     */
    private static final String NAME = "name";

    /**
     * 参数类型字段
     */
    private static final String TYPE = "type";

    /**
     * 参数结构字段
     */
    private static final String SCHEMA = "schema";

    /**
     * 循环体节点字段
     */
    private static final String LOOP_BODY = "loop_body";

    /**
     * 字段为空reason
     */
    private static final String EMPTY_REASON = "%s should not be empty";

    /**
     * 异常处理节点
     */
    private static final String EXCEPTION_PROCESS = "exception_process";

    /**
     * 参数提取节点异常处理配置
     */
    private static final String EXCEPTION_CONFIG = "exception_config";

    /**
     * 英文名以字母开头，可包含下划线，以字母或数字结尾
     */
    private static final String CODE_REGEX = "^[a-zA-Z]([-a-zA-Z0-9_\\.\\s]*[a-zA-Z0-9])?$";

    /**
     * 异常情况下正常分支
     */
    private static final String NORMAL_BRANCH = "@@branch_0";

    /**
     * 异常分支
     */
    private static final String EXCEPTION_BRANCH = "@@branch_1";

    /**
     * 中文名称支持任意中文、数字、字母、中划线、下划线、括号、感叹号
     */
    private static final String NAME_REGEX =
        "^[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!](?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]*[\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！!])?$";

    private static final String INVALID_NAME_REGEX = "[^\\u4e00-\\u9fa5a-zA-Z0-9_\\-（）()！! ]";

    /**
     * 提取{{}}包裹变量
     */
    private static final String REF_REGEX = "\\{\\{\\s*(\\w+)\\s*}}";

    private static final String QA_NODE_STRATEGY = "qaStrategy";

    private static final String QA_NODE_STRATEGY_RANDOM = "random";

    /**
     * 代码节点执行方式
     */
    private static final String EXEC_ENV = "exec_env";

    private static final String SANDBOX = "sandbox";

    /**
     * 只允许输入字母、数字，中划线，下划线，且不能以数字开头
     */
    private static final Pattern VALID_PATTERN = Pattern.compile("^[a-zA-Z_-][a-zA-Z0-9_-]*$");

    private static final String MESSAGE = "Message";

    private static final String ENABLE_HISTORY = "enable_history";

    @Value("${tool.plugin-publish:false}")
    private boolean pluginChoice;

    private static Pattern codePattern;

    private static Pattern referencePattern;

    private static Pattern namePattern;

    private static Pattern invalidNamePatter;

    @Autowired
    WorkflowMapper workflowMapper;

    @Autowired
    IrAdapterService irAdapterService;

    @Autowired
    MgObsService obsService;

    @Autowired
    ReleaseVersionMapper releaseVersionMapper;

    @Autowired
    UrlCheckUtils urlCheckUtils;

    @Autowired
    private ModelServiceManager modelServiceManager;

    @Autowired
    private IPluginBase pluginDomain;

    @Autowired
    private ShareResourceManagerService shareResourceManagerService;

    @Autowired
    private ShareResourceMapper shareResourceMapper;

    @Autowired
    private ShareScopeMapper shareScopeMapper;

    @Autowired
    private EnvironmentServiceManagerService environmentServiceManagerService;

    @Value("${workflow.schema:}")
    private String workflowSchema;

    @Value("${icon.max-size}")
    private String iconMaxSize;

    @Value("${op.svc.project-id}")
    private String opSvcProjectId;

    @Value("${workflow.system-fields:}")
    private String systemFields;

    @Value("${workflow.loop.interactive-node-type}")
    private String interactiveNodeType;

    @Value("${workflow.max-node-num}")
    private int maxNodeNum;

    @Value("${workflow.parallel.branch-node-type}")
    private String branchNodeType;

    @Value("${workflow.exception-support-nodes}")
    private String workflowExceptionSupportNodes;

    @Value("${env.type}")
    private String envType;

    @Value("${env.sandbox.enable}")
    private boolean sandboxEnable;

    @Value("${agent-builder.publish-cross-workspace.enable:false}")
    private boolean publishCrossWorkspace;

    @Value("${allow-plugin-cross-permission-query:false}")
    private boolean allowPluginCrossPermissionQuery;

    @Value("${front-page.block-nodes}")
    private String blockNodes;

    @Value("${workflow_node_questioner_config_maxLength:3000}")
    private int questionerConfigMaxLength;

    private List<String> exceptionNodeTypes;

    private List<String> branchNodeTypes;

    private List<String> interactiveNodeTypes;

    @Autowired
    private I18nUtil i18nUtil;

    @Autowired
    private AgentMemoryConfigService agentMemoryConfigService;

    /**
     * 正则匹配预编译
     */
    @PostConstruct
    public void init() {
        interactiveNodeTypes = Arrays.stream(interactiveNodeType.split(CommonConstant.SEPARATOR)).toList();
        codePattern = Pattern.compile(CODE_REGEX);
        referencePattern = Pattern.compile(REF_REGEX);
        namePattern = Pattern.compile(NAME_REGEX);
        invalidNamePatter = Pattern.compile(INVALID_NAME_REGEX);
        branchNodeTypes = Arrays.stream(branchNodeType.split(CommonConstant.SEPARATOR)).toList();
        exceptionNodeTypes = Arrays.stream(workflowExceptionSupportNodes.split(CommonConstant.SEPARATOR)).toList();
    }

    /**
     * 拆分工作流定义转换为图，并验证工作流信息
     *
     * @param workflow 工作流定义
     * @return 工作流验证信息，包含错误信息
     */
    public WorkflowValidationVO validate(String projectId, String workspaceId, WorkflowVO workflow) {
        // 获取工作流节点以及连接关系
        Node startNode = null;
        Node endNode = null;
        Map<String, Node> nodeMap = new HashMap<>();
        Set<String> freeNodeIds = WorkflowUtils.getFreeNodes(workflow);
        for (WorkflowNodeVO workflowNodeVo : workflow.getNodes()) {
            // 游离节点不参与工作流校验
            if (!CollectionUtils.isEmpty(freeNodeIds) && freeNodeIds.contains(workflowNodeVo.getId())) {
                continue;
            }
            nodeMap.put(workflowNodeVo.getId(), new Node(workflowNodeVo));
            if (Strings.CS.equals(NodeType.START.getType(), workflowNodeVo.getType())) {
                startNode = nodeMap.get(workflowNodeVo.getId());
            }
            if (Strings.CS.equals(NodeType.END.getType(), workflowNodeVo.getType())) {
                endNode = nodeMap.get(workflowNodeVo.getId());
            }
        }
        for (WorkflowEdgeVO workflowEdgeVo : workflow.getEdges()) {
            Node sourceNode = nodeMap.get(workflowEdgeVo.getSource());
            Node targetNode = nodeMap.get(workflowEdgeVo.getTarget());

            // 游离节点不参与工作流校验
            if (sourceNode == null || targetNode == null) {
                continue;
            }
            sourceNode.getOutNodes().add(targetNode);
            targetNode.getInNodes().add(sourceNode);
            if (StringUtils.isNotEmpty(workflowEdgeVo.getBranch())) {
                sourceNode.getOutBranches().add(workflowEdgeVo.getBranch());
            } else if (Boolean.TRUE.equals(workflowEdgeVo.isExceptionBranch())) {
                // 新增异常分支标记
                sourceNode.getOutBranches().add(EXCEPTION_PROCESS);
            }
        }
        // 循环节点内部节点需标志归属循环节点，便于后续验证
        for (WorkflowNodeVO workflowNodeVo : workflow.getNodes()) {
            if (nodeMap.containsKey(workflowNodeVo.getId())
                && Strings.CS.equals(NodeType.LOOP.getType(), workflowNodeVo.getType())) {
                Node loopNode = nodeMap.get(workflowNodeVo.getId());
                Map<String, Object> configs = loopNode.getNodeInfo().getConfigs();
                if (configs != null && configs.get(LOOP_BODY) != null) {
                    List<String> loopBody = JsonUtils.objectToClass(configs.get(LOOP_BODY));
                    if (loopBody != null) {
                        loopBody.forEach(nodeId -> nodeMap.get(nodeId).setParentLoopNode(loopNode));
                    }
                }
            }
        }
        // 工作流非游离节点最大数目校验
        if (nodeMap.size() > maxNodeNum) {
            throw new AgentStudioException(StudioError.WORKFLOW_NODE_EXCEED_LIMITS);
        }

        // 基本校验
        WorkflowValidationVO workflowValidationVo = validateAll(projectId, workspaceId, startNode, endNode, nodeMap);

        Map<String, String> reflection = new HashMap<>();
        workflow.getNodes().forEach(m -> reflection.put(m.getId(), m.getType()));

        // 并行节点校验
        List<WorkflowEdgeVO> edges = irAdapterService.addEdgeExceptionBranch(workflow, reflection);
        List<WorkflowNodeVO> nodes = irAdapterService.addNodeExceptionBranch(workflow, reflection);

        for (WorkflowNodeVO node : nodes) {
            List<WorkflowBranchVO> branches = node.getBranches();
            if (CollectionUtils.isEmpty(branches)) {
                continue;
            }
            AtomicBoolean hasExceptionBranch = new AtomicBoolean(false);
            branches.forEach(branch -> {
                if (Strings.CS.equals(branch.getId(), EXCEPTION_BRANCH)) {
                    hasExceptionBranch.set(true);
                }
            });
            if (!hasExceptionBranch.get()) {
                continue;
            }
            // 如果有异常分支，要求正常分支必须有连接线
            AtomicBoolean hasNormalBranch = new AtomicBoolean(false);
            branches.forEach(branch -> {
                if (Strings.CS.equals(branch.getId(), NORMAL_BRANCH)) {
                    hasNormalBranch.set(true);
                }
            });
            if (!hasNormalBranch.get()) {
                workflowValidationVo.getErrors().add(new WorkflowValidationVOErrors().setId(node.getId()).setType(node
                    .getType()).setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.output.least"),
                        node.getId())));
            }
        }
        List<WorkflowValidationVOErrors> errors = irAdapterService.addParallelTag(nodes, edges, freeNodeIds);
        workflowValidationVo.getErrors().addAll(errors);

        workflowValidationVo.setSuccess(workflowValidationVo.getErrors().isEmpty());
        return workflowValidationVo;
    }

    /**
     * 验证节点信息，包括连接关系，是否必填等
     *
     * @param startNode 开始节点
     * @param endNode 结束节点
     */
    private WorkflowValidationVO validateAll(String projectId, String workspaceId, Node startNode, Node endNode,
        Map<String, Node> nodeMap) {
        WorkflowValidationVO result = new WorkflowValidationVO().setSuccess(true).setErrors(new ArrayList<>());
        List<WorkflowValidationVOErrors> errors = result.getErrors();

        // 获取节点与可选输入映射
        Map<String, List<String>> inputReference = new HashMap<>();
        for (Node node : nodeMap.values()) {
            if (node.getNodeInfo().getInputs() != null) {
                inputReference.put(node.getId(),
                    node.getNodeInfo().getInputs().stream().map(WorkflowFieldVO::getName).collect(Collectors.toList()));
            } else {
                inputReference.put(node.getId(), new ArrayList<>());
            }
        }
        validateNodeDuplicateAttribute(nodeMap, errors);
        // 0.验证节点配置中必填项
        validateNodeConfig(projectId, workspaceId, nodeMap, inputReference, errors);

        // 1.start节点无入，end节点只有入
        validateTerminusNodeEdge(startNode, endNode, errors);

        // 2.其余非分支节点必须有出有入，确保无游离节点
        validateNormalNodeEdge(nodeMap, errors);

        // 获取节点与可选输出映射
        Map<String, List<String>> outputReference = new HashMap<>();
        List<Node> codeNodeList = new ArrayList<>();
        for (Node node : nodeMap.values()) {
            if (node.getNodeInfo().getOutputs() != null) {
                outputReference.put(node.getId(),
                    node.getNodeInfo()
                        .getOutputs()
                        .stream()
                        .map(WorkflowFieldVO::getName)
                        .collect(Collectors.toList()));
            } else {
                outputReference.put(node.getId(), new ArrayList<>());
            }
            if (Strings.CS.equals(node.getType(), NodeType.LOOP.getType())) {
                // 循环节点比较特殊，预定义输入值可以被循环体内引用
                if (node.getNodeInfo().getInputs() != null) {
                    outputReference.get(node.getId())
                        .addAll(node.getNodeInfo().getInputs().stream().map(WorkflowFieldVO::getName).toList());
                }
                // 循环节点隐含变量index可被循环体内节点引用
                outputReference.get(node.getId()).add("index");
            }
            if (Strings.CS.equals(node.getType(), NodeType.START.getType())) {
                // 开始节点隐含变量memory可被后续节点引用
                outputReference.get(node.getId()).add(CommonConstant.MEMORY);
            }
            if (Strings.CS.equals(node.getType(), NodeType.CODE.getType())) {
                codeNodeList.add(node);
            }
        }

        // 3.对输入输出内容进行检查
        validateNodeParams(nodeMap, outputReference, errors);

        // 4.判断单节点成环以及环无跳出逻辑（环中无分支类组件）
        validateAcyclic(nodeMap, errors);

        if (!errors.isEmpty()) {
            result.setSuccess(false);
            result.setErrors(errors);
        }
        return result;
    }

    private void validateNodeDuplicateAttribute(Map<String, Node> nodeMap, List<WorkflowValidationVOErrors> errors) {
        for (Node node : nodeMap.values()) {
            WorkflowNodeVO workflowNodeVO = node.getNodeInfo();
            validateDuplicateAttribute(workflowNodeVO.getInputs(), errors, node);
            validateDuplicateAttribute(workflowNodeVO.getOutputs(), errors, node);
        }
    }

    private void validateDuplicateAttribute(List<WorkflowFieldVO> workflowNodeVO,
        List<WorkflowValidationVOErrors> errors, Node node) {
        if (CollectionUtils.isEmpty(workflowNodeVO) || NodeType.SET_VARIABLE.getType().equals(node.getType())) {
            return;
        }
        Map<String, Long> filedNameCount = workflowNodeVO.stream()
            .collect(Collectors.groupingBy(WorkflowFieldVO::getName, Collectors.counting()));
        List<String> duplicateFieldNames = filedNameCount.entrySet()
            .stream()
            .filter(entry -> entry.getValue() > 1)
            .map(Map.Entry::getKey)
            .collect(Collectors.toList());
        if (CollectionUtils.isNotEmpty(duplicateFieldNames)) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId()).setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.param.duplicate"),
                    duplicateFieldNames.stream().collect(Collectors.joining(",")))));
        }
    }

    private void validateTerminusNodeEdge(Node startNode, Node endNode, List<WorkflowValidationVOErrors> errors) {
        if (startNode == null || !startNode.getInNodes().isEmpty()) {
            // 开始节点无输入
            errors.add(new WorkflowValidationVOErrors()
                .setId(startNode != null ? startNode.getId() : CommonConstant.Workflow.NODE_START)
                .setType(startNode != null ? startNode.getType() : NodeType.START.getType())
                .setReason(i18nUtil.getMessage("workflow.validate.node.start")));
        }
        if (endNode == null || endNode.getInNodes().isEmpty() || !endNode.getOutNodes().isEmpty()) {
            // 结束节点只有输入，无输出
            errors.add(new WorkflowValidationVOErrors()
                .setId(endNode != null ? endNode.getId() : CommonConstant.Workflow.NODE_END)
                .setType(endNode != null ? endNode.getType() : NodeType.END.getType())
                .setReason(i18nUtil.getMessage("workflow.validate.node.end")));
        }
    }

    private void validateNormalNodeEdge(Map<String, Node> nodeMap, List<WorkflowValidationVOErrors> errors) {
        List<String> excludeInputNodes = List.of(NodeType.START.getType(), NodeType.LOOP_INPUT.getType());
        List<String> excludeOutputNodes = List.of(NodeType.END.getType(), NodeType.LOOP_OUTPUT.getType());
        for (Node node : nodeMap.values()) {
            // 节点有至少一个输入
            if (!excludeInputNodes.contains(node.getType())) {
                if (node.getInNodes().isEmpty()) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(
                            MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.least"), node.getId())));
                }
            }
            // 节点至少一个输出
            if (!excludeOutputNodes.contains(node.getType())) {
                if (node.getOutNodes().isEmpty()) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(
                            MessageFormat.format(i18nUtil.getMessage("workflow.validate.output.least"), node.getId())));
                }
            }
        }
    }

    private void validateNodeConfig(String projectId, String workspaceId, Map<String, Node> nodeMap,
        Map<String, List<String>> inputReference, List<WorkflowValidationVOErrors> errors) {

        try {
            Map<String, List<IRConfig>> irConfigs =
                JSON.parseObject(workflowSchema, new com.alibaba.fastjson2.TypeReference<>() {});
            Set<String> modelIds = modelServiceManager.queryAllAvailableServiceIds(projectId, workspaceId);
            if (modelIds.isEmpty()) {
                log.warn("Not found available model service. project:{} workspace:{}", projectId, workspaceId);
            }
            ValidateConfigWrapper validateConfigData = ValidateConfigWrapper.builder()
                .inputReference(inputReference)
                .modelIds(modelIds)
                .errors(errors)
                .build();
            for (Node node : nodeMap.values()) {
                // 意图容器节点处理
                if (NodeType.INTENT_DETECTION_CONTAINER.getType().equalsIgnoreCase(node.getType())) {
                    validateIntentContainerNode(projectId, workspaceId, node, errors);
                    continue;
                }
                // 插件节点，检验鉴权信息
                if (NodeType.PLUGIN.getType().equalsIgnoreCase(node.getType())) {
                    validatePluginAuth(projectId, workspaceId, node, errors);
                }

                // 校验提问节点的Config
                if (NodeType.QUESTIONER.getType().equals(node.getType())) {
                    validateQuestionerNodeConfig(node, errors);
                }
                validateConfigData.setNode(node);

                if (NodeType.EMPTY.getType().equals(node.getType())) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.node.empty")));
                    continue;
                }
                if (NodeType.STREAM_TRANSFORM.getType().equals(node.getType())) {
                    validateStreamTransformNodeConfig(node, errors);
                }
                for (IRConfig irConfig : irConfigs.get(node.getType())) {
                    String id = irConfig.getId();
                    Map<String, Object> configs =
                        node.getNodeInfo().getConfigs() == null ? new HashMap<>() : node.getNodeInfo().getConfigs();
                    validateConfig(configs.get(id), irConfig, validateConfigData);
                }
                // 额外校验部分节点config配置
                NodeType nodeType = NodeType.fromType(node.getType());
                if (nodeType == null) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.invalid.node")));
                } else {
                    validateNodeExtraConfig(nodeType, node, errors);
                    validateExceptionBranch(nodeType, node, errors);
                }

                // 新增校验循环体内节点都需要为非可交互节点
                if (node.getParentLoopNode() != null && interactiveNodeTypes.contains(node.getType())) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(
                            MessageFormat.format(i18nUtil.getMessage("workflow.validate.type.node"), node.getType())));
                }
            }
        } catch (Exception e) {
            log.error("validate node failed!", e);
            throw new AgentStudioException(StudioError.UNEXPECTED_ERROR);
        }
    }

    public void validatePluginAuth(String projectId, String workspaceId, Node node,
        List<WorkflowValidationVOErrors> errors) {
        if (node == null || node.getNodeInfo() == null) {
            return;
        }
        boolean isAuth = pluginDomain.validateAuth(projectId, workspaceId, node.getNodeInfo().getConfigs());

        if (!isAuth) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(i18nUtil.getMessage("openjiuwen.02401121")));
        }
    }

    private void validateExceptionBranch(NodeType nodeType, Node node, List<WorkflowValidationVOErrors> errors) {
        // 节点未配置异常或不支持异常配置节点直接return
        Map<String, Object> nodeConfigs = node.getNodeInfo().getConfigs();
        if (!exceptionNodeTypes.contains(nodeType.getType())
            || (nodeConfigs.get(EXCEPTION_PROCESS) == null && nodeConfigs.get(EXCEPTION_CONFIG) == null)) {
            return;
        }
        // 普通节点的异常分支处理只有配置为异常分支才需要校验，其他放通
        if (nodeConfigs.get(EXCEPTION_PROCESS) != null) {
            ExceptionProcess exceptionProcess =
                JsonUtils.objectToClassType(nodeConfigs.get(EXCEPTION_PROCESS), ExceptionProcess.class);
            if (exceptionProcess == null) {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(i18nUtil.getMessage(StudioError.WORKFLOW_EXCEPTION_CONFIG_INVALID,
                        node.getNodeInfo().getName())));
                return;
            }
            if (!ExceptionProcess.HandleTypeEnum.ERRORBRANCH.equals(exceptionProcess.getHandleType())) {
                return;
            }
        }
        // 参数提取节点配置了异常进入条件才需要处理
        if (nodeConfigs.get(EXCEPTION_CONFIG) != null) {
            ParamExtractionExceptionConfig exceptionConfig =
                JsonUtils.objectToClassType(nodeConfigs.get(EXCEPTION_CONFIG), ParamExtractionExceptionConfig.class);
            if (exceptionConfig == null) {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(i18nUtil.getMessage(StudioError.WORKFLOW_EXCEPTION_CONFIG_INVALID,
                        node.getNodeInfo().getName())));
                return;
            }
        }
        // 无连接异常分支边
        if (!node.getOutBranches().contains(EXCEPTION_PROCESS)) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.branch"), node.getId())));
        }
    }

    private void validateNodeExtraConfig(NodeType nodeType, Node node, List<WorkflowValidationVOErrors> errors) {
        switch (nodeType) {
            case HTTP -> {
                // http节点对配置endpoint做校验白名单黑名单
                try {
                    urlCheckUtils.checkUrl(RequestContextUtils.getRequestProjectId(),
                        WorkflowUtils.parseHttpEndpoint(node.getNodeInfo().getConfigs()));
                } catch (AgentStudioException e) {
                    // url校验失败，记录并返回
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.http.endpoint")));
                }
            }
            case PLUGIN -> {
                if (node.getNodeInfo().getConfigs() != null
                    && node.getNodeInfo().getConfigs().get(Constants.ID) != null) {
                    String pluginId = node.getNodeInfo().getConfigs().get(Constants.ID).toString();
                    Object toolId = node.getNodeInfo().getConfigs().get(Constants.TOOL_ID);
                    if ( toolId != null) {
                        node.getNodeInfo().getConfigs().put(Constants.ID, pluginId + "#" + toolId);
                    } else {
                        node.getNodeInfo().getConfigs().put(Constants.ID, pluginId + "#0");
                    }
                    validateToolExist(node.getNodeInfo().getConfigs(), node, errors);
                } else {
                    // 插件校验错误信息返回
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.plugin.id")));
                }
            }
            case KNOWLEDGE_REPO -> {
                List<KnowledgeRepoEntity> knowledgeRepoEntities = irAdapterService.getReposFromWorkflowNode(
                    node.getNodeInfo().getConfigs(), RequestContextUtils.getRequestProjectId());
                if (CollectionUtils.isEmpty(knowledgeRepoEntities)) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.knowledge.repo")));
                }
            }
            case INTENT_DETECTION, INTENT_COMPLEX_INTENT, BRANCH -> {
                if (node.getNodeInfo().getBranches() != null
                    && node.getOutBranches().size() != node.getNodeInfo().getBranches().size()) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(
                            MessageFormat.format(i18nUtil.getMessage("workflow.validate.branch"), node.getId())));
                }
            }
            case STRUCTURED_MESSAGES_EXCEPTION -> {
                if (node.getNodeInfo().getConfigs() != null
                    && node.getNodeInfo().getConfigs().get("template") != null) {
                    Object templete = node.getNodeInfo().getConfigs().get("template");
                    String templeteStr = templete instanceof String ? (String) templete : JSON.toJSONString(templete);
                    if (!McpJsonUtils.isValidJson(templeteStr)) {
                        errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                            .setType(node.getType())
                            .setReason(i18nUtil.getMessage(StudioError.WORKFLOW_TEMPLATE_INVALID_JSON,
                                node.getNodeInfo().getName())));
                    }
                }
            }
            case AGENT -> validateAgentTools(node, errors);
            default -> {
            }
        }
    }

    private void validateAgentTools(Node node, List<WorkflowValidationVOErrors> errors) {
        Map<String, Object> configs = node.getNodeInfo().getConfigs();

        // 校验agent绑定工具是否存在
        if (configs.get(CommonConstant.Workflow.PLUGINS) != null) {
            List<Map<String, Object>> originPlugins =
                JsonUtils.objectToClass(configs.get(CommonConstant.Workflow.PLUGINS));
            if (originPlugins != null) {
                for (Map<String, Object> pluginConfig : originPlugins) {
                    if (pluginConfig.get(Constants.ID) != null) {
                        validateToolExist(pluginConfig, node, errors);
                    } else {
                        // 插件校验错误信息返回
                        errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                            .setType(node.getType())
                            .setReason(i18nUtil.getMessage("agent.validate.plugin")));
                    }
                }
            }
        }

    }

    private void validateToolExist(Map<String, Object> pluginConfig, Node node,
        List<WorkflowValidationVOErrors> errors) {
        // 插件节点信息校验
        try {
            irAdapterService.getPluginToolEntity(RequestContextUtils.getRequestProjectId(), pluginConfig);
        } catch (AgentStudioException e) {
            // 插件校验错误信息返回
            errors.add(
                new WorkflowValidationVOErrors().setId(node.getId()).setType(node.getType()).setReason(e.getMessage()));
        }
    }

    private void validateAcyclic(Map<String, Node> nodeMap, List<WorkflowValidationVOErrors> errors) {
        List<String> branchNodes = List.of(NodeType.BRANCH.getType(), NodeType.INTENT_DETECTION.getType(),
            NodeType.INTENT_COMPLEX_INTENT.getType());
        List<String> deleted = new ArrayList<>();
        do {
            // 拓扑排序，记录入度为0的节点和分支意图节点
            deleted.clear();
            for (Node node : nodeMap.values()) {
                if (node.getInNodes().isEmpty() || branchNodes.contains(node.getType())) {
                    deleted.add(node.getId());
                }
            }
            // 删除deleted图中节点，更新组件入度
            for (String deletedId : deleted) {
                for (Node outNode : nodeMap.get(deletedId).getOutNodes()) {
                    outNode.getInNodes().remove(nodeMap.get(deletedId));
                }
                nodeMap.remove(deletedId);
            }
        } while (!deleted.isEmpty());
        if (!nodeMap.isEmpty()) {
            for (Node node : nodeMap.values()) {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(i18nUtil.getMessage("workflow.validate.cycle")));
            }
        }
    }

    private void validateNodeParams(Map<String, Node> nodeMap, Map<String, List<String>> outputReference,
        List<WorkflowValidationVOErrors> errors) {
        for (Node node : nodeMap.values()) {
            WorkflowNodeVO nodeInfo = node.getNodeInfo();

            // 子工作流节点校验版本是否被删除
            if (Strings.CS.equals(nodeInfo.getType(), NodeType.WORKFLOW.getType())) {
                validateSubWorkflowNode(nodeInfo, errors);
            }

            // 聚合节点需校验每个聚合组内变量类型是否相等
            if (Strings.CS.equals(nodeInfo.getType(), NodeType.AGGREGATION.getType())) {
                validateAggregationNode(nodeInfo, errors);
            }

            // 设置变量节点需检测左右变量是否类型相同
            if (Strings.CS.equals(nodeInfo.getType(), NodeType.SET_VARIABLE.getType())) {
                validateSetVariableNode(nodeInfo, errors);
            }

            // 判断节点需检测变量值是否合法
            if (Strings.CS.equals(nodeInfo.getType(), NodeType.BRANCH.getType())) {
                validateBranchNode(nodeInfo, node, nodeMap, outputReference, errors);
            }

            // 循环节点需额外检查输出值引用是否为循环体内节点或自身
            if (Strings.CS.equals(nodeInfo.getType(), NodeType.LOOP.getType())) {
                // 循环节点新增未配置校验
                if (CollectionUtils.isEmpty(nodeInfo.getInputs()) || CollectionUtils.isEmpty(nodeInfo.getOutputs())) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.loop.invalid")));
                }
                validateLoopNode(nodeInfo.getOutputs(), node, nodeMap, outputReference, errors);
            }
            if (nodeInfo.getInputs() != null && !nodeInfo.getInputs().isEmpty()) {
                validateInputFields(nodeInfo.getInputs(), node, nodeMap, outputReference, errors);
                validateFieldNames(nodeInfo.getInputs(), node, errors);
            }
            if (nodeInfo.getOutputs() != null && !nodeInfo.getOutputs().isEmpty()) {
                if (nodeInfo.getOutputs().size() > CommonConstant.Workflow.MAX_PARAM_SIZE) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(
                            MessageFormat.format(i18nUtil.getMessage("workflow.validate.output.less"), node.getId())));
                }
                validateFieldNames(nodeInfo.getOutputs(), node, errors);
            }
        }
    }

    private void validateFieldNames(List<WorkflowFieldVO> fieldList, Node node,
        List<WorkflowValidationVOErrors> errors) {
        for (WorkflowFieldVO field : fieldList) {
            if (!isNameValid(field.getName())) {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.composed"), node.getId(),
                        field.getName())));
            }
        }
    }

    private void validateInputFields(List<WorkflowFieldVO> fieldList, Node node, Map<String, Node> nodeMap,
        Map<String, List<String>> outputReference, List<WorkflowValidationVOErrors> errors) {
        Set<WorkflowValidationVOErrors> newErrors = new HashSet<>();
        if (fieldList.size() > CommonConstant.Workflow.MAX_PARAM_SIZE) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.param"), node.getId())));
            return;
        }
        // QA 节点随机模式跳过输入参数校验
        if (NodeType.QA.getType().equals(node.getNodeInfo().getType())
            && QA_NODE_STRATEGY_RANDOM.equals(node.getNodeInfo().getConfigs().get(QA_NODE_STRATEGY))) {
            return;
        }
        for (WorkflowFieldVO field : fieldList) {
            WorkflowFieldVOValue value = field.getValue();
            if (NodeType.HTTP.getType().equals(node.getNodeInfo().getType()) && value.getType() == WorkflowFieldVOValue.TypeEnum.NESTED) {
                JSONArray schema = (JSONArray) field.getSchema();
                for (Object nestedField: schema) {
                    WorkflowFieldVO parsedNestedField = JSON.parseObject(JSON.toJSONString(nestedField),
                        WorkflowFieldVO.class);
                    // 检查key
                    String nestedName = parsedNestedField.getName();
                    checkName(nestedName, node, field, newErrors);
                    // 检查value
                    WorkflowFieldVOValue nestedValue = parsedNestedField.getValue();
                    if (nestedValue.getType() == WorkflowFieldVOValue.TypeEnum.REF) {
                        checkRefValue(nestedValue, node, field, newErrors, nodeMap, outputReference);
                    } else if (nestedValue.getType() == WorkflowFieldVOValue.TypeEnum.LITERAL) {
                        checkLiteralValue(nestedValue, node, field, newErrors);
                    }
                }
            } else if (value.getType() == WorkflowFieldVOValue.TypeEnum.REF) {
                checkRefValue(value, node, field, newErrors, nodeMap, outputReference);
            } else if (value.getType() == WorkflowFieldVOValue.TypeEnum.LITERAL && field.isRequired()) {
                checkLiteralValue(value, node, field, newErrors);
            }
        }
        errors.addAll(newErrors);
    }

    private void checkName(String key, Node node, WorkflowFieldVO field, Set<WorkflowValidationVOErrors> errors) {
        if (StringUtils.isEmpty(key)) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.empty"),
                    field.getName())));
        } else if (!VALID_PATTERN.matcher(key).matches()) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.invalid"),
                    field.getName())));
        }
    }

    private void checkLiteralValue(WorkflowFieldVOValue value, Node node, WorkflowFieldVO field,
        Set<WorkflowValidationVOErrors> errors) {
        if (value.getContent() == null || StringUtils.isEmpty(value.getContent().toString())) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.empty"),
                    field.getName())));
        }
    }

    private void checkRefValue(WorkflowFieldVOValue value, Node node, WorkflowFieldVO field,
        Set<WorkflowValidationVOErrors> errors, Map<String, Node> nodeMap,
        Map<String, List<String>> outputReference) {
        if (value.getContent() == null || StringUtils.isEmpty(value.getContent().toString())) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.empty"),
                    field.getName())));
        } else {
            ObjectMapper objectMapper = new ObjectMapper();
            Map<String, String> refMap =
                objectMapper.convertValue(value.getContent(), new TypeReference<>() {});
            if (isRefValid(refMap, outputReference)) {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.input.reference"),
                        field.getName())));
            } else {
                // 若引用节点存在，增加判断引用节点从属关系
                validateReference(nodeMap, refMap, node,
                    field.getName(), errors);
            }
        }
    }

    private void validateConfig(Object element, IRConfig irConfig, ValidateConfigWrapper ValidateConfigData) {
        Node node = ValidateConfigData.getNode();
        Map<String, List<String>> inputReferences = ValidateConfigData.getInputReference();
        Set<String> modelIds = ValidateConfigData.getModelIds();
        List<WorkflowValidationVOErrors> error = ValidateConfigData.getErrors();

        // 空属性特殊检查
        if (element == null) {
            // 必填属性为空报错
            if (irConfig.isRequired()) {
                error.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.element_empty"),
                        node.getId(), irConfig.getId())));
            }
            return;
        }
        if (irConfig.getListSchema() != null && Strings.CS.equals(irConfig.getType(), TypeEnum.ARRAY.toString())) {
            // list类型将每个元素提取进行校验
            List<Object> subElements = JsonUtils.objectToClass(element);
            IRConfig subIrConfig = irConfig.getListSchema();
            if (subElements != null) {
                for (Object subElement : subElements) {
                    validateConfig(subElement, subIrConfig, ValidateConfigData);
                }
            }
        } else if (irConfig.getObjectSchema() != null
            && Strings.CS.equals(irConfig.getType(), TypeEnum.OBJECT.toString())) {
            // object类型提取每个属性进行校验
            List<IRConfig> subIrConfigs = irConfig.getObjectSchema();
            Map<String, Object> elementMap = JsonUtils.objectToClass(element);
            for (IRConfig subIrConfig : subIrConfigs) {
                if (elementMap != null) {
                    validateConfig(elementMap.get(subIrConfig.getId()), subIrConfig, ValidateConfigData);
                }
            }
        } else {
            // 基础属性类型校验
            List<String> inputField =
                inputReferences.get(node.getId()) != null ? inputReferences.get(node.getId()) : new ArrayList<>();
            if (!isTypeValid(element, irConfig, inputField, node) || !isModelValid(element, irConfig, modelIds)) {
                // 模型字段报错只保留一个即可
                if (CommonConstant.MODEL_PARAMS.contains(irConfig.getId())) {
                    validateModelParams(node, error);
                } else {
                    String[] params = StringUtils.substringsBetween(element.toString(), "{{", "}}");
                    error.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.reference"), irConfig.getId(), Arrays.toString(params))));
                }
            }
        }
    }

    private void validateIntentContainerNode(String projectId, String workspaceId, Node node,
        List<WorkflowValidationVOErrors> errors) {
        List<WorkflowBranchVO> branches = node.getNodeInfo().getBranches();
        if (CollectionUtils.isEmpty(branches)) {
            return;
        }

        // 校验意图容器节点引用的工作流中模型是否有校
        Set<String> isCheckedId = new HashSet<>();
        for (WorkflowBranchVO workflowBranchVO : branches) {
            Map<String, Object> workflowConfig = workflowBranchVO.getConfigs();
            String workflowId =
                Optional.ofNullable(workflowConfig.get(CommonConstant.Workflow.ID)).orElse("").toString();
            if (StringUtils.isEmpty(workflowId)) {
                continue;
            }
            if (isCheckedId.contains(workflowId)) {
                continue;
            }

            isCheckedId.add(workflowId);
            String versionId = workflowConfig.get(CommonConstant.Workflow.VERSION_ID).toString();
            ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionId);
            String workflowInfo = obsService.downloadObsFile(releaseVersion.getDslPath());
            WorkflowVO workflowDsl = JSON.parseObject(workflowInfo, WorkflowVO.class);
            WorkflowValidationVO validate = validate(projectId, workspaceId, workflowDsl);
            if (validate.isSuccess()) {
                continue;
            }

            // 模型报错只保留一个即可
            for (WorkflowValidationVOErrors error : validate.getErrors()) {
                if (CommonConstant.MODEL_MSG.equalsIgnoreCase(error.getReason())) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.name"),
                            workflowConfig.get(CommonConstant.Workflow.NAME), CommonConstant.MODEL_MSG)));
                    break;
                }
            }
        }
    }

    /**
     * 校验模型配置是否有校
     *
     * @param element node元素
     * @param irConfig ir配置
     * @param modelIds 模型id列表
     * @return 校验结果
     */
    private boolean isModelValid(Object element, IRConfig irConfig, Set<String> modelIds) {
        if (!CommonConstant.ModelParam.MODEL_DEPLOYMENT_ID.equals(irConfig.getId())) {
            return true;
        }

        boolean ans = modelIds.contains(element.toString());
        if (!ans) {
            log.error("Model id is not exist. modelId:{}", irConfig.getId());
        }
        return ans;
    }

    private void validateModelParams(Node node, List<WorkflowValidationVOErrors> errors) {
        boolean doNeedAppend = true;
        for (WorkflowValidationVOErrors error : errors) {
            if (Strings.CS.equals(error.getId(), node.getId()) && Strings.CS.equals(error.getType(), node.getType())
                && Strings.CS.equals(error.getReason(), CommonConstant.MODEL_MSG)) {
                doNeedAppend = false;
            }
        }
        if (doNeedAppend) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(i18nUtil.getMessage("workflow.validate.model.invalid")));
        }
    }

    /**
     * 验证节点归属关系
     *
     * @param nodeMap 节点关系表
     * @param refMap 引用节点关系表
     * @param currentNode 当前节点
     * @param fieldName 当前字段
     * @param errors 错误信息
     */
    public void validateReference(Map<String, Node> nodeMap, Map<String, String> refMap, Node currentNode, String fieldName,
        Set<WorkflowValidationVOErrors> errors) {

        // 环境变量不属于任何节点，不需要验证和节点的引用关系
        if (Strings.CI.equals(refMap.get(CommonConstant.Workflow.SOURCE), "environment") || Strings.CI.equals(
            refMap.get(CommonConstant.Workflow.SOURCE), "request")) {
            return;
        }
        String referenceNodeId = refMap.get(CommonConstant.Workflow.REF_NODE_ID);
        String currentNodeId = currentNode.getId();

        // 保存图可能含有环，防止循环
        Map<String, Boolean> visited = nodeMap.keySet().stream().collect(Collectors.toMap(k -> k, k -> false));

        // 从被引用节点使用广度优先遍历查找+去重，当前支持引用自身，从被引用节点开始查找
        Queue<Node> handleNode = new LinkedList<>();
        if (nodeMap.get(referenceNodeId) != null) {
            visited.put(referenceNodeId, true);
            handleNode.offer(nodeMap.get(referenceNodeId));
        }

        while (!handleNode.isEmpty()) {
            Node node = handleNode.poll();

            // 如在子节点中找到当前节点，引用正确
            if (Strings.CS.equals(node.getId(), currentNodeId)) {
                return;
            }
            // 如果当前节点为循环体内节点，子节点走到循环体节点，引用正确
            if (currentNode.getParentLoopNode() != null
                && Strings.CS.equals(node.getId(), currentNode.getParentLoopNode().getId())) {
                return;
            }
            if (nodeMap.get(node.getId()) != null) {
                for (Node outNode : nodeMap.get(node.getId()).getOutNodes()) {
                    if (StringUtils.isNotEmpty(outNode.getId()) && visited.containsKey(outNode.getId())
                        && !visited.get(outNode.getId())) {
                        handleNode.offer(outNode);
                        visited.put(outNode.getId(), true);
                    }
                }
            }
        }
        errors.add(new WorkflowValidationVOErrors().setId(currentNodeId)
            .setType(currentNode.getType())
            .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.current.node"), fieldName)));
    }

    private boolean isTypeValid(Object element, IRConfig irConfig, List<String> inputFields, Node node) {
        String type = StringUtils.isNotEmpty(irConfig.getType()) ? irConfig.getType() : TypeEnum.STRING.toString();
        if (Strings.CS.equals(type, TypeEnum.STRING.toString())
            || type.toLowerCase(Locale.ENGLISH).startsWith(TypeEnum.FILE.toString())) {
            return isStringTypeValid(element, irConfig, inputFields, node);
        } else if (Strings.CS.equals(type, TypeEnum.INTEGER.toString())) {
            return element instanceof Integer;
        } else if (Strings.CS.equals(type, TypeEnum.NUMBER.toString())) {
            return element instanceof Number;
        } else if (Strings.CS.equals(type, TypeEnum.BOOLEAN.toString())) {
            return element instanceof Boolean;
        } else {
            return false;
        }
    }

    private boolean isStringTypeValid(Object element, IRConfig irConfig, List<String> inputFields, Node node) {
        // 字符串类型，需要校验非空，模板类型不可引用非本节点输入
        if (element instanceof String) {
            String stringConfig = element.toString();
            Map<String, Object> nodeConfigs = node.getNodeInfo().getConfigs();
            Boolean enableHistory = Boolean.TRUE;
            if (nodeConfigs.get(ENABLE_HISTORY) instanceof Boolean b) {
                enableHistory = b;
            }

            if (!irConfig.isBlank() && StringUtils.isEmpty(stringConfig)) {
                if (!MESSAGE.equals(node.getType())) {
                    // 非消息节点，判断逻辑不变
                    return false;
                }
                if (enableHistory) {
                    // 消息节点,历史打开:不为空，历史关闭:可以为空
                    return false;
                }
            }
            if (irConfig.isTemplate()) {
                Set<String> extractedReference = extractReference(stringConfig);
                for (String reference : extractedReference) {
                    if (!inputFields.contains(reference)) {
                        return false;
                    }
                }
            }
            return true;
        } else {
            return false;
        }
    }

    /**
     * 验证用户权限是否合法（当前只校验user_id相等）
     *
     * @param workflowEntity 工作流实例
     */
    public void validateModifyPrivilege(WorkflowEntity workflowEntity, String projectId, String workspaceId) {
        // 管理租户不校验
        if (Strings.CS.equals(RequestContextUtils.getRequestProjectId(), opSvcProjectId)) {
            return;
        }
        // 只有owner有管理面权限(修改删除)
        if (!Strings.CS.equals(workflowEntity.getProjectId(), projectId)
            || !Strings.CS.equals(workflowEntity.getWorkspaceId(), workspaceId)) {
            log.error("Privilege Error!, workflow projectId:{}, projectId:{}, workflow workspaceId:{}, workspaceId:{}",
                workflowEntity.getProjectId(), projectId, workflowEntity.getWorkspaceId(), workspaceId);
            throw new AgentStudioException(StudioError.PRIVILEGE_ERROR);
        }
    }

    /**
     * 验证用户中文名是否合法
     *
     * @param name 中文名
     */
    public void validateName(String name) {
        if (StringUtils.isEmpty(name)) {
            throw new AgentStudioException(StudioError.WORKFLOW_NAME_REPEATED);
        }
        if (name.length() > MAX_NAME_SIZE) {
            throw new AgentStudioException(StudioError.WORKFLOW_NAME_EXCEEDS_LIMIT);
        }
        // 工作流中文名后端接口新增校验
        Matcher matcher = namePattern.matcher(name);
        if (!matcher.matches()) {
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED);
        }
    }

    /**
     * 清洗字符串：移除非法字符 + 截断长度 + 去除首尾空格
     *
     * @param name     原始字符串
     * @return 清洗后的安全字符串
     */
    public String sanitizeName(String name) {
        if (name == null || name.isEmpty()) {
            return "";
        }

        String cleanedName = invalidNamePatter.matcher(name).replaceAll("").trim();
        if (cleanedName.length() > MAX_NAME_SIZE) {
            cleanedName = cleanedName.substring(0, MAX_NAME_SIZE).trim();
        }
        return cleanedName;
    }

    /**
     * 验证用户英文名是否合法
     *
     * @param code 英文名
     */
    public void validateCode(String code) {
        if (StringUtils.isEmpty(code)) {
            throw new AgentStudioException(StudioError.WORKFLOW_EN_NAME_REPEATED);
        }
        if (code.length() > MAX_NAME_SIZE) {
            throw new AgentStudioException(StudioError.WORKFLOW_NAME_EXCEEDS_LIMIT);
        }
        // 工作流英文名后端接口新增校验
        Matcher matcher = codePattern.matcher(code);
        if (!matcher.matches()) {
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED);
        }
    }

    /**
     * 验证用户上传头像
     *
     * @param icon 头像
     */
    public void validateIcon(String icon) {
        if (StringUtils.isEmpty(icon)) {
            throw new AgentStudioException(StudioError.WORKFLOW_ICON_EMPTY);
        }
        String base64Image = icon.substring(icon.indexOf(CommonConstant.SEPARATOR) + 1);

        // 检查base64图片大小是否符合要求
        byte[] imageBytes = Base64.getDecoder().decode(base64Image);
        if (Integer.parseInt(iconMaxSize) < imageBytes.length / KB) {
            log.error("Workflow icon size exceeds limit {} KB", iconMaxSize);
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED_ICON, iconMaxSize);
        }
    }

    /**
     * 验证type
     *
     * @param workflowType 工作流类型
     */
    public void validateWorkflowType(String workflowType) {
        if (!Strings.CS.equals(workflowType, "chat") && !Strings.CS.equals(workflowType, "task")) {
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED);
        }
    }

    /**
     * 验证工作流全局配置
     *
     * @param configs 全局配置
     */
    public void validateWorkflowConfigs(Map<String, Object> configs) {
        if (configs == null) {
            return;
        }

        // 验证工作流中使用的环境是否有效
        this.environmentServiceManagerService.validateEnvironmentId(configs.get("environment") == null ? "" : String.valueOf(configs.get("environment")));

        // 验证内容审核
        Object object = configs.get(Constants.Workflow.CONTENT_REVIEW);
        if (object == null) {
            return;
        }
        Map<String, Object> objectMap = JsonUtils.objectToClass(object);

        validateContentReview(objectMap);

        // 校验用户画像配置
        Object userProfileConfigObj = configs.get(Constants.Workflow.USER_PROFILE);
        if (userProfileConfigObj != null) {
            UserProfileMemoryConfig userProfileMemoryConfig = JsonUtils.objectToClassType(userProfileConfigObj,
                UserProfileMemoryConfig.class);
            agentMemoryConfigService.checkUserProfileConfig(userProfileMemoryConfig);
        }
    }

    /**
     * 校验内容审核
     *
     * @param contentReview 审核配置
     */
    public void validateContentReview(Map<String, Object> contentReview) {
        if (contentReview == null || contentReview.isEmpty()) {
            return;
        }
        SensitiveEntity entity = JsonUtils.json2ObjQuietly(JsonUtils.toJson(contentReview), SensitiveEntity.class);
        if (entity == null) {
            throw new AgentStudioException(StudioError.CONTENT_REVIEW_ERROR);
        }
        Set<String> word = new HashSet<>();
        Set<String> duplicateWord = new HashSet<>();
        BiConsumer<List<SensitiveEntity.WordsWrapper>, String> validates = (wrappers, tag) -> {
            if (wrappers == null) {
                return;
            }
            // 每种敏感词处理类型最多 CR_GROUP_MAX_SIZE(10) 组数据
            if (wrappers.size() > Constants.Workflow.CR_GROUP_MAX_SIZE) {
                throw new AgentStudioException(StudioError.CONTENT_REVIEW_ERROR_SIZE,
                    Constants.Workflow.CR_GROUP_MAX_SIZE, tag);
            }
            for (SensitiveEntity.WordsWrapper wrapper : wrappers) {
                // 每组敏感词长度最大 CR_KEYWORDS_MAX_LENGTH(1000) 个字符
                if (StringUtils.length(wrapper.getKeywords()) > Constants.Workflow.CR_KEYWORDS_MAX_LENGTH) {
                    throw new AgentStudioException(StudioError.CONTENT_REVIEW_ERROR_LENGTH,
                        Constants.Workflow.CR_KEYWORDS_MAX_LENGTH, tag);
                }
                // 记录重复敏感词
                for (String keyword : wrapper.getKeywordsList()) {
                    if (word.contains(keyword)) {
                        duplicateWord.add(keyword);
                    }
                    word.add(keyword);
                }

                // 校验字符长度
                if (StringUtils.length(wrapper.getReplace()) > Constants.Workflow.REPLACE_WORD_MAX_LENGTH) {
                    throw new AgentStudioException(StudioError.REPLACE_WORD_ERROR_LENGTH,
                        Constants.Workflow.REPLACE_WORD_MAX_LENGTH, "replace");
                }
                if (StringUtils.length(wrapper.getInputReplyText()) > Constants.Workflow.INPUT_TEXT_MAX_LENGTH) {
                    throw new AgentStudioException(StudioError.INPUT_TEXT_ERROR_LENGTH,
                        Constants.Workflow.INPUT_TEXT_MAX_LENGTH, "input_text");
                }
                if (StringUtils.length(wrapper.getOutputReplyText()) > Constants.Workflow.OUTPUT_TEXT_MAX_LENGTH) {
                    throw new AgentStudioException(StudioError.OUTPUT_TEXT_ERROR_LENGTH,
                        Constants.Workflow.OUTPUT_TEXT_MAX_LENGTH, "output_text");
                }
            }
        };
        if (entity.getFilter() != null) {
            validates.accept(List.of(entity.getFilter()), "filter");
        }
        validates.accept(entity.getReplace(), "replace");
        validates.accept(entity.getReply(), "reply");
        if (duplicateWord.size() > 0) {
            throw new AgentStudioException(StudioError.CONTENT_REVIEW_ERROR);
        }
    }

    /**
     * 获取当前租户所有可见工作流英文名合集
     *
     * @return 英文名合集
     */
    public Set<String> getCurrentCodes(String projectId, String workspaceId) {
        // 获取当前user id下所有英文名
        return workflowMapper.getAvailableWorkflowEntityByWorkspaceId(projectId, workspaceId)
            .stream()
            .map(WorkflowEntity::getCode)
            .collect(Collectors.toSet());
    }

    /**
     * 获取当前空间所有可见工作流中文名合集
     *
     * @return 中文名合集
     */
    public Set<String> getCurrentNames(String projectId, String workspaceId) {
        // 获取当前user id下所有名称
        return workflowMapper.getAvailableWorkflowEntityByWorkspaceId(projectId, workspaceId)
            .stream()
            .map(WorkflowEntity::getName)
            .collect(Collectors.toSet());
    }

    private Set<String> extractReference(String input) {
        // 定义正则表达式模式来匹配 {{val}} 和 {{input}}
        Matcher matcher = referencePattern.matcher(input);
        List<String> sysFields = JSON.parseObject(systemFields, new com.alibaba.fastjson2.TypeReference<>() {});

        // 存储提取出的值
        Set<String> extractedValues = new HashSet<>();

        // 遍历匹配项
        while (matcher.find()) {
            // 提取匹配项中的值
            String value = matcher.group(1);

            // 如果值之前没有添加过，则添加
            if (!sysFields.contains(value)) {
                extractedValues.add(value);
            }
        }
        return extractedValues;
    }

    private boolean isNameValid(String input) {
        // 正则表达式模式，表示不能以数字开头，可以包含字母、数字、下划线和中划线
        String regex = "^[a-zA-Z_][a-zA-Z0-9_-]*$";
        if (input == null) {
            return false;
        }
        return input.matches(regex);
    }

    private void validateSubWorkflowNode(WorkflowNodeVO nodeInfo, List<WorkflowValidationVOErrors> errors) {
        Map<String, Object> nodeConfig = nodeInfo.getConfigs();
        String workflowId = nodeConfig.get("id").toString();
        String versionId = nodeConfig.get("version_id").toString();
        ReleaseVersion releaseVersion = releaseVersionMapper.selectByAppIdAndVersionId(workflowId, versionId);

        // 如果子工作流被删除
        if (releaseVersion == null) {
            errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                    .setType(nodeInfo.getType())
                    .setReason(i18nUtil.getMessage("workflow.validate.workflow.node")));
        }
    }

    private void validateAggregationNode(WorkflowNodeVO nodeInfo, List<WorkflowValidationVOErrors> errors) {
        Map<String, List<Object>> groupConfigs = JsonUtils.objectToClass(nodeInfo.getConfigs().get("groups"));

        // group不能为空
        if (groupConfigs != null && !groupConfigs.isEmpty()) {
            for (Map.Entry<String, List<Object>> groupConfig : groupConfigs.entrySet()) {
                List<GroupConfig> groupConfigList = groupConfig.getValue().stream().map(m -> {
                    TypeReference<GroupConfig> type = new TypeReference<>() {};
                    return JsonUtils.json2Obj(JsonUtils.toJson(m), type);
                }).toList();
                if (groupConfigList.isEmpty()) {
                    errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                        .setType(nodeInfo.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.agg.node")));
                } else {
                    validateGroupType(groupConfig.getKey(), groupConfigList, nodeInfo, errors);
                }
            }
        } else {
            errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                .setType(nodeInfo.getType())
                .setReason(i18nUtil.getMessage("workflow.validate.agg.node.groups")));
        }
    }

    private void validateBranchNode(WorkflowNodeVO nodeInfo, Node node, Map<String, Node> nodeMap,
        Map<String, List<String>> outputReference, List<WorkflowValidationVOErrors> errors) {
        // 提取判断节点所有左值右值进行合法性校验
        List<WorkflowFieldVO> workflowFieldVOS = new ArrayList<>();
        nodeInfo.getBranches().forEach(workflowBranchVo -> {
            // 提取除默认节点外所有输入参数
            if (!Strings.CS.equals(CommonConstant.DEFAULT_BRANCH_ID, workflowBranchVo.getId())) {
                WorkflowBranchConfigVO workflowBranchConfig = JSON.parseObject(
                    JSON.toJSONString(workflowBranchVo.getConfigs(), JSONWriter.Feature.WriteMapNullValue),
                    WorkflowBranchConfigVO.class);
                workflowBranchConfig.getConditions().forEach(condition -> {
                    workflowFieldVOS.add(condition.getLeft());
                    workflowFieldVOS.add(condition.getRight());
                });
            }
        });
        workflowFieldVOS.removeIf(Objects::isNull);
        validateInputFields(workflowFieldVOS, node, nodeMap, outputReference, errors);
    }

    private void validateSetVariableNode(WorkflowNodeVO nodeInfo, List<WorkflowValidationVOErrors> errors) {
        ObjectMapper objectMapper = new ObjectMapper();
        List<SetVariableConfig> variablesList =
            objectMapper.convertValue(nodeInfo.getConfigs().get("settings"), new TypeReference<>() {});

        // settings不能为空
        if (variablesList != null && !variablesList.isEmpty()) {
            for (SetVariableConfig variable : variablesList) {
                if (!isSchemaTypeSame(variable.getLeft().getType(), variable.getLeft().getSchema(),
                    variable.getRight().getType(), variable.getRight().getSchema())) {
                    errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                        .setType(nodeInfo.getType())
                        .setReason(i18nUtil.getMessage("workflow.validate.set.sam.type")));
                    return;
                }
            }
        } else {
            errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                .setType(nodeInfo.getType())
                .setReason(i18nUtil.getMessage("workflow.validate.set.node.contain")));
        }
    }

    private void validateLoopNode(List<WorkflowFieldVO> fieldList, Node node, Map<String, Node> nodeMap,
        Map<String, List<String>> outputReference, List<WorkflowValidationVOErrors> errors) {

        for (WorkflowFieldVO field : fieldList) {
            WorkflowFieldVOValue workflowFieldVOValue = field.getValue();
            if (workflowFieldVOValue.getType() == WorkflowFieldVOValue.TypeEnum.REF) {
                if (workflowFieldVOValue.getContent() == null
                    || StringUtils.isEmpty(workflowFieldVOValue.getContent().toString())) {
                    errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                        .setType(node.getType())
                        .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.should.not.empty"),
                            field.getName())));
                } else {
                    ObjectMapper objectMapper = new ObjectMapper();
                    Map<String, String> refMaps =
                        objectMapper.convertValue(workflowFieldVOValue.getContent(), new TypeReference<>() {});
                    if (isRefValid(refMaps, outputReference)) {
                        errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                            .setType(node.getType())
                            .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.output.not.exist"),
                                field.getName())));
                    } else {
                        // 验证循环节点输出值是否合法
                        validateLoopOutputReference(nodeMap.get(refMaps.get(CommonConstant.Workflow.REF_NODE_ID)),
                            refMaps.get(CommonConstant.Workflow.REF_VAR_NAME), node, field, errors);
                    }
                }
            } else {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(
                        MessageFormat.format(i18nUtil.getMessage("workflow.validate.loop.output"), field.getName())));
            }
        }
    }

    private boolean isRefValid(Map<String, String> refMap, Map<String, List<String>> outputReference) {
        String source = refMap.get(CommonConstant.Workflow.SOURCE);
        if (Strings.CI.equals(source, "environment") || Strings.CI.equals(source, "request")) {
            return false;
        }
        String refNodeId = refMap.get(CommonConstant.Workflow.REF_NODE_ID);
        String refVarName = refMap.get(CommonConstant.Workflow.REF_VAR_NAME);
        if (refNodeId == null || refVarName == null) {
            return true;
        }
        if (!outputReference.containsKey(refNodeId)) {
            return true;
        }
        String varName = StringUtils.substringBefore(StringUtils.substringBefore(refVarName, "."), "[");
        return !outputReference.get(refNodeId).contains(varName);
    }

    private void validateLoopOutputReference(Node referNode, String referVarName, Node currentNode,
        WorkflowFieldVO field, List<WorkflowValidationVOErrors> errors) {
        // 循环节点输出值仅支持引用循环体内部，且属性为array，或循环体自身中间变量 intermediate_loop_var
        if (referNode.getParentLoopNode() != null
            && Strings.CS.equals(referNode.getParentLoopNode().getId(), currentNode.getId())
            && Strings.CS.equals(TypeEnum.ARRAY.toString(), field.getType().toLowerCase(Locale.ROOT))) {
            return;
        }
        if (referNode.getParentLoopNode() == null && Strings.CS.equals(referNode.getId(), currentNode.getId())
            && referVarName.startsWith("intermediate_loop_var")) {
            return;
        }
        errors.add(new WorkflowValidationVOErrors().setId(currentNode.getId())
            .setType(currentNode.getType())
            .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.loop.body"), field.getName())));
    }

    private void validateGroupType(String groupName, List<GroupConfig> groupConfigList, WorkflowNodeVO nodeInfo,
        List<WorkflowValidationVOErrors> errors) {
        // 根据config提取相同类型输入类型
        Set<String> sameTypeInputs = groupConfigList.stream().map(GroupConfig::getName).collect(Collectors.toSet());

        // 获取输出节点对应类型
        WorkflowFieldVO workflowFieldVO = null;
        for (WorkflowFieldVO output : nodeInfo.getOutputs()) {
            if (Strings.CS.equals(output.getName(), groupName)) {
                workflowFieldVO = output;
            }
        }
        // config中与实际出入输出不匹配，校验错误
        if (workflowFieldVO == null) {
            errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                .setType(nodeInfo.getType())
                .setReason(i18nUtil.getMessage("workflow.validate.agg.invalid")));
            return;
        }
        // 同一个group每个引用的输入进行类型判断
        for (WorkflowFieldVO input : nodeInfo.getInputs()) {
            if (sameTypeInputs.contains(input.getName()) && !isSchemaTypeSame(input.getType(), input.getSchema(),
                workflowFieldVO.getType(), workflowFieldVO.getSchema())) {
                errors.add(new WorkflowValidationVOErrors().setId(nodeInfo.getId())
                    .setType(nodeInfo.getType())
                    .setReason(MessageFormat.format(i18nUtil.getMessage("workflow.validate.agg.type"), groupName)));
                return;
            }
        }
    }

    private boolean isSchemaTypeSame(String srcType, Object srcSchema, String dstType, Object dstSchema) {
        // 如同一组group内类型不同直接返回false
        if (!Strings.CS.equals(srcType, dstType)) {
            return false;
        }
        // 复杂类型递归变量子项
        if (Strings.CS.equals(TypeEnum.ARRAY.toString(), srcType)) {
            return isListSchemaSame(srcSchema, dstSchema);
        } else if (Strings.CS.equals(TypeEnum.OBJECT.toString(), srcType)) {
            return isObjectSchemaSame(srcSchema, dstSchema);
        } else {
            return true;
        }
    }

    private boolean isObjectSchemaSame(Object srcSchema, Object dstSchema) {
        // object类型schema转换
        List<Object> srcList = JsonUtils.objectToClass(srcSchema);
        List<Object> dstList = JsonUtils.objectToClass(dstSchema);
        if (srcList == null || dstList == null) {
            return false;
        }
        // json类型转换, 转换失败或元素不对齐直接失败
        List<Map<String, Object>> srcListSchemas =
            srcList.stream().map(JsonUtils::<Map<String, Object>> objectToClass).toList();
        List<Map<String, Object>> dstListSchemas =
            dstList.stream().map(JsonUtils::<Map<String, Object>> objectToClass).toList();
        if (srcListSchemas.contains(null) || dstListSchemas.contains(null)
            || srcListSchemas.size() != dstListSchemas.size()) {
            return false;
        }
        // object类型对每个键值对按name进行排序，两组逐一比对
        List<Map<String, Object>> sortedSrc = srcListSchemas.stream()
            .sorted(Comparator.comparing(m -> m.getOrDefault(NAME, StringUtils.EMPTY).toString()))
            .toList();
        List<Map<String, Object>> sortedDst = dstListSchemas.stream()
            .sorted(Comparator.comparing(m -> m.getOrDefault(NAME, StringUtils.EMPTY).toString()))
            .toList();
        for (int i = 0; i < sortedSrc.size(); ++i) {
            Map<String, Object> src = sortedSrc.get(i);
            Map<String, Object> dst = sortedDst.get(i);
            if (!Strings.CS.equals(src.getOrDefault(NAME, StringUtils.EMPTY).toString(),
                dst.getOrDefault(NAME, StringUtils.EMPTY).toString())) {
                return false;
            }
            if (!isSchemaTypeSame(src.getOrDefault(TYPE, TypeEnum.STRING.toString()).toString(), src.get(SCHEMA),
                dst.getOrDefault(TYPE, TypeEnum.STRING.toString()).toString(), dst.get(SCHEMA))) {
                return false;
            }
        }
        return true;
    }

    private boolean isListSchemaSame(Object srcSchema, Object dstSchema) {
        // list类型schema转换
        Map<String, Object> src = JsonUtils.objectToClass(srcSchema);
        Map<String, Object> dst = JsonUtils.objectToClass(dstSchema);
        if (src == null || dst == null) {
            return false;
        } else {
            return isSchemaTypeSame(src.getOrDefault(TYPE, TypeEnum.STRING.toString()).toString(), src.get(SCHEMA),
                dst.getOrDefault(TYPE, TypeEnum.STRING.toString()).toString(), dst.get(SCHEMA));
        }
    }

    public void validateTools(List<Map<String, Object>> nodes, String projectId, String workspaceId) {
        if (nodes == null) {
            return;
        }

        List<Map<String, Object>> plugins = nodes.stream().filter(node -> "Plugin".equals(node.get("type"))).toList();
        plugins.forEach(plugin -> {
            Map<String, Object> config = JsonUtils.objectToClass(plugin.get("configs"));
            if (config == null) {
                return;
            }
            validatePluginException(config);
            String pluginId = (String) config.get("id");
            String toolId = (config.containsKey("tool_id") && config.get("tool_id") != null
                    && !((String) config.get("tool_id")).isEmpty()) ? (String) config.get("tool_id") : "0";
            // 支持引用共享插件
            String versionId = (String) config.get("version_id");
            ShareScopeEntity shareScopeEntity = shareScopeMapper.selectShareScopesByResourceIdAndWorkspaceId(
                    pluginId, workspaceId);
            // 非空表示跨空间引用查询，检查版本号是否被共享
            String shareWorkspaceId = null;
            if (shareScopeEntity != null) {
                // 检查工作流是否被授权
                ShareResourceEntity shareResourceEntity
                        = shareResourceMapper.selectShareResourceEntityByResourceId(pluginId);
                if (StringUtils.isNotEmpty(versionId) && shareResourceEntity.getVersionList()
                        .contains(versionId)) {
                    shareWorkspaceId = shareResourceEntity.getWorkspaceId();
                }
            }
            ToolEntity toolEntity = pluginDomain.buildToolByPlugin(projectId,
                    StringUtils.isNotEmpty(shareWorkspaceId) ? shareWorkspaceId : workspaceId, pluginId, toolId);

            if (!isToolAccessAllowed(publishCrossWorkspace, pluginChoice, workspaceId, toolEntity, shareWorkspaceId)) {
                log.error("agent information failed to check");
                throw new AgentStudioException(StudioError.CHECK_AGENT_INFO_FAILED);
            }
        });
    }

    public void validatePluginException(Map<String, Object> config) {
        if (config.containsKey("exception_process")) {
            Object Obj = config.get("exception_process");
            Map<String, Object> exceptionProcess = JsonUtils.objectToClass(Obj);
            if (exceptionProcess == null) {
                return;
            }
            int retryTimes = (int) exceptionProcess.get("retry_times");
            if (retryTimes < 0 || retryTimes > 3) {
                throw new AgentStudioException(StudioError.PLUGIN_EXCEPTION_OVER_LIMIT);
            }
        }
    }

    /**
     * 校验工作流的引用
     * @param nodes nodes
     * @param workspaceId workspaceId
     */
    public void validateIdAndName(List<Map<String, Object>> nodes, String projectId, String workspaceId) {
        if (nodes == null) {
            return;
        }

        Set<String> blockNodeSet = Arrays.stream(StringUtils.split(blockNodes, ",")).collect(Collectors.toSet());
        // 校验更新工作流是否包含隐藏节点
        if (nodes.stream().anyMatch(node -> blockNodeSet.contains(node.get("type").toString()))) {
            log.error("workflow validate failed because contains block nodes");
            throw new AgentStudioException(StudioError.WORKFLOW_BLOCK_NODE_EXIST, blockNodes);
        }

        List<Map<String, Object>> workflows = nodes.stream().filter(node -> NodeType.WORKFLOW.getType().equals(node.get("type"))).toList();
        workflows.forEach(workflow -> {
            Map<String, Object> config = JsonUtils.objectToClass(workflow.get("configs"));
            if (config != null && config.get("id") != null) {
                String workflowId = (String) config.get("id");
                String versionId = (String) config.get("version_id");
                if (StringUtils.isBlank(workflowId)) {
                    return;
                }
                WorkflowEntity workflowEntity = workflowMapper.getWorkflowById(workflowId);
                if (Objects.isNull(workflowEntity)) {
                    throw new AgentStudioException(StudioError.CHILD_WORKFLOW_NOT_EXIST, workflowId);
                }
                if (!Strings.CS.equals(workflowEntity.getWorkspaceId(), workspaceId)) {
                    if (!shareResourceManagerService.checkWorkspaceAuthByResourceOrNot(workspaceId, workflowId)
                        && !publishCrossWorkspace) {
                        throw new AgentStudioException(StudioError.WORKFLOW_NO_PERMISSION, workflowId);
                    }
                }

                // name长度校验
                String name = (String) workflow.get("name");
                if (StringUtils.length(name) > MAX_NAME_SIZE) {
                    throw new AgentStudioException(StudioError.WORKFLOW_NAME_EXCEEDS_LIMIT);
                }
            }
        });
    }

    /**
     * 校验代码节点执行方式是否被允许
     *
     * @param nodes 工作流节点详情
     */
    public void validateCodeExecMode(List<WorkflowNodeVO> nodes, String workflowId) {
        if (nodes == null) {
            return;
        }
        List<WorkflowNodeVO> codeNodes = nodes.stream()
            .filter(node -> NodeType.CODE.getType().equals(node.getType()))
            .toList();

        if (ObjectUtils.isEmpty(codeNodes)) {
            return;
        }
        codeNodes.forEach(code -> {
            Map<String, Object> config = code.getConfigs();
            if (config != null && config.get(EXEC_ENV) != null) {
                String codeExecMode = (String) config.get(EXEC_ENV);
                // hc环境需要校验是否支持沙箱模式运行
                if (CommonConstant.EnvType.HC.equalsIgnoreCase(envType) && !sandboxEnable && SANDBOX.equalsIgnoreCase(
                    codeExecMode)) {
                    log.error("There is an unauthorized code execution method in the workflow. Workflow ID: {}",
                        workflowId);
                    throw new AgentStudioException(StudioError.CODE_NOT_SUPPORT_SANDBOX);
                }
            }
        });
    }

    /**
     * 校验提问器节点配置字段长度
     * @param nodes nodes
     * @param workflowId workflowId
     */
    public void validateQuestionerNode(List<Map<String, Object>> nodes, String workflowId) {
        if (nodes == null) {
            return;
        }
        List<Map<String, Object>> questionerNodes =
            nodes.stream().filter(node -> NodeType.QUESTIONER.getType().equals(node.get("type"))).toList();
        questionerNodes.forEach(questionerNode -> {
            Map<String, Object> config = JsonUtils.objectToClass(questionerNode.get("configs"));
            if (config == null) {
                return;
            }
            String extraPrompt = (String) config.get("extra_prompt_for_fields_extraction");
            String questionContent = (String) config.get("question_content");
            if (extraPrompt != null && extraPrompt.length() > questionerConfigMaxLength
                || questionContent != null && questionContent.length() > questionerConfigMaxLength) {
                log.error("The configuration parameter length of the questioner node exceeds the maximum limit in the"
                    + " workflow. workflow ID:{}", workflowId);
                throw new AgentStudioException(StudioError.QUESTIONER_CONFIG_EXCEED_MAX_LENGTH);
            }
        });
    }

    /**
     * 校验提问节点 Configs
     */
    private void validateQuestionerNodeConfig(Node node, List<WorkflowValidationVOErrors> errors) {
        if (node == null || node.getNodeInfo() == null) {
            return;
        }

        boolean extractFieldsFromResponse = (boolean) node.getNodeInfo().getConfigs().get("extract_fields_from_response");
        String questionContent = (String) node.getNodeInfo().getConfigs().get("question_content");
        if (!extractFieldsFromResponse && StringUtils.isEmpty(questionContent)) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(i18nUtil.getMessage("openjiuwen.02201093")));
        }
    }


    /**
     * 校验流式输出节点 configs
     */
    @SuppressWarnings("unchecked")
    private void validateStreamTransformNodeConfig(Node node, List<WorkflowValidationVOErrors> errors) {
        if (node == null || node.getNodeInfo() == null) {
            return;
        }

        // 校验一定存在frame_template
        Map<String, Object> transformer =  (Map<String, Object>) node.getNodeInfo().getConfigs().get("transformer");
        String frame_template = (String) transformer.get("frame_template");
        if (StringUtils.isEmpty(frame_template)) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(i18nUtil.getMessage("openjiuwen.02201094")));
        }

        // 校验 frame_template 的格式是 json
        try {
            JSONObject.parseObject(frame_template);
        } catch (Exception e) {
            errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                .setType(node.getType())
                .setReason(i18nUtil.getMessage("openjiuwen.02201095")));
        }

        // 校验concat字段是在frame_template里的
        List<String> concatFields = (List<String>) node.getNodeInfo().getConfigs().get("concat");
        for (String concatField : concatFields) {
            if (!frame_template.contains(concatField)) {
                errors.add(new WorkflowValidationVOErrors().setId(node.getId())
                    .setType(node.getType())
                    .setReason(i18nUtil.getMessage("openjiuwen.02201096")));
            }
        }

    }

    /**
     * 校验workflowDetail
     * @param workflowVo workflowVo
     * @param workflowId workflowId
     */
    public void validateWorkflowDetail(WorkflowVO workflowVo, String workflowId) {
        if (workflowVo != null && workflowVo.getId() != null && !workflowId.equals(workflowVo.getId())) {
            log.error("Workflow ID inconsistency: path workflowId={}, workflow_details.id={}",
                workflowId, workflowVo.getId());
            throw new AgentStudioException(StudioError.CHECK_WORKFLOW_INFO_FAILED);
        }
    }

    /**
     * 校验接口组件节点，用于构成图进行校验
     *
     */
    @Data
    public static class Node {
        private String id;

        private String type;

        private WorkflowNodeVO nodeInfo;

        private List<Node> inNodes;

        private List<Node> outNodes;

        private Set<String> outBranches;

        private Node parentLoopNode;

        Node(WorkflowNodeVO nodeInfo) {
            id = nodeInfo.getId();
            type = nodeInfo.getType();
            inNodes = new ArrayList<>();
            outNodes = new ArrayList<>();
            outBranches = new HashSet<>();
            parentLoopNode = null;
            this.nodeInfo = nodeInfo;
        }

        @Override
        public String toString() {
            return String.format("{id='%s', type='%s', node_info=%s}", id, type, nodeInfo.toString());
        }
    }

    private boolean isToolAccessAllowed(boolean publishCrossWorkspace, boolean pluginChoice, String workspaceId,
            ToolEntity toolEntity, String shareWorkspaceId) {
        // 内置预置工具为平台级全局工具，不受工作空间隔离限制
        if (ToolType.INNER.type.equals(toolEntity.getType())) {
            return true;
        }
        if (publishCrossWorkspace || pluginChoice) {
            return true;
        }
        if (shareWorkspaceId != null) {
            return true;
        }
        if (!workspaceId.equals(toolEntity.getWorkspaceId())) {
            return false;
        }
        return !ToolType.INNER.type.equals(toolEntity.getType());
    }
}
